"""
颜色常量定义 - 基于Flatly主题的统一色彩系统
"""

class ThemeColors:
    """主题颜色常量"""
    
    # Flatly主题标准颜色映射
    COLOR_MAP = {
        'primary': {
            'value': '#18bc9c',
            'name': '主色绿',
            'description': '主要操作和重要信息',
            'css_class': 'bg-primary'
        },
        'danger': {
            'value': '#e74c3c',
            'name': '危险红', 
            'description': '高风险和危险操作',
            'css_class': 'bg-danger'
        },
        'warning': {
            'value': '#f39c12',
            'name': '警告橙',
            'description': '需要注意的操作',
            'css_class': 'bg-warning'
        },
        'info': {
            'value': '#3498db',
            'name': '信息蓝',
            'description': '普通信息和标准操作', 
            'css_class': 'bg-info'
        },
        'secondary': {
            'value': '#95a5a6',
            'name': '次要灰',
            'description': '次要信息和禁用状态',
            'css_class': 'bg-secondary'
        },
        'success': {
            'value': '#18bc9c',
            'name': '成功绿',
            'description': '成功状态和安全操作',
            'css_class': 'bg-success'
        },
        'dark': {
            'value': '#2c3e50',
            'name': '深色',
            'description': '重要信息和标题',
            'css_class': 'bg-dark'
        },
        'light': {
            'value': '#ecf0f1',
            'name': '浅色',
            'description': '背景和辅助信息',
            'css_class': 'bg-light'
        }
    }
    
    @classmethod
    def get_color_value(cls, color_key):
        """获取颜色值。

        Args:
            color_key: 颜色键，例如 'primary'。

        Returns:
            HEX 颜色字符串，未匹配时返回默认信息蓝。
        """
        return cls.COLOR_MAP.get(color_key, {}).get('value', '#3498db')
    
    @classmethod
    def get_color_name(cls, color_key):
        """获取颜色名称。

        Args:
            color_key: 颜色键。

        Returns:
            颜色中文名称，找不到时返回“信息蓝”。
        """
        return cls.COLOR_MAP.get(color_key, {}).get('name', '信息蓝')
    
    @classmethod
    def get_color_choices(cls):
        """获取表单选择项。

        Returns:
            (键, 展示文案) 的列表。
        """
        return [(key, f"{info['name']} - {info['description']}") 
                for key, info in cls.COLOR_MAP.items()]
    
    @classmethod
    def get_css_class(cls, color_key):
        """获取 CSS 类名。

        Args:
            color_key: 颜色键。

        Returns:
            与颜色对应的 CSS class，默认为 `bg-info`。
        """
        return cls.COLOR_MAP.get(color_key, {}).get('css_class', 'bg-info')
    
    @classmethod
    def is_valid_color(cls, color_key):
        """验证颜色键是否有效。

        Args:
            color_key: 颜色键。

        Returns:
            True 表示存在于 COLOR_MAP，False 表示未知颜色。
        """
        return color_key in cls.COLOR_MAP
    
    @classmethod
    def get_color_info(cls, color_key):
        """获取完整颜色信息。

        Args:
            color_key: 颜色键。

        Returns:
            包含 value/name/description/css_class 的字典。
        """
        return cls.COLOR_MAP.get(color_key, cls.COLOR_MAP['info'])
