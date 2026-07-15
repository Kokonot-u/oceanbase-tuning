# 第三周论文精读笔记：OceanBase 智能参数调优 B1/B2

负责人：Wang  
模块：B组 B1 参数影响因子分析 / B2 深度强化学习智能调优  
关联第二周真实数据：`outputs/real_week2/`、`docs/real_week2/`、`docs/real_week3/b1_b2_interface_definition_v0.1.md`

## 0. 与第二周 real_week2 数据的对齐基线

本周读论文不是单纯复述方法，而是要把论文方法落到当前 OceanBase 项目的 B1/B2 数据链路上。第二周已经形成了可复用的真实基础：

- OceanBase 环境：`5.7.25-OceanBase_CE-v4.4.2.1`，cluster 为 `obstandalone`，tenant 为 `test`，数据库为 `week2_bench_wang`。
- 参数数据：通过真实 `SHOW PARAMETERS` 导出，形成 `ob_parameters_real.tsv`，并筛出 347 个性能相关候选参数，生成 `top100_performance_params_real.csv`。
- Top5 初始候选参数：`cpu_quota_concurrency`、`memstore_limit_percentage`、`clog_io_isolation_mode`、`enable_sql_audit`、`large_query_worker_percentage`。
- workload baseline：轻量 SQL、BenchmarkSQL/TPC-C、TPC-H 22 查询均已真实执行，参数修改尚未执行，当前所有参数实验仍处于 baseline/计划阶段。

当前 baseline 可作为 B1/B2 的初始状态：轻量 SQL 平均延迟 139.228 ms、P95 178.12 ms、P99 239.711 ms、吞吐 7.17 ops/s；TPC-C 平均延迟 312.3 ms、P95 716.0 ms、P99 726.0 ms、吞吐 1.826 txn/s，tpmC=46.95；TPC-H 22 查询总耗时 3370.68 ms、平均 153.213 ms、P95 192.592 ms、P99 285.852 ms、吞吐 6.5269 q/s。

---

## 1. DB-BERT: A Database Tuning Tool that “Reads the Manual”

### 1.1 论文基本信息

- 论文：DB-BERT: A Database Tuning Tool that “Reads the Manual”
- 作者：Immanuel Trummer
- 发表：SIGMOD 2022，arXiv 2021 版本
- 核心关键词：数据库参数文档、自然语言 hint 抽取、BERT、Double DQN、NLP-enhanced database tuning
- 主要对象：PostgreSQL、MySQL；实验使用 TPC-C、TPC-H 等 benchmark，优化吞吐或执行时间。

### 1.2 研究问题

传统自动调优方法通常假设专家已经给出待调参数和合理范围，但真实 DBMS 参数很多，文档和调优博客里存在大量“半结构化经验”：例如 buffer 设为内存的 25%、日志文件大小增大会影响写入、某参数对 OLAP 更敏感。DB-BERT 要解决的问题是：如何让调优系统自动阅读数据库手册、博客、调优指南，从自然语言中提取参数名、推荐值、相对比例和隐式参数引用，再把这些 hint 作为强化学习调参的先验。

这对 OceanBase 很直接：我们第二周的 Top100 主要来自参数名关键词和 `SHOW PARAMETERS` 元信息，已经能筛出 `log_disk_utilization_threshold`、`query_memory_limit_percentage`、`io_scheduler_thread_count` 等参数，但还缺少“为什么调、怎么调、在什么 workload 下调”的文档语义。DB-BERT 提供的正是把 OceanBase 官方文档、参数说明、运维手册变成结构化调参 hint 的方法。

### 1.3 核心方法

DB-BERT 将自然语言调优信息转成形式化 hint：`<文本片段, 参数 p, 值 v>`，再翻译成公式 `p = f(v, S)`。其中 `S` 是系统属性，例如 RAM、CPU cores、disk size。它支持两类推荐：绝对值，例如 `random_page_cost = 1`；相对值，例如 buffer pool size = 0.8 * RAM。

