"""
OceanBase数据库连接器

提供PyMySQL连接封装，支持上下文管理器。
"""

from typing import Optional, Any, List, Dict
import pymysql
import pandas as pd
import yaml
from pathlib import Path
from loguru import logger


class DBConnector:
    """
    OceanBase数据库连接器

    从config/db_config.yaml读取配置，提供数据库操作功能
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化连接器

        Args:
            config_path: 配置文件路径，默认为 config/db_config.yaml
        """
        if config_path is None:
            # 默认配置路径（相对于项目根目录）
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / 'config' / 'db_config.yaml'

        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.connection: Optional[pymysql.Connection] = None

    def _load_config(self) -> Dict[str, str]:
        """
        加载数据库配置

        Returns:
            配置字典
        """
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)

            # 验证必需配置
            required_keys = ['host', 'port', 'user', 'password', 'database']
            for key in required_keys:
                if key not in config or not config[key]:
                    raise ValueError(f"Missing required config: {key}")

            logger.info(f"Loaded config from {self.config_path}")
            return config

        except FileNotFoundError:
            logger.error(f"Config file not found: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse config: {e}")
            raise

    def connect(self) -> pymysql.Connection:
        """
        建立数据库连接

        Returns:
            MySQL连接对象
        """
        if self.connection is not None and self.connection.open:
            logger.debug("Connection already exists")
            return self.connection

        try:
            self.connection = pymysql.connect(
                host=self.config['host'],
                port=int(self.config['port']),
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                charset=self.config.get('charset', 'utf8mb4'),
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=30,
                read_timeout=300,
                write_timeout=300,
            )

            logger.info(f"Connected to OceanBase at {self.config['host']}:{self.config['port']}")
            return self.connection

        except pymysql.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def execute_query(self, sql: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """
        执行查询并返回DataFrame

        Args:
            sql: SQL语句
            params: 查询参数

        Returns:
            结果DataFrame
        """
        if self.connection is None or not self.connection.open:
            self.connect()

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params or ())
                result = cursor.fetchall()

            df = pd.DataFrame(result)
            logger.debug(f"Query returned {len(df)} rows")
            return df

        except pymysql.Error as e:
            logger.error(f"Query failed: {e}")
            logger.error(f"SQL: {sql}")
            raise

    def execute_update(self, sql: str, params: Optional[tuple] = None) -> int:
        """
        执行INSERT/UPDATE/DELETE语句

        Args:
            sql: SQL语句
            params: 查询参数

        Returns:
            影响的行数
        """
        if self.connection is None or not self.connection.open:
            self.connect()

        try:
            with self.connection.cursor() as cursor:
                affected_rows = cursor.execute(sql, params or ())
                self.connection.commit()

            logger.debug(f"Update affected {affected_rows} rows")
            return affected_rows

        except pymysql.Error as e:
            logger.error(f"Update failed: {e}")
            logger.error(f"SQL: {sql}")
            self.connection.rollback()
            raise

    def execute_batch(self, sql: str, params_list: List[tuple]) -> int:
        """
        批量执行语句

        Args:
            sql: SQL语句
            params_list: 参数列表

        Returns:
            影响的总行数
        """
        if self.connection is None or not self.connection.open:
            self.connect()

        try:
            with self.connection.cursor() as cursor:
                affected_rows = cursor.executemany(sql, params_list)
                self.connection.commit()

            logger.debug(f"Batch update affected {affected_rows} rows")
            return affected_rows

        except pymysql.Error as e:
            logger.error(f"Batch update failed: {e}")
            self.connection.rollback()
            raise

    def execute_transaction(self, statements: List[str]) -> bool:
        """
        执行事务（多条语句）

        Args:
            statements: SQL语句列表

        Returns:
            是否成功
        """
        if self.connection is None or not self.connection.open:
            self.connect()

        try:
            with self.connection.cursor() as cursor:
                for sql in statements:
                    cursor.execute(sql)
                self.connection.commit()

            logger.debug(f"Transaction executed with {len(statements)} statements")
            return True

        except pymysql.Error as e:
            logger.error(f"Transaction failed: {e}")
            self.connection.rollback()
            return False

    def get_table_info(self, table_name: str) -> pd.DataFrame:
        """
        获取表信息

        Args:
            table_name: 表名

        Returns:
            表信息DataFrame
        """
        sql = f"DESCRIBE {table_name};"
        return self.execute_query(sql)

    def get_tables(self) -> pd.DataFrame:
        """
        获取所有表

        Returns:
            表列表DataFrame
        """
        sql = "SHOW TABLES;"
        return self.execute_query(sql)

    def get_schema(self) -> Dict[str, pd.DataFrame]:
        """
        获取数据库schema

        Returns:
            schema字典 {表名: 列信息}
        """
        tables_df = self.get_tables()
        table_name_col = tables_df.columns[0]

        schema = {}
        for _, row in tables_df.iterrows():
            table_name = row[table_name_col]
            schema[table_name] = self.get_table_info(table_name)

        return schema

    def test_connection(self) -> bool:
        """
        测试数据库连接

        Returns:
            是否连接成功
        """
        try:
            result = self.execute_query("SELECT 1 as test;")
            return len(result) == 1 and result.iloc[0]['test'] == 1
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def close(self) -> None:
        """关闭数据库连接"""
        if self.connection is not None and self.connection.open:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")

    def is_connected(self) -> bool:
        """
        检查连接是否有效

        Returns:
            连接是否有效
        """
        if self.connection is None:
            return False

        try:
            self.connection.ping(reconnect=False)
            return True
        except:
            return False

    def __enter__(self):
        """进入上下文管理器"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器"""
        self.close()
        return False

    def __del__(self):
        """析构函数"""
        self.close()

    @property
    def host(self) -> str:
        return self.config['host']

    @property
    def port(self) -> int:
        return int(self.config['port'])

    @property
    def user(self) -> str:
        return self.config['user']

    @property
    def database(self) -> str:
        return self.config['database']


class ConnectionPool:
    """
    数据库连接池

    管理多个数据库连接
    """

    def __init__(self, config_path: Optional[str] = None,
                 pool_size: int = 5):
        """
        初始化连接池

        Args:
            config_path: 配置文件路径
            pool_size: 连接池大小
        """
        self.config_path = config_path
        self.pool_size = pool_size
        self._pool: List[pymysql.Connection] = []
        self._available: List[bool] = [False] * pool_size

    def _create_connection(self, index: int) -> pymysql.Connection:
        """创建单个连接"""
        connector = DBConnector(self.config_path)
        return connector.connect()

    def get_connection(self, index: int = 0) -> pymysql.Connection:
        """
        获取连接

        Args:
            index: 连接索引

        Returns:
            数据库连接
        """
        if not 0 <= index < self.pool_size:
            raise IndexError(f"Connection index out of range: {index}")

        if self._pool[index] is None or not self._pool[index].open:
            self._pool[index] = self._create_connection(index)

        return self._pool[index]

    def release_connection(self, index: int) -> None:
        """
        释放连接

        Args:
            index: 连接索引
        """
        self._available[index] = True

    def close_all(self) -> None:
        """关闭所有连接"""
        for conn in self._pool:
            if conn and conn.open:
                conn.close()
        self._pool = []
        self._available = []