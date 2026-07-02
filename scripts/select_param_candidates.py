#!/usr/bin/env python3
"""Select OceanBase performance parameter candidates from exported TSV."""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATHS = [ROOT / "outputs" / "ob_parameters.tsv", ROOT / "output" / "ob_parameters.tsv"]
OUTPUT = ROOT / "outputs" / "param_candidates.csv"

CATEGORIES = {
    "CPU调度": ["cpu", "worker", "thread", "concurrency", "parallel", "queue", "scheduler"],
    "内存管理": ["memory", "mem", "cache", "tenant", "resource", "freeze", "buffer"],
    "磁盘IO": ["io", "disk", "log", "clog", "datafile", "flush", "compaction", "bandwidth"],
    "SQL执行": ["sql", "query", "plan", "optimizer", "timeout", "cursor", "connection", "px"],
}


def find_input() -> Path | None:
    for path in INPUT_PATHS:
        if path.exists():
            return path
    return None


def norm_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {col: col.strip().lower() for col in df.columns}
    return df.rename(columns=mapping)


def field(row: pd.Series, name: str) -> str:
    return str(row.get(name, "") if pd.notna(row.get(name, "")) else "")


def score_category(row: pd.Series, keywords: list[str]) -> tuple[int, list[str]]:
    name = field(row, "name").lower()
    info = field(row, "info").lower()
    section = field(row, "section").lower()
    edit_level = field(row, "edit_level").lower()
    score = 0
    hits: list[str] = []
    for kw in keywords:
        hit_score = 0
        if kw in name:
            hit_score += 3
        if kw in section:
            hit_score += 2
        if kw in info:
            hit_score += 1
        if hit_score:
            hits.append(kw)
            score += hit_score
    if "dynamic" in edit_level:
        score += 1
    return score, hits


def main() -> int:
    source = find_input()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if source is None:
        columns = ["category", "name", "current_value", "info", "section", "edit_level", "reason", "score"]
        pd.DataFrame(columns=columns).to_csv(OUTPUT, index=False)
        print("Missing ob_parameters.tsv. Wrote empty candidate template:", OUTPUT)
        return 0

    df = pd.read_csv(source, sep="\t", dtype=str, quoting=csv.QUOTE_MINIMAL)
    df = norm_columns(df)
    required = {"name", "value", "info", "section", "edit_level"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"Missing required columns in {source}: {sorted(missing)}")

    rows = []
    for _, row in df.iterrows():
        ranked = []
        for category, keywords in CATEGORIES.items():
            score, hits = score_category(row, keywords)
            ranked.append((score, category, hits))
        score, category, hits = max(ranked, key=lambda item: item[0])
        if score <= 0:
            continue
        rows.append(
            {
                "category": category,
                "name": field(row, "name"),
                "current_value": field(row, "value"),
                "info": field(row, "info"),
                "section": field(row, "section"),
                "edit_level": field(row, "edit_level"),
                "reason": "命中关键词: " + ", ".join(hits),
                "score": score,
            }
        )

    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["score", "category", "name"], ascending=[False, True, True])
    out.to_csv(OUTPUT, index=False)
    print(f"Selected {len(out)} candidates from {source} -> {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