论文中的关键步骤包括：

1. 切分文本片段，从手册和网页中识别是否包含 tuning hint。
2. 识别参数名和值，处理显式参数和隐式参数。例如文本只说 “buffer pool size” 而没有写完整参数名时，需要映射到具体 DBMS knob。
3. 将自然语言推荐翻译为公式，允许乘以系统属性和倍率。
4. 对同一参数的多个冲突 hint 赋权重，聚合成候选配置。
5. 用强化学习决定 hint 的翻译、偏移倍率和权重，并通过 benchmark 反馈更新策略。

DB-BERT 使用 Double DQN，把 hint 处理过程建模为离散 MDP。奖励来自 DBMS 是否接受该配置，以及 benchmark 性能是否改善；无效配置被惩罚，性能提升被奖励。

### 1.4 系统架构

系统输入包括 benchmark、硬件属性、文本集合和 DBMS 参数集合。流程是：

- Extract Hints：从文本中抽取候选参数和值。
- Prioritize Hints：优先处理高频出现的参数，同时避免同一参数连续占满 batch。
- Translate / Adapt / Weigh：把 hint 翻译成参数值，决定是否乘以偏移倍率，并为冲突 hint 赋权。
- Aggregate Hints：聚合成一组候选配置。
- Evaluate Configurations：在 DBMS 上执行 benchmark。
- Learn from Experiences：用 reward 更新 RL 策略。

映射到本项目，可以把 `ob_parameters_real.tsv` 和 Top100 参数作为参数全集 `P`，把 OceanBase 文档、参数说明、第二周 Top5 说明作为文本集合 `T`，把轻量 SQL、TPC-C、TPC-H baseline 作为 benchmark `b`。初期不用完整训练 BERT，也可以先用规则/LLM 抽取结构化 hint，形成 `b1_parameter_candidates_exp001.csv` 的 evidence 字段和 `b2_param_search_space_exp001.yaml` 的初始范围。

### 1.5 实验设置

论文使用多个数据库系统和 benchmark 验证 DB-BERT：数据库包括 PostgreSQL 和 MySQL，负载包括 TPC-C、TPC-H，目标包括吞吐和运行时间。输入文本来自数百篇数据库调优文档。对比方法包括不使用文本的调优方法和较简单的文本抽取方法。论文结论是：利用文本 hint 后，搜索空间更聚焦，DB-BERT 能更快找到高质量配置。

对我们当前 OceanBase 实验，最接近的复现实验不是直接训练 DB-BERT，而是做一个轻量版：

- 文档输入：OceanBase 参数手册、SQL 调优文档、内存/日志/租户资源相关文档。
- 参数全集：第二周 347 个候选参数，重点 Top100。
- benchmark：TPC-C 用 `BenchmarkSQL_TPC-C` baseline，TPC-H 用 `TPC-H-22-lightweight-real` baseline。
- 输出：对每个参数生成 `hint_value`、`hint_source`、`hint_confidence`、`applicable_workload`、`risk_level`。

### 1.6 优点

DB-BERT 的优点是把人工 DBA 的“读文档经验”前置到调优系统中，避免纯 RL 或贝叶斯优化在巨大参数空间里盲目试错。它还能处理相对值和隐式引用，这对 OceanBase 很重要，因为很多参数取值不是孤立数字，而是依赖租户内存、CPU 配额、日志盘容量和 workload 类型。

对本项目而言，它能补足第二周 Top100 的证据质量。当前 Top100 多数依据是参数名命中关键词，例如 `io`、`log`、`memory`、`thread`，这适合初筛，但不足以确定调参方向。DB-BERT 思路可以把“命中关键词”升级为“文档 hint + workload 条件 + 推荐范围”。

### 1.7 局限性

DB-BERT 依赖文档质量。若 OceanBase 文档只描述参数含义，不给推荐值或 workload 条件，抽取结果会稀疏。它的强化学习仍然需要真实 benchmark 反馈，而我们当前共享 test 租户尚未允许改参数，只能先做离线 hint 构建和仿真。另一个限制是 DB-BERT 原始实现偏离散决策，面对 OceanBase 中大量连续/范围型参数时，需要和 CDBTune 这类连续控制方法结合。

