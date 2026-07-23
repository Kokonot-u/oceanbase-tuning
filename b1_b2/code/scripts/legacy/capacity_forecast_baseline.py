#!/usr/bin/env python3
"""Capacity forecast baseline using docker metrics snapshots."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "outputs" / "metrics_log.csv"
OUT = ROOT / "outputs" / "capacity_forecast_baseline.csv"


def mape(y_true: pd.Series, y_pred: pd.Series) -> float:
    denom = y_true.replace(0, np.nan).abs()
    return float(((y_true - y_pred).abs() / denom).mean() * 100)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if not METRICS.exists():
        pd.DataFrame(columns=["timestamp", "metric", "actual", "prediction", "mae", "rmse", "mape", "note"]).to_csv(OUT, index=False)
        print("metrics_log.csv missing. Wrote empty forecast template.")
        return 0
    df = pd.read_csv(METRICS)
    numeric_cols = [col for col in ["cpu_percent", "memory_percent"] if col in df.columns]
    if len(df) < 6 or not numeric_cols:
        pd.DataFrame(
            [{"timestamp": "", "metric": col or "cpu_percent", "actual": "", "prediction": "", "mae": "", "rmse": "", "mape": "", "note": "需要至少 6 个时间点做 moving average 基线"} for col in (numeric_cols or ["cpu_percent"])]
        ).to_csv(OUT, index=False)
        print("Not enough metrics. Wrote baseline template.")
        return 0
    rows = []
    for col in numeric_cols:
        series = pd.to_numeric(df[col], errors="coerce")
        pred = series.rolling(window=3).mean().shift(1)
        valid = pd.DataFrame({"actual": series, "prediction": pred}).dropna()
        mae = float((valid["actual"] - valid["prediction"]).abs().mean())
        rmse = float(np.sqrt(((valid["actual"] - valid["prediction"]) ** 2).mean()))
        metric_mape = mape(valid["actual"], valid["prediction"])
        for idx, rec in valid.iterrows():
            rows.append(
                {
                    "timestamp": df.loc[idx, "timestamp"] if "timestamp" in df.columns else idx,
                    "metric": col,
                    "actual": rec["actual"],
                    "prediction": rec["prediction"],
                    "mae": mae,
                    "rmse": rmse,
                    "mape": metric_mape,
                    "note": "moving average window=3",
                }
            )
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
