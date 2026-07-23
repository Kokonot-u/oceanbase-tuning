#!/usr/bin/env python3
"""Plot simple parameter trend charts with matplotlib."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "outputs" / "param_perf_dataset.csv"
FIG_DIR = ROOT / "outputs" / "figures"
METRICS = ["qps", "avg_latency_ms", "p95_latency_ms", "p99_latency_ms"]


def main() -> int:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    readme = FIG_DIR / "README.md"
    if not DATASET.exists():
        readme.write_text("param_perf_dataset.csv 不存在，请先运行 summarize_results.py。\n", encoding="utf-8")
        print(f"Data missing. Wrote {readme}")
        return 0
    df = pd.read_csv(DATASET, dtype=str)
    if df.empty or "param_name" not in df.columns:
        readme.write_text("当前没有足够实验数据生成趋势图。\n", encoding="utf-8")
        print(f"Insufficient data. Wrote {readme}")
        return 0
    made = 0
    for metric in METRICS:
        if metric not in df.columns:
            continue
        metric_df = df[["param_name", "test_value", metric]].copy()
        metric_df[metric] = pd.to_numeric(metric_df[metric], errors="coerce")
        metric_df = metric_df.dropna(subset=[metric])
        if metric_df.empty:
            continue
        for param_name, part in metric_df.groupby("param_name"):
            plt.figure(figsize=(7, 4))
            plt.plot(part["test_value"].astype(str), part[metric], marker="o")
            plt.title(f"{param_name}: test_value vs {metric}")
            plt.xlabel("test_value")
            plt.ylabel(metric)
            plt.xticks(rotation=30, ha="right")
            plt.tight_layout()
            safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(param_name))
            plt.savefig(FIG_DIR / f"{safe}_{metric}.png", dpi=150)
            plt.close()
            made += 1
    if made == 0:
        readme.write_text("结果集中没有真实数值指标。dry-run 数据已保留，但不生成趋势图。\n", encoding="utf-8")
    print(f"Generated {made} figures in {FIG_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