### 1.8 对 OceanBase B1/B2 模块的借鉴

对 B1：

- 为每个候选参数增加文档语义特征：`manual_mentions`、`hint_type`、`recommended_range`、`relative_to_resource`、`workload_condition`。
- 将 Top100 的关键词分数与文档 hint 分数融合，形成更可信的参数影响先验。
- 对 Top5 参数给出语义解释：例如 `cpu_quota_concurrency` 与并发调度相关，`memstore_limit_percentage` 与内存水位/冻结相关，`clog_io_isolation_mode` 与日志 IO 隔离相关。

对 B2：

- 用文档 hint 缩小动作空间，避免 RL 一开始就尝试高风险参数和值。
- 将 hint 作为 warm start：例如 TPC-C 更重视写入和日志路径，可优先探索 `clog_io_isolation_mode`、日志盘阈值、CPU 并发参数；TPC-H 更重视 SQL 执行和内存，可优先探索 `query_memory_limit_percentage`、`large_query_worker_percentage`。
- 在 reward 中加入“DBMS 拒绝配置/参数不可修改/高风险参数”的惩罚，匹配当前共享租户的安全限制。

### 1.9 可以写进 PPT 的总结句

DB-BERT 的价值不是让模型替代 benchmark，而是把数据库手册中的调参经验转成可计算的 hint，作为 OceanBase B1 参数筛选和 B2 强化学习搜索空间的先验。

---

## 2. Automatic Database Management System Tuning Through Large-scale Machine Learning / OtterTune

### 2.1 论文基本信息

- 论文：Automatic Database Management System Tuning Through Large-scale Machine Learning
- 系统：OtterTune
- 作者：Dana Van Aken、Andrew Pavlo、Geoffrey J. Gordon、Bohan Zhang
- 发表：SIGMOD 2017
- 核心关键词：workload characterization、knob identification、Lasso、Factor Analysis、K-means、Gaussian Process、历史调优数据复用。
- 主要对象：MySQL、PostgreSQL、Vector；目标是降低延迟或提升吞吐。

### 2.2 研究问题

DBMS 参数调优难在三点：参数多、参数之间存在依赖、不同 workload 的最优配置不可直接复用。OtterTune 的问题定义是：如何利用过去调优会话的数据，为新的数据库实例识别关键参数、匹配相似 workload，并推荐下一组配置。

这正好支撑 B1。我们第二周已经有 baseline 与候选参数，但还没有真正的“参数影响因子分析”。OtterTune 给出了一条清晰路线：先用 runtime metrics 表征 workload，再用 Lasso 等方法识别最影响性能的 knob，而不是只靠参数名或人工直觉。

### 2.3 核心方法

OtterTune 的机器学习流水线分三部分：

1. Workload Characterization：收集 DBMS 内部运行指标，用 Factor Analysis 降维，再用 K-means 聚类选出最能区分 workload 的指标。它不要求人工解释每个指标含义，而是从统计相关性中选择代表性 metrics。
2. Knob Identification：用 Lasso 回归识别最重要的参数。Lasso 的 L1 正则会把不重要参数的权重压到 0，保留对目标指标最有解释力的参数。为捕捉参数交互，OtterTune 还加入多项式特征，例如 buffer pool 与 log file size 的乘积。
3. Configuration Recommendation：先把目标 workload 映射到历史 repository 中相似 workload，再用 Gaussian Process 推荐下一组参数配置，并通过新观测持续更新。

### 2.4 系统架构

OtterTune 分为 client-side controller 和 tuning manager：

- Controller 连接目标 DBMS，采集硬件信息、当前参数、外部性能指标和内部运行指标，并负责安装新配置。
- Tuning Manager 保存历史 tuning repository，训练 workload characterization、knob identification 和推荐模型。
- Repository 不保存业务数据，只保存参数配置、性能结果和 DBMS runtime metrics。

