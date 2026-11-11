import pytest  # noqa: F401  (stubbed in sandboxes without pytest)
from pipelines.ecommerce_elt import run_elt
from pipelines.ecommerce_etl import run_etl
from src.data_gen.synthetic import make_ecommerce


def _etl(tmp_path, raw):
    return run_etl(raw, out_dir=tmp_path / "wh", quarantine_dir=tmp_path / "q", dq_history_path=tmp_path / "h.jsonl")


def test_etl_cleans_and_quarantines(tmp_path):
    raw = make_ecommerce()
    r = _etl(tmp_path, raw)
    assert r["extracted"] == sum(len(v) for v in raw.values())
    assert r["rejected"] == r["extracted"] - r["loaded"] > 0
    assert r["tables"]["customers"]["customer_id"].is_unique
    assert (r["tables"]["orders"]["quantity"] >= 1).all()
    assert r["tables"]["orders"]["customer_id"].isin(r["tables"]["customers"]["customer_id"]).all()
    assert (r["tables"]["payments"]["amount"] > 0).all()
    assert (r["tables"]["customers"]["email"] != "").all() and r["tables"]["customers"]["email"].notna().all()
    assert len(r["quarantined"]["orders"]) > 0
    assert (tmp_path / "wh" / "ecommerce" / "metrics.json").exists()
    assert list((tmp_path / "q").glob("ecommerce_orders_*.csv"))


def test_clean_data_has_no_rejections(tmp_path):
    r = _etl(tmp_path, make_ecommerce(dirty=False))
    assert r["rejected"] == 0 and r["validation_status"] == "passed"


def test_elt_sqlite_matches_etl(tmp_path):
    raw = make_ecommerce()
    etl = _etl(tmp_path, raw)
    elt = run_elt(raw, out_dir=tmp_path / "wh2", engine="sqlite", dq_history_path=tmp_path / "h2.jsonl")
    a, b = etl["gold"]["gold_summary"].iloc[0], elt["gold"]["gold_summary"].iloc[0]
    assert a["total_orders"] == b["total_orders"]
    assert abs(a["total_revenue"] - b["total_revenue"]) < 0.05
    m1 = etl["gold"]["gold_monthly_revenue"].set_index("order_month")["revenue"]
    m2 = elt["gold"]["gold_monthly_revenue"].set_index("order_month")["revenue"]
    assert (m1 - m2).abs().max() < 0.05
    assert etl["gold"]["gold_customer_segments"]["segment"].value_counts().to_dict() == \
        elt["gold"]["gold_customer_segments"]["segment"].value_counts().to_dict()
    assert len(etl["tables"]["orders"]) == len(elt["silver"]["silver_orders"])
    assert elt["engine"] == "sqlite-sql"


def test_elt_layers_and_bronze_is_raw(tmp_path):
    raw = make_ecommerce()
    elt = run_elt(raw, out_dir=tmp_path, engine="sqlite", dq_history_path=tmp_path / "h.jsonl")
    assert len(elt["bronze"]["customers"]) == len(raw["customers"])     # bronze keeps duplicates
    assert "_ingested_at" in elt["bronze"]["orders"].columns
    assert elt["gold"]["gold_summary"].iloc[0]["total_revenue"] > 0


def test_elt_spark_unavailable_raises(tmp_path):
    from src.processing.spark_session import spark_available
    if spark_available()[0]:
        return
    try:
        run_elt(make_ecommerce(), out_dir=tmp_path, engine="spark", dq_history_path=tmp_path / "h.jsonl")
    except RuntimeError as e:
        assert "unavailable" in str(e)
    else:
        raise AssertionError("expected RuntimeError")
