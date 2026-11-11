from pipelines.healthcare_pipeline import run_healthcare
from src.data_gen.synthetic import make_healthcare


def _run(tmp_path, raw):
    return run_healthcare(raw, out_dir=tmp_path / "wh", quarantine_dir=tmp_path / "q", dq_history_path=tmp_path / "h.jsonl")


def test_ids_standardized_and_defects_quarantined(tmp_path):
    r = _run(tmp_path, make_healthcare())
    claims = r["silver"]["claims"]
    assert claims["patient_id"].str.match(r"^PT\d{4}$").all()      # lower/whitespace variants fixed
    assert claims["claim_id"].is_unique
    assert claims["diagnosis_code"].notna().all()
    assert (claims["claim_amount"] > 0).all()
    assert claims["patient_id"].isin(r["silver"]["patients"]["patient_id"]).all()
    assert claims["provider_id"].isin(r["silver"]["providers"]["provider_id"]).all()
    reasons = " ".join(r["quarantined"]["claims"]["failed_checks"])
    for expected in ("diagnosis_code", "claim_amount", "service_date", "processed_date", "logical duplicate", "patient_id exists"):
        assert expected in reasons


def test_logical_duplicates_removed(tmp_path):
    r = _run(tmp_path, make_healthcare())
    key = ["patient_id", "provider_id", "service_date", "diagnosis_code", "claim_amount"]
    assert not r["silver"]["claims"].duplicated(subset=key).any()


def test_gold_reports(tmp_path):
    r = _run(tmp_path, make_healthcare())
    g = r["gold"]
    assert g["gold_summary"].iloc[0]["total_claims"] == len(r["silver"]["claims"])
    assert (r["silver"]["claims"]["processing_days"].dropna() >= 0).all()
    assert {"denial_rate", "avg_processing_days"} <= set(g["gold_provider_performance"].columns)
    assert not any(c in r["silver"]["patients"].columns for c in ("name", "ssn", "address"))   # no PHI columns
