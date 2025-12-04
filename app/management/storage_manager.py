#!/usr/bin/env python3
"""Storage Management CLI

Command-line utility to manage stored sessions and data including purging old data,
listing sessions, and displaying storage statistics.
"""

import argparse
import sys
import json
import os
from pathlib import Path
from typing import Optional
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.storage.file_storage import FileStorage
from app.logger import Logger, session_logger
from app.config import Config


def resolve_storage_dir(cli_dir: Optional[str], data_root: Optional[str] = None) -> str:
    """
    Resolve storage directory with priority chain.

    Priority:
    1. CLI --data-root argument (storage/subdirectory)
    2. CLI --storage-dir argument (legacy)
    3. DOCO_DATA environment variable
    4. Config defaults
    """
    # Priority 1: --data-root points to data directory, storage/ is subdirectory
    if data_root:
        return str(Path(data_root) / "storage")

    # Priority 2: Legacy --storage-dir argument
    if cli_dir:
        return cli_dir

    # Priority 3: DOCO_DATA environment variable
    doco_data = os.environ.get("DOCO_DATA")
    if doco_data:
        return str(Path(doco_data) / "storage")

    # Priority 4: Config defaults
    return str(Config.get_storage_dir())


def purge_documents(args):
    """Purge documents older than specified age"""
    logger: Logger = session_logger

    storage_dir = resolve_storage_dir(args.storage_dir, args.data_root)

    try:
        storage = FileStorage(storage_dir)

        if args.age_days == 0:
            if args.group:
                msg = f"Purging ALL documents in group '{args.group}'"
            else:
                msg = "Purging ALL documents"
            logger.warning(f"WARNING: {msg}")

            if not args.yes:
                response = input("Are you sure? (yes/no): ")
                if response.lower() != "yes":
                    logger.info("Purge cancelled.")
                    return 0

        deleted = storage.purge(age_days=args.age_days, group=args.group)

        logger.info(f"Purge completed: {deleted} document(s) deleted")
        return 0

    except Exception as e:
        logger.error(f"Error during purge: {str(e)}")
        return 1


def list_documents(args):
    """List stored documents"""
    logger: Logger = session_logger

    storage_dir = resolve_storage_dir(args.storage_dir, args.data_root)

    try:
        storage = FileStorage(storage_dir)
        documents = storage.list_documents(group=args.group)

        if not documents:
            logger.info("No documents found.")
            return 0

        logger.info(f"{len(documents)} Document(s) Found:")

        if args.verbose:
            logger.info(
                f"{'GUID':<40} {'Format':<8} {'Group':<15} {'Size (bytes)':<12} {'Created'}"
            )
            logger.info("-" * 100)

            for guid in documents:
                # Get metadata
                if guid in storage.metadata:
                    meta = storage.metadata[guid]
                    fmt = meta.get("format", "?")
                    grp = meta.get("group", "none")
                    size = meta.get("size", 0)
                    created = meta.get("created_at", "N/A")[:19] if "created_at" in meta else "N/A"
                else:
                    fmt = "?"
                    grp = "?"
                    size = 0
                    created = "N/A"

                logger.info(f"{guid:<40} {fmt:<8} {grp:<15} {size:<12} {created}")
        else:
            for guid in documents:
                logger.info(guid)

        return 0

    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        return 1


def stats(args):
    """Display storage statistics"""
    logger: Logger = session_logger

    storage_dir = resolve_storage_dir(args.storage_dir, args.data_root)

    try:
        storage = FileStorage(storage_dir)
        documents = storage.list_documents(group=args.group)

        total_size = 0
        groups = {}

        for guid in documents:
            if guid in storage.metadata:
                meta = storage.metadata[guid]
                size = meta.get("size", 0)
                group = meta.get("group", "none")

                total_size += size
                groups[group] = groups.get(group, 0) + 1

        group_filter = f" in group '{args.group}'" if args.group else ""
        logger.info(f"Storage Statistics{group_filter}:")
        logger.info(f"Total documents:  {len(documents)}")
        logger.info(f"Total size:       {total_size:,} bytes ({total_size / (1024*1024):.2f} MB)")
        logger.info(f"Storage dir:      {storage_dir}")

        if groups:
            logger.info("Documents by group:")
            for group, count in sorted(groups.items()):
                logger.info(f"  {group:<15} {count:>5} documents")

        return 0

    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return 1


def resolve_sessions_dir(cli_dir: Optional[str], data_root: Optional[str] = None) -> str:
    """
    Resolve sessions directory with priority chain.

    Priority:
    1. CLI --data-root argument (sessions/subdirectory)
    2. CLI --sessions-dir argument (legacy)
    3. DOCO_DATA environment variable
    4. Config defaults
    """
    # Priority 1: --data-root points to data directory, sessions/ is subdirectory
    if data_root:
        return str(Path(data_root) / "sessions")

    # Priority 2: Legacy --sessions-dir argument
    if cli_dir:
        return cli_dir

    # Priority 3: DOCO_DATA environment variable
    doco_data = os.environ.get("DOCO_DATA")
    if doco_data:
        return str(Path(doco_data) / "sessions")

    # Priority 4: Config defaults
    return str(Config.get_sessions_dir())


