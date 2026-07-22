#!/usr/bin/env python3
"""Build week-4 B1/B2 offline deliverables from real week-2 data.

The current project has real OceanBase parameter exports and real baseline
workload results, but no authorized parameter-change trials yet. This script
therefore produces an auditable offline baseline:

- B1: feature engineering and Top30 parameter impact ranking.
- B2: safe action space, reward definition, and deterministic offline policy.
- Integration: B1 TopK -> B2 action candidates mapping report.
"""

from __future__ import annotations

import csv
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
WEEK2 = ROOT / "outputs" / "real_week2"
OUT = ROOT / "outputs" / "real_week4"
DOC = ROOT / "docs" / "real_week4"
WEEKLY = ROOT / "weekly_deliverables" / "week4" / "B_group"


CATEGORY_WEIGHT = {
    "CPU调度": 0.88,
    "内存管理": 0.84,
    "磁盘IO": 0.90,
    "SQL执行": 0.78,
}

RISK_WEIGHT = {
    "LOW": 1.00,
    "MEDIUM": 0.72,
    "HIGH": 0.38,
    "UNKNOWN": 0.50,
}

MODIFY_WEIGHT = {
    "YES": 1.00,
    "UNKNOWN": 0.62,
    "NO": 0.15,
}

WORKLOAD_HINT = {
    "CPU调度": {
        "TPC-C": 0.82,
        "TPC-H": 0.78,
        "lightweight_sql": 0.66,
        "reason": "并发调度和后台线程会影响事务排队与大查询执行资源。",
    },
    "内存管理": {
        "TPC-C": 0.76,
        "TPC-H": 0.88,
        "lightweight_sql": 0.60,
        "reason": "内存水位、缓存和冻结行为会影响写入路径与大查询中间结果。",
    },
    "磁盘IO": {
        "TPC-C": 0.90,
        "TPC-H": 0.70,
        "lightweight_sql": 0.58,
        "reason": "日志写入、刷盘和 IO 隔离对写事务路径更敏感。",
    },
    "SQL执行": {
        "TPC-C": 0.66,
        "TPC-H": 0.86,
        "lightweight_sql": 0.62,
        "reason": "SQL 审计、计划和长查询调度对复杂查询更敏感。",
    },
}


@dataclass
class Baseline:
    workload: str
    throughput: float
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    error_count: int


def ensure_dirs() -> None:
    for path in [
        OUT,
        DOC,
        WEEKLY / "docs",
        WEEKLY / "results",
        WEEKLY / "interfaces",
        WEEKLY / "tests",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, dtype=str).fillna("")


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value == "" or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def parse_score(notes: str, fallback: float = 0.0) -> float:
    match = re.search(r"score=([0-9.]+)", notes or "")
    return float(match.group(1)) if match else fallback


def parse_range(value_range: str, current_value: str, parameter_name: str) -> tuple[str, float | None, float | None, float | None, list[str]]:
    """Infer action encoding and numeric bounds from OceanBase range text."""
    text = (value_range or "").strip()
    current_num = to_float(re.sub(r"[^0-9.]", "", current_value), 0.0)

    if parameter_name == "clog_io_isolation_mode":
        return "enum", 1.0, 2.0, 1.0, ["1", "2"]
    if parameter_name == "enable_sql_audit" or current_value in {"True", "False", "true", "false"}:
        return "bool", 0.0, 1.0, 1.0, ["True", "False"]

    nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", text)]
    if len(nums) >= 2:
        low, high = nums[0], nums[1]
    elif len(nums) == 1:
        low, high = 0.0, nums[0]
    else:
        low = max(0.0, current_num * 0.5)
        high = max(current_num + 1.0, current_num * 1.5 if current_num else 100.0)

    if high <= low:
        high = low + max(1.0, abs(low) * 0.5)
    step = max(1.0, round((high - low) / 4.0, 4))
    return "numeric", low, high, step, []


def load_baselines() -> dict[str, Baseline]:
    perf = read_csv(WEEK2 / "param_perf_dataset_real.csv")
    baselines: dict[str, Baseline] = {}
    for _, row in perf.iterrows():
        workload = row["workload"]
        baselines[workload] = Baseline(
            workload=workload,
            throughput=to_float(row.get("qps_or_tps")),
            avg_latency_ms=to_float(row.get("avg_latency_ms")),
            p95_latency_ms=to_float(row.get("p95_latency_ms")),
            p99_latency_ms=to_float(row.get("p99_latency_ms")),
            error_count=int(to_float(row.get("error_count"), 0)),
        )
    return baselines


