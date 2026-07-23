#!/usr/bin/env python3
"""Choose five conservative OceanBase parameters for first-round testing."""

from __future__ import annotations

from pathlib import Path
import re

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "outputs" / "param_candidates.csv"
SELECTED = ROOT / "outputs" / "selected_5_params.csv"
DOC = ROOT / "docs" / "selected_params_explanation.md"
YAML_OUT = ROOT / "configs" / "selected_5_params.yaml"

PREFERRED = [
    "cpu_quota_concurrency",
    "large_query_worker_percentage",
    "memstore_limit_percentage",
    "cache_wash_threshold",
    "clog_io_isolation_mode",
    "minor_compact_trigger",
    "enable_sql_audit",
    "large_query_threshold",
    "enable_sql_operator_dump",
    "bf_cache_priority",
]

DANGEROUS_HINTS = ["memory_limit", "datafile_size", "log_disk_size", "cpu_count", "system_memory"]


def risk_level(name: str, edit_level: str) -> str:
    lname = name.lower()
    if any(hint in lname for hint in DANGEROUS_HINTS):
        return "high"
    if "static" in str(edit_level).lower():
        return "medium"
    return "medium"


def need_restart(edit_level: str) -> str:
    return "yes" if "static" in str(edit_level).lower() else "no"


def gradients(name: str, original: str) -> list[str]:
    lname = name.lower()
    if lname == "cpu_quota_concurrency":
        return ["4", "8", original or "10", "16"]
    if lname == "large_query_worker_percentage":
        return ["10", "20", original or "30", "40"]
    if lname == "memstore_limit_percentage":
        return ["0", "20", "40", "60"]
    if lname == "cache_wash_threshold":
        return ["1GB", "2GB", original or "4GB", "6GB"]
    if lname == "clog_io_isolation_mode":
        return ["1", "2", original or "1", "1"]
    if lname == "minor_compact_trigger":
        return ["2", "4", "8", "12"]
    if lname == "large_query_threshold":
        return ["60s", "300s", original or "600s", "900s"]
    if re.fullmatch(r"\d+", str(original or "")):
        val = int(original)
        return [str(max(0, val // 2)), str(val), str(max(val + 1, int(val * 1.5))), str(max(val + 2, val * 2))]
    return ["conservative", original or "default", "aggressive", "manual_confirm"]


def expected_impact(category: str, name: str) -> str:
    if category == "CPU调度":
        return "影响并发执行、后台任务调度和高负载下排队时间"
    if category == "内存管理":
        return "影响缓存命中、冻结频率和内存压力"
    if category == "磁盘IO":
        return "影响日志写入、刷盘、压缩和磁盘吞吐"
    if category == "SQL执行":
        return "影响 SQL 执行路径、审计开销和长查询调度"
    return f"观察 {name} 对吞吐与延迟的影响"


def pick_rows(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["pref_rank"] = df["name"].apply(lambda n: PREFERRED.index(n) if n in PREFERRED else 999)
    df["risk_level"] = df.apply(lambda r: risk_level(r["name"], r.get("edit_level", "")), axis=1)
    df = df[~df["risk_level"].eq("high")]
    recommended = df.sort_values(["pref_rank", "score"], ascending=[True, False]).head(15)

    chosen = []
    used = set()
    for category in ["CPU调度", "内存管理", "磁盘IO", "SQL执行"]:
        part = recommended[recommended["category"].eq(category)]
        if not part.empty:
            row = part.iloc[0]
            chosen.append(row)
            used.add(row["name"])
    for _, row in recommended.iterrows():
        if len(chosen) >= 5:
            break
        if row["name"] not in used:
            chosen.append(row)
            used.add(row["name"])
    return pd.DataFrame(chosen[:5])


def markdown_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["--"] * len(cols)) + " |"]
    for _, row in df.iterrows():
        vals = [str(row.get(col, "")).replace("|", "\\|").replace("\n", " ") for col in cols]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def main() -> int:
    if not CANDIDATES.exists():
        raise SystemExit("Run scripts/select_param_candidates.py first.")
    df = pd.read_csv(CANDIDATES, dtype=str)
    if "score" in df.columns:
        df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0)
    if df.empty:
        raise SystemExit("No parameter candidates found.")

    chosen = pick_rows(df)
    rows = []
    for _, row in chosen.iterrows():
        values = gradients(str(row["name"]), str(row.get("current_value", "")))
        rows.append(
            {
                "param_name": row["name"],
                "category": row["category"],
                "original_value": row.get("current_value", ""),
                "test_value_1": values[0],
                "test_value_2": values[1],
                "test_value_3": values[2],
                "test_value_4": values[3],
                "workload_tpcc": "yes",
                "workload_tpch": "yes",
                "expected_impact": expected_impact(row["category"], row["name"]),
                "risk_level": risk_level(row["name"], row.get("edit_level", "")),
                "need_restart": need_restart(row.get("edit_level", "")),
                "note": "需要人工确认官方文档默认值和范围；脚本不会自动执行 ALTER SYSTEM SET",
            }
        )

    out = pd.DataFrame(rows)
    SELECTED.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(SELECTED, index=False)
    YAML_OUT.parent.mkdir(parents=True, exist_ok=True)
    YAML_OUT.write_text(yaml.safe_dump(rows, allow_unicode=True, sort_keys=False), encoding="utf-8")

    DOC.parent.mkdir(parents=True, exist_ok=True)
    table = markdown_table(out)
    DOC.write_text(
        "# 5 个核心参数选择说明\n\n"
        "本轮从第一周导出的 OceanBase 参数表中，按 CPU 调度、内存管理、磁盘 IO、SQL 执行四类筛选候选参数。"
        "选择时优先覆盖多类性能机制，避开明显高风险或可能导致 observer 无法启动的参数。"
        "所有梯度均为保守占位，真实执行前必须核对官方文档范围和当前租户资源。\n\n"
        f"{table}\n\n"
        "注意：本脚本只生成建议，不执行参数修改。\n",
        encoding="utf-8",
    )
    print(f"Wrote selected params -> {SELECTED}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
