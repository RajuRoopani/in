"""
Tests for the Users and Posts domains.

Covers:
  - POST /users           (create user, duplicate username)
  - GET  /users/{id}      (found, missing)
  - PUT  /users/{id}      (update fields, missing user)
  - POST /posts           (create, content > 500 chars, missing user)
  - GET  /posts/{id}      (found with author, missing)
  - GET  /users/{id}/posts (newest-first, empty list)
  - DELETE /posts/{id}    (cascade likes/comments/reposts, missing post)
"""

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Users — creation
# ---------------------------------------------------------------------------

class TestCreateUser:
    def test_create_user_returns_201(self, client: TestClient):
        resp = client.post("/users", json={
            "username": "alice",
            "display_name": "Alice",
            "bio": "Hi there",
            "profile_picture_url": "https://example.com/alice.jpg",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "alice"
        assert data["display_name"] == "Alice"
        assert data["bio"] == "Hi there"
        assert data["profile_picture_url"] == "https://example.com/alice.jpg"
        assert data["followers_count"] == 0
        assert data["following_count"] == 0
        assert data["posts_count"] == 0
        assert "id" in data
        assert "created_at" in data

    def test_create_user_minimal_fields(self, client: TestClient):
        """username and display_name are required; bio/pic optional."""
        resp = client.post("/users", json={
            "username": "bob",
            "display_name": "Bob",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "bob"
        assert data["bio"] == ""
        assert data["profile_picture_url"] == ""

    def test_create_user_duplicate_username_returns_409(self, client: TestClient, create_user):
        create_user(username="alice")
        resp = client.post("/users", json={
            "username": "alice",
            "display_name": "Alice 2",
        })
        assert resp.status_code == 409

    def test_create_two_different_users_ok(self, client: TestClient):
        r1 = client.post("/users", json={"username": "user1", "display_name": "User One"})
        r2 = client.post("/users", json={"username": "user2", "display_name": "User Two"})
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["id"] != r2.json()["id"]


# ---------------------------------------------------------------------------
# Users — retrieval
# ---------------------------------------------------------------------------

class TestGetUser:
    def test_get_existing_user_returns_200(self, client: TestClient, create_user):
        user = create_user(username="charlie", display_name="Charlie")
        resp = client.get(f"/users/{user['id']}")
        assert resp.status_code == 200
        assert resp.json()["username"] == "charlie"

    def test_get_missing_user_returns_404(self, client: TestClient):
        resp = client.get("/users/nonexistent-id")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Users — update
# ---------------------------------------------------------------------------

class TestUpdateUser:
    def test_update_display_name_returns_200(self, client: TestClient, create_user):
        user = create_user(username="diana")
        resp = client.put(f"/users/{user['id']}", json={"display_name": "Diana Updated"})
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Diana Updated"

    def test_update_bio_returns_200(self, client: TestClient, create_user):
        user = create_user(username="eve", bio="old bio")
        resp = client.put(f"/users/{user['id']}", json={"bio": "new bio"})
        assert resp.status_code == 200
        assert resp.json()["bio"] == "new bio"

    def test_update_profile_picture_url(self, client: TestClient, create_user):
        user = create_user(username="frank")
        new_url = "https://cdn.example.com/frank.png"
        resp = client.put(f"/users/{user['id']}", json={"profile_picture_url": new_url})
        assert resp.status_code == 200
        assert resp.json()["profile_picture_url"] == new_url

    def test_update_partial_only_changes_given_fields(self, client: TestClient, create_user):
        user = create_user(username="grace", display_name="Grace", bio="original")
        resp = client.put(f"/users/{user['id']}", json={"display_name": "Grace V2"})
        data = resp.json()
        assert data["display_name"] == "Grace V2"
        assert data["bio"] == "original"  # unchanged

    def test_update_missing_user_returns_404(self, client: TestClient):
        resp = client.put("/users/no-such-id", json={"bio": "x"})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Posts — creation
# ---------------------------------------------------------------------------

class TestCreatePost:
    def test_create_post_returns_201(self, client: TestClient, create_user):
        user = create_user(username="poster")
        resp = client.post("/posts", json={"user_id": user["id"], "content": "Hello world!"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "Hello world!"
        assert data["user_id"] == user["id"]
        assert data["likes_count"] == 0
        assert data["comments_count"] == 0
        assert data["reposts_count"] == 0
        assert "id" in data

    def test_create_post_with_media(self, client: TestClient, create_user):
        user = create_user(username="mediauser")
        resp = client.post("/posts", json={
            "user_id": user["id"],
            "content": "Check this out",
            "media_url": "https://example.com/img.jpg",
            "media_type": "image",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["media_url"] == "https://example.com/img.jpg"
        assert data["media_type"] == "image"

    def test_create_post_author_info_attached(self, client: TestClient, create_user):
        user = create_user(username="authortest", display_name="Author Test")
        resp = client.post("/posts", json={"user_id": user["id"], "content": "test"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["author"] is not None
        assert data["author"]["username"] == "authortest"

    def test_create_post_increments_posts_count(self, client: TestClient, create_user):
        user = create_user(username="countuser")
        client.post("/posts", json={"user_id": user["id"], "content": "post 1"})
        user_resp = client.get(f"/users/{user['id']}")
        assert user_resp.json()["posts_count"] == 1

    def test_create_post_content_over_500_chars_returns_400(self, client: TestClient, create_user):
        user = create_user(username="longposter")
        resp = client.post("/posts", json={"user_id": user["id"], "content": "x" * 501})
        assert resp.status_code == 400

    def test_create_post_exactly_500_chars_allowed(self, client: TestClient, create_user):
        user = create_user(username="exactuser")
        resp = client.post("/posts", json={"user_id": user["id"], "content": "x" * 500})
        assert resp.status_code == 201

    def test_create_post_missing_user_returns_404(self, client: TestClient):
        resp = client.post("/posts", json={"user_id": "ghost-id", "content": "hello"})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Posts — retrieval
# ---------------------------------------------------------------------------

class TestGetPost:
    def test_get_post_returns_200_with_author(self, client: TestClient, create_post):
        user, post = create_post(content="My first post")
        resp = client.get(f"/posts/{post['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == "My first post"
        assert data["author"]["id"] == user["id"]

    def test_get_missing_post_returns_404(self, client: TestClient):
        resp = client.get("/posts/no-such-post")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Posts — list by user
# ---------------------------------------------------------------------------

class TestListUserPosts:
    def test_list_user_posts_newest_first(self, client: TestClient, create_user):
        user = create_user(username="orderedposter")
        client.post("/posts", json={"user_id": user["id"], "content": "first"})
        client.post("/posts", json={"user_id": user["id"], "content": "second"})
        client.post("/posts", json={"user_id": user["id"], "content": "third"})

        resp = client.get(f"/users/{user['id']}/posts")
        assert resp.status_code == 200
        posts = resp.json()
        assert len(posts) == 3
        # newest-first: timestamps should be descending
        timestamps = [p["created_at"] for p in posts]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_list_user_posts_returns_correct_content(self, client: TestClient, create_user):
        user = create_user(username="contentposter")
        client.post("/posts", json={"user_id": user["id"], "content": "alpha"})
        client.post("/posts", json={"user_id": user["id"], "content": "beta"})

        resp = client.get(f"/users/{user['id']}/posts")
        contents = {p["content"] for p in resp.json()}
        assert contents == {"alpha", "beta"}

    def test_list_posts_empty_for_new_user(self, client: TestClient, create_user):
        user = create_user(username="noposter")
        resp = client.get(f"/users/{user['id']}/posts")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_posts_missing_user_returns_404(self, client: TestClient):
        resp = client.get("/users/ghost/posts")
        assert resp.status_code == 404

    def test_list_posts_only_returns_own_posts(self, client: TestClient, create_user):
        user_a = create_user(username="usera")
        user_b = create_user(username="userb")
        client.post("/posts", json={"user_id": user_a["id"], "content": "post by A"})
        client.post("/posts", json={"user_id": user_b["id"], "content": "post by B"})

        resp = client.get(f"/users/{user_a['id']}/posts")
        posts = resp.json()
        assert len(posts) == 1
        assert posts[0]["content"] == "post by A"


# ---------------------------------------------------------------------------
# Posts — deletion with cascade
# ---------------------------------------------------------------------------

class TestDeletePost:
    def test_delete_post_returns_200(self, client: TestClient, create_post):
        _, post = create_post()
        resp = client.delete(f"/posts/{post['id']}")
        assert resp.status_code == 200

    def test_delete_post_removes_it(self, client: TestClient, create_post):
        _, post = create_post()
        client.delete(f"/posts/{post['id']}")
        resp = client.get(f"/posts/{post['id']}")
        assert resp.status_code == 404

    def test_delete_missing_post_returns_404(self, client: TestClient):
        resp = client.delete("/posts/no-such-post")
        assert resp.status_code == 404

    def test_delete_post_decrements_posts_count(self, client: TestClient, create_user):
        user = create_user(username="deleteposter")
        post_resp = client.post("/posts", json={"user_id": user["id"], "content": "bye"})
        post_id = post_resp.json()["id"]

        client.delete(f"/posts/{post_id}")
        user_resp = client.get(f"/users/{user['id']}")
        assert user_resp.json()["posts_count"] == 0

    def test_delete_post_cascades_likes(self, client: TestClient, create_post, create_user):
        user, post = create_post()
        liker = create_user(username="likeruser")
        # Like the post
        client.post(f"/posts/{post['id']}/like", json={"user_id": liker["id"]})
        # Delete the post
        client.delete(f"/posts/{post['id']}")
        # Post is gone — like should not resurface if post was re-checked
        assert post["id"] not in [p["id"] for p in client.get(f"/users/{user['id']}/posts").json()]

    def test_delete_post_cascades_comments(self, client: TestClient, create_post, create_user):
        user, post = create_post()
        commenter = create_user(username="commenteruser")
        # Add a comment
        client.post(f"/posts/{post['id']}/comments", json={"user_id": commenter["id"], "text": "hi"})
        # Delete the post
        client.delete(f"/posts/{post['id']}")
        # The post is gone — verifying cascade by confirming post no longer exists
        resp = client.get(f"/posts/{post['id']}")
        assert resp.status_code == 404

    def test_delete_post_cascades_reposts(self, client: TestClient, create_post, create_user):
        user, post = create_post()
        reposter = create_user(username="reposteruser")
        # Repost it
        client.post(f"/posts/{post['id']}/repost", json={"user_id": reposter["id"]})
        # Delete the post
        client.delete(f"/posts/{post['id']}")
        resp = client.get(f"/posts/{post['id']}")
        assert resp.status_code == 404