对本项目，可以按 B1/B2 接口拆分：

- `parameter_config_{experiment_id}.csv` 对应 OtterTune 的 knob configuration。
- `parameter_performance_{experiment_id}.csv` 对应 observation period 后的性能结果。
- `b1_feature_matrix_exp001.csv` 对应 workload metrics + 参数值 + 性能目标。
- `b1_feature_importance_exp001.csv` 对应 Lasso/随机森林等方法输出的重要性排序。

### 2.5 实验设置

OtterTune 在 MySQL、PostgreSQL、Vector 上测试，使用 OLTP/OLAP workload，评价目标包括延迟和吞吐。论文报告 OtterTune 可在较短时间内生成接近或超过专家配置的结果，并且相比从零开始的 GP 搜索，历史经验复用能显著减少试错成本。

在 OceanBase 当前阶段，实验设置应先采用“小而真实”的方式：

- 以第二周三个 baseline 作为初始 observation：轻量 SQL、TPC-C、TPC-H。
- 在允许改参后，围绕 Top5 或 Top10 做低风险实验矩阵，而不是直接对 Top100 全量搜索。
- 每次实验记录参数值、workload 类型、吞吐、平均延迟、P95/P99、错误数，后续补充 CPU、内存、磁盘 IO、等待事件、活跃会话等 A 组系统表数据。

### 2.6 优点

OtterTune 对 B1 最有价值的是“影响因子分析方法论”非常明确。它不是简单输出一个调参建议，而是先回答两个问题：哪些 workload 指标最能描述当前负载，哪些参数对目标性能最重要。这个顺序适合我们当前项目，因为 B1 的输出要能解释 B2 为什么只调某些参数。

它还强调历史数据复用。第二周虽然只有 baseline，没有参数变更结果，但这仍然可以作为 repository 的第一批记录。后续每次参数实验都可以追加到同一个格式中，逐步从规则筛选过渡到数据驱动筛选。

### 2.7 局限性

OtterTune 依赖足够多的历史 tuning session。我们现在只有 baseline 和参数候选表，真实参数变更尚未执行，因此短期内无法训练出稳定的 Lasso/GP 模型。另一个问题是 OtterTune 假设可安装新配置并反复观测，而当前共享 test 租户限制了直接改参。最后，Lasso 更偏线性解释，虽然多项式特征能补充交互，但对 OceanBase 中复杂的租户资源隔离、日志路径、SQL 执行器并发关系，可能需要随机森林、SHAP 或分 workload 建模辅助解释。

### 2.8 对 OceanBase B1/B2 模块的借鉴

对 B1：

- 将当前 Top100 从“规则候选表”升级为“候选表 + 重要性表”。初始重要性可以由关键词分数、风险、可修改性、文档 hint、workload 相关性共同计算；后续有参数实验后引入 Lasso/随机森林。
- 建议优先构建三类特征：参数特征、workload 特征、性能特征。参数特征来自 `top100_performance_params_real.csv` 的 category、scope、edit_level、risk_level、value_range；workload 特征来自轻量 SQL/TPC-C/TPC-H 类型和运行指标；性能特征来自 avg/P95/P99 latency、qps/tps、error_count。
- 对 Top5 可先建立假设：`cpu_quota_concurrency` 和 `large_query_worker_percentage` 更可能影响 TPC-C 并发排队与 TPC-H 大查询执行；`clog_io_isolation_mode` 更可能影响 TPC-C 写事务日志路径；`memstore_limit_percentage` 更可能影响写入、冻结和内存水位；`enable_sql_audit` 可能带来观测能力与额外开销的权衡。

对 B2：

- B2 不应直接接收 Top100 全量搜索空间，而应接收 B1 筛出的 TopK 参数、范围、风险和重要性。
- 对历史调优数据复用，可把每次实验保存为 replay/experience：`state = workload metrics + current knobs`，`action = changed knobs`，`reward = performance delta`。
- 在样本少时，OtterTune 风格的 GP/BO 可以作为 B2 的冷启动 baseline，与 CDBTune 的 DDPG 进行对比。

