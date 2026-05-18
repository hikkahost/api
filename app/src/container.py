import fcntl
import logging
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar

import docker
from docker.errors import APIError, NotFound
from python_on_whales import DockerClient

from app.config import CONTAINER, SERVER
from app.src.caddy import create_vhost, remove_caddy_user

logger = logging.getLogger(__name__)

client = docker.from_env()
_VALID_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,62}$")
_MAX_BRIDGE_NAME_LEN = 15
_IP_LOCK_PATH = Path("/tmp/hikkahost-ip.lock")
_COMPOSE_RETRY_ATTEMPTS = 3
_COMPOSE_RETRY_DELAY_SEC = 2.0
_BRIDGE_WAIT_TIMEOUT_SEC = 30.0
_BRIDGE_POLL_INTERVAL_SEC = 0.5
_STATS_RETRY_ATTEMPTS = 3
_STATS_RETRY_DELAY_SEC = 0.4

_docker_lock = threading.Lock()
T = TypeVar("T")


def _run_command(args: List[str]) -> None:
    subprocess.run(args, check=False)


def _validate_container_name(name: str) -> None:
    if not isinstance(name, str) or not name:
        raise ValueError("Container name is required")
    if not _VALID_NAME_RE.match(name):
        raise ValueError(
            "Invalid container name. Allowed: letters, numbers, '_', '-', '.'"
        )
    if len(f"br-{name}") > _MAX_BRIDGE_NAME_LEN:
        raise ValueError("Container name is too long for bridge name")


def _parse_port(port) -> int:
    try:
        port_int = int(port)
    except (TypeError, ValueError):
        raise ValueError("Port must be an integer")
    if port_int < 1 or port_int > 65535:
        raise ValueError("Port must be between 1 and 65535")
    return port_int


def _volume_path(name: str) -> Path:
    return Path(os.getcwd()) / "volumes" / name


def _compose_network_name(name: str) -> str:
    return f"{name}_hikka_net"


def _load_env(path: str) -> Dict[str, str]:
    env: Dict[str, str] = {}
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    except FileNotFoundError:
        return {}
    return env


def _build_container_ip(ip_prefix: Optional[str]) -> Optional[str]:
    if not ip_prefix:
        return None
    if re.match(r"^\d+\.\d+\.\d+$", ip_prefix):
        return f"{ip_prefix}.101"
    if re.match(r"^\d+\.\d+\.\d+\.\d+$", ip_prefix):
        return ip_prefix
    return None


