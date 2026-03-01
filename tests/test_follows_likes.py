"""
Tests for the Follows and Likes domains.

Covers:
  POST   /users/{user_id}/follow     — 201 success, 400 self-follow, 404 unknown user, 409 duplicate
  DELETE /users/{user_id}/follow     — 200 success, 404 not-following
  GET    /users/{user_id}/followers  — 200 list, 404 unknown user
  GET    /users/{user_id}/following  — 200 list, 404 unknown user
  Counter integrity: followers_count, following_count updated on follow/unfollow

  POST   /posts/{post_id}/like       — 201 success, 404 unknown post/user, 409 double-like
  DELETE /posts/{post_id}/like       — 200 success, 404 not-liked
  Counter integrity: likes_count updated on like/unlike
"""

import json as _json

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Compat helper
# ---------------------------------------------------------------------------

def _delete_json(client: TestClient, url: str, body: dict):
    """
    Send a DELETE with a JSON body.

    Starlette's TestClient (≤0.52) strips body kwargs from the per-method
    shortcut ``client.delete()``.  Using the lower-level ``client.request()``
    preserves the ``json=`` parameter correctly.
    """
    return client.request("DELETE", url, json=body)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_user(client: TestClient, username: str, display_name: str = "") -> dict:
    resp = client.post("/users", json={
        "username": username,
        "display_name": display_name or username.title(),
    })
    assert resp.status_code == 201
    return resp.json()


def _make_post(client: TestClient, user_id: str, content: str = "Hello!") -> dict:
    resp = client.post("/posts", json={"user_id": user_id, "content": content})
    assert resp.status_code == 201
    return resp.json()


# ===========================================================================
# Follows — POST /users/{user_id}/follow
# ===========================================================================

class TestFollowUser:
    def test_follow_returns_201(self, client: TestClient):
        alice = _make_user(client, "alice")
        bob = _make_user(client, "bob")

        resp = client.post(f"/users/{alice['id']}/follow", json={"target_user_id": bob["id"]})
        assert resp.status_code == 201

    def test_follow_response_contains_expected_fields(self, client: TestClient):
        alice = _make_user(client, "alice")
        bob = _make_user(client, "bob")

        resp = client.post(f"/users/{alice['id']}/follow", json={"target_user_id": bob["id"]})
        data = resp.json()
        assert data["follower_id"] == alice["id"]
        assert data["followed_id"] == bob["id"]
        assert "created_at" in data

    def test_follow_increments_following_count_for_follower(self, client: TestClient):
        alice = _make_user(client, "alice")
        bob = _make_user(client, "bob")

        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": bob["id"]})

        alice_updated = client.get(f"/users/{alice['id']}").json()
        assert alice_updated["following_count"] == 1

    def test_follow_increments_followers_count_for_target(self, client: TestClient):
        alice = _make_user(client, "alice")
        bob = _make_user(client, "bob")

        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": bob["id"]})

        bob_updated = client.get(f"/users/{bob['id']}").json()
        assert bob_updated["followers_count"] == 1

    def test_follow_multiple_users_updates_counts_independently(self, client: TestClient):
        alice = _make_user(client, "alice")
        bob = _make_user(client, "bob")
        carol = _make_user(client, "carol")

        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": bob["id"]})
        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": carol["id"]})

        alice_updated = client.get(f"/users/{alice['id']}").json()
        bob_updated = client.get(f"/users/{bob['id']}").json()
        carol_updated = client.get(f"/users/{carol['id']}").json()

        assert alice_updated["following_count"] == 2
        assert bob_updated["followers_count"] == 1
        assert carol_updated["followers_count"] == 1

    def test_follow_self_returns_400(self, client: TestClient):
        alice = _make_user(client, "alice")

        resp = client.post(f"/users/{alice['id']}/follow", json={"target_user_id": alice["id"]})
        assert resp.status_code == 400

    def test_follow_self_does_not_mutate_counters(self, client: TestClient):
        alice = _make_user(client, "alice")
        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": alice["id"]})

        alice_updated = client.get(f"/users/{alice['id']}").json()
        assert alice_updated["following_count"] == 0
        assert alice_updated["followers_count"] == 0

    def test_follow_unknown_follower_returns_404(self, client: TestClient):
        bob = _make_user(client, "bob")

        resp = client.post("/users/ghost-id/follow", json={"target_user_id": bob["id"]})
        assert resp.status_code == 404

    def test_follow_unknown_target_returns_404(self, client: TestClient):
        alice = _make_user(client, "alice")

        resp = client.post(f"/users/{alice['id']}/follow", json={"target_user_id": "ghost-id"})
        assert resp.status_code == 404

    def test_duplicate_follow_returns_409(self, client: TestClient):
        alice = _make_user(client, "alice")
        bob = _make_user(client, "bob")

        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": bob["id"]})
        resp = client.post(f"/users/{alice['id']}/follow", json={"target_user_id": bob["id"]})
        assert resp.status_code == 409

    def test_duplicate_follow_does_not_double_increment_counts(self, client: TestClient):
        alice = _make_user(client, "alice")
        bob = _make_user(client, "bob")

        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": bob["id"]})
        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": bob["id"]})  # 409

        alice_updated = client.get(f"/users/{alice['id']}").json()
        bob_updated = client.get(f"/users/{bob['id']}").json()
        assert alice_updated["following_count"] == 1
        assert bob_updated["followers_count"] == 1


