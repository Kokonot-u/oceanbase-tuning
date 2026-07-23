#!/usr/bin/env python3
"""Build real-week2 experiment matrix, rollback plan, and perf dataset."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = ROOT / "results" / "week2"
DOC_DIR = ROOT / "docs" / "week2"
LOG_DIR = ROOT / "logs" / "week2"


def main() -> int:
    top5 = pd.read_csv(OUT_DIR / "top5_params_real.csv", dtype=str).fillna("")
    rows = [
        {
            "experiment_id": 0,
            "parameter_name": "baseline",
            "old_value": "N/A",
            "test_value": "N/A",
            "workload_name": "lightweight_real_sql",
            "repeat_id": 1,
            "expected_effect": "真实基线 workload，不修改参数",
            "risk": "LOW",
            "rollback_sql": "N/A",
            "status": "executed_baseline",
            "notes": "安全模式已执行",
        }
    ]
    rollback_lines = [
        "-- Rollback SQL for real week-2 parameter experiments.",
        "-- No parameter changes were executed in this run.",
    ]
    plan_lines = [
        "# 参数变更计划",
        "",
        "当前连接的是同事共享的 `test` 租户。本次默认安全模式：只执行参数查询、建库、建表、插入数据和 workload，不执行 ALTER SYSTEM/ALTER TENANT/SET GLOBAL。",
        "",
        "如需执行下面计划，必须先由老师/同事确认权限、影响范围和恢复命令。",
        "",
        "| 参数 | 原值 | 候选值 | 风险 | 状态 | 恢复 SQL |",
        "| -- | -- | -- | -- | -- | -- |",
    ]
    exp_id = 1
    for _, row in top5.iterrows():
        for idx in [1, 2]:
            test_value = row.get(f"test_value_{idx}", "")
            rollback = f"-- planned rollback: ALTER SYSTEM SET {row['parameter_name']} = '{row['current_value']}';"
            rows.append(
                {
                    "experiment_id": exp_id,
                    "parameter_name": row["parameter_name"],
                    "old_value": row["current_value"],
                    "test_value": test_value,
                    "workload_name": "lightweight_real_sql",
                    "repeat_id": 1,
                    "expected_effect": row["expected_effect"],
                    "risk": row["risk_level"],
                    "rollback_sql": rollback,
                    "status": "planned_not_executed_due_to_shared_tenant_or_permission",
                    "notes": "未执行参数修改；需确认权限与影响范围",
                }
            )
            rollback_lines.append(rollback)
            plan_lines.append(
                f"| {row['parameter_name']} | {row['current_value']} | {test_value} | {row['risk_level']} | planned_not_executed_due_to_shared_tenant_or_permission | `{rollback}` |"
            )
            exp_id += 1
    pd.DataFrame(rows).to_csv(OUT_DIR / "param_test_matrix_real.csv", index=False)
    (LOG_DIR / "rollback.sql").write_text("\n".join(rollback_lines) + "\n", encoding="utf-8")
    (DOC_DIR / "parameter_change_plan.md").write_text("\n".join(plan_lines) + "\n", encoding="utf-8")

    summary = pd.read_csv(OUT_DIR / "workload_summary_real.csv", dtype=str).fillna("")
    perf = pd.DataFrame(
        [
            {
                "run_id": summary.loc[0, "run_id"],
                "timestamp": summary.loc[0, "timestamp"],
                "db_host": summary.loc[0, "db_host"],
                "tenant": summary.loc[0, "tenant"],
                "database": summary.loc[0, "database"],
                "workload": summary.loc[0, "workload"],
                "parameter_name": "baseline",
                "parameter_value": "current_real_values",
                "elapsed_ms": summary.loc[0, "elapsed_ms"],
                "qps_or_tps": summary.loc[0, "qps_or_tps"],
                "avg_latency_ms": summary.loc[0, "avg_latency_ms"],
                "p95_latency_ms": summary.loc[0, "p95_latency_ms"],
                "p99_latency_ms": summary.loc[0, "p99_latency_ms"],
                "error_count": summary.loc[0, "error_count"],
                "notes": "真实 baseline；未修改参数",
            }
        ]
    )
    perf.to_csv(OUT_DIR / "param_perf_dataset_real.csv", index=False)
    perf.to_csv(OUT_DIR / "param_perf_summary_real.csv", index=False)
    print("Wrote real experiment matrix, rollback, change plan, and perf dataset")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
