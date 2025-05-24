import docker

from pathlib import Path
from app.config import SERVER
from app.src.caddy import create_vhost


client = docker.from_env()


def containers_list():
    containers = client.containers.list(all=True)
    return containers


for container in containers_list():
    env_path = Path(f"volumes/{container.name}/.env")
    if not env_path.exists():
        print(f"Environment file for container {container.name} does not exist.")
        continue

    with open(env_path, "r") as f:
        env_vars = f.read().strip().split("\n")
    env_dict = {}
    for line in env_vars:
        key, value = line.split("=", 1)
        env_dict[key.strip()] = value.strip()

    if not container.name.isdigit():
        print(f"Container name {container.name} is not a digit, skipping vhost creation.")
        continue

    create_vhost(
        username=container.name,
        server=SERVER,
        ip_prefix=int(env_dict["IP_PREFIX"].split(".")[2]),
        hashed_password="$2b$12$nr213f0pJnQuCAdLnRTMeODqoniH1YH.Aqp6x2a9Wam01FtLdCB7O",
    )
