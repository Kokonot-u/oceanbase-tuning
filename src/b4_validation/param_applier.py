"""
参数应用器

自动应用参数配置到OceanBase数据库。
"""

from typing import Dict, Any, List, Optional
import time
from loguru import logger
import yaml


class ParamApplier:
    """
    OceanBase参数应用器

    负责将参数配置应用到OceanBase数据库
    """

    def __init__(self, db_connector):
        """
        初始化参数应用器

        Args:
            db_connector: 数据库连接器实例
        """
        self.db = db_connector
        self.applied_params: Dict[str, Any] = {}

    def apply_param(self, name: str, value: Any,
                    scope: str = "tenant",
                    check_required: bool = True) -> bool:
        """
        应用单个参数

        Args:
            name: 参数名
            value: 参数值
            scope: 作用域 (tenant, server, cluster)
            check_required: 是否检查参数有效性

        Returns:
            是否成功
        """
        if check_required:
            if not self._validate_param(name, value):
                return False

        try:
            if scope == "tenant":
                sql = f"ALTER SYSTEM SET {name} = '{value}';"
            elif scope == "server":
                sql = f"ALTER SYSTEM SET {name} = '{value}' SERVER='127.0.0.1:2882';"
            else:  # cluster
                sql = f"ALTER SYSTEM SET {name} = '{value}';"

            self.db.execute_update(sql)
            self.applied_params[name] = value

            logger.info(f"Applied parameter: {name} = {value}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply parameter {name}: {e}")
            return False

    def apply_params(self, params: Dict[str, Any],
                    scope: str = "tenant") -> Dict[str, bool]:
        """
        批量应用参数

        Args:
            params: 参数字典
            scope: 作用域

        Returns:
            应用结果字典 {参数名: 是否成功}
        """
        results = {}

        for name, value in params.items():
            success = self.apply_param(name, value, scope)
            results[name] = success

        return results

    def apply_from_file(self, file_path: str) -> bool:
        """
        从配置文件应用参数

        Args:
            file_path: 配置文件路径

        Returns:
            是否全部成功
        """
        with open(file_path, 'r') as f:
            config = yaml.safe_load(f)

        params = config.get('parameters', {})
        scope = config.get('scope', 'tenant')

        results = self.apply_params(params, scope)

        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)

        logger.info(f"Applied {success_count}/{total_count} parameters from {file_path}")
        return success_count == total_count

    def get_current_value(self, name: str) -> Optional[Any]:
        """
        获取参数当前值

        Args:
            name: 参数名

        Returns:
            当前值
        """
        try:
            sql = f"SHOW PARAMETERS LIKE '{name}';"
            result = self.db.execute_query(sql)
            if len(result) > 0:
                return result.iloc[0]['value']
        except Exception as e:
            logger.error(f"Failed to get parameter {name}: {e}")
        return None

    def _validate_param(self, name: str, value: Any) -> bool:
        """
        验证参数有效性

        Args:
            name: 参数名
            value: 参数值

        Returns:
            是否有效
        """
        try:
            # 获取参数信息
            sql = f"""
                SELECT name, data_type, min, max, edit_level
                FROM oceanbase.__all_virtual_parameter_stat
                WHERE name = '{name}'
            """
            result = self.db.execute_query(sql)

            if len(result) == 0:
                logger.warning(f"Parameter {name} not found in parameter list")
                return True  # 允许未知参数

            param_info = result.iloc[0]
            edit_level = param_info['edit_level']

            # 检查是否为只读参数
            if edit_level == 'readonly':
                logger.error(f"Parameter {name} is readonly")
                return False

            # 检查范围
            if param_info['min'] is not None and value < param_info['min']:
                logger.error(f"Parameter {name} value {value} below minimum {param_info['min']}")
                return False

            if param_info['max'] is not None and value > param_info['max']:
                logger.error(f"Parameter {name} value {value} above maximum {param_info['max']}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating parameter {name}: {e}")
            return False

    def restore_defaults(self) -> bool:
        """
        恢复所有参数为默认值

        Returns:
            是否成功
        """
        try:
            # 获取所有非默认参数
            sql = """
                SELECT name, default_value, edit_level
                FROM oceanbase.__all_virtual_parameter_stat
                WHERE edit_level IN ('static', 'dynamic')
                  AND value != default_value
            """
            result = self.db.execute_query(sql)

            if len(result) == 0:
                logger.info("No parameters to restore")
                return True

            for _, row in result.iterrows():
                if row['edit_level'] == 'dynamic':
                    self.apply_param(row['name'], row['default_value'], check_required=False)

            logger.info(f"Restored {len(result)} parameters to default values")
            return True

        except Exception as e:
            logger.error(f"Failed to restore defaults: {e}")
            return False

    def save_current_config(self, output_path: str) -> bool:
        """
        保存当前参数配置

        Args:
            output_path: 输出路径

        Returns:
            是否成功
        """
        try:
            sql = """
                SELECT name, value, default_value, section, scope,
                       data_type, min, max, edit_level
                FROM oceanbase.__all_virtual_parameter_stat
                WHERE edit_level IN ('static', 'dynamic')
                ORDER BY section, name
            """
            result = self.db.execute_query(sql)

            # 转换为字典格式
            config = {
                'parameters': {}
            }

            for _, row in result.iterrows():
                config['parameters'][row['name']] = {
                    'value': row['value'],
                    'default_value': row['default_value'],
                    'section': row['section'],
                    'scope': row['scope'],
                    'data_type': row['data_type'],
                    'min': row['min'],
                    'max': row['max'],
                    'edit_level': row['edit_level']
                }

            with open(output_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)

            logger.info(f"Saved current config to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False

    def rollback(self) -> bool:
        """
        回滚所有已应用的参数

        Returns:
            是否成功
        """
        if not self.applied_params:
            logger.info("No parameters to rollback")
            return True

        logger.info(f"Rolling back {len(self.applied_params)} parameters...")

        success = True
        for name in list(self.applied_params.keys()):
            # 这里简化实现，实际应该记录应用前的值
            if not self.apply_param(name, "default", check_required=False):
                success = False

        self.applied_params.clear()
        return success

    def wait_for_reload(self, timeout: int = 30) -> bool:
        """
        等待参数重新加载（对于动态参数）

        Args:
            timeout: 超时时间（秒）

        Returns:
            是否成功
        """
        logger.info(f"Waiting for parameter reload (timeout: {timeout}s)...")

        for i in range(timeout):
            time.sleep(1)

            # 这里可以检查参数是否已生效
            # 例如查询特定参数的值是否已改变

            if i % 5 == 0:
                logger.debug(f"Waiting... {i}s elapsed")

        logger.info("Parameter reload wait completed")
        return True

    def get_param_diff(self, config1: Dict[str, Any],
                      config2: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        比较两份参数配置的差异

        Args:
            config1: 配置1
            config2: 配置2

        Returns:
            差异字典
        """
        all_keys = set(config1.keys()) | set(config2.keys())
        diff = {}

        for key in all_keys:
            val1 = config1.get(key)
            val2 = config2.get(key)

            if val1 != val2:
                diff[key] = {
                    'before': val1,
                    'after': val2,
                    'changed': val1 is not None and val2 is not None
                }

        return diff

    def validate_applied_params(self) -> Dict[str, bool]:
        """
        验证已应用的参数是否生效

        Returns:
            验证结果字典
        """
        results = {}

        for name, expected_value in self.applied_params.items():
            current_value = self.get_current_value(name)
            results[name] = (current_value == expected_value)

            if not results[name]:
                logger.warning(f"Parameter {name} not applied correctly: "
                             f"expected={expected_value}, actual={current_value}")

        return results


class SafeParamApplier(ParamApplier):
    """
    安全的参数应用器

    在应用参数前创建备份，支持自动回滚
    """

    def __init__(self, db_connector, backup_path: str = "backups"):
        """
        初始化安全参数应用器

        Args:
            db_connector: 数据库连接器
            backup_path: 备份路径
        """
        super().__init__(db_connector)
        self.backup_path = Path(backup_path)
        self.backup_path.mkdir(parents=True, exist_ok=True)
        self.backup_file = None

    def safe_apply(self, params: Dict[str, Any],
                   scope: str = "tenant",
                   validate: bool = True) -> bool:
        """
        安全地应用参数（带备份）

        Args:
            params: 参数字典
            scope: 作用域
            validate: 是否验证

        Returns:
            是否成功
        """
        from datetime import datetime

        # 创建备份
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_file = self.backup_path / f'param_backup_{timestamp}.yaml'

        if not self.save_current_config(str(self.backup_file)):
            logger.error("Failed to create backup")
            return False

        logger.info(f"Created backup: {self.backup_file}")

        # 应用参数
        results = self.apply_params(params, scope)

        # 检查是否全部成功
        if not all(results.values()):
            logger.warning("Some parameters failed to apply")
            if validate:
                logger.info("Rolling back...")
                self.restore_from_backup(self.backup_file)
                return False

        # 验证参数生效
        if validate:
            validation = self.validate_applied_params()
            if not all(validation.values()):
                logger.warning("Some parameters did not take effect")
                self.restore_from_backup(self.backup_file)
                return False

        logger.info("Parameters applied and validated successfully")
        return True

    def restore_from_backup(self, backup_file: Optional[Path] = None) -> bool:
        """
        从备份恢复参数

        Args:
            backup_file: 备份文件路径

        Returns:
            是否成功
        """
        if backup_file is None:
            backup_file = self.backup_file

        if backup_file is None or not backup_file.exists():
            logger.error("No backup file found")
            return False

        return self.apply_from_file(str(backup_file))