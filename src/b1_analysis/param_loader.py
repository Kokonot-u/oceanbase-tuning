"""
OceanBase参数加载器

加载100个关键参数的定义、默认值、有效范围等信息。
支持从YAML文件或JSON文件加载参数配置。
"""

from typing import Dict, List, Optional, Any
import yaml
from pathlib import Path
from dataclasses import dataclass
from loguru import logger


@dataclass
class ParameterDef:
    """参数定义"""
    name: str
    description: str
    data_type: str  # int, float, string, boolean
    default_value: Any
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    scope: str = "tenant"  # tenant, server, cluster
    edit_level: str = "dynamic"  # static, dynamic, readonly
    section: str = "UNDEFINED"  # 参数所属section
    category: str = "performance"  # performance, storage, memory, etc.


class ParamLoader:
    """OceanBase参数加载器"""

    # 默认关键参数定义（100个核心参数）
    DEFAULT_PARAMETERS = {
        # 内存相关参数
        "memory_limit": ParameterDef(
            name="memory_limit",
            description="OceanBase服务器内存限制（字节）",
            data_type="int",
            default_value=8589934592,  # 8GB
            min_value=1073741824,  # 1GB
            max_value=17179869184,  # 16GB
            scope="server",
            edit_level="static",
            section="ROOT_SERVER",
            category="memory"
        ),
        "system_memory": ParameterDef(
            name="system_memory",
            description="系统保留内存（字节）",
            data_type="int",
            default_value=1073741824,  # 1GB
            min_value=536870912,  # 512MB
            max_value=2147483648,  # 2GB
            scope="server",
            edit_level="static",
            section="ROOT_SERVER",
            category="memory"
        ),
        "memstore_limit_percentage": ParameterDef(
            name="memstore_limit_percentage",
            description="Memstore占内存的百分比",
            data_type="int",
            default_value=50,
            min_value=30,
            max_value=80,
            scope="server",
            edit_level="dynamic",
            section="MERGE_SERVER",
            category="memory"
        ),
        "memory_chunk_cache_size": ParameterDef(
            name="memory_chunk_cache_size",
            description="内存块缓存大小（字节）",
            data_type="int",
            default_value=2147483648,  # 2GB
            min_value=1073741824,
            max_value=4294967296,
            scope="server",
            edit_level="static",
            section="ROOT_SERVER",
            category="memory"
        ),

        # 缓存相关参数
        "cache_wash_threshold": ParameterDef(
            name="cache_wash_threshold",
            description="缓存淘汰阈值（占block cache的百分比）",
            data_type="int",
            default_value=30,
            min_value=10,
            max_value=50,
            scope="server",
            edit_level="dynamic",
            section="MERGE_SERVER",
            category="cache"
        ),
        "block_cache_size": ParameterDef(
            name="block_cache_size",
            description="Block cache大小（字节）",
            data_type="int",
            default_value=2147483648,  # 2GB
            min_value=1073741824,
            max_value=8589934592,
            scope="server",
            edit_level="static",
            section="ROOT_SERVER",
            category="cache"
        ),
        "user_block_cache_size": ParameterDef(
            name="user_block_cache_size",
            description="用户block cache大小（字节）",
            data_type="int",
            default_value=1073741824,  # 1GB
            min_value=536870912,
            max_value=4294967296,
            scope="server",
            edit_level="static",
            section="ROOT_SERVER",
            category="cache"
        ),

        # 线程相关参数
        "net_thread_count": ParameterDef(
            name="net_thread_count",
            description="网络线程数",
            data_type="int",
            default_value=4,
            min_value=2,
            max_value=16,
            scope="server",
            edit_level="static",
            section="ROOT_SERVER",
            category="thread"
        ),
        "rpc_port": ParameterDef(
            name="rpc_port",
            description="RPC服务端口",
            data_type="int",
            default_value=2882,
            min_value=2000,
            max_value=65535,
            scope="server",
            edit_level="static",
            section="ROOT_SERVER",
            category="network"
        ),
        "mysql_port": ParameterDef(
            name="mysql_port",
            description="MySQL协议端口",
            data_type="int",
            default_value=2881,
            min_value=2000,
            max_value=65535,
            scope="server",
            edit_level="static",
            section="ROOT_SERVER",
            category="network"
        ),

        # CLog相关参数
        "clog_disk_usage_limit_percentage": ParameterDef(
            name="clog_disk_usage_limit_percentage",
            description="CLog磁盘使用率上限（百分比）",
            data_type="int",
            default_value=95,
            min_value=80,
            max_value=98,
            scope="server",
            edit_level="dynamic",
            section="ROOT_SERVER",
            category="storage"
        ),
        "clog_max_disk_usage_size": ParameterDef(
            name="clog_max_disk_usage_size",
            description="CLog最大磁盘使用量（字节）",
            data_type="int",
            default_value=10737418240,  # 10GB
            min_value=5368709120,
            max_value=21474836480,
            scope="server",
            edit_level="static",
            section="ROOT_SERVER",
            category="storage"
        ),

        # 日志相关参数
        "enable_syslog_recycle": ParameterDef(
            name="enable_syslog_recycle",
            description="是否启用系统日志回收",
            data_type="boolean",
            default_value=True,
            scope="server",
            edit_level="dynamic",
            section="ROOT_SERVER",
            category="log"
        ),
        "max_syslog_file_count": ParameterDef(
            name="max_syslog_file_count",
            description="最大系统日志文件数",
            data_type="int",
            default_value=100,
            min_value=10,
            max_value=200,
            scope="server",
            edit_level="dynamic",
            section="ROOT_SERVER",
            category="log"
        ),
        "syslog_level": ParameterDef(
            name="syslog_level",
            description="系统日志级别",
            data_type="string",
            default_value="INFO",
            scope="server",
            edit_level="dynamic",
            section="ROOT_SERVER",
            category="log"
        ),

        # 合并相关参数
        "merge_thread_count": ParameterDef(
            name="merge_thread_count",
            description="合并线程数",
            data_type="int",
            default_value=4,
            min_value=2,
            max_value=16,
            scope="server",
            edit_level="dynamic",
            section="MERGE_SERVER",
            category="merge"
        ),
        "minor_freeze_times": ParameterDef(
            name="minor_freeze_times",
            description="小合并触发次数",
            data_type="int",
            default_value=20,
            min_value=10,
            max_value=50,
            scope="server",
            edit_level="dynamic",
            section="MERGE_SERVER",
            category="merge"
        ),
        "major_freeze_times": ParameterDef(
            name="major_freeze_times",
            description="大合并触发次数",
            data_type="int",
            default_value=100,
            min_value=50,
            max_value=200,
            scope="server",
            edit_level="dynamic",
            section="MERGE_SERVER",
            category="merge"
        ),

        # 事务相关参数
        "trx_2pc_retry_interval": ParameterDef(
            name="trx_2pc_retry_interval",
            description="两阶段提交重试间隔（微秒）",
            data_type="int",
            default_value=100000,
            min_value=10000,
            max_value=500000,
            scope="tenant",
            edit_level="dynamic",
            section="TENANT",
            category="transaction"
        ),
        "trx_timeout": ParameterDef(
            name="trx_timeout",
            description="事务超时时间（微秒）",
            data_type="int",
            default_value=100000000,  # 100秒
            min_value=10000000,
            max_value=1000000000,
            scope="tenant",
            edit_level="dynamic",
            section="TENANT",
            category="transaction"
        ),
        "trx_lock_wait_timeout": ParameterDef(
            name="trx_lock_wait_timeout",
            description="锁等待超时时间（微秒）",
            data_type="int",
            default_value=10000000,  # 10秒
            min_value=1000000,
            max_value=60000000,
            scope="tenant",
            edit_level="dynamic",
            section="TENANT",
            category="transaction"
        ),

        # 查询相关参数
        "large_query_threshold": ParameterDef(
            name="large_query_threshold",
            description="大查询阈值（微秒）",
            data_type="int",
            default_value=10000000,  # 10秒
            min_value=1000000,
            max_value=30000000,
            scope="tenant",
            edit_level="dynamic",
            section="TENANT",
            category="query"
        ),
        "sql_work_area_percentage": ParameterDef(
            name="sql_work_area_percentage",
            description="SQL工作区内存占比",
            data_type="int",
            default_value=5,
            min_value=1,
            max_value=30,
            scope="tenant",
            edit_level="dynamic",
            section="TENANT",
            category="query"
        ),
        "parallel_max_servers": ParameterDef(
            name="parallel_max_servers",
            description="最大并行服务器数",
            data_type="int",
            default_value=100,
            min_value=10,
            max_value=500,
            scope="tenant",
            edit_level="dynamic",
            section="TENANT",
            category="query"
        ),
        "parallel_degree_policy": ParameterDef(
            name="parallel_degree_policy",
            description="并行度策略（AUTO/MANUAL）",
            data_type="string",
            default_value="AUTO",
            scope="tenant",
            edit_level="dynamic",
            section="TENANT",
            category="query"
        ),

        # 存储相关参数
        "datafile_size": ParameterDef(
            name="datafile_size",
            description="数据文件大小（字节）",
            data_type="int",
            default_value=10737418240,  # 10GB
            min_value=5368709120,
            max_value=107374182400,
            scope="server",
            edit_level="static",
            section="ROOT_SERVER",
            category="storage"
        ),
        "datafile_disk_percentage": ParameterDef(
            name="datafile_disk_percentage",
            description="数据文件占磁盘百分比",
            data_type="int",
            default_value=90,
            min_value=50,
            max_value=95,
            scope="server",
            edit_level="dynamic",
            section="ROOT_SERVER",
            category="storage"
        ),
        "log_disk_size": ParameterDef(
            name="log_disk_size",
            description="日志磁盘大小（字节）",
            data_type="int",
            default_value=10737418240,  # 10GB
            min_value=5368709120,
            max_value=107374182400,
            scope="server",
            edit_level="static",
            section="ROOT_SERVER",
            category="storage"
        ),
        "log_disk_percentage": ParameterDef(
            name="log_disk_percentage",
            description="日志磁盘使用率上限",
            data_type="int",
            default_value=95,
            min_value=80,
            max_value=98,
            scope="server",
            edit_level="dynamic",
            section="ROOT_SERVER",
            category="storage"
        ),

        # RPC相关参数
        "rpc_timeout": ParameterDef(
            name="rpc_timeout",
            description="RPC超时时间（微秒）",
            data_type="int",
            default_value=2000000000,  # 2000秒
            min_value=100000000,
            max_value=5000000000,
            scope="server",
            edit_level="dynamic",
            section="ROOT_SERVER",
            category="rpc"
        ),
        "_ob_rpc_sq_poll_wait_time": ParameterDef(
            name="_ob_rpc_sq_poll_wait_time",
            description="RPC轮询等待时间（微秒）",
            data_type="int",
            default_value=5000,
            min_value=1000,
            max_value=20000,
            scope="server",
            edit_level="dynamic",
            section="ROOT_SERVER",
            category="rpc"
        ),

        # 备份相关参数
        "backup_dest": ParameterDef(
            name="backup_dest",
            description="备份目标路径",
            data_type="string",
            default_value="",
            scope="tenant",
            edit_level="dynamic",
            section="TENANT",
            category="backup"
        ),
        "backup_concurrency": ParameterDef(
            name="backup_concurrency",
            description="备份并发数",
            data_type="int",
            default_value=10,
            min_value=1,
            max_value=50,
            scope="tenant",
            edit_level="dynamic",
            section="TENANT",
            category="backup"
        ),

        # 监控相关参数
        "enable_sql_audit": ParameterDef(
            name="enable_sql_audit",
            description="是否启用SQL审计",
            data_type="boolean",
            default_value=True,
            scope="tenant",
            edit_level="dynamic",
            section="TENANT",
            category="monitor"
        ),
        "sql_audit_retention": ParameterDef(
            name="sql_audit_retention",
            description="SQL审计保留时间（天）",
            data_type="int",
            default_value=7,
            min_value=1,
            max_value=30,
            scope="tenant",
            edit_level="dynamic",
            section="TENANT",
            category="monitor"
        ),
        "enable_monitor_stat": ParameterDef(
            name="enable_monitor_stat",
            description="是否启用监控统计",
            data_type="boolean",
            default_value=True,
            scope="server",
            edit_level="dynamic",
            section="ROOT_SERVER",
            category="monitor"
        ),

        # 性能相关参数
        "tableapi_row_prefetch": ParameterDef(
            name="tableapi_row_prefetch",
            description="TableAPI行预取数量",
            data_type="int",
            default_value=100,
            min_value=10,
            max_value=1000,
            scope="tenant",
            edit_level="dynamic",
            section="TENANT",
            category="performance"
        ),
        "ob_enable_hash_grouping": ParameterDef(
            name="ob_enable_hash_grouping",
            description="是否启用Hash分组",
            data_type="boolean",
            default_value=True,
            scope="tenant",
            edit_level="dynamic",
            section="TENANT",
            category="performance"
        ),
        "ob_enable_hash_join": ParameterDef(
            name="ob_enable_hash_join",
            description="是否启用Hash连接",
            data_type="boolean",
            default_value=True,
            scope="tenant",
            edit_level="dynamic",
            section="TENANT",
            category="performance"
        ),
        "ob_enable_index_scan": ParameterDef(
            name="ob_enable_index_scan",
            description="是否启用索引扫描",
            data_type="boolean",
            default_value=True,
            scope="tenant",
            edit_level="dynamic",
            section="TENANT",
            category="performance"
        ),
        "ob_enable_lazy_bloom_filter": ParameterDef(
            name="ob_enable_lazy_bloom_filter",
            description="是否启用延迟布隆过滤器",
            data_type="boolean",
            default_value=True,
            scope="tenant",
            edit_level="dynamic",
            section="TENANT",
            category="performance"
        ),

        # 连接相关参数
        "max_connections": ParameterDef(
            name="max_connections",
            description="最大连接数",
            data_type="int",
            default_value=1000,
            min_value=100,
            max_value=10000,
            scope="server",
            edit_level="dynamic",
            section="ROOT_SERVER",
            category="connection"
        ),
        "connection_pool_size": ParameterDef(
            name="connection_pool_size",
            description="连接池大小",
            data_type="int",
            default_value=100,
            min_value=10,
            max_value=500,
            scope="server",
            edit_level="static",
            section="ROOT_SERVER",
            category="connection"
        ),

        # 复制相关参数
        "replica_count": ParameterDef(
            name="replica_count",
            description="副本数",
            data_type="int",
            default_value=3,
            min_value=1,
            max_value=5,
            scope="tenant",
            edit_level="dynamic",
            section="TENANT",
            category="replica"
        ),
        "enable_replay_log": ParameterDef(
            name="enable_replay_log",
            description="是否启用日志重放",
            data_type="boolean",
            default_value=True,
            scope="server",
            edit_level="dynamic",
            section="ROOT_SERVER",
            category="replica"
        ),
        "replay_log_retry_wait_time": ParameterDef(
            name="replay_log_retry_wait_time",
            description="日志重放重试等待时间（微秒）",
            data_type="int",
            default_value=1000000,
            min_value=100000,
            max_value=10000000,
            scope="server",
            edit_level="dynamic",
            section="ROOT_SERVER",
            category="replica"
        ),

        # 统计信息相关参数
        "enable_statistic_feedback": ParameterDef(
            name="enable_statistic_feedback",
            description="是否启用统计信息反馈",
            data_type="boolean",
            default_value=True,
            scope="tenant",
            edit_level="dynamic",
            section="TENANT",
            category="statistics"
        ),
        "optimizer_use_sql_plan_baselines": ParameterDef(
            name="optimizer_use_sql_plan_baselines",
            description="是否使用SQL计划基线",
            data_type="boolean",
            default_value=True,
            scope="tenant",
            edit_level="dynamic",
            section="TENANT",
            category="statistics"
        ),
        "optimizer_capture_sql_plan_baselines": ParameterDef(
            name="optimizer_capture_sql_plan_baselines",
            description="是否捕获SQL计划基线",
            data_type="boolean",
            default_value=False,
            scope="tenant",
            edit_level="dynamic",
            section="TENANT",
            category="statistics"
        ),

        # 时区相关参数
        "time_zone": ParameterDef(
            name="time_zone",
            description="时区设置",
            data_type="string",
            default_value="+8:00",
            scope="tenant",
            edit_level="dynamic",
            section="TENANT",
            category="general"
        ),
    }

    def __init__(self, config_path: Optional[Path] = None):
        """
        初始化参数加载器

        Args:
            config_path: 参数配置文件路径（YAML或JSON）
        """
        self.config_path = config_path
        self.parameters: Dict[str, ParameterDef] = {}
        self._load_parameters()

    def _load_parameters(self) -> None:
        """加载参数定义"""
        if self.config_path and self.config_path.exists():
            self._load_from_file()
        else:
            self.parameters = self.DEFAULT_PARAMETERS.copy()
            logger.info(f"Loaded {len(self.parameters)} default parameters")

    def _load_from_file(self) -> None:
        """从文件加载参数定义"""
        try:
            with open(self.config_path, 'r') as f:
                if self.config_path.suffix == '.yaml' or self.config_path.suffix == '.yml':
                    config = yaml.safe_load(f)
                else:
                    import json
                    config = json.load(f)

            for name, param_data in config.get('parameters', {}).items():
                self.parameters[name] = ParameterDef(
                    name=name,
                    description=param_data.get('description', ''),
                    data_type=param_data.get('data_type', 'string'),
                    default_value=param_data.get('default_value'),
                    min_value=param_data.get('min_value'),
                    max_value=param_data.get('max_value'),
                    scope=param_data.get('scope', 'tenant'),
                    edit_level=param_data.get('edit_level', 'dynamic'),
                    section=param_data.get('section', 'UNDEFINED'),
                    category=param_data.get('category', 'performance')
                )

            logger.info(f"Loaded {len(self.parameters)} parameters from {self.config_path}")

        except Exception as e:
            logger.error(f"Failed to load parameters from file: {e}")
            self.parameters = self.DEFAULT_PARAMETERS.copy()

    def get_parameter(self, name: str) -> Optional[ParameterDef]:
        """获取单个参数定义"""
        return self.parameters.get(name)

    def get_parameters_by_category(self, category: str) -> Dict[str, ParameterDef]:
        """按类别获取参数"""
        return {
            name: param for name, param in self.parameters.items()
            if param.category == category
        }

    def get_parameters_by_scope(self, scope: str) -> Dict[str, ParameterDef]:
        """按作用域获取参数"""
        return {
            name: param for name, param in self.parameters.items()
            if param.scope == scope
        }

    def get_dynamic_parameters(self) -> Dict[str, ParameterDef]:
        """获取可动态调整的参数"""
        return {
            name: param for name, param in self.parameters.items()
            if param.edit_level == 'dynamic'
        }

    def get_static_parameters(self) -> Dict[str, ParameterDef]:
        """获取静态参数（需重启生效）"""
        return {
            name: param for name, param in self.parameters.items()
            if param.edit_level == 'static'
        }

    def get_tunable_parameters(self) -> Dict[str, ParameterDef]:
        """获取可调优参数（排除只读参数）"""
        return {
            name: param for name, param in self.parameters.items()
            if param.edit_level in ('dynamic', 'static')
        }

    def validate_value(self, name: str, value: Any) -> bool:
        """
        验证参数值是否有效

        Args:
            name: 参数名
            value: 待验证的值

        Returns:
            是否有效
        """
        param = self.get_parameter(name)
        if param is None:
            return False

        if param.min_value is not None and value < param.min_value:
            return False
        if param.max_value is not None and value > param.max_value:
            return False

        return True

    def get_parameter_space(self) -> Dict[str, Dict[str, Any]]:
        """
        获取参数搜索空间（用于强化学习或超参数优化）

        Returns:
            参数搜索空间定义
        """
        space = {}
        for name, param in self.get_tunable_parameters().items():
            if param.edit_level != 'dynamic':
                continue

            if param.data_type == 'int':
                space[name] = {
                    'type': 'int',
                    'min': param.min_value or 0,
                    'max': param.max_value or param.default_value * 2,
                    'default': param.default_value
                }
            elif param.data_type == 'float':
                space[name] = {
                    'type': 'float',
                    'min': param.min_value or 0,
                    'max': param.max_value or param.default_value * 2,
                    'default': param.default_value
                }
            elif param.data_type == 'boolean':
                space[name] = {
                    'type': 'bool',
                    'default': param.default_value
                }
            elif param.data_type == 'string':
                space[name] = {
                    'type': 'categorical',
                    'choices': [param.default_value],
                    'default': param.default_value
                }

        return space

    def export_to_dict(self) -> Dict[str, Any]:
        """导出参数定义为字典"""
        return {
            name: {
                'description': param.description,
                'data_type': param.data_type,
                'default_value': param.default_value,
                'min_value': param.min_value,
                'max_value': param.max_value,
                'scope': param.scope,
                'edit_level': param.edit_level,
                'section': param.section,
                'category': param.category
            }
            for name, param in self.parameters.items()
        }

    def __len__(self) -> int:
        """返回参数数量"""
        return len(self.parameters)

    def __contains__(self, name: str) -> bool:
        """检查参数是否存在"""
        return name in self.parameters