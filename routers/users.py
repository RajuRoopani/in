"""
Users router — AC6-AC9.

Endpoints:
  POST   /users               Create a new user profile (409 on duplicate username)
  GET    /users/{user_id}     Fetch a user by ID (404 if missing)
  PUT    /users/{user_id}     Update display_name / bio / profile_picture_url (404 if missing)
"""

from datetime import datetime, timezone
from typing import List
import uuid

from fastapi import APIRouter, HTTPException, status

from in_app.models import UserCreate, UserOut, UserUpdate
from in_app.storage import store

router = APIRouter(prefix="/users", tags=["users"])


def _user_to_out(u: dict) -> UserOut:
    """Convert a raw storage dict to a typed UserOut."""
    return UserOut(**u)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate) -> UserOut:
    """
    Create a new user profile.

    Raises 409 if *username* is already taken.
    """
    # Duplicate username check
    for existing in store.users.values():
        if existing["username"] == body.username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Username '{body.username}' is already taken.",
            )

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    user = {
        "id": user_id,
        "username": body.username,
        "display_name": body.display_name,
        "bio": body.bio or "",
        "profile_picture_url": body.profile_picture_url or "",
        "followers_count": 0,
        "following_count": 0,
        "posts_count": 0,
        "created_at": now,
    }
    store.users[user_id] = user
    return _user_to_out(user)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str) -> UserOut:
    """
    Fetch a user profile by ID.

    Raises 404 if the user does not exist.
    """
    user = store.users.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return _user_to_out(user)


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: str, body: UserUpdate) -> UserOut:
    """
    Partially update a user profile.

    Only *display_name*, *bio*, and *profile_picture_url* may be changed.
    Raises 404 if the user does not exist.
    """
    user = store.users.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if body.display_name is not None:
        user["display_name"] = body.display_name
    if body.bio is not None:
        user["bio"] = body.bio
    if body.profile_picture_url is not None:
        user["profile_picture_url"] = body.profile_picture_url

    return _user_to_out(user)
