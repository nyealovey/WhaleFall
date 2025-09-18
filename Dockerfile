# 使用Ubuntu 22.04作为基础镜像
FROM ubuntu:22.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y \
    python3.11 \
    python3.11-pip \
    python3.11-venv \
    python3.11-dev \
    build-essential \
    libpq-dev \
    pkg-config \
    libssl-dev \
    libffi-dev \
    curl \
    wget \
    git \
    supervisor \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3 \
    && ln -sf /usr/bin/python3.11 /usr/bin/python

# 创建非root用户
RUN useradd -m -s /bin/bash whalefall && \
    chown -R whalefall:whalefall /app

# 切换到非root用户
USER whalefall

# 创建虚拟环境
RUN python3 -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# 复制requirements文件
COPY --chown=whalefall:whalefall requirements-prod.txt /app/requirements.txt

# 安装Python依赖
RUN python3.11 -m pip install --no-cache-dir --upgrade pip && \
    python3.11 -m pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY --chown=whalefall:whalefall . /app/

# 创建必要的目录
RUN mkdir -p /app/userdata/logs /app/userdata/exports /app/userdata/backups /app/userdata/uploads

# 设置权限
RUN chmod -R 755 /app/userdata

# 创建Gunicorn配置文件
RUN cat > /app/gunicorn.conf.py << 'EOF'
# Gunicorn配置文件
import multiprocessing
import os

# 服务器套接字
bind = "0.0.0.0:5000"
backlog = 2048

# 工作进程
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"
worker_connections = 1000
timeout = 30
keepalive = 2

# 重启
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# 日志
accesslog = "/app/userdata/logs/gunicorn_access.log"
errorlog = "/app/userdata/logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程名称
proc_name = "whalefall"

# 用户和组
user = "whalefall"
group = "whalefall"

# 环境变量
raw_env = [
    "FLASK_APP=app.py",
    "FLASK_ENV=production",
]

# 安全
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
EOF

# 创建Supervisor配置文件
RUN cat > /app/supervisord.conf << 'EOF'
[supervisord]
nodaemon=true
user=whalefall
logfile=/app/userdata/logs/supervisord.log
pidfile=/app/userdata/logs/supervisord.pid
childlogdir=/app/userdata/logs/

[program:whalefall]
command=/app/.venv/bin/gunicorn --config /app/gunicorn.conf.py app:app
directory=/app
user=whalefall
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/app/userdata/logs/whalefall.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
stderr_logfile=/app/userdata/logs/whalefall_error.log
stderr_logfile_maxbytes=50MB
stderr_logfile_backups=10

[program:whalefall-scheduler]
command=/app/.venv/bin/python -c "from app.scheduler import start_scheduler; start_scheduler()"
directory=/app
user=whalefall
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/app/userdata/logs/scheduler.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
stderr_logfile=/app/userdata/logs/scheduler_error.log
stderr_logfile_maxbytes=50MB
stderr_logfile_backups=10
EOF

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# 启动命令 - 使用Supervisor管理多个进程
CMD ["/usr/bin/supervisord", "-c", "/app/supervisord.conf"]