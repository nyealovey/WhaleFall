# 鲸落项目术语表

> 最后更新：2025-11-21  
> 本文档定义项目中使用的技术术语及其中文翻译，所有术语均来自项目实际代码。

## 使用说明

- 代码注释和文档中应使用统一的中文术语
- 专有名词（如框架名、库名）保持原文
- 新增术语时需在此文档中补充

---

## 1. 核心架构术语

| 英文术语 | 中文翻译 | 说明 | 代码示例 |
| --- | --- | --- | --- |
| Service | 服务 | 业务逻辑服务类 | `AccountSyncService`, `CacheService` |
| Manager | 管理器 | 资源管理类 | `AccountInventoryManager`, `DatabaseFilterManager` |
| Controller | 控制器 | 控制器类（较少使用） | - |
| Helper | 辅助类 | 工具辅助类 | `DOMHelpers` |
| Coordinator | 协调器 | 协调多个服务的类 | `AccountSyncCoordinator` |
| Orchestrator | 编排器 | 编排业务流程 | `AccountClassificationService` |
| Blueprint | 蓝图 | Flask 路由蓝图 | `auth_bp`, `users_bp` |
| Middleware | 中间件 | Flask 中间件 | - |
| Decorator | 装饰器 | Python 装饰器 | `@login_required`, `@require_csrf` |

## 2. 数据处理术语

| 英文术语 | 中文翻译 | 说明 | 代码示例 |
| --- | --- | --- | --- |
| Validator | 校验器 | 数据校验类 | `DataValidator` |
| Sanitizer | 清洗器 | 数据清洗/净化 | `sanitize_form_data()` |
| Serializer | 序列化器 | 数据序列化 | `to_dict()` |
| Formatter | 格式化器 | 数据格式化 | `format_size()` |
| Filter | 过滤器 | 数据过滤 | `DatabaseFilterManager` |
| Aggregation | 聚合 | 数据聚合统计 | `DatabaseSizeAggregation` |
| Aggregator | 聚合器 | 执行聚合的组件 | `AggregationService` |
| Collector | 采集器 | 数据采集组件 | `DatabaseSizeCollectorService` |
| Inventory | 清单 | 资源清单管理 | `AccountInventoryManager` |
| Synchronization | 同步 | 数据同步 | `AccountSyncService` |

## 3. 业务领域术语

| 英文术语 | 中文翻译 | 说明 | 代码示例 |
| --- | --- | --- | --- |
| Instance | 实例 | 数据库实例 | `Instance` 模型 |
| Account | 账户 | 数据库账户 | `InstanceAccount` 模型 |
| Credential | 凭据 | 登录凭据 | `Credential` 模型 |
| Permission | 权限 | 账户权限 | `AccountPermission` 模型 |
| Classification | 分类 | 账户分类 | `AccountClassification` 模型 |
| Rule | 规则 | 分类规则 | `ClassificationRule` 模型 |
| Tag | 标签 | 资源标签 | `Tag` 模型 |
| Partition | 分区 | 数据库表分区 | `PartitionManagementService` |
| Capacity | 容量 | 数据库容量 | `DatabaseSizeStat` |
| Session | 会话 | 同步会话 | `SyncSession` 模型 |

## 4. 技术框架术语

| 英文术语 | 中文翻译 | 说明 | 代码示例 |
| --- | --- | --- | --- |
| Flask | Flask | Web 框架，保持原文 | `from flask import Flask` |
| SQLAlchemy | SQLAlchemy | ORM 框架，保持原文 | `from sqlalchemy import Column` |
| structlog | structlog | 日志库，保持原文 | `from app.utils.structlog_config import log_info` |
| APScheduler | APScheduler | 任务调度器，保持原文 | `from apscheduler.schedulers.background import BackgroundScheduler` |
| Redis | Redis | 缓存数据库，保持原文 | `redis.Redis()` |
| PostgreSQL | PostgreSQL | 关系数据库，保持原文 | - |
| Gunicorn | Gunicorn | WSGI 服务器，保持原文 | - |
| Nginx | Nginx | Web 服务器，保持原文 | - |

## 5. 日志和监控术语

| 英文术语 | 中文翻译 | 说明 | 代码示例 |
| --- | --- | --- | --- |
| Logger | 日志记录器 | 日志对象 | `log_info()`, `log_error()` |
| Handler | 处理器 | 日志处理器 | - |
| Processor | 处理器 | 日志处理器 | - |
| Logger Factory | 日志工厂 | 创建日志记录器 | - |
| Metrics | 指标 | 监控指标 | `get_core_aggregation_metrics()` |
| Status | 状态 | 任务状态 | `AggregationStatus` |
| Level | 级别 | 日志级别 | `LogLevel.INFO` |

## 6. 任务和调度术语

| 英文术语 | 中文翻译 | 说明 | 代码示例 |
| --- | --- | --- | --- |
| Task | 任务 | 异步任务 | `sync_accounts_task()` |
| Job | 作业 | 调度作业 | APScheduler Job |
| Scheduler | 调度器 | 任务调度器 | `get_scheduler()` |
| Trigger | 触发器 | 任务触发器 | `CronTrigger` |
| Executor | 执行器 | 任务执行器 | - |
| Runner | 运行器 | 任务运行器 | - |
| Worker | 工作线程 | 后台工作线程 | - |
| Queue | 队列 | 任务队列 | - |

