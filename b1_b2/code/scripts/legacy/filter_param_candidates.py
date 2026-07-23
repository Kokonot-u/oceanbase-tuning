#!/usr/bin/env python3
"""
OceanBase 性能参数候选筛选脚本

从 ob_parameters.tsv 中按关键词筛选性能相关参数，
按4个维度分类：CPU调度、内存管理、磁盘IO、SQL执行

输出: outputs/param_candidates.csv
"""

import csv
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_PATH = os.path.join(BASE_DIR, "output", "ob_parameters.tsv")
OUTPUT_PATH = os.path.join(BASE_DIR, "output", "param_candidates.csv")

# ============================================================
# 筛选规则定义
# ============================================================
# 每个维度的关键词，匹配参数名(不区分大小写)
CATEGORY_RULES = {
    "CPU调度": {
        "keywords": ["cpu", "worker", "thread", "concurrency", "parallel", "queue", "scheduler"],
        "exclude": ["sql_operator_dump", "spill", "log_archive", "backup", "restore",
                     "migration", "transfer", "balance", "replay"],
    },
    "内存管理": {
        "keywords": ["memory_limit", "memory_reserved", "memstore", "mem_limit",
                      "_hash_area", "_sort_area", "sql_work_area", "cache_wash",
                      "cache_priority", "row_cache", "block_cache", "index_block_cache",
                      "fuse_row_cache", "storage_meta_mem", "_mds_memory",
                      "_tx_data_memory", "_tx_share_memory", "_ctx_memory",
                      "query_memory_limit", "result_cache", "_chunk_row_store",
                      "_px_max_message", "_parallel_min_message", "_temporary_file_io_area",
                      "ob_vector_memory", "rpc_memory_limit", "memory_chunk_cache"],
        "exclude": ["thread", "migration", "transfer", "location_cache_refresh"],
    },
    "磁盘IO": {
        "keywords": ["io_", "disk_", "datafile", "data_disk", "log_disk", "clog", "_io_",
                      "writing_throttling", "_private_buffer", "log_writer",
                      "compaction_high", "compaction_low", "compaction_mid",
                      "minor_compact", "major_compact", "freeze_trigger",
                      "memstore_limit", "ss_cache", "micro_cache"],
        "exclude": ["sql_login", "sql_net", "memory_limit", "memory_chunk", "memory_reserved",
                     "cache_wash", "cpu_quota", "worker", "thread_count",
                     "job_queue", "ddl_thread", "ha_thread", "compaction_dag_cnt",
                     "compaction_schedule", "mds_compaction",
                     "alert_log", "audit_log", "syslog", "diag_syslog",
                     "archive_lag", "log_archive", "log_restore",
                     "backup_", "standby_db", "arbitration",
                     "_ss_advance", "_ss_clog", "_ss_disk_space", "_ss_enable",
                     "_ss_failed", "_ss_garbage", "_ss_hidden", "_ss_local_cache",
                     "_ss_macro_block", "_ss_major", "_ss_mem_macro", "_ss_micro_cache",
                     "_ss_new_leader", "_ss_old_ver", "_ss_schedule", "_ss_sslog",
                     "_ss_tablet", "shared_log"],
    },
    "SQL执行": {
        "keywords": ["plan_cache", "sql_audit", "sql_operator_dump", "spill_",
                      "hash_join", "nested_loop", "sortmerge_join", "bloom_filter",
                      "optimizer_index", "index_merge", "px_workers", "px_join_skew",
                      "px_max_pipeline", "parallel_max_active", "max_px_workers",
                      "trace_log_slow", "adaptive_plan_cache", "plan_cache_evict",
                      "plan_cache_gc", "plan_cache_auto_flush", "large_query",
                      "pc_adaptive", "hash_area_size", "sort_area_size"],
        "exclude": ["sql_login_thread", "sql_net_thread", "tenant_sql_net",
                     "sql_protocol", "sql_work_area", "enable_sql_extension",
                     "rpc_timeout", "ha_rpc", "connection_control",
                     "sql_insert_multi", "sql_plan_management",
                     "balancer_task", "dead_socket", "debug_sync",
                     "enable_ob_ratelimit", "audit_log_query"],
    },
}


def classify_param(name, info, section, edit_level):
    """
    对参数进行分类，返回 (category, reason) 或 (None, None)
    """
    name_lower = name.lower()
    info_lower = (info or "").lower()

    # 排除：只读参数、已废弃参数、内部调试参数
    if edit_level == "READONLY":
        return None, None
    if "to be removed" in info_lower or "deprecated" in info_lower:
        return None, None

    # 遍历4个维度，按优先级匹配
    for category, rule in CATEGORY_RULES.items():
        # 检查排除关键词
        excluded = False
        for ex in rule["exclude"]:
            if ex in name_lower:
                excluded = True
                break
        if excluded:
            continue

        # 检查匹配关键词（在参数名或INFO中）
        matched_keywords = []
        for kw in rule["keywords"]:
            if kw in name_lower:
                matched_keywords.append(kw)
            elif kw in info_lower:
                matched_keywords.append(f"info:{kw}")

        if matched_keywords:
            reason = f"关键词匹配: {', '.join(matched_keywords)}"
            return category, reason

    return None, None


def main():
    print("=" * 60)
    print("OceanBase 性能参数候选筛选")
    print("=" * 60)

    # 1. 读取TSV
    print("\n[1/2] 读取参数表...")
    params = []
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            params.append(row)
    print(f"  共 {len(params)} 个参数")

    # 2. 筛选并分类
    print("\n[2/2] 筛选性能参数...")
    candidates = []
    for row in params:
        name = row['NAME']
        info = row['INFO']
        section = row['SECTION']
        edit_level = row['EDIT_LEVEL']

        category, reason = classify_param(name, info, section, edit_level)
        if category:
            candidates.append({
                "category": category,
                "name": name,
                "current_value": row['VALUE'],
                "info": (info or "")[:200],  # 截断过长INFO
                "section": section,
                "edit_level": edit_level,
                "reason": reason,
            })

    # 3. 输出CSV
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "category", "name", "current_value", "info", "section", "edit_level", "reason"
        ])
        writer.writeheader()
        writer.writerows(candidates)

    # 4. 统计
    stats = {}
    for c in candidates:
        stats[c["category"]] = stats.get(c["category"], 0) + 1

    print(f"\n  筛选结果: {len(candidates)} 个性能参数候选")
    print(f"  输出文件: {OUTPUT_PATH}")
    print(f"\n  分类统计:")
    for cat in ["CPU调度", "内存管理", "磁盘IO", "SQL执行"]:
        count = stats.get(cat, 0)
        print(f"    {cat}: {count} 个")

    # 5. 列出每类TOP 10参数
    for cat in ["CPU调度", "内存管理", "磁盘IO", "SQL执行"]:
        cat_params = [c for c in candidates if c["category"] == cat]
        print(f"\n  {cat} TOP 10:")
        for i, p in enumerate(cat_params[:10], 1):
            print(f"    {i}. {p['name']} (当前值: {p['current_value']})")


if __name__ == "__main__":
    main()
