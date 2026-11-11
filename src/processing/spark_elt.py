"""Run the layered SQL on Spark (Spark SQL), optionally writing Delta tables."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.processing.spark_session import get_spark


def run_layers_spark(bronze: dict[str, pd.DataFrame], layers: list[tuple[str, str]],
                     delta_dir: Path | None = None) -> tuple[dict[str, pd.DataFrame], str]:
    """Register bronze frames as views, execute each (name, sql) in order, return pandas results.
    If Delta is available and delta_dir is given, each layer table is also written as Delta.
    Returns (tables, storage_format)."""
    from pyspark.sql.types import StringType, StructField, StructType
    spark, delta_ok = get_spark("ecommerce-elt")
    for name, pdf in bronze.items():
        schema = StructType([StructField(c, StringType(), True) for c in pdf.columns])
        rows = pdf.astype(object).where(pdf.notna(), None).values.tolist()
        spark.createDataFrame(rows, schema).createOrReplaceTempView(f"bronze_{name}")
    out: dict[str, pd.DataFrame] = {}
    for name, sql in layers:
        sdf = spark.sql(sql)
        sdf.createOrReplaceTempView(name)
        out[name] = sdf.toPandas()
        if delta_ok and delta_dir is not None:
            sdf.write.format("delta").mode("overwrite").save(str(delta_dir / name))
    return out, ("delta" if delta_ok else "parquet/csv")
