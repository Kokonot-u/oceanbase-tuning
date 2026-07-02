#!/usr/bin/env python3
"""
OceanBase v4.5 磁盘IO参数机制补充
基于源码 src/logservice/palf/, src/share/io/, src/storage/ 等分析
"""

DISK_IO_PARAMS_MECHANISM = {
    "datafile_disk_percentage": {
        "code_files": ["src/storage/blocksstable/ob_block_manager.cpp", "src/observer/ob_server.cpp"],
        "mechanism": (
            "ob_block_manager.cpp中，datafile_disk_percentage指定数据文件占磁盘空间的百分比。"
            "值为0时使用datafile_size配置。OceanBase使用预分配磁盘空间策略，"
            "启动时根据此百分比分配磁盘空间给数据文件(block_file)。"
            "值越大留给日志和OS的空间越少，但数据可用空间更大。"
            "建议数据文件占70-80%，留20-30%给日志和OS。"
        )
    },
    "data_disk_usage_limit_percentage": {
        "code_files": ["src/rootserver/ob_unit_manager.cpp", "src/rootserver/ob_server_balancer.cpp"],
        "mechanism": (
            "ob_unit_manager.cpp中，数据磁盘安全使用率百分比阈值，默认90%。"
            "当磁盘使用率超过此值时触发告警，系统开始限流写入操作。"
            "这是防止磁盘写满的最后防线，不建议设得太高。"
            "当磁盘使用率达到data_disk_write_limit_percentage时完全停止用户写入。"
        )
    },
    "data_disk_write_limit_percentage": {
        "code_files": ["src/rootserver/ob_root_service.cpp", "src/share/io/ob_local_device.cpp"],
        "mechanism": (
            "ob_local_device.cpp中，数据磁盘写入限制百分比，默认0表示不额外限制。"
            "当用户数据磁盘使用率超过此值时，停止用户写入操作（系统内部操作仍可写入）。"
            "与data_disk_usage_limit_percentage形成二级保护："
            "前者触发告警和限流，后者直接禁止写入。建议设为95%。"
        )
    },
    "log_disk_percentage": {
        "code_files": ["src/observer/ob_server.cpp"],
        "mechanism": (
            "指定日志文件(clog/slog)占磁盘空间的百分比，值0时使用log_disk_size。"
            "与datafile_disk_percentage之和不应超过100%。"
            "日志空间不足会导致事务无法提交，需确保日志空间充足。"
            "建议数据文件70%+日志20%+OS/其他10%的配比。"
        )
    },
    "log_disk_size": {
        "code_files": ["src/rootserver/ob_unit_placement_strategy.cpp", "src/rootserver/ob_unit_manager.cpp"],
        "mechanism": (
            "日志文件磁盘空间绝对大小，当log_disk_percentage=0时生效。"
            "ob_unit_manager.cpp中用于计算租户日志磁盘配额。"
            "每个租户的日志配额=租户unit配置的log_disk_size。"
            "日志空间不足会触发写入限流甚至停止写入，务必保证充足。"
        )
    },
    "log_disk_throttling_percentage": {
        "code_files": ["src/logservice/palf/palf_env_impl.cpp", "src/logservice/palf/log_throttle.cpp", "src/logservice/palf/palf_options.h"],
        "mechanism": (
            "palf_env_impl.cpp:97-102，日志磁盘写入限流的触发阈值："
            "trigger_size = log_disk_usage_limit_size * log_disk_throttling_percentage / 100。"
            "当不可回收日志磁盘大小超过trigger_size时，need_throttling()返回true。"
            "palf_options.h:182-187，限流还要求trigger_percentage < stopping_writing_percentage，"
            "即log_disk_throttling_percentage须小于log_disk_utilization_limit_threshold才有效。"
            "log_throttle.cpp:161-163，触发后使用衰减因子控制写入速率，"
            "available=total*(stopping_threshold-trigger_percentage)/100，空间越少衰减越快。"
            "设为100表示关闭限流。默认60%，在80%停止写入前给20%的缓冲区间。"
        )
    },
    "log_disk_throttling_maximum_duration": {
        "code_files": ["src/logservice/palf/palf_env_impl.cpp", "src/logservice/palf/log_throttle.cpp"],
        "mechanism": (
            "日志磁盘限流的最大持续时间。当限流持续时间超过此值，"
            "系统认为限流无法解决问题，可能触发更激进的处理(如强制日志回收)。"
            "默认2h，确保限流不会无限期持续。"
        )
    },
    "log_disk_utilization_threshold": {
        "code_files": ["src/logservice/palf/palf_env_impl.cpp", "src/logservice/palf/palf_options.cpp"],
        "mechanism": (
            "palf_env_impl.cpp中，日志磁盘利用率阈值，默认80%。"
            "超过此阈值后，系统开始重用(回收)旧的日志文件。"
            "这是日志空间回收的触发点，应在log_disk_throttling_percentage之后、"
            "log_disk_utilization_limit_threshold之前。即：60%限流<80%回收<95%停止写入。"
        )
    },
    "log_disk_utilization_limit_threshold": {
        "code_files": ["src/logservice/palf/palf_env_impl.cpp", "src/logservice/palf/palf_options.h"],
        "mechanism": (
            "palf_options.h:182-187，日志磁盘利用率硬上限，默认95%。"
            "超过此阈值后停止提交新日志(Stop Writing)，事务无法提交。"
            "这是保护日志磁盘不被写满的最后防线。"
            "必须大于log_disk_throttling_percentage，否则限流永远不会触发。"
        )
    },
    "_data_storage_io_timeout": {
        "code_files": ["src/share/parameter/ob_parameter_seed.ipp"],
        "mechanism": (
            "数据存储IO操作的超时时间，范围[1s, 600s]，默认10s。"
            "当单个IO请求(如SSTable读取)超过此时间未完成，返回IO超时错误。"
            "在慢磁盘或IO拥塞场景下可适当调大，避免误超时；"
            "但过大会导致故障检测延迟，影响系统容错能力。"
        )
    },
    "_io_read_batch_size": {
        "code_files": ["src/storage/access/ob_table_cache.cpp", "src/sql/engine/table/ob_table_cg_service.cpp"],
        "mechanism": (
            "单次读IO请求的最大批量大小，范围[0K, 16M]，0表示使用默认值。"
            "ob_table_cache.cpp中用于控制一次IO读取的数据量。"
            "增大此值可减少IO次数(更多数据一次读出)，适合顺序扫描场景；"
            "减小此值可降低IO延迟，适合点查场景。"
        )
    },
    "_io_read_redundant_limit_percentage": {
        "code_files": ["src/sql/engine/table/ob_table_context.cpp", "src/sql/code_generator/ob_static_engine_cg.cpp"],
        "mechanism": (
            "单次读IO请求中冗余数据百分比上限，默认0不限制。"
            "由于SSTable按块存储，读取可能包含不需要的数据(冗余)。"
            "设置此上限可控制冗余读取量，减少无用IO。"
            "对精确查询场景有帮助，但设置过低可能导致IO拆分增加。"
        )
    },
    "clog_io_isolation_mode": {
        "code_files": ["src/share/io/ob_io_define.cpp"],
        "mechanism": (
            "ob_io_define.cpp:1466-1477，CLog IO隔离模式："
            "模式1(默认)=共享模式，CLog与数据IO共享磁盘队列；"
            "模式2=独占模式，CLog有独立IO队列和带宽。"
            "独占模式下CLog写入不受数据IO影响，保障事务提交延迟的稳定性。"
            "在IO竞争激烈的场景(如大量compaction期间)建议使用独占模式。"
        )
    },
    "clog_sync_time_warn_threshold": {
        "code_files": ["src/storage/tx/ob_trans_part_ctx.cpp"],
        "mechanism": (
            "ob_trans_part_ctx.cpp中，CLog同步时间告警阈值，默认100ms。"
            "当CLog从Leader同步到Follower的时间超过此阈值，记录告警日志。"
            "这是判断主从同步延迟的重要监控指标。"
            "频繁告警说明网络或磁盘IO存在瓶颈，需排查。"
        )
    },
    "_log_writer_parallelism": {
        "code_files": ["src/logservice/palf/palf_env_impl.cpp", "src/logservice/ob_log_service.cpp"],
        "mechanism": (
            "palf_env_impl.cpp中，并行日志写入线程数，默认3。"
            "多个线程并行将日志写入磁盘，提升日志写入吞吐。"
            "在高速SSD上增大此值可充分利用磁盘带宽；"
            "HDD上增大效果有限(磁盘顺序写入已接近物理上限)。"
        )
    },
    "_enable_parallel_redo_logging": {
        "code_files": ["src/storage/tx/ob_trans_part_ctx.cpp"],
        "mechanism": (
            "ob_trans_part_ctx.cpp中，是否启用并行REDO日志写入。"
            "为True时，大事务的REDO日志可由多个线程并行写入，提升大事务提交性能。"
            "当单个事务待写日志大小超过_parallel_redo_logging_trigger时触发并行写入。"
            "关闭后所有日志写入串行执行，大事务提交延迟增加。"
        )
    },
    "_parallel_redo_logging_trigger": {
        "code_files": ["src/storage/tx/ob_trans_part_ctx.cpp"],
        "mechanism": (
            "ob_trans_part_ctx.cpp中，触发并行REDO日志写入的待写日志大小阈值，默认16M。"
            "仅当_enable_parallel_redo_logging=True且待写日志>此阈值时，"
            "才启用并行写入。小事务仍使用串行写入，避免并行化的额外开销。"
            "增大此值意味着更少的事务触发并行写入，减小则更多事务受益。"
        )
    },
    "_enable_tree_based_io_scheduler": {
        "code_files": ["src/share/io/ob_io_manager.cpp"],
        "mechanism": (
            "ob_io_manager.cpp:595/1485/2152/2249，IO调度器选择开关："
            "True=树形IO调度器(基于deadline的层级调度)，"
            "False=传统FIFO调度器。树形调度器按IO优先级和deadline组织请求队列，"
            "能更好地区分IO优先级(如CLog高优先、compaction低优先)，"
            "减少高优先IO的等待延迟。生产环境建议开启。"
        )
    },
    "ss_cache_max_percentage": {
        "code_files": ["src/share/parameter/ob_parameter_seed.ipp"],
        "mechanism": (
            "共享存储模式下，本地缓存磁盘空间占数据文件空间的最大百分比，默认30%。"
            "控制本地SSD缓存的大小，缓存热点数据减少对共享存储的访问。"
            "值越大可缓存更多热点数据，但占用更多本地磁盘。"
        )
    },
    "ss_cache_maxsize_percpu": {
        "code_files": ["src/share/parameter/ob_parameter_seed.ipp"],
        "mechanism": (
            "每CPU允许的最大本地缓存磁盘空间，默认128G。"
            "在共享存储模式下，控制单节点的本地缓存容量上限。"
            "增大此值可缓存更多数据，减少共享存储IO。"
        )
    },
    "_ss_micro_cache_memory_percentage": {
        "code_files": ["src/share/parameter/ob_parameter_seed.ipp"],
        "mechanism": (
            "共享存储模式下，微块缓存占租户内存的百分比，默认20%。"
            "微块缓存存储最热的数据块，是查询性能的关键缓存。"
            "值越大查询命中率越高，但减少其他内存可用量。"
        )
    },
    "_ss_micro_cache_size_max_percentage": {
        "code_files": ["src/share/parameter/ob_parameter_seed.ipp"],
        "mechanism": (
            "共享存储模式下，微块缓存占租户磁盘空间的最大百分比，默认20%。"
            "控制微块缓存在磁盘上的空间上限，防止缓存占用过多磁盘。"
        )
    },
    "writing_throttling_maximum_duration": {
        "code_files": ["src/share/throttle/ob_share_throttle_define.cpp", "src/share/allocator/ob_memstore_allocator.cpp"],
        "mechanism": (
            "ob_share_throttle_define.cpp/ob_memstore_allocator.cpp中，写入限流最大持续时间，默认2h。"
            "在init_throttle_config()中赋值给max_duration参数。"
            "当MemStore使用率触发限流后，限流最多持续此时间。"
            "超时后系统必须找到其他方式释放内存(如强制freeze)或报错。"
            "这是写入限流的安全阀，防止无限期限流阻塞写入。"
        )
    },
    "_private_buffer_size": {
        "code_files": ["src/storage/memtable/ob_memtable_context.cpp", "src/storage/tx/ob_mvcc_trans_ctx.cpp"],
        "mechanism": (
            "ob_memtable_context.cpp:955/968，事务私有缓冲区大小阈值，默认16K。"
            "当事务写入数据量未超过此值时，使用私有缓冲区(不直接写MemStore)；"
            "超过后将私有缓冲区批量刷新到MemStore。"
            "小事务使用私有缓冲区可减少MemStore锁竞争，提升小事务并发性能。"
            "增大此值让更多小事务使用私有缓冲区，但占用更多内存。"
        )
    },
    "_object_storage_io_timeout": {
        "code_files": ["src/share/io/ob_object_storage_io.cpp", "src/sql/engine/table/ob_table_cg_service.cpp"],
        "mechanism": (
            "对象存储IO操作超时时间，范围[1s, 1200s]，默认20s。"
            "用于控制访问对象存储(如S3/OSS)的IO超时。"
            "对象存储延迟远高于本地磁盘，需更长的超时时间。"
            "在网络不稳定或大对象场景下可适当调大。"
        )
    },
}


def main():
    import json
    output_path = "/Users/wzh/Documents/DBdoctor/oceanbase-tuning/output/disk_io_params_mechanism.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(DISK_IO_PARAMS_MECHANISM, f, ensure_ascii=False, indent=2)
    print(f"✓ 磁盘IO参数机制已导出: {output_path}")
    print(f"  共 {len(DISK_IO_PARAMS_MECHANISM)} 个参数")


if __name__ == "__main__":
    main()
