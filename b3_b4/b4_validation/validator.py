# -*- coding: utf-8 -*-
"""
B4 模块三：自动化测试调度 + 调优前后效果对比报告
==================================================
调度逻辑：
  1) 读取 Wang(B2) 的调优建议 b2_tuning_recommendations_*.csv
  2) 按 workload 分组；requires_approval==1 的高风险策略不自动执行（对齐
     联调测试计划 JT-04），只登记为待人工审核
  3) 对每个 workload 先跑一次 baseline，再对每条“已批准”策略跑一次 tuned
  4) 采集指标 -> 对比 -> 按阈值判定是否建议推广
  5) 生成 validation_report_{experiment_id}.md（对齐 §7.1）与
     b4_validation_results_{experiment_id}.csv
"""

import os
import pandas as pd

from b4_validation.benchmark_cases import build_cases_from_baseline
from b4_validation import metrics_collector as mc


def _rollback_sql(param_name):
    return "ALTER SYSTEM SET %s = <baseline_value>;  -- 回滚到 baseline" % param_name


def run_validation(cfg, root):
    exp = cfg["experiment_id"]
    operator = cfg.get("operator", "Huang")
    b4 = cfg["b4"]
    out_dir = os.path.join(root, "outputs")
    fig_dir = os.path.join(out_dir, "figures")
    os.makedirs(fig_dir, exist_ok=True)

    rec_path = os.path.join(root, b4["recommendations_csv"])
    base_path = os.path.join(root, b4["baseline_perf_csv"])
    recs = pd.read_csv(rec_path)

    cases = build_cases_from_baseline(base_path, b4["workloads"], mode=b4["mode"])

    min_reward = float(b4.get("promote_min_reward", 0.0))
    min_gain = float(b4.get("promote_min_throughput_gain", 0.02))

    results = []
    executed = 0
    skipped = 0
    for _, r in recs.iterrows():
        wl = str(r["workload_type"])
        if wl not in cases:
            continue
        case = cases[wl]
        policy = r.to_dict()
        requires_approval = int(r.get("requires_approval", 0))
        param = r["parameter_name"]

        base_m = case.run_baseline()

        if requires_approval == 1:
            # 高风险：不自动执行，仅登记为待人工审核（JT-04）
            skipped += 1
            results.append({
                "experiment_id": exp, "workload_type": wl,
                "policy_id": r.get("policy_id", ""), "parameter_name": param,
                "recommended_value": r.get("recommended_value", ""),
                "status": "pending_manual_approval",
                "executed": 0, "requires_approval": 1,
                "throughput_metric": base_m["throughput_metric"],
                "baseline_throughput": base_m["throughput"],
                "tuned_throughput": "", "throughput_gain_pct": "",
                "baseline_p95_ms": base_m["p95_latency_ms"], "tuned_p95_ms": "",
                "p95_change_pct": "", "tuned_error_count": "",
                "estimated_reward": r.get("estimated_reward", ""),
                "promote": "no",
                "rollback_sql": _rollback_sql(param),
                "note": "requires_approval=1，高风险，未自动执行，转人工审核",
            })
            continue

        tuned_m = case.run(policy)
        cmp = mc.compare(base_m, tuned_m)
        executed += 1

        reward = float(r.get("estimated_reward", 0.0))
        promote = (
            cmp["throughput_gain_pct"] >= min_gain * 100.0
            and cmp["p95_change_pct"] <= 0.0
            and cmp["tuned_error_count"] == 0
            and reward >= min_reward
        )
        results.append({
            "experiment_id": exp, "workload_type": wl,
            "policy_id": r.get("policy_id", ""), "parameter_name": param,
            "recommended_value": r.get("recommended_value", ""),
            "status": "validated",
            "executed": 1, "requires_approval": 0,
            "throughput_metric": cmp["throughput_metric"],
            "baseline_throughput": cmp["baseline_throughput"],
            "tuned_throughput": cmp["tuned_throughput"],
            "throughput_gain_pct": cmp["throughput_gain_pct"],
            "baseline_p95_ms": cmp["baseline_p95_ms"],
            "tuned_p95_ms": cmp["tuned_p95_ms"],
            "p95_change_pct": cmp["p95_change_pct"],
            "tuned_error_count": cmp["tuned_error_count"],
            "estimated_reward": reward,
            "promote": "yes" if promote else "no",
            "rollback_sql": _rollback_sql(param),
            "note": "自动化验证通过" if promote else "验证完成但未达推广阈值",
        })

    res_df = pd.DataFrame(results)
    res_path = os.path.join(out_dir, "b4_validation_results_%s.csv" % exp)
    res_df.to_csv(res_path, index=False, encoding="utf-8-sig")

    _plot_before_after(res_df, fig_dir)
    report = _build_report(exp, operator, b4, cases, res_df, executed, skipped)
    rep_path = os.path.join(out_dir, "validation_report_%s.md" % exp)
    with open(rep_path, "w", encoding="utf-8") as f:
        f.write(report)

    return res_df, res_path, rep_path, executed, skipped


