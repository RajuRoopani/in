"""
Groups router — AC38-AC46.

Endpoints:
  POST   /groups                          Create a group
  GET    /groups/{group_id}               Get group details
  POST   /groups/{group_id}/members       Add a member
  DELETE /groups/{group_id}/members       Remove a member
  POST   /groups/{group_id}/messages      Send a group message
  GET    /groups/{group_id}/messages      List group messages, newest first
"""

from datetime import datetime, timezone
from typing import List
import uuid

from fastapi import APIRouter, HTTPException, status

from in_app.models import (
    GroupCreate,
    GroupOut,
    GroupMessageCreate,
    GroupMessageOut,
    AddMemberRequest,
)
from in_app.storage import store

router = APIRouter(prefix="/groups", tags=["groups"])


@router.post("", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(body: GroupCreate) -> GroupOut:
    """
    Create a new group.

    The creator is automatically added to the member list.
    Raises 404 if the creator does not exist.
    Raises 400 if the group name is empty.
    """
    if body.creator_id not in store.users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creator user not found.")
    if not body.name or not body.name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Group name cannot be empty.",
        )

    group_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Ensure creator is in member list, deduplicate
    member_ids = list(set([body.creator_id] + body.member_ids))

    # Validate all initial members exist
    for mid in member_ids:
        if mid not in store.users:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Member user '{mid}' not found.",
            )

    group = {
        "id": group_id,
        "name": body.name,
        "creator_id": body.creator_id,
        "member_ids": member_ids,
        "created_at": now,
    }
    store.groups[group_id] = group
    store.group_messages[group_id] = []
    return GroupOut(**group)


@router.get("/{group_id}", response_model=GroupOut)
def get_group(group_id: str) -> GroupOut:
    """
    Get group details by ID.

    Raises 404 if the group does not exist.
    """
    group = store.groups.get(group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")
    return GroupOut(**group)


@router.post("/{group_id}/members", response_model=GroupOut, status_code=status.HTTP_200_OK)
def add_member(group_id: str, body: AddMemberRequest) -> GroupOut:
    """
    Add a user to a group.

    Raises 404 if the group or user does not exist.
    Raises 409 if the user is already a member.
    """
    group = store.groups.get(group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")
    if body.user_id not in store.users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if body.user_id in group["member_ids"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this group.",
        )

    group["member_ids"].append(body.user_id)
    return GroupOut(**group)


@router.delete("/{group_id}/members", status_code=status.HTTP_200_OK)
def remove_member(group_id: str, body: AddMemberRequest) -> dict:
    """
    Remove a user from a group.

    Raises 404 if the group or the membership does not exist.
    """
    group = store.groups.get(group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")
    if body.user_id not in group["member_ids"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this group.",
        )

    group["member_ids"].remove(body.user_id)
    return {"detail": "Member removed."}


@router.post(
    "/{group_id}/messages",
    response_model=GroupMessageOut,
    status_code=status.HTTP_201_CREATED,
)
def send_group_message(group_id: str, body: GroupMessageCreate) -> GroupMessageOut:
    """
    Send a message to a group.

    Raises 404 if the group does not exist.
    Raises 403 if the sender is not a member of the group.
    Raises 400 if text is empty.
    """
    group = store.groups.get(group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")
    if body.sender_id not in group["member_ids"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sender is not a member of this group.",
        )
    if not body.text or not body.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message text cannot be empty.",
        )

    msg_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    msg = {
        "id": msg_id,
        "group_id": group_id,
        "sender_id": body.sender_id,
        "text": body.text,
        "created_at": now,
    }
    store.group_messages[group_id].append(msg)
    return GroupMessageOut(**msg)


@router.get("/{group_id}/messages", response_model=List[GroupMessageOut])
def list_group_messages(group_id: str) -> List[GroupMessageOut]:
    """
    List all messages in a group, newest first.

    Raises 404 if the group does not exist.
    """
    group = store.groups.get(group_id)
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")

    msgs = store.group_messages.get(group_id, [])
    msgs_sorted = sorted(msgs, key=lambda m: m["created_at"], reverse=True)
    return [GroupMessageOut(**m) for m in msgs_sorted]
