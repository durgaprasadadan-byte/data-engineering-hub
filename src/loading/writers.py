"""Loading: Parquet (CSV fallback), SQLite warehouse, optional PostgreSQL."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pandas as pd

from src.monitoring.logging_config import get_logger

log = get_logger("loading")


def write_table(df: pd.DataFrame, directory: Path, name: str) -> dict:
    """Write Parquet if pyarrow/fastparquet is installed, otherwise CSV. Returns {path, format}."""
    directory.mkdir(parents=True, exist_ok=True)
    try:
        path = directory / f"{name}.parquet"
        df.to_parquet(path, index=False)
        return {"path": str(path), "format": "parquet"}
    except ImportError:
        path = directory / f"{name}.csv"
        df.to_csv(path, index=False)
        return {"path": str(path), "format": "csv"}


def read_table(directory: Path, name: str) -> pd.DataFrame | None:
    for ext, reader in ((".parquet", pd.read_parquet), (".csv", pd.read_csv)):
        p = directory / f"{name}{ext}"
        if p.exists():
            try:
                return reader(p)
            except ImportError:
                continue
    return None


def load_sqlite(tables: dict[str, pd.DataFrame], db_path: Path) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with sqlite3.connect(db_path) as con:
        for name, df in tables.items():
            df.to_sql(name, con, if_exists="replace", index=False)
            total += len(df)
    return total


def load_postgres(tables: dict[str, pd.DataFrame], url: str | None = None) -> int:
    """Load into PostgreSQL when POSTGRES_URL is set and sqlalchemy+driver are installed.
    Raises RuntimeError with a clear message otherwise; callers treat it as optional."""
    url = url or os.getenv("POSTGRES_URL")
    if not url:
        raise RuntimeError("POSTGRES_URL is not set")
    try:
        from sqlalchemy import create_engine
    except ImportError as exc:
        raise RuntimeError("sqlalchemy is not installed") from exc
    engine = create_engine(url)
    total = 0
    for name, df in tables.items():
        df.to_sql(name, engine, if_exists="replace", index=False)
        total += len(df)
    return total
