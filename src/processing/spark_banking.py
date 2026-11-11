"""PySpark equivalents of the banking transformations and a Structured Streaming sketch.

NOT executed in the project's automated tests (requires pyspark, Java and, for Kafka, a broker).
Run `python -m scripts.spark_selftest` on a machine with Spark to verify the Spark path.
"""
from __future__ import annotations

from pathlib import Path


def build_features_spark(spark, tx_pdf):
    """Spark version of frequency and per-account statistics features. Returns a Spark DataFrame."""
    from pyspark.sql import Window, functions as F
    df = spark.createDataFrame(tx_pdf).withColumn("ts", F.to_timestamp("timestamp"))
    df = df.withColumn("amount", F.col("amount").cast("double")).withColumn("hour", F.hour("ts"))
    w_acct = Window.partitionBy("account_id")
    w_1h = Window.partitionBy("account_id").orderBy(F.col("ts").cast("long")).rangeBetween(-3600, 0)
    w_24h = Window.partitionBy("account_id").orderBy(F.col("ts").cast("long")).rangeBetween(-86400, 0)
    return (df.withColumn("txn_count_1h", F.count("*").over(w_1h))
              .withColumn("txn_count_24h", F.count("*").over(w_24h))
              .withColumn("acct_mean_amount", F.avg("amount").over(w_acct))
              .withColumn("acct_std_amount", F.coalesce(F.stddev("amount").over(w_acct), F.lit(0.0)))
              .withColumn("acct_txn_count", F.count("*").over(w_acct)))


def save_delta(sdf, path: Path) -> None:
    sdf.write.format("delta").mode("overwrite").save(str(path))


def start_file_stream(spark, input_dir: Path, checkpoint: Path, output: Path, schema):
    """Structured Streaming from a directory of CSV files into Delta (local, no Kafka needed)."""
    stream = spark.readStream.schema(schema).option("header", True).csv(str(input_dir))
    return (stream.writeStream.format("delta").option("checkpointLocation", str(checkpoint))
            .outputMode("append").start(str(output)))


def start_kafka_stream(spark, bootstrap_servers: str, topic: str, checkpoint: Path, output: Path):
    """Kafka -> Delta. Requires a reachable broker and the spark-sql-kafka package; bootstrap_servers
    must come from configuration, never be hardcoded."""
    raw = (spark.readStream.format("kafka").option("kafka.bootstrap.servers", bootstrap_servers)
           .option("subscribe", topic).load())
    parsed = raw.selectExpr("CAST(value AS STRING) AS json", "timestamp")
    return (parsed.writeStream.format("delta").option("checkpointLocation", str(checkpoint))
            .outputMode("append").start(str(output)))
