"""
DEBUG日志过滤器
专门用于过滤同步适配器中的DEBUG日志
"""

import logging
import re


class DebugLogFilter(logging.Filter):
    """DEBUG日志过滤器"""

    def __init__(self):
        super().__init__()
        # 定义需要过滤的DEBUG日志模式
        self.debug_patterns = [
            r"账户无变更，更新同步时间",
            r"无法访问用户表空间配额视图",
            r"无法获取用户对象表空间权限",
            r"开始获取用户实际数据库权限",
            r"用户数据库权限获取完成",
            r"准备新增账户",
            r"准备标记删除账户",
            r"准备更新账户权限",
            r"账户无变更",
        ]

        # 编译正则表达式
        self.compiled_patterns = [re.compile(pattern) for pattern in self.debug_patterns]

    def filter(self, record: logging.LogRecord) -> bool:
        """过滤日志记录"""
        # 如果不是DEBUG级别，直接通过
        if record.levelno != logging.DEBUG:
            return True

        # 检查消息是否匹配需要过滤的模式
        message = record.getMessage()
        for pattern in self.compiled_patterns:
            if pattern.search(message):
                return False  # 过滤掉匹配的DEBUG日志

        # 其他DEBUG日志也过滤掉
        return False


def configure_debug_filter():
    """配置DEBUG日志过滤器"""
    # 获取根记录器
    root_logger = logging.getLogger()

    # 添加DEBUG过滤器
    debug_filter = DebugLogFilter()
    root_logger.addFilter(debug_filter)

    # 为特定记录器添加过滤器
    for logger_name in ["sync_adapter", "unknown", "app.services.sync_adapters"]:
        logger = logging.getLogger(logger_name)
        logger.addFilter(debug_filter)
        logger.setLevel(logging.INFO)

    # 设置所有记录器的级别为INFO
    for logger_name in ["sync_adapter", "unknown", "app", "api", "auth", "database", "sync", "task"]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