def build_feature_matrix(candidates: pd.DataFrame, baselines: dict[str, Baseline]) -> pd.DataFrame:
    max_raw = max([to_float(x) for x in candidates.get("score", pd.Series(["0"]))] + [1.0])
    rows: list[dict[str, Any]] = []
    for _, row in candidates.iterrows():
        category = row["category"]
        raw_score = to_float(row.get("score"), parse_score(row.get("notes", "")))
        risk = row.get("risk_level", "UNKNOWN")
        can_modify = row.get("can_modify", "UNKNOWN")
        action_type, min_value, max_value, step, enum_values = parse_range(
            row.get("value_range", ""),
            row.get("current_value", ""),
            row.get("parameter_name", ""),
        )
        dynamic = 1 if "DYNAMIC" in row.get("notes", "").upper() else 0
        tenant_scope = 1 if "scope=TENANT" in row.get("notes", "").upper() else 0
        range_known = 0 if row.get("value_range", "UNKNOWN") == "UNKNOWN" else 1
        doc_hint = 1 if "previous_export" in row.get("evidence_source", "") else 0
        category_prior = CATEGORY_WEIGHT.get(category, 0.55)
        safety = RISK_WEIGHT.get(risk, 0.50) * MODIFY_WEIGHT.get(can_modify, 0.50)
        workload_prior = WORKLOAD_HINT.get(category, WORKLOAD_HINT["SQL执行"])

        for workload_key, baseline_name in [
            ("lightweight_sql", "lightweight_real_sql"),
            ("TPC-C", "BenchmarkSQL_TPC-C"),
            ("TPC-H", "TPC-H-22-lightweight-real"),
        ]:
            baseline = baselines.get(baseline_name, Baseline(baseline_name, 0.0, 0.0, 0.0, 0.0, 0))
            workload_weight = workload_prior[workload_key]
            normalized_keyword_score = raw_score / max_raw
            impact_score = (
                0.34 * normalized_keyword_score
                + 0.20 * category_prior
                + 0.18 * workload_weight
                + 0.12 * safety
                + 0.08 * dynamic
                + 0.05 * range_known
                + 0.03 * doc_hint
            )
            rows.append(
                {
                    "experiment_id": "real_week4_offline",
                    "parameter_name": row["parameter_name"],
                    "category": category,
                    "workload_type": workload_key,
                    "current_value": row.get("current_value", ""),
                    "default_value": row.get("default_value", ""),
                    "value_range": row.get("value_range", ""),
                    "action_type": action_type,
                    "min_value": "" if min_value is None else min_value,
                    "max_value": "" if max_value is None else max_value,
                    "step": "" if step is None else step,
                    "enum_values": "|".join(enum_values),
                    "raw_keyword_score": raw_score,
                    "normalized_keyword_score": round(normalized_keyword_score, 6),
                    "category_prior": category_prior,
                    "workload_prior": workload_weight,
                    "safety_score": round(safety, 6),
                    "dynamic_effective": dynamic,
                    "tenant_scope": tenant_scope,
                    "range_known": range_known,
                    "doc_hint_available": doc_hint,
                    "baseline_throughput": baseline.throughput,
                    "baseline_avg_latency_ms": baseline.avg_latency_ms,
                    "baseline_p95_latency_ms": baseline.p95_latency_ms,
                    "baseline_p99_latency_ms": baseline.p99_latency_ms,
                    "impact_score": round(impact_score, 6),
                    "risk_level": risk,
                    "can_modify": can_modify,
                    "evidence": row.get("why_performance_related", ""),
                    "interpretation": WORKLOAD_HINT.get(category, WORKLOAD_HINT["SQL执行"])["reason"],
                }
            )
    return pd.DataFrame(rows)


