#!/usr/bin/env python3
"""JWT Token Management CLI

Command-line utility to create, list, and revoke JWT tokens for doco authentication.
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.auth import AuthService
from app.logger import Logger, session_logger


def resolve_jwt_secret(cli_secret: Optional[str]) -> Optional[str]:
    """Resolve JWT secret from CLI or environment variable."""

    return cli_secret or os.environ.get("DOCO_JWT_SECRET")


def create_token(args):
    """Create a new JWT token"""
    logger: Logger = session_logger

    # Validate JWT secret is provided
    jwt_secret = resolve_jwt_secret(args.secret)
    if not jwt_secret:
        logger.error("FATAL: No JWT secret provided")
        logger.error("Set DOCO_JWT_SECRET environment variable or use --secret flag")
        return 1

    # Initialize auth service
    auth_service = AuthService(
        secret_key=jwt_secret,
        token_store_path=args.token_store,
    )

    try:
        token = auth_service.create_token(group=args.group, expires_in_seconds=args.expires)

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

    # Validate JWT secret is provided
    jwt_secret = resolve_jwt_secret(args.secret)
    if not jwt_secret:
        logger.error("FATAL: No JWT secret provided")
        logger.error("Set DOCO_JWT_SECRET environment variable or use --secret flag")
        return 1

    # Initialize auth service
    auth_service = AuthService(
        secret_key=jwt_secret,
        token_store_path=args.token_store,
    )

    try:
        tokens = auth_service.list_tokens()

        if not tokens:
            logger.info("No tokens found.")
            return 0

        logger.info(f"{len(tokens)} Token(s) Found:")
        logger.info(f"{'Group':<20} {'Issued':<25} {'Expires':<25} {'Token (first 20 chars)'}")
        logger.info("-" * 100)

        for token, info in tokens.items():
            group = info.get("group", "N/A")
            issued = info.get("issued_at", "N/A")
            expires = info.get("expires_at", "N/A")

            # Parse dates if possible

            try:
                issued_dt = datetime.fromisoformat(issued)
                issued_str = issued_dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                issued_str = issued[:16] if len(issued) > 16 else issued

            try:
                expires_dt = datetime.fromisoformat(expires)
                expires_str = expires_dt.strftime("%Y-%m-%d %H:%M")

                # Check if expired
                if expires_dt < datetime.utcnow():
                    expires_str += " (EXPIRED)"
            except Exception:
                expires_str = expires[:16] if len(expires) > 16 else expires

            token_preview = token[:20] + "..."
            logger.info(f"{group:<20} {issued_str:<25} {expires_str:<25} {token_preview}")

        return 0
    except Exception as e:
        logger.error(f"Error listing tokens: {str(e)}")
        return 1


def revoke_token(args):
    """Revoke a token"""
    logger: Logger = session_logger

    # Validate JWT secret is provided
    jwt_secret = resolve_jwt_secret(args.secret)
    if not jwt_secret:
        logger.error("FATAL: No JWT secret provided")
        logger.error("Set DOCO_JWT_SECRET environment variable or use --secret flag")
        return 1

    # Initialize auth service
    auth_service = AuthService(
        secret_key=jwt_secret,
        token_store_path=args.token_store,
    )

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

    # Validate JWT secret is provided
    jwt_secret = resolve_jwt_secret(args.secret)
    if not jwt_secret:
        logger.error("FATAL: No JWT secret provided")
        logger.error("Set DOCO_JWT_SECRET environment variable or use --secret flag")
        return 1

    # Initialize auth service
    auth_service = AuthService(
        secret_key=jwt_secret,
        token_store_path=args.token_store,
    )

    try:
        token_info = auth_service.verify_token(args.token)

        logger.info("Token is valid")
        logger.info(f"Group:      {token_info.group}")
        logger.info(f"Issued:     {token_info.issued_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        logger.info(f"Expires:    {token_info.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")

        # Check if close to expiry
        now = datetime.utcnow()
        days_until_expiry = (token_info.expires_at - now).days
        if days_until_expiry < 7:
            logger.warning(f"Warning: Token expires in {days_until_expiry} days")

        return 0
    except Exception as e:
        logger.error(f"Token validation failed: {str(e)}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="doco JWT Token Manager - Create and manage authentication tokens",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a token for the 'research' group that expires in 30 days (2592000 seconds)
  python token_manager.py create --group research --expires 2592000

  # Create a token that expires in 1 hour
  python token_manager.py create --group research --expires 3600

  # List all tokens
  python token_manager.py list

  # Verify a token
  python token_manager.py verify --token eyJhbGc...

  # Revoke a token
  python token_manager.py revoke --token eyJhbGc...

Environment Variables:
    DOCO_JWT_SECRET     JWT secret key for token signing and verification
        """,
    )

    parser.add_argument(
        "--secret",
        type=str,
        help="JWT secret key (default: DOCO_JWT_SECRET env var)",
    )
    parser.add_argument(
        "--token-store",
        type=str,
        default=None,
        help="Path to token store file (default: /tmp/doco_tokens.json)",
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
