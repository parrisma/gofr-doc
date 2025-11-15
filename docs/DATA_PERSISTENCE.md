# Data Directory

This directory contains persistent data for the doco application.

## Structure

```
data/
├── auth/          # Authentication data (JWT tokens, user sessions)
│   └── tokens.json    # Token-to-group mappings
└── storage/       # Image storage (rendered graphs)
    └── metadata.json  # Image metadata and group access control
```

## Configuration

The data directory location can be configured via:

1. **Environment Variable**: `DOCO_DATA_DIR`

    ```bash
    export DOCO_DATA_DIR=/path/to/custom/data
    ```

2. **Default Location**: `{project_root}/data`

3. **Docker**: Mount a volume to `/home/{user}/devroot/doco/data` in the container

## Docker Volumes

For persistent data in Docker deployments, mount the data directory:

```bash
docker run -v /host/path/to/data:/home/doco/devroot/doco/data doco_prod
```

## Testing

Tests automatically use temporary directories that are cleaned up after each test run. This ensures test isolation and prevents pollution of the persistent data directory.

## Security Notes

- **tokens.json**: Contains JWT token mappings. Keep secure and backup regularly.
- **storage/**: Contains rendered images. Access is controlled via group permissions.
- **.gitignore**: The entire data directory content is gitignored (except structure).

## Backup

To backup all persistent data:

```bash
tar -czf doco_data_backup_$(date +%Y%m%d).tar.gz data/
```

To restore:

```bash
tar -xzf doco_data_backup_YYYYMMDD.tar.gz
```
