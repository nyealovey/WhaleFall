"""路由模块。

定义所有 HTTP 路由端点，处理客户端请求并返回响应。


主要路由：
- auth: 认证相关路由（登录、登出、修改密码）
- instances: 实例管理路由
- credentials: 凭据管理路由
- accounts: 账户管理路由
- tags: 标签管理路由
- dashboard: 仪表板路由
- aggregations: 数据聚合路由
- capacity: 容量统计路由
- logs: 日志查询路由
- sync_sessions: 同步会话路由
- scheduler: 定时任务路由
- partition: 分区管理路由
- connections: 连接测试路由
"""

from flask import Blueprint

# 创建主蓝图

# 该文件仅作为包标识，避免在导入阶段引入循环依赖。
