#!/usr/bin/env python3
"""JWT Token Management CLI

Command-line utility to create, list, and revoke JWT tokens for gofr-doc authentication.
Uses Vault-backed stores via gofr-common.
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gofr_common.auth import (
    AuthService,
    JwtSecretProvider,
    create_stores_from_env,
    create_vault_client_from_env,
    GroupRegistry,
)
from app.logger import Logger, session_logger

ENV_PREFIX = "GOFR_DOC"


def _build_auth_service(args) -> AuthService:
    """Build an AuthService from environment (Vault-backed)."""
    logger: Logger = session_logger

    vault_client = create_vault_client_from_env(ENV_PREFIX, logger=logger)
    secret_provider = JwtSecretProvider(
        vault_client=vault_client,
        logger=logger,
    )
    token_store, group_store = create_stores_from_env(
        ENV_PREFIX,
        vault_client=vault_client,
    )
    group_registry = GroupRegistry(store=group_store)

    return AuthService(
        token_store=token_store,
        group_registry=group_registry,
        secret_provider=secret_provider,
        env_prefix=ENV_PREFIX,
    )


def create_token(args):
    """Create a new JWT token"""
    logger: Logger = session_logger

    auth_service = _build_auth_service(args)

    try:
        token = auth_service.create_token(groups=[args.group], expires_in_seconds=args.expires)

        # Convert seconds to human-readable format
        days = args.expires // 86400
        hours = (args.expires % 86400) // 3600
        minutes = (args.expires % 3600) // 60

        expiry_str = []
        if days > 0:
            expiry_str.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            expiry_str.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            expiry_str.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if not expiry_str:
            expiry_str.append(f"{args.expires} second{'s' if args.expires != 1 else ''}")

        logger.info("JWT Token Created Successfully")
        logger.info(f"Group:      {args.group}")
        logger.info(f"Expires:    {', '.join(expiry_str)} ({args.expires} seconds)")
        logger.info("Token:")
        logger.info(token)
        logger.info(
            "Save this token securely. Use it in the 'Authorization: Bearer <token>' header."
        )
        logger.info("Or pass it as the 'token' parameter in MCP tool calls.")

        return 0
    except Exception as e:
        logger.error(f"Error creating token: {str(e)}")
        return 1


def list_tokens(args):
    """List all tokens"""
    logger: Logger = session_logger

    auth_service = _build_auth_service(args)

    try:
        records = auth_service.list_tokens()

        if not records:
            logger.info("No tokens found.")
            return 0

        logger.info(f"{len(records)} Token(s) Found:")
        logger.info(f"{'Groups':<20} {'Created':<25} {'Expires':<25} {'Status':<10} {'Name'}")
        logger.info("-" * 100)

        for record in records:
            groups_str = ", ".join(record.groups) if record.groups else "N/A"
            created_str = record.created_at.strftime("%Y-%m-%d %H:%M")
            name_str = record.name or ""

            if record.expires_at:
                expires_str = record.expires_at.strftime("%Y-%m-%d %H:%M")
                if record.is_expired:
                    expires_str += " (EXPIRED)"
            else:
                expires_str = "never"

            logger.info(
                f"{groups_str:<20} {created_str:<25} {expires_str:<25} "
                f"{record.status:<10} {name_str}"
            )

        return 0
    except Exception as e:
        logger.error(f"Error listing tokens: {str(e)}")
        return 1


def revoke_token(args):
    """Revoke a token"""
    logger: Logger = session_logger

    auth_service = _build_auth_service(args)

    try:
        auth_service.revoke_token(args.token)
        logger.info("Token revoked successfully")
        return 0
    except Exception as e:
        logger.error(f"Error revoking token: {str(e)}")
        return 1


def verify_token(args):
    """Verify a token"""
    logger: Logger = session_logger

    auth_service = _build_auth_service(args)

    try:
        token_info = auth_service.verify_token(args.token)

        logger.info("Token is valid")
        logger.info(f"Groups:     {', '.join(token_info.groups)}")
        logger.info(f"Issued:     {token_info.issued_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if token_info.expires_at:
            logger.info(f"Expires:    {token_info.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")

            # Check if close to expiry
            now = datetime.utcnow()
            days_until_expiry = (token_info.expires_at - now).days
            if days_until_expiry < 7:
                logger.warning(f"Warning: Token expires in {days_until_expiry} days")
        else:
            logger.info("Expires:    never")

        return 0
    except Exception as e:
        logger.error(f"Token validation failed: {str(e)}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="gofr-doc JWT Token Manager - Create and manage authentication tokens (Vault-backed)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a token for the 'research' group that expires in 30 days (2592000 seconds)
  python -m app.management.token_manager create --group research --expires 2592000

  # Create a token that expires in 1 hour
  python -m app.management.token_manager create --group research --expires 3600

  # List all tokens
  python -m app.management.token_manager list

  # Verify a token
  python -m app.management.token_manager verify --token eyJhbGc...

  # Revoke a token
  python -m app.management.token_manager revoke --token eyJhbGc...

Environment Variables:
    GOFR_DOC_ENV            Environment mode (TEST or PROD)

    GOFR_DOC_AUTH_BACKEND   Must be "vault"
    GOFR_DOC_VAULT_URL      Vault server URL
    GOFR_DOC_VAULT_TOKEN    Vault authentication token
        """,
    )

    # Global arguments
    parser.add_argument(
        "--gofr-doc-env",
        type=str,
        default=os.environ.get("GOFR_DOC_ENV", "TEST"),
        choices=["TEST", "PROD"],
        help="Environment mode (TEST or PROD, default: from GOFR_DOC_ENV or TEST)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Create token
    create_parser = subparsers.add_parser("create", help="Create a new JWT token")
    create_parser.add_argument(
        "--group", type=str, required=True, help="Group name to associate with this token"
    )
    create_parser.add_argument(
        "--expires",
        type=int,
        default=2592000,
        help="Number of seconds until token expires (default: 2592000 = 30 days)",
    )

    # List tokens
    subparsers.add_parser("list", help="List all tokens")

    # Revoke token
    revoke_parser = subparsers.add_parser("revoke", help="Revoke a token")
    revoke_parser.add_argument("--token", type=str, required=True, help="Token to revoke")

    # Verify token
    verify_parser = subparsers.add_parser("verify", help="Verify a token")
    verify_parser.add_argument("--token", type=str, required=True, help="Token to verify")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    if args.command == "create":
        return create_token(args)
    elif args.command == "list":
        return list_tokens(args)
    elif args.command == "revoke":
        return revoke_token(args)
    elif args.command == "verify":
        return verify_token(args)
    else:
        logger: Logger = session_logger
        logger.error(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
