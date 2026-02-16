"""Housekeeper Service — periodic storage pruning for gofr-doc.

Runs in a loop, calling ``prune_size`` from the storage manager to keep the
rendered-documents directory under a configurable size limit.

Environment Variables:
    GOFR_DOC_HOUSEKEEPING_INTERVAL_MINS  Check interval in minutes (default: 60)
    GOFR_DOC_MAX_STORAGE_MB              Max storage in MiB          (default: 1024)
    GOFR_DOC_HOUSEKEEPER_LOCK_STALE_SECONDS  Stale-lock timeout      (default: 3600)
    GOFR_DOC_STORAGE_DIR                 Storage directory override
"""

import time
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.management.storage_manager import prune_size
from app.logger import session_logger as logger


def _parse_positive_int_env(name: str, default: int, minimum: int = 1) -> int:
    """Parse a positive integer from an environment variable with fallback."""
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default

    try:
        value = int(raw)
        if value < minimum:
            raise ValueError(f"must be >= {minimum}")
        return value
    except Exception:
        logger.warning(
            "housekeeper.invalid_env",
            variable=name,
            provided_value=raw,
            default_value=default,
        )
        return default


class HousekeeperArgs:
    """Mock arguments object matching what ``prune_size`` expects."""

    def __init__(self, max_mb: int, storage_dir: str | None = None, group: str | None = None):
        self.max_mb = max_mb
        self.storage_dir = storage_dir
        self.data_root = None
        self.group = group
        self.verbose = False
        self.lock_stale_seconds = _parse_positive_int_env(
            "GOFR_DOC_HOUSEKEEPER_LOCK_STALE_SECONDS", 3600, minimum=30
        )


def main() -> None:
    logger.info("Starting gofr-doc housekeeper service")

    while True:
        interval_mins = _parse_positive_int_env("GOFR_DOC_HOUSEKEEPING_INTERVAL_MINS", 60)
        max_mb = _parse_positive_int_env("GOFR_DOC_MAX_STORAGE_MB", 1024)
        storage_dir = os.environ.get("GOFR_DOC_STORAGE_DIR")

        try:
            logger.info(
                "housekeeper.cycle_start",
                interval_mins=interval_mins,
                max_mb=max_mb,
                storage_dir=storage_dir,
            )

            args = HousekeeperArgs(max_mb=max_mb, storage_dir=storage_dir)
            result = prune_size(args)

            if result != 0:
                logger.warning("housekeeper.cycle_nonzero", status=result)
            else:
                logger.info("housekeeper.cycle_ok")

        except Exception as e:
            logger.error("housekeeper.cycle_failed", error=str(e), cause=type(e).__name__)

        # Sleep until next cycle
        sleep_seconds = max(1, interval_mins * 60)
        logger.info("housekeeper.sleep", sleep_seconds=sleep_seconds, interval_mins=interval_mins)
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    main()