### 2.9 可以写进 PPT 的总结句

OtterTune 对本项目的核心启发是：B1 先用 workload characterization 和 knob identification 解释“哪些参数值得调”，B2 再基于这些高价值参数做智能搜索。

---

## 3. An End-to-End Automatic Cloud Database Tuning System Using Deep Reinforcement Learning / CDBTune

### 3.1 论文基本信息

- 论文：An End-to-End Automatic Cloud Database Tuning System Using Deep Reinforcement Learning
- 系统：CDBTune
- 作者：J. Zhang、Y. Liu、K. Zhou、G. Li、Z. Xiao 等
- 发表：ICDM 2019
- 核心关键词：Deep Reinforcement Learning、DDPG、连续参数空间、state/action/reward、experience replay、cloud database tuning。
- 优化目标：吞吐和延迟。

### 3.2 研究问题

数据库参数空间往往高维、连续、相互依赖。传统方法要么依赖专家预选参数，要么在高维空间里搜索效率低。CDBTune 的问题是：如何把云数据库调参建模为强化学习控制问题，让 agent 根据数据库运行状态直接输出一组参数配置，并通过吞吐/延迟反馈持续学习。

这正好对应 B2。OceanBase 的很多关键参数是连续或准连续范围，例如 `query_memory_limit_percentage` 为 `[0,100]`，`log_disk_utilization_threshold` 为 `[10,100)`，`io_scheduler_thread_count` 为 `[1,16]`。如果把这些参数离散成很多档，动作空间会迅速膨胀；DDPG 这类连续控制算法更适合输出向量化动作。

### 3.3 核心方法

CDBTune 把调参建模为 MDP：

- Agent：深度强化学习模型。
- Environment：待调优的 DBMS 实例。
- State：DBMS 内部运行指标向量，例如 buffer、IO、lock、transaction、thread 等 runtime metrics。
- Action：一组 knob configuration，也就是参数配置向量。
- Reward：执行 workload 后的性能收益，综合吞吐提升和延迟下降。
- Policy：从状态到动作的映射。

论文采用 DDPG，即 actor-critic 框架：

- Actor 网络根据当前 state 输出连续 action。
- Critic 网络评估某个 state-action 的价值，指导 actor 更新。
- Replay buffer 存储 `(state, action, reward, next_state)`，通过随机采样提高训练稳定性和样本利用率。
- 通过探索噪声让 agent 不只利用当前最优动作，也尝试邻近配置。

### 3.4 系统架构

CDBTune 的闭环可以抽象为：

1. 采集当前 DBMS metrics，形成 state。
2. Agent 输出参数配置 action。
3. Controller 将配置应用到 DBMS。
4. 运行固定 workload。
5. 采集吞吐、延迟和下一时刻 metrics。
6. 计算 reward。
7. 写入 replay buffer 并更新 actor/critic。

映射到 OceanBase：

- Environment：OceanBase test 租户或后续独立压测租户。
- State：第二周 baseline 的性能指标 + A 组系统表数据，如 CPU 使用率、内存使用率、磁盘 IO、活跃会话、等待事件、SQL audit 聚合指标。
- Action：B1 输出的 TopK 参数配置向量。初期建议 Top5，不直接使用 Top100。
- Reward：基于 TPC-C/TPC-H 的吞吐和延迟变化，同时加入 error_count 和安全惩罚。
- Controller：可复用 `src/b2_tuning/env.py`、`src/b4_validation/param_applier.py`、`src/b4_validation/experiment_tracker.py` 的接口思路。

### 3.5 实验设置

CDBTune 面向云数据库，通常通过一组待调参数、固定 workload 和 benchmark 反馈训练模型。它强调真实 DBMS 作为环境，而不是只在离线模拟器中优化。评价时关注吞吐提升、延迟下降和调优迭代效率。

