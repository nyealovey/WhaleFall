# 调度器单实例修复记录（对比 v1.0.5）

## 背景
- 线上定时任务面板持续出现两条「调度器已经初始化过，跳过重复初始化」告警，时间戳相同（ID:393015/393019），说明同一进程内重复进行初始化。
- 告警自 v1.0.5 之后的版本出现，彼时新增了容量采集/聚合等任务，它们在后台线程里调用 `create_app()` 获取上下文。

## v1.0.5 与当前实现的差异
| 对比项 | v1.0.5 | 修复前 |
| --- | --- | --- |
| 任务执行方式 | 仅 `sync_accounts`、`cleanup_old_logs`，在主进程中运行 | 多个任务/脚本在线程或子进程里调用 `create_app()` |
| `create_app()` 行为 | 只由主进程调用，因此调度器只初始化一次 | 所有线程/脚本都会触发 `init_scheduler()` |
| 保护手段 | 没有文件锁，但也没有重复调用场景 | 即便加了文件锁，同进程任务线程仍二次初始化，写出 WARNING |

根因：任务线程每次 `create_app()` 都会重新触发 `init_scheduler()`，而文件锁由于在同一进程内已持有，不会阻止重复初始化。

## 修复策略
1. **应用工厂增加显式开关**  
   - `create_app(..., init_scheduler_on_start: bool = True)`，默认行为与历史一致。
   - 只有真正运行 Web 服务/Gunicorn/Flask CLI 时才传 `True`。

2. **入口显式启用，其他场景禁用**  
   - `app.py`、`wsgi.py` 传 `True`，确保主流程仍启动调度器。
   - 所有后台任务、脚本、测试以及手动触发线程一律传 `False`。

3. **移除模块级 `app = create_app()`**  
   - 避免导入 `app` 模块时就隐式开启调度器。
   - 仅保留模型导入，满足 SQLAlchemy 注册需求。

4. **同步文档**  
   - 记录问题背景、v1.0.5 行为、修复方式及验证步骤，方便回溯。

## 修改点总览
- `app/__init__.py`：增加参数、受控初始化、移除全局 `create_app()`。
- `app.py`、`wsgi.py`：入口显式启用调度器。
- 所有任务脚本/API 线程：`create_app(init_scheduler_on_start=False)`。
- 测试与密码脚本：同样禁用调度器。

## 验证步骤
1. **启动 Flask/Gunicorn**：`python app.py` 或 `gunicorn wsgi:application`，日志应仅出现一次 “调度器初始化完成”。
2. **后台任务/脚本执行**：运行任意任务（capacity/account sync）或 `scripts/password/reset_admin_password.py`，日志不再出现 “调度器已经初始化过”。
3. **面板手动执行任务**：通过 `/scheduler/jobs/<job_id>/run` 触发，确保后台线程调用 `create_app` 时不再初始化调度器。
4. **测试**：执行 `make test` 或 `pytest`，确认测试输出没有调度器告警。

## 风险与注意
- 如有脚本依赖调度器立即可用，需要显式传 `init_scheduler_on_start=True`。
- 如果未来新增任务/脚本，请按照本规范传入参数，避免重复初始化问题再现。
