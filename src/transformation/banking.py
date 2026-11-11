"""Feature engineering for fraud detection (pandas)."""
from __future__ import annotations

import numpy as np
import pandas as pd

FEATURES = ["amount", "amount_log", "hour", "is_night", "dow", "is_foreign", "txn_count_1h", "txn_count_24h",
            "acct_mean_amount", "acct_std_amount", "acct_txn_count", "amount_zscore", "customer_age",
            "ch_online", "ch_pos", "ch_atm"]


def build_features(tx: pd.DataFrame, accounts: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    """Validated transactions -> model-ready frame sorted by time.

    Rolling counts are causal (past events only). Per-account statistics use the whole
    dataset, a simplification documented in the README (production would use point-in-time stats).
    """
    df = tx.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["amount"] = pd.to_numeric(df["amount"])
    df = df.sort_values(["account_id", "timestamp"]).reset_index(drop=True)
    df["amount_log"] = np.log1p(df["amount"])
    df["hour"] = df["timestamp"].dt.hour
    df["is_night"] = (df["hour"] < 6).astype(int)
    df["dow"] = df["timestamp"].dt.dayofweek
    indexed = df.set_index("timestamp")
    for label, window in (("txn_count_1h", "1h"), ("txn_count_24h", "24h")):
        df[label] = indexed.groupby("account_id")["amount"].rolling(window).count().to_numpy()
    g = df.groupby("account_id")["amount"]
    df["acct_mean_amount"] = g.transform("mean")
    df["acct_std_amount"] = g.transform("std").fillna(0.0)
    df["acct_txn_count"] = g.transform("count")
    df["amount_zscore"] = ((df["amount"] - df["acct_mean_amount"]) /
                           df["acct_std_amount"].replace(0, np.nan)).fillna(0.0)
    age = accounts.merge(customers[["customer_id", "age"]], on="customer_id", how="left").set_index("account_id")["age"]
    df["customer_age"] = df["account_id"].map(age).fillna(age.median())
    for ch in ("online", "pos", "atm"):
        df[f"ch_{ch}"] = (df["channel"] == ch).astype(int)
    df["is_fraud"] = df["is_fraud"].astype(int)
    return df.sort_values("timestamp").reset_index(drop=True)
