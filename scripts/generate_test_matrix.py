#!/usr/bin/env python3
"""Expand selected OceanBase parameters into a workload test matrix."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
SELECTED = ROOT / "outputs" / "selected_5_params.csv"
MATRIX = ROOT / "outputs" / "param_test_matrix.csv"
YAML_OUT = ROOT / "configs" / "param_test_matrix.yaml"


def main() -> int:
    if not SELECTED.exists():
        raise SystemExit("Run scripts/choose_top5_params.py first.")
    selected = pd.read_csv(SELECTED, dtype=str).fillna("")
    rows = []
    experiment_id = 1
    for _, row in selected.iterrows():
        values = [row.get(f"test_value_{idx}", "") for idx in range(1, 5)]
        for test_round, value in enumerate([v for v in values if v], start=1):
            for workload in ["tpcc", "tpch"]:
                rows.append(
                    {
                        "experiment_id": experiment_id,
                        "param_name": row["param_name"],
                        "category": row["category"],
                        "original_value": row["original_value"],
                        "test_value": value,
                        "workload_type": workload,
                        "test_round": test_round,
                        "expected_impact": row["expected_impact"],
                        "risk_level": row["risk_level"],
                        "need_restart": row["need_restart"],
                        "status": "pending",
                        "note": row["note"],
                    }
                )
                experiment_id += 1
    out = pd.DataFrame(rows)
    out.to_csv(MATRIX, index=False)
    YAML_OUT.write_text(yaml.safe_dump(rows, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"Wrote {len(out)} experiment rows -> {MATRIX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