def list_sessions(args):
    """List stored sessions"""
    logger: Logger = session_logger

    sessions_dir = resolve_sessions_dir(args.sessions_dir, args.data_root)
    sessions_path = Path(sessions_dir)

    try:
        if not sessions_path.exists():
            logger.info(f"Sessions directory not found: {sessions_dir}")
            return 0

        session_files = list(sessions_path.glob("*.json"))

        if not session_files:
            logger.info("No sessions found.")
            return 0

        logger.info(f"{len(session_files)} Session(s) Found:")

        if args.verbose:
            logger.info(f"{'Session ID':<40} {'Template':<20} {'Fragments':<10} {'Created'}")
            logger.info("-" * 90)

            for session_file in sorted(session_files):
                try:
                    with open(session_file, "r") as f:
                        data = json.load(f)
                        session_id = data.get("session_id", session_file.stem)
                        template = data.get("template_id", "N/A")
                        fragments = len(data.get("fragments", []))
                        created = (
                            data.get("created_at", "N/A")[:19] if "created_at" in data else "N/A"
                        )

                        logger.info(f"{session_id:<40} {template:<20} {fragments:<10} {created}")
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in {session_file.name}")
        else:
            for session_file in sorted(session_files):
                logger.info(session_file.stem)

        return 0

    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}")
        return 1


def purge_sessions(args):
    """Purge sessions older than specified age"""
    logger: Logger = session_logger

    sessions_dir = resolve_sessions_dir(args.sessions_dir, args.data_root)
    sessions_path = Path(sessions_dir)

    try:
        if not sessions_path.exists():
            logger.info(f"Sessions directory not found: {sessions_dir}")
            return 0

        session_files = list(sessions_path.glob("*.json"))

        if not session_files:
            logger.info("No sessions found to purge.")
            return 0

        # Filter by age
        deleted_count = 0
        now = datetime.now().timestamp()
        cutoff_time = now - (args.age_days * 86400)  # Convert days to seconds

        sessions_to_delete = []
        for session_file in session_files:
            try:
                with open(session_file, "r") as f:
                    data = json.load(f)
                    created_at_str = data.get("created_at", "")

                    if created_at_str:
                        # Parse ISO format timestamp
                        created_at = datetime.fromisoformat(
                            created_at_str.replace("Z", "+00:00")
                        ).timestamp()
                        if created_at < cutoff_time:
                            sessions_to_delete.append(
                                (session_file, data.get("session_id", session_file.stem))
                            )
            except (json.JSONDecodeError, ValueError):
                pass

        if not sessions_to_delete:
            logger.info("No sessions match the purge criteria.")
            return 0

        if args.age_days == 0:
            msg = f"Purging ALL {len(sessions_to_delete)} sessions"
            logger.warning(f"WARNING: {msg}")

            if not args.yes:
                response = input("Are you sure? (yes/no): ")
                if response.lower() != "yes":
                    logger.info("Purge cancelled.")
                    return 0

        for session_file, session_id in sessions_to_delete:
            try:
                session_file.unlink()
                deleted_count += 1
                if args.verbose:
                    logger.info(f"Deleted session: {session_id}")
            except Exception as e:
                logger.warning(f"Failed to delete session {session_id}: {str(e)}")

        logger.info(f"Purge completed: {deleted_count} session(s) deleted")
        return 0

    except Exception as e:
        logger.error(f"Error during purge: {str(e)}")
        return 1


def sessions_stats(args):
    """Show sessions statistics"""
    logger: Logger = session_logger

    sessions_dir = resolve_sessions_dir(args.sessions_dir, args.data_root)
    sessions_path = Path(sessions_dir)

    try:
        if not sessions_path.exists():
            logger.info(f"Sessions directory not found: {sessions_dir}")
            return 0

        session_files = list(sessions_path.glob("*.json"))

        if not session_files:
            logger.info("No sessions found.")
            return 0

        total_size = 0
        templates = {}
        oldest_created = None
        newest_created = None

        for session_file in session_files:
            try:
                total_size += session_file.stat().st_size

                with open(session_file, "r") as f:
                    data = json.load(f)
                    template = data.get("template_id", "unknown")
                    templates[template] = templates.get(template, 0) + 1

                    created_at_str = data.get("created_at", "")
                    if created_at_str:
                        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                        if oldest_created is None or created_at < oldest_created:
                            oldest_created = created_at
                        if newest_created is None or created_at > newest_created:
                            newest_created = created_at
            except (json.JSONDecodeError, ValueError):
                pass

        logger.info("Sessions Statistics:")
        logger.info(f"Total sessions:   {len(session_files)}")
        logger.info(f"Total size:       {total_size:,} bytes ({total_size / (1024):.2f} KB)")
        logger.info(f"Sessions dir:     {sessions_dir}")

        if oldest_created:
            logger.info(f"Oldest session:   {oldest_created.isoformat()}")
        if newest_created:
            logger.info(f"Newest session:   {newest_created.isoformat()}")

        if templates:
            logger.info("Sessions by template:")
            for template, count in sorted(templates.items()):
                logger.info(f"  {template:<25} {count:>5} sessions")

        return 0

    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="doco Storage Manager - Manage stored sessions and rendered documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Storage Commands (manage rendered documents)
  python -m app.management.storage_manager storage purge --age-days 30
  python -m app.management.storage_manager storage list --verbose
  python -m app.management.storage_manager storage stats

  # Sessions Commands (manage document sessions)
  python -m app.management.storage_manager sessions list --verbose
  python -m app.management.storage_manager sessions purge --age-days 7
  python -m app.management.storage_manager sessions stats

  # Purge all with confirmation skip
  python -m app.management.storage_manager storage purge --age-days 0 --yes
  python -m app.management.storage_manager sessions purge --age-days 0 --yes

  # Filter storage by group
  python -m app.management.storage_manager storage list --group research --verbose
  python -m app.management.storage_manager storage stats --group research

  # Using with environment variables
  python -m app.management.storage_manager --doco-env PROD --data-root /path/to/data storage stats
  python -m app.management.storage_manager --gofr-doc-env TEST sessions list --verbose