def build_top30(feature_matrix: pd.DataFrame) -> pd.DataFrame:
    agg = (
        feature_matrix.groupby(["parameter_name", "category"], as_index=False)
        .agg(
            importance_score=("impact_score", "mean"),
            max_workload_score=("impact_score", "max"),
            safety_score=("safety_score", "max"),
            raw_keyword_score=("raw_keyword_score", "max"),
            risk_level=("risk_level", "first"),
            can_modify=("can_modify", "first"),
            action_type=("action_type", "first"),
            min_value=("min_value", "first"),
            max_value=("max_value", "first"),
            step=("step", "first"),
            enum_values=("enum_values", "first"),
            interpretation=("interpretation", "first"),
        )
        .sort_values(["importance_score", "safety_score", "raw_keyword_score"], ascending=[False, False, False])
    )
    agg["rank"] = range(1, len(agg) + 1)
    return agg.head(30)[
        [
            "rank",
            "parameter_name",
            "category",
            "importance_score",
            "max_workload_score",
            "safety_score",
            "risk_level",
            "can_modify",
            "action_type",
            "min_value",
            "max_value",
            "step",
            "enum_values",
            "interpretation",
        ]
    ]


def build_action_space(top30: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in top30.iterrows():
        auto_allowed = row["risk_level"] == "LOW" and row["can_modify"] == "YES"
        requires_approval = not auto_allowed
        rows.append(
            {
                "experiment_id": "real_week4_offline",
                "rank": row["rank"],
                "parameter_name": row["parameter_name"],
                "category": row["category"],
                "action_type": row["action_type"],
                "current_value": "",
                "min_value": row["min_value"],
                "max_value": row["max_value"],
                "step": row["step"],
                "enum_values": row["enum_values"],
                "risk_level": row["risk_level"],
                "can_modify": row["can_modify"],
                "auto_execute_allowed": int(auto_allowed),
                "requires_approval": int(requires_approval),
                "action_mask_reason": "allowed_offline_recommendation_only"
                if auto_allowed
                else "manual_approval_required_due_to_risk_or_unknown_modifiability",
            }
        )
    return pd.DataFrame(rows)


def reward(throughput_gain: float, p95_reduction: float, p99_reduction: float, error_penalty: float, safety_penalty: float) -> float:
    return (
        0.45 * throughput_gain
        + 0.35 * p95_reduction
        + 0.10 * p99_reduction
        - 0.10 * error_penalty
        - safety_penalty
    )


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_empty_"
    cols = list(df.columns)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["--"] * len(cols)) + " |",
    ]
    for _, row in df.iterrows():
        values = [str(row.get(col, "")).replace("|", "\\|") for col in cols]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def simulate_policy(top30: pd.DataFrame, baselines: dict[str, Baseline]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create deterministic offline policy rows and evaluation from feature scores."""
    rows = []
    evaluations = []
    workloads = [
        ("TPC-C", "BenchmarkSQL_TPC-C", "tps"),
        ("TPC-H", "TPC-H-22-lightweight-real", "qps"),
    ]
    for _, param in top30.head(10).iterrows():
        for workload_short, workload_name, throughput_name in workloads:
            baseline = baselines[workload_name]
            importance = to_float(param["importance_score"])
            safety_score = to_float(param["safety_score"])
            risk = param["risk_level"]
            approval_penalty = 0.08 if risk != "LOW" else 0.0
            throughput_gain = max(0.0, (importance - 0.50) * (0.12 if workload_short == "TPC-C" else 0.08))
            p95_reduction = max(0.0, (importance - 0.48) * (0.18 if workload_short == "TPC-H" else 0.12))
            p99_reduction = max(0.0, p95_reduction * 0.75)
            error_penalty = 0.0
            safety_penalty = max(0.0, 0.12 - 0.12 * safety_score) + approval_penalty
            estimated_reward = reward(throughput_gain, p95_reduction, p99_reduction, error_penalty, safety_penalty)
            recommended_value = recommend_value(param)
            rows.append(
                {
                    "policy_id": f"policy_{int(param['rank']):02d}_{workload_short.lower()}",
                    "experiment_id": "real_week4_offline",
                    "workload_type": workload_short,
                    "parameter_name": param["parameter_name"],
                    "recommended_value": recommended_value,
                    "expected_metric": throughput_name,
                    "estimated_throughput_gain": round(throughput_gain, 6),
                    "estimated_p95_reduction": round(p95_reduction, 6),
                    "estimated_reward": round(estimated_reward, 6),
                    "requires_approval": int(risk != "LOW" or param["can_modify"] != "YES"),
                    "evidence": param["interpretation"],
                }
            )
            evaluations.append(
                {
                    "workload_type": workload_short,
                    "baseline_throughput": baseline.throughput,
                    "baseline_p95_latency_ms": baseline.p95_latency_ms,
                    "parameter_name": param["parameter_name"],
                    "recommended_value": recommended_value,
                    "estimated_reward": round(estimated_reward, 6),
                    "offline_eval_note": "surrogate_from_week2_baseline_no_parameter_change_executed",
                }
            )
    policy_df = pd.DataFrame(rows).sort_values(["workload_type", "estimated_reward"], ascending=[True, False])
    eval_df = pd.DataFrame(evaluations).sort_values(["workload_type", "estimated_reward"], ascending=[True, False])
    return policy_df, eval_df


def recommend_value(row: pd.Series) -> str:
    action_type = row["action_type"]
    if action_type == "bool":
        return "False" if row["parameter_name"] == "enable_sql_audit" else "True"
    if action_type == "enum":
        values = str(row.get("enum_values", "")).split("|")
        return values[-1] if values and values[-1] else str(row.get("max_value", ""))
    min_value = to_float(row.get("min_value"), 0.0)
    max_value = to_float(row.get("max_value"), min_value)
    current = min_value + 0.5 * (max_value - min_value)
    if math.isclose(current, round(current)):
        return str(int(round(current)))
    return str(round(current, 4))


def write_markdown(top30: pd.DataFrame, action_space: pd.DataFrame, policy: pd.DataFrame, baselines: dict[str, Baseline]) -> None:
    report = DOC / "b1_parameter_impact_report_real_week4.md"
    lines = [
        "# B1 参数影响因子分析报告 - real_week4",
        "",
        "负责人：Wang",
        "",
        "## 数据来源",
        "",
        "- 参数候选：`outputs/real_week2/param_candidates_real.csv`，共 347 个性能相关候选参数。",
        "- 基线性能：`outputs/real_week2/param_perf_dataset_real.csv`，包含轻量 SQL、BenchmarkSQL TPC-C、TPC-H 22 查询。",
        "- 当前限制：共享 `test` 租户尚未开放参数修改窗口，因此本报告使用离线启发式特征工程，不声称已经完成真实改参因果验证。",
        "",
        "## Top30 参数影响力",
        "",
        markdown_table(top30),
        "",
        "## 方法说明",
        "",
        "影响力得分由关键词/参数元信息、参数类别先验、workload 相关性、安全可执行性、动态生效、范围可解析性、文档证据共同加权得到。该方法用于在样本不足阶段为 B2 缩小动作空间，后续真实参数实验产出后应替换或叠加 Lasso、RandomForest、XGBoost、SHAP 等数据驱动重要性。",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")

    rl_report = DOC / "b2_offline_rl_evaluation_real_week4.md"
    best = policy.sort_values("estimated_reward", ascending=False).head(10)
    lines = [
        "# B2 离线强化学习调优框架与评估 - real_week4",
        "",
        "负责人：Wang",
        "",
        "## 框架实现",
        "",
        "- State：workload 类型、baseline throughput、avg/P95/P99 latency、error_count，以及 B1 输出的参数特征。",
        "- Action：B1 Top30 参数映射出的安全动作空间，包含 numeric/enum/bool 三类动作。",
        "- Reward：`0.45 * throughput_gain + 0.35 * p95_reduction + 0.10 * p99_reduction - 0.10 * error_penalty - safety_penalty`。",
        "- Agent：当前交付为离线 surrogate policy，等真实改参样本和 A 组系统指标补齐后接入 DDPG/TD3 训练。",
        "",
        "## Baseline",
        "",
        f"- TPC-C：throughput={baselines['BenchmarkSQL_TPC-C'].throughput}, P95={baselines['BenchmarkSQL_TPC-C'].p95_latency_ms} ms。",
        f"- TPC-H：throughput={baselines['TPC-H-22-lightweight-real'].throughput}, P95={baselines['TPC-H-22-lightweight-real'].p95_latency_ms} ms。",
        "",
        "## 离线策略 Top10",
        "",
        markdown_table(best),
        "",
        "## 风险边界",
        "",
        "本周没有在共享 `test` 租户执行参数修改。所有推荐均为离线建议，必须经 B4 自动化验证框架和人工审批后才能进入真实执行。",
    ]
    rl_report.write_text("\n".join(lines) + "\n", encoding="utf-8")

    integration = DOC / "b1_b2_integration_test_report_real_week4.md"
    mapped = action_space[action_space["parameter_name"].isin(top30.head(10)["parameter_name"])]
    lines = [
        "# B1-B2 内部联调测试报告 - real_week4",
        "",
        "## 测试目标",
        "",
        "验证 B1 Top 参数筛选结果可以自动映射为 B2 动作空间，并生成离线调优策略。",
        "",
        "## 测试结果",
        "",
        f"- B1 输出 Top30 参数：{len(top30)} 个。",
        f"- B2 动作空间参数：{len(action_space)} 个。",
        f"- 离线策略建议：{len(policy)} 条。",
        f"- 自动执行允许参数：{int(action_space['auto_execute_allowed'].sum())} 个；其余进入人工审核。",
        "",
        "## 映射样例",
        "",
        markdown_table(mapped.head(10)),
        "",
        "## 结论",
        "",
        "B1 到 B2 的参数名、动作类型、范围、风险等级和审批标记已打通。下一步需要 Huang 的 B4 验证模块消费 `b2_tuning_recommendations_real_week4.csv`，并在授权窗口执行单轮验证。",
    ]
    integration.write_text("\n".join(lines) + "\n", encoding="utf-8")


def copy_to_weekly() -> None:
    files = [
        OUT / "b1_feature_matrix_real_week4.csv",
        OUT / "b1_top30_parameter_importance_real_week4.csv",
        OUT / "b2_action_space_real_week4.csv",
        OUT / "b2_tuning_recommendations_real_week4.csv",
        OUT / "b2_offline_eval_real_week4.csv",
        DOC / "b1_parameter_impact_report_real_week4.md",
        DOC / "b2_offline_rl_evaluation_real_week4.md",
        DOC / "b1_b2_integration_test_report_real_week4.md",
    ]
    for src in files:
        if src.suffix == ".md":
            dst = WEEKLY / "docs" / src.name
        elif "action_space" in src.name:
            dst = WEEKLY / "interfaces" / src.name
        elif "integration_test" in src.name:
            dst = WEEKLY / "tests" / src.name
        else:
            dst = WEEKLY / "results" / src.name
        dst.write_bytes(src.read_bytes())

    readme = ROOT / "weekly_deliverables" / "week4" / "README.md"
    readme.parent.mkdir(parents=True, exist_ok=True)
    readme.write_text(
        """# Week 4 Deliverables

第四周产出按组整理。

## B 组

- 目录：`B_group/`
- 内容：B1 参数影响因子分析模块输出、B2 离线强化学习调优框架输出、B1-B2 内部联调报告。

## 说明

当前结果基于第二周真实 baseline 与参数候选表构建，未在共享 `test` 租户执行参数修改。所有 B2 推荐均为离线策略建议，后续需要 B4 验证和人工审批。
""",
        encoding="utf-8",
    )
    (ROOT / "weekly_deliverables" / "week4" / "A_group").mkdir(parents=True, exist_ok=True)
    (ROOT / "weekly_deliverables" / "week4" / "A_group" / ".gitkeep").touch()


def main() -> int:
    ensure_dirs()
    candidates = read_csv(WEEK2 / "param_candidates_real.csv")
    baselines = load_baselines()
    feature_matrix = build_feature_matrix(candidates, baselines)
    top30 = build_top30(feature_matrix)
    action_space = build_action_space(top30)
    policy, eval_df = simulate_policy(top30, baselines)

    feature_matrix.to_csv(OUT / "b1_feature_matrix_real_week4.csv", index=False)
    top30.to_csv(OUT / "b1_top30_parameter_importance_real_week4.csv", index=False)
    action_space.to_csv(OUT / "b2_action_space_real_week4.csv", index=False)
    policy.to_csv(OUT / "b2_tuning_recommendations_real_week4.csv", index=False)
    eval_df.to_csv(OUT / "b2_offline_eval_real_week4.csv", index=False)
    write_markdown(top30, action_space, policy, baselines)
    copy_to_weekly()

    print(json.dumps({
        "feature_matrix_rows": len(feature_matrix),
        "top30_rows": len(top30),
        "action_space_rows": len(action_space),
        "recommendation_rows": len(policy),
        "output_dir": str(OUT),
        "weekly_dir": str(WEEKLY),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
