# -*- coding: utf-8 -*-
"""
B3 长短期资源容量预测 —— 主入口
================================
输入：A1(Wu) 预处理后的归一化时序数据 inputs/normal_features_tpcc_10w_sample.csv
输出（outputs/）：
  - capacity_forecast_{experiment_id}.csv   跨组接口标准格式（第一次联调测试计划 §7.2）
  - b3_backtest_metrics.csv                  各指标 RMSE / MAE 基线指标
  - b3_forecast_report.md                    基线预测效果报告
  - figures/b3_forecast_{metric}.png         预测曲线图（若有 matplotlib）

用法（在 b3_b4/ 目录下）：
  python -m b3_forecast.run_b3
  python -m b3_forecast.run_b3 --config config.json
"""

import os
import json
import argparse
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from b3_forecast.patchtst_lite import ChannelForecaster

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_series(cfg_b3):
    csv_path = os.path.join(ROOT, cfg_b3["input_csv"])
    df = pd.read_csv(csv_path)
    tcol = cfg_b3["time_col"]
    df[tcol] = pd.to_datetime(df[tcol])
    df = df.sort_values(tcol).reset_index(drop=True)
    metrics = [m for m in cfg_b3["target_metrics"] if m in df.columns]
    return df, tcol, metrics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(ROOT, "config.json"))
    args = ap.parse_args()

    cfg = load_config(args.config)
    exp = cfg["experiment_id"]
    c = cfg["b3"]
    out_dir = os.path.join(ROOT, "outputs")
    fig_dir = os.path.join(out_dir, "figures")
    os.makedirs(fig_dir, exist_ok=True)

    df, tcol, metrics = load_series(c)
    gran = int(c["granularity_seconds"])
    last_ts = df[tcol].iloc[-1]

    short_steps = int(round(c["short_term_hours"] * 3600 / gran))
    long_steps = int(round(c["long_term_days"] * 24 * 3600 / gran))
    long_out_every = max(1, int(round(c["long_term_output_step_seconds"] / gran)))

    print("=" * 68)
    print("B3 资源容量预测 (PatchTST-Lite)  experiment_id=%s" % exp)
    print("输入: %s  行数=%d  指标=%s" % (c["input_csv"], len(df), metrics))
    print("短期: 未来 %dh -> %d 步 @%ds；长期: 未来 %dd -> %d 步 (按 %ds 输出)"
          % (c["short_term_hours"], short_steps, gran,
             c["long_term_days"], long_steps, c["long_term_output_step_seconds"]))
    print("=" * 68)

    forecast_rows = []
    metric_reports = []

    for metric in metrics:
        series = df[metric].astype(float).to_numpy()
        fc = ChannelForecaster(
            input_window=c["input_window"], horizon=c["train_horizon"],
            patch_len=c["patch_len"], stride=c["patch_stride"],
            alpha=c["ridge_alpha"])

        rmse, mae = fc.backtest(series)
        fc.fit(series)
        last_window = series[-c["input_window"]:]

        short_fc = fc.forecast_recursive(last_window, short_steps)
        long_fc = fc.forecast_recursive(last_window, long_steps)

        resid = fc.resid_std if fc.resid_std and fc.resid_std > 0 else float(np.std(series))

        # ---- 短期：按原始粒度逐点输出 ----
        for i, v in enumerate(short_fc, start=1):
            ts = last_ts + timedelta(seconds=gran * i)
            band = 1.96 * resid * np.sqrt(1.0 + i / max(1, c["train_horizon"]))
            forecast_rows.append([exp, ts.strftime("%Y-%m-%d %H:%M:%S"), metric,
                                  round(float(v), 6), round(float(v - band), 6),
                                  round(float(v + band), 6), "short_term",
                                  c["model_version"]])

        # ---- 长期：按 long_term_output_step_seconds 下采样输出 ----
        for i in range(long_out_every, long_steps + 1, long_out_every):
            v = long_fc[i - 1]
            ts = last_ts + timedelta(seconds=gran * i)
            band = 1.96 * resid * np.sqrt(1.0 + i / max(1, c["train_horizon"]))
            forecast_rows.append([exp, ts.strftime("%Y-%m-%d %H:%M:%S"), metric,
                                  round(float(v), 6), round(float(v - band), 6),
                                  round(float(v + band), 6), "long_term",
                                  c["model_version"]])

        metric_reports.append({
            "experiment_id": exp, "metric_name": metric,
            "rmse": round(rmse, 6), "mae": round(mae, 6),
            "residual_std": round(resid, 6),
            "train_samples": max(0, len(series) - c["input_window"] - c["train_horizon"] + 1),
            "model_version": c["model_version"],
        })
        print("  [%-22s] RMSE=%.4f MAE=%.4f" % (metric, rmse, mae))

        # ---- 画图 ----
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            plt.figure(figsize=(10, 3.2))
            hist_x = np.arange(-len(series), 0)
            plt.plot(hist_x, series, label="history", color="#3366cc")
            fx = np.arange(1, short_steps + 1)
            plt.plot(fx, short_fc, label="short_term forecast", color="#dc3912")
            band = 1.96 * resid * np.sqrt(1.0 + fx / max(1, c["train_horizon"]))
            plt.fill_between(fx, short_fc - band, short_fc + band, color="#dc3912",
                             alpha=0.15, label="95% CI")
            plt.axvline(0, color="gray", ls="--", lw=0.8)
            plt.title("B3 forecast - %s (RMSE=%.3f MAE=%.3f)" % (metric, rmse, mae))
            plt.legend(loc="upper left", fontsize=8)
            plt.tight_layout()
            plt.savefig(os.path.join(fig_dir, "b3_forecast_%s.png" % metric), dpi=110)
            plt.close()
        except Exception as e:
            print("    (跳过画图: %s)" % e)

    # ---- 写 capacity_forecast_{exp}.csv ----
    fc_df = pd.DataFrame(forecast_rows, columns=[
        "experiment_id", "forecast_timestamp", "metric_name", "forecast_value",
        "confidence_lower", "confidence_upper", "horizon_type", "model_version"])
    fc_path = os.path.join(out_dir, "capacity_forecast_%s.csv" % exp)
    fc_df.to_csv(fc_path, index=False, encoding="utf-8-sig")

    # ---- 写 backtest 指标 ----
    mr_df = pd.DataFrame(metric_reports)
    mr_path = os.path.join(out_dir, "b3_backtest_metrics.csv")
    mr_df.to_csv(mr_path, index=False, encoding="utf-8-sig")

    # ---- 写基线效果报告 ----
    report = _build_report(exp, c, df, metrics, mr_df, short_steps, long_steps)
    rp_path = os.path.join(out_dir, "b3_forecast_report.md")
    with open(rp_path, "w", encoding="utf-8") as f:
        f.write(report)

    print("-" * 68)
    print("已输出:")
    print("  %s  (%d 行)" % (os.path.relpath(fc_path, ROOT), len(fc_df)))
    print("  %s" % os.path.relpath(mr_path, ROOT))
    print("  %s" % os.path.relpath(rp_path, ROOT))
    print("  outputs/figures/b3_forecast_*.png")
    print("=" * 68)


