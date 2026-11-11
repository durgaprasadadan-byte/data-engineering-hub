from src.monitoring.run_registry import load_runs, summarize
from src.monitoring.tracker import run_tracked


def test_success_records_metrics(tmp_path):
    h = tmp_path / "h.jsonl"
    run, res = run_tracked("p", lambda: {"extracted": 10, "loaded": 8, "rejected": 2, "quality_score": 95.0,
                                         "validation_status": "passed"}, history_path=h)
    assert run.status == "success" and run.records_loaded == 8 and run.duration_seconds >= 0
    assert load_runs(h)[0].execution_id == run.execution_id


def test_retry_then_success(tmp_path):
    state = {"n": 0}
    def flaky():
        state["n"] += 1
        if state["n"] < 3:
            raise ValueError("boom")
        return {"loaded": 1}
    run, _ = run_tracked("p", flaky, max_retries=2, history_path=tmp_path / "h.jsonl")
    assert run.status == "success" and run.retries == 2 and run.error_message is None


def test_failure_is_recorded_not_hidden(tmp_path):
    h = tmp_path / "h.jsonl"
    run, res = run_tracked("p", lambda: (_ for _ in ()).throw(RuntimeError("down")), max_retries=1, history_path=h)
    assert run.status == "failed" and res is None and "down" in run.error_message and run.retries == 1
    assert summarize(load_runs(h))["failed"] == 1
