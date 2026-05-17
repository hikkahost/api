import asyncio
import logging
from typing import Tuple

logger = logging.getLogger("setup_web")


async def _run_docker(*args: str) -> Tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        "docker",
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return (
        proc.returncode or 0,
        stdout.decode(errors="replace"),
        stderr.decode(errors="replace"),
    )


async def container_is_running(name: str) -> bool:
    code, stdout, _ = await _run_docker(
        "inspect",
        "-f",
        "{{.State.Running}}",
        name,
    )
    if code != 0:
        return False
    return stdout.strip().lower() == "true"


async def stop_container(name: str) -> None:
    code, _, stderr = await _run_docker("stop", name)
    if code != 0:
        raise RuntimeError(stderr.strip() or f"docker stop {name} failed")


async def start_container(name: str) -> None:
    code, _, stderr = await _run_docker("start", name)
    if code != 0:
        raise RuntimeError(stderr.strip() or f"docker start {name} failed")


async def restart_container(name: str) -> None:
    code, _, stderr = await _run_docker("restart", name)
    if code != 0:
        raise RuntimeError(stderr.strip() or f"docker restart {name} failed")
