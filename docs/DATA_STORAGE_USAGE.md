# Data Storage Folder Usage

## Overview

The `data/storage` folder is used by the **image storage system** for persisting rendered images (screenshots, exports, etc.) with GUID-based file naming and group-based access control.

## Directory Structure

```
data/
├── storage/           ← Image storage (FileStorage)
│   ├── metadata.json  ← Index of all stored images with metadata
│   ├── <guid>.png
│   ├── <guid>.jpg
│   ├── <guid>.pdf
│   ├── <guid>.svg
│   └── ...
├── sessions/          ← Document sessions (SessionStore)
├── proxy/             ← Proxy-stored rendered documents
├── auth/              ← Authentication tokens
```

## Components Using `data/storage`

### 1. **FileStorage** (`app/storage/file_storage.py`)

The primary implementation of image storage. Stores images with GUID-based filenames.

**Key Methods:**
- `save_image(image_data, format, group)` → Returns GUID
- `get_image(identifier, group)` → Returns (bytes, format) tuple
- `delete_image(identifier, group)` → Deletes file and metadata
- `list_images(group)` → Lists all images for a group
- `purge(age_days, group)` → Cleanup old images

**Features:**
- Group-based segregation for multi-tenant access control
- Metadata tracking (format, group, size, created_at)
- GUID validation (UUID format)
- Support for multiple formats: PNG, JPG, JPEG, SVG, PDF

### 2. **Web Server** (`app/web_server.py`)

Initializes FileStorage for the web API:

```python
self.storage = FileStorage(str(Config.get_storage_dir()))
```

Used to:
- Store rendered images/exports from documents
- Retrieve previously stored images
- Manage image lifecycle (delete, list, purge)

### 3. **Config Management** (`app/config.py`)

Centralized configuration for storage directory:

```python
@classmethod
def get_storage_dir(cls) -> Path:
    """Get the directory for image storage"""
    return cls.get_data_dir() / "storage"

def get_default_storage_dir() -> str:
    """Get default storage directory as string"""
    return str(Config.get_storage_dir())
```

**Configuration Sources (in priority order):**
1. `DOCO_DATA_DIR` environment variable (if set)
2. Default: `<project>/data/storage`
3. Test override: Custom temporary directory

## Metadata Format

The `metadata.json` file tracks all stored images:

```json
{
  "550e8400-e29b-41d4-a716-446655440000": {
    "format": "pdf",
    "group": "public",
    "size": 245632,
    "created_at": "2025-11-16T14:07:10.327Z"
  },
  "660e8400-e29b-41d4-a716-446655440001": {
    "format": "png",
    "group": "private",
    "size": 125488,
    "created_at": "2025-11-16T14:08:15.892Z"
  }
}
```

## Group-Based Access Control

Images are segregated by group at the metadata level:

```python
# Save image to "public" group
guid = storage.save_image(image_bytes, format="pdf", group="public")

# Retrieve image (group verified)
image_data, format = storage.get_image(guid, group="public")

# This would fail - group mismatch
# storage.get_image(guid, group="private")  # Raises ValueError
```

## Usage Example

### In Web Server

```python
from app.storage import get_storage
from app.config import Config

storage = get_storage(Config.get_storage_dir())

# Save rendered document
image_guid = storage.save_image(
    image_data=pdf_bytes,
    format="pdf",
    group=user_group
)

# Client receives GUID for later retrieval
return {"guid": image_guid, "format": "pdf"}

# Later, retrieve the image
image_data, format = storage.get_image(image_guid, group=user_group)
```

### In Tests

Tests use temporary directories via Config test mode:

```python
import tempfile
from app.config import Config

temp_dir = tempfile.mkdtemp()
Config.set_test_mode(test_data_dir=Path(temp_dir))

# FileStorage now uses temporary directory
storage = FileStorage(str(Config.get_storage_dir()))
```

## Purge/Cleanup

The `purge()` method supports cleanup of old images:

```python
# Delete images older than 30 days
deleted = storage.purge(age_days=30)

# Delete all images (dangerous!)
deleted = storage.purge(age_days=0)

# Delete old images in specific group
deleted = storage.purge(age_days=30, group="archived")
```

**Cleanup Script Available:**

```bash
python scripts/storage_manager.py --purge 30
```

## Docker Integration

In Docker, the storage directory can be mounted for persistence:

```bash
# Entrypoint creates directory
mkdir -p /home/doco/devroot/doco/data/storage

# Mount for persistence
docker run -v /host/path/to/storage:/home/doco/devroot/doco/data/storage doco
```

## Other Storage Directories

| Directory | Purpose | Implementation |
|-----------|---------|-----------------|
| `data/storage/` | **Image files** | `FileStorage` (GUID-based) |
| `data/sessions/` | **Document sessions** | `SessionStore` (JSON files) |
| `data/proxy/` | **Proxy-stored renders** | `RenderingEngine._store_proxy_document()` |
| `data/auth/` | **Auth tokens** | `tokens.json` |

## Summary

**`data/storage`** is used for:
- ✅ Storing rendered images/exports with GUID identifiers
- ✅ Multi-tenant group segregation
- ✅ Image metadata tracking (format, size, timestamps)
- ✅ Lifecycle management (save, retrieve, delete, purge)
- ✅ Persistence across server restarts
- ✅ Docker-friendly mount point

**NOT used for:**
- ❌ Session storage (use `data/sessions/`)
- ❌ Proxy documents (use `data/proxy/`)
- ❌ Authentication (use `data/auth/`)
