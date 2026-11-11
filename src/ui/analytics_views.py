"""Plotly views over Gold tables (used by project pages and the Analytics dashboard)."""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from src.ui.components import df_view, plot


def ecommerce_view(gold: dict, key: str = "ecom") -> None:
    s = gold["gold_summary"].iloc[0]
    c = st.columns(3)
    c[0].metric("Total revenue", f"${s['total_revenue']:,.2f}")
    c[1].metric("Total orders", f"{int(s['total_orders']):,}")
    c[2].metric("Average order value", f"${s['avg_order_value']:,.2f}")
    plot(px.line(gold["gold_monthly_revenue"], x="order_month", y="revenue", markers=True, title="Monthly revenue"))
    left, right = st.columns(2)
    seg = gold["gold_customer_segments"]
    with left:
        by = seg.groupby("segment").agg(customers=("customer_id", "count"), revenue=("total_spend", "sum")).reset_index()
        plot(px.bar(by, x="segment", y="revenue", color="segment", title="Revenue by customer segment (spend terciles)"))
    with right:
        plot(px.bar(gold["gold_product_performance"].head(10), x="product_name", y="revenue", color="category",
                    title="Top 10 products by revenue"))
    with st.expander("Product performance table"):
        df_view(gold["gold_product_performance"])


def banking_view(gold: dict, meta: dict) -> None:
    k = gold["gold_kpis"].iloc[0]
    c = st.columns(3)
    c[0].metric("Total transactions", f"{int(k['total_transactions']):,}")
    c[1].metric("Suspicious (labelled fraud)", f"{int(k['suspicious_transactions']):,}")
    c[2].metric("Fraud percentage", f"{k['fraud_pct']}%")
    m = meta.get("model_metrics", {})
    if m:
        c = st.columns(4)
        c[0].metric("Precision", m["precision"]); c[1].metric("Recall", m["recall"])
        c[2].metric("F1", m["f1"]); c[3].metric("ROC AUC", m["roc_auc"])
    d = gold["gold_daily_volume"]
    plot(px.line(d, x="date", y="transactions", title="Daily transaction volume"))
    plot(px.bar(d, x="date", y="fraud", title="Daily labelled-fraud count"))
    plot(px.bar(gold["gold_feature_importance"].head(10), x="importance", y="feature", orientation="h",
                title="Top feature importances"))


def healthcare_view(gold: dict) -> None:
    s = gold["gold_summary"].iloc[0]
    c = st.columns(4)
    c[0].metric("Valid claims", f"{int(s['total_claims']):,}")
    c[1].metric("Total cost", f"${s['total_cost']:,.0f}")
    c[2].metric("Avg processing days", s["avg_processing_days"])
    c[3].metric("Denial rate", f"{s['denial_rate_pct']}%")
    plot(px.line(gold["gold_monthly_cost"], x="service_month", y="total_cost", markers=True, title="Monthly claim cost"))
    left, right = st.columns(2)
    with left:
        plot(px.bar(gold["gold_cost_by_diagnosis"], x="diagnosis_code", y="total_cost", title="Cost by diagnosis code"))
    with right:
        plot(px.bar(gold["gold_cost_by_age_group"], x="age_group", y="avg_cost", title="Average claim by age group"))
    perf = gold["gold_provider_performance"]
    plot(px.scatter(perf, x="avg_processing_days", y="denial_rate", size="total_billed", color="specialty",
                    hover_data=["provider_id", "hospital"], title="Provider performance"))
    with st.expander("Provider performance report"):
        df_view(perf)