Environment Variables:
    GOFR_DOC_ENV           Environment mode (TEST or PROD)
    GOFR_DOC_DATA          Data root directory (contains storage/ and sessions/)
    GOFR_DOC_TOKEN_STORE   Token store path
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
    parser.add_argument(
        "--data-root",
        type=str,
        default=os.environ.get("GOFR_DOC_DATA"),
        help="Data root directory (contains storage/ and sessions/)",
    )
    parser.add_argument(
        "--token-store",
        type=str,
        default=os.environ.get("DOCO_TOKEN_STORE"),
        help="Token store path",
    )

    # Legacy arguments (kept for backward compatibility)
    parser.add_argument(
        "--storage-dir",
        type=str,
        default=None,
        help="Storage directory path (default: project data/storage or DOCO_DATA_DIR env var)",
    )

    parser.add_argument(
        "--sessions-dir",
        type=str,
        default=None,
        help="Sessions directory path (default: project data/sessions or DOCO_DATA_DIR env var)",
    )

    subparsers = parser.add_subparsers(dest="resource", help="Resource to manage")

    # Storage subcommands
    storage_parser = subparsers.add_parser("storage", help="Manage rendered documents in storage")
    storage_subparsers = storage_parser.add_subparsers(dest="command", help="Storage command")

    # Storage purge
    storage_purge = storage_subparsers.add_parser(
        "purge",
        help="Purge rendered documents older than specified days",
    )
    storage_purge.add_argument(
        "--age-days",
        type=int,
        default=30,
        help="Delete documents older than this many days (0 = delete all, default: 30)",
    )
    storage_purge.add_argument(
        "--group",
        type=str,
        default=None,
        help="Only purge documents from this group",
    )
    storage_purge.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt when deleting all documents",
    )

    # Storage list
    storage_list = storage_subparsers.add_parser(
        "list",
        help="List stored rendered documents",
    )
    storage_list.add_argument(
        "--group",
        type=str,
        default=None,
        help="Filter by group name",
    )
    storage_list.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed information",
    )

    # Storage stats
    storage_stats = storage_subparsers.add_parser(
        "stats",
        help="Show storage statistics",
    )
    storage_stats.add_argument(
        "--group",
        type=str,
        default=None,
        help="Filter statistics by group name",
    )

    # Sessions subcommands
    sessions_parser = subparsers.add_parser("sessions", help="Manage document sessions")
    sessions_subparsers = sessions_parser.add_subparsers(dest="command", help="Sessions command")

    # Sessions list
    sessions_list = sessions_subparsers.add_parser(
        "list",
        help="List stored sessions",
    )
    sessions_list.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed information",
    )

    # Sessions purge
    sessions_purge = sessions_subparsers.add_parser(
        "purge",
        help="Purge sessions older than specified days",
    )
    sessions_purge.add_argument(
        "--age-days",
        type=int,
        default=30,
        help="Delete sessions older than this many days (0 = delete all, default: 30)",
    )
    sessions_purge.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt when deleting all sessions",
    )
    sessions_purge.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show deleted sessions",
    )

    # Sessions stats
    sessions_subparsers.add_parser(  # noqa: F841 - parser registered but reference not needed
        "stats",
        help="Show sessions statistics",
    )

    args = parser.parse_args()

    if not args.resource:
        parser.print_help()
        return 1

    # Handle storage commands
    if args.resource == "storage":
        if not args.command:
            storage_parser.print_help()
            return 1

        if args.command == "purge":
            return purge_documents(args)
        elif args.command == "list":
            return list_documents(args)
        elif args.command == "stats":
            return stats(args)

    # Handle sessions commands
    elif args.resource == "sessions":
        if not args.command:
            sessions_parser.print_help()
            return 1

        if args.command == "list":
            return list_sessions(args)
        elif args.command == "purge":
            return purge_sessions(args)
        elif args.command == "stats":
            return sessions_stats(args)

    else:
        logger: Logger = session_logger
        logger.error(f"Unknown resource: {args.resource}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
