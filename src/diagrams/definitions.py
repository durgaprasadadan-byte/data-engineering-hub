"""Architecture definitions and generators.

Diagrams are generated from these definitions (no static images), so the
Mermaid, Graphviz DOT and the interactive component explanations always agree.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Stage:
    id: str
    label: str
    technology: str
    description: str


@dataclass(frozen=True)
class Architecture:
    key: str
    title: str
    summary: str
    stages: tuple[Stage, ...]  # linear flow, left to right


ETL = Architecture(
    key="etl", title="Traditional ETL",
    summary="Data is transformed and validated before it reaches the warehouse.",
    stages=(
        Stage("src", "Data Sources", "CSV, JSON, PostgreSQL, REST APIs", "Operational systems and files that hold the raw business data."),
        Stage("ext", "Extraction", "Python, Pandas", "Reads data from each source and records source name and record counts."),
        Stage("stg", "Staging", "Parquet / local files", "Temporary landing area so extraction is decoupled from transformation."),
        Stage("trf", "Transformation", "Pandas / PySpark", "Deduplicates, handles nulls, standardizes types and applies business rules."),
        Stage("val", "Validation", "Custom DQ framework", "Runs quality checks; failing records go to quarantine."),
        Stage("dwh", "Data Warehouse", "PostgreSQL / Parquet", "Stores validated, analytics-ready tables."),
        Stage("ana", "Analytics", "Streamlit, Plotly", "Dashboards and reports built on the warehouse."),
    ),
)

ELT = Architecture(
    key="elt", title="Modern ELT (Medallion)",
    summary="Raw data is loaded first and transformed in layers inside the platform.",
    stages=(
        Stage("src", "Data Sources", "CSV, JSON, APIs, databases", "Source systems feeding the platform."),
        Stage("ing", "Ingestion", "Python, PySpark", "Loads data as-is, adding ingestion metadata."),
        Stage("raw", "Raw Storage", "Local files / S3 / GCS", "Immutable copy of the source data."),
        Stage("brz", "Bronze", "Delta Lake", "Raw records in table form, schema-on-read, full history."),
        Stage("slv", "Silver", "Spark SQL, Delta Lake", "Cleaned, deduplicated, typed and validated tables."),
        Stage("gld", "Gold", "Spark SQL, Delta Lake", "Aggregated business tables (revenue, segments, KPIs)."),
        Stage("ana", "Analytics", "Streamlit, Plotly", "Dashboards reading Gold tables."),
    ),
)

LAKEHOUSE = Architecture(
    key="lakehouse", title="Lakehouse Architecture",
    summary="One platform combines data lake storage with warehouse-style reliability.",
    stages=(
        Stage("src", "Source Systems", "Databases, files, APIs", "Where data originates."),
        Stage("lake", "Data Lake", "Object storage (S3 / GCS / local)", "Low-cost storage for raw and curated files."),
        Stage("dl", "Delta Lake", "Delta Lake", "ACID transactions, schema enforcement and time travel over lake files."),
        Stage("dbx", "Databricks", "Databricks workspace", "Managed compute and notebooks (requires credentials; optional here)."),
        Stage("spk", "Spark Processing", "PySpark, Spark SQL", "Distributed transformations and aggregations."),
        Stage("ana", "Analytics", "BI, ML, Streamlit", "Reporting and machine-learning use cases."),
    ),
)

STREAMING = Architecture(
    key="streaming", title="Streaming Architecture",
    summary="Event streams are processed continuously. In this hub the stream is simulated unless a real Kafka source is configured.",
    stages=(
        Stage("src", "Data Sources", "Event producers", "Applications emitting events (simulated in this project)."),
        Stage("kfk", "Kafka", "Apache Kafka", "Durable event log decoupling producers and consumers."),
        Stage("sss", "Spark Structured Streaming", "PySpark", "Micro-batch processing with windows and checkpoints."),
        Stage("dl", "Delta Lake", "Delta Lake", "Transactional sink for streamed records."),
        Stage("mon", "Monitoring", "Streamlit, logs", "Throughput, lag and failure tracking."),
    ),
)

ARCHITECTURES: dict[str, Architecture] = {a.key: a for a in (ETL, ELT, LAKEHOUSE, STREAMING)}

_HIGHLIGHT = "#2563EB"


def to_mermaid(arch: Architecture, highlight: str | None = None) -> str:
    lines = ["flowchart LR"]
    for s in arch.stages:
        lines.append(f'  {s.id}["{s.label}<br/><i>{s.technology}</i>"]')
    for a, b in zip(arch.stages, arch.stages[1:]):
        lines.append(f"  {a.id} --> {b.id}")
    if highlight:
        lines.append(f"  style {highlight} fill:{_HIGHLIGHT},color:#fff,stroke:#1E3A8A")
    return "\n".join(lines) + "\n"


def to_dot(arch: Architecture, highlight: str | None = None) -> str:
    lines = [
        "digraph G {",
        "  rankdir=LR;",
        '  node [shape=box, style="rounded,filled", fillcolor="#F1F5F9", color="#64748B", fontname="Helvetica"];',
        '  edge [color="#475569"];',
    ]
    for s in arch.stages:
        label = f"{s.label}\\n({s.technology})".replace('"', "'")
        extra = f', fillcolor="{_HIGHLIGHT}", fontcolor="white"' if s.id == highlight else ""
        lines.append(f'  {s.id} [label="{label}"{extra}];')
    for a, b in zip(arch.stages, arch.stages[1:]):
        lines.append(f"  {a.id} -> {b.id};")
    lines.append("}")
    return "\n".join(lines) + "\n"
