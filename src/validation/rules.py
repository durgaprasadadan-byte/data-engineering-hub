"""Rule sets per project/dataset built on DataQualityValidator.

`ctx` holds reference tables (already cleaned where relevant) for referential
integrity. If a reference table is absent, that check is skipped.
"""
from __future__ import annotations

from typing import Callable

import pandas as pd

from src.validation.dq import DataQualityValidator

Ctx = dict[str, pd.DataFrame]


def _ref(ctx: Ctx, table: str, col: str):
    return ctx[table][col].dropna() if table in ctx else None


def _ri(v: DataQualityValidator, col: str, ctx: Ctx, table: str, ref_col: str, blocking: bool = True):
    ref = _ref(ctx, table, ref_col)
    if ref is not None:
        v.referential_integrity(col, ref, table, blocking=blocking)


# ---- E-commerce ----
def ecom_customers(df, ctx):
    v = DataQualityValidator(df, "customers")
    v.schema({"customer_id": "str", "email": "str", "country": "str", "signup_date": "datetime"})
    v.completeness(["customer_id"]).uniqueness(["customer_id"])
    v.completeness(["email"], blocking=False)
    v.validity("email contains @", lambda d: d["email"].isna() | d["email"].astype(str).str.contains("@|unknown"), blocking=False)
    v.timeliness("signup_date", blocking=False)
    return v


def ecom_products(df, ctx):
    v = DataQualityValidator(df, "products")
    v.schema({"product_id": "str", "unit_price": "numeric"})
    v.completeness(["product_id"]).uniqueness(["product_id"]).accuracy("unit_price", min_value=0.01)
    v.completeness(["product_name"], blocking=False)
    return v


def ecom_orders(df, ctx):
    v = DataQualityValidator(df, "orders")
    v.schema({"order_id": "str", "quantity": "numeric", "order_date": "datetime"})
    v.completeness(["order_id", "customer_id", "product_id", "quantity"]).uniqueness(["order_id"])
    v.accuracy("quantity", min_value=1)
    _ri(v, "customer_id", ctx, "customers", "customer_id")
    _ri(v, "product_id", ctx, "products", "product_id")
    v.timeliness("order_date", blocking=False)
    return v


def ecom_payments(df, ctx):
    v = DataQualityValidator(df, "payments")
    v.schema({"payment_id": "str", "amount": "numeric"})
    v.completeness(["payment_id"]).uniqueness(["payment_id"]).accuracy("amount", min_value=0.01)
    _ri(v, "order_id", ctx, "orders", "order_id")
    return v


def ecom_inventory(df, ctx):
    v = DataQualityValidator(df, "inventory")
    v.schema({"product_id": "str", "stock_qty": "numeric"})
    v.completeness(["product_id"]).uniqueness(["product_id"]).accuracy("stock_qty", min_value=0)
    return v


# ---- Banking ----
def bank_customers(df, ctx):
    v = DataQualityValidator(df, "customers")
    v.completeness(["customer_id"]).uniqueness(["customer_id"]).accuracy("age", 18, 120)
    return v


def bank_accounts(df, ctx):
    v = DataQualityValidator(df, "accounts")
    v.completeness(["account_id"]).uniqueness(["account_id"])
    _ri(v, "customer_id", ctx, "customers", "customer_id")
    return v


def bank_transactions(df, ctx):
    v = DataQualityValidator(df, "transactions")
    v.schema({"transaction_id": "str", "amount": "numeric", "timestamp": "datetime"})
    v.completeness(["transaction_id", "account_id", "amount"]).uniqueness(["transaction_id"])   # missing values, ID uniqueness
    _ri(v, "account_id", ctx, "accounts", "account_id")                                        # account ID validation
    v.accuracy("amount", min_value=0.01, max_value=10_000_000)                                 # invalid amounts
    v.timeliness("timestamp")                                                                  # timestamp validation
    v.allowed_values("is_fraud", [0, 1])                                                       # fraud label validation
    return v


# ---- Healthcare ----
def hc_patients(df, ctx):
    v = DataQualityValidator(df, "patients")
    v.completeness(["patient_id"]).uniqueness(["patient_id"])
    return v


def hc_providers(df, ctx):
    v = DataQualityValidator(df, "providers")
    v.completeness(["provider_id"]).uniqueness(["provider_id"])
    return v


def hc_claims(df, ctx):
    v = DataQualityValidator(df, "claims")
    v.schema({"claim_id": "str", "claim_amount": "numeric", "service_date": "datetime"})
    v.completeness(["claim_id", "patient_id", "provider_id"]).uniqueness(["claim_id"])
    v.completeness(["diagnosis_code"])                                       # missing diagnosis codes
    v.accuracy("claim_amount", min_value=0.01)                               # amount validation
    v.timeliness("service_date")                                             # invalid claim dates
    v.consistency("processed_date >= submitted_date", lambda d: (
        d["processed_date"].isna()
        | (pd.to_datetime(d["processed_date"], errors="coerce") >= pd.to_datetime(d["submitted_date"], errors="coerce"))))
    key = ["patient_id", "provider_id", "service_date", "diagnosis_code", "claim_amount"]
    if all(c in df for c in key):
        v.check_mask("uniqueness", "no logical duplicate claims", df.duplicated(subset=key, keep="first"),
                     detail="same patient, provider, date, diagnosis and amount under a different claim_id")
    _ri(v, "patient_id", ctx, "patients", "patient_id")
    _ri(v, "provider_id", ctx, "providers", "provider_id")
    return v


def hc_visits(df, ctx):
    v = DataQualityValidator(df, "visits")
    v.completeness(["visit_id"]).uniqueness(["visit_id"])
    _ri(v, "patient_id", ctx, "patients", "patient_id")
    _ri(v, "provider_id", ctx, "providers", "provider_id")
    return v


def hc_prescriptions(df, ctx):
    v = DataQualityValidator(df, "prescriptions")
    v.completeness(["rx_id"]).uniqueness(["rx_id"]).accuracy("cost", min_value=0)
    _ri(v, "patient_id", ctx, "patients", "patient_id")
    _ri(v, "provider_id", ctx, "providers", "provider_id")
    return v


RULESETS: dict[str, dict[str, Callable[[pd.DataFrame, Ctx], DataQualityValidator]]] = {
    "ecommerce": {"customers": ecom_customers, "products": ecom_products, "orders": ecom_orders,
                  "payments": ecom_payments, "inventory": ecom_inventory},
    "banking": {"customers": bank_customers, "accounts": bank_accounts, "transactions": bank_transactions},
    "healthcare": {"patients": hc_patients, "providers": hc_providers, "claims": hc_claims,
                   "visits": hc_visits, "prescriptions": hc_prescriptions},
}


def validate(project: str, dataset: str, df: pd.DataFrame, ctx: Ctx | None = None) -> DataQualityValidator:
    return RULESETS[project][dataset](df, ctx or {})
