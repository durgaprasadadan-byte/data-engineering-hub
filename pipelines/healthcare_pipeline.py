"""Healthcare claims pipeline: integrate -> standardize -> validate -> Silver -> Gold. Synthetic data only."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config.settings import SETTINGS
from src.loading.outputs import persist_gold
from src.loading.writers import write_table
from src.monitoring.logging_config import get_logger
from src.transformation.healthcare import add_processing_time, build_gold, standardize_tables
from src.validation.dq import append_history, build_report, write_quarantine
from src.validation.rules import validate

log = get_logger("healthcare")
TABLES = ["patients", "providers", "claims", "visits", "prescriptions"]


def run_healthcare(raw: dict[str, pd.DataFrame], *, out_dir: Path | None = None, quarantine_dir: Path | None = None,
                   dq_history_path: Path | None = None) -> dict:
    out_dir = out_dir or SETTINGS.warehouse_dir
    quarantine_dir = quarantine_dir or SETTINGS.quarantine_dir
    dq_history_path = dq_history_path or SETTINGS.dq_history_file
    missing = [t for t in TABLES if t not in raw]
    if missing:
        raise ValueError(f"Missing source tables: {missing}")
    base = out_dir / "healthcare"
    extracted = sum(len(raw[t]) for t in TABLES)

    std = standardize_tables({t: raw[t] for t in TABLES})
    transformed = sum(len(d) for d in std.values())
    clean, quarantined, validators = {}, {}, []
    for t in ["patients", "providers", "claims", "visits", "prescriptions"]:
        v = validate("healthcare", t, std[t], clean)
        validators.append(v)
        clean[t], quarantined[t] = v.split()
    report = build_report(validators)
    append_history(report, dq_history_path, "healthcare")
    for t, q in quarantined.items():
        write_quarantine(q, f"healthcare_{t}", report["report_id"], quarantine_dir)

    silver = dict(clean)
    silver["claims"] = add_processing_time(clean["claims"])
    formats = {f"silver_{t}": write_table(d, base / "silver", t)["format"] for t, d in silver.items()}
    gold = build_gold(silver["claims"], silver["providers"], silver["patients"])
    loaded = sum(len(d) for d in silver.values())
    persist_gold("healthcare", gold, {"pipeline": "healthcare", "engine": "pandas"}, out_dir)
    return {
        "extracted": extracted, "transformed": transformed, "loaded": loaded, "rejected": extracted - loaded,
        "quality_score": report["overall_score"],
        "validation_status": "passed" if report["checks_failed"] == 0 else "quarantined",
        "silver": silver, "gold": gold, "quarantined": quarantined, "dq_report": report,
        "storage_formats": formats,
    }