本项目第三周适合给出 B2 设计，不宜马上大规模在线训练：

- 初始 state 使用第二周 baseline：TPC-C 平均延迟 312.3 ms、P95 716.0 ms、P99 726.0 ms、吞吐 1.826 txn/s；TPC-H 平均 153.213 ms、P95 192.592 ms、P99 285.852 ms、吞吐 6.5269 q/s。
- 初始 action space 使用 Top5 参数，并标注可修改性和风险；不可确认参数先只进入推荐，不自动执行。
- reward 先定义为离线可计算公式，等允许改参后再接入真实执行结果。

### 3.6 优点

CDBTune 的最大优点是适合连续动作空间。数据库调参不是简单选择 A/B/C，很多参数是百分比、线程数、内存大小或阈值。DDPG 可以直接输出连续向量，再经过边界裁剪、类型转换和安全规则变成实际参数值。

它还天然适合闭环优化。每次实验都能成为下一轮训练样本，这与我们 B2 接口中的 `parameter_config`、`parameter_performance`、`b2_tuning_recommendations` 是一致的。

### 3.7 局限性

CDBTune 的短板是样本成本高。每个 action 都要真实部署参数并运行 workload，数据库实验比游戏或仿真环境昂贵得多。另一个问题是安全性：DDPG 探索噪声可能产生危险配置，因此不能直接在共享租户上自动执行。它也依赖稳定 workload，如果 workload 从 TPC-C 切到 TPC-H，原策略可能不再适用。

对 OceanBase 来说，还要处理参数生效方式差异：有些参数动态生效，有些静态生效；有些是 cluster scope，有些是 tenant scope；有些当前 `can_modify=UNKNOWN`。这些约束必须进入 action mask 或安全校验层。

### 3.8 对 OceanBase B1/B2 模块的借鉴

对 B1：

- B1 输出不能只给参数名，还要给 B2 可用的动作边界：最小值、最大值、类型、步长、scope、edit_level、risk_level。
- 对连续参数保留原始范围，对枚举/布尔参数单独编码。例如 `clog_io_isolation_mode` 是枚举，`enable_sql_audit` 是布尔，`cpu_quota_concurrency` 和 `large_query_worker_percentage` 可按数值动作处理。
- B1 需要提供 workload-specific TopK：TPC-C 和 TPC-H 的敏感参数不应完全相同。

对 B2：

- State space 建议包含三层：workload 类型 one-hot、性能指标、系统运行指标。当前已有性能指标，A 组数据到位后补齐 CPU/memory/io/wait event。
- Action space 初期用 Top5：`cpu_quota_concurrency`、`memstore_limit_percentage`、`clog_io_isolation_mode`、`enable_sql_audit`、`large_query_worker_percentage`。执行前必须经过 action sanitizer：范围裁剪、类型转换、只允许低/中风险、生成 rollback。
- Reward function 可定义为：

```text
reward = 0.45 * throughput_gain
       + 0.35 * latency_reduction_p95
       + 0.10 * latency_reduction_p99
       - 0.10 * error_penalty
       - safety_penalty
```

其中 TPC-C 更偏吞吐和事务延迟，TPC-H 更偏总执行时间和 P95/P99。所有指标都与 baseline 比较，例如 TPC-C baseline `tps=1.826`、`p95=716.0 ms`，TPC-H baseline `qps=6.5269`、`p95=192.592 ms`。

### 3.9 可以写进 PPT 的总结句

CDBTune 把数据库调参变成“状态-动作-奖励”的连续控制问题，适合作为 OceanBase B2 智能调优模块的核心建模框架，但必须由 B1 的参数筛选和安全约束先缩小动作空间。

---

## 4. 三篇论文对比表