## 7. 数据库术语

| 英文术语 | 中文翻译 | 说明 | 代码示例 |
| --- | --- | --- | --- |
| Model | 模型 | ORM 模型 | `User`, `Instance` |
| Query | 查询 | 数据库查询 | `User.query.filter()` |
| Filter | 过滤 | 查询过滤 | `.filter(User.is_active == True)` |
| Join | 连接 | 表连接 | `.join(Role)` |
| Relationship | 关系 | 模型关系 | `db.relationship()` |
| Migration | 迁移 | 数据库迁移 | `flask db migrate` |
| Transaction | 事务 | 数据库事务 | `db.session.commit()` |
| Rollback | 回滚 | 事务回滚 | `db.session.rollback()` |

## 8. Web 开发术语

| 英文术语 | 中文翻译 | 说明 | 代码示例 |
| --- | --- | --- | --- |
| Request | 请求 | HTTP 请求 | `request.get_json()` |
| Response | 响应 | HTTP 响应 | `jsonify_unified_success()` |
| Route | 路由 | URL 路由 | `@app.route('/users')` |
| View | 视图 | 视图函数 | `def list_users()` |
| Template | 模板 | Jinja2 模板 | `render_template()` |
| Context | 上下文 | 请求/应用上下文 | `request context`, `app context` |
| Session | 会话 | 用户会话 | `session['user_id']` |
| Cookie | Cookie | HTTP Cookie | - |
| CSRF | CSRF | 跨站请求伪造 | `@require_csrf` |

## 9. 前端术语

| 英文术语 | 中文翻译 | 说明 | 代码示例 |
| --- | --- | --- | --- |
| Render | 渲染 | 页面渲染 | `render_template()` |
| Component | 组件 | UI 组件 | - |
| Chart | 图表 | 数据图表 | Chart.js |
| Modal | 模态框 | 弹出框 | Bootstrap Modal |
| Dropdown | 下拉菜单 | 下拉选择 | - |
| Tooltip | 提示框 | 悬停提示 | - |
| Pagination | 分页 | 数据分页 | - |
| Filter | 筛选 | 数据筛选 | - |
| Debounce | 防抖 | 防抖动 | - |
| Throttle | 节流 | 节流控制 | - |

## 10. 通用术语

| 英文术语 | 中文翻译 | 说明 | 代码示例 |
| --- | --- | --- | --- |
| Payload | 载荷/数据 | 请求数据 | `request.get_json()` |
| Fallback | 回退/降级 | 降级策略 | - |
| Scope | 范围 | 作用范围 | - |
| Period | 周期 | 时间周期 | `daily`, `weekly`, `monthly` |
| Cache | 缓存 | 数据缓存 | `cache_manager` |
| Hook | 钩子 | 事件钩子 | - |
| Adapter | 适配器 | 接口适配 | - |
| Factory | 工厂 | 工厂模式 | - |
| Singleton | 单例 | 单例模式 | - |
| Wrapper | 包装器 | 包装类 | - |

## 11. 错误处理术语

| 英文术语 | 中文翻译 | 说明 | 代码示例 |
| --- | --- | --- | --- |
| Error | 错误 | 错误类 | `ValidationError`, `SystemError` |
| Exception | 异常 | Python 异常 | `try...except` |
| Validation | 校验 | 数据校验 | `validate_instance_data()` |
| Authorization | 授权 | 权限授权 | `@admin_required` |
| Authentication | 认证 | 身份认证 | `@login_required` |

## 12. 状态和结果术语

| 英文术语 | 中文翻译 | 说明 | 代码示例 |
| --- | --- | --- | --- |
| Success | 成功 | 操作成功 | `ServiceResult.success()` |
| Failure | 失败 | 操作失败 | `ServiceResult.fail()` |
| Pending | 待处理 | 等待处理 | - |
| Running | 运行中 | 正在运行 | - |
| Completed | 已完成 | 已完成 | - |
| Skipped | 已跳过 | 跳过执行 | - |
| Active | 活跃/启用 | 启用状态 | `is_active=True` |
| Inactive | 非活跃/禁用 | 禁用状态 | `is_active=False` |

---

## 使用示例

### 正确的注释示例

```python
class AccountSyncService:
    """账户同步服务
    
    负责协调账户数据的同步流程，包括：
    - 账户清单管理
    - 权限快照更新
    - 数据库过滤规则应用
    """
    
    def sync_accounts(self, instance_id: int) -> ServiceResult:
        """同步指定实例的账户数据
        
        Args:
            instance_id: 实例 ID
            
        Returns:
            ServiceResult: 服务结果对象
        """
        pass
```

### 避免的注释示例

```python
# 错误：混用中英文
class AccountSyncService:
    """Account同步service"""
    
# 错误：使用不统一的术语
def sync_accounts(self):
    """同步帐号数据"""  # 应使用"账户"而非"帐号"
```

---

**相关文档**:
- [CODING_STANDARDS.md](./CODING_STANDARDS.md) - 编码规范
- [FRONTEND_STYLE_GUIDE.md](./FRONTEND_STYLE_GUIDE.md) - 前端样式指南
