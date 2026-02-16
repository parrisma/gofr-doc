"""Centralized configuration documentation and defaults for DOCO service.

This module provides a comprehensive overview of all configuration options
and their environment variable mappings.
"""

# =============================================================================
# ENVIRONMENT VARIABLES REFERENCE
# =============================================================================

# Data & Storage
# --------------
# DOCO_DATA_DIR: Base directory for all persistent data (default: ./data)
#   Used for: sessions, storage, auth tokens, proxy documents
#
# Application Ports
# -----------------
# GOFR_DOC_MCP_PORT: MCP server port (default: 8010)
# GOFR_DOC_WEB_PORT: Web server port (default: 8012)
# GOFR_DOC_MCPO_PORT: MCPO wrapper port (default: 8011)
#
# GOFR_DOC_WEB_SERVER_URL: Base URL for web server (default: http://localhost:8012)
#   Used for: proxy document download URLs
#
# Authentication & Security
# -------------------------
# GOFR_JWT_SECRET: Secret key for JWT token signing/verification (required for auth mode)
# GOFR_DOC_TOKEN_STORE: Path to token store file (default: {DATA_DIR}/auth/tokens.json)
# GOFR_DOC_JWT_TOKEN: Bearer token for API authentication
#
# MCPO Configuration
# ------------------
# GOFR_DOC_MCPO_MODE: MCPO operation mode (default: "public")
#   Values: "auth" (requires JWT), "public" (no auth)
#
# GOFR_DOC_MCPO_API_KEY: API key for MCPO wrapper access
#
# Development & Testing
# ---------------------
# GOFR_DOC_TEST_MODE: Enable test mode (set by test framework)
# GOFR_DOC_LOG_LEVEL: Logging verbosity (default: INFO)
#   Values: DEBUG, INFO, WARNING, ERROR, CRITICAL

# =============================================================================
# CONFIGURATION DEFAULTS
# =============================================================================

DEFAULT_MCP_PORT = 8010
DEFAULT_WEB_PORT = 8012
DEFAULT_MCPO_PORT = 8011
DEFAULT_WEB_SERVER_URL = f"http://localhost:{DEFAULT_WEB_PORT}"
DEFAULT_MCPO_MODE = "public"
DEFAULT_LOG_LEVEL = "INFO"

# Image validation defaults
DEFAULT_IMAGE_MAX_SIZE_MB = 10
DEFAULT_IMAGE_REQUIRE_HTTPS = True
DEFAULT_IMAGE_TIMEOUT_SECONDS = 10

# Session defaults
DEFAULT_SESSION_TIMEOUT_MINUTES = 60

# =============================================================================
# CONFIGURATION HELPER FUNCTIONS
# =============================================================================


def get_config_summary() -> dict:
    """Get a summary of current configuration from environment.

    Returns:
        Dictionary with current configuration values
    """
    import os

    from app.config import Config

    return {
        "data_dir": str(Config.get_data_dir()),
        "storage_dir": str(Config.get_storage_dir()),
        "sessions_dir": str(Config.get_sessions_dir()),
        "auth_dir": str(Config.get_auth_dir()),
        "proxy_dir": str(Config.get_proxy_dir()),
        "test_mode": Config.is_test_mode(),
        "mcp_port": int(os.getenv("GOFR_DOC_MCP_PORT", DEFAULT_MCP_PORT)),
        "web_port": int(os.getenv("GOFR_DOC_WEB_PORT", DEFAULT_WEB_PORT)),
        "mcpo_port": int(os.getenv("GOFR_DOC_MCPO_PORT", DEFAULT_MCPO_PORT)),
        "web_server_url": os.getenv("GOFR_DOC_WEB_SERVER_URL", DEFAULT_WEB_SERVER_URL),
        "mcpo_mode": os.getenv("GOFR_DOC_MCPO_MODE", DEFAULT_MCPO_MODE),
        "jwt_secret_set": bool(os.getenv("GOFR_JWT_SECRET")),
        "log_level": os.getenv("GOFR_DOC_LOG_LEVEL", DEFAULT_LOG_LEVEL),
    }


