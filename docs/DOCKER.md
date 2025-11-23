# Docker Setup

> **Related Documentation:**
> - [← Back to README](../README.md#-documentation) | [Development Guide](DEVELOPMENT.md) | [Configuration](../app/config_docs.py)
> - **Deployment**: [Authentication](AUTHENTICATION.md) | [Data Persistence](DATA_PERSISTENCE.md)
> - **Integration**: [Integration Guide](INTEGRATIONS.md)

This directory contains Docker configurations for the doco document generation MCP service.

## Architecture

The Docker setup uses a multi-stage approach with UV for Python package management:

1. **Base Image** (`doco_base`): Ubuntu 22.04 with Python 3.11, UV, and dependencies for rendering
2. **Development Image** (`doco_dev`): Includes Git, GitHub CLI, SSH for VS Code remote development
3. **Production Image** (`doco_prod`): Minimal image with only runtime dependencies

### Dependencies in Base Image

The base image includes comprehensive libraries for document generation:
- **Jinja2**: Template rendering
- **WeasyPrint**: HTML → PDF conversion (requires pango, cairo, libffi)
- **html2text**: HTML → Markdown conversion
- **PyYAML**: Template and style metadata parsing
- **Fonts**: DejaVu, Liberation, and Noto fonts for consistent rendering
- **font-config**: Font management and fallback resolution

These ensure professional document rendering with proper styling and fallbacks.

## Prerequisites

- Docker installed and running
- For development: Your project should be at `~/devroot/doco`

## Building Images

### 1. Build Base Image (Required First)

```bash
cd /home/parris3142/devroot/doco
./docker/build-base.sh
```

This creates the `doco_base:latest` image with Python 3.11, UV, and document rendering libraries.

### 2. Build Development Image

```bash
./docker/build-dev.sh
```

This creates the `doco_dev:latest` image configured for VS Code remote development. The build script automatically uses your current user's UID and GID to avoid permission issues.

### 3. Build Production Image

```bash
./docker/build-prod.sh
```

This creates the `doco_prod:latest` image with the application installed via UV and pyproject.toml.

## Running Containers

### Development Container

```bash
./docker/run-dev.sh
```

This will:
- Stop and remove any existing `doco_dev` container
- Start a new container named `doco_dev`
- Mount your local `~/devroot/doco` directory to `/home/doco/devroot/doco`
- Mount your `~/.ssh` directory (read-only) for Git authentication
- Expose port 8010 for the web server and 8011 for MCP server

**Connecting to the dev container:**

From terminal:
```bash
docker exec -it doco_dev /bin/bash
```

From VS Code:
1. Install the "Dev Containers" extension
2. Click the remote connection icon (bottom left)
3. Select "Attach to Running Container"
4. Choose `doco_dev`

### Production Container

Use the provided script for production deployment (recommended):
```bash
./docker/run-prod.sh [WEB_PORT] [MCP_PORT]
# Example: ./docker/run-prod.sh 9000 9001
```

This script automatically:
- Creates persistent data directory at `~/doco_data`
- Mounts data directory for persistent session storage
- Creates doco_net Docker network
- Exposes configurable ports (default 8010, 8011)

**Manual deployment:**
```bash
# Create data directory for persistence
mkdir -p ~/doco_data/{auth,storage}

# Run with persistent data volume
docker run -d \
  --name doco_prod \
  --network doco_net \
  -v ~/doco_data:/home/doco/devroot/doco/data \
  -p 8010:8010 \
  -p 8011:8011 \
  doco_prod:latest
```

## Using UV Inside Containers

### Development Container

Once inside the dev container, install dependencies from pyproject.toml:

```bash
# Sync dependencies (install/update)
uv sync

# Install the project in editable mode
uv pip install -e .

# Add a new dependency
uv add <package-name>

# Add a dev dependency
uv add --dev <package-name>

# Run the MCP server
python -m app.main_mcp

# Run the web server
python -m app.main_web
```

### Production Container

Dependencies are pre-installed during the image build. The production image is ready to run immediately.

## Project Structure Inside Containers

### Development Container
```
/home/doco/
├── devroot/doco/          # Your mounted project directory
│   ├── app/
│   ├── docker/
│   ├── templates/         # Template bundles
│   ├── styles/            # Style bundles
│   ├── pyproject.toml
│   └── ...
├── .venv/                  # UV virtual environment
└── .ssh/                   # Your SSH keys (read-only)
```

### Production Container
```
/home/doco/
├── devroot/doco/
│   ├── app/                # Application code
│   ├── templates/          # Template bundles
│   ├── styles/             # Style bundles
│   ├── data/               # Persistent data (mounted from host)
│   │   ├── auth/           # JWT tokens
│   │   └── storage/        # Session data
│   ├── pyproject.toml      # Project configuration
│   └── .venv/              # UV virtual environment with installed deps
```

**Note**: The `data/` directory should be mounted from the host for persistent storage.

## Data Persistence

### Development Container
The development container mounts your entire project directory, so all data is automatically persisted on your host machine at `~/devroot/doco/data/`.

### Production Container
The production container uses a separate data directory (`~/doco_data/`) mounted as a volume:

**Structure:**
```
~/doco_data/
├── auth/
│   └── tokens.json           # JWT token-to-group mappings
└── storage/
    ├── metadata.json         # Session metadata
    └── session_<uuid>/       # Per-session directories
        ├── metadata.json     # Session state
        ├── parameters.json   # Global parameters
        └── fragments.json    # Fragment instances
```

**Configuration:**
You can override the data directory location using the `DOCO_DATA_DIR` environment variable:

```bash
docker run -d \
  --name doco_prod \
  -e DOCO_DATA_DIR=/data/doco \
  -v /host/path/to/data:/data/doco \
  -p 8010:8010 \
  -p 8011:8011 \
  doco_prod:latest
```

**Backup:**
```bash
# Backup all data
tar -czf doco_data_backup_$(date +%Y%m%d).tar.gz ~/doco_data/

# Backup only sessions
tar -czf doco_sessions_backup_$(date +%Y%m%d).tar.gz ~/doco_data/storage/

# Restore data
tar -xzf doco_data_backup_YYYYMMDD.tar.gz -C ~/
```

## Environment Variables

The containers use these environment variables:

- `VIRTUAL_ENV=/home/doco/.venv`
- `PATH=/home/doco/.venv/bin:$PATH`
- `DOCO_DATA_DIR` (optional): Override default data directory location
- `DOCO_JWT_SECRET` (optional): JWT secret for authentication

This ensures all Python commands use the UV-managed virtual environment.

## Permissions

- Development container runs as user `doco` with your host UID/GID
- Production container runs as user `doco` with system-allocated UID/GID
- This prevents permission issues with mounted volumes in development

## Rebuilding

If you modify dependencies in `pyproject.toml`:

**Development**: Just run `uv sync` inside the container
**Production**: Rebuild the production image with `./docker/build-prod.sh`

## Troubleshooting

### Permission Issues
- Make sure your host directory is at `~/devroot/doco`
- The dev build script uses your current UID/GID

### UV Not Found
- Rebuild the base image: `./docker/build-base.sh`
- Verify UV is in PATH: `echo $PATH` inside container

### Dependencies Not Installing
- Check `pyproject.toml` syntax
- Try: `uv pip install --verbose -e .`
- View UV logs: `uv pip install --verbose <package>`

### WeasyPrint/Rendering Errors
- Ensure base image includes `pango`, `cairo`, `libffi` libraries
- Verify fonts are installed: `fc-list` inside container
- Check PDF conversion: `python -c "import weasyprint; print(weasyprint.__version__)"`

### Container Won't Start
- Check if ports are in use: `lsof -i :8010` and `lsof -i :8011`
- View container logs: `docker logs doco_dev`

## Cleaning Up

Remove all doco containers and images:

```bash
# Stop and remove containers
docker stop doco_dev doco_prod 2>/dev/null
docker rm doco_dev doco_prod 2>/dev/null

# Remove images
docker rmi doco_prod:latest doco_dev:latest doco_base:latest

# Remove network
docker network rm doco_net 2>/dev/null
```

## See Also

- [PROJECT_SPEC.md](../PROJECT_SPEC.md) — Technology stack and architecture
- [DATA_PERSISTENCE.md](DATA_PERSISTENCE.md) — Session storage and recovery
- [DOCUMENT_GENERATION.md](DOCUMENT_GENERATION.md) — Using the document API

