import os
import random
import shutil
import docker
from python_on_whales import DockerClient


client = docker.from_env()

def create(port, name):
    path = os.path.join(os.getcwd(), "volumes", name)
    os.mkdir(path)
    os.mkdir(os.path.join(path, "data"))
    shutil.copy("./docker-compose.yml", path)
    ip_prefix = random.randint(100, 255)
    env = f"""
CONTAINER_NAME={name}
EXTERNAL_PORT={port}
CPU_LIMIT=1.0
MEMORY_LIMIT=512M
IP_PREFIX=192.168.{ip_prefix}
TMPFS_SIZE=3G
BRIDGE_NAME=br-{name}
"""
    with open(os.path.join(path, ".env"), "w") as f:
        f.write(env)

    docker = DockerClient(
        compose_files=[os.path.join(path, "docker-compose.yml")],
        compose_env_file=os.path.join(path, ".env"),
    )

    docker.compose.build()
    docker.compose.up(detach=True)


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
    except:
        pass

    docker.compose.rm(volumes=True)
    shutil.rmtree(path)
    return
