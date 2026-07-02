#!/usr/bin/env python3
"""Merge TPC-C/TPC-H result CSV files into week-2 performance datasets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"
DATASET = OUT_DIR / "param_perf_dataset.csv"
SUMMARY = OUT_DIR / "param_perf_summary.csv"


def load_results() -> pd.DataFrame:
    frames = []
    for path in sorted(OUT_DIR.glob("tpcc_result_*.csv")):
        frames.append(pd.read_csv(path, dtype=str))
    for path in sorted(OUT_DIR.glob("tpch_result_*.csv")):
        frames.append(pd.read_csv(path, dtype=str))
    if not frames:
        return pd.DataFrame(
            columns=[
                "experiment_id",
                "workload_type",
                "param_name",
                "test_value",
                "qps",
                "avg_latency_ms",
                "p95_latency_ms",
                "p99_latency_ms",
                "error_count",
                "query_id",
                "elapsed_ms",
                "status",
                "note",
            ]
        )
    return pd.concat(frames, ignore_index=True, sort=False)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_results()
    for col in ["qps", "avg_latency_ms", "p95_latency_ms", "p99_latency_ms", "error_count", "query_id", "elapsed_ms", "status", "note"]:
        if col not in df.columns:
            df[col] = pd.NA
    df.to_csv(DATASET, index=False)
    if df.empty:
        summary = pd.DataFrame(columns=["workload_type", "param_name", "status", "rows", "avg_qps", "avg_latency_ms", "avg_elapsed_ms"])
    else:
        for col in ["qps", "avg_latency_ms", "elapsed_ms"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        summary = (
            df.groupby(["workload_type", "param_name", "status"], dropna=False)
            .agg(rows=("experiment_id", "count"), avg_qps=("qps", "mean"), avg_latency_ms=("avg_latency_ms", "mean"), avg_elapsed_ms=("elapsed_ms", "mean"))
            .reset_index()
        )
    summary.to_csv(SUMMARY, index=False)
    print(f"Wrote {DATASET} and {SUMMARY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
