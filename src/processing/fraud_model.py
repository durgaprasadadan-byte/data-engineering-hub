"""Scikit-learn fraud classifier training/evaluation and simulated streaming replay."""
from __future__ import annotations

from typing import Iterator

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

from src.transformation.banking import FEATURES


def train_and_evaluate(feat: pd.DataFrame, seed: int = 42, threshold: float = 0.5):
    """Stratified 75/25 split. Returns (model, metrics dict, test frame with scores, importances)."""
    if feat["is_fraud"].nunique() < 2:
        raise ValueError("Need both fraud and non-fraud examples to train a classifier")
    train, test = train_test_split(feat, test_size=0.25, random_state=seed, stratify=feat["is_fraud"])
    model = RandomForestClassifier(n_estimators=150, max_depth=10, class_weight="balanced_subsample",
                                   random_state=seed, n_jobs=-1)
    model.fit(train[FEATURES], train["is_fraud"])
    proba = model.predict_proba(test[FEATURES])[:, 1]
    pred = (proba >= threshold).astype(int)
    y = test["is_fraud"]
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    metrics = {
        "precision": round(float(precision_score(y, pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y, pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y, pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y, proba)), 4),
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "train_rows": len(train), "test_rows": len(test), "threshold": threshold,
    }
    scored = test.assign(fraud_score=proba, predicted_fraud=pred).sort_values("timestamp").reset_index(drop=True)
    imp = pd.Series(model.feature_importances_, index=FEATURES).sort_values(ascending=False)
    return model, metrics, scored, imp


def simulate_stream(scored: pd.DataFrame, model, batch_size: int = 100, max_batches: int | None = None) -> Iterator[dict]:
    """SIMULATED streaming: replays held-out transactions in time order as micro-batches and scores them.
    There is no live source or Kafka connection; this demonstrates the processing pattern only."""
    for i, start in enumerate(range(0, len(scored), batch_size)):
        if max_batches is not None and i >= max_batches:
            return
        batch = scored.iloc[start:start + batch_size]
        proba = model.predict_proba(batch[FEATURES])[:, 1]
        flagged = int((proba >= 0.5).sum())
        yield {"batch": i + 1, "records": len(batch), "flagged": flagged,
               "actual_fraud": int(batch["is_fraud"].sum()), "window_start": str(batch["timestamp"].iloc[0]),
               "window_end": str(batch["timestamp"].iloc[-1]), "simulated": True}
