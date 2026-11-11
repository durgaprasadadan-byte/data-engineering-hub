"""Reusable data quality framework.

Dimensions: completeness, uniqueness, validity, consistency, accuracy,
timeliness, referential integrity, schema. Row-level checks record which rows
failed so they can be displayed and quarantined. A check with blocking=False is
reported but does not cause rows to be quarantined.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd

DIMENSIONS = ["completeness", "uniqueness", "validity", "consistency", "accuracy",
              "timeliness", "referential_integrity", "schema"]


@dataclass
class CheckResult:
    dataset: str
    dimension: str
    check: str
    passed: bool
    total: int
    failed: int
    pass_rate: float  # 0-1
    threshold: float
    blocking: bool = True
    detail: str = ""


class DataQualityValidator:
    def __init__(self, df: pd.DataFrame, dataset: str):
        self.df = df.reset_index(drop=True)
        self.dataset = dataset
        self.results: list[CheckResult] = []
        self._masks: dict[str, pd.Series] = {}
        self._blocking: dict[str, bool] = {}

    # -- core ---------------------------------------------------------------
    def check_mask(self, dimension: str, name: str, bad: pd.Series, *, threshold: float = 1.0,
                   blocking: bool = True, detail: str = "") -> "DataQualityValidator":
        """Register a row-level check from a boolean 'bad row' mask."""
        bad = pd.Series(bad, index=self.df.index).fillna(False).astype(bool)
        total, failed = len(self.df), int(bad.sum())
        rate = 1.0 if total == 0 else 1 - failed / total
        key = f"{dimension}:{name}"
        self.results.append(CheckResult(self.dataset, dimension, name, rate >= threshold, total,
                                        failed, round(rate, 6), threshold, blocking, detail))
        if failed:
            self._masks[key] = bad
            self._blocking[key] = blocking
        return self

    # -- dimensions -----------------------------------------------------------
    def completeness(self, columns: Iterable[str], threshold: float = 1.0, blocking: bool = True):
        for c in columns:
            if c not in self.df:
                self._missing_col("completeness", c)
                continue
            s = self.df[c]
            bad = s.isna() | s.astype(str).str.strip().eq("")
            self.check_mask("completeness", f"{c} not null", bad, threshold=threshold, blocking=blocking)
        return self

    def uniqueness(self, columns: list[str], blocking: bool = True):
        if any(c not in self.df for c in columns):
            return self._missing_col("uniqueness", ",".join(columns))
        bad = self.df.duplicated(subset=columns, keep="first")
        return self.check_mask("uniqueness", f"{'+'.join(columns)} unique", bad, blocking=blocking,
                               detail="first occurrence kept; later duplicates fail")

    def validity(self, name: str, valid_rule: Callable[[pd.DataFrame], pd.Series], blocking: bool = True,
                 dimension: str = "validity", threshold: float = 1.0):
        try:
            valid = valid_rule(self.df).fillna(False).astype(bool)
        except Exception as exc:  # noqa: BLE001
            return self._error(dimension, name, exc)
        return self.check_mask(dimension, name, ~valid, blocking=blocking, threshold=threshold)

    def consistency(self, name: str, valid_rule: Callable[[pd.DataFrame], pd.Series], blocking: bool = True):
        return self.validity(name, valid_rule, blocking, dimension="consistency")

    def allowed_values(self, column: str, allowed: Iterable, blocking: bool = True):
        if column not in self.df:
            return self._missing_col("validity", column)
        bad = self.df[column].notna() & ~self.df[column].isin(list(allowed))
        return self.check_mask("validity", f"{column} in allowed set", bad, blocking=blocking)

    def accuracy(self, column: str, min_value: float | None = None, max_value: float | None = None,
                 blocking: bool = True):
        """Numeric range check. Non-numeric/missing values are left to completeness/schema."""
        if column not in self.df:
            return self._missing_col("accuracy", column)
        n = pd.to_numeric(self.df[column], errors="coerce")
        bad = pd.Series(False, index=n.index)
        if min_value is not None:
            bad |= n < min_value
        if max_value is not None:
            bad |= n > max_value
        return self.check_mask("accuracy", f"{column} in [{min_value}, {max_value}]", bad.fillna(False),
                               blocking=blocking)

    def timeliness(self, column: str, *, max_date: str | pd.Timestamp | None = None,
                   min_date: str | pd.Timestamp | None = None, blocking: bool = True):
        """Dates must parse and lie within [min_date, max_date] (max defaults to now)."""
        if column not in self.df:
            return self._missing_col("timeliness", column)
        d = pd.to_datetime(self.df[column], errors="coerce", utc=True)
        hi = pd.Timestamp(max_date or datetime.now(timezone.utc))
        hi = hi.tz_localize("UTC") if hi.tzinfo is None else hi
        bad = d.isna() & self.df[column].notna()
        bad |= d > hi
        if min_date is not None:
            lo = pd.Timestamp(min_date)
            bad |= d < (lo.tz_localize("UTC") if lo.tzinfo is None else lo)
        return self.check_mask("timeliness", f"{column} valid and not in future", bad, blocking=blocking)

    def referential_integrity(self, column: str, reference: Iterable, ref_name: str, blocking: bool = True):
        if column not in self.df:
            return self._missing_col("referential_integrity", column)
        bad = self.df[column].notna() & ~self.df[column].isin(set(reference))
        return self.check_mask("referential_integrity", f"{column} exists in {ref_name}", bad, blocking=blocking)

    def schema(self, expected: dict[str, str]):
        """expected maps column -> 'str' | 'numeric' | 'datetime'. Dataset-level check."""
        problems: list[str] = []
        for col, kind in expected.items():
            if col not in self.df:
                problems.append(f"{col}: missing")
                continue
            s = self.df[col].dropna()
            if kind == "numeric" and pd.to_numeric(s, errors="coerce").isna().any():
                problems.append(f"{col}: non-numeric values")
            elif kind == "datetime" and pd.to_datetime(s, errors="coerce").isna().any():
                problems.append(f"{col}: unparseable dates")
        total = len(expected)
        self.results.append(CheckResult(self.dataset, "schema", "expected columns/types", not problems, total,
                                        len(problems), round(1 - len(problems) / total, 6) if total else 1.0,
                                        1.0, False, "; ".join(problems)))
        return self

    # -- helpers ----------------------------------------------------------------
    def _missing_col(self, dimension: str, col: str):
        self.results.append(CheckResult(self.dataset, dimension, f"{col} (column missing)", False,
                                        len(self.df), len(self.df), 0.0, 1.0, False, "column not found"))
        return self

    def _error(self, dimension: str, name: str, exc: Exception):
        self.results.append(CheckResult(self.dataset, dimension, name, False, len(self.df), len(self.df),
                                        0.0, 1.0, False, f"rule error: {exc}"))
        return self

    # -- outputs ----------------------------------------------------------------
    def score(self) -> float:
        """Mean pass rate over all checks, as a percentage (100 when no checks)."""
        if not self.results:
            return 100.0
        return round(100 * sum(r.pass_rate for r in self.results) / len(self.results), 2)

    def results_frame(self) -> pd.DataFrame:
        return pd.DataFrame([asdict(r) for r in self.results])

    def failed_records(self, blocking_only: bool = False) -> pd.DataFrame:
        """All rows failing at least one row-level check, with a `failed_checks` column."""
        reasons = pd.Series([[] for _ in range(len(self.df))], index=self.df.index, dtype=object)
        for key, mask in self._masks.items():
            if blocking_only and not self._blocking[key]:
                continue
            for i in mask[mask].index:
                reasons[i] = reasons[i] + [key]
        bad = reasons.map(len) > 0
        out = self.df[bad].copy()
        out["failed_checks"] = reasons[bad].map("; ".join)
        return out

    def split(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """(clean rows, quarantined rows) using blocking checks only."""
        q = self.failed_records(blocking_only=True)
        clean = self.df.drop(index=q.index)
        return clean.reset_index(drop=True), q.reset_index(drop=True)


# -- reports, quarantine, history ---------------------------------------------------
def build_report(validators: list[DataQualityValidator]) -> dict:
    frames = [v.results_frame() for v in validators]
    checks = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    scores = {v.dataset: v.score() for v in validators}
    return {
        "report_id": uuid.uuid4().hex[:12],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_score": round(sum(scores.values()) / len(scores), 2) if scores else 100.0,
        "dataset_scores": scores,
        "checks_passed": int(checks["passed"].sum()) if len(checks) else 0,
        "checks_failed": int((~checks["passed"]).sum()) if len(checks) else 0,
        "checks": checks.to_dict("records") if len(checks) else [],
    }


def report_to_json(report: dict) -> str:
    return json.dumps(report, indent=2, default=str)


def report_to_csv(report: dict) -> str:
    return pd.DataFrame(report["checks"]).to_csv(index=False)


def report_to_markdown(report: dict) -> str:
    lines = [f"# Data Quality Report `{report['report_id']}`", f"Generated: {report['generated_at']}",
             f"Overall score: **{report['overall_score']}%** "
             f"({report['checks_passed']} passed, {report['checks_failed']} failed)", "",
             "| Dataset | Dimension | Check | Result | Failed/Total | Detail |", "|---|---|---|---|---|---|"]
    for c in report["checks"]:
        lines.append(f"| {c['dataset']} | {c['dimension']} | {c['check']} | "
                     f"{'PASS' if c['passed'] else 'FAIL'} | {c['failed']}/{c['total']} | {c['detail']} |")
    return "\n".join(lines) + "\n"


def write_quarantine(df: pd.DataFrame, dataset: str, run_id: str, directory: Path) -> Path | None:
    """Persist quarantined rows as CSV; returns the path (None if nothing to store)."""
    if df.empty:
        return None
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{dataset}_{run_id}.csv"
    df.to_csv(path, index=False)
    return path


def append_history(report: dict, path: Path, project: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {k: report[k] for k in ("report_id", "generated_at", "overall_score", "dataset_scores",
                                    "checks_passed", "checks_failed")}
    entry["project"] = project
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def load_history(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return pd.DataFrame(rows)
