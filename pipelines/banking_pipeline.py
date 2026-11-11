"""Banking fraud pipeline: ingest -> validate -> features -> store -> model -> (simulated) streaming."""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from src.config.settings import SETTINGS
from src.loading.outputs import persist_gold
from src.loading.writers import write_table
from src.monitoring.logging_config import get_logger
from src.processing.fraud_model import train_and_evaluate
from src.transformation.banking import build_features
from src.validation.dq import append_history, build_report, write_quarantine
from src.validation.rules import validate

log = get_logger("banking")
TABLES = ["customers", "accounts", "transactions"]


def run_banking(raw: dict[str, pd.DataFrame], *, out_dir: Path | None = None, quarantine_dir: Path | None = None,
                dq_history_path: Path | None = None, use_delta: bool = False) -> dict:
    out_dir = out_dir or SETTINGS.warehouse_dir
    quarantine_dir = quarantine_dir or SETTINGS.quarantine_dir
    dq_history_path = dq_history_path or SETTINGS.dq_history_file
    missing = [t for t in TABLES if t not in raw]
    if missing:
        raise ValueError(f"Missing source tables: {missing}")
    base = out_dir / "banking"
    extracted = len(raw["transactions"])   # fact table; customers/accounts are validated reference data

    clean, quarantined, validators = {}, {}, []
    for t in TABLES:
        v = validate("banking", t, raw[t], clean)
        validators.append(v)
        clean[t], quarantined[t] = v.split()
    report = build_report(validators)
    append_history(report, dq_history_path, "banking")
    for t, q in quarantined.items():
        write_quarantine(q, f"banking_{t}", report["report_id"], quarantine_dir)

    tx = clean["transactions"]
    feat = build_features(tx, clean["accounts"], clean["customers"])
    storage = write_table(feat, base / "validated", "transactions_features")
    storage["delta"] = "not requested"
    if use_delta:
        try:
            from src.processing.spark_banking import save_delta
            from src.processing.spark_session import get_spark
            spark, ok = get_spark("banking")
            if not ok:
                raise RuntimeError("delta-spark not installed")
            save_delta(spark.createDataFrame(feat.astype({"timestamp": str})), base / "delta" / "transactions")
            storage["delta"] = "written"
        except Exception as exc:  # noqa: BLE001
            storage["delta"] = f"skipped: {exc}"

    t0 = time.perf_counter()
    model, metrics, scored, importances = train_and_evaluate(feat)
    metrics["train_seconds"] = round(time.perf_counter() - t0, 2)

    daily = (feat.assign(date=feat["timestamp"].dt.strftime("%Y-%m-%d"))
             .groupby("date").agg(transactions=("transaction_id", "count"), fraud=("is_fraud", "sum"),
                                  volume=("amount", "sum")).round(2).reset_index())
    total = len(feat)
    kpis = pd.DataFrame([{"total_transactions": total, "suspicious_transactions": int(feat["is_fraud"].sum()),
                          "fraud_pct": round(100 * feat["is_fraud"].mean(), 2),
                          "precision": metrics["precision"], "recall": metrics["recall"], "f1": metrics["f1"]}])
    persist_gold("banking", {"gold_kpis": kpis, "gold_daily_volume": daily,
                             "gold_feature_importance": importances.rename_axis("feature").reset_index(name="importance")},
                 {"pipeline": "banking", "engine": "pandas+sklearn", "model_metrics": metrics}, out_dir)
    return {
        "extracted": extracted, "transformed": len(feat), "loaded": len(feat),
        "rejected": extracted - len(feat),
        "quality_score": report["overall_score"],
        "validation_status": "passed" if report["checks_failed"] == 0 else "quarantined",
        "features": feat, "quarantined": quarantined, "dq_report": report, "model": model,
        "metrics": metrics, "scored": scored, "importances": importances, "daily": daily,
        "kpis": kpis, "storage": storage,
    }
