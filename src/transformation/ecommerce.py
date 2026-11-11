"""Pandas transformations for the e-commerce ETL (standardize, dedupe, cast, enrich)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _s(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip()


def standardize_customers(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["customer_id"] = _s(out["customer_id"])
    out["name"] = _s(out["name"])
    out["email"] = _s(out["email"]).str.lower().fillna("unknown")      # missing values handled
    out["country"] = _s(out["country"]).str.upper()
    return out.drop_duplicates("customer_id", keep="first").reset_index(drop=True)


def standardize_products(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["product_id"] = _s(out["product_id"])
    out["category"] = _s(out["category"])
    out["unit_price"] = pd.to_numeric(out["unit_price"], errors="coerce")
    return out.drop_duplicates("product_id", keep="first").reset_index(drop=True)


def standardize_orders(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in ("order_id", "customer_id", "product_id"):
        out[c] = _s(out[c])
    out["quantity"] = pd.to_numeric(out["quantity"], errors="coerce")
    out["order_date"] = _s(out["order_date"])
    out["status"] = _s(out["status"]).str.lower()
    return out.drop_duplicates("order_id", keep="first").reset_index(drop=True)


def standardize_payments(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["payment_id"] = _s(out["payment_id"])
    out["order_id"] = _s(out["order_id"])
    out["amount"] = pd.to_numeric(out["amount"], errors="coerce")
    return out.drop_duplicates("payment_id", keep="first").reset_index(drop=True)


def standardize_inventory(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["product_id"] = _s(out["product_id"])
    out["stock_qty"] = pd.to_numeric(out["stock_qty"], errors="coerce")
    return out.drop_duplicates("product_id", keep="first").reset_index(drop=True)


def enrich_orders(orders: pd.DataFrame, products: pd.DataFrame) -> pd.DataFrame:
    """Add unit_price, order_total and order_month to validated orders."""
    out = orders.merge(products[["product_id", "unit_price"]], on="product_id", how="inner")
    out["quantity"] = out["quantity"].astype(int)
    out["order_total"] = out["quantity"] * out["unit_price"]
    out["order_month"] = out["order_date"].astype(str).str[:7]
    return out


def ntile_labels(n: int, buckets: int = 3) -> np.ndarray:
    """SQL NTILE assignment (1..buckets); earlier buckets get the extra rows."""
    base, extra = divmod(n, buckets)
    sizes = [base + (1 if i < extra else 0) for i in range(buckets)]
    return np.repeat(np.arange(1, buckets + 1), sizes)
