"""Optional Databricks SQL connectivity. Requires `pip install databricks-sql-connector` and credentials in
environment variables (DATABRICKS_HOST, DATABRICKS_HTTP_PATH, DATABRICKS_TOKEN). Nothing is hardcoded."""
from __future__ import annotations

import os
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DatabricksConfig:
    host: str
    http_path: str
    token: str


def get_config() -> DatabricksConfig | None:
    host, path, token = (os.getenv("DATABRICKS_HOST"), os.getenv("DATABRICKS_HTTP_PATH"), os.getenv("DATABRICKS_TOKEN"))
    if host and path and token:
        return DatabricksConfig(host.replace("https://", "").rstrip("/"), path, token)
    return None


def missing_settings() -> list[str]:
    return [k for k in ("DATABRICKS_HOST", "DATABRICKS_HTTP_PATH", "DATABRICKS_TOKEN") if not os.getenv(k)]


def connector_installed() -> bool:
    try:
        import databricks.sql  # noqa: F401
        return True
    except ImportError:
        return False


def run_query(cfg: DatabricksConfig, query: str) -> pd.DataFrame:
    if not connector_installed():
        raise RuntimeError("databricks-sql-connector is not installed")
    from databricks import sql as dbsql
    with dbsql.connect(server_hostname=cfg.host, http_path=cfg.http_path, access_token=cfg.token) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_text_safe(query))
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
    return pd.DataFrame([list(r) for r in rows], columns=cols)


def sql_text_safe(sql_text: str) -> str:
    """Single statement only; the page uses this for read-only connectivity checks."""
    s = sql_text.strip().rstrip(";")
    if ";" in s:
        raise ValueError("Only a single SQL statement is allowed")
    return s


def test_connection() -> tuple[bool, str]:
    cfg = get_config()
    if cfg is None:
        return False, f"Not configured. Missing: {', '.join(missing_settings())}"
    try:
        df = run_query(cfg, "SELECT 1 AS ok")
        return bool(len(df)), "Connected to Databricks SQL warehouse"
    except Exception as exc:  # noqa: BLE001
        return False, f"Connection failed: {type(exc).__name__}: {exc}"
