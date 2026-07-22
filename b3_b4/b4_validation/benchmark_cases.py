# -*- coding: utf-8 -*-
"""
B4 模块一：基准测试用例封装
============================
把 TPC-C / TPC-H 基准测试抽象成统一的 BenchmarkCase 接口，屏蔽底层是
BenchmarkSQL 还是 tpch-obs。B4 调度器只需要调用 case.run(param_overrides)
就能拿到一组标准化性能指标。

两种运行模式：
  - simulation（默认）：不连真库，基于 Wang(B2) 给出的预期收益 + Wu 的真实
    baseline，确定性地推算“调优后”指标，用于跑通链路和自动化验证 Demo。
  - real：预留真实执行钩子（连独立测试租户跑 BenchmarkSQL/tpch）。当前抛出
    NotImplementedError，接入真实租户时在这里实现即可。
"""

import hashlib


def _stable_jitter(key, scale=0.01):
    """由字符串 key 生成确定性的小扰动，模拟真实跑批的轻微波动。"""
    h = int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16)
    return ((h % 1000) / 1000.0 - 0.5) * 2 * scale  # [-scale, +scale]


class BenchmarkCase:
    def __init__(self, name, workload_type, baseline_metrics, mode="simulation"):
        """
        baseline_metrics: dict，含 throughput / avg_latency_ms /
                          p95_latency_ms / p99_latency_ms / throughput_metric
        """
        self.name = name
        self.workload_type = workload_type
        self.baseline = dict(baseline_metrics)
        self.mode = mode

    # ------------------------------------------------------------------
    def run_baseline(self):
        m = dict(self.baseline)
        m["error_count"] = 0
        m["run_type"] = "baseline"
        return m

    def run(self, policy):
        """按一条 B2 调优策略跑一次，返回调优后指标。policy 为 dict。"""
        if self.mode == "simulation":
            return self._run_simulation(policy)
        elif self.mode == "real":
            return self._run_real(policy)
        raise ValueError("未知运行模式: %s" % self.mode)

    # ------------------------------------------------------------------
    def _run_simulation(self, policy):
        gain = float(policy.get("estimated_throughput_gain", 0.0))
        p95_red = float(policy.get("estimated_p95_reduction", 0.0))
        key = "%s|%s" % (self.name, policy.get("parameter_name", ""))
        j = _stable_jitter(key, scale=0.008)

        base = self.baseline
        tuned = {
            "throughput_metric": base["throughput_metric"],
            "throughput": round(base["throughput"] * (1 + gain + j), 4),
            "avg_latency_ms": round(base["avg_latency_ms"] * (1 - p95_red * 0.9 + j), 3),
            "p95_latency_ms": round(base["p95_latency_ms"] * (1 - p95_red + j), 3),
            "p99_latency_ms": round(base["p99_latency_ms"] * (1 - p95_red * 0.8 + j), 3),
            "error_count": 0,
            "run_type": "tuned",
        }
        return tuned

    def _run_real(self, policy):
        raise NotImplementedError(
            "real 模式需要接入独立测试租户：\n"
            "  1) 通过 ALTER SYSTEM/ALTER TENANT 应用 policy['parameter_name']="
            "policy['recommended_value']\n"
            "  2) 调用 BenchmarkSQL(TPC-C) / tpch-obs(TPC-H) 跑一轮\n"
            "  3) 解析日志得到 tps/qps 与 p95/p99，并在结束后执行 rollback_sql\n"
            "现阶段共享/联调环境请使用 simulation 模式。")


def build_cases_from_baseline(baseline_perf_csv, workloads, mode="simulation"):
    """从 Wang 的 param_perf_dataset_real.csv 解析各 workload 的 baseline 指标。"""
    import pandas as pd
    df = pd.read_csv(baseline_perf_csv)

    # workload 列里的取值 -> 归一到 TPC-C / TPC-H
    def match_row(wl):
        key = {"TPC-C": "TPC-C", "TPC-H": "TPC-H"}[wl]
        sub = df[df["workload"].astype(str).str.contains(key, case=False, na=False)]
        return sub.iloc[0] if len(sub) else None

    metric_field = {"TPC-C": "tps", "TPC-H": "qps"}
    cases = {}
    for wl in workloads:
        row = match_row(wl)
        if row is None:
            continue
        cases[wl] = BenchmarkCase(
            name="%s_case" % wl,
            workload_type=wl,
            baseline_metrics={
                "throughput_metric": metric_field.get(wl, "tps"),
                "throughput": float(row["qps_or_tps"]),
                "avg_latency_ms": float(row["avg_latency_ms"]),
                "p95_latency_ms": float(row["p95_latency_ms"]),
                "p99_latency_ms": float(row["p99_latency_ms"]),
            },
            mode=mode,
        )
    return cases
