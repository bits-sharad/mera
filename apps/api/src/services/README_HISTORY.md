# Session History Service

## Overview

The `SessionHistoryService` manages conversation history storage in MongoDB. It stores chat messages by session ID, allowing for conversation continuity and history retrieval.

## MongoDB Collection

**Collection Name:** `history`

**Schema:**
```json
{
  "_id": "ObjectId",
  "session_id": "string (unique)",
  "messages": [
    {
      "role": "string (user|assistant|system)",
      "content": "string",
      "timestamp": "datetime"
    }
  ],
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

## Indexes

The service creates the following indexes for optimal performance:

1. **session_id** (unique) - Fast lookup by session ID
2. **updated_at** (descending) - Sorting recent sessions
3. **session_id + created_at** (compound) - Session queries with time range

## Usage

### Initialize Service

```python
from src.services.history import SessionHistoryService

# Uses default MongoDB settings from config
history = SessionHistoryService()

# Or with custom settings
history = SessionHistoryService(
    mongodb_uri="mongodb+srv://...",
    mongodb_database="custom_db"
)
```

### Append Message to Session

```python
# Add user message
await history.append("session-123", "user", "What is job matching?")

# Add assistant response
await history.append("session-123", "assistant", "Job matching is...")
```

### Get Session History

```python
# Retrieve all messages for a session
session_data = await history.get("session-123")

# Returns:
# {
#   "session_id": "session-123",
#   "messages": [
#     {"role": "user", "content": "...", "timestamp": "..."},
#     {"role": "assistant", "content": "...", "timestamp": "..."}
#   ],
#   "created_at": "...",
#   "updated_at": "..."
# }
```

### Get All Sessions

```python
# Get list of recent sessions (default limit: 100)
sessions = history.get_all_sessions(limit=50)
```

### Delete Session

```python
# Delete a session history
deleted = history.delete_session("session-123")
# Returns True if deleted, False if not found
```

### Close Connection

```python
# Close MongoDB connection when done
history.close()
```

## Initialize Indexes

Run the index initialization script:

```bash
cd apps/api
python -m src.services.init_history_indexes
```

Or initialize programmatically:

```python
history = SessionHistoryService()
history.create_indexes()
history.close()
```

## API Integration

The service is automatically used in the `/chat` endpoint:

```python
@router.post("/chat")
async def chat(req: ChatRequest, core_api: CoreAPIClient = Depends(_core)):
    # Initialize history service
    history = SessionHistoryService(core_api)
    
    # Append user message
    await history.append(req.session_id, "user", req.user_query)
    
    # ... process request ...
    
    # Append assistant response
    await history.append(req.session_id, "assistant", final_answer)
```

## Migration from Core API

The service has been migrated from using the Core API metadata store to direct MongoDB storage. The `core_api` parameter is now optional and maintained for backward compatibility only.

**Before:**
```python
history = SessionHistoryService(core_api)
```

**After (both work):**
```python
# With core_api (ignored, backward compatible)
history = SessionHistoryService(core_api)

# Without core_api (recommended)
history = SessionHistoryService()
```

## Configuration

The service uses these settings from `src.core.config`:

- `MONGODB_URI` - MongoDB connection string
- `MONGODB_DATABASE` - Database name (default: "jobmatchingmodelpocDev")

## Notes

- Messages are automatically timestamped when appended
- Session IDs should be unique per conversation
- The service uses upsert operations for efficient session creation/updates
- All MongoDB ObjectIds are automatically serialized to strings for JSON compatibility
