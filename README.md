# in — Social Media Platform API

**in** is a modern, feature-rich social media API inspired by Instagram. Built with FastAPI and Python, it provides a complete backend for managing user profiles, posts, follows, likes, comments, reposts, personalised feeds, direct messages, and group chats.

## Features

- **User Profiles** — Create, view, and update user profiles with customizable display names and bios
- **Posts** — Create, view, and delete posts (with a 500-character limit) with timestamps
- **Follows** — Follow and unfollow users; browse follower and following lists
- **Likes** — Like and unlike posts; view who liked each post
- **Comments** — Add comments to posts, list all comments on a post, delete individual comments
- **Reposts** — Repost content from other users; view who has reposted
- **Personalised Feed** — Get a chronologically-ordered feed of posts from users you follow
- **Direct Messages** — Send and receive 1-to-1 private messages with conversation history
- **Group Chats** — Create groups, add/remove members, and send messages in group conversations
- **Health Check** — Built-in status endpoint for service health monitoring

## Tech Stack

- **Python 3.9+** — Modern Python with type hints and async support
- **FastAPI** — Fast, modern web framework for building APIs
- **Pydantic** — Data validation and serialization with type safety
- **In-Memory Storage** — Fast, stateless storage (thread-safe singleton)
- **pytest** — Comprehensive test framework
- **httpx** — ASGI testing client for integration tests

## Getting Started

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/RajuRojpani/in.git
   cd in
   ```

2. Install dependencies:
   ```bash
   pip install -r in_app/requirements.txt
   ```

### Running the API

Start the development server with hot-reload:

```bash
uvicorn in_app.main:app --reload
```

The API will be available at:
- **Base URL:** `http://localhost:8000`
- **Interactive Docs (Swagger UI):** `http://localhost:8000/docs`
- **Alternative Docs (ReDoc):** `http://localhost:8000/redoc`

### Running Tests

Run the full test suite:

```bash
pytest in_app/tests/ -v
```

Run tests for a specific domain:

```bash
pytest in_app/tests/test_users.py -v
pytest in_app/tests/test_posts.py -v
pytest in_app/tests/test_comments.py -v
pytest in_app/tests/test_reposts.py -v
pytest in_app/tests/test_feed.py -v
pytest in_app/tests/test_messages.py -v
pytest in_app/tests/test_groups.py -v
```

## API Endpoints

### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/` | Service health check — returns platform status |

### Users (7 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/users` | Create a new user account |
| GET    | `/users/{user_id}` | Retrieve a user's profile by ID |
| PUT    | `/users/{user_id}` | Update a user's profile information |
| GET    | `/users/{user_id}/posts` | List all posts by a specific user |
| GET    | `/users/{user_id}/followers` | Get list of users following this user |
| GET    | `/users/{user_id}/following` | Get list of users this user follows |

### Follows (2 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/users/{user_id}/follow` | Follow a user |
| DELETE | `/users/{user_id}/follow` | Unfollow a user |

### Posts (3 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/posts` | Create a new post (max 500 characters) |
| GET    | `/posts/{post_id}` | Retrieve a post by ID |
| DELETE | `/posts/{post_id}` | Delete a post (cascades to comments and likes) |

### Likes (2 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/posts/{post_id}/like` | Like a post |
| DELETE | `/posts/{post_id}/like` | Unlike a post |
| GET    | `/posts/{post_id}/likes` | Get list of users who liked the post |

### Comments (3 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/posts/{post_id}/comments` | Add a comment to a post |
| GET    | `/posts/{post_id}/comments` | List all comments on a post |
| DELETE | `/comments/{comment_id}` | Delete a comment by ID |

### Reposts (2 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/posts/{post_id}/repost` | Repost a post from another user |
| GET    | `/posts/{post_id}/reposts` | List users who have reposted this post |

### Feed (1 endpoint)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/users/{user_id}/feed` | Get personalised feed (posts from followed users, chronologically ordered) |

### Messages (2 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/messages` | Send a direct message to another user |
| GET    | `/messages/{user_1}/{user_2}` | Get conversation history between two users |

### Groups (5 endpoints)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/groups` | Create a new group chat |
| GET    | `/groups/{group_id}` | Get group details |
| POST   | `/groups/{group_id}/members` | Add a member to a group |
| DELETE | `/groups/{group_id}/members` | Remove a member from a group |
| POST   | `/groups/{group_id}/messages` | Send a message in a group |
| GET    | `/groups/{group_id}/messages` | List all messages in a group |

**Total:** 29 endpoints across 8 resource domains

## Project Structure

```
in_app/
├── __init__.py                 # Package initialization
├── main.py                     # FastAPI app entry point + router registration
├── models.py                   # Pydantic data models for all domains
├── storage.py                  # In-memory singleton data store
├── requirements.txt            # Python dependencies
│
├── routers/                    # API endpoint handlers
│   ├── __init__.py
│   ├── users.py               # User CRUD endpoints
│   ├── follows.py             # Follow/unfollow + follower lists
│   ├── posts.py               # Post CRUD + user posts list
│   ├── likes.py               # Like/unlike + who liked
│   ├── comments.py            # Add/list/delete comments
│   ├── reposts.py             # Repost/un-repost + who reposted
│   ├── feed.py                # Personalised feed endpoint
│   ├── messages.py            # Direct message endpoints
│   └── groups.py              # Group CRUD + group messages
│
├── tests/                      # Comprehensive test suite
│   ├── __init__.py
│   ├── conftest.py            # pytest fixtures and setup
│   ├── test_users.py          # User endpoint tests
│   ├── test_posts.py          # Post endpoint tests
│   ├── test_follows.py        # Follow functionality tests
│   ├── test_likes.py          # Like functionality tests
│   ├── test_comments.py       # Comment endpoint tests
│   ├── test_reposts.py        # Repost endpoint tests
│   ├── test_feed.py           # Feed endpoint tests
│   ├── test_messages.py       # Direct message tests
│   └── test_groups.py         # Group chat tests
│
└── docs/
    └── architecture-design.md  # Technical architecture documentation
```

