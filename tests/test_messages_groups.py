"""
Comprehensive tests for Messages (DMs) and Groups features.

Tests for AC34-AC46:
- AC34-AC37: Messages (DMs)
- AC38-AC46: Groups
"""

import pytest
from datetime import datetime


# ===== MESSAGES TESTS =====

class TestSendMessage:
    """Tests for POST /messages."""

    def test_send_message_success(self, client, create_user):
        """Send a DM from one user to another — 201."""
        alice = create_user(username="alice", display_name="Alice")
        bob = create_user(username="bob", display_name="Bob")

        resp = client.post("/messages", json={
            "sender_id": alice["id"],
            "receiver_id": bob["id"],
            "text": "Hello Bob!",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["sender_id"] == alice["id"]
        assert data["receiver_id"] == bob["id"]
        assert data["text"] == "Hello Bob!"
        assert "id" in data
        assert "created_at" in data

    def test_send_message_to_self_allowed(self, client, create_user):
        """Send DM to self — allowed (201)."""
        alice = create_user(username="alice", display_name="Alice")

        resp = client.post("/messages", json={
            "sender_id": alice["id"],
            "receiver_id": alice["id"],
            "text": "Talk to myself",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["sender_id"] == alice["id"]
        assert data["receiver_id"] == alice["id"]

    def test_send_message_empty_text_400(self, client, create_user):
        """Send DM with empty text — 400."""
        alice = create_user(username="alice", display_name="Alice")
        bob = create_user(username="bob", display_name="Bob")

        resp = client.post("/messages", json={
            "sender_id": alice["id"],
            "receiver_id": bob["id"],
            "text": "",
        })
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    def test_send_message_whitespace_only_400(self, client, create_user):
        """Send DM with only whitespace — 400."""
        alice = create_user(username="alice", display_name="Alice")
        bob = create_user(username="bob", display_name="Bob")

        resp = client.post("/messages", json={
            "sender_id": alice["id"],
            "receiver_id": bob["id"],
            "text": "   \t\n  ",
        })
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    def test_send_message_missing_sender_404(self, client, create_user):
        """Send DM from non-existent user — 404."""
        bob = create_user(username="bob", display_name="Bob")
        fake_sender_id = "nonexistent-user-id"

        resp = client.post("/messages", json={
            "sender_id": fake_sender_id,
            "receiver_id": bob["id"],
            "text": "Hello",
        })
        assert resp.status_code == 404
        assert "sender" in resp.json()["detail"].lower()

    def test_send_message_missing_receiver_404(self, client, create_user):
        """Send DM to non-existent user — 404."""
        alice = create_user(username="alice", display_name="Alice")
        fake_receiver_id = "nonexistent-user-id"

        resp = client.post("/messages", json={
            "sender_id": alice["id"],
            "receiver_id": fake_receiver_id,
            "text": "Hello",
        })
        assert resp.status_code == 404
        assert "receiver" in resp.json()["detail"].lower()


class TestGetConversation:
    """Tests for GET /messages/{user1_id}/{user2_id}."""

    def test_get_conversation_single_message(self, client, create_user):
        """Get conversation with one message — 200, newest-first order."""
        alice = create_user(username="alice", display_name="Alice")
        bob = create_user(username="bob", display_name="Bob")

        # Send one message
        msg_resp = client.post("/messages", json={
            "sender_id": alice["id"],
            "receiver_id": bob["id"],
            "text": "First message",
        })
        assert msg_resp.status_code == 201

        # Retrieve conversation
        resp = client.get(f"/messages/{alice['id']}/{bob['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["text"] == "First message"
        assert data[0]["sender_id"] == alice["id"]

    def test_get_conversation_multiple_messages_oldest_first(self, client, create_user):
        """Get conversation with multiple messages — ordered oldest-first (chronological)."""
        alice = create_user(username="alice", display_name="Alice")
        bob = create_user(username="bob", display_name="Bob")

        # Send messages in order: msg1, msg2, msg3
        for i in range(1, 4):
            client.post("/messages", json={
                "sender_id": alice["id"],
                "receiver_id": bob["id"],
                "text": f"Message {i}",
            })

        # Get conversation
        resp = client.get(f"/messages/{alice['id']}/{bob['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        # Should be oldest first (chronological): msg1, msg2, msg3
        assert data[0]["text"] == "Message 1"
        assert data[1]["text"] == "Message 2"
        assert data[2]["text"] == "Message 3"

    def test_get_conversation_bidirectional(self, client, create_user):
        """Conversation includes messages in both directions (A→B and B→A)."""
        alice = create_user(username="alice", display_name="Alice")
        bob = create_user(username="bob", display_name="Bob")

        # Alice -> Bob
        client.post("/messages", json={
            "sender_id": alice["id"],
            "receiver_id": bob["id"],
            "text": "Alice to Bob",
        })

        # Bob -> Alice
        client.post("/messages", json={
            "sender_id": bob["id"],
            "receiver_id": alice["id"],
            "text": "Bob to Alice",
        })

        # Get conversation from Alice's perspective
        resp = client.get(f"/messages/{alice['id']}/{bob['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        texts = {m["text"] for m in data}
        assert "Alice to Bob" in texts
        assert "Bob to Alice" in texts

    def test_get_conversation_bidirectional_reverse_order(self, client, create_user):
        """Conversation is same regardless of user order in URL."""
        alice = create_user(username="alice", display_name="Alice")
        bob = create_user(username="bob", display_name="Bob")

        # Send message both directions
        client.post("/messages", json={
            "sender_id": alice["id"],
            "receiver_id": bob["id"],
            "text": "Alice to Bob",
        })
        client.post("/messages", json={
            "sender_id": bob["id"],
            "receiver_id": alice["id"],
            "text": "Bob to Alice",
        })

        # Get from both perspectives
        resp1 = client.get(f"/messages/{alice['id']}/{bob['id']}")
        resp2 = client.get(f"/messages/{bob['id']}/{alice['id']}")

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert len(resp1.json()) == 2
        assert len(resp2.json()) == 2

    def test_get_conversation_missing_user1_returns_empty(self, client, create_user):
        """Get conversation with non-existent user1 — returns empty list (200)."""
        bob = create_user(username="bob", display_name="Bob")
        fake_id = "nonexistent-id"

        resp = client.get(f"/messages/{fake_id}/{bob['id']}")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_conversation_missing_user2_returns_empty(self, client, create_user):
        """Get conversation with non-existent user2 — returns empty list (200)."""
        alice = create_user(username="alice", display_name="Alice")
        fake_id = "nonexistent-id"

        resp = client.get(f"/messages/{alice['id']}/{fake_id}")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_conversation_no_messages(self, client, create_user):
        """Get conversation between users with no messages — returns empty list."""
        alice = create_user(username="alice", display_name="Alice")
        bob = create_user(username="bob", display_name="Bob")

        resp = client.get(f"/messages/{alice['id']}/{bob['id']}")
        assert resp.status_code == 200
        assert resp.json() == []


# ===== GROUPS TESTS =====

class TestCreateGroup:
    """Tests for POST /groups."""

    def test_create_group_success(self, client, create_user):
        """Create a group — 201, creator auto-added to members."""
        alice = create_user(username="alice", display_name="Alice")
        bob = create_user(username="bob", display_name="Bob")

        resp = client.post("/groups", json={
            "name": "Chat Room",
            "creator_id": alice["id"],
            "member_ids": [bob["id"]],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Chat Room"
        assert data["creator_id"] == alice["id"]
        # Creator should be auto-added
        assert alice["id"] in data["member_ids"]
        assert bob["id"] in data["member_ids"]
        assert len(data["member_ids"]) == 2
        assert "id" in data
        assert "created_at" in data

    def test_create_group_creator_only(self, client, create_user):
        """Create a group with no initial members — creator is the only member."""
        alice = create_user(username="alice", display_name="Alice")

        resp = client.post("/groups", json={
            "name": "Solo Group",
            "creator_id": alice["id"],
            "member_ids": [],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["member_ids"] == [alice["id"]]

    def test_create_group_empty_name_400(self, client, create_user):
        """Create group with empty name — 400."""
        alice = create_user(username="alice", display_name="Alice")

        resp = client.post("/groups", json={
            "name": "",
            "creator_id": alice["id"],
            "member_ids": [],
        })
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    def test_create_group_whitespace_name_400(self, client, create_user):
        """Create group with whitespace-only name — 400."""
        alice = create_user(username="alice", display_name="Alice")

        resp = client.post("/groups", json={
            "name": "   \t\n  ",
            "creator_id": alice["id"],
            "member_ids": [],
        })
        assert resp.status_code == 400

    def test_create_group_missing_creator_404(self, client):
        """Create group with non-existent creator — 404."""
        fake_creator_id = "nonexistent-user-id"

        resp = client.post("/groups", json={
            "name": "Test Group",
            "creator_id": fake_creator_id,
            "member_ids": [],
        })
        assert resp.status_code == 404
        assert "creator" in resp.json()["detail"].lower()

    def test_create_group_missing_member_404(self, client, create_user):
        """Create group with non-existent member — 404."""
        alice = create_user(username="alice", display_name="Alice")
        fake_member_id = "nonexistent-user-id"

        resp = client.post("/groups", json={
            "name": "Test Group",
            "creator_id": alice["id"],
            "member_ids": [fake_member_id],
        })
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_create_group_deduplicates_creator(self, client, create_user):
        """Create group with creator in member_ids — deduplicates."""
        alice = create_user(username="alice", display_name="Alice")

        resp = client.post("/groups", json={
            "name": "Test Group",
            "creator_id": alice["id"],
            "member_ids": [alice["id"]],  # Creator listed twice
        })
        assert resp.status_code == 201
        data = resp.json()
        # Should have creator only once
        assert data["member_ids"].count(alice["id"]) == 1


class TestGetGroup:
    """Tests for GET /groups/{group_id}."""

    def test_get_group_success(self, client, create_user):
        """Get group details — 200."""
        alice = create_user(username="alice", display_name="Alice")
        bob = create_user(username="bob", display_name="Bob")

        create_resp = client.post("/groups", json={
            "name": "Test Group",
            "creator_id": alice["id"],
            "member_ids": [bob["id"]],
        })
        group_id = create_resp.json()["id"]

        resp = client.get(f"/groups/{group_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test Group"
        assert data["creator_id"] == alice["id"]
        assert bob["id"] in data["member_ids"]

    def test_get_group_missing_404(self, client):
        """Get non-existent group — 404."""
        fake_group_id = "nonexistent-group-id"

        resp = client.get(f"/groups/{fake_group_id}")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


class TestAddMember:
    """Tests for POST /groups/{group_id}/members."""

    def test_add_member_success(self, client, create_user):
        """Add a member to a group — 200."""
        alice = create_user(username="alice", display_name="Alice")
        bob = create_user(username="bob", display_name="Bob")
        charlie = create_user(username="charlie", display_name="Charlie")

        create_resp = client.post("/groups", json={
            "name": "Test Group",
            "creator_id": alice["id"],
            "member_ids": [bob["id"]],
        })
        group_id = create_resp.json()["id"]

        # Add Charlie
        resp = client.post(f"/groups/{group_id}/members", json={
            "user_id": charlie["id"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert charlie["id"] in data["member_ids"]
        assert len(data["member_ids"]) == 3  # Alice, Bob, Charlie

    def test_add_member_duplicate_409(self, client, create_user):
        """Add a member who is already in the group — 409."""
        alice = create_user(username="alice", display_name="Alice")
        bob = create_user(username="bob", display_name="Bob")

        create_resp = client.post("/groups", json={
            "name": "Test Group",
            "creator_id": alice["id"],
            "member_ids": [bob["id"]],
        })
        group_id = create_resp.json()["id"]

        # Try to add Bob again
        resp = client.post(f"/groups/{group_id}/members", json={
            "user_id": bob["id"],
        })
        assert resp.status_code == 409
        assert "already a member" in resp.json()["detail"].lower()

    def test_add_member_missing_group_404(self, client, create_user):
        """Add member to non-existent group — 404."""
        alice = create_user(username="alice", display_name="Alice")
        fake_group_id = "nonexistent-group-id"

        resp = client.post(f"/groups/{fake_group_id}/members", json={
            "user_id": alice["id"],
        })
        assert resp.status_code == 404
        assert "group" in resp.json()["detail"].lower()

    def test_add_member_missing_user_404(self, client, create_user):
        """Add non-existent user to group — 404."""
        alice = create_user(username="alice", display_name="Alice")

        create_resp = client.post("/groups", json={
            "name": "Test Group",
            "creator_id": alice["id"],
            "member_ids": [],
        })
        group_id = create_resp.json()["id"]

        fake_user_id = "nonexistent-user-id"
        resp = client.post(f"/groups/{group_id}/members", json={
            "user_id": fake_user_id,
        })
        assert resp.status_code == 404
        assert "user" in resp.json()["detail"].lower()


class TestRemoveMember:
    """Tests for DELETE /groups/{group_id}/members."""

    def test_remove_member_success(self, client, create_user):
        """Remove a member from a group — 200."""
        alice = create_user(username="alice", display_name="Alice")
        bob = create_user(username="bob", display_name="Bob")
        charlie = create_user(username="charlie", display_name="Charlie")

        create_resp = client.post("/groups", json={
            "name": "Test Group",
            "creator_id": alice["id"],
            "member_ids": [bob["id"], charlie["id"]],
        })
        group_id = create_resp.json()["id"]

        # Remove Bob
        resp = client.request("DELETE", f"/groups/{group_id}/members", json={
            "user_id": bob["id"],
        })
        assert resp.status_code == 200

        # Verify Bob is gone
        get_resp = client.get(f"/groups/{group_id}")
        assert bob["id"] not in get_resp.json()["member_ids"]

    def test_remove_member_not_member_404(self, client, create_user):
        """Remove non-member from group — 404."""
        alice = create_user(username="alice", display_name="Alice")
        bob = create_user(username="bob", display_name="Bob")

        create_resp = client.post("/groups", json={
            "name": "Test Group",
            "creator_id": alice["id"],
            "member_ids": [],
        })
        group_id = create_resp.json()["id"]

        # Try to remove Bob (who was never added)
        resp = client.request("DELETE", f"/groups/{group_id}/members", json={
            "user_id": bob["id"],
        })
        assert resp.status_code == 404
        assert "not a member" in resp.json()["detail"].lower()


class TestSendGroupMessage:
    """Tests for POST /groups/{group_id}/messages."""

    def test_send_group_message_success(self, client, create_user):
        """Send a message to a group — 201."""
        alice = create_user(username="alice", display_name="Alice")
        bob = create_user(username="bob", display_name="Bob")

        create_resp = client.post("/groups", json={
            "name": "Test Group",
            "creator_id": alice["id"],
            "member_ids": [bob["id"]],
        })
        group_id = create_resp.json()["id"]

        # Alice sends message
        resp = client.post(f"/groups/{group_id}/messages", json={
            "sender_id": alice["id"],
            "text": "Hello group!",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["group_id"] == group_id
        assert data["sender_id"] == alice["id"]
        assert data["text"] == "Hello group!"
        assert "id" in data
        assert "created_at" in data

    def test_send_group_message_non_member_403(self, client, create_user):
        """Send group message as non-member — 403."""
        alice = create_user(username="alice", display_name="Alice")
        bob = create_user(username="bob", display_name="Bob")
        charlie = create_user(username="charlie", display_name="Charlie")

        create_resp = client.post("/groups", json={
            "name": "Test Group",
            "creator_id": alice["id"],
            "member_ids": [bob["id"]],
        })
        group_id = create_resp.json()["id"]

        # Charlie (not a member) tries to send
        resp = client.post(f"/groups/{group_id}/messages", json={
            "sender_id": charlie["id"],
            "text": "Hello",
        })
        assert resp.status_code == 403
        assert "not a member" in resp.json()["detail"].lower()

    def test_send_group_message_empty_text_400(self, client, create_user):
        """Send group message with empty text — 400."""
        alice = create_user(username="alice", display_name="Alice")

        create_resp = client.post("/groups", json={
            "name": "Test Group",
            "creator_id": alice["id"],
            "member_ids": [],
        })
        group_id = create_resp.json()["id"]

        resp = client.post(f"/groups/{group_id}/messages", json={
            "sender_id": alice["id"],
            "text": "",
        })
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    def test_send_group_message_whitespace_only_400(self, client, create_user):
        """Send group message with whitespace-only text — 400."""
        alice = create_user(username="alice", display_name="Alice")

        create_resp = client.post("/groups", json={
            "name": "Test Group",
            "creator_id": alice["id"],
            "member_ids": [],
        })
        group_id = create_resp.json()["id"]

        resp = client.post(f"/groups/{group_id}/messages", json={
            "sender_id": alice["id"],
            "text": "   \t\n  ",
        })
        assert resp.status_code == 400

    def test_send_group_message_missing_group_404(self, client, create_user):
        """Send message to non-existent group — 404."""
        alice = create_user(username="alice", display_name="Alice")
        fake_group_id = "nonexistent-group-id"

        resp = client.post(f"/groups/{fake_group_id}/messages", json={
            "sender_id": alice["id"],
            "text": "Hello",
        })
        assert resp.status_code == 404
        assert "group" in resp.json()["detail"].lower()


class TestListGroupMessages:
    """Tests for GET /groups/{group_id}/messages."""

    def test_list_group_messages_single(self, client, create_user):
        """List group messages with one message — 200."""
        alice = create_user(username="alice", display_name="Alice")

        create_resp = client.post("/groups", json={
            "name": "Test Group",
            "creator_id": alice["id"],
            "member_ids": [],
        })
        group_id = create_resp.json()["id"]

        # Send one message
        client.post(f"/groups/{group_id}/messages", json={
            "sender_id": alice["id"],
            "text": "First message",
        })

        resp = client.get(f"/groups/{group_id}/messages")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["text"] == "First message"

    def test_list_group_messages_newest_first(self, client, create_user):
        """List group messages — newest-first order."""
        alice = create_user(username="alice", display_name="Alice")
        bob = create_user(username="bob", display_name="Bob")

        create_resp = client.post("/groups", json={
            "name": "Test Group",
            "creator_id": alice["id"],
            "member_ids": [bob["id"]],
        })
        group_id = create_resp.json()["id"]

        # Send messages in order
        for i in range(1, 4):
            client.post(f"/groups/{group_id}/messages", json={
                "sender_id": alice["id"] if i % 2 == 1 else bob["id"],
                "text": f"Message {i}",
            })

        resp = client.get(f"/groups/{group_id}/messages")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        # Should be newest first: msg3, msg2, msg1
        assert data[0]["text"] == "Message 3"
        assert data[1]["text"] == "Message 2"
        assert data[2]["text"] == "Message 1"

    def test_list_group_messages_empty(self, client, create_user):
        """List group messages when none exist — returns empty list."""
        alice = create_user(username="alice", display_name="Alice")

        create_resp = client.post("/groups", json={
            "name": "Test Group",
            "creator_id": alice["id"],
            "member_ids": [],
        })
        group_id = create_resp.json()["id"]

        resp = client.get(f"/groups/{group_id}/messages")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_group_messages_missing_group_404(self, client):
        """List messages for non-existent group — 404."""
        fake_group_id = "nonexistent-group-id"

        resp = client.get(f"/groups/{fake_group_id}/messages")
        assert resp.status_code == 404
        assert "group" in resp.json()["detail"].lower()
