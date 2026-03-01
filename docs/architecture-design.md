# "in" Social Media Platform — Architecture Design

## Overview

"in" is an in-memory FastAPI backend exposing a RESTful API across 8 functional
domains: users, posts, follows, likes, comments, reposts, feed, direct messages,
and group chats. All state lives in a single `Storage` singleton
(`in_app/storage.py`) that is reset between test runs. The app is launched via
`uvicorn in_app.main:app`.

---

## Components

| Component | File | Role |
|---|---|---|
| App entry point | `main.py` | FastAPI instance, router registration, health check |
| Storage singleton | `storage.py` | Single source of truth for all in-memory state |
| Pydantic schemas | `models.py` | All request/response types — nothing raw escapes a router |
| Users router | `routers/users.py` | AC6-AC9: CRUD user profiles |
| Posts router | `routers/posts.py` | AC10-AC14: CRUD posts + user post list |
| Follows router | `routers/follows.py` | AC15-AC19: follow/unfollow, follower/following lists |
| Likes router | `routers/likes.py` | AC20-AC22: like/unlike posts |
| Comments router | `routers/comments.py` | AC23-AC26: comment CRUD |
| Reposts router | `routers/reposts.py` | AC27-AC29: repost, list reposters |
| Feed router | `routers/feed.py` | AC30-AC31: personalised feed |
| Messages router | `routers/messages.py` | AC32-AC34: DMs between users |
| Groups router | `routers/groups.py` | AC35-AC39: group chat CRUD |
| Test fixtures | `tests/conftest.py` | TestClient + autouse storage reset |

---

## Data Flow

```
HTTP Request
     │
     ▼
FastAPI (main.py)
     │  validates path + method
     ▼
Router function
     │  validates body with Pydantic model
     │  reads/writes store.*
     ▼
Storage singleton (store)
     │  Dict / Set / List structures
     ▼
Router function
     │  builds typed response model
     ▼
HTTP Response (JSON)
```

---

## API Contracts (summary)

### Users  `prefix: /users`
| Method | Path | Status | Notes |
|--------|------|--------|-------|
| POST | /users | 201/409 | Duplicate username → 409 |
| GET | /users/{user_id} | 200/404 | |
| PUT | /users/{user_id} | 200/404 | Partial update |

### Posts  `prefix: /posts, /users`
| Method | Path | Status | Notes |
|--------|------|--------|-------|
| POST | /posts | 201/400/404 | content ≤ 500 chars |
| GET | /posts/{post_id} | 200/404 | Includes author |
| GET | /users/{user_id}/posts | 200/404 | Newest first |
| DELETE | /posts/{post_id} | 200/404 | Cascade likes/comments/reposts |

### Follows  `prefix: /users`
| Method | Path | Status | Notes |
|--------|------|--------|-------|
| POST | /users/{user_id}/follow | 201/400/404/409 | Self-follow → 400 |
| DELETE | /users/{user_id}/follow | 200/404 | Body: {target_user_id} |
| GET | /users/{user_id}/followers | 200/404 | |
| GET | /users/{user_id}/following | 200/404 | |

### Likes  `prefix: /posts`
| Method | Path | Status | Notes |
|--------|------|--------|-------|
| POST | /posts/{post_id}/like | 201/404/409 | Double-like → 409 |
| DELETE | /posts/{post_id}/like | 200/404 | |

### Comments  `prefix: /posts, /comments`
| Method | Path | Status | Notes |
|--------|------|--------|-------|
| POST | /posts/{post_id}/comments | 201/400/404 | Empty text → 400 |
| GET | /posts/{post_id}/comments | 200/404 | Newest first |
| DELETE | /comments/{comment_id} | 200/404 | Decrements post count |

### Reposts  `prefix: /posts`
| Method | Path | Status | Notes |
|--------|------|--------|-------|
| POST | /posts/{post_id}/repost | 201/404/409 | Double-repost → 409 |
| GET | /posts/{post_id}/reposts | 200/404 | Returns user objects |

