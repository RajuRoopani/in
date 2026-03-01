"""
Tests for the Feed domain.

Covers:
  - GET /feed/{user_id}  — personalised feed
  - Feed includes posts from followed users only
  - Feed includes reposted content from followed users
  - Deduplication (original wins over repost)
  - Newest-first ordering
  - Empty feed when following nobody
  - 404 for missing user
"""

import pytest
from fastapi.testclient import TestClient


class TestFeed:
    def _setup_social_graph(self, client, create_user):
        """Create alice (viewer), bob (followed), charlie (not followed)."""
        alice = create_user(username="alice")
        bob = create_user(username="bob")
        charlie = create_user(username="charlie")
        # alice follows bob only
        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": bob["id"]})
        return alice, bob, charlie

    def test_feed_returns_200(self, client: TestClient, create_user):
        alice = create_user(username="alice")
        resp = client.get(f"/feed/{alice['id']}")
        assert resp.status_code == 200

    def test_feed_empty_when_following_nobody(self, client: TestClient, create_user):
        alice = create_user(username="alice")
        resp = client.get(f"/feed/{alice['id']}")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_feed_missing_user_returns_404(self, client: TestClient):
        resp = client.get("/feed/ghost")
        assert resp.status_code == 404

    def test_feed_includes_posts_from_followed_users(self, client: TestClient, create_user):
        alice, bob, _ = self._setup_social_graph(client, create_user)
        client.post("/posts", json={"user_id": bob["id"], "content": "Bob's post"})

        feed = client.get(f"/feed/{alice['id']}").json()
        assert len(feed) == 1
        assert feed[0]["post"]["content"] == "Bob's post"
        assert feed[0]["reposted_by"] is None

    def test_feed_excludes_posts_from_unfollowed_users(self, client: TestClient, create_user):
        alice, bob, charlie = self._setup_social_graph(client, create_user)
        client.post("/posts", json={"user_id": charlie["id"], "content": "Charlie's post"})

        feed = client.get(f"/feed/{alice['id']}").json()
        assert len(feed) == 0

    def test_feed_includes_reposts_from_followed_users(self, client: TestClient, create_user):
        alice, bob, charlie = self._setup_social_graph(client, create_user)
        # Charlie creates a post, Bob reposts it
        post_resp = client.post("/posts", json={"user_id": charlie["id"], "content": "Original by charlie"})
        post_id = post_resp.json()["id"]
        client.post(f"/posts/{post_id}/repost", json={"user_id": bob["id"]})

        feed = client.get(f"/feed/{alice['id']}").json()
        assert len(feed) == 1
        assert feed[0]["post"]["content"] == "Original by charlie"
        assert feed[0]["reposted_by"] == bob["id"]

    def test_feed_deduplication_original_wins(self, client: TestClient, create_user):
        """If bob posts something AND reposts it (hypothetically), only original appears."""
        alice, bob, charlie = self._setup_social_graph(client, create_user)
        # Bob creates a post
        post_resp = client.post("/posts", json={"user_id": bob["id"], "content": "Bob original"})
        post_id = post_resp.json()["id"]
        # Charlie reposts it — but alice doesn't follow charlie, so this repost is invisible
        # Instead, let alice also follow charlie to test dedup
        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": charlie["id"]})
        client.post(f"/posts/{post_id}/repost", json={"user_id": charlie["id"]})

        feed = client.get(f"/feed/{alice['id']}").json()
        # Should appear only once (original from bob wins)
        post_ids = [item["post"]["id"] for item in feed]
        assert post_ids.count(post_id) == 1
        # The entry should be the original (reposted_by is None)
        matching = [item for item in feed if item["post"]["id"] == post_id]
        assert matching[0]["reposted_by"] is None

    def test_feed_newest_first_ordering(self, client: TestClient, create_user):
        alice, bob, _ = self._setup_social_graph(client, create_user)
        client.post("/posts", json={"user_id": bob["id"], "content": "first"})
        client.post("/posts", json={"user_id": bob["id"], "content": "second"})
        client.post("/posts", json={"user_id": bob["id"], "content": "third"})

        feed = client.get(f"/feed/{alice['id']}").json()
        assert len(feed) == 3
        contents = [item["post"]["content"] for item in feed]
        assert contents == ["third", "second", "first"]

    def test_feed_does_not_include_own_posts(self, client: TestClient, create_user):
        alice = create_user(username="alice")
        bob = create_user(username="bob")
        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": bob["id"]})
        # Alice's own post should NOT appear in her feed
        client.post("/posts", json={"user_id": alice["id"], "content": "My own post"})
        client.post("/posts", json={"user_id": bob["id"], "content": "Bob's post"})

        feed = client.get(f"/feed/{alice['id']}").json()
        contents = [item["post"]["content"] for item in feed]
        assert "My own post" not in contents
        assert "Bob's post" in contents

    def test_feed_multiple_followed_users(self, client: TestClient, create_user):
        alice = create_user(username="alice")
        bob = create_user(username="bob")
        charlie = create_user(username="charlie")
        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": bob["id"]})
        client.post(f"/users/{alice['id']}/follow", json={"target_user_id": charlie["id"]})

        client.post("/posts", json={"user_id": bob["id"], "content": "From Bob"})
        client.post("/posts", json={"user_id": charlie["id"], "content": "From Charlie"})

        feed = client.get(f"/feed/{alice['id']}").json()
        assert len(feed) == 2
        contents = {item["post"]["content"] for item in feed}
        assert contents == {"From Bob", "From Charlie"}