# ===========================================================================
# Follows — DELETE /users/{user_id}/follow
# ===========================================================================

class TestUnfollowUser:
    def test_unfollow_returns_200(self, client: TestClient):
        alice = _make_user(client, "alice")
        bob = _make_user(client, "bob")

        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": bob["id"]})
        resp = _delete_json(client, f"/users/{alice['id']}/follow", {"target_user_id": bob["id"]})
        assert resp.status_code == 200

    def test_unfollow_response_has_detail(self, client: TestClient):
        alice = _make_user(client, "alice")
        bob = _make_user(client, "bob")

        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": bob["id"]})
        resp = _delete_json(client, f"/users/{alice['id']}/follow", {"target_user_id": bob["id"]})
        assert "detail" in resp.json()

    def test_unfollow_decrements_following_count(self, client: TestClient):
        alice = _make_user(client, "alice")
        bob = _make_user(client, "bob")

        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": bob["id"]})
        _delete_json(client, f"/users/{alice['id']}/follow", {"target_user_id": bob["id"]})

        alice_updated = client.get(f"/users/{alice['id']}").json()
        assert alice_updated["following_count"] == 0

    def test_unfollow_decrements_followers_count(self, client: TestClient):
        alice = _make_user(client, "alice")
        bob = _make_user(client, "bob")

        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": bob["id"]})
        _delete_json(client, f"/users/{alice['id']}/follow", {"target_user_id": bob["id"]})

        bob_updated = client.get(f"/users/{bob['id']}").json()
        assert bob_updated["followers_count"] == 0

    def test_unfollow_does_not_go_below_zero(self, client: TestClient):
        """Counts floor at 0 — double unfollow (second hits 404) must not produce negative counts."""
        alice = _make_user(client, "alice")
        bob = _make_user(client, "bob")

        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": bob["id"]})
        _delete_json(client, f"/users/{alice['id']}/follow", {"target_user_id": bob["id"]})
        # second unfollow → 404, but counts must still be 0
        _delete_json(client, f"/users/{alice['id']}/follow", {"target_user_id": bob["id"]})

        alice_updated = client.get(f"/users/{alice['id']}").json()
        bob_updated = client.get(f"/users/{bob['id']}").json()
        assert alice_updated["following_count"] == 0
        assert bob_updated["followers_count"] == 0

    def test_unfollow_relationship_not_following_returns_404(self, client: TestClient):
        alice = _make_user(client, "alice")
        bob = _make_user(client, "bob")

        resp = _delete_json(client, f"/users/{alice['id']}/follow", {"target_user_id": bob["id"]})
        assert resp.status_code == 404

    def test_unfollow_asymmetric_relationships_intact(self, client: TestClient):
        """If bob also follows alice, unfollowing alice → bob should not affect bob → alice."""
        alice = _make_user(client, "alice")
        bob = _make_user(client, "bob")

        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": bob["id"]})
        client.post(f"/users/{bob['id']}/follow", json={"target_user_id": alice["id"]})

        _delete_json(client, f"/users/{alice['id']}/follow", {"target_user_id": bob["id"]})

        # alice → bob removed; bob → alice should still exist
        bob_following = client.get(f"/users/{bob['id']}/following").json()
        following_ids = {u["id"] for u in bob_following}
        assert alice["id"] in following_ids

        alice_following = client.get(f"/users/{alice['id']}/following").json()
        assert alice_following == []


