# 路由模块初始化文件

from flask import Blueprint

# 创建主蓝图

# 导入所有路由模块
from . import (  # noqa: F401, E402
    auth,
    credentials,
    dashboard,
    instances,
    main,
)
