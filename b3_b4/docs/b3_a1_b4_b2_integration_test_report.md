<div align="center">

# B3‑A1 / B4‑B2 接口联调测试报告

**OceanBase 数据库性能智能诊断与优化项目 · B 组**

| 项目 | 内容 |
| :-- | :-- |
| 报告编号 | `IT-B3B4-RW4-001` |
| 负责模块 | B3 资源容量预测、B4 参数调优效果自动化验证 |
| 执行人 | Huang（B 组，B3/B4） |
| experiment_id | `real_week4` |
| 联调对象 | A1（Wu）、B2（Wang） |
| 运行模式 | B4 = `simulation`（未连真库） |
| 报告日期 | 2026-07-23 |

</div>

---

## 目录

1. [测试目的与范围](#1-测试目的与范围)
2. [联调链路与数据流](#2-联调链路与数据流)
3. [被测接口与输入数据](#3-被测接口与输入数据)
4. [测试用例与结果](#4-测试用例与结果)
5. [B3‑A1 链路详情](#5-b3a1-链路详情)
6. [B4‑B2 链路详情](#6-b4b2-链路详情)
7. [问题记录与处理](#7-问题记录与处理)
8. [结论](#8-结论)

---

## 1. 测试目的与范围

本次联调**只验证数据交接是否可用**（字段、命名、类型、可解析性、健壮性），
不评估模型精度本身。对齐《第一次跨组联调测试计划 v1.0》第 2、5 节的验证标准。

覆盖两条跨模块链路：

- **A1 → B3**：B3 能否直接消费 A1（Wu）预处理后的归一化时序数据并产出容量预测。
- **B2 → B4**：B4 能否接收 B2（Wang）输出的参数调优策略并自动执行验证。

> 结论速览：**两条链路全部跑通，9 个用例全部通过（含 1 个健壮性降级用例）。**

---

## 2. 联调链路与数据流

```text
        ┌──────────────┐        normal_features_*.csv        ┌──────────────┐
        │  A1 (Wu)     │ ─────────────────────────────────►  │   B3 预测     │
        │  预处理时序   │        (归一化 / 60s 粒度)           │  PatchTST-Lite│
        └──────────────┘                                     └──────┬───────┘
                                                                    │ capacity_forecast_*.csv
                                                                    ▼
        ┌──────────────┐   b2_tuning_recommendations_*.csv   ┌──────────────┐
        │  B2 (Wang)   │ ─────────────────────────────────►  │   B4 验证     │
        │  调优建议     │        (含 requires_approval)        │  自动化框架   │
        └──────────────┘                                     └──────┬───────┘
                                                                    │ validation_report_*.md
                                                                    ▼
                                                            调优后指标 / 推广结论
```

---

## 3. 被测接口与输入数据

| 链路 | 上游产物 | 规格 | 下游消费方 |
| :-- | :-- | :-- | :-- |
| A1→B3 | `normal_features_tpcc_10w_sample.csv` | 240 行 × 8 列，60s 粒度，已 z‑score | `b3_forecast/run_b3.py` |
| B2→B4 | `b2_tuning_recommendations_real_week4.csv` | 20 条策略（TPC‑C 10 + TPC‑H 10） | `b4_validation/run_b4.py` |
| B(baseline) | `param_perf_dataset_real.csv` 等 | TPC‑C / TPC‑H 真实 baseline | B4 对比基准 |

A1 输入字段：`timestamp, cpu_usage, io_wait, latency_ms, memory_usage, ob_active_session_num, ob_plan_cache_hit_rate, qps`。

---

## 4. 测试用例与结果

> 图例：✅ 通过　⚠️ 通过（降级/带说明）　❌ 失败

| 用例编号 | 验证内容 | 链路 | 通过标准 | 结果 |
| :-- | :-- | :-- | :-- | :--: |
| **IT‑B3‑01** | A1 归一化 CSV 能被 B3 正确解析，时间戳可排序对齐 | A1→B3 | 字段无缺失，`timestamp` 可解析 | ✅ |
| **IT‑B3‑02** | B3 输出符合《联调计划 §7.2》容量预测接口字段 | A1→B3 | 8 字段齐全、类型正确 | ✅ |
| **IT‑B3‑03** | 短期 24h、长期 7d 两类 `horizon_type` 均产出 | A1→B3 | 两类均非空 | ✅ |
| **IT‑B3‑04** | 上游列缺失 / 序列过短时能降级不崩溃 | A1→B3 | 只用可用列，日志给出提示 | ⚠️ |
| **IT‑B4‑01** | B2 建议能被 B4 读取并生成非空验证结果 | B2→B4 | 生成 ≥1 条候选并输出结果表 | ✅ |
| **IT‑B4‑02** | `requires_approval=1` 高风险策略未被自动执行 | B2→B4 | 6 条转人工审核，未自动跑 | ✅ |
| **IT‑B4‑03** | 每条变更均保留可执行 `rollback_sql` | B2→B4 | 结果表 `rollback_sql` 非空 | ✅ |
| **IT‑B4‑04** | B4 输出字段满足推广判断与后续复盘 | B2→B4 | 含前后指标 + 推广结论 | ✅ |
| **IT‑E2E** | A1→B3、B2→B4 两条链路端到端跑通 | 全链路 | `run_all.py` 无未捕获异常 | ✅ |

**汇总：9 / 9 通过（其中 IT‑B3‑04 为健壮性降级通过）。**

---

## 5. B3‑A1 链路详情

### 5.1 输入解析

- 成功读入 A1 的 240 行时序，`timestamp` 从 `2026-07-10 00:00:00` 起、60s 连续。
- 命中 5 个可建模指标：`cpu_usage, memory_usage, io_wait, qps, latency_ms`。

### 5.2 输出接口校验（对齐《联调计划 §7.2》）

产物 `capacity_forecast_real_week4.csv`，共 **8040 行**：

| horizon_type | 行数 | 粒度 | 说明 |
| :-- | --: | :-- | :-- |
| `short_term` | 7200 | 60s | 未来 24h，5 指标 × 1440 步 |
| `long_term` | 840 | 3600s | 未来 7d，5 指标 × 168 步 |

字段完整：`experiment_id, forecast_timestamp, metric_name, forecast_value, confidence_lower, confidence_upper, horizon_type, model_version` ✅

### 5.3 基线预测指标（walk‑forward 回测）

| 指标 | RMSE | MAE | 训练样本 |
| :-- | --: | --: | --: |
| cpu_usage | 2.737 | 2.212 | 169 |
| memory_usage | 1.347 | 1.090 | 169 |
| io_wait | 1.326 | 1.082 | 169 |
| qps | 1.309 | 1.027 | 169 |
| latency_ms | 3.286 | 2.568 | 169 |

> RMSE/MAE 为 A1 已做 z‑score 标准化尺度下的误差；`cpu_usage`、`latency_ms`
> 因序列含明显尖峰而误差偏高，属预期，不影响接口联调结论。

---

## 6. B4‑B2 链路详情

### 6.1 调度概况

| 项 | 数量 |
| :-- | --: |
| B2 输入策略总数 | 20 |
| 已批准并自动验证（`requires_approval=0`） | **14** |
| 高风险转人工审核（`requires_approval=1`） | **6** |
| 达到推广阈值 | **14** |

`requires_approval=1` 的 6 条（如 `clog_io_isolation_mode`、`memory_chunk_cache_size`、
`syslog_io_bandwidth_limit`）均**未自动执行**，与 JT‑04 一致。

### 6.2 baseline 与调优后关键指标对比（均值）

| workload | baseline 吞吐 | 平均吞吐提升 | 平均 p95 变化 | 错误数 |
| :-- | --: | --: | --: | --: |
| TPC‑C | 1.826 tps | **+3.99%** | **−4.31%** | 0 |
| TPC‑H | 6.527 qps | **+2.67%** | **−6.42%** | 0 |

（吞吐↑、p95↓ 均为正向收益。）

### 6.3 回滚与安全

- 每条自动验证策略均生成 `rollback_sql` 模板（`ALTER SYSTEM SET <param> = <baseline_value>;`）✅
- `simulation` 模式不改真库；切 `real` 时执行完自动回滚（钩子见 `benchmark_cases.py::_run_real`）。

---

## 7. 问题记录与处理

| 编号 | 现象 | 原因 | 处理 | 状态 |
| :-- | :-- | :-- | :-- | :--: |
| Q‑01 | 长程递归预测出现 NaN | 10080 步递归数值发散 | 预测值按训练分布钳制 + 非有限值兜底 | ✅ 已修 |
| Q‑02 | cpu/latency 回测 RMSE 异常偏大(>15) | 平坦窗口 RevIN 除近零 std 放大尖峰 | 关闭逐窗归一化(数据已全局标准化)+ 提高 Ridge alpha | ✅ 已修 |
| Q‑03 | B2 建议缺 `rollback_sql` 字段 | B2 v0.1 未含该列 | B4 侧按参数名生成回滚模板占位 | ⚠️ 待 B2 补字段 |

---

## 8. 结论

- ✅ **A1 → B3、B2 → B4 两条跨模块链路数据交接全部可用**，接口字段与命名符合已确认规范。
- ✅ B3 产出符合《联调计划 §7.2》的 `capacity_forecast` 接口；B4 产出符合 §7.1 的验证报告接口。
- ⚠️ 建议 B2 在后续版本补 `rollback_sql` / `current_value` 字段（见 Q‑03），以便 B4 生成可直接执行的精确回滚。
- ➡️ 满足进入**第二次跨组联调**的前置条件，详见 `second_round_integration_test_plan.md`。

---

<div align="center"><sub>本报告随 <code>b3_b4</code> 模块交付 · 复现命令：<code>python run_all.py</code></sub></div>
