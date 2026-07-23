#!/usr/bin/env python3
"""Generate real week-2 TPC-C/TPC-H baseline summary table and latency chart."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
DATASET = ROOT / "results" / "week2" / "param_perf_dataset_real.csv"
FIG_DIR = ROOT / "results" / "week2" / "figures"
CACHE_DIR = ROOT / "results" / "week2" / ".mpl_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(CACHE_DIR))
os.environ.setdefault("XDG_CACHE_HOME", str(CACHE_DIR))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

WORKLOAD_LABELS = {
    "BenchmarkSQL_TPC-C": "TPC-C / BenchmarkSQL",
    "TPC-H-22-lightweight-real": "TPC-H / 22 queries",
}


def markdown_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["--"] * len(cols)) + " |"]
    for _, row in df.iterrows():
        values = [str(row.get(col, "")).replace("|", "\\|") for col in cols]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def main() -> int:
    if not DATASET.exists():
        raise SystemExit(f"Missing dataset: {DATASET}")
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(DATASET)
    df = df[df["workload"].isin(WORKLOAD_LABELS)].copy()
    if df.empty:
        raise SystemExit("No TPC-C/TPC-H baseline rows found in param_perf_dataset_real.csv")

    numeric_cols = ["elapsed_ms", "qps_or_tps", "avg_latency_ms", "p95_latency_ms", "p99_latency_ms", "error_count"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    summary = pd.DataFrame(
        {
            "workload": df["workload"].map(WORKLOAD_LABELS),
            "run_id": df["run_id"],
            "throughput_ops_s": df["qps_or_tps"].round(4),
            "avg_latency_ms": df["avg_latency_ms"].round(3),
            "p95_latency_ms": df["p95_latency_ms"].round(3),
            "p99_latency_ms": df["p99_latency_ms"].round(3),
            "elapsed_ms": df["elapsed_ms"].round(3),
            "error_count": df["error_count"].fillna(0).astype(int),
            "notes": df["notes"],
        }
    )
    summary = summary.where(pd.notna(summary), "N/A")

    csv_path = FIG_DIR / "baseline_summary_table.csv"
    md_path = FIG_DIR / "baseline_summary_table.md"
    table_png = FIG_DIR / "baseline_summary_table.png"
    chart_png = FIG_DIR / "latency_comparison.png"

    summary.to_csv(csv_path, index=False)
    md_path.write_text(markdown_table(summary), encoding="utf-8")

    display = summary[
        [
            "workload",
            "throughput_ops_s",
            "avg_latency_ms",
            "p95_latency_ms",
            "p99_latency_ms",
            "elapsed_ms",
            "error_count",
        ]
    ].copy()
    display.columns = ["Workload", "Throughput\nops/s", "AVG\nms", "P95\nms", "P99\nms", "Elapsed\nms", "Errors"]

    fig_height = 1.2 + 0.5 * len(display)
    fig, ax = plt.subplots(figsize=(10.5, fig_height))
    ax.axis("off")
    table = ax.table(
        cellText=display.astype(str).values,
        colLabels=list(display.columns),
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.4)
    ax.set_title("Real Week-2 Baseline Summary", fontsize=13, pad=12)
    fig.tight_layout()
    fig.savefig(table_png, dpi=180)
    plt.close(fig)

    latency = summary[["workload", "avg_latency_ms", "p95_latency_ms", "p99_latency_ms"]].set_index("workload")
    ax = latency.plot(kind="bar", figsize=(9, 5), width=0.72)
    ax.set_title("TPC-C vs TPC-H Baseline Latency")
    ax.set_xlabel("Workload")
    ax.set_ylabel("Latency (ms)")
    ax.tick_params(axis="x", rotation=0)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.legend(["AVG", "P95", "P99"], title="Metric")
    for container in ax.containers:
        ax.bar_label(container, fmt="%.1f", fontsize=8, padding=2)
    plt.tight_layout()
    plt.savefig(chart_png, dpi=180)
    plt.close()

    print(f"Wrote {csv_path}")
    print(f"Wrote {md_path}")
    print(f"Wrote {table_png}")
    print(f"Wrote {chart_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
