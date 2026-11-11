"""Runs only where pyspark and Java are installed; skipped otherwise."""
import pytest

pytest.importorskip("pyspark")
from pipelines.ecommerce_elt import run_elt  # noqa: E402
from src.data_gen.synthetic import make_ecommerce  # noqa: E402
from src.processing.spark_session import spark_available  # noqa: E402


def test_spark_elt_matches_sqlite(tmp_path):
    if not spark_available()[0]:
        return
    raw = make_ecommerce()
    a = run_elt(raw, out_dir=tmp_path / "a", engine="spark", dq_history_path=tmp_path / "h")
    b = run_elt(raw, out_dir=tmp_path / "b", engine="sqlite", dq_history_path=tmp_path / "h")
    assert a["engine"] == "spark-sql"
    assert abs(a["gold"]["gold_summary"].iloc[0]["total_revenue"] - b["gold"]["gold_summary"].iloc[0]["total_revenue"]) < 0.05
