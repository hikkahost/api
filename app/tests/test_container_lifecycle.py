import shutil
from pathlib import Path
from unittest.mock import MagicMock

import docker
import pytest

from app.src import container as container_mod


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docker-compose.yml").write_text("services: {}\n")
    return tmp_path


def test_force_cleanup_removes_volume_dir(workdir, monkeypatch):
    volume = workdir / "volumes" / "user1"
    volume.mkdir(parents=True)
    (volume / "data").mkdir()
    (volume / "docker-compose.yml").write_text("services: {}\n")
    (volume / ".env").write_text("IP_PREFIX=192.168.5\nBRIDGE_NAME=br-user1\n")

    monkeypatch.setattr(container_mod, "remove_caddy_user", lambda *a, **k: None)
    monkeypatch.setattr(
        container_mod,
        "_compose_client",
        lambda path: MagicMock(compose=MagicMock(down=MagicMock(), rm=MagicMock())),
    )
    monkeypatch.setattr(container_mod, "_remove_docker_container", lambda *a, **k: None)
    monkeypatch.setattr(container_mod, "_remove_docker_network", lambda *a, **k: None)
    monkeypatch.setattr(container_mod, "_clear_network_limits", lambda *a, **k: None)

    warnings = container_mod._force_cleanup("user1")
    assert warnings == []
    assert not volume.exists()


def test_remove_raises_if_volume_remains(workdir, monkeypatch):
    volume = workdir / "volumes" / "user1"
    volume.mkdir(parents=True)

    monkeypatch.setattr(
        container_mod,
        "_force_cleanup",
        lambda name: ["volume rmtree: permission denied"],
    )

    with pytest.raises(RuntimeError, match="Failed to remove volume directory"):
        container_mod.remove("user1")


def test_create_reconciles_running_container(workdir, monkeypatch):
    volume = workdir / "volumes" / "user1"
    volume.mkdir(parents=True)
    (volume / "docker-compose.yml").write_text("services: {}\n")

    running = MagicMock(status="running")
    monkeypatch.setattr(container_mod, "_get_container", lambda name: running)
    reconcile = MagicMock()
    monkeypatch.setattr(container_mod, "_reconcile_running_container", reconcile)

    container_mod.create(8080, "user1", password="hash")
    reconcile.assert_called_once_with("user1", "hash")


def test_create_cleans_orphan_volume_before_provision(workdir, monkeypatch):
    volume = workdir / "volumes" / "orphan"
    volume.mkdir(parents=True)
    cleanup_calls = []

    def _cleanup(name):
        cleanup_calls.append(name)
        if volume.exists():
            shutil.rmtree(volume)
        return []

    monkeypatch.setattr(container_mod, "_get_container", lambda name: None)
    monkeypatch.setattr(container_mod, "_force_cleanup", _cleanup)
    monkeypatch.setattr(container_mod, "_allocate_ip_suffix", lambda: 10)
    monkeypatch.setattr(container_mod, "_apply_network_limits", lambda *a, **k: None)
    monkeypatch.setattr(container_mod, "create_vhost", lambda *a, **k: None)

    compose = MagicMock()
    monkeypatch.setattr(container_mod, "_compose_client", lambda path: compose)
    monkeypatch.setattr(container_mod, "_retry", lambda func, **kwargs: func())

    container_mod.create(8080, "orphan")

    assert cleanup_calls == ["orphan"]
    assert (volume / ".env").is_file()
    compose.compose.build.assert_called_once()
    compose.compose.up.assert_called_once_with(detach=True)


def test_create_rolls_back_on_compose_failure(workdir, monkeypatch):
    monkeypatch.setattr(container_mod, "_get_container", lambda name: None)

    rollback_calls = []
    monkeypatch.setattr(
        container_mod,
        "_force_cleanup",
        lambda name: rollback_calls.append(name) or [],
    )
    monkeypatch.setattr(container_mod, "_allocate_ip_suffix", lambda: 11)

    compose = MagicMock()
    compose.compose.build.side_effect = RuntimeError("daemon overloaded")
    monkeypatch.setattr(container_mod, "_compose_client", lambda path: compose)
    monkeypatch.setattr(container_mod, "_retry", lambda func, **kwargs: func())

    with pytest.raises(RuntimeError, match="daemon overloaded"):
        container_mod.create(8080, "broken")

    assert rollback_calls == ["broken"]
    assert not (workdir / "volumes" / "broken").exists()


def test_snapshot_not_found_without_volume(workdir, monkeypatch):
    monkeypatch.setattr(
        container_mod.client.containers,
        "get",
        MagicMock(side_effect=docker.errors.NotFound("missing")),
    )
    snap = container_mod.get_container_snapshot("missing")
    assert snap["state"] == "not_found"
    assert snap["stats"] is None


def test_snapshot_provisioning_when_volume_exists(workdir, monkeypatch):
    volume = workdir / "volumes" / "pending"
    volume.mkdir(parents=True)
    monkeypatch.setattr(
        container_mod.client.containers,
        "get",
        MagicMock(side_effect=docker.errors.NotFound("pending")),
    )
    snap = container_mod.get_container_snapshot("pending")
    assert snap["state"] == "provisioning"
    assert snap["stats"] is None


def test_snapshot_running_includes_stats(workdir, monkeypatch):
    container = MagicMock(status="running", attrs={"Id": "abc"})
    container.stats.return_value = {"cpu_stats": {}}
    monkeypatch.setattr(
        container_mod.client.containers,
        "get",
        MagicMock(return_value=container),
    )

    snap = container_mod.get_container_snapshot("user1")
    assert snap["state"] == "running"
    assert snap["stats"] == {"cpu_stats": {}}
    assert snap["inspect"] == {"Id": "abc"}


def test_snapshot_stopped_without_stats(workdir, monkeypatch):
    container = MagicMock(status="exited", attrs={"Id": "abc"})
    monkeypatch.setattr(
        container_mod.client.containers,
        "get",
        MagicMock(return_value=container),
    )

    snap = container_mod.get_container_snapshot("user1")
    assert snap["state"] == "stopped"
    assert snap["docker_status"] == "exited"
    assert snap["stats"] is None
    assert snap["inspect"] == {"Id": "abc"}


def test_remove_docker_container_stops_before_remove(monkeypatch):
    warnings = []
    container = MagicMock()
    container.kill.side_effect = docker.errors.APIError("busy")
    container.stop.return_value = None
    container.remove.return_value = None

    get_mock = MagicMock(return_value=container)
    monkeypatch.setattr(container_mod.client.containers, "get", get_mock)

    container_mod._remove_docker_container("user1", warnings)

    container.stop.assert_called_once()
    container.remove.assert_called_once_with(force=True)
    assert warnings == []
