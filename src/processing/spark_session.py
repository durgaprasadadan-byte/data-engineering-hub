"""Spark/Delta session helpers. Requires `pip install pyspark delta-spark` and a Java 17+ runtime.
Delta jars are fetched by delta-spark on first use (needs internet once)."""
from __future__ import annotations

import shutil


def spark_available() -> tuple[bool, str]:
    try:
        import pyspark  # noqa: F401
    except ImportError:
        return False, "pyspark is not installed"
    if shutil.which("java") is None:
        return False, "Java runtime not found on PATH"
    return True, "pyspark and Java found"


def delta_available() -> bool:
    try:
        import delta  # noqa: F401
        return True
    except ImportError:
        return False


def get_spark(app_name: str = "data-engineering-hub"):
    """Return (SparkSession, delta_enabled)."""
    from pyspark.sql import SparkSession
    builder = (SparkSession.builder.appName(app_name).master("local[2]")
               .config("spark.sql.shuffle.partitions", "4").config("spark.ui.enabled", "false"))
    if delta_available():
        from delta import configure_spark_with_delta_pip
        builder = (builder.config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
                   .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog"))
        return configure_spark_with_delta_pip(builder).getOrCreate(), True
    return builder.getOrCreate(), False
