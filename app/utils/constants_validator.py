"""
鲸落 - 常量验证器
验证常量值的有效性和范围
"""

import re
from typing import Any, Dict, List, Tuple, Union

from app.constants import (
    CacheKeys,
    DangerousPatterns,
    DefaultConfig,
    ErrorMessages,
    FieldLengths,
    LogLevel,
    LogType,
    Pagination,
    RegexPatterns,
    SuccessMessages,
    SyncType,
    SystemConstants,
    TaskStatus,
    TimeFormats,
    UserRole,
)


class ConstantsValidator:
    """常量验证器"""

    def __init__(self):
        """初始化常量验证器"""
        self.validation_rules = self._build_validation_rules()
        self.validation_errors = []

    def _build_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """
        构建验证规则

        Returns:
            Dict: 验证规则字典
        """
        return {
            # 分页相关常量
            "DEFAULT_PAGE_SIZE": {
                "type": int,
                "min_value": 1,
                "max_value": 1000,
                "description": "默认分页大小"
            },
            "MAX_PAGE_SIZE": {
                "type": int,
                "min_value": 1,
                "max_value": 10000,
                "description": "最大分页大小"
            },
            "MIN_PAGE_SIZE": {
                "type": int,
                "min_value": 1,
                "max_value": 100,
                "description": "最小分页大小"
            },
            
            # 密码相关常量
            "MIN_PASSWORD_LENGTH": {
                "type": int,
                "min_value": 6,
                "max_value": 50,
                "description": "最小密码长度"
            },
            "MAX_PASSWORD_LENGTH": {
                "type": int,
                "min_value": 8,
                "max_value": 256,
                "description": "最大密码长度"
            },
            "PASSWORD_HASH_ROUNDS": {
                "type": int,
                "min_value": 10,
                "max_value": 20,
                "description": "密码哈希轮数"
            },
            
            # 缓存相关常量
            "DEFAULT_CACHE_TIMEOUT": {
                "type": int,
                "min_value": 1,
                "max_value": 86400,
                "description": "默认缓存超时时间（秒）"
            },
            "LONG_CACHE_TIMEOUT": {
                "type": int,
                "min_value": 1,
                "max_value": 604800,
                "description": "长缓存超时时间（秒）"
            },
            "SHORT_CACHE_TIMEOUT": {
                "type": int,
                "min_value": 1,
                "max_value": 3600,
                "description": "短缓存超时时间（秒）"
            },
            
            # 数据库连接相关常量
            "CONNECTION_TIMEOUT": {
                "type": int,
                "min_value": 1,
                "max_value": 300,
                "description": "数据库连接超时时间（秒）"
            },
            "QUERY_TIMEOUT": {
                "type": int,
                "min_value": 1,
                "max_value": 3600,
                "description": "数据库查询超时时间（秒）"
            },
            "MAX_CONNECTIONS": {
                "type": int,
                "min_value": 1,
                "max_value": 1000,
                "description": "最大数据库连接数"
            },
            "CONNECTION_RETRY_ATTEMPTS": {
                "type": int,
                "min_value": 1,
                "max_value": 10,
                "description": "数据库连接重试次数"
            },
            
            # 速率限制相关常量
            "RATE_LIMIT_REQUESTS": {
                "type": int,
                "min_value": 1,
                "max_value": 100000,
                "description": "速率限制请求数"
            },
            "RATE_LIMIT_WINDOW": {
                "type": int,
                "min_value": 1,
                "max_value": 3600,
                "description": "速率限制时间窗口（秒）"
            },
            
            # 日志相关常量
            "LOG_MAX_SIZE": {
                "type": int,
                "min_value": 1024,
                "max_value": 1073741824,  # 1GB
                "description": "日志文件最大大小（字节）"
            },
            "LOG_BACKUP_COUNT": {
                "type": int,
                "min_value": 1,
                "max_value": 100,
                "description": "日志备份文件数量"
            },
            "LOG_RETENTION_DAYS": {
                "type": int,
                "min_value": 1,
                "max_value": 365,
                "description": "日志保留天数"
            },
            
            # JWT相关常量
            "JWT_ACCESS_TOKEN_EXPIRES": {
                "type": int,
                "min_value": 60,
                "max_value": 86400,
                "description": "JWT访问令牌过期时间（秒）"
            },
            "JWT_REFRESH_TOKEN_EXPIRES": {
                "type": int,
                "min_value": 3600,
                "max_value": 2592000,
                "description": "JWT刷新令牌过期时间（秒）"
            },
            
            # 会话相关常量
            "SESSION_LIFETIME": {
                "type": int,
                "min_value": 60,
                "max_value": 86400,
                "description": "会话生命周期（秒）"
            },
            "REMEMBER_ME_LIFETIME": {
                "type": int,
                "min_value": 3600,
                "max_value": 2592000,
                "description": "记住我功能生命周期（秒）"
            },
            
            # 重试相关常量
            "MAX_RETRY_ATTEMPTS": {
                "type": int,
                "min_value": 1,
                "max_value": 10,
                "description": "最大重试次数"
            },
            "RETRY_BASE_DELAY": {
                "type": float,
                "min_value": 0.1,
                "max_value": 60.0,
                "description": "重试基础延迟时间（秒）"
            },
            "RETRY_MAX_DELAY": {
                "type": float,
                "min_value": 1.0,
                "max_value": 3600.0,
                "description": "重试最大延迟时间（秒）"
            },
            
            # 性能相关常量
            "SLOW_QUERY_THRESHOLD": {
                "type": float,
                "min_value": 0.1,
                "max_value": 60.0,
                "description": "慢查询阈值（秒）"
            },
            "SLOW_API_THRESHOLD": {
                "type": float,
                "min_value": 0.1,
                "max_value": 60.0,
                "description": "慢API阈值（秒）"
            },
            "MEMORY_WARNING_THRESHOLD": {
                "type": int,
                "min_value": 50,
                "max_value": 95,
                "description": "内存警告阈值（百分比）"
            },
            "CPU_WARNING_THRESHOLD": {
                "type": int,
                "min_value": 50,
                "max_value": 95,
                "description": "CPU警告阈值（百分比）"
            },
            
            # 安全相关常量
            "CSRF_TOKEN_LIFETIME": {
                "type": int,
                "min_value": 60,
                "max_value": 86400,
                "description": "CSRF令牌生命周期（秒）"
            },
            "PASSWORD_RESET_TOKEN_LIFETIME": {
                "type": int,
                "min_value": 300,
                "max_value": 3600,
                "description": "密码重置令牌生命周期（秒）"
            },
            "EMAIL_VERIFICATION_TOKEN_LIFETIME": {
                "type": int,
                "min_value": 300,
                "max_value": 86400,
                "description": "邮箱验证令牌生命周期（秒）"
            },
            
            # 监控相关常量
            "HEALTH_CHECK_INTERVAL": {
                "type": int,
                "min_value": 10,
                "max_value": 300,
                "description": "健康检查间隔（秒）"
            },
            "METRICS_COLLECTION_INTERVAL": {
                "type": int,
                "min_value": 10,
                "max_value": 3600,
                "description": "指标收集间隔（秒）"
            },
            "ALERT_CHECK_INTERVAL": {
                "type": int,
                "min_value": 10,
                "max_value": 3600,
                "description": "告警检查间隔（秒）"
            },
        }

    def validate_positive_int(self, value: Any, constant_name: str) -> Tuple[bool, str]:
        """
        验证正整数

        Args:
            value: 要验证的值
            constant_name: 常量名称

        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if not isinstance(value, int):
            return False, f"{constant_name} 必须是整数，当前类型: {type(value).__name__}"
        
        if value <= 0:
            return False, f"{constant_name} 必须是正整数，当前值: {value}"
        
        return True, ""

    def validate_positive_float(self, value: Any, constant_name: str) -> Tuple[bool, str]:
        """
        验证正浮点数

        Args:
            value: 要验证的值
            constant_name: 常量名称

        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if not isinstance(value, (int, float)):
            return False, f"{constant_name} 必须是数字，当前类型: {type(value).__name__}"
        
        if value <= 0:
            return False, f"{constant_name} 必须是正数，当前值: {value}"
        
        return True, ""

    def validate_range(self, value: Any, constant_name: str, min_value: Any = None, max_value: Any = None) -> Tuple[bool, str]:
        """
        验证值范围

        Args:
            value: 要验证的值
            constant_name: 常量名称
            min_value: 最小值
            max_value: 最大值

        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if min_value is not None and value < min_value:
            return False, f"{constant_name} 不能小于 {min_value}，当前值: {value}"
        
        if max_value is not None and value > max_value:
            return False, f"{constant_name} 不能大于 {max_value}，当前值: {value}"
        
        return True, ""

    def validate_type(self, value: Any, constant_name: str, expected_type: type) -> Tuple[bool, str]:
        """
        验证类型

        Args:
            value: 要验证的值
            constant_name: 常量名称
            expected_type: 期望类型

        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if not isinstance(value, expected_type):
            return False, f"{constant_name} 必须是 {expected_type.__name__} 类型，当前类型: {type(value).__name__}"
        
        return True, ""

    def validate_string_pattern(self, value: Any, constant_name: str, pattern: str) -> Tuple[bool, str]:
        """
        验证字符串模式

        Args:
            value: 要验证的值
            constant_name: 常量名称
            pattern: 正则表达式模式

        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if not isinstance(value, str):
            return False, f"{constant_name} 必须是字符串，当前类型: {type(value).__name__}"
        
        if not re.match(pattern, value):
            return False, f"{constant_name} 格式不正确，当前值: {value}"
        
        return True, ""

    def validate_constant(self, constant_name: str, value: Any) -> Tuple[bool, str]:
        """
        验证单个常量

        Args:
            constant_name: 常量名称
            value: 常量值

        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if constant_name not in self.validation_rules:
            return True, ""  # 没有验证规则，认为有效
        
        rule = self.validation_rules[constant_name]
        
        # 验证类型
        if "type" in rule:
            is_valid, error_msg = self.validate_type(value, constant_name, rule["type"])
            if not is_valid:
                return False, error_msg
        
        # 验证范围
        if "min_value" in rule or "max_value" in rule:
            is_valid, error_msg = self.validate_range(
                value, 
                constant_name, 
                rule.get("min_value"), 
                rule.get("max_value")
            )
            if not is_valid:
                return False, error_msg
        
        # 验证模式
        if "pattern" in rule:
            is_valid, error_msg = self.validate_string_pattern(value, constant_name, rule["pattern"])
            if not is_valid:
                return False, error_msg
        
        return True, ""

    def validate_all_constants(self) -> Dict[str, List[str]]:
        """
        验证所有常量

        Returns:
            Dict: 验证结果，键为常量名称，值为错误信息列表
        """
        validation_results = {}
        
        # 验证 SystemConstants
        for attr_name in dir(SystemConstants):
            if not attr_name.startswith("_"):
                value = getattr(SystemConstants, attr_name)
                is_valid, error_msg = self.validate_constant(attr_name, value)
                
                if not is_valid:
                    if attr_name not in validation_results:
                        validation_results[attr_name] = []
                    validation_results[attr_name].append(error_msg)
        
        # 验证 DefaultConfig
        for attr_name in dir(DefaultConfig):
            if not attr_name.startswith("_"):
                value = getattr(DefaultConfig, attr_name)
                is_valid, error_msg = self.validate_constant(attr_name, value)
                
                if not is_valid:
                    if attr_name not in validation_results:
                        validation_results[attr_name] = []
                    validation_results[attr_name].append(error_msg)
        
        return validation_results

    def validate_constants_in_class(self, constant_class: type) -> Dict[str, List[str]]:
        """
        验证指定类中的常量

        Args:
            constant_class: 常量类

        Returns:
            Dict: 验证结果
        """
        validation_results = {}
        
        for attr_name in dir(constant_class):
            if not attr_name.startswith("_"):
                value = getattr(constant_class, attr_name)
                is_valid, error_msg = self.validate_constant(attr_name, value)
                
                if not is_valid:
                    if attr_name not in validation_results:
                        validation_results[attr_name] = []
                    validation_results[attr_name].append(error_msg)
        
        return validation_results

    def get_validation_summary(self) -> Dict[str, Any]:
        """
        获取验证摘要

        Returns:
            Dict: 验证摘要信息
        """
        all_results = self.validate_all_constants()
        
        total_constants = sum(len(results) for results in all_results.values())
        invalid_constants = len(all_results)
        valid_constants = total_constants - invalid_constants
        
        return {
            "total_constants": total_constants,
            "valid_constants": valid_constants,
            "invalid_constants": invalid_constants,
            "validation_errors": all_results,
            "validation_rate": (valid_constants / total_constants * 100) if total_constants > 0 else 100,
        }

    def export_validation_report(self, output_file: str = None) -> str:
        """
        导出验证报告

        Args:
            output_file: 输出文件路径

        Returns:
            str: 输出文件路径
        """
        if not output_file:
            output_file = "constants_validation_report.json"
        
        import json
        report = self.get_validation_summary()
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        return output_file


def main():
    """主函数"""
    validator = ConstantsValidator()
    
    # 验证所有常量
    results = validator.validate_all_constants()
    
    if results:
        print("发现以下常量验证错误:")
        for constant_name, errors in results.items():
            print(f"\n{constant_name}:")
            for error in errors:
                print(f"  - {error}")
    else:
        print("所有常量验证通过！")
    
    # 生成验证摘要
    summary = validator.get_validation_summary()
    print(f"\n验证摘要:")
    print(f"总常量数: {summary['total_constants']}")
    print(f"有效常量数: {summary['valid_constants']}")
    print(f"无效常量数: {summary['invalid_constants']}")
    print(f"验证通过率: {summary['validation_rate']:.2f}%")
    
    # 导出验证报告
    report_file = validator.export_validation_report()
    print(f"\n验证报告已导出到: {report_file}")


if __name__ == "__main__":
    main()