# ===========================================================================
# Follows — GET /users/{user_id}/followers
# ===========================================================================

class TestListFollowers:
    def test_list_followers_returns_200(self, client: TestClient):
        target = _make_user(client, "target")
        resp = client.get(f"/users/{target['id']}/followers")
        assert resp.status_code == 200

    def test_list_followers_empty_for_new_user(self, client: TestClient):
        target = _make_user(client, "target")
        resp = client.get(f"/users/{target['id']}/followers")
        assert resp.json() == []

    def test_list_followers_shows_correct_users(self, client: TestClient):
        alice = _make_user(client, "alice")
        bob = _make_user(client, "bob")
        carol = _make_user(client, "carol")

        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": carol["id"]})
        client.post(f"/users/{bob['id']}/follow", json={"target_user_id": carol["id"]})

        followers = client.get(f"/users/{carol['id']}/followers").json()
        follower_ids = {u["id"] for u in followers}
        assert alice["id"] in follower_ids
        assert bob["id"] in follower_ids
        assert len(followers) == 2

    def test_list_followers_does_not_include_non_followers(self, client: TestClient):
        alice = _make_user(client, "alice")
        bob = _make_user(client, "bob")
        carol = _make_user(client, "carol")

        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": carol["id"]})

        followers = client.get(f"/users/{carol['id']}/followers").json()
        follower_ids = {u["id"] for u in followers}
        assert bob["id"] not in follower_ids

    def test_list_followers_unknown_user_returns_404(self, client: TestClient):
        resp = client.get("/users/ghost-id/followers")
        assert resp.status_code == 404

    def test_list_followers_returns_user_objects(self, client: TestClient):
        alice = _make_user(client, "alice")
        bob = _make_user(client, "bob")

        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": bob["id"]})

        followers = client.get(f"/users/{bob['id']}/followers").json()
        assert len(followers) == 1
        follower = followers[0]
        # Confirm it's a full UserOut shape
        for field in ("id", "username", "display_name", "followers_count", "following_count"):
            assert field in follower

    def test_list_followers_removed_after_unfollow(self, client: TestClient):
        alice = _make_user(client, "alice")
        bob = _make_user(client, "bob")

        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": bob["id"]})
        _delete_json(client, f"/users/{alice['id']}/follow", {"target_user_id": bob["id"]})

        followers = client.get(f"/users/{bob['id']}/followers").json()
        assert followers == []


# ===========================================================================
# Follows — GET /users/{user_id}/following
# ===========================================================================

class TestListFollowing:
    def test_list_following_returns_200(self, client: TestClient):
        alice = _make_user(client, "alice")
        resp = client.get(f"/users/{alice['id']}/following")
        assert resp.status_code == 200

    def test_list_following_empty_for_new_user(self, client: TestClient):
        alice = _make_user(client, "alice")
        resp = client.get(f"/users/{alice['id']}/following")
        assert resp.json() == []

    def test_list_following_shows_followed_users(self, client: TestClient):
        alice = _make_user(client, "alice")
        bob = _make_user(client, "bob")
        carol = _make_user(client, "carol")

        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": bob["id"]})
        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": carol["id"]})

        following = client.get(f"/users/{alice['id']}/following").json()
        following_ids = {u["id"] for u in following}
        assert bob["id"] in following_ids
        assert carol["id"] in following_ids
        assert len(following) == 2

    def test_list_following_does_not_cross_contaminate(self, client: TestClient):
        """alice follows bob; carol follows nobody — carol's following list stays empty."""
        alice = _make_user(client, "alice")
        bob = _make_user(client, "bob")
        carol = _make_user(client, "carol")

        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": bob["id"]})

        carol_following = client.get(f"/users/{carol['id']}/following").json()
        assert carol_following == []

    def test_list_following_unknown_user_returns_404(self, client: TestClient):
        resp = client.get("/users/ghost-id/following")
        assert resp.status_code == 404

    def test_list_following_removed_after_unfollow(self, client: TestClient):
        alice = _make_user(client, "alice")
        bob = _make_user(client, "bob")

        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": bob["id"]})
        _delete_json(client, f"/users/{alice['id']}/follow", {"target_user_id": bob["id"]})

        following = client.get(f"/users/{alice['id']}/following").json()
        assert following == []