def _build_report(exp, c, df, metrics, mr_df, short_steps, long_steps):
    lines = []
    lines.append("# B3 资源容量预测 基线效果报告\n")
    lines.append("- experiment_id: `%s`" % exp)
    lines.append("- 模型: PatchTST-Lite (`%s`) —— patching + RevIN + Ridge 线性头，通道独立" % c["model_version"])
    lines.append("- 输入数据: `%s`（A1/Wu 预处理后的归一化时序，%d 行）" % (c["input_csv"], len(df)))
    lines.append("- 采样粒度: %d 秒；输入窗口 L=%d；训练预测步长 H=%d" %
                 (c["granularity_seconds"], c["input_window"], c["train_horizon"]))
    lines.append("- 预测范围: 短期 %d 小时、长期 %d 天（多步递归预测）\n" %
                 (c["short_term_hours"], c["long_term_days"]))
    lines.append("## 1. 基线预测指标 (walk-forward 回测)\n")
    lines.append("| 指标 metric | RMSE | MAE | 残差std | 训练样本 |")
    lines.append("| -- | -- | -- | -- | -- |")
    for _, r in mr_df.iterrows():
        lines.append("| %s | %.4f | %.4f | %.4f | %d |" %
                     (r["metric_name"], r["rmse"], r["mae"],
                      r["residual_std"], r["train_samples"]))
    lines.append("\n> 说明：输入为 Wu 已做 z-score 标准化的特征，故 RMSE/MAE 为标准化尺度下的误差。\n")
    lines.append("## 2. 输出接口\n")
    lines.append("`capacity_forecast_%s.csv` 遵循《第一次跨组联调测试计划 §7.2》字段：" % exp)
    lines.append("`experiment_id, forecast_timestamp, metric_name, forecast_value, "
                 "confidence_lower, confidence_upper, horizon_type, model_version`。")
    lines.append("`horizon_type` 取值 `short_term`（未来 %d 小时，按 %d 秒逐点）与 "
                 "`long_term`（未来 %d 天，按 %d 秒下采样）。\n" %
                 (c["short_term_hours"], c["granularity_seconds"],
                  c["long_term_days"], c["long_term_output_step_seconds"]))
    lines.append("## 3. 与上下游对接\n")
    lines.append("- 上游 A1(Wu): 直接消费其预处理归一化 CSV，无需再清洗。")
    lines.append("- 下游: 预测结果供容量规划与 B4 验证后复盘使用。")
    lines.append("- 说明：本 sample 数据量较小，仅用于跑通链路与产出基线指标；接入完整 "
                 "24h/7d 历史后同一套代码即可给出生产级预测。\n")
    lines.append("## 4. 复现\n")
    lines.append("```\npython -m b3_forecast.run_b3\n```\n")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
