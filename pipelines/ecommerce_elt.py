"""E-commerce ELT: raw -> Bronze -> Silver -> Gold using SQL (Spark SQL if available, else SQLite)."""
from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.config.settings import SETTINGS
from src.loading.outputs import persist_gold
from src.loading.writers import write_table
from src.monitoring.logging_config import get_logger
from src.processing.spark_session import spark_available
from src.processing.sql_layers import BRONZE_TABLES, GOLD_SQL, SILVER_SQL
from src.validation.dq import append_history, build_report
from src.validation.rules import validate

log = get_logger("ecommerce_elt")


def to_bronze(raw: dict[str, pd.DataFrame], source: str = "ingest") -> dict[str, pd.DataFrame]:
    """Raw copy as strings plus ingestion metadata (no cleaning)."""
    ts = datetime.now(timezone.utc).isoformat()
    out = {}
    for name in BRONZE_TABLES:
        b = raw[name].copy()
        for c in b.columns:
            b[c] = b[c].map(lambda v: None if pd.isna(v) else str(v))
        b["_ingested_at"], b["_source"] = ts, source
        out[name] = b
    return out


def run_layers_sqlite(bronze: dict[str, pd.DataFrame], layers: list[tuple[str, str]]) -> dict[str, pd.DataFrame]:
    con = sqlite3.connect(":memory:")
    try:
        for name, df in bronze.items():
            df.to_sql(f"bronze_{name}", con, index=False)
        out = {}
        for name, sql in layers:
            con.execute(f"CREATE TABLE {name} AS {sql}")
            out[name] = pd.read_sql(f"SELECT * FROM {name}", con)
        return out
    finally:
        con.close()


def run_elt(raw: dict[str, pd.DataFrame], *, out_dir: Path | None = None, engine: str = "auto",
            dq_history_path: Path | None = None) -> dict:
    """engine: 'auto' (Spark if available, else SQLite), 'spark' (fail if unavailable) or 'sqlite'."""
    out_dir = out_dir or SETTINGS.warehouse_dir
    dq_history_path = dq_history_path or SETTINGS.dq_history_file
    missing = [t for t in BRONZE_TABLES if t not in raw]
    if missing:
        raise ValueError(f"Missing source tables: {missing}")
    ok, why = spark_available()
    if engine == "spark" and not ok:
        raise RuntimeError(f"Spark requested but unavailable: {why}")
    use_spark = engine == "spark" or (engine == "auto" and ok)
    base = out_dir / "ecommerce_elt"

    t0 = time.perf_counter()
    bronze = to_bronze(raw)
    extracted = sum(len(b) for b in bronze.values())
    layers = SILVER_SQL + GOLD_SQL
    delta_used = False
    if use_spark:
        from src.processing.spark_elt import run_layers_spark
        results, fmt = run_layers_spark(bronze, layers, base / "delta")
        delta_used = fmt == "delta"
    else:
        results = run_layers_sqlite(bronze, layers)
    elapsed = round(time.perf_counter() - t0, 3)

    formats = {}
    for n, df in bronze.items():
        formats[f"bronze_{n}"] = write_table(df, base / "bronze", n)["format"]
    silver = {n: df for n, df in results.items() if n.startswith("silver_")}
    gold = {n: df for n, df in results.items() if n.startswith("gold_")}
    for n, df in silver.items():
        formats[n] = write_table(df, base / "silver", n)["format"]
    for n, df in gold.items():
        formats[n] = write_table(df, base / "gold", n)["format"]

    # Validate Silver with the shared DQ framework (report only; Silver already filtered)
    ctx = {k.removeprefix("silver_"): v for k, v in silver.items()}
    validators = [validate("ecommerce", t, ctx[t], ctx) for t in
                  ["customers", "products", "orders", "payments", "inventory"]]
    report = build_report(validators)
    append_history(report, dq_history_path, "ecommerce_elt")

    silver_rows = sum(len(d) for d in silver.values())
    engine_name = "spark-sql" if use_spark else "sqlite-sql"
    persist_gold("ecommerce", {n: d for n, d in gold.items()},
                 {"pipeline": "ecommerce_elt", "engine": engine_name, "delta": delta_used}, out_dir)
    return {
        "extracted": extracted, "transformed": silver_rows, "loaded": silver_rows,
        "rejected": sum(len(raw[t]) for t in BRONZE_TABLES) - silver_rows,
        "quality_score": report["overall_score"],
        "validation_status": "passed" if report["checks_failed"] == 0 else "quarantined",
        "bronze": bronze, "silver": silver, "gold": gold, "dq_report": report,
        "engine": engine_name, "delta": delta_used, "seconds": elapsed, "storage_formats": formats,
        "spark_status": why,
    }
