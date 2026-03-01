"""
Entry point for the 'in' social media platform API.

Start with:
    uvicorn in_app.main:app --reload

All routers are registered here with their canonical prefixes.
Route ordering: routers that share a URL prefix are included in a fixed order
so that FastAPI's top-to-bottom path matching resolves ambiguities correctly.
"""

from fastapi import FastAPI

from in_app.routers import (
    comments,
    feed,
    follows,
    groups,
    likes,
    messages,
    posts,
    reposts,
    users,
)

app = FastAPI(
    title="in — Social Media Platform",
    description=(
        "RESTful API for the 'in' social media platform. "
        "Supports user profiles, posts, follows, likes, comments, reposts, "
        "personalised feeds, direct messages, and group chats."
    ),
    version="1.0.0",
)

# ── Router registration ────────────────────────────────────────────────────────
#
# IMPORTANT: routers that share a URL prefix must be registered in the correct
# order so that static path segments are evaluated before dynamic ones.
# FastAPI resolves routes top-to-bottom within the include list.
#
# Prefix ownership:
#   /users    → users.router (CRUD)
#               follows.router (follow ops + follower/following lists)
#               posts.router   (GET /users/{id}/posts)
#   /posts    → posts.router (CRUD)
#               likes.router, comments.router, reposts.router
#   /comments → comments.router (DELETE /comments/{id})
#   /feed     → feed.router
#   /messages → messages.router
#   /groups   → groups.router

app.include_router(users.router)
app.include_router(follows.router)    # /users/{id}/follow*, /users/{id}/followers|following
app.include_router(posts.router)      # /posts + /users/{id}/posts
app.include_router(likes.router)      # /posts/{id}/like
app.include_router(comments.router)   # /posts/{id}/comments + /comments/{id}
app.include_router(reposts.router)    # /posts/{id}/repost(s)
app.include_router(feed.router)
app.include_router(messages.router)
app.include_router(groups.router)


@app.get("/", tags=["health"])
def health_check() -> dict:
    """Liveness probe — returns platform name and version."""
    return {"platform": "in", "version": "1.0.0", "status": "ok"}
