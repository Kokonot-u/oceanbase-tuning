"""Tests for week-4 B1/B2 offline deliverable builders."""

from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.real_week4.build_b1_b2_week4_outputs import (
    Baseline,
    build_action_space,
    build_feature_matrix,
    build_top30,
    reward,
)


def test_build_top30_and_action_space_from_candidates():
    candidates = pd.DataFrame(
        [
            {
                "parameter_name": "log_disk_utilization_threshold",
                "category": "磁盘IO",
                "current_value": "80",
                "default_value": "80",
                "value_range": "[10, 100)",
                "why_performance_related": "命中关键词: io, disk, log",
                "risk_level": "LOW",
                "can_modify": "YES",
                "evidence_source": "real_query",
                "notes": "scope=TENANT; edit_level=DYNAMIC_EFFECTIVE; score=15",
                "score": "15",
            },
            {
                "parameter_name": "enable_sql_audit",
                "category": "SQL执行",
                "current_value": "True",
                "default_value": "True",
                "value_range": "UNKNOWN",
                "why_performance_related": "命中关键词: sql",
                "risk_level": "MEDIUM",
                "can_modify": "UNKNOWN",
                "evidence_source": "real_query",
                "notes": "scope=CLUSTER; edit_level=DYNAMIC_EFFECTIVE; score=5",
                "score": "5",
            },
        ]
    )
    baselines = {
        "lightweight_real_sql": Baseline("lightweight_real_sql", 7.17, 139.228, 178.12, 239.711, 0),
        "BenchmarkSQL_TPC-C": Baseline("BenchmarkSQL_TPC-C", 1.826, 312.3, 716.0, 726.0, 0),
        "TPC-H-22-lightweight-real": Baseline("TPC-H-22-lightweight-real", 6.5269, 153.213, 192.592, 285.852, 0),
    }

    feature_matrix = build_feature_matrix(candidates, baselines)
    top30 = build_top30(feature_matrix)
    action_space = build_action_space(top30)

    assert len(feature_matrix) == 6
    assert top30.iloc[0]["parameter_name"] == "log_disk_utilization_threshold"
    assert action_space.iloc[0]["action_type"] == "numeric"
    assert action_space.iloc[0]["auto_execute_allowed"] == 1
    assert set(action_space["parameter_name"]) == {
        "log_disk_utilization_threshold",
        "enable_sql_audit",
    }


def test_composite_reward_penalizes_unsafe_actions():
    safe = reward(0.10, 0.10, 0.05, 0.0, 0.0)
    unsafe = reward(0.10, 0.10, 0.05, 0.0, 0.20)

    assert safe > unsafe
    assert round(safe, 4) == 0.085
