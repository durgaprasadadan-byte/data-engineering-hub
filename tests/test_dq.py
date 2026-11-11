import pandas as pd
from src.validation.dq import (DataQualityValidator, append_history, build_report, load_history, report_to_csv,
                               report_to_json, report_to_markdown, write_quarantine)


def _df():
    return pd.DataFrame({"id": ["a", "b", "b", "c", None], "amt": [1, -5, 3, "x", 10],
                         "d": ["2024-01-01", "2024-02-30", "2999-01-01", "2024-03-01", "2024-04-01"]})


def test_each_dimension_flags_expected_rows():
    v = DataQualityValidator(_df(), "t")
    v.completeness(["id"]).uniqueness(["id"]).accuracy("amt", min_value=0).timeliness("d")
    v.referential_integrity("id", ["a", "b"], "ref").allowed_values("id", ["a", "b"])
    v.validity("amt numeric", lambda d: pd.to_numeric(d["amt"], errors="coerce").notna())
    v.consistency("amt < 100", lambda d: pd.to_numeric(d["amt"], errors="coerce") < 100)
    v.schema({"id": "str", "amt": "numeric", "missing_col": "str"})
    r = {(x.dimension, x.check): x for x in v.results}
    assert r[("completeness", "id not null")].failed == 1
    assert r[("uniqueness", "id unique")].failed == 1
    assert r[("accuracy", "amt in [0, None]")].failed == 1
    assert r[("timeliness", "d valid and not in future")].failed == 2   # bad date + future
    assert r[("referential_integrity", "id exists in ref")].failed == 1  # 'c'
    assert r[("validity", "amt numeric")].failed == 1
    assert not r[("schema", "expected columns/types")].passed
    assert all(x.dimension in {"completeness", "uniqueness", "accuracy", "timeliness", "referential_integrity",
                               "validity", "consistency", "schema"} for x in v.results)


def test_split_respects_blocking_flag():
    v = DataQualityValidator(pd.DataFrame({"a": [1, 2, None, 4], "b": [None, 1, 1, 1]}), "t")
    v.completeness(["a"]).completeness(["b"], blocking=False)
    clean, q = v.split()
    assert len(q) == 1 and len(clean) == 3                       # only the blocking failure is quarantined
    assert len(v.failed_records()) == 2                         # but both are visible as failed
    assert 0 < v.score() < 100


def test_report_exports_and_history(tmp_path):
    v = DataQualityValidator(_df(), "t").completeness(["id"]).uniqueness(["id"])
    rep = build_report([v])
    assert rep["checks_failed"] == 2 and rep["checks_passed"] == 0
    assert '"overall_score"' in report_to_json(rep)
    assert "dataset,dimension,check" in report_to_csv(rep)
    assert "FAIL" in report_to_markdown(rep)
    append_history(rep, tmp_path / "h.jsonl", "demo"); append_history(rep, tmp_path / "h.jsonl", "demo")
    assert len(load_history(tmp_path / "h.jsonl")) == 2
    _, q = v.split()
    assert write_quarantine(q, "t", "r1", tmp_path).exists()
    assert write_quarantine(q.iloc[0:0], "t", "r2", tmp_path) is None


def test_empty_and_perfect_data():
    v = DataQualityValidator(pd.DataFrame({"a": [1, 2]}), "t").completeness(["a"]).uniqueness(["a"])
    assert v.score() == 100.0 and v.failed_records().empty
    assert DataQualityValidator(pd.DataFrame({"a": []}), "t").completeness(["a"]).score() == 100.0
