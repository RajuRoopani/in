"""
Centralized in-memory storage for the 'in' social media platform.

All data lives in the singleton `store` object. Call `store.reset()` between
test runs to guarantee a clean slate.
"""

from typing import Dict, List, Set, Tuple


class Storage:
    """Single source of truth for all in-memory data."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Clear every collection — used by conftest between tests."""
        # Core entities
        self.users: Dict[str, dict] = {}
        self.posts: Dict[str, dict] = {}
        self.comments: Dict[str, dict] = {}
        self.groups: Dict[str, dict] = {}

        # Relationship sets — tuples keep uniqueness cheap (O(1) lookup)
        self.follows: Set[Tuple[str, str]] = set()   # (follower_id, followed_id)
        self.likes: Set[Tuple[str, str]] = set()     # (user_id, post_id)
        self.reposts: Set[Tuple[str, str]] = set()   # (user_id, post_id)

        # Message lists
        self.messages: List[dict] = []
        self.group_messages: Dict[str, List[dict]] = {}  # group_id → [msg, ...]


# Module-level singleton — imported by all routers
store = Storage()
