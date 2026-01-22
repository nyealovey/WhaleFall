# Scheduler Dedicated Process Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 APScheduler 从 Web Gunicorn worker 中剥离为独立进程，使 Web 可以安全提升到 `workers=2`（甚至更多）且定时任务不重复、页面不再因任务执行而卡住。

**Architecture:**
- Web 进程：提供所有页面与业务 API，但通过 `ENABLE_SCHEDULER=false` 禁用调度器。
- Scheduler 进程：单独跑一套 WSGI/Gunicorn（单 worker），通过 `ENABLE_SCHEDULER=true` 启用调度器，只负责运行 APScheduler + 提供 `/api/v1/scheduler/**` 管理接口。
- Nginx：按路径路由，将 `/api/v1/scheduler/**` 代理到 Scheduler 进程，其余请求代理到 Web 进程。

**Tech Stack:** Python (Flask + APScheduler), Gunicorn, Supervisor, Nginx, Docker

---

### Task 1: 显式暴露 `ENABLE_SCHEDULER` 配置并补齐单测

**Files:**
- Modify: `env.example`
- Test: `tests/unit/test_settings_enable_scheduler_flag.py`

**Step 1: Write the failing test**

```python
from __future__ import annotations


def test_settings_enable_scheduler_can_be_disabled(monkeypatch) -> None:
    # Arrange
    monkeypatch.setenv("ENABLE_SCHEDULER", "false")

    # Act
    from app.settings import Settings

    settings = Settings.load()

    # Assert
    assert settings.enable_scheduler is False
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest -m unit tests/unit/test_settings_enable_scheduler_flag.py -q`

Expected: FAIL（尚未创建该测试文件）。

**Step 3: Write minimal implementation**
- 在 `env.example` 增加 `ENABLE_SCHEDULER`（并注释：web 进程建议 false；scheduler 进程 true）。

**Step 4: Run test to verify it passes**

Run: `uv run pytest -m unit tests/unit/test_settings_enable_scheduler_flag.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add env.example tests/unit/test_settings_enable_scheduler_flag.py
git commit -m "docs: expose ENABLE_SCHEDULER and add settings test"
```

---

### Task 2: 生产环境 Web 进程调整为 `workers=2`

**Files:**
- Modify: `nginx/gunicorn/gunicorn-prod.conf.py`

**Step 1: Change the config (minimal)**
- 将 `workers = 1` 改为 `workers = 2`。
- 同步修正注释（当前注释写“固定2个进程”但实际是 1）。

**Step 2: Quick smoke check (syntax only)**

Run: `python -m py_compile nginx/gunicorn/gunicorn-prod.conf.py`

Expected: no output

**Step 3: Commit**

```bash
git add nginx/gunicorn/gunicorn-prod.conf.py
git commit -m "ops: bump web gunicorn workers to 2"
```

---

### Task 3: 新增 Scheduler 专用 Gunicorn 配置（单端口/单 worker）

**Files:**
- Create: `nginx/gunicorn/gunicorn-scheduler.conf.py`

**Step 1: Create the config file**

```python
"""Scheduler Gunicorn 配置.

专用于运行 APScheduler（ENABLE_SCHEDULER=true）。
"""

import os
import tempfile


bind = "127.0.0.1:5002"
backlog = 1024

workers = 1
worker_class = "sync"  # scheduler 进程不需要 gevent 并发
timeout = 120
keepalive = 2

max_requests = 1000
max_requests_jitter = 50
preload_app = False

accesslog = "/app/userdata/logs/gunicorn_scheduler_access.log"
errorlog = "/app/userdata/logs/gunicorn_scheduler_error.log"
loglevel = "info"

proc_name = "whalefall-scheduler"

user = "root"
group = "root"

raw_env = [
    "FLASK_APP=app.py",
    "FLASK_ENV=production",
]

limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

capture_output = True
enable_stdio_inheritance = True

worker_tmp_dir = os.getenv("GUNICORN_WORKER_TMP_DIR", tempfile.gettempdir())
```

