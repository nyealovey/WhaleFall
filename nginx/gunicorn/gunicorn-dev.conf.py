# Gunicorn配置文件 - 开发环境
import multiprocessing
import os

# 服务器套接字
bind = "0.0.0.0:5001"
backlog = 1024

# 工作进程 - 开发环境简化配置
workers = 1  # 开发环境使用单进程
worker_class = "sync"  # 使用同步工作器，便于调试
timeout = 60  # 开发环境超时时间更长
keepalive = 2

# 重启
max_requests = 0  # 开发环境不限制请求数
preload_app = False  # 开发环境不预加载应用

# 日志配置
accesslog = "/app/userdata/logs/gunicorn_access.log"
errorlog = "/app/userdata/logs/gunicorn_error.log"
loglevel = "debug"  # 开发环境使用debug级别
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程名称
proc_name = "whalefall-dev"

# 用户和组
user = "root"
group = "root"

# 环境变量
raw_env = [
    "FLASK_APP=app.py",
    "FLASK_ENV=development",
    "FLASK_DEBUG=1",
]

# 安全
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# 调试配置
capture_output = True
enable_stdio_inheritance = True
reload = True  # 开发环境启用自动重载
