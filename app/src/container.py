import os
import shutil
import docker
import socket

from python_on_whales import DockerClient
from app.config import CONTAINER
from app.src.lookup import find_free_ip


client = docker.from_env()


def check_ip(ip_prefix: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10.0)
    result = sock.connect_ex((f"192.168.{ip_prefix}.101", 8080))
    sock.close()
    return result == 0


def create(port, name):
    path = os.path.join(os.getcwd(), "volumes", name)
    os.mkdir(path)
    os.mkdir(os.path.join(path, "data"))
    shutil.copy("./docker-compose.yml", path)
    ip_prefix = find_free_ip(range(0, 256))

    env = f"""
CONTAINER_NAME={name}
EXTERNAL_PORT={port}
CPU_LIMIT={CONTAINER['cpu']}
MEMORY_LIMIT={CONTAINER['memory']}
IP_PREFIX=192.168.{ip_prefix}
TMPFS_SIZE={CONTAINER['size']}
BRIDGE_NAME=br-{name}
"""

    with open(os.path.join(path, ".env"), "w") as f:
        f.write(env)

    docker = DockerClient(
        compose_files=[os.path.join(path, "docker-compose.yml")],
        compose_env_files=[os.path.join(path, ".env")],
    )

    docker.compose.build()
    docker.compose.up(detach=True)

    # first level, iptables
    os.system(
        f"iptables -A OUTPUT -s 192.168.{ip_prefix}.101 -m limit --limit {CONTAINER['rate']} -j ACCEPT"
    )

    # second level, tc
    os.system(
        (
            f"tc qdisc add dev br-{name} root tbf rate {CONTAINER['rate']} "
            f"burst {CONTAINER['burst']} latency {CONTAINER['latency']}"
        )
    )


def stop(name):
    client.containers.get(name).stop()
    return


def start(name):
    client.containers.get(name).start()
    return


def restart(name):
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
    log = client.containers.get(name).logs(tail="all", follow=False).decode("utf-8")
    return log


def execute(name, command):
    exec = client.containers.get(name).exec_run(command)
    return {"exit_code": exec[0], "output": exec[1].decode("utf-8")}


def stats(name):
    container = client.containers.get(name)
    if container.status != "running":
        return None
    return container.stats(stream=False)


def inspect(name):
    try:
        container = client.containers.get(name)
        if container.status != "running":
            return None
        return container.inspect_container()
    except Exception:
        return


def remove(name):
    path = os.path.join(os.getcwd(), "volumes", name)
    docker = DockerClient(
        compose_files=[os.path.join(path, "docker-compose.yml")],
    )
    try:
        stop(name)
    except Exception:
        pass
    docker.compose.rm(volumes=True)
    #os.system(f"docker network rm {name}_hikka_net")
    client.networks.get(f"{name}_hikka_net").remove()
    shutil.rmtree(path)
    return