| 维度 | DB-BERT | OtterTune | CDBTune | 对 OceanBase B1/B2 的作用 |
| -- | -- | -- | -- | -- |
| 核心思想 | 读取手册和调优文档，抽取参数 hint，再结合 RL 评估 | 复用历史调优数据，做 workload 表征、参数重要性分析和配置推荐 | 用深度强化学习直接输出连续参数配置 | DB-BERT 给文档先验，OtterTune 支撑 B1 分析，CDBTune 支撑 B2 调优 |
| 输入数据 | 文本集合、benchmark、硬件属性、参数集合 | 历史参数配置、性能结果、DBMS metrics、目标 workload | DBMS runtime metrics、当前参数、benchmark 反馈 | 当前已有 Top100、Top5、TPC-C/TPC-H baseline；还需补 OceanBase 文档和 A 组系统指标 |
| 参数筛选 | 从自然语言中发现参数和值 | Lasso/多项式特征识别重要 knob | 依赖预选动作空间，通常不负责解释筛参 | B1 可融合文档 hint + Lasso/统计重要性，给 B2 输出 TopK |
| workload 建模 | benchmark 作为性能反馈对象，文本 hint 可含 workload 条件 | Factor Analysis + K-means 选择代表性 runtime metrics，映射相似 workload | state 中包含 DBMS 内部指标，隐式表示 workload | TPC-C/TPC-H 应分开建模；轻量 SQL 只适合连通性和小样本验证 |
| 推荐算法 | Double DQN，离散决策 hint 翻译/偏移/权重 | Gaussian Process 推荐下一组配置 | DDPG actor-critic，适合连续动作 | B2 可用 DDPG 主线，GP/规则作为冷启动 baseline |
| 适合参数类型 | 文档中可描述的整数、数值、布尔参数 | 可建模的数值/类别参数，需足够历史样本 | 连续参数和高维配置向量 | OceanBase 参数需按连续、枚举、布尔、静态/动态分别编码 |
| 优点 | 降低盲目搜索，解释性强，可利用官方文档 | B1 方法最完整，可解释参数重要性和 workload 相似性 | B2 建模最直接，能处理连续搜索空间 | 三者组合可形成“文档先验 -> 影响因子 -> RL 调优”链路 |
| 局限 | 依赖文档质量，仍需 benchmark，原生更偏离散决策 | 需要大量历史实验；样本少时模型不稳 | 样本成本高，有安全风险，对 workload 漂移敏感 | 当前共享 test 租户不能直接自动改参，需先做离线设计和安全执行窗口 |
| 与 real_week2 结合点 | 用 Top100 + OceanBase 文档生成 hint/range/evidence | 用 baseline 和后续参数实验构建 feature matrix/importances | 用 Top5 和 baseline 定义 state/action/reward | 第三周交付可先完成接口、笔记、搜索空间和 reward 设计 |

## 5. 本周可落地结论

1. B1 不应停留在 Top100 参数列表，而要输出“参数为什么重要”的证据链：参数元信息、文档 hint、workload 相关性、历史实验重要性。
2. B2 不应直接对 OceanBase 全参数空间做 RL，而应接收 B1 筛出的 TopK 安全动作空间，先围绕第二周 Top5 建模。
3. 当前 baseline 已经足够定义 reward 的参照点：TPC-C 以吞吐、P95/P99 延迟为主；TPC-H 以总耗时、平均延迟和尾延迟为主。
4. 最适合本项目的融合路线是：DB-BERT 提供文档语义先验，OtterTune 提供 B1 参数影响因子分析框架，CDBTune 提供 B2 连续动作强化学习框架。

## 参考资料

- Immanuel Trummer, DB-BERT: A Database Tuning Tool that “Reads the Manual”, SIGMOD 2022 / arXiv:2112.10925.
- Dana Van Aken, Andrew Pavlo, Geoffrey J. Gordon, Bohan Zhang, Automatic Database Management System Tuning Through Large-scale Machine Learning, SIGMOD 2017.
- J. Zhang et al., An End-to-End Automatic Cloud Database Tuning System Using Deep Reinforcement Learning, ICDM 2019.
- Limeng Zhang, M. Ali Babar, Automatic Configuration Tuning on Cloud Database: A Survey, arXiv:2404.06043.
