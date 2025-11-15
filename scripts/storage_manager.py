#!/usr/bin/env python3
"""Storage Management CLI

Command-line utility to manage stored images including purging old data.
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage.file_storage import FileStorage
from app.logger import Logger, session_logger


def purge_images(args):
    """Purge images older than specified age"""
    logger: Logger = session_logger

    try:
        storage = FileStorage(args.storage_dir)

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

    try:
        storage = FileStorage(args.storage_dir)
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

    try:
        storage = FileStorage(args.storage_dir)
        images = storage.list_images()

        total_size = 0
        groups = {}

        for guid in images:
            if guid in storage.metadata:
                meta = storage.metadata[guid]
                size = meta.get("size", 0)
                group = meta.get("group", "none")

                total_size += size
                groups[group] = groups.get(group, 0) + 1

        logger.info("Storage Statistics:")
        logger.info(f"Total images:     {len(images)}")
        logger.info(f"Total size:       {total_size:,} bytes ({total_size / (1024*1024):.2f} MB)")
        logger.info(f"Storage dir:      {storage.storage_dir}")

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
        description="doco Storage Manager - Manage stored images and data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Purge images older than 30 days
  python storage_manager.py purge --age-days 30

  # Purge all images in 'test_group'
  python storage_manager.py purge --age-days 0 --group test_group --yes

  # List all images with details
  python storage_manager.py list --verbose

  # Show storage statistics
  python storage_manager.py stats
        """,
    )

    parser.add_argument(
        "--storage-dir",
        type=str,
        default=None,
        help="Storage directory (default: from app.config)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Purge command
    purge_parser = subparsers.add_parser("purge", help="Purge old images")
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
        help="Skip confirmation prompt",
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List stored images")
    list_parser.add_argument(
        "--group",
        type=str,
        default=None,
        help="Filter by group",
    )
    list_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed information",
    )

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show storage statistics")

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
