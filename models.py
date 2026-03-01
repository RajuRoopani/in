"""
Pydantic request/response schemas for the 'in' social media platform.

Every endpoint accepts a typed request body and returns a typed response —
no raw dicts escape the router layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    username: str
    display_name: str
    bio: Optional[str] = ""
    profile_picture_url: Optional[str] = ""


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    profile_picture_url: Optional[str] = None


class UserOut(BaseModel):
    id: str
    username: str
    display_name: str
    bio: str
    profile_picture_url: str
    followers_count: int
    following_count: int
    posts_count: int
    created_at: datetime


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------

class PostCreate(BaseModel):
    user_id: str
    content: str
    media_url: Optional[str] = None
    media_type: Optional[str] = None


class PostOut(BaseModel):
    id: str
    user_id: str
    author: Optional[UserOut] = None
    content: str
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    likes_count: int
    comments_count: int
    reposts_count: int
    created_at: datetime


# ---------------------------------------------------------------------------
# Follows
# ---------------------------------------------------------------------------

class FollowRequest(BaseModel):
    target_user_id: str


class UnfollowRequest(BaseModel):
    target_user_id: str


# ---------------------------------------------------------------------------
# Likes
# ---------------------------------------------------------------------------

class LikeRequest(BaseModel):
    user_id: str


class LikeOut(BaseModel):
    post_id: str
    user_id: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

class CommentCreate(BaseModel):
    user_id: str
    text: str


class CommentOut(BaseModel):
    id: str
    post_id: str
    user_id: str
    text: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Reposts
# ---------------------------------------------------------------------------

class RepostRequest(BaseModel):
    user_id: str


class RepostOut(BaseModel):
    post_id: str
    user_id: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Feed
# ---------------------------------------------------------------------------

class FeedItem(BaseModel):
    """A feed entry — either an original post or a repost surfaced into the feed."""
    post: PostOut
    reposted_by: Optional[str] = None   # user_id of the reposter, if applicable


# ---------------------------------------------------------------------------
# Messages (DMs)
# ---------------------------------------------------------------------------

class MessageCreate(BaseModel):
    sender_id: str
    receiver_id: str
    text: str


class MessageOut(BaseModel):
    id: str
    sender_id: str
    receiver_id: str
    text: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------

class GroupCreate(BaseModel):
    name: str
    creator_id: str
    member_ids: List[str] = []


class GroupMessageCreate(BaseModel):
    sender_id: str
    text: str


class AddMemberRequest(BaseModel):
    user_id: str


class GroupOut(BaseModel):
    id: str
    name: str
    creator_id: str
    member_ids: List[str]
    created_at: datetime


class GroupMessageOut(BaseModel):
    id: str
    group_id: str
    sender_id: str
    text: str
    created_at: datetime
