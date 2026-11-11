"""Run a pipeline function with logging, retries and run-history recording."""
from __future__ import annotations

import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from src.monitoring.logging_config import get_logger
from src.monitoring.run_registry import PipelineRun, append_run

log = get_logger("tracker")


def run_tracked(pipeline_name: str, fn: Callable[[], dict], *, max_retries: int = 1,
                backoff: float = 0.0, source: str = "actual",
                history_path: Path | None = None) -> tuple[PipelineRun, Any]:
    """Execute fn(); return (run record, fn's result or None on failure).

    fn must return a dict that may include: extracted, transformed, loaded, rejected,
    quality_score, validation_status. Every attempt chain is recorded once.
    """
    run = PipelineRun(pipeline_name=pipeline_name, status="running", source=source)
    result: dict | None = None
    for attempt in range(max_retries + 1):
        run.retries = attempt
        try:
            log.info("%s start id=%s attempt=%d", pipeline_name, run.execution_id, attempt + 1)
            result = fn()
            run.status = "success"
            run.error_message = None
            break
        except Exception as exc:  # noqa: BLE001
            run.error_message = f"{type(exc).__name__}: {exc}"
            log.error("%s failed attempt %d: %s\n%s", pipeline_name, attempt + 1, exc, traceback.format_exc())
            run.status = "failed"
            if attempt < max_retries and backoff:
                time.sleep(backoff * (2 ** attempt))
    run.end_time = datetime.now(timezone.utc).isoformat()
    if result:
        run.records_extracted = int(result.get("extracted", 0))
        run.records_transformed = int(result.get("transformed", 0))
        run.records_loaded = int(result.get("loaded", 0))
        run.records_rejected = int(result.get("rejected", 0))
        run.validation_status = result.get("validation_status", "not_run")
        run.quality_score = result.get("quality_score")
    append_run(run, history_path)
    return run, result
