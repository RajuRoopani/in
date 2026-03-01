"""
Shared test fixtures for the 'in' social media platform.

Provides an httpx async-compatible TestClient and resets storage between tests.
"""

import pytest
from fastapi.testclient import TestClient

from in_app.main import app
from in_app.storage import store


@pytest.fixture(autouse=True)
def reset_storage():
    """Reset all in-memory storage before every test."""
    store.reset()
    yield
    store.reset()


@pytest.fixture
def client():
    """Provide a synchronous test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def create_user(client):
    """Helper fixture: creates a user and returns the response JSON."""
    def _create(username: str = "testuser", display_name: str = "Test User", bio: str = "Hello", profile_picture_url: str = ""):
        resp = client.post("/users", json={
            "username": username,
            "display_name": display_name,
            "bio": bio,
            "profile_picture_url": profile_picture_url,
        })
        assert resp.status_code == 201
        return resp.json()
    return _create


@pytest.fixture
def create_post(client, create_user):
    """Helper fixture: creates a user + post and returns (user, post) dicts."""
    def _create(content: str = "Hello world!", username: str = "poster"):
        user = create_user(username=username, display_name=username.title())
        resp = client.post("/posts", json={
            "user_id": user["id"],
            "content": content,
        })
        assert resp.status_code == 201
        return user, resp.json()
    return _create
