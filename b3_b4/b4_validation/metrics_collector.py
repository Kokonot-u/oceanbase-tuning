# -*- coding: utf-8 -*-
"""
B4 模块二：性能指标自动采集
============================
把 baseline 与 tuned 两次跑批的指标标准化，并计算调优前后的对比 delta。
真实模式下这里还可以扩展成从 OCP/系统表拉 CPU/内存/IO 等资源指标。
"""


def pct(new, old):
    if old in (None, 0):
        return 0.0
    return round((new - old) / abs(old) * 100.0, 3)


def compare(baseline, tuned):
    """返回调优前后对比 dict（吞吐提升为正向收益，延迟下降为正向收益）。"""
    thr_metric = baseline["throughput_metric"]
    thr_gain_pct = pct(tuned["throughput"], baseline["throughput"])
    p95_change_pct = pct(tuned["p95_latency_ms"], baseline["p95_latency_ms"])
    p99_change_pct = pct(tuned["p99_latency_ms"], baseline["p99_latency_ms"])
    avg_change_pct = pct(tuned["avg_latency_ms"], baseline["avg_latency_ms"])
    return {
        "throughput_metric": thr_metric,
        "baseline_throughput": baseline["throughput"],
        "tuned_throughput": tuned["throughput"],
        "throughput_gain_pct": thr_gain_pct,          # 越高越好
        "baseline_p95_ms": baseline["p95_latency_ms"],
        "tuned_p95_ms": tuned["p95_latency_ms"],
        "p95_change_pct": p95_change_pct,              # 负数=下降=好
        "baseline_p99_ms": baseline["p99_latency_ms"],
        "tuned_p99_ms": tuned["p99_latency_ms"],
        "p99_change_pct": p99_change_pct,
        "baseline_avg_ms": baseline["avg_latency_ms"],
        "tuned_avg_ms": tuned["avg_latency_ms"],
        "avg_change_pct": avg_change_pct,
        "tuned_error_count": tuned.get("error_count", 0),
    }
