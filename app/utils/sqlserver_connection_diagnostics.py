"""
鲸落 - SQL Server连接诊断工具
分析SQL Server连接失败的具体原因
"""

import socket
import time
from typing import Any, Dict, List

from app.utils.structlog_config import get_sync_logger
from app.constants import UserRole


class SQLServerConnectionDiagnostics:
    """SQL Server连接诊断工具"""

    def __init__(self) -> None:
        self.diag_logger = get_sync_logger()

    def diagnose_connection_error(self, error_message: str, host: str, port: int) -> Dict[str, Any]:
        """
        诊断SQL Server连接错误
        
        Args:
            error_message: 错误消息
            host: 主机地址
            port: 端口号
            
        Returns:
            诊断结果
        """
        diagnosis = {
            "host": host,
            "port": port,
            "error_message": error_message,
            "error_type": "unknown",
            "possible_causes": [],
            "solutions": [],
            "network_check": False,
            "port_check": False
        }

        # 分析错误类型
        if "18456" in error_message:
            diagnosis["error_type"] = "authentication_failed"
            diagnosis["possible_causes"] = [
                "用户名或密码不正确",
                "SQL Server认证模式设置问题",
                "用户账户被禁用或锁定",
                "数据库不存在或用户无访问权限"
            ]
            diagnosis["solutions"] = [
                "检查用户名和密码是否正确",
                "确认SQL Server使用混合认证模式",
                "检查用户账户状态",
                "验证用户是否有登录权限"
            ]
        elif "20018" in error_message:
            diagnosis["error_type"] = "general_sql_server_error"
            diagnosis["possible_causes"] = [
                "SQL Server服务未启动",
                "SQL Server配置错误",
                "数据库损坏或不可用",
                "权限不足"
            ]
            diagnosis["solutions"] = [
                "检查SQL Server服务状态",
                "查看SQL Server错误日志",
                "验证数据库完整性",
                "检查用户权限"
            ]
        elif "20002" in error_message:
            diagnosis["error_type"] = "connection_failed"
            diagnosis["possible_causes"] = [
                "网络连接问题",
                "防火墙阻止连接",
                "SQL Server未监听指定端口",
                "服务器不可达"
            ]
            diagnosis["solutions"] = [
                "检查网络连接",
                "验证防火墙设置",
                "确认SQL Server端口配置",
                "测试服务器可达性"
            ]
        elif "timeout" in error_message.lower():
            diagnosis["error_type"] = "timeout"
            diagnosis["possible_causes"] = [
                "网络延迟过高",
                "SQL Server响应慢",
                "连接超时设置过短",
                "服务器负载过高"
            ]
            diagnosis["solutions"] = [
                "增加连接超时时间",
                "检查网络质量",
                "优化SQL Server性能",
                "检查服务器资源使用"
            ]

        # 执行网络检查
        diagnosis["network_check"] = self._check_network_connectivity(host)
        diagnosis["port_check"] = self._check_port_accessibility(host, port)

        return diagnosis

    def _check_network_connectivity(self, host: str) -> bool:
        """检查网络连通性"""
        try:
            socket.gethostbyname(host)
            return True
        except socket.gaierror:
            return False

    def _check_port_accessibility(self, host: str, port: int) -> bool:
        """检查端口可访问性"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def get_connection_string_suggestions(self, host: str, port: int, username: str, database: str = "master") -> List[str]:
        """获取连接字符串建议"""
        suggestions = []
        
        # 基本连接字符串
        suggestions.append(f"Server={host},{port};Database={database};User Id={username};Password=***;")
        
        # 带超时的连接字符串
        suggestions.append(f"Server={host},{port};Database={database};User Id={username};Password=***;Connection Timeout=60;")
        
        # 带加密的连接字符串
        suggestions.append(f"Server={host},{port};Database={database};User Id={username};Password=***;Encrypt=True;TrustServerCertificate=True;")
        
        # 带重试的连接字符串
        suggestions.append(f"Server={host},{port};Database={database};User Id={username};Password=***;Connection Timeout=60;Command Timeout=300;")
        
        return suggestions

    def analyze_error_patterns(self, error_message: str) -> Dict[str, Any]:
        """分析错误模式"""
        patterns = {
            "has_network_error": any(keyword in error_message.lower() for keyword in ["timeout", "connection", "network", "unreachable"]),
            "has_auth_error": any(keyword in error_message.lower() for keyword in ["login", "authentication", "password", "user"]),
            "has_server_error": any(keyword in error_message.lower() for keyword in ["server", "service", "database", "sql"]),
            "has_permission_error": any(keyword in error_message.lower() for keyword in ["permission", "access", "denied", "unauthorized"])
        }
        
        return patterns


# 创建全局实例
sqlserver_diagnostics = SQLServerConnectionDiagnostics()
