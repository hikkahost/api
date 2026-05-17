import asyncio
import time

import pytest

from app.utils.task_queue import TaskStatus, queue_service

pytestmark = pytest.mark.asyncio(loop_scope="function")


@pytest.fixture(autouse=True)
def mock_container_ops(monkeypatch):
    queue_service.reset_for_tests()
    monkeypatch.setattr("app.utils.task_queue.create", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.utils.task_queue.start", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.utils.task_queue.stop", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.utils.task_queue.restart", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.utils.task_queue.recreate", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.utils.task_queue.remove", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        "app.utils.task_queue.execute",
        lambda *args, **kwargs: {"exit_code": 0, "output": "ok"},
    )
    monkeypatch.setattr("app.src.container.logs", lambda *args, **kwargs: "log")
    monkeypatch.setattr(
        "app.src.container.get_container_snapshot",
        lambda *args, **kwargs: {
            "state": "running",
            "docker_status": "running",
            "stats": {"cpu": 1},
            "inspect": {"id": "x"},
        },
    )
    monkeypatch.setattr(
        "app.src.container.containers_list", lambda *args, **kwargs: [{"name": "test"}]
    )
    monkeypatch.setattr(
        "app.src.container.get_number_of_containers", lambda *args, **kwargs: 1
    )
    monkeypatch.setattr(
        "app.utils.task_queue.update_password", lambda *args, **kwargs: True
    )


@pytest.fixture(autouse=True)
async def _shutdown_queue_worker():
    yield
    await queue_service.shutdown_worker()


async def _wait_for_task(app, task_id, timeout=10.0):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        request, response = await app.asgi_client.get(
            f"/api/host/tasks/{task_id}",
            headers={"Authorization": "secret"},
        )
        if response.status == 200:
            last = response.json
            status = last.get("status")
            if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                return last
        await asyncio.sleep(0.05)
    raise AssertionError(f"Task did not complete in time (last={last})")


async def test_ping(app):
    request, response = await app.asgi_client.get(
        "/api/host/ping", headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert response.json == {"message": "pong"}


async def test_create_container_hikka(app):
    params = {"port": "8080", "name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/create", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 202
    task = await _wait_for_task(app, response.json["task_id"])
    assert task["status"] == TaskStatus.COMPLETED
    assert task["result"] == {"message": "created"}


async def test_create_container_heroku(app):
    params = {"port": "8081", "name": "test2", "userbot": "fajox/hikkahost:heroku"}
    request, response = await app.asgi_client.get(
        "/api/host/create", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 202, response.json
    task = await _wait_for_task(app, response.json["task_id"])
    assert task["status"] == TaskStatus.COMPLETED


async def test_remove_container2(app):
    params = {"name": "test2"}
    request, response = await app.asgi_client.get(
        "/api/host/remove", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 202
    task = await _wait_for_task(app, response.json["task_id"])
    assert task["status"] == TaskStatus.COMPLETED
    assert "remove" in task["result"]


async def test_start_container(app):
    params = {"type": "start", "name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/action", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 202
    task = await _wait_for_task(app, response.json["task_id"])
    assert task["status"] == TaskStatus.COMPLETED
    assert task["result"] == {"message": "action completed"}


async def test_recreate_container(app):
    params = {"type": "recreate", "name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/action", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 202
    task = await _wait_for_task(app, response.json["task_id"])
    assert task["status"] == TaskStatus.COMPLETED


async def test_list_containers(app):
    request, response = await app.asgi_client.get(
        "/api/host/list", headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert "list" in response.json
    assert isinstance(response.json["list"], list)


async def test_get_container_number(app):
    request, response = await app.asgi_client.get(
        "/api/host/number", headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert "number" in response.json
    assert isinstance(response.json["number"], int)


async def test_get_logs(app):
    params = {"name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/logs", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert "logs" in response.json


async def test_exec_command(app):
    params = {"name": "test", "command": "echo hello"}
    request, response = await app.asgi_client.get(
        "/api/host/exec", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 202
    task = await _wait_for_task(app, response.json["task_id"])
    assert task["status"] == TaskStatus.COMPLETED
    assert "exec" in task["result"]


async def test_container_stats(app):
    params = {"name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/stats", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert response.json["state"] == "running"
    assert "stats" in response.json
    assert "inspect" in response.json


async def test_container_status(app):
    params = {"name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/status", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert "status" in response.json
    assert response.json["status"] in [
        "running",
        "stopped",
        "provisioning",
        "not_found",
    ]


async def test_server_resources(app):
    request, response = await app.asgi_client.get(
        "/api/host/resources", headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert "resources" in response.json


async def test_restart_container(app):
    params = {"type": "restart", "name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/action", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 202
    task = await _wait_for_task(app, response.json["task_id"])
    assert task["status"] == TaskStatus.COMPLETED


async def test_remove_container(app):
    params = {"name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/remove", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 202
    task = await _wait_for_task(app, response.json["task_id"])
    assert task["status"] == TaskStatus.COMPLETED
    assert "remove" in task["result"]


async def test_update_password(app):
    from app.handlers.servers.api import DEFAULT_PASSWORD

    params = {"name": "test", "password": DEFAULT_PASSWORD}
    request, response = await app.asgi_client.get(
        "/api/host/update-password", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 202
    task = await _wait_for_task(app, response.json["task_id"])
    assert task["status"] == TaskStatus.COMPLETED
    assert "update" in task["result"]


async def test_update_password_rejects_invalid_hash(app):
    params = {"name": "test", "password": "hash"}
    request, response = await app.asgi_client.get(
        "/api/host/update-password", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 400
    assert response.json["error"] == "Invalid password hash"


async def test_task_not_found(app):
    request, response = await app.asgi_client.get(
        "/api/host/tasks/unknown", headers={"Authorization": "secret"}
    )
    assert response.status == 404
