# Gunicorn配置文件 - 生产环境
import multiprocessing
import os

# 服务器套接字
bind = "0.0.0.0:5001"
backlog = 2048

# 工作进程 - 简化配置
workers = 2  # 固定2个进程，避免复杂配置
worker_class = "gevent"  # 使用gevent工作器，支持异步
worker_connections = 1000  # gevent工作器连接数
timeout = 30
keepalive = 2

# 重启
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# 日志配置
accesslog = "/app/userdata/logs/gunicorn_access.log"
errorlog = "/app/userdata/logs/gunicorn_error.log"
loglevel = "info"  # 改为info级别，减少日志量
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程名称
proc_name = "whalefall"

# 用户和组
user = "root"
group = "root"

# 环境变量
raw_env = [
    "FLASK_APP=app.py",
    "FLASK_ENV=production",
]

# 安全
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# 调试配置
capture_output = True
enable_stdio_inheritance = True

# Gevent特定配置
worker_tmp_dir = "/dev/shm"  # 使用内存文件系统提高性能
