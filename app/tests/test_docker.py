import asyncio
import pytest

from app.utils.task_queue import TaskStatus, queue_service


@pytest.fixture(autouse=True)
def mock_container_ops(monkeypatch):
    monkeypatch.setattr("app.src.container.create", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.src.container.start", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.src.container.stop", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.src.container.restart", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.src.container.recreate", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.src.container.remove", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        "app.src.container.execute",
        lambda *args, **kwargs: {"exit_code": 0, "output": "ok"},
    )
    monkeypatch.setattr("app.src.container.logs", lambda *args, **kwargs: "log")
    monkeypatch.setattr("app.src.container.stats", lambda *args, **kwargs: {"cpu": 1})
    monkeypatch.setattr("app.src.container.inspect", lambda *args, **kwargs: {"id": "x"})
    monkeypatch.setattr(
        "app.src.container.containers_list", lambda *args, **kwargs: [{"name": "test"}]
    )
    monkeypatch.setattr(
        "app.src.container.get_number_of_containers", lambda *args, **kwargs: 1
    )
    monkeypatch.setattr("app.src.caddy.update_password", lambda *args, **kwargs: True)
    queue_service._tasks.clear()


async def _wait_for_task(app, task_id):
    for _ in range(50):
        request, response = await app.asgi_client.get(
            f"/api/host/tasks/{task_id}",
            headers={"Authorization": "secret"},
        )
        if response.status == 200:
            status = response.json.get("status")
            if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                return response.json
        await asyncio.sleep(0)
    raise AssertionError("Task did not complete in time")


@pytest.mark.anyio
async def test_ping(app):
    request, response = await app.asgi_client.get(
        "/api/host/ping", headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert response.json == {"message": "pong"}


@pytest.mark.anyio
async def test_create_container_hikka(app):
    params = {"port": "8080", "name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/create", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 202
    task = await _wait_for_task(app, response.json["task_id"])
    assert task["status"] == TaskStatus.COMPLETED
    assert task["result"] == {"message": "created"}


@pytest.mark.anyio
async def test_create_container_heroku(app):
    params = {"port": "8081", "name": "test2", "userbot": "vsecoder/hikka:fork-codrago"}
    request, response = await app.asgi_client.get(
        "/api/host/create", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 202
    task = await _wait_for_task(app, response.json["task_id"])
    assert task["status"] == TaskStatus.COMPLETED


@pytest.mark.anyio
async def test_remove_container2(app):
    params = {"name": "test2"}
    request, response = await app.asgi_client.get(
        "/api/host/remove", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 202
    task = await _wait_for_task(app, response.json["task_id"])
    assert task["status"] == TaskStatus.COMPLETED
    assert "remove" in task["result"]


@pytest.mark.anyio
async def test_start_container(app):
    params = {"type": "start", "name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/action", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 202
    task = await _wait_for_task(app, response.json["task_id"])
    assert task["status"] == TaskStatus.COMPLETED
    assert task["result"] == {"message": "action completed"}


@pytest.mark.anyio
async def test_recreate_container(app):
    params = {"type": "recreate", "name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/action", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 202
    task = await _wait_for_task(app, response.json["task_id"])
    assert task["status"] == TaskStatus.COMPLETED


@pytest.mark.anyio
async def test_list_containers(app):
    request, response = await app.asgi_client.get(
        "/api/host/list", headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert "list" in response.json
    assert isinstance(response.json["list"], list)


@pytest.mark.anyio
async def test_get_container_number(app):
    request, response = await app.asgi_client.get(
        "/api/host/number", headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert "number" in response.json
    assert isinstance(response.json["number"], int)


@pytest.mark.anyio
async def test_get_logs(app):
    params = {"name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/logs", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert "logs" in response.json


@pytest.mark.anyio
async def test_exec_command(app):
    params = {"name": "test", "command": "echo 'hello'"}
    request, response = await app.asgi_client.get(
        "/api/host/exec", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 202
    task = await _wait_for_task(app, response.json["task_id"])
    assert task["status"] == TaskStatus.COMPLETED
    assert "exec" in task["result"]


@pytest.mark.anyio
async def test_container_stats(app):
    params = {"name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/stats", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert "stats" in response.json
    assert "inspect" in response.json


@pytest.mark.anyio
async def test_container_status(app):
    params = {"name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/status", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert "status" in response.json
    assert response.json["status"] in ["running", "stopped"]


@pytest.mark.anyio
async def test_server_resources(app):
    request, response = await app.asgi_client.get(
        "/api/host/resources", headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert "resources" in response.json


@pytest.mark.anyio
async def test_restart_container(app):
    params = {"type": "restart", "name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/action", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 202
    task = await _wait_for_task(app, response.json["task_id"])
    assert task["status"] == TaskStatus.COMPLETED


@pytest.mark.anyio
async def test_remove_container(app):
    params = {"name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/remove", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 202
    task = await _wait_for_task(app, response.json["task_id"])
    assert task["status"] == TaskStatus.COMPLETED
    assert "remove" in task["result"]


@pytest.mark.anyio
async def test_update_password(app):
    params = {"name": "test", "password": "hash"}
    request, response = await app.asgi_client.get(
        "/api/host/update-password", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 202
    task = await _wait_for_task(app, response.json["task_id"])
    assert task["status"] == TaskStatus.COMPLETED
    assert "update" in task["result"]


@pytest.mark.anyio
async def test_task_not_found(app):
    request, response = await app.asgi_client.get(
        "/api/host/tasks/unknown", headers={"Authorization": "secret"}
    )
    assert response.status == 404
