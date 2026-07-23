"""
测试数据库连接器
"""

import pytest
import pandas as pd
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from utils.db_conn import DBConnector


class TestDBConnector:
    """数据库连接器测试"""

    @pytest.fixture
    def sample_config(self, tmp_path):
        """创建测试配置文件"""
        config_path = tmp_path / 'db_config.yaml'
        config_content = """
host: "127.0.0.1"
port: 2881
user: "root@sys"
password: "test_password"
database: "oceanbase"
charset: utf8mb4
"""
        config_path.write_text(config_content)
        return str(config_path)

    def test_load_config(self, sample_config):
        """测试配置加载"""
        connector = DBConnector(sample_config)
        assert connector.config['host'] == '127.0.0.1'
        assert connector.config['port'] == '2881'
        assert connector.config['user'] == 'root@sys'
        assert connector.config['database'] == 'oceanbase'

    def test_missing_config_file(self):
        """测试缺少配置文件"""
        with pytest.raises(FileNotFoundError):
            DBConnector('nonexistent_config.yaml')

    def test_invalid_config(self, tmp_path):
        """测试无效配置"""
        config_path = tmp_path / 'invalid_config.yaml'
        config_path.write_text("invalid: yaml: content")

        with pytest.raises(Exception):  # YAML解析错误或验证错误
            DBConnector(str(config_path))

    def test_missing_required_field(self, tmp_path):
        """测试缺少必需字段"""
        config_path = tmp_path / 'incomplete_config.yaml'
        config_path.write_text("""
host: "127.0.0.1"
port: 2881
# 缺少user, password, database
""")

        with pytest.raises(ValueError, match="Missing required config"):
            DBConnector(str(config_path))

    @pytest.mark.skip(reason="需要实际的OceanBase实例")
    def test_connect_and_query(self, sample_config):
        """测试连接和查询（需要实际数据库）"""
        connector = DBConnector(sample_config)
        connector.connect()

        # 测试简单查询
        result = connector.execute_query("SELECT 1 as test;")
        assert len(result) == 1
        assert result.iloc[0]['test'] == 1

        connector.close()

    @pytest.mark.skip(reason="需要实际的OceanBase实例")
    def test_context_manager(self, sample_config):
        """测试上下文管理器"""
        with DBConnector(sample_config) as conn:
            result = conn.execute_query("SELECT VERSION() as version;")
            assert len(result) == 1

        # 确保连接已关闭
        assert conn.connection is None

    def test_properties(self, sample_config):
        """测试属性访问"""
        connector = DBConnector(sample_config)
        assert connector.host == '127.0.0.1'
        assert connector.port == 2881
        assert connector.user == 'root@sys'
        assert connector.database == 'oceanbase'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])