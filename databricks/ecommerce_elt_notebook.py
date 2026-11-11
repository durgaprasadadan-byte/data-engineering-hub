# Databricks notebook source
# MAGIC %md
# MAGIC # E-commerce ELT (Bronze -> Silver -> Gold) on Delta Lake
# MAGIC Import this file into Databricks (Workspace > Import) or run it from a Repo clone of this project.
# MAGIC Raw CSVs (customers, products, orders, payments, inventory) must exist in the volume path below.

# COMMAND ----------
dbutils.widgets.text("catalog", "main")
dbutils.widgets.text("schema", "data_engineering_hub")
dbutils.widgets.text("raw_path", "/Volumes/main/data_engineering_hub/raw/ecommerce")
catalog, schema, raw_path = (dbutils.widgets.get(k) for k in ("catalog", "schema", "raw_path"))
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
spark.sql(f"USE {catalog}.{schema}")

# COMMAND ----------
# Bronze: raw data as strings plus ingestion metadata
from pyspark.sql import functions as F
for name in ["customers", "products", "orders", "payments", "inventory"]:
    df = (spark.read.option("header", True).option("inferSchema", False).csv(f"{raw_path}/{name}.csv")
          .withColumn("_ingested_at", F.current_timestamp()).withColumn("_source", F.lit(f"{raw_path}/{name}.csv")))
    df.write.format("delta").mode("overwrite").saveAsTable(f"bronze_{name}")

# COMMAND ----------
# Silver and Gold: the SAME SQL used by the local project (src/processing/sql_layers.py).
# Option A (Repos): sys.path.append("/Workspace/Repos/<you>/data-engineering-hub"); from src.processing.sql_layers import SILVER_SQL, GOLD_SQL
# Option B: paste the SQL lists here.
import sys
sys.path.append("/Workspace/Repos/<your-user>/data-engineering-hub")   # edit this path
from src.processing.sql_layers import SILVER_SQL, GOLD_SQL

for table, sql in SILVER_SQL + GOLD_SQL:
    spark.sql(f"CREATE OR REPLACE TABLE {table} USING DELTA AS {sql}")
    print(table, spark.table(table).count())

# COMMAND ----------
display(spark.table("gold_summary"))
display(spark.table("gold_monthly_revenue"))
