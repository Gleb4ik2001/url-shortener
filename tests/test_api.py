import os
import tempfile

from fastapi.testclient import TestClient

from app.main import create_app
from app import settings as settings_module


def test_shorten_and_redirect_ok(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        db_path = os.path.join(d, "test.sqlite3")
        monkeypatch.setenv("DB_PATH", db_path)
        monkeypatch.setenv("BASE_URL", "http://testserver")

        # пересоздаём settings через импорт модуля заново нельзя просто так,
        # поэтому обращаемся к create_app(), которая вызывает init_db по settings
        # (settings читает env при импорте). Проще — перезагрузить модуль settings.
        import importlib
        importlib.reload(settings_module)
        import app.main as main_module
        importlib.reload(main_module)

        app = main_module.create_app()
        client = TestClient(app)

        r = client.post("/shorten", json={"url": "https://example.com/path"})
        assert r.status_code == 201
        data = r.json()
        assert "code" in data and len(data["code"]) >= 5
        assert data["short_url"] == f"http://testserver/{data['code']}"
        assert data["long_url"] == "https://example.com/path"

        r2 = client.get(f"/{data['code']}", follow_redirects=False)
        assert r2.status_code == 307
        assert r2.headers["location"] == "https://example.com/path"


def test_custom_code_conflict(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        db_path = os.path.join(d, "test.sqlite3")
        monkeypatch.setenv("DB_PATH", db_path)
        monkeypatch.setenv("BASE_URL", "http://testserver")

        import importlib
        import app.settings as settings_mod
        importlib.reload(settings_mod)
        import app.main as main_mod
        importlib.reload(main_mod)

        client = TestClient(main_mod.create_app())

        r1 = client.post("/shorten", json={"url": "https://a.com", "custom_code": "myCode1"})
        assert r1.status_code == 201

        r2 = client.post("/shorten", json={"url": "https://b.com", "custom_code": "myCode1"})
        assert r2.status_code == 409
        assert r2.json()["detail"] == "custom_code already exists"


def test_redirect_404(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        db_path = os.path.join(d, "test.sqlite3")
        monkeypatch.setenv("DB_PATH", db_path)
        monkeypatch.setenv("BASE_URL", "http://testserver")

        import importlib
        import app.settings as settings_mod
        importlib.reload(settings_mod)
        import app.main as main_mod
        importlib.reload(main_mod)

        client = TestClient(main_mod.create_app())

        r = client.get("/no_such_code", follow_redirects=False)
        assert r.status_code == 404
