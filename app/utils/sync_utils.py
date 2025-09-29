"""
鲸落 - 同步相关工具函数
提供同步操作方式和分类的验证、转换和显示功能
"""

from typing import Dict, List, Optional
from app.constants.sync_constants import SyncConstants, SyncOperationType, SyncCategory


class SyncUtils:
    """同步相关工具类"""
    
    @staticmethod
    def validate_sync_operation_type(operation_type: str) -> bool:
        """验证同步操作方式是否有效"""
        return SyncConstants.is_valid_operation_type(operation_type)
    
    @staticmethod
    def validate_sync_category(category: str) -> bool:
        """验证同步分类是否有效"""
        return SyncConstants.is_valid_category(category)
    
    @staticmethod
    def get_operation_type_display(operation_type: str) -> str:
        """获取操作方式的中文显示名称"""
        return SyncConstants.get_operation_type_display(operation_type)
    
    @staticmethod
    def get_category_display(category: str) -> str:
        """获取同步分类的中文显示名称"""
        return SyncConstants.get_category_display(category)
    
    @staticmethod
    def get_operation_type_description(operation_type: str) -> str:
        """获取操作方式的英文描述"""
        return SyncConstants.get_operation_type_description(operation_type)
    
    @staticmethod
    def get_category_description(category: str) -> str:
        """获取同步分类的英文描述"""
        return SyncConstants.get_category_description(category)
    
    @staticmethod
    def get_operation_type_options() -> List[Dict[str, str]]:
        """获取操作方式选项列表（用于前端下拉框）"""
        return SyncConstants.get_all_operation_types()
    
    @staticmethod
    def get_category_options() -> List[Dict[str, str]]:
        """获取同步分类选项列表（用于前端下拉框）"""
        return SyncConstants.get_all_categories()
    
    @staticmethod
    def format_sync_info(operation_type: str, category: str) -> str:
        """格式化同步信息显示"""
        op_display = SyncUtils.get_operation_type_display(operation_type)
        cat_display = SyncUtils.get_category_display(category)
        return f"{op_display} - {cat_display}"
    
    @staticmethod
    def get_sync_type_choices() -> List[tuple]:
        """获取同步操作方式的Django/Flask选择项"""
        return [(op.value, SyncConstants.OPERATION_TYPE_DISPLAY[op]) for op in SyncOperationType]
    
    @staticmethod
    def get_sync_category_choices() -> List[tuple]:
        """获取同步分类的Django/Flask选择项"""
        return [(cat.value, SyncConstants.CATEGORY_DISPLAY[cat]) for cat in SyncCategory]
    
    @staticmethod
    def is_manual_operation(operation_type: str) -> bool:
        """判断是否为手动操作"""
        return operation_type in [
            SyncOperationType.MANUAL_SINGLE.value,
            SyncOperationType.MANUAL_BATCH.value,
            SyncOperationType.MANUAL_TASK.value
        ]
    
    @staticmethod
    def is_scheduled_operation(operation_type: str) -> bool:
        """判断是否为定时操作"""
        return operation_type == SyncOperationType.SCHEDULED_TASK.value
    
    @staticmethod
    def get_operation_type_icon(operation_type: str) -> str:
        """获取操作方式对应的图标类名"""
        icon_mapping = {
            SyncOperationType.MANUAL_SINGLE.value: "fas fa-hand-pointer",
            SyncOperationType.MANUAL_BATCH.value: "fas fa-tasks",
            SyncOperationType.MANUAL_TASK.value: "fas fa-play-circle",
            SyncOperationType.SCHEDULED_TASK.value: "fas fa-clock"
        }
        return icon_mapping.get(operation_type, "fas fa-question-circle")
    
    @staticmethod
    def get_category_icon(category: str) -> str:
        """获取同步分类对应的图标类名"""
        icon_mapping = {
            SyncCategory.ACCOUNT.value: "fas fa-users",
            SyncCategory.CAPACITY.value: "fas fa-database",
            SyncCategory.CONFIG.value: "fas fa-cog",
            SyncCategory.AGGREGATION.value: "fas fa-chart-bar",
            SyncCategory.OTHER.value: "fas fa-ellipsis-h"
        }
        return icon_mapping.get(category, "fas fa-question-circle")
    
    @staticmethod
    def get_operation_type_color(operation_type: str) -> str:
        """获取操作方式对应的颜色类名"""
        color_mapping = {
            SyncOperationType.MANUAL_SINGLE.value: "primary",
            SyncOperationType.MANUAL_BATCH.value: "info",
            SyncOperationType.MANUAL_TASK.value: "warning",
            SyncOperationType.SCHEDULED_TASK.value: "success"
        }
        return color_mapping.get(operation_type, "secondary")
    
    @staticmethod
    def get_category_color(category: str) -> str:
        """获取同步分类对应的颜色类名"""
        color_mapping = {
            SyncCategory.ACCOUNT.value: "primary",
            SyncCategory.CAPACITY.value: "success",
            SyncCategory.CONFIG.value: "info",
            SyncCategory.AGGREGATION.value: "warning",
            SyncCategory.OTHER.value: "secondary"
        }
        return color_mapping.get(category, "secondary")
