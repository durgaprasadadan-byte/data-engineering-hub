"""E-commerce ETL: Extract -> Staging -> Transform -> Validate -> Load -> Analytics (Pandas)."""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from src.analytics.ecommerce import compute_gold
from src.config.settings import SETTINGS
from src.loading.outputs import persist_gold
from src.loading.writers import load_postgres, load_sqlite, write_table
from src.monitoring.logging_config import get_logger
from src.transformation import ecommerce as T
from src.validation.dq import append_history, build_report, write_quarantine
from src.validation.rules import validate

log = get_logger("ecommerce_etl")
TABLES = ["customers", "products", "orders", "payments", "inventory"]
STANDARDIZE = {"customers": T.standardize_customers, "products": T.standardize_products,
               "orders": T.standardize_orders, "payments": T.standardize_payments,
               "inventory": T.standardize_inventory}


def run_etl(raw: dict[str, pd.DataFrame], *, out_dir: Path | None = None, quarantine_dir: Path | None = None,
            dq_history_path: Path | None = None, use_postgres: bool = False) -> dict:
    out_dir = out_dir or SETTINGS.warehouse_dir
    quarantine_dir = quarantine_dir or SETTINGS.quarantine_dir
    dq_history_path = dq_history_path or SETTINGS.dq_history_file
    missing = [t for t in TABLES if t not in raw]
    if missing:
        raise ValueError(f"Missing source tables: {missing}")
    stages: list[dict] = []

    def stage(name: str, t0: float, **info):
        stages.append({"stage": name, "seconds": round(time.perf_counter() - t0, 3), **info})

    # Extract + Staging
    t0 = time.perf_counter()
    extracted = sum(len(raw[t]) for t in TABLES)
    etl_dir = out_dir / "ecommerce_etl"
    for t in TABLES:
        write_table(raw[t], etl_dir / "staging", t)
    stage("extract+staging", t0, records=extracted)

    # Transform (standardize, dedupe, cast)
    t0 = time.perf_counter()
    std = {t: STANDARDIZE[t](raw[t]) for t in TABLES}
    transformed = sum(len(df) for df in std.values())
    stage("transform", t0, records=transformed, duplicates_removed=extracted - transformed)

    # Validate in dependency order so referential checks use clean parents
    t0 = time.perf_counter()
    clean: dict[str, pd.DataFrame] = {}
    quarantined: dict[str, pd.DataFrame] = {}
    validators = []
    for t in ["customers", "products", "orders", "payments", "inventory"]:
        v = validate("ecommerce", t, std[t], clean)
        validators.append(v)
        clean[t], quarantined[t] = v.split()
    report = build_report(validators)
    append_history(report, dq_history_path, "ecommerce")
    q_rows = sum(len(q) for q in quarantined.values())
    run_id = report["report_id"]
    for t, q in quarantined.items():
        write_quarantine(q, f"ecommerce_{t}", run_id, quarantine_dir)
    stage("validate", t0, quarantined=q_rows, quality_score=report["overall_score"])

    # Enrich + Load
    t0 = time.perf_counter()
    clean["orders"] = T.enrich_orders(clean["orders"], clean["products"])
    gold = compute_gold(clean["orders"], clean["customers"], clean["products"])
    formats = {t: write_table(df, etl_dir / "warehouse", t)["format"] for t, df in clean.items()}
    loaded = load_sqlite({**clean, **gold}, etl_dir / "warehouse.db")
    pg = "not requested"
    if use_postgres:
        try:
            load_postgres(clean)
            pg = "loaded"
        except RuntimeError as exc:
            pg = f"skipped: {exc}"
    persist_gold("ecommerce", gold, {"pipeline": "ecommerce_etl", "engine": "pandas"}, out_dir)
    stage("load", t0, records=sum(len(d) for d in clean.values()), postgres=pg)

    loaded_rows = sum(len(d) for d in clean.values())
    return {
        "extracted": extracted, "transformed": transformed, "loaded": loaded_rows,
        "rejected": extracted - loaded_rows, "quality_score": report["overall_score"],
        "validation_status": "passed" if report["checks_failed"] == 0 else "quarantined",
        "tables": clean, "gold": gold, "quarantined": quarantined, "dq_report": report,
        "stages": stages, "storage_formats": formats, "sqlite_rows": loaded, "postgres": pg,
    }
