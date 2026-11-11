from src.monitoring.run_registry import PipelineRun, append_run, load_runs, summarize


def test_missing_file_gives_empty(tmp_path):
    assert load_runs(tmp_path / "none.jsonl") == []


def test_roundtrip_and_summary_excludes_samples(tmp_path):
    f = tmp_path / "runs.jsonl"
    append_run(PipelineRun("a", "success", records_loaded=10, quality_score=90.0), f)
    append_run(PipelineRun("b", "failed", error_message="boom"), f)
    append_run(PipelineRun("demo", "success", source="sample", records_loaded=999), f)
    runs = load_runs(f)
    assert len(runs) == 3
    s = summarize(runs)
    assert (s["total"], s["success"], s["failed"], s["records_processed"]) == (2, 1, 1, 10)
    assert s["quality_score"] == 90.0
    assert summarize(runs, include_sample=True)["total"] == 3


def test_corrupt_line_skipped(tmp_path):
    f = tmp_path / "runs.jsonl"
    f.write_text("not json\n")
    assert load_runs(f) == []


def test_no_quality_score_is_none():
    assert summarize([PipelineRun("a", "success")])["quality_score"] is None
