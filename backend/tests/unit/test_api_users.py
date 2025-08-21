import pytest
from fastapi.testclient import TestClient

from app import app
from dependencies import get_existing_user_id

client = TestClient(app)


def test_delete_current_user_success(monkeypatch):
    app.dependency_overrides[get_existing_user_id] = lambda: "testuser"
    monkeypatch.setattr("api.users.profile_manager.delete_user", lambda uid: True)

    response = client.delete("/user")
    assert response.status_code == 200

    app.dependency_overrides = {}


def test_delete_current_user_no_user():
    app.dependency_overrides[get_existing_user_id] = lambda: None

    response = client.delete("/user")
    assert response.status_code == 404

    app.dependency_overrides = {}


def test_admin_delete_all_users(monkeypatch):
    monkeypatch.setattr("api.admin.verify_admin_token", lambda auth: None)
    monkeypatch.setattr("api.admin.profile_manager.delete_all_users", lambda: True)

    response = client.delete("/admin/users", headers={"Authorization": "Bearer test"})
    assert response.status_code == 200

