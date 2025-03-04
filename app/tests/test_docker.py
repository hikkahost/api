import pytest


@pytest.mark.anyio
async def test_ping(app):
    """Тест пинга сервера."""
    request, response = await app.asgi_client.get(
        "/api/host/ping", headers={"Authorization": "secret"}
    )
    print(response.json)
    assert response.status == 200
    assert response.json == {"message": "pong"}


@pytest.mark.anyio
async def test_create_container_hikka(app):
    """Тест создания контейнера."""
    params = {"port": "8080", "name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/create", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert response.json == {"message": "created"}


@pytest.mark.anyio
async def test_create_container_heroku(app):
    """Тест создания контейнера 2."""
    params = {"port": "8081", "name": "test2", "userbot": "heroku"}
    request, response = await app.asgi_client.get(
        "/api/host/create", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert response.json == {"message": "created"}


@pytest.mark.anyio
async def test_remove_container2(app):
    """Тест удаления контейнера 2."""
    params = {"name": "test2"}
    request, response = await app.asgi_client.get(
        "/api/host/remove", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert "remove" in response.json


@pytest.mark.anyio
async def test_start_container(app):
    """Тест запуска контейнера."""
    params = {"type": "start", "name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/action", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert response.json == {"message": "action completed"}


@pytest.mark.anyio
async def test_recreate_container(app):
    """Тест запуска контейнера."""
    params = {"type": "recreate", "name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/action", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert response.json == {"message": "action completed"}


@pytest.mark.anyio
async def test_list_containers(app):
    """Тест получения списка контейнеров."""
    request, response = await app.asgi_client.get(
        "/api/host/list", headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert "list" in response.json
    assert isinstance(response.json["list"], list)


@pytest.mark.anyio
async def test_get_container_number(app):
    """Тест получения количества контейнеров."""
    request, response = await app.asgi_client.get(
        "/api/host/number", headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert "number" in response.json
    assert isinstance(response.json["number"], int)


@pytest.mark.anyio
async def test_get_logs(app):
    """Тест получения логов контейнера."""
    params = {"name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/logs", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert "logs" in response.json


@pytest.mark.anyio
async def test_exec_command(app):
    """Тест выполнения команды в контейнере."""
    params = {"name": "test", "command": "echo 'hello'"}
    request, response = await app.asgi_client.get(
        "/api/host/exec", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert "exec" in response.json


@pytest.mark.anyio
async def test_container_stats(app):
    """Тест получения статистики контейнера."""
    params = {"name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/stats", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert "stats" in response.json
    assert "inspect" in response.json


@pytest.mark.anyio
async def test_container_status(app):
    """Тест получения статуса контейнера."""
    params = {"name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/status", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert "status" in response.json
    assert response.json["status"] in ["running", "stopped"]


@pytest.mark.anyio
async def test_server_resources(app):
    """Тест получения ресурсов сервера."""
    request, response = await app.asgi_client.get(
        "/api/host/resources", headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert "resources" in response.json


@pytest.mark.anyio
async def test_restart_container(app):
    """Тест перезапуска контейнера."""
    params = {"type": "restart", "name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/action", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert response.json == {"message": "action completed"}


@pytest.mark.anyio
async def test_remove_container(app):
    """Тест удаления контейнера."""
    params = {"name": "test"}
    request, response = await app.asgi_client.get(
        "/api/host/remove", params=params, headers={"Authorization": "secret"}
    )
    assert response.status == 200
    assert "remove" in response.json
