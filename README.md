# Collaborative Event Management System

A production-grade FastAPI backend for creating, sharing, and managing events with:

- 🔐 **JWT Authentication**  
- 🗓️ **Event CRUD** with conflict detection  
- 🧑‍🤝‍🧑 **Role-Based Sharing** (Owner / Editor / Viewer)  
- 🔄 **Versioning & Changelogs** (snapshot, rollback, diff)  
- 🔔 **Real-Time Notifications** via WebSocket  
- 🛠️ **Batch Create** and **MessagePack** support  

---

## 🗺️ Project Flow & Architecture

1. **User Authentication**  
   - Register (`POST /api/auth/register`) → stores hashed password  
   - Login  (`POST /api/auth/login`) → returns JWT bearer token  

2. **Event Management**  
   - Create (`POST /api/events`)  
     - Conflict-checks existing events for the same owner  
     - Persists and notifies via DB+WebSocket  
   - Read  
     - List all accessible events (`GET /api/events`)  
     - Get by ID (`GET /api/events/{id}`)  
   - Update (`PUT /api/events/{id}`)  
     - Permission check (owner/editor)  
     - Snapshots previous version → `EventVersion`  
     - Conflict detection on new times  
     - Persists, notifies, returns updated event  
   - Delete (`DELETE /api/events/{id}`)  

3. **Sharing & Permissions**  
   - Share event (`POST /api/events/{id}/share`)  
   - List permissions (`GET /api/events/{id}/permissions`)  
   - Update permission (`PUT /api/events/{id}/permissions/{userId}`)  
   - Remove access (`DELETE /api/events/{id}/permissions/{userId}`)  

4. **Versioning & History**  
   - Versions stored in `EventVersion` table  
   - Changelog (`GET /api/events/{id}/changelog`)  
   - Diff (`GET /api/events/{id}/diff/{v1}/{v2}`)  
   - Rollback (`POST /api/events/{id}/rollback/{versionId}`)  

5. **Batch Operations**  
   - Create many at once: `POST /api/events/batch`  

6. **Notifications**  
   - Persisted in `Notification` table  
   - Real-time via WebSocket: `ws://<host>/ws/notifications?token=<JWT>`  
   - Polling API:  
     - List → `GET /api/notifications`  
     - Mark read → `POST /api/notifications/{notifId}/read`  

---


## 🚀 Getting Started

1. **Clone Repo**  
   ```bash
   git clone https://github.com/gandharvtalikoti/event-management-system.git
   cd event-management-system
2. Start the server
uvicorn app.main:app --reload

Open Swagger UI → http://127.0.0.1:8000/docs
Open Redoc → http://127.0.0.1:8000/redoc
Start testing!

