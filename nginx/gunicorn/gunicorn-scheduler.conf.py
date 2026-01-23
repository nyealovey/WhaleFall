"""Scheduler Gunicorn 配置.

专用于运行 APScheduler（ENABLE_SCHEDULER=true）。
"""

import os
import tempfile

# 服务器套接字（仅容器内/本机回环访问，由 Nginx 反代）
bind = "127.0.0.1:5002"
backlog = 1024

# Scheduler 进程只需要 1 个 worker，避免重复启动调度器
workers = 1
worker_class = "sync"
timeout = 120
keepalive = 2

# 重启
max_requests = 1000
max_requests_jitter = 50
preload_app = False

# 日志配置
accesslog = "/app/userdata/logs/gunicorn_scheduler_access.log"
errorlog = "/app/userdata/logs/gunicorn_scheduler_error.log"
loglevel = "info"

# 进程名称
proc_name = "whalefall-scheduler"

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

worker_tmp_dir = os.getenv("GUNICORN_WORKER_TMP_DIR", tempfile.gettempdir())
