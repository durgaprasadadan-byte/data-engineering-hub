"""Business analytics (Gold equivalents) computed in pandas from validated tables."""
from __future__ import annotations

import pandas as pd

from src.transformation.ecommerce import ntile_labels

SEGMENT = {1: "High", 2: "Medium", 3: "Low"}


def compute_gold(orders: pd.DataFrame, customers: pd.DataFrame, products: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """`orders` must include order_total and order_month. Cancelled orders are excluded from revenue."""
    live = orders[orders["status"] != "cancelled"]
    n_orders = live["order_id"].nunique()
    revenue = live["order_total"].sum()
    summary = pd.DataFrame([{
        "total_orders": n_orders,
        "total_revenue": round(float(revenue), 2),
        "avg_order_value": round(float(revenue) / n_orders, 2) if n_orders else 0.0,
    }])
    monthly = (live.groupby("order_month").agg(revenue=("order_total", "sum"), orders=("order_id", "count"))
               .round(2).reset_index().sort_values("order_month"))
    perf = (live.merge(products[["product_id", "product_name", "category"]], on="product_id")
            .groupby(["product_id", "product_name", "category"])
            .agg(units_sold=("quantity", "sum"), revenue=("order_total", "sum")).round(2).reset_index()
            .sort_values("revenue", ascending=False))
    spend = (live.groupby("customer_id").agg(total_spend=("order_total", "sum"), orders=("order_id", "count"))
             .round(2).reset_index().sort_values("total_spend", ascending=False).reset_index(drop=True))
    spend["segment"] = pd.Series(ntile_labels(len(spend))).map(SEGMENT)
    return {"gold_summary": summary, "gold_monthly_revenue": monthly,
            "gold_product_performance": perf, "gold_customer_segments": spend}
