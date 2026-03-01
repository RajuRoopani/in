"""
Follows router — AC15-AC19.

Endpoints:
  POST   /users/{user_id}/follow     Follow a user (400 self-follow, 409 already following)
  DELETE /users/{user_id}/follow     Unfollow a user (404 if not following)
  GET    /users/{user_id}/followers  List followers of a user (404 if user missing)
  GET    /users/{user_id}/following  List users that user_id follows (404 if user missing)
"""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, status

from in_app.models import FollowRequest, UnfollowRequest, UserOut
from in_app.storage import store

router = APIRouter(prefix="/users", tags=["follows"])


def _user_out(u: dict) -> UserOut:
    """Convert storage dict to typed UserOut."""
    return UserOut(**u)


@router.post("/{user_id}/follow", status_code=status.HTTP_201_CREATED)
def follow_user(user_id: str, body: FollowRequest) -> dict:
    """
    Follow *target_user_id* on behalf of *user_id*.

    Raises 404 if either user does not exist.
    Raises 400 if *user_id* == *target_user_id* (self-follow).
    Raises 409 if already following.
    """
    if user_id not in store.users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follower user not found.")
    if body.target_user_id not in store.users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found.")
    if user_id == body.target_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Users cannot follow themselves.",
        )

    pair = (user_id, body.target_user_id)
    if pair in store.follows:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already following this user.",
        )

    store.follows.add(pair)
    store.users[user_id]["following_count"] += 1
    store.users[body.target_user_id]["followers_count"] += 1

    return {
        "follower_id": user_id,
        "followed_id": body.target_user_id,
        "created_at": datetime.now(timezone.utc),
    }


@router.delete("/{user_id}/follow", status_code=status.HTTP_200_OK)
def unfollow_user(user_id: str, body: UnfollowRequest) -> dict:
    """
    Unfollow *target_user_id* on behalf of *user_id*.

    Raises 404 if the follow relationship does not exist.
    """
    pair = (user_id, body.target_user_id)
    if pair not in store.follows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Follow relationship not found.",
        )

    store.follows.discard(pair)
    store.users[user_id]["following_count"] = max(0, store.users[user_id]["following_count"] - 1)
    if body.target_user_id in store.users:
        store.users[body.target_user_id]["followers_count"] = max(
            0, store.users[body.target_user_id]["followers_count"] - 1
        )

    return {"detail": "Unfollowed successfully."}


@router.get("/{user_id}/followers", response_model=List[UserOut])
def list_followers(user_id: str) -> List[UserOut]:
    """
    Return all users who follow *user_id*.

    Raises 404 if the user does not exist.
    """
    if user_id not in store.users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    follower_ids = {follower for follower, followed in store.follows if followed == user_id}
    return [_user_out(store.users[uid]) for uid in follower_ids if uid in store.users]


@router.get("/{user_id}/following", response_model=List[UserOut])
def list_following(user_id: str) -> List[UserOut]:
    """
    Return all users that *user_id* is following.

    Raises 404 if the user does not exist.
    """
    if user_id not in store.users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    followed_ids = {followed for follower, followed in store.follows if follower == user_id}
    return [_user_out(store.users[uid]) for uid in followed_ids if uid in store.users]
