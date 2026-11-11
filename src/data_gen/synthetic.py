"""Deterministic SYNTHETIC datasets with deliberately injected defects.

All data is fabricated. Healthcare data contains no names or real identifiers.
Set dirty=False for a defect-free version.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _dates(rng, start: str, days: int, n: int, fmt: str = "%Y-%m-%d") -> list[str]:
    base = pd.Timestamp(start)
    return list((base + pd.to_timedelta(rng.integers(0, days, n), unit="D")).strftime(fmt))


def make_ecommerce(seed: int = 42, n_customers: int = 300, n_products: int = 60,
                   n_orders: int = 1500, dirty: bool = True) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    customers = pd.DataFrame({
        "customer_id": [f"C{i:04d}" for i in range(1, n_customers + 1)],
        "name": [f"Customer {i}" for i in range(1, n_customers + 1)],
        "email": [f"customer{i}@example.com" for i in range(1, n_customers + 1)],
        "country": rng.choice(["USA", "UK", "Germany", "India", "Canada", "Australia"], n_customers),
        "signup_date": _dates(rng, "2023-01-01", 700, n_customers),
    })
    products = pd.DataFrame({
        "product_id": [f"P{i:03d}" for i in range(1, n_products + 1)],
        "product_name": [f"Product {i}" for i in range(1, n_products + 1)],
        "category": rng.choice(["Electronics", "Home", "Fashion", "Sports", "Books"], n_products),
        "unit_price": np.round(rng.uniform(5, 300, n_products), 2),
    })
    orders = pd.DataFrame({
        "order_id": [f"O{i:05d}" for i in range(1, n_orders + 1)],
        "customer_id": rng.choice(customers["customer_id"], n_orders),
        "product_id": rng.choice(products["product_id"], n_orders),
        "quantity": rng.integers(1, 6, n_orders),
        "order_date": _dates(rng, "2024-01-01", 730, n_orders),
        "status": rng.choice(["completed", "shipped", "cancelled", "pending"], n_orders, p=[.55, .2, .1, .15]),
    })
    price = orders["product_id"].map(products.set_index("product_id")["unit_price"])
    payments = pd.DataFrame({
        "payment_id": [f"PAY{i:05d}" for i in range(1, n_orders + 1)],
        "order_id": orders["order_id"],
        "amount": np.round(orders["quantity"] * price, 2),
        "method": rng.choice(["card", "paypal", "bank_transfer"], n_orders),
        "payment_date": orders["order_date"],
    })
    inventory = pd.DataFrame({
        "product_id": products["product_id"],
        "stock_qty": rng.integers(0, 500, n_products),
        "warehouse": rng.choice(["WH-East", "WH-West", "WH-Central"], n_products),
    })
    if dirty:
        customers.loc[5:12, "email"] = np.nan                      # missing values
        customers.loc[20:29, "country"] = customers.loc[20:29, "country"].str.lower().radd(" ")  # inconsistent format
        customers = pd.concat([customers, customers.iloc[:5]], ignore_index=True)  # duplicates
        products.loc[3, "unit_price"] = -5.0                         # invalid price
        orders.loc[100:103, "customer_id"] = "C9999"                 # orphan customers
        orders.loc[200:204, "quantity"] = 0                          # invalid quantity
        orders = pd.concat([orders, orders.iloc[300:306]], ignore_index=True)
        payments.loc[50:52, "amount"] = -10.0                        # invalid amounts
        inventory.loc[1:2, "stock_qty"] = -3                         # invalid stock
    return {"customers": customers, "products": products, "orders": orders,
            "payments": payments, "inventory": inventory}


def make_banking(seed: int = 7, n_customers: int = 200, n_accounts: int = 260,
                 n_txn: int = 6000, dirty: bool = True) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    customers = pd.DataFrame({
        "customer_id": [f"CU{i:04d}" for i in range(1, n_customers + 1)],
        "age": rng.integers(18, 85, n_customers),
        "country": rng.choice(["USA", "UK", "Germany", "India"], n_customers),
        "segment": rng.choice(["retail", "premium", "student"], n_customers, p=[.6, .15, .25]),
    })
    accounts = pd.DataFrame({
        "account_id": [f"AC{i:04d}" for i in range(1, n_accounts + 1)],
        "customer_id": rng.choice(customers["customer_id"], n_accounts),
        "account_type": rng.choice(["checking", "savings", "credit"], n_accounts),
        "open_date": _dates(rng, "2015-01-01", 3000, n_accounts),
    })
    ts = pd.Timestamp("2025-01-01") + pd.to_timedelta(np.sort(rng.integers(0, 180 * 86400, n_txn)), unit="s")
    amount = np.round(rng.lognormal(3.6, 1.0, n_txn), 2)
    hour = ts.hour.to_numpy()
    foreign = rng.random(n_txn) < 0.08
    channel = rng.choice(["online", "pos", "atm"], n_txn, p=[.45, .45, .10])
    p = (0.01 + 0.25 * (amount > np.quantile(amount, 0.95)) + 0.15 * (hour < 6)
         + 0.20 * foreign + 0.05 * (channel == "online"))
    tx = pd.DataFrame({
        "transaction_id": [f"T{i:06d}" for i in range(1, n_txn + 1)],
        "account_id": rng.choice(accounts["account_id"], n_txn),
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "amount": amount,
        "merchant_category": rng.choice(["grocery", "travel", "electronics", "dining", "utilities"], n_txn),
        "channel": channel,
        "is_foreign": foreign.astype(int),
        "is_fraud": (rng.random(n_txn) < np.clip(p, 0, 0.9)).astype(int),
    })
    if dirty:
        tx.loc[100:109, "amount"] = [-50, 0, -1, 0, -9, -3, 0, -2, -7, -8]
        tx.loc[200:207, "amount"] = np.nan
        tx.loc[300:305, "timestamp"] = "not-a-date"
        tx.loc[400:406, "account_id"] = "AC9999"
        tx.loc[500:504, "is_fraud"] = 2
        tx = pd.concat([tx, tx.iloc[600:615]], ignore_index=True)
    return {"customers": customers, "accounts": accounts, "transactions": tx}


def make_healthcare(seed: int = 11, n_patients: int = 400, n_providers: int = 40,
                    n_claims: int = 2500, dirty: bool = True) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    patients = pd.DataFrame({
        "patient_id": [f"PT{i:04d}" for i in range(1, n_patients + 1)],
        "age_group": rng.choice(["0-17", "18-34", "35-49", "50-64", "65+"], n_patients),
        "gender": rng.choice(["F", "M", "U"], n_patients, p=[.49, .49, .02]),
        "state": rng.choice(["CA", "NY", "TX", "FL", "WA"], n_patients),
    })
    providers = pd.DataFrame({
        "provider_id": [f"PR{i:03d}" for i in range(1, n_providers + 1)],
        "specialty": rng.choice(["Cardiology", "Orthopedics", "Primary Care", "Oncology", "Neurology"], n_providers),
        "state": rng.choice(["CA", "NY", "TX", "FL", "WA"], n_providers),
        "hospital": rng.choice(["General", "St. Mary", "Riverside", "Lakeview"], n_providers),
    })
    service = pd.Timestamp("2024-01-01") + pd.to_timedelta(rng.integers(0, 600, n_claims), unit="D")
    submitted = service + pd.to_timedelta(rng.integers(1, 10, n_claims), unit="D")
    processed = submitted + pd.to_timedelta(rng.integers(1, 45, n_claims), unit="D")
    status = rng.choice(["paid", "denied", "pending"], n_claims, p=[.75, .15, .10])
    claims = pd.DataFrame({
        "claim_id": [f"CL{i:06d}" for i in range(1, n_claims + 1)],
        "patient_id": rng.choice(patients["patient_id"], n_claims),
        "provider_id": rng.choice(providers["provider_id"], n_claims),
        "diagnosis_code": rng.choice(["I10", "E11.9", "M54.5", "J45.909", "C50.9", "G43.909"], n_claims),
        "service_date": service.strftime("%Y-%m-%d"),
        "submitted_date": submitted.strftime("%Y-%m-%d"),
        "processed_date": np.where(status == "pending", None, processed.strftime("%Y-%m-%d")),
        "claim_amount": np.round(np.clip(rng.lognormal(6.0, 0.8, n_claims), 20, 50000), 2),
        "status": status,
    })
    visits = pd.DataFrame({
        "visit_id": [f"V{i:06d}" for i in range(1, 1201)],
        "patient_id": rng.choice(patients["patient_id"], 1200),
        "provider_id": rng.choice(providers["provider_id"], 1200),
        "visit_date": _dates(rng, "2024-01-01", 600, 1200),
        "hospital": rng.choice(["General", "St. Mary", "Riverside", "Lakeview"], 1200),
    })
    rx = pd.DataFrame({
        "rx_id": [f"RX{i:06d}" for i in range(1, 1501)],
        "patient_id": rng.choice(patients["patient_id"], 1500),
        "provider_id": rng.choice(providers["provider_id"], 1500),
        "drug_code": rng.choice(["D100", "D200", "D300", "D400"], 1500),
        "fill_date": _dates(rng, "2024-01-01", 600, 1500),
        "cost": np.round(rng.uniform(5, 400, 1500), 2),
    })
    if dirty:
        claims.loc[10:15, "patient_id"] = claims.loc[10:15, "patient_id"].str.lower() + " "  # id formatting
        claims.loc[30:41, "diagnosis_code"] = None
        pend = claims["status"] != "pending"
        claims.loc[claims.index[50:55].intersection(claims.index[pend]), "processed_date"] = "2023-01-01"
        claims.loc[60:63, "claim_amount"] = -100.0
        claims.loc[70:74, "patient_id"] = "PT9999"
        claims.loc[80:82, "provider_id"] = "PR999"
        claims.loc[90:92, "service_date"] = "2025-13-45"
        logical = claims.iloc[120:128].copy()
        logical["claim_id"] = [f"CL9{i:05d}" for i in range(len(logical))]   # same content, new id
        claims = pd.concat([claims, claims.iloc[130:140], logical], ignore_index=True)  # id + logical dups
    return {"patients": patients, "providers": providers, "claims": claims,
            "visits": visits, "prescriptions": rx}


GENERATORS = {"ecommerce": make_ecommerce, "banking": make_banking, "healthcare": make_healthcare}
