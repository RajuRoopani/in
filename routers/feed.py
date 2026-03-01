"""
Feed router — AC30-AC31.

Endpoints:
  GET /feed/{user_id}   Personalised feed: posts from followed users + their reposts,
                        newest first. Returns empty list (not an error) if user
                        follows nobody. Raises 404 if *user_id* doesn't exist.
"""

from typing import List

from fastapi import APIRouter, HTTPException, status

from in_app.models import FeedItem, PostOut, UserOut
from in_app.storage import store

router = APIRouter(prefix="/feed", tags=["feed"])


def _build_post_out(post: dict) -> PostOut:
    """Build a PostOut from a raw storage dict, attaching author info."""
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


@router.get("/{user_id}", response_model=List[FeedItem])
def get_feed(user_id: str) -> List[FeedItem]:
    """
    Build a personalised feed for *user_id*.

    Rules:
    - Include every post authored by a followed user.
    - Include every post reposted by a followed user (even if authored by a
      non-followed user), annotated with *reposted_by*.
    - Deduplicate: if a post appears as both an original and a repost, the
      original entry wins (repost entry is dropped).
    - Sort the combined list newest-first by the post's *created_at*.
    - Returns an empty list (not 404) when the user follows nobody.

    Raises 404 if *user_id* does not exist.
    """
    if user_id not in store.users:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    # Who does this user follow?
    followed_ids = {followed for follower, followed in store.follows if follower == user_id}

    if not followed_ids:
        return []

    # Collect feed items keyed by post_id to deduplicate
    feed_map: dict = {}

    # 1. Original posts from followed users (highest priority — wins dedup)
    for post in store.posts.values():
        if post["user_id"] in followed_ids:
            feed_map[post["id"]] = FeedItem(post=_build_post_out(post), reposted_by=None)

    # 2. Reposts by followed users (only add if post not already present as an original)
    for reposter_id, post_id in store.reposts:
        if reposter_id in followed_ids and post_id not in feed_map:
            post = store.posts.get(post_id)
            if post:
                feed_map[post_id] = FeedItem(
                    post=_build_post_out(post),
                    reposted_by=reposter_id,
                )

    # Sort newest-first by the post's own created_at
    items = sorted(feed_map.values(), key=lambda fi: fi.post.created_at, reverse=True)
    return items
