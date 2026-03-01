"""
Tests for the comments and reposts routers of the 'in' social media platform.

Covers:
  Comments — add, list (newest-first), delete, count tracking, edge cases
  Reposts  — repost, double-repost, list reposters, count tracking, edge cases
"""

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# COMMENTS
# ---------------------------------------------------------------------------


class TestAddComment:
    """POST /posts/{post_id}/comments → 201 / 400 / 404"""

    def test_add_comment_returns_201(self, client: TestClient, create_post):
        """Happy path: valid comment is created and returned."""
        user, post = create_post()
        resp = client.post(
            f"/posts/{post['id']}/comments",
            json={"user_id": user["id"], "text": "Great post!"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["post_id"] == post["id"]
        assert body["user_id"] == user["id"]
        assert body["text"] == "Great post!"
        assert "id" in body
        assert "created_at" in body

    def test_add_comment_increments_comments_count(self, client: TestClient, create_post):
        """comments_count on the post should increase after each comment."""
        user, post = create_post()
        assert post["comments_count"] == 0

        client.post(
            f"/posts/{post['id']}/comments",
            json={"user_id": user["id"], "text": "First comment"},
        )
        client.post(
            f"/posts/{post['id']}/comments",
            json={"user_id": user["id"], "text": "Second comment"},
        )

        resp = client.get(f"/posts/{post['id']}")
        assert resp.status_code == 200
        assert resp.json()["comments_count"] == 2

    def test_add_comment_empty_text_returns_400(self, client: TestClient, create_post):
        """Empty text should be rejected with 400."""
        user, post = create_post()
        resp = client.post(
            f"/posts/{post['id']}/comments",
            json={"user_id": user["id"], "text": ""},
        )
        assert resp.status_code == 400

    def test_add_comment_whitespace_text_returns_400(self, client: TestClient, create_post):
        """Whitespace-only text should be rejected with 400."""
        user, post = create_post()
        resp = client.post(
            f"/posts/{post['id']}/comments",
            json={"user_id": user["id"], "text": "   "},
        )
        assert resp.status_code == 400

    def test_add_comment_missing_post_returns_404(self, client: TestClient, create_user):
        """Non-existent post_id should return 404."""
        user = create_user()
        resp = client.post(
            "/posts/nonexistent-post-id/comments",
            json={"user_id": user["id"], "text": "Hello"},
        )
        assert resp.status_code == 404

    def test_add_comment_missing_user_returns_404(self, client: TestClient, create_post):
        """Non-existent user_id should return 404."""
        _, post = create_post()
        resp = client.post(
            f"/posts/{post['id']}/comments",
            json={"user_id": "nonexistent-user-id", "text": "Hello"},
        )
        assert resp.status_code == 404


class TestListComments:
    """GET /posts/{post_id}/comments → 200 / 404"""

    def test_list_comments_returns_200_empty(self, client: TestClient, create_post):
        """New post has no comments — returns empty list."""
        _, post = create_post()
        resp = client.get(f"/posts/{post['id']}/comments")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_comments_returns_all_comments(self, client: TestClient, create_post):
        """All comments for the post are returned."""
        user, post = create_post()
        texts = ["Alpha", "Beta", "Gamma"]
        for text in texts:
            client.post(
                f"/posts/{post['id']}/comments",
                json={"user_id": user["id"], "text": text},
            )
        resp = client.get(f"/posts/{post['id']}/comments")
        assert resp.status_code == 200
        returned_texts = [c["text"] for c in resp.json()]
        assert set(returned_texts) == set(texts)

    def test_list_comments_newest_first(self, client: TestClient, create_post):
        """Comments should be returned newest-first by created_at."""
        user, post = create_post()
        for text in ["First", "Second", "Third"]:
            client.post(
                f"/posts/{post['id']}/comments",
                json={"user_id": user["id"], "text": text},
            )
        resp = client.get(f"/posts/{post['id']}/comments")
        assert resp.status_code == 200
        comments = resp.json()
        # Verify descending order
        timestamps = [c["created_at"] for c in comments]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_list_comments_missing_post_returns_404(self, client: TestClient):
        """Non-existent post_id should return 404 on list."""
        resp = client.get("/posts/bogus-post-id/comments")
        assert resp.status_code == 404


class TestDeleteComment:
    """DELETE /comments/{comment_id} → 200 / 404"""

    def test_delete_comment_returns_200(self, client: TestClient, create_post):
        """Successfully deleting a comment returns 200."""
        user, post = create_post()
        add_resp = client.post(
            f"/posts/{post['id']}/comments",
            json={"user_id": user["id"], "text": "To be deleted"},
        )
        comment_id = add_resp.json()["id"]

        del_resp = client.delete(f"/comments/{comment_id}")
        assert del_resp.status_code == 200

    def test_delete_comment_removes_from_list(self, client: TestClient, create_post):
        """Deleted comment no longer appears in the post's comment list."""
        user, post = create_post()
        add_resp = client.post(
            f"/posts/{post['id']}/comments",
            json={"user_id": user["id"], "text": "Temporary"},
        )
        comment_id = add_resp.json()["id"]

        client.delete(f"/comments/{comment_id}")

        list_resp = client.get(f"/posts/{post['id']}/comments")
        assert list_resp.status_code == 200
        ids = [c["id"] for c in list_resp.json()]
        assert comment_id not in ids

    def test_delete_comment_decrements_comments_count(self, client: TestClient, create_post):
        """Deleting a comment decrements the post's comments_count."""
        user, post = create_post()
        add_resp = client.post(
            f"/posts/{post['id']}/comments",
            json={"user_id": user["id"], "text": "Will be deleted"},
        )
        comment_id = add_resp.json()["id"]

        # Verify count is 1 after adding
        get_resp = client.get(f"/posts/{post['id']}")
        assert get_resp.json()["comments_count"] == 1

        client.delete(f"/comments/{comment_id}")

        # Verify count is 0 after deleting
        get_resp = client.get(f"/posts/{post['id']}")
        assert get_resp.json()["comments_count"] == 0

    def test_delete_comment_missing_returns_404(self, client: TestClient):
        """Attempting to delete a non-existent comment returns 404."""
        resp = client.delete("/comments/nonexistent-comment-id")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# REPOSTS
# ---------------------------------------------------------------------------


class TestRepost:
    """POST /posts/{post_id}/repost → 201 / 404 / 409"""

    def test_repost_returns_201(self, client: TestClient, create_post, create_user):
        """Happy path: valid repost is created and returned."""
        _, post = create_post(username="author")
        reposter = create_user(username="reposter", display_name="Reposter")
        resp = client.post(
            f"/posts/{post['id']}/repost",
            json={"user_id": reposter["id"]},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["post_id"] == post["id"]
        assert body["user_id"] == reposter["id"]
        assert "created_at" in body

    def test_repost_increments_reposts_count(self, client: TestClient, create_post, create_user):
        """reposts_count on the post should increase after a repost."""
        _, post = create_post(username="author")
        reposter = create_user(username="reposter", display_name="Reposter")

        client.post(f"/posts/{post['id']}/repost", json={"user_id": reposter["id"]})

        resp = client.get(f"/posts/{post['id']}")
        assert resp.status_code == 200
        assert resp.json()["reposts_count"] == 1

    def test_double_repost_returns_409(self, client: TestClient, create_post, create_user):
        """Reposting the same post twice should return 409 Conflict."""
        _, post = create_post(username="author")
        reposter = create_user(username="reposter", display_name="Reposter")

        client.post(f"/posts/{post['id']}/repost", json={"user_id": reposter["id"]})
        resp = client.post(f"/posts/{post['id']}/repost", json={"user_id": reposter["id"]})
        assert resp.status_code == 409

    def test_repost_missing_post_returns_404(self, client: TestClient, create_user):
        """Reposting a non-existent post should return 404."""
        user = create_user()
        resp = client.post(
            "/posts/nonexistent-post/repost",
            json={"user_id": user["id"]},
        )
        assert resp.status_code == 404

    def test_repost_missing_user_returns_404(self, client: TestClient, create_post):
        """Reposting with a non-existent user_id should return 404."""
        _, post = create_post()
        resp = client.post(
            f"/posts/{post['id']}/repost",
            json={"user_id": "nonexistent-user"},
        )
        assert resp.status_code == 404


class TestListReposters:
    """GET /posts/{post_id}/reposts → 200 / 404"""

    def test_list_reposters_empty(self, client: TestClient, create_post):
        """Post with no reposts returns empty list."""
        _, post = create_post()
        resp = client.get(f"/posts/{post['id']}/reposts")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_reposters_returns_correct_users(
        self, client: TestClient, create_post, create_user
    ):
        """All users who reposted the post are returned as UserOut objects."""
        _, post = create_post(username="author")
        r1 = create_user(username="rep1", display_name="Reposter One")
        r2 = create_user(username="rep2", display_name="Reposter Two")

        client.post(f"/posts/{post['id']}/repost", json={"user_id": r1["id"]})
        client.post(f"/posts/{post['id']}/repost", json={"user_id": r2["id"]})

        resp = client.get(f"/posts/{post['id']}/reposts")
        assert resp.status_code == 200
        returned_ids = {u["id"] for u in resp.json()}
        assert r1["id"] in returned_ids
        assert r2["id"] in returned_ids

    def test_list_reposters_missing_post_returns_404(self, client: TestClient):
        """Non-existent post_id should return 404 on reposts list."""
        resp = client.get("/posts/nonexistent-post/reposts")
        assert resp.status_code == 404

    def test_repost_count_matches_reposter_list_length(
        self, client: TestClient, create_post, create_user
    ):
        """reposts_count on the post should match the length of reposters list."""
        _, post = create_post(username="author")
        for i in range(3):
            reposter = create_user(username=f"rep{i}", display_name=f"Rep {i}")
            client.post(f"/posts/{post['id']}/repost", json={"user_id": reposter["id"]})

        post_resp = client.get(f"/posts/{post['id']}")
        reposts_resp = client.get(f"/posts/{post['id']}/reposts")

        assert post_resp.json()["reposts_count"] == len(reposts_resp.json())
        assert post_resp.json()["reposts_count"] == 3