def validate_configuration() -> tuple[bool, list[str]]:
    """Validate current configuration for completeness and consistency.

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    import os

    errors = []

    # Check data directory is writable
    from app.config import Config

    try:
        data_dir = Config.get_data_dir()
        if not data_dir.exists():
            data_dir.mkdir(parents=True, exist_ok=True)
        if not os.access(data_dir, os.W_OK):
            errors.append(f"Data directory not writable: {data_dir}")
    except Exception as e:
        errors.append(f"Cannot access data directory: {e}")

    # Check auth configuration if mode is "auth"
    mcpo_mode = os.getenv("GOFR_DOC_MCPO_MODE", DEFAULT_MCPO_MODE)
    if mcpo_mode == "auth":
        if not os.getenv("GOFR_JWT_SECRET"):
            errors.append("GOFR_JWT_SECRET required when GOFR_DOC_MCPO_MODE='auth' but not set")

    # Check port numbers are valid
    for port_var, default in [
        ("GOFR_DOC_MCP_PORT", DEFAULT_MCP_PORT),
        ("GOFR_DOC_WEB_PORT", DEFAULT_WEB_PORT),
        ("GOFR_DOC_MCPO_PORT", DEFAULT_MCPO_PORT),
    ]:
        port_str = os.getenv(port_var, str(default))
        try:
            port = int(port_str)
            if not (1024 <= port <= 65535):
                errors.append(f"{port_var}={port} out of valid range (1024-65535)")
        except ValueError:
            errors.append(f"{port_var}='{port_str}' is not a valid integer")

    return len(errors) == 0, errors


def print_configuration_help() -> None:
    """Print comprehensive configuration help to stdout."""
    help_text = """
╔═══════════════════════════════════════════════════════════════════════════╗
║                   DOCO CONFIGURATION REFERENCE                             ║
╚═══════════════════════════════════════════════════════════════════════════╝

ENVIRONMENT VARIABLES
═════════════════════

📁 DATA & STORAGE
  GOFR_DOC_DATA_DIR       Base directory for all persistent data
                          Default: ./data
                          Used for: sessions, storage, auth, proxy docs

🔌 APPLICATION PORTS
  GOFR_DOC_MCP_PORT       MCP server port
                          Default: 8010
  
  GOFR_DOC_WEB_PORT       Web server port
                          Default: 8012
  
  GOFR_DOC_MCPO_PORT      MCPO wrapper port
                          Default: 8011
  
  GOFR_DOC_WEB_SERVER_URL Web server base URL for proxy downloads
                          Default: http://localhost:8012

🔐 AUTHENTICATION & SECURITY
  GOFR_JWT_SECRET        Secret key for JWT signing/verification
                          Required: When using auth mode
                          Format: Any secure random string
  
  GOFR_DOC_TOKEN_STORE    Path to token store file
                          Default: {DATA_DIR}/auth/tokens.json
  
  GOFR_DOC_JWT_TOKEN      Bearer token for API authentication
                          Format: JWT token string

🎛️  MCPO CONFIGURATION
  GOFR_DOC_MCPO_MODE      Operation mode
                          Values: "auth" | "public"
                          Default: "public"
  
  GOFR_DOC_MCPO_API_KEY   API key for MCPO wrapper access

🧪 DEVELOPMENT & TESTING
  GOFR_DOC_LOG_LEVEL      Logging verbosity
                          Values: DEBUG | INFO | WARNING | ERROR | CRITICAL
                          Default: INFO

═════════════════════════════════════════════════════════════════════════════

CONFIGURATION MODES
═══════════════════

Production (Authenticated)
--------------------------
export GOFR_DOC_MCPO_MODE=auth
export GOFR_JWT_SECRET="your-secret-key-here"
export GOFR_DOC_DATA_DIR="/var/gofr_doc/data"

Development (Public Access)
---------------------------
export GOFR_DOC_MCPO_MODE=public
# No JWT_SECRET needed

Testing
-------
# Set by test framework automatically
export GOFR_DOC_DATA_DIR="/tmp/gofr_doc-test-XXXXX"

═════════════════════════════════════════════════════════════════════════════

QUICK START
═══════════

1. Minimal Setup (Development)
   export GOFR_DOC_MCP_PORT=8010
   export GOFR_DOC_WEB_PORT=8012
   python app/main_mcp.py

2. Authenticated Setup (Production)
   export GOFR_DOC_MCPO_MODE=auth
   export GOFR_JWT_SECRET="$(openssl rand -hex 32)"
   export GOFR_DOC_DATA_DIR="/var/gofr-doc/data"
   python app/main_mcp.py

3. Docker Setup
   # See docker/docker-compose.yml for container configuration

═════════════════════════════════════════════════════════════════════════════

VALIDATION
══════════

To check your configuration:
  python -c "from app.config_docs import validate_configuration; \\
             valid, errors = validate_configuration(); \\
             print('Valid!' if valid else '\\n'.join(errors))"

To view current configuration:
  python -c "from app.config_docs import get_config_summary; \\
             import json; \\
             print(json.dumps(get_config_summary(), indent=2))"

═════════════════════════════════════════════════════════════════════════════
"""
    print(help_text)


if __name__ == "__main__":
    print_configuration_help()
    print("\n" + "=" * 79)
    print("CURRENT CONFIGURATION")
    print("=" * 79)

    import json

    config = get_config_summary()
    print(json.dumps(config, indent=2))

    print("\n" + "=" * 79)
    print("VALIDATION")
    print("=" * 79)

    is_valid, errors = validate_configuration()
    if is_valid:
        print("✅ Configuration is valid")
    else:
        print("❌ Configuration errors:")
        for error in errors:
            print(f"   • {error}")
