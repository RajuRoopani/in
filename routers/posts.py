"""
Posts router — AC10-AC14.

Endpoints:
  POST   /posts                    Create a post (400 if content > 500 chars, 404 if user missing)
  GET    /posts/{post_id}          Fetch post with author info (404 if missing)
  GET    /users/{user_id}/posts    List posts by user, newest first (404 if user missing)
  DELETE /posts/{post_id}          Delete post + cascade likes/comments/reposts (404 if missing)
"""

from datetime import datetime, timezone
from typing import List
import uuid

from fastapi import APIRouter, HTTPException, status

from in_app.models import PostCreate, PostOut, UserOut
from in_app.storage import store

router = APIRouter(tags=["posts"])

_MAX_CONTENT_LEN = 500


def _build_post_out(post: dict) -> PostOut:
    """Attach author info and return a typed PostOut."""
    author_raw = store.users.get(post["user_id"])
    author = UserOut(**author_raw) if author_raw else None
    return PostOut(
        id=post["id"],
        user_id=post["user_id"],
        author=author,
        content=post["content"],
        media_url=post.get("media_url"),
        media_type=post.get("media_type"),
        likes_count=post["likes_count"],
        comments_count=post["comments_count"],
        reposts_count=post["reposts_count"],
        created_at=post["created_at"],
    )


# ── /posts prefix ────────────────────────────────────────────────────────────

@router.post("/posts", response_model=PostOut, status_code=status.HTTP_201_CREATED)
def create_post(body: PostCreate) -> PostOut:
    """
    Create a new post.

    Raises 404 if *user_id* does not exist.
    Raises 400 if *content* exceeds 500 characters.
    """
    if body.user_id not in store.users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if len(body.content) > _MAX_CONTENT_LEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Post content exceeds {_MAX_CONTENT_LEN} characters.",
        )

    post_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    post = {
        "id": post_id,
        "user_id": body.user_id,
        "content": body.content,
        "media_url": body.media_url,
        "media_type": body.media_type,
        "likes_count": 0,
        "comments_count": 0,
        "reposts_count": 0,
        "created_at": now,
    }
    store.posts[post_id] = post
    store.users[body.user_id]["posts_count"] += 1
    return _build_post_out(post)


@router.get("/posts/{post_id}", response_model=PostOut)
def get_post(post_id: str) -> PostOut:
    """
    Fetch a single post (with author info).

    Raises 404 if the post does not exist.
    """
    post = store.posts.get(post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")
    return _build_post_out(post)


@router.delete("/posts/{post_id}", status_code=status.HTTP_200_OK)
def delete_post(post_id: str) -> dict:
    """
    Delete a post and cascade-remove all associated likes, comments, and reposts.

    Raises 404 if the post does not exist.
    """
    post = store.posts.get(post_id)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

    # Decrement author post count
    author_id = post["user_id"]
    if author_id in store.users:
        store.users[author_id]["posts_count"] = max(
            0, store.users[author_id]["posts_count"] - 1
        )

    # Cascade: remove likes, reposts, comments for this post
    store.likes = {pair for pair in store.likes if pair[1] != post_id}
    store.reposts = {pair for pair in store.reposts if pair[1] != post_id}
    store.comments = {
        cid: c for cid, c in store.comments.items() if c["post_id"] != post_id
    }

    del store.posts[post_id]
    return {"detail": "Post deleted."}


# ── /users prefix ─────────────────────────────────────────────────────────────

@router.get("/users/{user_id}/posts", response_model=List[PostOut])
def list_user_posts(user_id: str) -> List[PostOut]:
    """
    List all posts by a user, newest first.

    Raises 404 if the user does not exist.
    """
    if user_id not in store.users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user_posts = [p for p in store.posts.values() if p["user_id"] == user_id]
    user_posts.sort(key=lambda p: p["created_at"], reverse=True)
    return [_build_post_out(p) for p in user_posts]
