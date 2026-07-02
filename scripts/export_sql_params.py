#!/usr/bin/env python3
"""
OceanBase v4.5 SQL执行参数机制补充
基于源码 src/sql/optimizer/, src/sql/engine/, src/sql/plan_cache/ 等分析
"""

SQL_PARAMS_MECHANISM = {
    "enable_sql_audit": {
        "code_files": ["src/sql/ob_sql_utils.cpp", "src/sql/ob_sql.cpp", "src/sql/engine/ob_operator.cpp", "src/sql/engine/px/ob_px_task_process.cpp", "src/sql/session/ob_basic_session_info.cpp"],
        "mechanism": (
            "ob_sql_utils.cpp:5009，SQL审计总开关，需同时满足GCONF.enable_sql_audit和会话级ob_enable_sql_audit。"
            "handle_audit_record()中，双开关均开时才将ObAuditRecordData写入gv$ob_sql_audit。"
            "ob_operator.cpp:1136，关闭时跳过实时监控节点注册(ObPlanMonitorNodeList)。"
            "ob_operator.cpp:1273，关闭时跳过算子监控节点提交(sql_plan_monitor)。"
            "ob_px_task_process.cpp:187，关闭时跳过PX执行审计记录。"
            "关闭可减少开销，但失去性能诊断能力。"
        )
    },
    "trace_log_slow_query_watermark": {
        "code_files": ["src/sql/ob_sql_utils.cpp"],
        "mechanism": (
            "ob_sql_utils.cpp中，慢查询判定阈值。执行时间超过此值的查询被记录到慢日志和SQL审计。"
            "这是性能监控的基础参数——所有慢查询分析都依赖此阈值筛选。"
            "默认1s，OLTP场景建议降低到100ms-500ms以捕获更多慢查询；"
            "OLAP场景建议2-5s避免大量记录。调低会增加审计表写入量。"
        )
    },
    "plan_cache_evict_interval": {
        "code_files": ["src/sql/plan_cache/ob_plan_cache.cpp"],
        "mechanism": (
            "ob_plan_cache.cpp:412，计划缓存淘汰任务的调度间隔："
            "TG_SCHEDULE(tg_id_, evict_task_, GCONF.plan_cache_evict_interval, true)。"
            "每隔此时间触发一次计划缓存淘汰，清理过期和低效的执行计划。"
            "值越小淘汰越频繁，内存占用更可控但增加CPU开销；"
            "值越大计划缓存更稳定，但可能积累过多无用计划。"
        )
    },
    "enable_adaptive_plan_cache": {
        "code_files": ["src/sql/plan_cache/ob_plan_cache.cpp"],
        "mechanism": (
            "自适应计划缓存开关。开启后，系统根据执行统计信息动态调整计划选择："
            "当计划命中率低于_pc_adaptive_effectiveness_ratio_threshold时，"
            "自动将该计划标记为低效，后续查询重新生成计划。"
            "适用于数据分布变化导致执行计划变差的场景。"
        )
    },
    "_pc_adaptive_effectiveness_ratio_threshold": {
        "code_files": ["src/sql/plan_cache/ob_plan_cache.cpp"],
        "mechanism": (
            "自适应计划缓存的最低有效性比率阈值，默认5。"
            "当计划的命中/未命中比率低于此值时，该计划被视为低效，"
            "触发计划淘汰或重新生成。值越大淘汰越激进，"
            "值越小则允许更多低效计划留在缓存中。"
        )
    },
    "_ob_plan_cache_auto_flush_interval": {
        "code_files": ["src/sql/plan_cache/ob_plan_cache.cpp"],
        "mechanism": (
            "ob_plan_cache.cpp:2732，计划缓存自动刷新间隔。"
            "auto_flush_pc_interval = GCONF._ob_plan_cache_auto_flush_interval / (1000*1000L)，单位转换为秒。"
            "每隔此时间自动清空整个计划缓存。值0表示不自动刷新。"
            "用于强制刷新计划缓存以消除低效计划的累积影响。"
        )
    },
    "_ob_plan_cache_gc_strategy": {
        "code_files": ["src/sql/plan_cache/ob_plan_cache.cpp"],
        "mechanism": (
            "ob_plan_cache.cpp:2719，计划缓存GC策略："
            "OFF=关闭GC，计划永不过期；"
            "REPORT=仅检查和报告泄露的计划缓存对象；"
            "RELEASE=检查并释放泄露对象(默认)。"
            "REPORT模式用于诊断，RELEASE模式用于自动修复。"
        )
    },
    "enable_sql_operator_dump": {
        "code_files": ["src/sql/engine/ob_tenant_sql_memory_manager.cpp"],
        "mechanism": (
            "SQL算子(排序/哈希连接/物化/窗口函数)是否允许磁盘溢写(spill)。"
            "为True时，当算子内存超过_hash_area_size/_sort_area_size等限制后，"
            "将中间数据写入临时文件，避免OOM错误。"
            "为False时，内存不足直接报错。生产环境务必开启。"
        )
    },
    "spill_compression_codec": {
        "code_files": ["src/sql/code_generator/ob_static_engine_cg.cpp", "src/rootserver/ob_tenant_ddl_service.cpp"],
        "mechanism": (
            "ob_static_engine_cg.cpp中，磁盘溢写数据的压缩算法，默认NONE不压缩。"
            "可选ZSTD/LZ4等。压缩可减少溢写IO量(尤其对SSD友好)，"
            "但增加CPU开销。IO密集型场景建议LZ4(压缩快)，"
            "磁盘空间紧张场景建议ZSTD(压缩率高)。"
        )
    },
    "_force_hash_join_spill": {
        "code_files": ["src/sql/engine/join/ob_hash_join_op.cpp", "src/sql/engine/join/hash_join/ob_hash_join_vec_op.cpp"],
        "mechanism": (
            "ob_hash_join_op.cpp中，强制HASH JOIN溢写的调试开关。"
            "为True时，无论内存是否充足，HASH JOIN构建完哈希表后都强制溢写。"
            "仅用于测试和验证溢写路径的正确性，生产环境必须关闭。"
        )
    },
    "_force_hash_groupby_dump": {
        "code_files": ["src/sql/engine/aggregate/ob_hash_groupby_op.cpp"],
        "mechanism": (
            "强制哈希聚合溢写的调试开关，类似_force_hash_join_spill。"
            "为True时强制HASH GROUP BY溢写到磁盘。"
            "仅用于测试，生产环境必须关闭。"
        )
    },
    "_hash_join_enabled": {
        "code_files": ["src/sql/optimizer/ob_log_join.cpp"],
        "mechanism": (
            "ob_log_join.cpp中，优化器是否考虑HASH JOIN计划。"
            "为False时，优化器不会生成HASH JOIN算子，"
            "只考虑NESTED LOOP JOIN或MERGE JOIN。"
            "在Hash Join效率低下的场景(如无等值条件)可关闭，"
            "但通常不建议关闭，Hash Join是大表关联的最优选择。"
        )
    },
    "_nested_loop_join_enabled": {
        "code_files": ["src/sql/optimizer/ob_log_join.cpp"],
        "mechanism": (
            "优化器是否考虑NESTED LOOP JOIN计划。"
            "为False时优化器不生成NLJ计划。"
            "NLJ适合小表驱动大表且有索引的场景，关闭后可能影响小表关联性能。"
        )
    },
    "_optimizer_sortmerge_join_enabled": {
        "code_files": ["src/sql/optimizer/ob_log_join.cpp"],
        "mechanism": (
            "优化器是否考虑MERGE SORT JOIN计划。"
            "为False时优化器不生成MSJ计划。"
            "MSJ适合两个大表都已按关联键排序的场景，关闭后这类查询需使用Hash Join。"
        )
    },
    "_enable_hash_join_hasher": {
        "code_files": ["src/sql/engine/join/ob_hash_join_op.cpp"],
        "mechanism": (
            "ob_hash_join_op.cpp中，HASH JOIN使用的哈希函数选择："
            "1=murmurhash(默认，分布均匀)，2=crc64(计算更快但分布可能不均)。"
            "数据倾斜严重时可尝试切换，murmurhash通常更优。"
        )
    },
    "_enable_hash_join_processor": {
        "code_files": ["src/sql/engine/join/ob_hash_join_op.cpp", "src/sql/engine/join/hash_join/ob_hash_join_vec_op.cpp"],
        "mechanism": (
            "ob_hash_join_op.cpp中，HASH JOIN的处理路径选择，默认7=自动选择。"
            "不同路径在内存管理、分区策略上有差异。"
            "自动模式下系统根据数据量和可用内存选择最优路径。"
            "仅在特定调优场景下需手动指定。"
        )
    },
    "_bloom_filter_ratio": {
        "code_files": ["src/sql/optimizer/ob_join_order.cpp", "src/sql/plan_cache/ob_plan_cache_util.cpp"],
        "mechanism": (
            "ob_join_order.cpp:16318，PX布隆过滤器误判率："
            "misjudgment_rate = _bloom_filter_ratio / 100.0。"
            "布隆过滤器用于PX并行查询时过滤不满足条件的数据。"
            "值越小过滤越精确(误判少)但消耗更多内存；"
            "值越大内存节省但过滤效果差(更多无效数据传输)。"
            "默认35%，数据倾斜场景可降低到5-10%提升过滤精度。"
        )
    },
    "px_workers_per_cpu_quota": {
        "code_files": ["src/observer/omt/ob_tenant_mgr.cpp"],
        "mechanism": (
            "ob_tenant_mgr.cpp中，每个CPU配额分配的PX(并行查询)工作线程数，默认10。"
            "PX Worker数 = tenant_cpu * px_workers_per_cpu_quota。"
            "值越大并行查询可用Worker越多，但占用更多CPU和内存。"
            "OLAP场景建议增大，OLTP场景可保持默认或降低。"
        )
    },
    "_max_px_workers_per_cpu": {
        "code_files": ["src/sql/engine/px/ob_px_sqc_handler.cpp", "src/sql/engine/px/ob_px_admission.cpp"],
        "mechanism": (
            "ob_px_admission.cpp:234，每CPU允许的PX Worker上限："
            "upper_bound = tenant_min_cpu * _max_px_workers_per_cpu。"
            "这是PX Worker数的硬上限，防止并行查询消耗过多CPU。"
            "默认1，即每CPU最多1个PX Worker，较为保守。"
            "OLAP场景建议增大到2-4以提升并行度。"
        )
    },
    "_parallel_max_active_sessions": {
        "code_files": ["src/sql/engine/px/ob_px_admission.cpp"],
        "mechanism": (
            "ob_px_admission.cpp:38，租户最大活跃并行会话数："
            "pmas = tenant_config->_parallel_max_active_sessions。"
            "值0表示不限制。当活跃并行会话超过此值时，新的并行查询需排队等待。"
            "用于控制并行查询资源消耗，防止过多并行查询同时执行导致CPU/内存争用。"
        )
    },
    "_px_max_pipeline_depth": {
        "code_files": ["src/sql/engine/px/ob_px_coord_op.cpp"],
        "mechanism": (
            "并行执行的最大流水线深度，范围[2,3]，默认2。"
            "深度2表示两阶段并行(Scan->Join/Agg)，深度3增加一个阶段。"
            "深度越大并行度可能更高，但调度开销和内存占用也更大。"
            "大多数场景2层已足够，极复杂的查询可尝试3层。"
        )
    },
    "_px_join_skew_handling": {
        "code_files": ["src/sql/engine/px/ob_px_coord_op.cpp"],
        "mechanism": (
            "PX并行连接的数据倾斜处理开关，默认True。"
            "开启后系统检测数据倾斜(基于_px_join_skew_minfreq)，"
            "对倾斜值单独分配处理逻辑，避免某个Worker处理过多数据。"
            "数据倾斜场景下效果显著，关闭则所有Worker平均分配。"
        )
    },
    "_px_join_skew_minfreq": {
        "code_files": ["src/sql/engine/px/ob_px_coord_op.cpp"],
        "mechanism": (
            "PX并行连接倾斜值的最小频率阈值，默认30%。"
            "当某个值的出现频率超过此阈值时，被判定为倾斜值，"
            "触发特殊的倾斜处理逻辑(如分而治之)。"
            "值越大只处理极端倾斜，值越小更多值被视为倾斜。"
        )
    },
    "_enable_index_merge": {
        "code_files": ["src/sql/optimizer/ob_join_order.cpp", "src/sql/optimizer/ob_log_table_scan.cpp"],
        "mechanism": (
            "ob_join_order.cpp中，索引合并优化开关，默认False。"
            "开启后优化器可生成同时使用多个索引的执行计划，"
            "将多个索引扫描结果取交集/并集。适合多条件OR查询。"
            "关闭时每个表访问路径只选择一个索引。"
            "索引合并增加优化器搜索空间，可能增加计划生成时间。"
        )
    },
    "optimizer_index_cost_adj": {
        "code_files": ["src/sql/optimizer/ob_opt_est_cost.cpp"],
        "mechanism": (
            "ob_opt_est_cost.cpp中，索引扫描成本调整因子，默认0表示不调整。"
            "非0时，索引扫描成本=原始成本*optimizer_index_cost_adj/100。"
            "值<100使索引扫描看起来更便宜(倾向选索引)，"
            "值>100使索引扫描看起来更贵(倾向全表扫描)。"
            "用于微调优化器选择索引的倾向性。"
        )
    },
}


def main():
    import json
    output_path = "/Users/wzh/Documents/DBdoctor/oceanbase-tuning/output/sql_params_mechanism.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(SQL_PARAMS_MECHANISM, f, ensure_ascii=False, indent=2)
    print(f"✓ SQL执行参数机制已导出: {output_path}")
    print(f"  共 {len(SQL_PARAMS_MECHANISM)} 个参数")


if __name__ == "__main__":
    main()
