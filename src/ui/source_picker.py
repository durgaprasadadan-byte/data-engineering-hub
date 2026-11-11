"""Data source selection: bundled synthetic sample, uploaded CSV/JSON, or REST API."""
from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from src.config.settings import SETTINGS
from src.data_gen.synthetic import GENERATORS
from src.ingestion.loaders import SourceInfo, fetch_api, load_sample_dir, read_csv, read_json
from src.ui.components import df_view

SAMPLE, UPLOAD, API = "Bundled synthetic sample", "Upload CSV / JSON", "REST API (JSON)"


def _sample(project: str, names: list[str]):
    try:
        return load_sample_dir(SETTINGS.sample_dir / project, names)
    except FileNotFoundError:
        gen = GENERATORS[project]()
        infos = [SourceInfo(n, "sample (generated in memory)", "synthetic generator", len(gen[n]), gen[n].shape[1], "") for n in names]
        return {n: gen[n] for n in names}, infos


def pick_sources(project: str, names: list[str], key: str) -> dict[str, pd.DataFrame] | None:
    mode = st.radio("Data source", [SAMPLE, UPLOAD, API], horizontal=True, key=f"{key}_mode")
    raw: dict[str, pd.DataFrame] | None = None
    infos: list[SourceInfo] = []
    if mode == SAMPLE:
        st.caption("Synthetic data with deliberately injected defects (duplicates, nulls, invalid values).")
        raw, infos = _sample(project, names)
    elif mode == UPLOAD:
        st.caption(f"Expected datasets: {', '.join(names)}. Upload synthetic or de-identified data only.")
        got: dict[str, pd.DataFrame] = {}
        for n in names:
            f = st.file_uploader(f"{n} (.csv or .json)", type=["csv", "json"], key=f"{key}_up_{n}")
            if f is None:
                continue
            try:
                df, info = (read_csv(f, n) if f.name.lower().endswith(".csv") else read_json(f, n))
                got[n] = df
                infos.append(info)
            except Exception as exc:  # noqa: BLE001
                st.error(f"Could not read {f.name}: {exc}")
        if len(got) == len(names):
            raw = got
        else:
            st.info(f"Waiting for: {', '.join(n for n in names if n not in got)}")
    else:
        st.caption("Provide a JSON endpoint per dataset. For authenticated APIs enter the NAME of an environment "
                   "variable holding a bearer token; the token itself is never typed or stored here.")
        env_name = st.text_input("Token environment variable (optional)", key=f"{key}_tokenenv")
        urls = {n: st.text_input(f"{n} URL", key=f"{key}_url_{n}") for n in names}
        if st.button("Fetch from API", key=f"{key}_fetch"):
            headers = {"Authorization": f"Bearer {os.getenv(env_name)}"} if env_name and os.getenv(env_name) else None
            got, got_infos = {}, []
            try:
                for n, u in urls.items():
                    if not u:
                        raise ValueError(f"URL missing for {n}")
                    df, info = fetch_api(u, n, headers=headers)
                    got[n] = df
                    got_infos.append(info)
                st.session_state[f"{key}_api"] = (got, got_infos)
            except Exception as exc:  # noqa: BLE001
                st.error(f"API ingestion failed: {exc}")
        if f"{key}_api" in st.session_state:
            raw, infos = st.session_state[f"{key}_api"]
    if infos:
        df_view(pd.DataFrame([i.as_dict() for i in infos])[["name", "kind", "location", "records", "columns"]])
    return raw