# ===========================================================================
# Likes — POST /posts/{post_id}/like
# ===========================================================================

class TestLikePost:
    def test_like_returns_201(self, client: TestClient):
        alice = _make_user(client, "alice")
        post = _make_post(client, alice["id"])
        bob = _make_user(client, "bob")

        resp = client.post(f"/posts/{post['id']}/like", json={"user_id": bob["id"]})
        assert resp.status_code == 201

    def test_like_response_contains_expected_fields(self, client: TestClient):
        alice = _make_user(client, "alice")
        post = _make_post(client, alice["id"])
        bob = _make_user(client, "bob")

        resp = client.post(f"/posts/{post['id']}/like", json={"user_id": bob["id"]})
        data = resp.json()
        assert data["post_id"] == post["id"]
        assert data["user_id"] == bob["id"]
        assert "created_at" in data

    def test_like_increments_likes_count(self, client: TestClient):
        alice = _make_user(client, "alice")
        post = _make_post(client, alice["id"])
        bob = _make_user(client, "bob")

        client.post(f"/posts/{post['id']}/like", json={"user_id": bob["id"]})

        post_updated = client.get(f"/posts/{post['id']}").json()
        assert post_updated["likes_count"] == 1

    def test_multiple_likes_increment_count_correctly(self, client: TestClient):
        alice = _make_user(client, "alice")
        post = _make_post(client, alice["id"])
        bob = _make_user(client, "bob")
        carol = _make_user(client, "carol")

        client.post(f"/posts/{post['id']}/like", json={"user_id": bob["id"]})
        client.post(f"/posts/{post['id']}/like", json={"user_id": carol["id"]})

        post_updated = client.get(f"/posts/{post['id']}").json()
        assert post_updated["likes_count"] == 2

    def test_like_author_can_like_own_post(self, client: TestClient):
        """Authors may like their own posts — no restriction on self-likes."""
        alice = _make_user(client, "alice")
        post = _make_post(client, alice["id"])

        resp = client.post(f"/posts/{post['id']}/like", json={"user_id": alice["id"]})
        assert resp.status_code == 201

    def test_like_unknown_post_returns_404(self, client: TestClient):
        alice = _make_user(client, "alice")

        resp = client.post("/posts/ghost-post-id/like", json={"user_id": alice["id"]})
        assert resp.status_code == 404

    def test_like_unknown_user_returns_404(self, client: TestClient):
        alice = _make_user(client, "alice")
        post = _make_post(client, alice["id"])

        resp = client.post(f"/posts/{post['id']}/like", json={"user_id": "ghost-user-id"})
        assert resp.status_code == 404

    def test_double_like_returns_409(self, client: TestClient):
        alice = _make_user(client, "alice")
        post = _make_post(client, alice["id"])
        bob = _make_user(client, "bob")

        client.post(f"/posts/{post['id']}/like", json={"user_id": bob["id"]})
        resp = client.post(f"/posts/{post['id']}/like", json={"user_id": bob["id"]})
        assert resp.status_code == 409

    def test_double_like_does_not_double_increment_count(self, client: TestClient):
        alice = _make_user(client, "alice")
        post = _make_post(client, alice["id"])
        bob = _make_user(client, "bob")

        client.post(f"/posts/{post['id']}/like", json={"user_id": bob["id"]})
        client.post(f"/posts/{post['id']}/like", json={"user_id": bob["id"]})  # 409

        post_updated = client.get(f"/posts/{post['id']}").json()
        assert post_updated["likes_count"] == 1

    def test_different_users_can_each_like_same_post(self, client: TestClient):
        alice = _make_user(client, "alice")
        post = _make_post(client, alice["id"])
        bob = _make_user(client, "bob")
        carol = _make_user(client, "carol")
        dave = _make_user(client, "dave")

        for user in (bob, carol, dave):
            resp = client.post(f"/posts/{post['id']}/like", json={"user_id": user["id"]})
            assert resp.status_code == 201

        post_updated = client.get(f"/posts/{post['id']}").json()
        assert post_updated["likes_count"] == 3


