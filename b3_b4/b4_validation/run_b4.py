# -*- coding: utf-8 -*-
"""
B4 参数调优效果自动化验证 —— 主入口
====================================
输入：
  - Wang(B2) 调优建议 inputs/b2_tuning_recommendations_real_week4.csv
  - Wang 真实 baseline 性能 inputs/baseline_perf/param_perf_dataset_real.csv
输出（outputs/）：
  - validation_report_{experiment_id}.md      验证报告（联调测试计划 §7.1）
  - b4_validation_results_{experiment_id}.csv  机器可读的逐条验证结果
  - figures/b4_before_after_*.png              调优前后吞吐对比图

用法（在 b3_b4/ 目录下）：
  python -m b4_validation.run_b4
  python -m b4_validation.run_b4 --config config.json
"""

import os
import json
import argparse

from b4_validation.validator import run_validation

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(ROOT, "config.json"))
    args = ap.parse_args()
    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    print("=" * 68)
    print("B4 参数调优效果自动化验证  experiment_id=%s  mode=%s"
          % (cfg["experiment_id"], cfg["b4"]["mode"]))
    print("=" * 68)

    res_df, res_path, rep_path, executed, skipped = run_validation(cfg, ROOT)

    print("已批准自动验证: %d 条；转人工审核(高风险): %d 条" % (executed, skipped))
    promoted = (res_df["promote"] == "yes").sum()
    print("达到推广阈值: %d 条" % promoted)
    print("-" * 68)
    print("已输出:")
    print("  %s  (%d 行)" % (os.path.relpath(res_path, ROOT), len(res_df)))
    print("  %s" % os.path.relpath(rep_path, ROOT))
    print("  outputs/figures/b4_before_after_*.png")
    print("=" * 68)


if __name__ == "__main__":
    main()
