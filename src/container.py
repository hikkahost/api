import docker
from config import CONTAINER


client = docker.from_env()

docker_waiting = []

def create(port, name):
    client.containers.run(
        CONTAINER['image'],
        cpu_period=CONTAINER['cpu_period'],
        cpu_quota=CONTAINER['cpu_quota'],
        mem_limit=CONTAINER['mem_limit'],
        name=name,
        ports={8080: port},
        detach=True,
        tty=True,
    )


def stop(name):
    if name in docker_waiting:
        return {"message": "waiting for payment"}
    client.containers.get(name).stop()


def start(name):
    if name in docker_waiting:
        return {"message": "waiting for payment"}
    client.containers.get(name).start()


def restart(name):
    if name in docker_waiting:
        return {"message": "waiting for payment"}
    client.containers.get(name).restart()


def json_serializable(obj):
    return [{"name": i.name, "status": i.status} for i in obj]


def containers_list():
    containers = client.containers.list(all=True)
    return json_serializable(containers)


def get_number_of_containers():
    arr = containers_list()
    return len([i for i in arr if i['status'] == 'running'])


def logs(name):
    log = client.containers.get(name).logs(tail=0, follow=True).decode("utf-8")
    return log

def wait(name):
    docker_waiting.append(name)
    stop(name)
    return {"message": "waiting for payment"}

def payment(name):
    docker_waiting.remove(name)
    start(name)
    return {"message": "payment received"}
