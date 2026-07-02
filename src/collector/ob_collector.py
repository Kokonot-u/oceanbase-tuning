"""
OceanBase性能数据采集器

从OceanBase系统表采集性能数据，包括：
- 系统资源使用情况（CPU、内存、IO、网络）
- SQL执行统计
- 慢查询日志
- 锁等待信息
"""

from typing import Optional, Dict, List
import pandas as pd
from loguru import logger


class OBCollector:
    """OceanBase性能数据采集器"""

    # 系统资源查询SQL
    CPU_USAGE_SQL = """
        SELECT
            svr_ip,
            svr_port,
            cpu_usage,
            cpu_time_in_us,
            iops,
            iops_read,
            iops_write,
            io_size,
            io_read_bytes,
            io_write_bytes
        FROM oceanbase.__all_virtual_server_stat
        WHERE svr_ip IS NOT NULL
        ORDER BY svr_ip, svr_port
    """

    MEMORY_USAGE_SQL = """
        SELECT
            svr_ip,
            svr_port,
            mem_total,
            mem_used,
            mem_limit,
            hold,
            usage
        FROM oceanbase.__all_virtual_memory_info
        WHERE svr_ip IS NOT NULL
        ORDER BY svr_ip, svr_port
    """

    # SQL执行统计
    SQL_STATS_SQL = """
        SELECT
            tenant_id,
            plan_id,
            plan_hash,
            sql_id,
            server,
            type,
            execute_times,
            elapsed_time,
            cpu_time,
            io_time,
            round_trip_time,
            affect_rows,
            mem_used,
            retry_times
        FROM oceanbase.__all_virtual_sql_workarea_history_stat
        WHERE execute_times > 0
        ORDER BY execute_times DESC
        LIMIT 1000
    """

    # 慢查询
    SLOW_QUERY_SQL = """
        SELECT
            tenant_id,
            user_id,
            database_id,
            query_sql,
            plan_id,
            affect_rows,
            return_rows,
            ret_code,
            elapsed_time,
            cpu_time,
            io_time,
            execute_times,
            query_retry_times,
            table_scan,
            memstore_read_row_count,
            ssstore_read_row_count,
            rpc_count
        FROM oceanbase.gv$sql_audit
        WHERE elapsed_time > 1000000  # 超过1秒
        ORDER BY elapsed_time DESC
        LIMIT 100
    """

    # 锁等待
    LOCK_WAIT_SQL = """
        SELECT
            tenant_id,
            svr_ip,
            svr_port,
            addr,
            tenant_id,
            user_id,
            db_id,
            table_id,
            mode,
            type,
            key_id,
            lock_id,
            create_trans_id,
            create_stmt_id,
            block_trans_id,
            expire_time
        FROM oceanbase.__all_virtual_lock_wait_stat
        WHERE 1=1
        ORDER BY expire_time DESC
        LIMIT 100
    """

    # 配置参数
    PARAM_SQL = """
        SELECT
            tenant_id,
            zone,
            svr_type,
            name,
            value,
            data_type,
            section,
            scope,
            source,
            edit_level,
            default_value,
            min,
            max,
            info
        FROM oceanbase.__all_virtual_parameter_stat
        WHERE edit_level IN ('static', 'dynamic')
        ORDER BY name
    """

    def __init__(self, db_connector):
        """
        初始化采集器

        Args:
            db_connector: 数据库连接器实例
        """
        self.db = db_connector

    def collect_cpu_usage(self) -> Optional[pd.DataFrame]:
        """采集CPU使用情况"""
        try:
            df = self.db.execute_query(self.CPU_USAGE_SQL)
            logger.info(f"Collected CPU usage data: {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Failed to collect CPU usage: {e}")
            return None

    def collect_memory_usage(self) -> Optional[pd.DataFrame]:
        """采集内存使用情况"""
        try:
            df = self.db.execute_query(self.MEMORY_USAGE_SQL)
            logger.info(f"Collected memory usage data: {len(df)} rows")
            return df
        except None
        except Exception as e:
            logger.error(f"Failed to collect memory usage: {e}")
            return None

    def collect_sql_stats(self) -> Optional[pd.DataFrame]:
        """采集SQL执行统计"""
        try:
            df = self.db.execute_query(self.SQL_STATS_SQL)
            logger.info(f"Collected SQL stats: {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Failed to collect SQL stats: {e}")
            return None

    def collect_slow_queries(self, limit: int = 100) -> Optional[pd.DataFrame]:
        """
        采集慢查询

        Args:
            limit: 返回记录数
        """
        try:
            sql = self.SLOW_QUERY_SQL.replace("LIMIT 100", f"LIMIT {limit}")
            df = self.db.execute_query(sql)
            logger.info(f"Collected slow queries: {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Failed to collect slow queries: {e}")
            return None

    def collect_lock_waits(self, limit: int = 100) -> Optional[pd.DataFrame]:
        """
        采集锁等待信息

        Args:
            limit: 返回记录数
        """
        try:
            sql = self.LOCK_WAIT_SQL.replace("LIMIT 100", f"LIMIT {limit}")
            df = self.db.execute_query(sql)
            logger.info(f"Collected lock waits: {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Failed to collect lock waits: {e}")
            return None

    def collect_parameters(self) -> Optional[pd.DataFrame]:
        """采集配置参数"""
        try:
            df = self.db.execute_query(self.PARAM_SQL)
            logger.info(f"Collected parameters: {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Failed to collect parameters: {e}")
            return None

    def collect_performance_metrics(self) -> Dict[str, pd.DataFrame]:
        """
        采集所有性能指标

        Returns:
            包含各类性能指标的字典
        """
        metrics = {
            "cpu_usage": self.collect_cpu_usage(),
            "memory_usage": self.collect_memory_usage(),
            "sql_stats": self.collect_sql_stats(),
            "slow_queries": self.collect_slow_queries(),
            "lock_waits": self.collect_lock_waits(),
            "parameters": self.collect_parameters(),
        }
        return metrics

    def collect_io_stats(self) -> Optional[pd.DataFrame]:
        """采集IO统计信息"""
        sql = """
            SELECT
                svr_ip,
                svr_port,
                disk_total,
                disk_used,
                disk_percent,
                data_disk_total,
                data_disk_used,
                data_disk_percent,
                log_disk_total,
                log_disk_used,
                log_disk_percent
            FROM oceanbase.__all_virtual_server_disk_stat
            ORDER BY svr_ip, svr_port
        """
        try:
            df = self.db.execute_query(sql)
            logger.info(f"Collected IO stats: {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Failed to collect IO stats: {e}")
            return None

    def collect_network_stats(self) -> Optional[pd.DataFrame]:
        """采集网络统计信息"""
        sql = """
            SELECT
                svr_ip,
                svr_port,
                interface,
                ip,
                net_speed_in,
                net_speed_out,
                net_packet_in,
                net_packet_out,
                net_err_in,
                net_err_out
            FROM oceanbase.__all_virtual_network_stat
            ORDER BY svr_ip, svr_port
        """
        try:
            df = self.db.execute_query(sql)
            logger.info(f"Collected network stats: {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Failed to collect network stats: {e}")
            return None