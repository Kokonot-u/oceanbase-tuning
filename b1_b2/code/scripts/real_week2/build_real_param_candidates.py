#!/usr/bin/env python3
"""Build real week-2 OceanBase performance parameter candidates."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
REAL_PARAMS = ROOT / "outputs" / "real_week2" / "ob_parameters_real.tsv"
PREVIOUS_PARAMS = ROOT / "outputs" / "ob_parameters.tsv"
OUT_DIR = ROOT / "outputs" / "real_week2"
DOC_DIR = ROOT / "docs" / "real_week2"

CATEGORIES = {
    "CPU调度": ["cpu", "worker", "thread", "concurrency", "parallel", "queue", "scheduler"],
    "内存管理": ["memory", "mem", "cache", "tenant", "resource", "freeze", "buffer"],
    "磁盘IO": ["io", "disk", "log", "clog", "datafile", "flush", "compaction", "bandwidth"],
    "SQL执行": ["sql", "query", "plan", "optimizer", "timeout", "cursor", "connection", "px"],
}

PREFERRED_TOP5 = [
    "cpu_quota_concurrency",
    "memstore_limit_percentage",
    "clog_io_isolation_mode",
    "enable_sql_audit",
    "large_query_worker_percentage",
    "large_query_threshold",
    "minor_compact_trigger",
]

HIGH_RISK = ["memory_limit", "datafile_size", "log_disk_size", "cpu_count", "system_memory", "rootservice"]


def read_tsv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, sep="\t", dtype=str).fillna("")


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns={col: col.strip().lower() for col in df.columns})


def extract_range(info: str) -> str:
    patterns = [
        r"Range:\s*([^.;]+)",
        r"range:\s*([^.;]+)",
        r"ranges from\s*([^.;]+)",
        r"Value:\s*([^.;]+)",
        r"Values:\s*([^.;]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, info)
        if match:
            return match.group(1).strip()
    return "UNKNOWN"


def score(row: pd.Series, keywords: list[str]) -> tuple[int, list[str]]:
    name = row.get("name", "").lower()
    info = row.get("info", "").lower()
    section = row.get("section", "").lower()
    edit_level = row.get("edit_level", "").lower()
    total = 0
    hits: list[str] = []
    for kw in keywords:
        s = 0
        if kw in name:
            s += 3
        if kw in section:
            s += 2
        if kw in info:
            s += 1
        if s:
            total += s
            hits.append(kw)
    if "dynamic" in edit_level:
        total += 1
    return total, hits


def risk_and_modify(name: str, edit_level: str, scope: str) -> tuple[str, str]:
    lname = name.lower()
    if any(part in lname for part in HIGH_RISK):
        return "HIGH", "UNKNOWN"
    if "static" in edit_level.lower():
        return "HIGH", "UNKNOWN"
    if scope.upper() == "CLUSTER":
        return "MEDIUM", "UNKNOWN"
    if "dynamic" in edit_level.lower():
        return "LOW", "YES"
    return "MEDIUM", "UNKNOWN"


def effect(category: str, name: str) -> str:
    if category == "CPU调度":
        return "影响并发度、后台线程调度、排队和高负载响应时间"
    if category == "内存管理":
        return "影响缓存、冻结、内存水位和租户资源使用"
    if category == "磁盘IO":
        return "影响日志写入、刷盘、压缩、磁盘带宽和 IO 隔离"
    if category == "SQL执行":
        return "影响 SQL 计划、审计、长查询调度和执行超时"
    return f"观察 {name} 对 workload 指标的影响"


def gradients(name: str, current: str) -> list[str]:
    if name == "cpu_quota_concurrency":
        return ["4", "8"]
    if name == "memstore_limit_percentage":
        return ["20", "40"]
    if name == "clog_io_isolation_mode":
        return ["1", "2"]
    if name == "enable_sql_audit":
        return ["True", "False"]
    if name == "large_query_worker_percentage":
        return ["20", "40"]
    if name == "large_query_threshold":
        return ["60s", "300s"]
    if re.fullmatch(r"\d+", current or ""):
        val = int(current)
        return [str(max(0, val // 2)), str(max(val + 1, int(val * 1.5)))]
    return [current or "UNKNOWN", "MANUAL_CONFIRM"]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    real = normalize(read_tsv(REAL_PARAMS))
    prev = normalize(read_tsv(PREVIOUS_PARAMS))
    prev_by_name = {row["name"]: row for _, row in prev.iterrows()} if "name" in prev.columns else {}
    if real.empty:
        raise SystemExit(f"Missing real parameter export: {REAL_PARAMS}")

    rows = []
    for _, row in real.iterrows():
        ranked = []
        for category, keywords in CATEGORIES.items():
            s, hits = score(row, keywords)
            ranked.append((s, category, hits))
        s, category, hits = max(ranked, key=lambda item: item[0])
        if s <= 0:
            continue
        name = row.get("name", "")
        info = row.get("info", "")
        default_value = row.get("default_value", "") or "UNKNOWN"
        value_range = extract_range(info)
        evidence = "real_query"
        if (default_value == "UNKNOWN" or value_range == "UNKNOWN") and name in prev_by_name:
            prev_row = prev_by_name[name]
            default_value = default_value if default_value != "UNKNOWN" else prev_row.get("default_value", "UNKNOWN") or "UNKNOWN"
            value_range = value_range if value_range != "UNKNOWN" else extract_range(prev_row.get("info", ""))
            evidence = "real_query + previous_export"
        risk, can_modify = risk_and_modify(name, row.get("edit_level", ""), row.get("scope", ""))
        rows.append(
            {
                "parameter_name": name,
                "category": category,
                "current_value": row.get("value", ""),
                "default_value": default_value,
                "value_range": value_range,
                "core_effect": effect(category, name),
                "why_performance_related": "命中关键词: " + ", ".join(hits),
                "risk_level": risk,
                "can_modify": can_modify,
                "evidence_source": evidence,
                "notes": f"scope={row.get('scope', 'UNKNOWN')}; edit_level={row.get('edit_level', 'UNKNOWN')}; section={row.get('section', 'UNKNOWN')}; score={s}",
                "score": s,
            }
        )

    candidates = pd.DataFrame(rows).sort_values(["score", "risk_level", "parameter_name"], ascending=[False, True, True])
    candidates.to_csv(OUT_DIR / "param_candidates_real.csv", index=False)
    candidates.head(100).drop(columns=["score"]).to_csv(OUT_DIR / "top100_performance_params_real.csv", index=False)

    top_pool = candidates[candidates["risk_level"].isin(["LOW", "MEDIUM"])].copy()
    top_pool["pref_rank"] = top_pool["parameter_name"].apply(lambda n: PREFERRED_TOP5.index(n) if n in PREFERRED_TOP5 else 999)
    chosen = []
    used = set()
    for category in ["CPU调度", "内存管理", "磁盘IO", "SQL执行"]:
        part = top_pool[top_pool["category"].eq(category)].sort_values(["pref_rank", "score"], ascending=[True, False])
        if not part.empty:
            row = part.iloc[0]
            chosen.append(row)
            used.add(row["parameter_name"])
    for _, row in top_pool.sort_values(["pref_rank", "score"], ascending=[True, False]).iterrows():
        if len(chosen) >= 5:
            break
        if row["parameter_name"] not in used:
            chosen.append(row)
            used.add(row["parameter_name"])

    top5_rows = []
    for row in chosen[:5]:
        vals = gradients(row["parameter_name"], row["current_value"])
        top5_rows.append(
            {
                "parameter_name": row["parameter_name"],
                "category": row["category"],
                "current_value": row["current_value"],
                "test_value_1": vals[0],
                "test_value_2": vals[1],
                "risk_level": row["risk_level"],
                "can_modify": row["can_modify"],
                "expected_effect": row["core_effect"],
                "evidence_source": row["evidence_source"],
                "notes": "仅生成参数实验计划；共享 test 租户默认不直接执行 ALTER SYSTEM/ALTER TENANT",
            }
        )
    top5 = pd.DataFrame(top5_rows)
    top5.to_csv(OUT_DIR / "top5_params_real.csv", index=False)

    lines = [
        "# Top5 真实参数选择说明",
        "",
        "Top5 基于真实 `SHOW PARAMETERS` 导出结果生成；默认只做安全模式，不直接修改共享 test 租户参数。",
        "",
        "| 参数 | 类别 | 当前值 | 风险 | 可修改性 | 依据 |",
        "| -- | -- | -- | -- | -- | -- |",
    ]
    for _, row in top5.iterrows():
        lines.append(
            f"| {row['parameter_name']} | {row['category']} | {row['current_value']} | {row['risk_level']} | {row['can_modify']} | {row['expected_effect']} |"
        )
    lines.append("")
    lines.append("所有候选值执行前需老师/同事确认，并先写入 rollback SQL。")
    (DOC_DIR / "top5_params_explanation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"real candidates={len(candidates)}, top100={min(100, len(candidates))}, top5={len(top5)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
