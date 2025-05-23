# Collaborative Event Management System

A production‑grade FastAPI backend for creating, sharing, and managing events with:

* 🔐 **JWT Authentication**
* 🗓️ **Event CRUD** with conflict detection
* 🧑‍🤝‍🧑 **Role-Based Sharing** (Owner / Editor / Viewer)
* 🔄 **Versioning & Changelogs** (snapshot, rollback, diff)
* 🔔 **Real-Time Notifications** via WebSocket
* 🛠️ **Batch Create** and **MessagePack** support

---

## 🗺️ Project Flow & Architecture

This API follows a layered architecture with clear separation:

1. **Authentication Layer**

   * Registers users and issues JWTs
   * Secures all routes via OAuth2PasswordBearer
2. **Database Layer (SQLModel + Alembic)**

   * Models: `User`, `Event`, `EventPermission`, `EventVersion`, `Notification`
   * Migrations: incremental schema changes via Alembic
3. **Business Logic Layer (Services & Utilities)**

   * Conflict detection, permission resolution, diff generation
   * Notification dispatcher for WebSocket and persistence
4. **API Layer (Routers)**

   * Modular routers: `auth`, `events`, `permissions`, `notifications`
   * Clear path prefixes and tags for Swagger grouping
5. **Real‑Time Layer**

   * WebSocket endpoint managing active connections per user
   * Pushes live JSON notifications on event changes

---

## 🚀 Getting Started

Follow these steps to run locally:

### 1. Clone & Install

```bash
git clone https://github.com/gandharvtalikoti/event-management-system.git
cd event-management-system
python -m venv env
# Windows
.\env\Scripts\activate
# macOS/Linux
source env/bin/activate
pip install -r requirements.txt
```

### 2. Configuration

Copy `.env.example` to `.env` and adjust values:

```ini
DATABASE_URL=postgresql+psycopg2://<user>:<pass>@localhost/neofi_db
SECRET_KEY=<random_hex32>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 3. Database Setup & Migrations

```bash
# Initialize DB (creates tables)
alembic upgrade head
```

### 4. Start the Server

```bash
uvicorn app.main:app --reload
```

### 5. Explore the API Docs

* Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* Redoc:       [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## ⚙️ Environment Variables

| Key                           | Description                          |
| ----------------------------- | ------------------------------------ |
| `DATABASE_URL`                | SQLAlchemy database URL (PostgreSQL) |
| `SECRET_KEY`                  | Secret for signing JWT tokens        |
| `ALGORITHM`                   | JWT algorithm (e.g., HS256)          |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry time in minutes         |

---

## 💡 Core Features & Endpoints

### 1. Authentication

* **POST** `/api/auth/register`

  * Registers a new user
  * **Body**: `username`, `email`, `password`
  * **Response**: `UserRead` (id, username, email, role)

* **POST** `/api/auth/login`

  * Authenticates and returns a JWT
  * **Body**: `username`, `password`
  * **Response**: `{ access_token, token_type }`

* **POST** `/api/auth/refresh` / `/logout` (optional)

---

### 2. Event Management

* **POST** `/api/events`

  * Creates a new event
  * Performs conflict detection (no overlapping times)
  * Persists event and notifies owner
  * **Body**: `EventCreate` schema
  * **Response**: `EventRead`

* **GET** `/api/events`

  * Lists events the user owns or has access to
  * Supports pagination & date filtering

* **GET** `/api/events/{event_id}`

  * Retrieves a specific event

* **PUT** `/api/events/{event_id}`

  * Updates fields; snapshots previous state (`EventVersion`)
  * Conflict detection on new times
  * Notifies owner & collaborators
  * **Body**: partial `EventUpdate` schema

* **DELETE** `/api/events/{event_id}`

  * Deletes an event (Owner only)

---

### 3. Sharing & Permissions

* **POST** `/api/events/{event_id}/share`

  * Shares event with multiple users
  * Assigns `editor` or `viewer` roles
  * Persists `EventPermission` and notifies each user
  * **Body**: list of `{ user_id, role }`

* **GET** `/api/events/{event_id}/permissions`

  * Lists all permissions for the event

* **PUT** `/api/events/{event_id}/permissions/{user_id}`

  * Updates a single user’s role

* **DELETE** `/api/events/{event_id}/permissions/{user_id}`

  * Revokes a user’s access

---

### 4. Versioning & History

* **GET** `/api/events/{event_id}/changelog`

  * Returns all `EventVersion` entries in order

* **GET** `/api/events/{event_id}/diff/{v1_id}/{v2_id}`

  * Returns a dict of field-level changes between two versions

* **POST** `/api/events/{event_id}/rollback/{version_id}`

  * Reverts the event to a given version snapshot

---

### 5. Batch Operations

* **POST** `/api/events/batch`

  * Atomically creates multiple events
  * Rolls back all if any conflict or validation error
  * **Body**: `{ events: [EventCreate, …] }`

---

### 6. Notifications

* **GET** `/api/notifications`

  * Lists current user’s notifications

* **POST** `/api/notifications/{notif_id}/read`

  * Marks a notification as read

* **WebSocket** `/ws/notifications?token=<JWT>`

  * Opens a live feed of JSON payloads on event changes
  * Example payload:

    ```json
    { "type": "event_updated", "event_id": 42, "timestamp": "2025-05-23T12:00:00Z" }
    ```

---

## 📦 Serialization Formats

* **JSON** (default)
* **MessagePack** via `application/msgpack` header (Starlette-msgpack)

---

## 📝 Migrations

Use **Alembic** to manage schema changes:

```bash
alembic revision --autogenerate -m "Your message"
alembic upgrade head
```

---

## 🛠️ Contributing & License

Contributions are welcome! Please open issues or pull requests.

MIT License © Gandharv Talikoti
