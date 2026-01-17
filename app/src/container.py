import os
import re
import shutil
import subprocess
from typing import Dict, List, Optional
import docker

from python_on_whales import DockerClient
from app.config import CONTAINER, SERVER
from app.src.caddy import create_vhost, remove_caddy_user


client = docker.from_env()
_VALID_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,62}$")
_MAX_BRIDGE_NAME_LEN = 15


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


def _apply_network_limits(ip_prefix: str, bridge_name: str) -> None:
    source_ip = _build_container_ip(ip_prefix)
    if not source_ip:
        return
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
    _run_command(
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
        ]
    )


def _clear_network_limits(
    ip_prefix: Optional[str], bridge_name: Optional[str]
) -> None:
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

    for network in networks:
        if not network.ipam.config:
            continue
        if network.ipam.config[0]['Subnet'] == f'192.168.{ip_prefix}.0/24':
            return False
    return True


def create(port, name, userbot="vsecoder/hikka:latest", password="$2b$12$nr213f0pJnQuCAdLnRTMeODqoniH1YH.Aqp6x2a9Wam01FtLdCB7O"):
    _validate_container_name(name)
    port = _parse_port(port)
    path = os.path.join(os.getcwd(), "volumes", name)
    os.mkdir(path)
    os.mkdir(os.path.join(path, "data"))
    shutil.copy("./docker-compose.yml", path)
    ip_prefix = None

    for ip in range(1, 256):
        if check_ip(ip):
            ip_prefix = ip
            break

    if ip_prefix is None:
        raise RuntimeError("No available IP prefix found for container network.")

    ip_prefix = f"192.168.{ip_prefix}"
    bridge_name = f"br-{name}"

    env = f"""
IMAGE={userbot}
CONTAINER_NAME={name}
EXTERNAL_PORT={port}
CPU_LIMIT={CONTAINER['cpu']}
MEMORY_LIMIT={CONTAINER['memory']}
IP_PREFIX={ip_prefix}
TMPFS_SIZE={CONTAINER['size']}
BRIDGE_NAME={bridge_name}
"""

    with open(os.path.join(path, ".env"), "w") as f:
        f.write(env)

    docker = DockerClient(
        compose_files=[os.path.join(path, "docker-compose.yml")],
        compose_env_file=os.path.join(path, ".env"),
    )

    docker.compose.build()
    docker.compose.up(detach=True)

    _apply_network_limits(ip_prefix, bridge_name)

    create_vhost(name, SERVER, ip_prefix, password)


def stop(name):
    _validate_container_name(name)
    client.containers.get(name).stop()
    return


def kill(name):
    _validate_container_name(name)
    client.containers.get(name).kill()
    return


def start(name):
    _validate_container_name(name)
    client.containers.get(name).start()
    return


def restart(name):
    _validate_container_name(name)
    client.containers.get(name).restart()
    return


def json_serializable(obj):
    return [{"name": i.name, "status": i.status} for i in obj]


def containers_list():
    containers = client.containers.list(all=True)
    return json_serializable(containers)


def get_number_of_containers():
    arr = containers_list()
    return len([i for i in arr if i["status"] == "running"])


def logs(name):
    _validate_container_name(name)
    log = client.containers.get(name).logs(tail="all", follow=False).decode("utf-8")
    return log


def execute(name, command):
    _validate_container_name(name)
    exec = client.containers.get(name).exec_run(f"bash -c '{command}'")
    return {"exit_code": exec[0], "output": exec[1].decode("utf-8")}


def stats(name):
    _validate_container_name(name)
    container = client.containers.get(name)
    if container.status != "running":
        return None
    return container.stats(stream=False)


def inspect(name):
    _validate_container_name(name)
    try:
        container = client.containers.get(name)
        if container.status != "running":
            return None
        return container.inspect_container()
    except Exception:
        return


def remove(name):
    try:
        _validate_container_name(name)
        remove_caddy_user(name, SERVER)
        path = os.path.join(os.getcwd(), "volumes", name)
        env = _load_env(os.path.join(path, ".env"))
        ip_prefix = env.get("IP_PREFIX")
        bridge_name = env.get("BRIDGE_NAME", f"br-{name}")
        docker = DockerClient(
            compose_files=[os.path.join(path, "docker-compose.yml")],
        )
        try:
            kill(name)
        except Exception:
            pass
        docker.compose.rm(volumes=True)
        _clear_network_limits(ip_prefix, bridge_name)
        client.networks.get(f"{name}_hikka_net").remove()
        shutil.rmtree(path)
        return
    except:
        return


def recreate(name, force_recreate=False):
    _validate_container_name(name)
    path = os.path.join(os.getcwd(), "volumes", name)
    docker = DockerClient(
        compose_files=[os.path.join(path, "docker-compose.yml")],
        compose_env_file=os.path.join(path, ".env"),
    )

    docker.compose.create(force_recreate=force_recreate)
    docker.compose.start()
