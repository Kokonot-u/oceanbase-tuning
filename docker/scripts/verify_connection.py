#!/usr/bin/env python3
"""
OceanBase 连接验证脚本

验证OceanBase单节点集群是否正常工作，包括：
- 版本检查
- 数据库列表
- 节点状态
- 系统统计
"""

import sys
import pymysql
import pandas as pd
from typing import Optional, List, Dict, Any


class OceanBaseVerifier:
    """OceanBase连接验证器"""

    def __init__(self, host: str = "127.0.0.1",
                 port: int = 2881,
                 user: str = "root",
                 password: str = "",
                 database: str = "oceanbase"):
        """
        初始化验证器

        Args:
            host: 主机地址
            port: SQL端口
            user: 用户名（格式：user@tenant）
            password: 密码
            database: 数据库名
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection: Optional[pymysql.Connection] = None

    def connect(self) -> bool:
        """
        连接到OceanBase

        Returns:
            是否连接成功
        """
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=30
            )
            print(f"✓ 成功连接到 OceanBase: {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"✗ 连接失败: {e}")
            return False

    def execute_query(self, sql: str, description: str) -> Optional[pd.DataFrame]:
        """
        执行查询并打印结果

        Args:
            sql: SQL语句
            description: 查询描述

        Returns:
            查询结果DataFrame
        """
        print(f"\n{'='*60}")
        print(f"测试: {description}")
        print(f"{'='*60}")
        print(f"SQL: {sql}\n")

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                result = cursor.fetchall()

            if not result:
                print("✓ 查询成功，但无结果")
                return None

            # 转换为DataFrame
            df = pd.DataFrame(result)

            # 打印结果
            print(f"✓ 查询成功，返回 {len(df)} 行结果")
            print("\n结果:")
            print(df.to_string(index=False))
            print()

            return df

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            return None

    def test_version(self) -> bool:
        """测试版本查询"""
        result = self.execute_query(
            "SELECT version() as version;",
            "查询OceanBase版本"
        )
        return result is not None

    def test_databases(self) -> bool:
        """测试数据库列表"""
        result = self.execute_query(
            "SHOW DATABASES;",
            "列出所有数据库"
        )
        return result is not None

    def test_server_status(self) -> bool:
        """测试服务器状态"""
        result = self.execute_query(
            "SELECT svr_ip, svr_port, zone, status, build_version "
            "FROM oceanbase.DBA_OB_SERVERS;",
            "查询服务器状态（DBA_OB_SERVERS）"
        )

        if result is not None:
            # 检查状态是否为ACTIVE
            status = result['status'].values[0] if len(result) > 0 else None
            if status and status.upper() == 'ACTIVE':
                print("✓ 服务器状态为 ACTIVE")
                return True
            else:
                print(f"⚠ 服务器状态: {status} (期望: ACTIVE)")
                return False

        return False

    def test_sysstat(self) -> bool:
        """测试系统统计"""
        result = self.execute_query(
            "SELECT name, value "
            "FROM oceanbase.v$sysstat "
            "WHERE name IN ('DB CPU', 'io read bytes', 'io read count') "
            "LIMIT 5;",
            "查询系统统计（v$sysstat）"
        )
        return result is not None

    def test_parameters(self) -> bool:
        """测试参数查询"""
        result = self.execute_query(
            "SELECT NAME, VALUE, DATA_TYPE, EDIT_LEVEL "
            "FROM oceanbase.GV$OB_PARAMETERS "
            "WHERE EDIT_LEVEL != 'READONLY' "
            "LIMIT 10;",
            "查询可配置参数（GV$OB_PARAMETERS）"
        )
        return result is not None

    def test_connection_pool(self) -> bool:
        """测试连接池信息"""
        result = self.execute_query(
            "SELECT COUNT(*) as connection_count "
            "FROM oceanbase.v$ob_session;",
            "查询当前连接数（v$ob_session）"
        )
        return result is not None

    def run_all_tests(self) -> bool:
        """
        运行所有验证测试

        Returns:
            所有测试是否通过
        """
        print("\n" + "="*60)
        print("OceanBase 单节点部署验证")
        print("="*60)

        # 连接测试
        if not self.connect():
            return False

        # 运行各项测试
        tests = [
            ("版本查询", self.test_version),
            ("数据库列表", self.test_databases),
            ("服务器状态", self.test_server_status),
            ("系统统计", self.test_sysstat),
            ("参数查询", self.test_parameters),
            ("连接信息", self.test_connection_pool),
        ]

        results = {}
        for name, test_func in tests:
            results[name] = test_func()

        # 打印总结
        print("\n" + "="*60)
        print("验证总结")
        print("="*60)

        for name, passed in results.items():
            status = "✓ 通过" if passed else "✗ 失败"
            print(f"{status} | {name}")

        all_passed = all(results.values())

        print("\n" + "="*60)
        if all_passed:
            print("✓ OceanBase单节点部署验证成功！")
            print("="*60)
            print("\n可以开始使用OceanBase了。")
            print("\n提示：将以下配置填入 config/db_config.yaml：")
            print(f"  host: \"{self.host}\"")
            print(f"  port: {self.port}")
            print(f"  user: \"{self.user}\"")
            print(f"  password: \"{self.password}\"")
            print(f"  database: \"{self.database}\"")
        else:
            print("✗ 部分验证失败，请检查OceanBase集群状态")
            print("="*60)
            print("\n调试命令：")
            print("  docker exec -it ob-node bash")
            print("  obd cluster display obcluster")

        print("="*60)

        return all_passed

    def close(self):
        """关闭连接"""
        if self.connection:
            self.connection.close()
            print("\n连接已关闭")


def main():
    """主函数"""
    # TODO: 根据实际部署情况修改连接信息
    verifier = OceanBaseVerifier(
        host="127.0.0.1",
        port=2881,
        user="root@sys",  # OceanBase默认root用户在sys租户
        database="oceanbase"
    )

    try:
        success = verifier.run_all_tests()
        sys.exit(0 if success else 1)
    finally:
        verifier.close()


if __name__ == "__main__":
    main()
