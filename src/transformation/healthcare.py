"""Healthcare standardization and analytics (synthetic/de-identified data only)."""
from __future__ import annotations

import pandas as pd


def standardize_id(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.upper()


def standardize_tables(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Standardize patient/provider identifiers everywhere they occur; dedupe exact claim_id repeats."""
    out = {k: v.copy() for k, v in raw.items()}
    for t, df in out.items():
        for col in ("patient_id", "provider_id"):
            if col in df:
                df[col] = standardize_id(df[col])
    for t, key in (("claims", "claim_id"), ("visits", "visit_id"), ("prescriptions", "rx_id"),
                   ("patients", "patient_id"), ("providers", "provider_id")):
        out[t] = out[t].drop_duplicates(key, keep="first").reset_index(drop=True)
    return out


def add_processing_time(claims: pd.DataFrame) -> pd.DataFrame:
    out = claims.copy()
    sub, proc = pd.to_datetime(out["submitted_date"], errors="coerce"), pd.to_datetime(out["processed_date"], errors="coerce")
    out["processing_days"] = (proc - sub).dt.days
    out["service_month"] = pd.to_datetime(out["service_date"], errors="coerce").dt.strftime("%Y-%m")
    return out


def build_gold(claims: pd.DataFrame, providers: pd.DataFrame, patients: pd.DataFrame) -> dict[str, pd.DataFrame]:
    c = claims.merge(providers[["provider_id", "specialty", "hospital"]], on="provider_id", how="left") \
              .merge(patients[["patient_id", "age_group"]], on="patient_id", how="left")
    cost_dx = (c.groupby("diagnosis_code").agg(claims=("claim_id", "count"), total_cost=("claim_amount", "sum"),
                                              avg_cost=("claim_amount", "mean")).round(2).reset_index()
               .sort_values("total_cost", ascending=False))
    cost_age = (c.groupby("age_group").agg(claims=("claim_id", "count"), avg_cost=("claim_amount", "mean"))
                .round(2).reset_index())
    monthly = (c.groupby("service_month").agg(claims=("claim_id", "count"), total_cost=("claim_amount", "sum"))
               .round(2).reset_index().sort_values("service_month"))
    perf = (c.groupby(["provider_id", "specialty", "hospital"]).agg(
        claims=("claim_id", "count"), total_billed=("claim_amount", "sum"), avg_claim=("claim_amount", "mean"),
        avg_processing_days=("processing_days", "mean"),
        denial_rate=("status", lambda s: round(100 * (s == "denied").mean(), 2))).round(2).reset_index()
        .sort_values("total_billed", ascending=False))
    summary = pd.DataFrame([{"total_claims": len(c), "total_cost": round(float(c["claim_amount"].sum()), 2),
                             "avg_claim": round(float(c["claim_amount"].mean()), 2) if len(c) else 0.0,
                             "avg_processing_days": round(float(c["processing_days"].mean()), 2) if c["processing_days"].notna().any() else None,
                             "denial_rate_pct": round(100 * float((c["status"] == "denied").mean()), 2) if len(c) else 0.0}])
    return {"gold_summary": summary, "gold_cost_by_diagnosis": cost_dx, "gold_cost_by_age_group": cost_age,
            "gold_monthly_cost": monthly, "gold_provider_performance": perf}
