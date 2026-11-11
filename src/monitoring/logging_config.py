"""Logging setup shared by the app and pipelines."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from src.config.settings import SETTINGS

_FMT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def get_logger(name: str) -> logging.Logger:
    """Return a logger writing to console and logs/hub.log (configured once)."""
    root = logging.getLogger("hub")
    if not root.handlers:
        root.setLevel(SETTINGS.log_level.upper())
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter(_FMT))
        root.addHandler(console)
        try:
            SETTINGS.logs_dir.mkdir(parents=True, exist_ok=True)
            fh = RotatingFileHandler(SETTINGS.logs_dir / "hub.log", maxBytes=1_000_000, backupCount=3)
            fh.setFormatter(logging.Formatter(_FMT))
            root.addHandler(fh)
        except OSError:  # read-only filesystems (e.g. some hosted environments)
            root.warning("File logging unavailable; using console only.")
    return root.getChild(name)
