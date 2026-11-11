from pipelines.banking_pipeline import run_banking
from src.data_gen.synthetic import make_banking
from src.processing.fraud_model import simulate_stream


def _run(tmp_path, raw):
    return run_banking(raw, out_dir=tmp_path / "wh", quarantine_dir=tmp_path / "q", dq_history_path=tmp_path / "h.jsonl")


def test_validation_quarantines_defects(tmp_path):
    raw = make_banking()
    r = _run(tmp_path, raw)
    q = r["quarantined"]["transactions"]
    checks = " ".join(q["failed_checks"])
    for expected in ("transaction_id unique", "amount", "timestamp", "account_id", "is_fraud"):
        assert expected in checks
    assert r["features"]["transaction_id"].is_unique
    assert (r["features"]["amount"] > 0).all()
    assert set(r["features"]["is_fraud"].unique()) <= {0, 1}
    assert r["rejected"] == len(q) > 0


def test_model_metrics_reasonable_and_features_present(tmp_path):
    r = _run(tmp_path, make_banking())
    m = r["metrics"]
    assert 0 <= m["precision"] <= 1 and 0 <= m["recall"] <= 1 and 0 <= m["f1"] <= 1
    assert m["roc_auc"] > 0.6   # synthetic fraud is correlated with features
    for col in ("txn_count_1h", "acct_mean_amount", "amount_zscore"):
        assert col in r["features"].columns and r["features"][col].notna().all()
    assert (r["features"]["txn_count_1h"] >= 1).all()


def test_simulated_stream_is_labelled_and_ordered(tmp_path):
    r = _run(tmp_path, make_banking())
    batches = list(simulate_stream(r["scored"], r["model"], batch_size=50, max_batches=3))
    assert len(batches) == 3 and all(b["simulated"] for b in batches)
    assert batches[0]["window_start"] <= batches[1]["window_start"]