**Step 2: Quick smoke check (syntax only)**

Run: `python -m py_compile nginx/gunicorn/gunicorn-scheduler.conf.py`

Expected: no output

**Step 3: Commit**

```bash
git add nginx/gunicorn/gunicorn-scheduler.conf.py
git commit -m "ops: add scheduler gunicorn config"
```

---

### Task 4: Supervisor 启动两个 Gunicorn 进程（web + scheduler）

**Files:**
- Modify: `nginx/supervisor/whalefall-prod.conf`

**Step 1: Update supervisor programs**
- 保留 `[program:nginx]`。
- 将原 `[program:whalefall]` 拆为：
  - `[program:whalefall_web]`：`--config /app/gunicorn.conf.py wsgi:application` + `environment=ENABLE_SCHEDULER="false"`
  - `[program:whalefall_scheduler]`：`--config /app/nginx/gunicorn/gunicorn-scheduler.conf.py wsgi:application` + `environment=ENABLE_SCHEDULER="true"`
- 为 scheduler program 单独指定 stdout/stderr logfile，避免和 web 混在一起。

**Step 2: Validate supervisor config (container 内验证)**

Run (in container): `supervisord -n -c /etc/supervisor/supervisord.conf -t`

Expected: `OK`

**Step 3: Commit**

```bash
git add nginx/supervisor/whalefall-prod.conf
git commit -m "ops: split web and scheduler gunicorn under supervisor"
```

---

### Task 5: Nginx 按路径把 scheduler API 路由到 5002

**Files:**
- Modify: `nginx/sites-available/whalefall-prod`

**Step 1: Add a dedicated location block**
- 在 `location / { ... }` 之前新增：
  - `location ^~ /api/v1/scheduler/ { proxy_pass http://127.0.0.1:5002; ... }`
  - （可选）同时兼容不带 trailing slash：`location = /api/v1/scheduler { return 301 /api/v1/scheduler/; }`
- headers/timeout 复用主 proxy 配置，保证 CSRF/session cookie 正常。

**Step 2: Validate Nginx config (container 内验证)**

Run (in container): `nginx -t`

Expected: `syntax is ok` + `test is successful`

**Step 3: Commit**

```bash
git add nginx/sites-available/whalefall-prod
git commit -m "ops: route /api/v1/scheduler to scheduler process"
```

---

### Task 6: 端到端验证（Docker 生产编排）

**Files:**
- None

**Step 1: Build image**

Run: `docker compose -f docker-compose.prod.yml build whalefall`

Expected: build success

**Step 2: Start services**

Run: `docker compose -f docker-compose.prod.yml up -d`

Expected: all services healthy

**Step 3: Verify routing & scheduler stability**

Run:
- `curl -fsS http://localhost/api/v1/health/basic`
- `curl -fsS http://localhost/api/v1/scheduler/jobs`

Expected:
- health: 200
- scheduler jobs: 200（不再出现随机 409: 调度器未启动）

**Step 4: Verify “页面不卡住”**
- 打开 `/scheduler` 页面，点击“立即执行/重新加载”等操作，同时在另一个浏览器标签页持续刷新 `/dashboard`。
- 预期：dashboard 刷新不再因任务执行而卡死（web 进程与 scheduler 进程隔离）。

---

### Task 7: 文档补齐（说明为什么可以安全把 worker 改为 2）

**Files:**
- Modify: `docs/Obsidian/standards/backend/task-and-scheduler.md`

**Step 1: Update doc**
- 增加一节“生产部署建议”：web/scheduler 分进程（或分容器），web 侧 `ENABLE_SCHEDULER=false`。
- 强调：多副本部署应使用集中式锁（redis/postgres advisory lock）作为下一步，避免任务重复执行。

**Step 2: Commit**

```bash
git add docs/Obsidian/standards/backend/task-and-scheduler.md
git commit -m "docs: document dedicated scheduler process deployment"
```
