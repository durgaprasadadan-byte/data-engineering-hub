"""Ingestion from CSV, JSON, REST APIs and bundled sample directories."""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO

import pandas as pd

from src.monitoring.logging_config import get_logger

log = get_logger("ingestion")


@dataclass
class SourceInfo:
    name: str
    kind: str  # csv | json | api | sample
    location: str
    records: int
    columns: int
    loaded_at: str

    def as_dict(self) -> dict:
        return asdict(self)


def _info(name: str, kind: str, location: str, df: pd.DataFrame) -> SourceInfo:
    return SourceInfo(name, kind, location, len(df), df.shape[1], datetime.now(timezone.utc).isoformat())


def read_csv(src: str | Path | BinaryIO, name: str) -> tuple[pd.DataFrame, SourceInfo]:
    if hasattr(src, "seek"):
        src.seek(0)
    df = pd.read_csv(src)
    loc = str(src) if isinstance(src, (str, Path)) else getattr(src, "name", "<upload>")
    log.info("csv %s: %d records", name, len(df))
    return df, _info(name, "csv", loc, df)


def _records_from_json(obj: Any) -> list:
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for key in ("data", "records", "results", "items"):
            if isinstance(obj.get(key), list):
                return obj[key]
        for value in obj.values():
            if isinstance(value, list):
                return value
        return [obj]
    raise ValueError("Unsupported JSON structure")


def read_json(src: str | Path | BinaryIO, name: str) -> tuple[pd.DataFrame, SourceInfo]:
    """Accepts a JSON array, an object wrapping an array, or JSON Lines."""
    if hasattr(src, "seek"):
        src.seek(0)
    raw = Path(src).read_text(encoding="utf-8") if isinstance(src, (str, Path)) else src.read().decode("utf-8")
    try:
        records = _records_from_json(json.loads(raw))
    except json.JSONDecodeError:
        records = [json.loads(line) for line in raw.splitlines() if line.strip()]
    df = pd.json_normalize(records)
    loc = str(src) if isinstance(src, (str, Path)) else getattr(src, "name", "<upload>")
    log.info("json %s: %d records", name, len(df))
    return df, _info(name, "json", loc, df)


def fetch_api(url: str, name: str, *, params: dict | None = None, headers: dict | None = None,
              timeout: int = 15, retries: int = 2, backoff: float = 1.0,
              session: Any = None) -> tuple[pd.DataFrame, SourceInfo]:
    """GET a JSON endpoint with retries. Only http(s) URLs are allowed.

    Pass credentials via `headers` (read from environment/secrets, never hardcode).
    """
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError("Only http(s) URLs are supported")
    if session is None:
        import requests
        session = requests
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = session.get(url, params=params, headers=headers, timeout=timeout)
            resp.raise_for_status()
            df = pd.json_normalize(_records_from_json(resp.json()))
            log.info("api %s: %d records (attempt %d)", name, len(df), attempt + 1)
            return df, _info(name, "api", url, df)
        except Exception as exc:  # noqa: BLE001 - re-raised after retries
            last = exc
            log.warning("api %s failed (attempt %d): %s", name, attempt + 1, exc)
            if attempt < retries:
                time.sleep(backoff * (2 ** attempt))
    raise RuntimeError(f"API ingestion failed for {name}: {last}") from last


def load_sample_dir(directory: str | Path, names: list[str]) -> tuple[dict[str, pd.DataFrame], list[SourceInfo]]:
    """Load name.csv or name.json for each dataset name from a directory."""
    directory = Path(directory)
    tables: dict[str, pd.DataFrame] = {}
    infos: list[SourceInfo] = []
    for n in names:
        csv, js = directory / f"{n}.csv", directory / f"{n}.json"
        if csv.exists():
            df, info = read_csv(csv, n)
        elif js.exists():
            df, info = read_json(js, n)
        else:
            raise FileNotFoundError(f"No sample file for '{n}' in {directory}. Run: python -m scripts.generate_sample_data")
        info.kind = "sample"
        tables[n], _ = df, infos.append(info)
    return tables, infos