def _bridge_exists(bridge_name: str) -> bool:
    result = subprocess.run(
        ["ip", "link", "show", bridge_name],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def _wait_for_bridge(
    bridge_name: str, timeout: float = _BRIDGE_WAIT_TIMEOUT_SEC
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _bridge_exists(bridge_name):
            return True
        time.sleep(_BRIDGE_POLL_INTERVAL_SEC)
    return False


def _ip_suffix_from_prefix(ip_prefix: str) -> Optional[int]:
    match = re.match(r"^192\.168\.(\d+)$", ip_prefix.strip())
    if not match:
        return None
    return int(match.group(1))


def _apply_network_limits(ip_prefix: str, bridge_name: str) -> None:
    source_ip = _build_container_ip(ip_prefix)
    if source_ip:
        _run_command(
            [
                "iptables",
                "-A",
                "OUTPUT",
                "-s",
                source_ip,
                "-m",
                "limit",
                "--limit",
                CONTAINER["rate"],
                "-j",
                "ACCEPT",
            ]
        )

    if not _wait_for_bridge(bridge_name):
        logger.warning(
            "Bridge %s not ready after %.0fs; skipping tc limits",
            bridge_name,
            _BRIDGE_WAIT_TIMEOUT_SEC,
        )
        return

    result = subprocess.run(
        [
            "tc",
            "qdisc",
            "add",
            "dev",
            bridge_name,
            "root",
            "tbf",
            "rate",
            CONTAINER["rate"],
            "burst",
            CONTAINER["burst"],
            "latency",
            CONTAINER["latency"],
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        logger.warning(
            "tc limits on %s failed (exit %s): %s",
            bridge_name,
            result.returncode,
            stderr or "unknown error",
        )


def _reconcile_running_container(name: str, password: str) -> None:
    path = _volume_path(name)
    env = _load_env(str(path / ".env"))
    ip_prefix = env.get("IP_PREFIX")
    bridge_name = env.get("BRIDGE_NAME", f"br-{name}")
    if ip_prefix:
        _apply_network_limits(ip_prefix, bridge_name)
    ip_suffix = _ip_suffix_from_prefix(ip_prefix) if ip_prefix else None
    if ip_suffix is None:
        logger.warning(
            "Container %s is running but IP_PREFIX is missing; skipping caddy reconcile",
            name,
        )
        return
    create_vhost(name, SERVER, ip_suffix, password)


def _start_existing_compose(name: str, password: str) -> None:
    path = _volume_path(name)
    compose = _compose_client(path)
    _retry(
        lambda: compose.compose.up(detach=True),
        action=f"compose up for existing {name}",
    )
    env = _load_env(str(path / ".env"))
    ip_prefix = env.get("IP_PREFIX", "")
    bridge_name = env.get("BRIDGE_NAME", f"br-{name}")
    if ip_prefix:
        _apply_network_limits(ip_prefix, bridge_name)
    ip_suffix = _ip_suffix_from_prefix(ip_prefix) if ip_prefix else None
    if ip_suffix is not None:
        create_vhost(name, SERVER, ip_suffix, password)


def _clear_network_limits(ip_prefix: Optional[str], bridge_name: Optional[str]) -> None:
    source_ip = _build_container_ip(ip_prefix)
    if source_ip:
        _run_command(
            [
                "iptables",
                "-D",
                "OUTPUT",
                "-s",
                source_ip,
                "-m",
                "limit",
                "--limit",
                CONTAINER["rate"],
                "-j",
                "ACCEPT",
            ]
        )
    if bridge_name:
        _run_command(["tc", "qdisc", "del", "dev", bridge_name, "root"])


def check_ip(ip_prefix: int) -> bool:
    docker_client = DockerClient()
    networks = docker_client.network.list()
    target_subnet = f"192.168.{ip_prefix}.0/24"

    for network in networks:
        if not network.ipam.config:
            continue
        try:
            subnet = network.ipam.config[0]["Subnet"]
        except (IndexError, KeyError, TypeError):
            continue
        if subnet == target_subnet:
            return False
    return True


def _allocate_ip_suffix() -> int:
    _IP_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_IP_LOCK_PATH, "w") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            for ip in range(1, 256):
                if check_ip(ip):
                    return ip
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    raise RuntimeError("No available IP prefix found for container network.")


def _compose_client(path: Path) -> DockerClient:
    compose_file = path / "docker-compose.yml"
    env_file = path / ".env"
    kwargs = {"compose_files": [str(compose_file)]}
    if env_file.is_file():
        kwargs["compose_env_file"] = str(env_file)
    return DockerClient(**kwargs)


def _retry(
    func: Callable[[], T],
    *,
    attempts: int = _COMPOSE_RETRY_ATTEMPTS,
    delay: float = _COMPOSE_RETRY_DELAY_SEC,
    action: str,
) -> T:
    last_error: Optional[Exception] = None
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except Exception as exc:
            last_error = exc
            logger.warning(
                "%s failed (attempt %s/%s): %s",
                action,
                attempt,
                attempts,
                exc,
            )
            if attempt < attempts:
                time.sleep(delay * attempt)
    assert last_error is not None
    raise RuntimeError(f"{action} failed after {attempts} attempts") from last_error


def _get_container(name: str):
    try:
        return client.containers.get(name)
    except NotFound:
        return None


def _remove_docker_container(name: str, warnings: List[str]) -> None:
    try:
        container = client.containers.get(name)
    except NotFound:
        return
    except Exception as exc:
        warnings.append(f"container lookup: {exc}")
        return

    for method_name in ("kill", "stop"):
        try:
            getattr(container, method_name)()
            break
        except Exception:
            continue

    try:
        container.remove(force=True)
    except Exception as exc:
        warnings.append(f"container remove: {exc}")


def _remove_docker_network(
    name: str,
    bridge_name: Optional[str],
    warnings: List[str],
) -> None:
    network_name = _compose_network_name(name)
    try:
        client.networks.get(network_name).remove()
        return
    except NotFound:
        pass
    except Exception as exc:
        warnings.append(f"network {network_name}: {exc}")

    if not bridge_name:
        return

    for network in client.networks.list():
        options = (network.attrs or {}).get("Options") or {}
        if options.get("com.docker.network.bridge.name") == bridge_name:
            try:
                network.remove()
                return
            except Exception as exc:
                warnings.append(f"network by bridge {bridge_name}: {exc}")


def _force_cleanup(name: str) -> List[str]:
    warnings: List[str] = []
    path = _volume_path(name)
    env_path = path / ".env"
    env = _load_env(str(env_path)) if env_path.is_file() else {}
    ip_prefix = env.get("IP_PREFIX")
    bridge_name = env.get("BRIDGE_NAME", f"br-{name}")

    try:
        remove_caddy_user(name, SERVER)
    except Exception as exc:
        warnings.append(f"caddy: {exc}")

    compose_file = path / "docker-compose.yml"
    if compose_file.is_file():
        compose = _compose_client(path)
        for action, kwargs in (
            ("compose down", {"remove_orphans": True, "volumes": True}),
            ("compose rm", {"volumes": True}),
        ):
            try:
                if action == "compose down":
                    compose.compose.down(**kwargs)
                else:
                    compose.compose.rm(**kwargs)
            except Exception as exc:
                warnings.append(f"{action}: {exc}")

    _remove_docker_container(name, warnings)
    _remove_docker_network(name, bridge_name, warnings)
    _clear_network_limits(ip_prefix, bridge_name)

    if path.exists():
        try:
            shutil.rmtree(path)
        except Exception as exc:
            warnings.append(f"volume rmtree: {exc}")

    return warnings


def create(
    port,
    name,
    userbot="vsecoder/hikka:latest",
    password="$2b$12$nr213f0pJnQuCAdLnRTMeODqoniH1YH.Aqp6x2a9Wam01FtLdCB7O",
):
    _validate_container_name(name)
    port = _parse_port(port)
    path = _volume_path(name)

    with _docker_lock:
        existing = _get_container(name)
        volume_ready = path.is_dir() and (path / "docker-compose.yml").is_file()

        if existing is not None and volume_ready:
            if existing.status == "running":
                logger.info("Container %s already running; reconciling", name)
                _reconcile_running_container(name, password)
                return
            logger.info("Container %s exists but stopped; starting compose", name)
            _start_existing_compose(name, password)
            return

        if existing is not None:
            raise ValueError(
                f"Container '{name}' already exists without a volume; remove it first"
            )

        if path.exists():
            logger.warning(
                "Orphan volume for %s found before create; cleaning up", name
            )
            orphan_warnings = _force_cleanup(name)
            for warning in orphan_warnings:
                logger.warning("Orphan cleanup for %s: %s", name, warning)
            if path.exists():
                raise RuntimeError(
                    f"Could not remove existing volume directory for '{name}'"
                )

        path.mkdir(parents=True)
        (path / "data").mkdir(parents=True)
        shutil.copy("./docker-compose.yml", path)

        ip_suffix = _allocate_ip_suffix()
        ip_prefix = f"192.168.{ip_suffix}"
        bridge_name = f"br-{name}"

        env = f"""IMAGE={userbot}
CONTAINER_NAME={name}
EXTERNAL_PORT={port}
CPU_LIMIT={CONTAINER['cpu']}
MEMORY_LIMIT={CONTAINER['memory']}
IP_PREFIX={ip_prefix}
BRIDGE_NAME={bridge_name}
"""
        (path / ".env").write_text(env)

        compose = _compose_client(path)
        try:
            _retry(
                lambda: compose.compose.build(),
                action=f"compose build for {name}",
            )
            _retry(
                lambda: compose.compose.up(detach=True),
                action=f"compose up for {name}",
            )
        except Exception as exc:
            logger.exception("Compose failed for %s; rolling back", name)
            rollback_warnings = _force_cleanup(name)
            for warning in rollback_warnings:
                logger.warning("Rollback for %s: %s", name, warning)
            if path.exists():
                raise RuntimeError(
                    f"Create failed for '{name}' and volume directory could not be removed"
                ) from exc
            raise

        _apply_network_limits(ip_prefix, bridge_name)
        try:
            create_vhost(name, SERVER, ip_suffix, password)
        except Exception as exc:
            logger.warning(
                "Caddy vhost setup failed for %s (container is running): %s",
                name,
                exc,
            )


def stop(name):
    _validate_container_name(name)
    with _docker_lock:
        client.containers.get(name).stop()


def kill(name):
    _validate_container_name(name)
    with _docker_lock:
        client.containers.get(name).kill()


def start(name):
    _validate_container_name(name)
    with _docker_lock:
        client.containers.get(name).start()


def restart(name):
    _validate_container_name(name)
    with _docker_lock:
        client.containers.get(name).restart()


def json_serializable(obj):
    return [{"name": i.name, "status": i.status} for i in obj]


def containers_list():
    with _docker_lock:
        containers = client.containers.list(all=True)
        return json_serializable(containers)


def get_number_of_containers():
    arr = containers_list()
    return len([i for i in arr if i["status"] == "running"])


def logs(name):
    _validate_container_name(name)
    with _docker_lock:
        log = client.containers.get(name).logs(tail="all", follow=False).decode("utf-8")
    return log


def execute(name, command):
    _validate_container_name(name)
    if not isinstance(command, str) or not command.strip():
        raise ValueError("Command is required")
    if "\x00" in command:
        raise ValueError("Invalid command")
    with _docker_lock:
        container = client.containers.get(name)
        exec_result = container.exec_run(cmd=["bash", "-c", command])
    output = exec_result.output
    if isinstance(output, bytes):
        output = output.decode("utf-8", errors="replace")
    elif output is None:
        output = ""
    return {"exit_code": exec_result.exit_code, "output": output}


def _empty_docker_stats(memory_limit: int = 0) -> Dict[str, Any]:
    return {
        "cpu_stats": {
            "cpu_usage": {"total_usage": 0},
            "system_cpu_usage": 0,
            "online_cpus": 1,
        },
        "precpu_stats": {
            "cpu_usage": {"total_usage": 0},
            "system_cpu_usage": 0,
        },
        "memory_stats": {
            "usage": 0,
            "limit": memory_limit,
            "max_usage": 0,
        },
    }


def _memory_limit_from_container(container) -> int:
    try:
        limit = (container.attrs or {}).get("HostConfig", {}).get("Memory") or 0
        return max(int(limit), 0)
    except (TypeError, ValueError):
        return 0


def _apply_zero_stats(snapshot: Dict[str, Any], memory_limit: int = 0) -> None:
    snapshot["stats"] = _empty_docker_stats(memory_limit)


def _read_container_stats(container) -> Optional[Dict[str, Any]]:
    try:
        container.reload()
    except APIError as exc:
        logger.warning("container.reload before stats failed: %s", exc)

    last_error: Optional[Exception] = None
    for attempt in range(1, _STATS_RETRY_ATTEMPTS + 1):
        try:
            return container.stats(stream=False)
        except APIError as exc:
            last_error = exc
            logger.warning(
                "container.stats failed (attempt %s/%s): %s",
                attempt,
                _STATS_RETRY_ATTEMPTS,
                exc,
            )
            if attempt < _STATS_RETRY_ATTEMPTS:
                time.sleep(_STATS_RETRY_DELAY_SEC * attempt)

    try:
        return client.api.get(
            f"/containers/{container.id}/stats",
            params={"stream": "false"},
        )
    except Exception as exc:
        last_error = exc
        logger.warning("container stats API fallback failed: %s", exc)

    if last_error is not None:
        logger.warning("Giving up on container.stats: %s", last_error)
    return None


def get_container_snapshot(name: str) -> Dict[str, Any]:
    _validate_container_name(name)
    path = _volume_path(name)
    snapshot: Dict[str, Any] = {
        "state": "not_found",
        "docker_status": None,
        "stats": None,
        "inspect": None,
    }

    with _docker_lock:
        try:
            container = client.containers.get(name)
        except NotFound:
            if path.exists():
                snapshot["state"] = "provisioning"
                snapshot["docker_status"] = "provisioning"
            return snapshot
        except APIError as exc:
            logger.warning("Docker lookup failed for %s: %s", name, exc)
            if path.exists():
                snapshot["state"] = "provisioning"
                snapshot["docker_status"] = "provisioning"
            return snapshot

        snapshot["docker_status"] = container.status
        mem_limit = _memory_limit_from_container(container)

        try:
            snapshot["inspect"] = container.attrs
        except APIError as exc:
            logger.warning("container.attrs failed for %s: %s", name, exc)

        if container.status != "running":
            snapshot["state"] = "stopped"
            _apply_zero_stats(snapshot, mem_limit)
            return snapshot

        snapshot["state"] = "running"
        stats_data = _read_container_stats(container)
        if stats_data is None:
            _apply_zero_stats(snapshot, mem_limit)
        else:
            snapshot["stats"] = stats_data
        return snapshot


def stats(name):
    return get_container_snapshot(name)["stats"]


def inspect(name):
    return get_container_snapshot(name)["inspect"]


def remove(name) -> Dict[str, object]:
    _validate_container_name(name)
    with _docker_lock:
        warnings = _force_cleanup(name)
        path = _volume_path(name)
        if path.exists():
            raise RuntimeError(
                f"Failed to remove volume directory for '{name}'"
                + (f"; warnings: {'; '.join(warnings)}" if warnings else "")
            )
        if warnings:
            logger.warning("Remove %s completed with warnings: %s", name, warnings)
        return {"removed": True, "warnings": warnings}


def recreate(name, force_recreate=False):
    _validate_container_name(name)
    path = _volume_path(name)
    if not path.is_dir():
        raise ValueError(f"Volume for container '{name}' does not exist")
    with _docker_lock:
        docker = _compose_client(path)
        docker.compose.create(force_recreate=force_recreate)
        docker.compose.start()
