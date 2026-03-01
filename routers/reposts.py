"""
Reposts router — AC27-AC29.

Endpoints:
  POST /posts/{post_id}/repost   Repost a post (409 double-repost, 404 post/user missing)
  GET  /posts/{post_id}/reposts  List users who reposted this post
"""

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, status

from in_app.models import RepostRequest, RepostOut, UserOut
from in_app.storage import store

router = APIRouter(prefix="/posts", tags=["reposts"])


@router.post(
    "/{post_id}/repost",
    response_model=RepostOut,
    status_code=status.HTTP_201_CREATED,
)
def repost(post_id: str, body: RepostRequest) -> RepostOut:
    """
    Repost *post_id* on behalf of *user_id*.

    Raises 404 if *post_id* or *user_id* does not exist.
    Raises 409 if the user has already reposted this post.
    """
    if post_id not in store.posts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")
    if body.user_id not in store.users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    pair = (body.user_id, post_id)
    if pair in store.reposts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Post already reposted by this user.",
        )

    store.reposts.add(pair)
    store.posts[post_id]["reposts_count"] += 1
    now = datetime.now(timezone.utc)

    return RepostOut(post_id=post_id, user_id=body.user_id, created_at=now)


@router.get("/{post_id}/reposts", response_model=List[UserOut])
def list_reposters(post_id: str) -> List[UserOut]:
    """
    List all users who have reposted *post_id*.

    Raises 404 if the post does not exist.
    """
    if post_id not in store.posts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

    reposter_ids = {uid for uid, pid in store.reposts if pid == post_id}
    return [UserOut(**store.users[uid]) for uid in reposter_ids if uid in store.users]
