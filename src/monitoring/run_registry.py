"""Pipeline run history stored as JSON Lines.

Each record has `source`: "actual" (produced by a real pipeline execution) or
"sample" (a labelled demonstration). Summaries count only "actual" runs by
default so the dashboard never presents demo data as real results.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from src.config.settings import SETTINGS


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PipelineRun:
    pipeline_name: str
    status: str  # "success" | "failed" | "running"
    source: str = "actual"  # "actual" | "sample"
    execution_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    start_time: str = field(default_factory=_now)
    end_time: Optional[str] = None
    records_extracted: int = 0
    records_transformed: int = 0
    records_loaded: int = 0
    records_rejected: int = 0
    validation_status: str = "not_run"  # "passed" | "failed" | "not_run"
    quality_score: Optional[float] = None  # 0-100
    error_message: Optional[str] = None
    retries: int = 0

    @property
    def duration_seconds(self) -> Optional[float]:
        if not self.end_time:
            return None
        start = datetime.fromisoformat(self.start_time)
        end = datetime.fromisoformat(self.end_time)
        return (end - start).total_seconds()


def append_run(run: PipelineRun, path: Path | None = None) -> None:
    path = path or SETTINGS.run_history_file
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(run)) + "\n")


def load_runs(path: Path | None = None) -> list[PipelineRun]:
    path = path or SETTINGS.run_history_file
    if not path.exists():
        return []
    runs: list[PipelineRun] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            runs.append(PipelineRun(**json.loads(line)))
        except (json.JSONDecodeError, TypeError):
            continue  # skip corrupt lines rather than failing the dashboard
    return runs


def summarize(runs: Iterable[PipelineRun], include_sample: bool = False) -> dict:
    """Aggregate metrics. Quality score is None when no run reported one."""
    selected = [r for r in runs if include_sample or r.source == "actual"]
    scores = [r.quality_score for r in selected if r.quality_score is not None]
    return {
        "total": len(selected),
        "success": sum(r.status == "success" for r in selected),
        "failed": sum(r.status == "failed" for r in selected),
        "records_processed": sum(r.records_loaded for r in selected),
        "quality_score": round(sum(scores) / len(scores), 1) if scores else None,
    }
