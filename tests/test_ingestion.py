import io
import json

from src.ingestion.loaders import fetch_api, load_sample_dir, read_csv, read_json


class _Resp:
    def __init__(self, payload, fail=False):
        self.payload, self.fail = payload, fail
    def raise_for_status(self):
        if self.fail:
            raise RuntimeError("500")
    def json(self):
        return self.payload


class _Session:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), 0
    def get(self, url, **kw):
        self.calls += 1
        return self.responses.pop(0)


def test_csv_and_json_variants(tmp_path):
    df, info = read_csv(io.BytesIO(b"a,b\n1,2\n3,4\n"), "t")
    assert info.records == 2 and info.kind == "csv"
    assert read_json(io.BytesIO(b'[{"a":1},{"a":2}]'), "t")[1].records == 2
    assert read_json(io.BytesIO(b'{"data":[{"a":1}]}'), "t")[1].records == 1
    assert read_json(io.BytesIO(b'{"a":1}\n{"a":2}\n'), "t")[1].records == 2     # JSON Lines
    p = tmp_path / "x.json"; p.write_text(json.dumps([{"k": 1}]))
    assert read_json(p, "x")[0].shape == (1, 1)


def test_api_retries_then_succeeds_and_fails_cleanly():
    s = _Session([_Resp(None, fail=True), _Resp([{"a": 1}, {"a": 2}])])
    df, info = fetch_api("https://example.com/x", "x", session=s, retries=2, backoff=0)
    assert len(df) == 2 and s.calls == 2 and info.kind == "api"
    s2 = _Session([_Resp(None, fail=True)] * 3)
    try:
        fetch_api("https://example.com/x", "x", session=s2, retries=2, backoff=0)
    except RuntimeError as e:
        assert "failed" in str(e) and s2.calls == 3
    else:
        raise AssertionError


def test_api_rejects_non_http_scheme():
    try:
        fetch_api("file:///etc/passwd", "x")
    except ValueError:
        return
    raise AssertionError


def test_load_sample_dir_missing_message(tmp_path):
    try:
        load_sample_dir(tmp_path, ["nothing"])
    except FileNotFoundError as e:
        assert "generate_sample_data" in str(e)
    else:
        raise AssertionError