## API Usage Examples

### Create a User

```bash
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "display_name": "Alice", "bio": "I love coding"}'
```

### Create a Post

```bash
curl -X POST http://localhost:8000/posts \
  -H "Content-Type: application/json" \
  -d '{"author_id": 1, "content": "Hello, in!"}'
```

### Like a Post

```bash
curl -X POST http://localhost:8000/posts/1/like \
  -H "Content-Type: application/json" \
  -d '{"user_id": 2}'
```

### Follow a User

```bash
curl -X POST http://localhost:8000/users/2/follow \
  -H "Content-Type: application/json" \
  -d '{"follower_id": 1}'
```

### Get Personalised Feed

```bash
curl http://localhost:8000/users/1/feed
```

### Send a Direct Message

```bash
curl -X POST http://localhost:8000/messages \
  -H "Content-Type: application/json" \
  -d '{"sender_id": 1, "recipient_id": 2, "content": "Hi there!"}'
```

## Data Models

All data is structured using Pydantic models for type safety and validation:

- **User** — username, display_name, bio, created_at
- **Post** — author_id, content (max 500 chars), created_at, is_repost
- **Follow** — follower_id, following_id, created_at
- **Like** — user_id, post_id, created_at
- **Comment** — author_id, post_id, content, created_at
- **Repost** — reposted_by_id, original_post_id, created_at
- **Message** — sender_id, recipient_id, content, created_at, is_read
- **Group** — group_id, name, description, created_by_id, created_at
- **GroupMember** — group_id, user_id, joined_at
- **GroupMessage** — group_id, sender_id, content, created_at

## Storage & State Management

The platform uses an **in-memory data store** with a thread-safe singleton pattern. This design:

- ✅ Provides instant access to data (no database latency)
- ✅ Simplifies testing and development
- ✅ Allows for reset between tests via `StorageManager.reset()`

**Important:** Data is not persisted between application restarts. For a production deployment, integrate a database such as PostgreSQL or MongoDB.

## Error Handling

All endpoints follow consistent HTTP status codes:

- **200 OK** — Successful GET/PUT request
- **201 Created** — Successful POST request (resource created)
- **204 No Content** — Successful DELETE request
- **400 Bad Request** — Invalid request data (missing required fields, validation errors)
- **404 Not Found** — Resource does not exist
- **409 Conflict** — Operation conflicts with existing state (e.g., already following)
- **500 Internal Server Error** — Unexpected server error

## Testing

The project includes **50+ automated tests** covering:

- ✅ User creation, updates, and profile retrieval
- ✅ Post creation, deletion, and cascading deletes
- ✅ Following/unfollowing and follower lists
- ✅ Liking posts and viewing likes
- ✅ Commenting, listing, and deleting comments
- ✅ Reposting and viewing reposters
- ✅ Personalised feed generation
- ✅ Direct messaging and conversation history
- ✅ Group creation, member management, and group messaging
- ✅ Edge cases and error conditions

Run all tests with coverage:

```bash
pytest in_app/tests/ -v --cov=in_app
```

## Design Decisions

1. **In-Memory Storage** — Chosen for simplicity and development speed. Each domain has its own collection within the singleton `StorageManager`.

2. **RESTful Design** — Follows REST conventions with logical resource paths and HTTP methods (GET for retrieval, POST for creation, DELETE for removal).

3. **Cascade Deletes** — Deleting a user or post automatically removes associated data (comments, likes, follows, messages) to maintain referential integrity.

4. **Timestamps** — All entities include `created_at` for audit trails and chronological ordering.

5. **Stateless API** — No session management or cookies — all operations are stateless and idempotent where applicable.

## Limitations & Future Enhancements

### Current Limitations
- In-memory storage is lost on application restart
- No user authentication or authorization
- No pagination for large result sets
- No image/media support for posts

### Planned Enhancements
- PostgreSQL database integration
- JWT-based authentication and authorization
- Pagination and cursor-based navigation
- Media uploads (images, videos)
- Real-time notifications via WebSockets
- Search functionality (posts, users, hashtags)
- User recommendations and trending posts

## Contributing

Contributions are welcome! Please:

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Write tests for new functionality
3. Ensure all tests pass: `pytest in_app/tests/ -v`
4. Commit your changes: `git commit -am 'feat: add your feature'`
5. Push to the branch: `git push origin feature/your-feature`
6. Open a pull request

## License

This project is licensed under the MIT License — see the LICENSE file for details.

## Support

For questions or issues, please open a GitHub issue or contact the development team.

---

**Built with ❤️ by Team Claw**

*"in" — connect with those who matter most.*
