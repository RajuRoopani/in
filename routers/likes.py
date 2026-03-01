"""
Likes router — AC20-AC22.

Endpoints:
  POST   /posts/{post_id}/like   Like a post (409 double-like, 404 if post/user missing)
  DELETE /posts/{post_id}/like   Unlike a post (404 if not liked)
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from in_app.models import LikeRequest, LikeOut
from in_app.storage import store

router = APIRouter(prefix="/posts", tags=["likes"])


@router.post("/{post_id}/like", response_model=LikeOut, status_code=status.HTTP_201_CREATED)
def like_post(post_id: str, body: LikeRequest) -> LikeOut:
    """
    Like a post on behalf of *user_id*.

    Raises 404 if *post_id* or *user_id* does not exist.
    Raises 409 if the user has already liked this post.
    """
    if post_id not in store.posts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")
    if body.user_id not in store.users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    pair = (body.user_id, post_id)
    if pair in store.likes:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Post already liked by this user.",
        )

    store.likes.add(pair)
    store.posts[post_id]["likes_count"] += 1
    now = datetime.now(timezone.utc)

    return LikeOut(post_id=post_id, user_id=body.user_id, created_at=now)


@router.delete("/{post_id}/like", status_code=status.HTTP_200_OK)
def unlike_post(post_id: str, body: LikeRequest) -> dict:
    """
    Remove a like from a post.

    Raises 404 if the like does not exist.
    """
    pair = (body.user_id, post_id)
    if pair not in store.likes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Like not found.",
        )

    store.likes.discard(pair)
    if post_id in store.posts:
        store.posts[post_id]["likes_count"] = max(0, store.posts[post_id]["likes_count"] - 1)

    return {"detail": "Like removed."}
