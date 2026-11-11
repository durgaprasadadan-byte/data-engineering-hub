"""Central configuration. Reads environment variables; never hardcodes secrets."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # optional dependency
    def load_dotenv(*_a, **_k):  # type: ignore
        return False

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    app_name: str = "Durga Prasad Jinna"
    tagline: str = "Data Engineering Hub, Building Scalable, Reliable, and Intelligent Data Pipelines."
    env: str = os.getenv("APP_ENV", "local")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    logs_dir: Path = ROOT_DIR / "logs"
    sample_dir: Path = ROOT_DIR / "data" / "sample"
    diagrams_dir: Path = ROOT_DIR / "diagrams"
    run_history_file: Path = ROOT_DIR / "logs" / "pipeline_runs.jsonl"
    warehouse_dir: Path = ROOT_DIR / "data" / "warehouse"
    quarantine_dir: Path = ROOT_DIR / "data" / "quarantine"
    dq_history_file: Path = ROOT_DIR / "logs" / "dq_history.jsonl"


SETTINGS = Settings()

# Project catalogue; `status` reflects what is implemented in this repository.
PROJECTS: list[dict[str, str]] = [
    {"key": "ecommerce", "name": "E-commerce Data Engineering",
     "scenario": "ETL (Pandas) and ELT (Bronze/Silver/Gold via Spark SQL or SQLite) on customers, orders, products, payments, inventory.",
     "status": "Implemented"},
    {"key": "banking", "name": "Banking Fraud Detection Pipeline",
     "scenario": "Batch ETL, simulated streaming replay, feature engineering and a Scikit-learn fraud model.",
     "status": "Implemented"},
    {"key": "healthcare", "name": "Healthcare Claims Analytics",
     "scenario": "Integrates synthetic patients, claims, providers, visits and prescriptions into Silver and Gold reports.",
     "status": "Implemented"},
]

ROADMAP: list[dict[str, str]] = [
    {"phase": "1", "scope": "Foundation, navigation, home, architecture diagrams", "status": "Implemented"},
    {"phase": "2", "scope": "E-commerce ETL (Pandas)", "status": "Implemented"},
    {"phase": "3", "scope": "E-commerce ELT (Spark SQL / Delta; SQLite fallback)", "status": "Implemented (Spark path needs pyspark + Java)"},
    {"phase": "4", "scope": "Reusable data quality framework", "status": "Implemented"},
    {"phase": "5", "scope": "Databricks integration", "status": "Implemented (needs your workspace credentials)"},
    {"phase": "6", "scope": "Banking and healthcare pipelines", "status": "Implemented"},
    {"phase": "7", "scope": "Monitoring and analytics dashboards", "status": "Implemented"},
    {"phase": "8", "scope": "GitHub docs and Streamlit deployment", "status": "Implemented (deploy step is yours)"},
]
