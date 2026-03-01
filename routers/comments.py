"""
Comments router — AC23-AC26.

Endpoints:
  POST   /posts/{post_id}/comments   Add a comment (400 empty text, 404 post/user missing)
  GET    /posts/{post_id}/comments   List comments, newest first
  DELETE /comments/{comment_id}      Delete a comment (404 if missing), decrement post count
"""

from datetime import datetime, timezone
from typing import List
import uuid

from fastapi import APIRouter, HTTPException, status

from in_app.models import CommentCreate, CommentOut
from in_app.storage import store

router = APIRouter(tags=["comments"])


@router.post(
    "/posts/{post_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
def add_comment(post_id: str, body: CommentCreate) -> CommentOut:
    """
    Add a comment to *post_id*.

    Raises 404 if *post_id* or *user_id* does not exist.
    Raises 400 if *text* is empty or whitespace-only.
    """
    if post_id not in store.posts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")
    if body.user_id not in store.users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if not body.text or not body.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comment text cannot be empty.",
        )

    comment_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    comment = {
        "id": comment_id,
        "post_id": post_id,
        "user_id": body.user_id,
        "text": body.text,
        "created_at": now,
    }
    store.comments[comment_id] = comment
    store.posts[post_id]["comments_count"] += 1

    return CommentOut(**comment)


@router.get("/posts/{post_id}/comments", response_model=List[CommentOut])
def list_comments(post_id: str) -> List[CommentOut]:
    """
    List all comments on *post_id*, newest first.

    Raises 404 if the post does not exist.
    """
    if post_id not in store.posts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

    post_comments = [c for c in store.comments.values() if c["post_id"] == post_id]
    post_comments.sort(key=lambda c: c["created_at"], reverse=True)
    return [CommentOut(**c) for c in post_comments]


@router.delete("/comments/{comment_id}", status_code=status.HTTP_200_OK)
def delete_comment(comment_id: str) -> dict:
    """
    Delete a comment by ID and decrement the parent post's comments_count.

    Raises 404 if the comment does not exist.
    """
    comment = store.comments.get(comment_id)
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found.")

    post_id = comment["post_id"]
    del store.comments[comment_id]

    if post_id in store.posts:
        store.posts[post_id]["comments_count"] = max(
            0, store.posts[post_id]["comments_count"] - 1
        )

    return {"detail": "Comment deleted."}
