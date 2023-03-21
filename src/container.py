
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
    res = []
    for i in obj:
        res.append({
            "name": i.name,
            "status": i.status,
        })

    return res

def containers_list():
    containers = client.containers.list(all=True)
    return json_serializable(containers)

def get_number_of_containers():
    num = 0
    
    arr = containers_list()
    for i in arr:
        if i['status'] == 'running':
            num += 1

    return num

def logs(name):
    log = client.containers.get(name).logs(tail=0, follow=True).decode("utf-8")
    print(log)
    return log