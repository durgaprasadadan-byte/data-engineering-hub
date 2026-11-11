"""Verify the Spark path on a machine with pyspark + Java: python -m scripts.spark_selftest"""
import tempfile
from pathlib import Path

from pipelines.ecommerce_elt import run_elt
from src.data_gen.synthetic import make_ecommerce
from src.processing.spark_session import delta_available, spark_available

ok, why = spark_available()
print("spark:", ok, why, "| delta-spark installed:", delta_available())
if ok:
    tmp = Path(tempfile.mkdtemp())
    res = run_elt(make_ecommerce(), out_dir=tmp, engine="spark", dq_history_path=tmp / "h.jsonl")
    print("engine:", res["engine"], "| delta written:", res["delta"])
    print(res["gold"]["gold_summary"])
