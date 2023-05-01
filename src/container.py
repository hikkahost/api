import docker
from config import CONTAINER


client = docker.from_env()

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
    client.containers.get(name).stop()


def start(name):
    client.containers.get(name).start()


def restart(name):
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
