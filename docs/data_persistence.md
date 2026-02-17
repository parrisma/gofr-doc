# Data Persistence

> **Related Documentation:**
> - [← Back to README](../readme.md#advanced-topics) | [Project Spec](project_spec.md) | [Configuration](../app/config_docs.py)
> - **Features**: [Features Guide](features.md)
> - **Deployment**: [Docker](docker.md) | [Authentication](authentication.md)

This document describes how doco persists data across restarts and manages long-lived sessions.

## Overview

doco uses file-system storage to persist:
- **Session data**: Document assembly state, fragments, parameters
- **Authentication tokens**: JWT token-to-group mappings
- **Session metadata**: Creation/update timestamps, template ID, global parameters

## Directory Structure

```
data/
├── auth/                     # Authentication data
│   └── tokens.json           # Token-to-group mappings
└── storage/                  # Session and document data
    ├── session_<uuid>/       # Per-session directory
    │   ├── metadata.json     # Session metadata
    │   ├── parameters.json   # Global parameters
    │   └── fragments.json    # Fragment instances with GUIDs
    └── metadata.json         # Overall storage metadata
```

## Session Persistence

### Session Lifecycle

1. **Creation** (`create_document_session`):
   - Session UUID4 generated
   - Directory created at `data/storage/session_<uuid>/`
   - Metadata written: template_id, creation timestamp

2. **Iteration** (`set_global_parameters`, `add_fragment`, `remove_fragment`):
   - Parameters and fragments written to session files
   - Update timestamp recorded
   - Fragment GUIDs (UUID4) persisted with parameters

3. **Rendering** (`get_document`):
   - Session data loaded from disk
   - HTML generated from template + fragments
   - PDF/Markdown converted in-memory
   - Session remains on disk for subsequent renders

4. **Cleanup** (`abort_document_session`):
   - Session directory deleted
   - All fragment GUIDs and parameters purged
   - Metadata cleaned up

### Persistence Across Restarts

Sessions automatically survive process restarts because:
- Session data is written to disk immediately
- Session manager loads all sessions from `data/storage/` on startup
- Fragment GUIDs remain stable (UUID4, persisted in metadata)
- Concurrent operations use file locking to prevent corruption

**Example:**

```bash
# Start server, create session
$ python -m app.main_mcp
# Creates session 550e8400-e29b-41d4-a716-446655440000
# Adds fragments, renders

# Kill server
$ pkill -f main_mcp

# Restart server
$ python -m app.main_mcp
# Session 550e8400-e29b-41d4-a716-446655440000 still exists
# Can continue rendering without re-assembly
```

## Configuration

The data directory location can be configured via:

1. **Environment Variable**: `DOCO_DATA_DIR`

    ```bash
    export DOCO_DATA_DIR=/path/to/custom/data
    ```

2. **Default Location**: `{project_root}/data`

3. **Docker**: Mount a volume to `/home/doco/devroot/doco/data` in the container

## Docker Volumes

For persistent data in Docker deployments, mount the data directory:

```bash
docker run \
  -v /host/path/to/data:/home/doco/devroot/doco/data \
  -v /host/path/to/sessions:/home/doco/devroot/doco/data/storage \
  doco_prod
```

## Storage Backend

doco uses the pluggable `app/storage` module:

- **FileStorage** (default): Persists to `data/storage/` directory
- **Interface** (`StorageBackend`): Extensible for S3, database, etc.

## Testing

Tests automatically use temporary directories that are cleaned up after each test run:

```bash
pytest test/
# Tests use: /tmp/pytest-of-{user}/pytest-{pid}/test_name/doco_test_data/
# Cleanup: automatic after test completion
```

This ensures test isolation and prevents pollution of the persistent data directory.

## Session Concurrency & Locking

Sessions support concurrent operations while maintaining consistency:

- **File locking**: Storage backend acquires exclusive locks during writes
- **Atomic writes**: Session metadata and fragment lists written atomically
- **Multiple readers**: Concurrent renders allowed (read-only operations)
- **Single writer**: Only one operation can modify a session at a time

## Security Notes

- **tokens.json**: Contains JWT token mappings. Keep secure and backup regularly.
- **storage/**: Contains session data and assembled documents. Access is scoped to authenticated users.
- **.gitignore**: The entire data directory content is gitignored (except structure).
- **Sensitive data**: Fragment parameters may contain sensitive content; restrict file permissions accordingly.

## Backup & Recovery

### Backup

To backup all persistent data:

```bash
tar -czf doco_data_backup_$(date +%Y%m%d).tar.gz data/
```

To backup only sessions:

```bash
tar -czf doco_sessions_backup_$(date +%Y%m%d).tar.gz data/storage/
```

### Restore

To restore:

```bash
tar -xzf doco_data_backup_YYYYMMDD.tar.gz
```

### Recovery Procedures

If a session is corrupted:
1. Delete the corrupted session: `rm -rf data/storage/session_<uuid>/`
2. Verify metadata: `cat data/storage/metadata.json`
3. Restart the application

If entire storage is lost:
1. Restart application (will recreate `data/storage/`)
2. All existing sessions will be lost
3. Users must create new sessions and re-assemble documents

## Monitoring

Monitor session storage with:

```bash
# List active sessions
ls -la data/storage/session_*/

# Check disk usage
du -sh data/storage/

# View session metadata
cat data/storage/session_<uuid>/metadata.json
```

## See Also

- [project_spec.md](../project_spec.md) — Session lifecycle details
- [document_generation.md](document_generation.md) — Session workflow
- [authentication.md](authentication.md) — Token storage and rotation

