"""
泰摸鱼吧 - API响应工具
"""

from typing import Any

from flask import jsonify


class APIResponse:
    """API响应工具类"""

    @staticmethod
    def success(data: "Any" = None, message: str = "操作成功") -> "Response":
        """
        成功响应

        Args:
            data: 响应数据
            message: 响应消息

        Returns:
            JSON响应
        """
        response = {"success": True, "message": message}
        if data is not None:
            response["data"] = data
        return jsonify(response)

    @staticmethod
    def error(message: str = "操作失败", code: int = 400, data: "Any" = None) -> "Response":
        """
        错误响应

        Args:
            message: 错误消息
            code: 错误代码
            data: 响应数据

        Returns:
            JSON响应
        """
        response = {"success": False, "message": message, "code": code}
        if data is not None:
            response["data"] = data
        return jsonify(response), code


# 便捷函数
def success_response(data: Any = None, message: str = "操作成功") -> APIResponse:  # noqa: ANN401
    """成功响应便捷函数"""
    return APIResponse.success(data, message)


def error_response(message: str = "操作失败", code: int = 400, data: Any = None) -> APIResponse:  # noqa: ANN401
    """错误响应便捷函数"""
    return APIResponse.error(message, code, data)
