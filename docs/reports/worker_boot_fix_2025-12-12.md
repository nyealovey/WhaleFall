# Gunicorn Worker 启动失败修复记录（2025-12-12）

## 背景
线上容器在 `docker compose -f docker-compose.prod.yml exec whalefall tail -f /app/userdata/logs/gunicorn_error.log` 中持续出现 `ImportError: cannot import name 'db' from partially initialized module 'app'`，导致 Gunicorn worker 无法启动。堆栈显示 `app/__init__.py → app/scheduler.py → app/tasks/accounts_sync_tasks.py → app/services/... → app/models/... → app/__init__` 形成循环导入。之前的临时修复通过在任务模块里大量使用延迟导入和 `# noqa`，虽然勉强绕过了循环，但引入了新的 Ruff 告警和代码可读性问题，需要从根因上解决。

## 根因分析
1. `app/scheduler.py` 在模块顶层直接 `from app.tasks... import ...`，而这些任务文件在导入时会立即引用 `db`、模型、服务等对象。由于调度器在 `create_app` 期间初始化，导致 Flask 应用尚未完成初始化时就加载了依赖，从而出现 "partially initialized module 'app'"。
2. `app/tasks/__init__.py` 也在包导入阶段加载了所有任务，实现上与调度器的行为相叠加，加剧了循环依赖问题。
3. `app/routes/accounts/sync.py` 同样在模块顶层引用 `sync_accounts`，在 blueprint 注册阶段（即应用初始化）又触发一次任务导入。

## 修复方案
1. **调度器惰性加载任务**：
   - 移除 `app/scheduler.py` 顶层的所有任务函数导入，改为维护一个 `TASK_FUNCTIONS` 字典，存放 `"模块路径:函数名"` 的字符串。
   - 新增 `_load_task_callable()` 辅助函数按需使用 `importlib.import_module` 加载任务函数，并缓存结果，确保只有在真正注册 Job 时才导入任务模块，从源头消除循环依赖。
2. **任务包去副作用**：
   - 将 `app/tasks/__init__.py` 精简为仅包含文档注释和 `__all__`，避免包级导入触发实际任务加载。
   - `app/tasks/accounts_sync_tasks.py` 中去掉顶层对模型、协调器、缓存等依赖的引用，只在 `sync_accounts()` 内部、并在 Flask 应用上下文已建立后再导入。`ACCOUNT_TASK_EXCEPTIONS` 也改为函数内部的局部元组，避免在模块导入时引用未初始化的类。
   - 仍需在任务内部获取 `db`，故保留 `_get_app_for_task()` 与 `_get_db()`，但去掉多余的 `# noqa` 并保持导入清晰。
3. **其它入口惰性加载**：
   - `app/routes/accounts/sync.py` 在 `_launch_background_sync()` 中才导入 `sync_accounts`，确保蓝图在注册时不会触发任务模块导入。

## 代码改动摘要
- `app/scheduler.py`：删除顶层任务导入，新增惰性加载逻辑，并在 `_register_task_from_config` 中使用 `_load_task_callable()`。
- `app/tasks/__init__.py`：去掉对各任务文件的导入，仅保留 `__all__`。
- `app/tasks/accounts_sync_tasks.py`：
  - 顶层仅保留与配置相关的依赖；在任务内部延迟导入 `AccountSyncCoordinator`、`sync_session_service`、`Instance` 等。
  - 将异常元组改为函数级局部变量，同时保持 Ruff 对 import 顺序的要求。
- `app/routes/accounts/sync.py`：后台线程启动前才动态导入 `sync_accounts`。

## 验证
1. **静态检查**：执行 `ruff check app/tasks/accounts_sync_tasks.py app/scheduler.py app/routes/accounts/sync.py --select I001,TC003,E501`，确认导入顺序与行宽符合要求，无新的 Ruff 告警。
2. **运行验证**：在容器中重新部署并执行 `docker compose -f docker-compose.prod.yml restart whalefall` 后，通过 `docker compose -f docker-compose.prod.yml logs -f whalefall` 确认 Gunicorn worker 能正常启动，不再打印 `ImportError: cannot import name 'db'`。

## 后续建议
- 新增任务时，继续在 `TASK_FUNCTIONS` 中登记模块路径，避免直接在调度器模块导入任务函数。
- 编写集成测试覆盖 `sync_accounts` 调度场景，可通过 Flask testing context 直接调用任务函数，确保后续改动不会再次引入循环依赖。