# ===========================================================================
# Likes — DELETE /posts/{post_id}/like
# ===========================================================================

class TestUnlikePost:
    def test_unlike_returns_200(self, client: TestClient):
        alice = _make_user(client, "alice")
        post = _make_post(client, alice["id"])
        bob = _make_user(client, "bob")

        client.post(f"/posts/{post['id']}/like", json={"user_id": bob["id"]})
        resp = _delete_json(client, f"/posts/{post['id']}/like", {"user_id": bob["id"]})
        assert resp.status_code == 200

    def test_unlike_response_has_detail(self, client: TestClient):
        alice = _make_user(client, "alice")
        post = _make_post(client, alice["id"])
        bob = _make_user(client, "bob")

        client.post(f"/posts/{post['id']}/like", json={"user_id": bob["id"]})
        resp = _delete_json(client, f"/posts/{post['id']}/like", {"user_id": bob["id"]})
        assert "detail" in resp.json()

    def test_unlike_decrements_likes_count(self, client: TestClient):
        alice = _make_user(client, "alice")
        post = _make_post(client, alice["id"])
        bob = _make_user(client, "bob")

        client.post(f"/posts/{post['id']}/like", json={"user_id": bob["id"]})
        _delete_json(client, f"/posts/{post['id']}/like", {"user_id": bob["id"]})

        post_updated = client.get(f"/posts/{post['id']}").json()
        assert post_updated["likes_count"] == 0

    def test_unlike_count_does_not_go_below_zero(self, client: TestClient):
        alice = _make_user(client, "alice")
        post = _make_post(client, alice["id"])
        bob = _make_user(client, "bob")

        client.post(f"/posts/{post['id']}/like", json={"user_id": bob["id"]})
        _delete_json(client, f"/posts/{post['id']}/like", {"user_id": bob["id"]})
        _delete_json(client, f"/posts/{post['id']}/like", {"user_id": bob["id"]})  # 404

        post_updated = client.get(f"/posts/{post['id']}").json()
        assert post_updated["likes_count"] == 0

    def test_unlike_not_liked_returns_404(self, client: TestClient):
        alice = _make_user(client, "alice")
        post = _make_post(client, alice["id"])
        bob = _make_user(client, "bob")

        resp = _delete_json(client, f"/posts/{post['id']}/like", {"user_id": bob["id"]})
        assert resp.status_code == 404

    def test_unlike_only_removes_specific_users_like(self, client: TestClient):
        """When bob unlikes, carol's like on the same post should remain."""
        alice = _make_user(client, "alice")
        post = _make_post(client, alice["id"])
        bob = _make_user(client, "bob")
        carol = _make_user(client, "carol")

        client.post(f"/posts/{post['id']}/like", json={"user_id": bob["id"]})
        client.post(f"/posts/{post['id']}/like", json={"user_id": carol["id"]})

        _delete_json(client, f"/posts/{post['id']}/like", {"user_id": bob["id"]})

        post_updated = client.get(f"/posts/{post['id']}").json()
        assert post_updated["likes_count"] == 1

    def test_reliking_after_unlike_succeeds(self, client: TestClient):
        """User should be able to like a post again after unliking it."""
        alice = _make_user(client, "alice")
        post = _make_post(client, alice["id"])
        bob = _make_user(client, "bob")

        client.post(f"/posts/{post['id']}/like", json={"user_id": bob["id"]})
        _delete_json(client, f"/posts/{post['id']}/like", {"user_id": bob["id"]})
        resp = client.post(f"/posts/{post['id']}/like", json={"user_id": bob["id"]})
        assert resp.status_code == 201

        post_updated = client.get(f"/posts/{post['id']}").json()
        assert post_updated["likes_count"] == 1