### Feed  `prefix: /feed`
| Method | Path | Status | Notes |
|--------|------|--------|-------|
| GET | /feed/{user_id} | 200/404 | Posts + reposts from followed users |

### Messages  `prefix: /messages`
| Method | Path | Status | Notes |
|--------|------|--------|-------|
| POST | /messages | 201/400/404 | Empty text → 400 |
| GET | /messages/{user_id}/{other_user_id} | 200 | Chronological |

### Groups  `prefix: /groups`
| Method | Path | Status | Notes |
|--------|------|--------|-------|
| POST | /groups | 201/404 | Creator auto-added |
| GET | /groups/{group_id} | 200/404 | |
| POST | /groups/{group_id}/members | 200/404 | Idempotent |
| POST | /groups/{group_id}/messages | 201/400/403/404 | Non-member → 403 |
| GET | /groups/{group_id}/messages | 200/404 | Chronological |

---

## Data Model

### `store.users`  `Dict[str, dict]`
```
{
  id: str (UUID4)
  username: str
  display_name: str
  bio: str
  profile_picture_url: str
  followers_count: int
  following_count: int
  posts_count: int
  created_at: datetime
}
```

### `store.posts`  `Dict[str, dict]`
```
{
  id: str
  user_id: str
  content: str          # max 500 chars
  media_url: str | None
  media_type: str | None
  likes_count: int
  comments_count: int
  reposts_count: int
  created_at: datetime
}
```

### `store.follows`  `Set[Tuple[str, str]]`
```
(follower_id, followed_id)
```

### `store.likes`  `Set[Tuple[str, str]]`
```
(user_id, post_id)
```

### `store.reposts`  `Set[Tuple[str, str]]`
```
(user_id, post_id)
```

### `store.comments`  `Dict[str, dict]`
```
{
  id: str
  post_id: str
  user_id: str
  text: str
  created_at: datetime
}
```

### `store.messages`  `List[dict]`
```
{
  id: str
  sender_id: str
  receiver_id: str
  text: str
  created_at: datetime
}
```

### `store.groups`  `Dict[str, dict]`
```
{
  id: str
  name: str
  creator_id: str
  member_ids: List[str]
  created_at: datetime
}
```

### `store.group_messages`  `Dict[str, List[dict]]`
```
group_id → [
  {
    id: str
    group_id: str
    sender_id: str
    text: str
    created_at: datetime
  }
]
```

---

## Non-Functional Considerations

### Security
- All request bodies validated by Pydantic before any storage mutation
- 400 for empty/whitespace text prevents empty-content spam
- 409 idempotency guards prevent duplicate relationships
- Non-member group message rejection (403) enforces group privacy

### Performance
- O(1) duplicate checks via `set` membership for follows, likes, reposts
- Feed aggregation is O(F×P) where F = followed count, P = post count — acceptable
  for an in-memory prototype; a production build would use an indexed fanout queue
- No N+1 queries — author data is embedded at response build time from the same dict

### Scalability
- In-memory store is intentionally non-distributed — single process only
- Upgrading to a persistent store (PostgreSQL + Redis sets for follows/likes) would
  require replacing `storage.py` only; all router logic stays identical
- The `Store.reset()` contract makes the storage layer trivially testable

---

## Key Design Decisions

1. **Sets for relationships** — follows, likes, reposts use `Set[Tuple[str, str]]`
   for O(1) membership tests. Lists would require O(n) scans on every like/follow check.

2. **Cascade on delete** — `DELETE /posts/{id}` rebuilds `store.likes`, `store.reposts`
   (set comprehension) and `store.comments` (dict comprehension) in one pass each.
   This is O(n) but acceptable for in-memory prototypes.

3. **Feed deduplication** — a post already present as an original is not surfaced
   again as a repost entry. The `feed_map` dict keyed on `post_id` handles this
   naturally in a single pass.

4. **Router prefix sharing** — multiple routers legitimately own paths under `/users`
   and `/posts`. They are included in a fixed order in `main.py` so FastAPI's
   top-to-bottom path matching resolves ambiguities correctly.
