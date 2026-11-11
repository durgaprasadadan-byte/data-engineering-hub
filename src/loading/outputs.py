"""Persist and read pipeline outputs consumed by the Analytics dashboard."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.loading.writers import read_table, write_table


def persist_gold(project: str, tables: dict[str, pd.DataFrame], meta: dict, base: Path) -> dict:
    gold_dir = base / project / "gold"
    fmt = {name: write_table(df, gold_dir, name)["format"] for name, df in tables.items()}
    meta = {**meta, "generated_at": datetime.now(timezone.utc).isoformat(), "formats": fmt}
    (base / project).mkdir(parents=True, exist_ok=True)
    (base / project / "metrics.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    return meta


def load_gold(project: str, base: Path) -> tuple[dict[str, pd.DataFrame], dict] | None:
    mfile = base / project / "metrics.json"
    if not mfile.exists():
        return None
    meta = json.loads(mfile.read_text(encoding="utf-8"))
    gold_dir = base / project / "gold"
    tables = {}
    for name in meta.get("formats", {}):
        df = read_table(gold_dir, name)
        if df is not None:
            tables[name] = df
    return tables, meta