def _plot_before_after(res_df, fig_dir):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    d = res_df[res_df["executed"] == 1].copy()
    if d.empty:
        return
    for wl, g in d.groupby("workload_type"):
        g = g.head(8)
        labels = [str(p)[:14] for p in g["parameter_name"]]
        x = range(len(g))
        plt.figure(figsize=(10, 3.5))
        plt.bar([i - 0.2 for i in x], g["baseline_throughput"], width=0.4,
                label="baseline", color="#999999")
        plt.bar([i + 0.2 for i in x], g["tuned_throughput"], width=0.4,
                label="tuned", color="#3366cc")
        plt.xticks(list(x), labels, rotation=30, ha="right", fontsize=7)
        plt.ylabel(g.iloc[0]["throughput_metric"])
        plt.title("B4 before/after throughput - %s" % wl)
        plt.legend(fontsize=8)
        plt.tight_layout()
        plt.savefig(os.path.join(fig_dir, "b4_before_after_%s.png" % wl), dpi=110)
        plt.close()


def _build_report(exp, operator, b4, cases, res_df, executed, skipped):
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    L = []
    L.append("# B4 参数调优效果自动化验证报告\n")
    L.append("- experiment_id: `%s`" % exp)
    L.append("- 执行人: %s" % operator)
    L.append("- 执行时间: %s" % now)
    L.append("- 运行模式: `%s`（simulation=基于 B2 预期收益+真实 baseline 推算；"
             "real=连独立测试租户实跑）" % b4["mode"])
    L.append("- 输入: B2 调优建议 `%s`，baseline 性能 `%s`\n"
             % (b4["recommendations_csv"], b4["baseline_perf_csv"]))

    L.append("## 1. baseline 基准")
    L.append("| workload | 吞吐指标 | baseline 吞吐 | p95(ms) | p99(ms) | avg(ms) |")
    L.append("| -- | -- | -- | -- | -- | -- |")
    for wl, case in cases.items():
        b = case.baseline
        L.append("| %s | %s | %.4f | %.1f | %.1f | %.1f |" %
                 (wl, b["throughput_metric"], b["throughput"],
                  b["p95_latency_ms"], b["p99_latency_ms"], b["avg_latency_ms"]))
    L.append("")

    L.append("## 2. 调优参数与取值（调度概况）")
    L.append("- 已批准并自动验证: **%d** 条；requires_approval=1 转人工审核: **%d** 条\n"
             % (executed, skipped))

    done = res_df[res_df["executed"] == 1]
    if not done.empty:
        L.append("## 3. baseline 与调优后关键指标对比")
        L.append("| workload | 参数 | 建议值 | 吞吐提升% | p95变化% | 错误 | 推广 |")
        L.append("| -- | -- | -- | -- | -- | -- | -- |")
        for _, r in done.iterrows():
            L.append("| %s | %s | %s | %+.2f | %+.2f | %s | %s |" %
                     (r["workload_type"], r["parameter_name"],
                      r["recommended_value"], r["throughput_gain_pct"],
                      r["p95_change_pct"], r["tuned_error_count"],
                      "✅" if r["promote"] == "yes" else "—"))
        L.append("")

    pend = res_df[res_df["executed"] == 0]
    if not pend.empty:
        L.append("## 4. 待人工审核（未自动执行）")
        L.append("| workload | 参数 | 建议值 | 说明 |")
        L.append("| -- | -- | -- | -- |")
        for _, r in pend.iterrows():
            L.append("| %s | %s | %s | %s |" %
                     (r["workload_type"], r["parameter_name"],
                      r["recommended_value"], r["note"]))
        L.append("")

    promoted = res_df[res_df["promote"] == "yes"]
    L.append("## 5. 是否建议在生产环境推广的结论")
    if len(promoted):
        names = ", ".join("%s(%s)" % (r["parameter_name"], r["workload_type"])
                          for _, r in promoted.iterrows())
        L.append("建议优先在生产灰度验证以下 **%d** 条通过自动化验证的参数：\n\n> %s\n"
                 % (len(promoted), names))
    else:
        L.append("本轮没有参数达到推广阈值，建议维持 baseline 并继续调参。\n")
    L.append("> 所有变更均附带 `rollback_sql`，推广前需在独立测试租户复跑确认，"
             "并保留回滚路径。\n")

    L.append("## 6. 复现")
    L.append("```\npython -m b4_validation.run_b4\n```\n")
    return "\n".join(L)
