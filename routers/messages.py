"""
Messages (DM) router — AC32-AC34.

Endpoints:
  POST /messages                              Send a direct message (400 empty text, 404 unknown user)
  GET  /messages/{user_id}/{other_user_id}    Get conversation chronologically (oldest first)
"""

from datetime import datetime, timezone
from typing import List
import uuid

from fastapi import APIRouter, HTTPException, status

from in_app.models import MessageCreate, MessageOut
from in_app.storage import store

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send_message(body: MessageCreate) -> MessageOut:
    """
    Send a direct message from *sender_id* to *receiver_id*.

    Raises 404 if either user does not exist.
    Raises 400 if *text* is empty or whitespace-only.
    """
    if body.sender_id not in store.users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sender not found.")
    if body.receiver_id not in store.users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receiver not found.")
    if not body.text or not body.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message text cannot be empty.",
        )

    msg_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    msg = {
        "id": msg_id,
        "sender_id": body.sender_id,
        "receiver_id": body.receiver_id,
        "text": body.text,
        "created_at": now,
    }
    store.messages.append(msg)
    return MessageOut(**msg)


@router.get("/{user_id}/{other_user_id}", response_model=List[MessageOut])
def get_conversation(user_id: str, other_user_id: str) -> List[MessageOut]:
    """
    Retrieve the conversation between *user_id* and *other_user_id* in
    chronological order (oldest message first).

    Does not raise 404 for unknown users — returns empty list when no messages exist.
    """
    pair = {user_id, other_user_id}
    convo = [
        m for m in store.messages
        if {m["sender_id"], m["receiver_id"]} == pair
    ]
    convo.sort(key=lambda m: m["created_at"])  # oldest first = chronological
    return [MessageOut(**m) for m in convo]
