#!/usr/bin/env python3
"""
OceanBase v4.5 内存管理参数机制补充
基于源码 src/share/config/, src/storage/tx_storage/, src/share/allocator/ 等分析
"""

MEMORY_PARAMS_MECHANISM = {
    "memory_limit": {
        "code_files": ["src/share/config/ob_server_config.cpp", "src/share/config/ob_server_config.h", "src/observer/ob_server_reload_config.cpp"],
        "mechanism": (
            "ob_server_config.cpp:285-378 reload_config()中，memory_limit是observer进程内存总上限。"
            "当值为0时，实际值=物理内存*memory_limit_percentage/100（第292行）。"
            "非0时直接使用设定值，但不能小于4G或大于物理内存。"
            "关键派生：get_server_memory_avail()=memory_limit-system_memory，"
            "所有租户的memory_size之和不能超过此值（第347行校验）。"
            "这是OceanBase内存体系的根参数，所有内存子配额都从它派生。"
        )
    },
    "memory_limit_percentage": {
        "code_files": ["src/share/config/ob_server_config.cpp", "src/share/parameter/ob_parameter_seed.ipp"],
        "mechanism": (
            "仅当memory_limit=0时生效，实际内存上限=物理内存*memory_limit_percentage/100。"
            "默认80%，即observer使用80%物理内存，留20%给OS和其他进程。"
            "与memory_limit互斥：设置了memory_limit后此参数不生效。"
            "生产环境建议80-90%，为OS预留足够内存避免OOM。"
        )
    },
    "system_memory": {
        "code_files": ["src/share/config/ob_server_config.cpp", "src/observer/ob_server_reload_config.cpp"],
        "mechanism": (
            "ob_server_config.cpp中，system_memory从总memory_limit中扣除，不分配给任何租户。"
            "get_server_memory_avail()=memory_limit-system_memory。"
            "这部分内存用于observer内部核心操作(如schema管理、election等)。"
            "值0时系统自动计算。设置过小会导致内部操作内存不足，过大则浪费可分配给租户的内存。"
        )
    },
    "memstore_limit_percentage": {
        "code_files": ["src/share/config/ob_config_helper.cpp", "src/storage/tx_storage/ob_tenant_freezer.cpp", "src/share/allocator/ob_shared_memory_allocator_mgr.cpp"],
        "mechanism": (
            "ob_config_helper.cpp:100-136，memstore_limit_percentage用于校验内存配额约束："
            "memstore_limit + tx_data_limit + mds_limit 均须 <= _tx_share_memory_limit_percentage。"
            "ob_tenant_freezer.cpp:1445，MemStore冻结阈值=min(memstore_limit, max_memstore_can_get) * freeze_trigger_percentage/100。"
            "ob_shared_memory_allocator_mgr.cpp:55，实际memstore内存=total_memory/100*memstore_limit_percentage。"
            "该参数决定了写内存的上限，值越大写性能越好但留给读缓存的内存越少。"
        )
    },
    "freeze_trigger_percentage": {
        "code_files": ["src/storage/tx_storage/ob_tenant_freezer.cpp", "src/storage/tx_storage/ob_checkpoint_service.cpp"],
        "mechanism": (
            "ob_tenant_freezer.cpp:1445，freeze_trigger计算："
            "memstore_freeze_trigger = min(memstore_limit, max_memstore_can_get) / 100 * freeze_trigger_percentage。"
            "当MemStore使用量达到此阈值时，触发minor freeze将MemStore数据转储到磁盘，释放写内存。"
            "值越小越早触发freeze，写内存更安全但可能频繁freeze影响写入性能；"
            "值越大写性能更好但MemStore溢出风险增加。"
        )
    },
    "query_memory_limit_percentage": {
        "code_files": ["src/share/memory/ob_memory_tracker.cpp", "src/share/ob_errno.h"],
        "mechanism": (
            "单个查询可使用的租户内存百分比上限。当查询申请内存超过此限额时，"
            "返回OB_EXCEED_MEM_LIMIT错误（ob_errno.h中定义）。"
            "这是防止单个大查询耗尽租户内存的硬限制。默认50%，意味着单查询最多使用租户内存的一半。"
            "OLTP场景建议降低(如30%)防止单查询冲击，OLAP场景可适当调高。"
        )
    },
    "sql_work_area": {
        "code_files": ["src/observer/omt/ob_tenant_duty_task.cpp", "src/sql/engine/ob_sql_mem_mgr_processor.cpp"],
        "mechanism": (
            "ob_tenant_duty_task.cpp中，sql_work_area作为租户级SQL工作区内存总量上限。"
            "排序(SORT)、哈希连接(HASH JOIN)、物化等算子共享此工作区。"
            "ob_sql_mem_mgr_processor.cpp中，各算子通过ObSqlMemMgrProcessor申请内存，"
            "总分配不能超过sql_work_area。超出时算子触发磁盘溢写(spill)。"
            "值越大，更多操作可在内存中完成，性能越好。"
        )
    },
    "_hash_area_size": {
        "code_files": ["src/sql/engine/join/ob_hash_join_op.cpp", "src/sql/engine/join/hash_join/ob_hash_join_vec_op.cpp", "src/sql/engine/ob_sql_mem_mgr_processor.cpp"],
        "mechanism": (
            "ob_sql_mem_mgr_processor.cpp:358-369，HASH JOIN可用的最大内存。"
            "优先使用session级变量get_tenant_hash_area_size()，否则使用tenant_config->_hash_area_size。"
            "ob_hash_join_op.cpp:1406-1419，手动模式直接使用该值；"
            "自动模式下通过ObSqlWorkAreaType::HASH_WORK_AREA申请。"
            "实际可用=hash_area_size*80/100（第1419行，预留20%给哈希表结构）。"
            "增大此值可减少HASH JOIN磁盘溢写，提升大表关联性能。"
        )
    },
    "_sort_area_size": {
        "code_files": ["src/sql/engine/ob_sql_mem_mgr_processor.cpp", "src/sql/session/ob_sql_session_info.h"],
        "mechanism": (
            "ob_sql_mem_mgr_processor.cpp:360-371，排序操作可用的最大内存。"
            "优先使用session级变量get_tenant_sort_area_size()，否则使用tenant_config->_sort_area_size。"
            "当排序数据量超过此值时，触发外部排序(磁盘溢写)。"
            "增大此值可让更多排序在内存中完成，减少IO开销。"
            "OLAP场景建议调大(如64M-128M)，OLTP场景默认32M通常足够。"
        )
    },
    "cache_wash_threshold": {
        "code_files": ["src/observer/ob_server.cpp", "src/observer/ob_server_reload_config.cpp"],
        "mechanism": (
            "当系统剩余内存低于cache_wash_threshold时，触发KV缓存淘汰(wash)。"
            "ob_server_reload_config.cpp中，配置变更时重新加载该阈值。"
            "淘汰优先级由各缓存的priority参数决定(如user_block_cache_priority)。"
            "值越大越早触发缓存淘汰，为其他操作预留更多内存；"
            "值越小则缓存使用更充分，但可能导致内存紧张时淘汰不够及时。"
        )
    },
    "memory_chunk_cache_size": {
        "code_files": ["src/observer/ob_server_reload_config.cpp"],
        "mechanism": (
            "内存块缓存(Chunk Cache)的最大值。OceanBase内存分配器使用Chunk(2M)为单位管理内存，"
            "Chunk Cache缓存已释放的Chunk避免重复向OS申请。值0表示自动管理。"
            "增大此值可减少内存分配延迟(更多Chunk可复用)，但占用更多常驻内存。"
        )
    },
    "memory_reserved": {
        "code_files": ["src/observer/ob_server.cpp", "src/observer/ob_server_reload_config.cpp"],
        "mechanism": (
            "系统预留的紧急内存，用于极端情况(如内存不足时的内部操作)。"
            "这部分内存不在常规分配路径中，仅在紧急路径可使用。"
            "默认500M，为schema刷新、日志写入等关键操作提供内存保障。"
            "不建议调小，否则可能在内存紧张时导致集群操作失败。"
        )
    },
    "_storage_meta_memory_limit_percentage": {
        "code_files": ["src/storage/meta_mem/ob_tenant_meta_mem_mgr.cpp", "src/storage/meta_mem/ob_tenant_meta_obj_pool.h"],
        "mechanism": (
            "ob_tenant_meta_mem_mgr.cpp中，存储元数据(如Tablet、SSTable元信息)占租户内存的百分比上限。"
            "Tablet数量越多(如大量分区表)，所需元数据内存越大。"
            "当元数据内存达到此上限时，触发元数据淘汰和复用。"
            "默认20%，在海量Tablet场景下可能需要调大。"
        )
    },
    "_mds_memory_limit_percentage": {
        "code_files": ["src/share/config/ob_config_helper.cpp", "src/share/config/ob_server_config.h"],
        "mechanism": (
            "ob_config_helper.cpp:108，MDS(多版本数据服务)占租户内存的百分比上限。"
            "MDS存储锁信息、事务上下文等多版本数据。该值须<=_tx_share_memory_limit_percentage（校验逻辑在第125行）。"
            "默认10%，高并发写入场景下可能需要调大以容纳更多事务上下文。"
        )
    },
    "_tx_data_memory_limit_percentage": {
        "code_files": ["src/share/config/ob_config_helper.cpp", "src/share/config/ob_server_config.h"],
        "mechanism": (
            "ob_config_helper.cpp:108，事务数据占租户内存的百分比上限。"
            "tx_data包含事务状态、提交记录等。该值须<=_tx_share_memory_limit_percentage。"
            "默认20%，高并发事务场景下事务数据量大，可能需要调大。"
        )
    },
    "_tx_share_memory_limit_percentage": {
        "code_files": ["src/share/config/ob_config_helper.cpp", "src/share/throttle/ob_share_throttle_define.cpp"],
        "mechanism": (
            "ob_config_helper.cpp:96-142，事务共享内存上限百分比。它是memstore、tx_data、mds三个子配额的总约束："
            "memstore_limit + tx_data_limit + mds_limit 均须 <= tx_share_memory_limit。"
            "值0表示自动计算=MAX(memstore_limit_percentage, vector_mem_limit_percentage+5)+10（ob_share_throttle_define.cpp:44-51）。"
            "这是写路径内存的总天花板。"
        )
    },
    "rpc_memory_limit_percentage": {
        "code_files": ["src/observer/omt/ob_tenant_duty_task.cpp"],
        "mechanism": (
            "RPC占用租户内存的百分比上限，值0表示不限制。"
            "当RPC内存使用超过此限额时，新RPC请求可能被拒绝或排队。"
            "在大量数据传输(如大结果集返回、数据导入导出)场景下，RPC内存占用可能很大，"
            "设置此上限可防止RPC内存挤占查询和写入内存。"
        )
    },
    "ob_vector_memory_limit_percentage": {
        "code_files": ["src/share/config/ob_server_config.h", "src/sql/engine/expr/ob_vector_index_allocator/ob_tenant_vector_allocator.cpp"],
        "mechanism": (
            "向量索引占租户内存的百分比上限。ob_tenant_vector_allocator.cpp中，"
            "向量索引内存申请受此配额约束。值0表示不限制。"
            "使用向量搜索功能时需关注，过小会导致向量索引加载失败或频繁淘汰。"
        )
    },
    "_ctx_memory_limit": {
        "code_files": ["src/observer/omt/ob_tenant_duty_task.cpp"],
        "mechanism": (
            "租户上下文(Context)内存限制，字符串格式如'1G'。"
            "控制会话级上下文对象(如PL/SQL变量、游标状态等)的总内存占用。"
            "值空表示不限制。PL/SQL大量使用场景下需要关注此限制。"
        )
    },
    "_chunk_row_store_mem_limit": {
        "code_files": ["src/sql/engine/basic/ob_chunk_datum_store.cpp", "src/sql/pl/ob_pl_type.cpp", "src/sql/ob_spi.cpp"],
        "mechanism": (
            "ChunkRowStore(行存储格式转换缓冲区)的最大内存。值0表示跟随sql_work_area。"
            "ob_chunk_datum_store.cpp中使用此限制控制行数据缓存大小。"
            "当数据量超过限制时触发磁盘溢写。在宽表查询场景下可适当调大。"
        )
    },
    "result_cache_max_size": {
        "code_files": ["src/sql/engine/expr/ob_udf_result_cache.h", "src/sql/engine/expr/ob_udf_result_cache_mgr.cpp"],
        "mechanism": (
            "ob_udf_result_cache_mgr.cpp中，查询结果缓存的最大内存容量。"
            "结果缓存存储查询的最终结果集，相同查询命中缓存时直接返回无需重新执行。"
            "增大此值可缓存更多结果，但占用更多内存。建议在重复查询多的场景启用并调大。"
        )
    },
    "result_cache_max_result": {
        "code_files": ["src/sql/engine/expr/ob_udf_result_cache.h", "src/sql/engine/expr/ob_udf_result_cache_mgr.cpp"],
        "mechanism": (
            "单条结果缓存占结果缓存总量的百分比上限，默认5%。"
            "超过此比例的结果集不会被缓存，防止单个大结果集挤占整个结果缓存。"
            "OLAP场景大结果集较多时可适当调大，但注意不要让单条缓存占比过高。"
        )
    },
    "_px_max_message_pool_pct": {
        "code_files": ["src/sql/dtl/ob_dtl_channel_mem_manager.cpp"],
        "mechanism": (
            "ob_dtl_channel_mem_manager.cpp中，DTL(数据传输层)消息缓冲池占租户内存的百分比上限。"
            "DTL用于PX并行执行时各Worker间的数据传输。消息缓冲池存储传输中的中间数据。"
            "默认40%，并行查询多且中间数据量大时可适当增大。"
        )
    },
    "_parallel_min_message_pool": {
        "code_files": ["src/sql/dtl/ob_dtl_tenant_mem_manager.cpp"],
        "mechanism": (
            "ob_dtl_tenant_mem_manager.cpp中，DTL消息缓冲池保留的最小内存。"
            "当缓冲池缩容时不会低于此值，确保PX并行执行始终有基本的通信缓冲可用。"
            "默认16M，高并行度场景下可适当增大。"
        )
    },
    "_temporary_file_io_area_size": {
        "code_files": ["src/sql/engine/basic/ob_tmp_file_write_cache.cpp"],
        "mechanism": (
            "ob_tmp_file_write_cache.cpp中，临时文件IO缓冲区占租户内存的百分比，默认1%。"
            "临时文件用于SQL算子溢写(spill)和中间结果存储。"
            "增大此值可提升溢写性能(更大的写缓冲)，但减少可用查询内存。"
            "在大量spill的OLAP场景下建议调大。"
        )
    },
}


def main():
    import json
    output_path = "/Users/wzh/Documents/DBdoctor/oceanbase-tuning/output/memory_params_mechanism.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(MEMORY_PARAMS_MECHANISM, f, ensure_ascii=False, indent=2)
    print(f"✓ 内存管理参数机制已导出: {output_path}")
    print(f"  共 {len(MEMORY_PARAMS_MECHANISM)} 个参数")


if __name__ == "__main__":
    main()
