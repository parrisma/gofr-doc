#!/usr/bin/env python3
"""Storage Management CLI

Command-line utility to manage stored sessions and data including purging old data,
listing sessions, and displaying storage statistics.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage.file_storage import FileStorage
from app.logger import Logger, session_logger
from app.config import Config


def resolve_storage_dir(cli_dir: Optional[str]) -> str:
    """Resolve storage directory from CLI, environment variable, or project default."""
    if cli_dir:
        return cli_dir
    
    return str(Config.get_storage_dir())


def purge_images(args):
    """Purge images older than specified age"""
    logger: Logger = session_logger

    storage_dir = resolve_storage_dir(args.storage_dir)

    try:
        storage = FileStorage(storage_dir)

        if args.age_days == 0:
            if args.group:
                msg = f"Purging ALL images in group '{args.group}'"
            else:
                msg = "Purging ALL images"
            logger.warning(f"WARNING: {msg}")

            if not args.yes:
                response = input("Are you sure? (yes/no): ")
                if response.lower() != "yes":
                    logger.info("Purge cancelled.")
                    return 0

        deleted = storage.purge(age_days=args.age_days, group=args.group)

        logger.info(f"Purge completed: {deleted} image(s) deleted")
        return 0

    except Exception as e:
        logger.error(f"Error during purge: {str(e)}")
        return 1


def list_images(args):
    """List stored images"""
    logger: Logger = session_logger

    storage_dir = resolve_storage_dir(args.storage_dir)

    try:
        storage = FileStorage(storage_dir)
        images = storage.list_images(group=args.group)

        if not images:
            logger.info("No images found.")
            return 0

        logger.info(f"{len(images)} Image(s) Found:")

        if args.verbose:
            logger.info(
                f"{'GUID':<40} {'Format':<8} {'Group':<15} {'Size (bytes)':<12} {'Created'}"
            )
            logger.info("-" * 100)

            for guid in images:
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
            for guid in images:
                logger.info(guid)

        return 0

    except Exception as e:
        logger.error(f"Error listing images: {str(e)}")
        return 1


def stats(args):
    """Show storage statistics"""
    logger: Logger = session_logger

    storage_dir = resolve_storage_dir(args.storage_dir)

    try:
        storage = FileStorage(storage_dir)
        images = storage.list_images(group=args.group)

        total_size = 0
        groups = {}

        for guid in images:
            if guid in storage.metadata:
                meta = storage.metadata[guid]
                size = meta.get("size", 0)
                group = meta.get("group", "none")

                total_size += size
                groups[group] = groups.get(group, 0) + 1

        group_filter = f" in group '{args.group}'" if args.group else ""
        logger.info(f"Storage Statistics{group_filter}:")
        logger.info(f"Total images:     {len(images)}")
        logger.info(f"Total size:       {total_size:,} bytes ({total_size / (1024*1024):.2f} MB)")
        logger.info(f"Storage dir:      {storage_dir}")

        if groups:
            logger.info("Images by group:")
            for group, count in sorted(groups.items()):
                logger.info(f"  {group:<15} {count:>5} images")

        return 0

    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="doco Storage Manager - Manage stored sessions and data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Purge images older than 30 days (uses project data/storage by default)
  python storage_manager.py purge --age-days 30

  # Purge all images in 'research' group (requires confirmation)
  python storage_manager.py purge --age-days 0 --group research

  # Skip confirmation for purge
  python storage_manager.py purge --age-days 0 --yes

  # List all images with details
  python storage_manager.py list --verbose

  # Filter images by group
  python storage_manager.py list --group research --verbose

  # Show storage statistics
  python storage_manager.py stats

  # Show statistics for a specific group
  python storage_manager.py stats --group research

  # Use custom storage directory
  python storage_manager.py --storage-dir /custom/path stats

Environment Variables:
    DOCO_DATA_DIR       Override project data directory (optional)
        """,
    )

    parser.add_argument(
        "--storage-dir",
        type=str,
        default=None,
        help="Storage directory path (default: project data/storage or DOCO_DATA_DIR env var)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Purge command
    purge_parser = subparsers.add_parser(
        "purge",
        help="Purge images older than specified days",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Purge images from storage by age or group"
    )
    purge_parser.add_argument(
        "--age-days",
        type=int,
        default=30,
        help="Delete images older than this many days (0 = delete all, default: 30)",
    )
    purge_parser.add_argument(
        "--group",
        type=str,
        default=None,
        help="Only purge images from this group",
    )
    purge_parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt when deleting all images",
    )

    # List command
    list_parser = subparsers.add_parser(
        "list",
        help="List stored images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="List and inspect stored images"
    )
    list_parser.add_argument(
        "--group",
        type=str,
        default=None,
        help="Filter by group name",
    )
    list_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed information (GUID, format, group, size, created time)",
    )

    # Stats command
    stats_parser = subparsers.add_parser(
        "stats",
        help="Show storage statistics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Display storage usage statistics"
    )
    stats_parser.add_argument(
        "--group",
        type=str,
        default=None,
        help="Filter statistics by group name",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    if args.command == "purge":
        return purge_images(args)
    elif args.command == "list":
        return list_images(args)
    elif args.command == "stats":
        return stats(args)
    else:
        logger: Logger = session_logger
        logger.error(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
