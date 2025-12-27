# 003 后端 form_service 全量移除 - 进度

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2025-12-26
> 更新: 2025-12-26
> 范围: 后端写操作与表单写链路; 彻底移除 `app/services/form_service/**`
> 关联: 方案文档: [003-backend-form-service-removal-plan](003-backend-form-service-removal-plan.md)
> 前置:
> - [001-backend-repository-serializer-boundary-plan](001-backend-repository-serializer-boundary-plan.md)
> - [002-backend-write-operation-boundary-plan](002-backend-write-operation-boundary-plan.md)
> - [002-backend-write-operation-boundary-progress](002-backend-write-operation-boundary-progress.md)
>
> 开始日期: 2025-12-26
> 最后更新: 2025-12-26

## 当前状态

- 已完成: Phase F0/F4/F5/F6(门禁/表单适配层/调度任务/删除 form_service)
- 已迁移: Tags, Credentials, Users, Instances, Accounts classifications/rules 的写链路与表单 handler
- 已验证: Instances HTML 表单端到端流程(创建/编辑页面,含 tag_names 同步与模板路径)
- 门禁: `scripts/ci/form-service-import-guard.sh` 已新增, 禁止 `app.services.form_service` import
- 回归: `.venv/bin/pytest -m unit` 通过

## Checklist

### Phase F0: 前置条件与门禁(必须先完成)

- [x] 完成 `002` 的 Phase W1: 移除 form_service 内部 `commit()`, 改为 `flush()` 或交由上层事务统一处理.
- [x] 补齐写 route 的 `safe_route_call` 覆盖: create/update 等写入口必须纳入统一事务边界.
- [x] 为"将被迁移的写端点/表单"补齐最小契约测试/单测(至少覆盖错误 message_key).

### Phase F1: 以 Tags 为样板(首个域直迁)

- [x] 扩展 `app/repositories/tags_repository.py`: 新增写方法(add/delete/flush + 关系维护).
- [x] 新增 `app/services/tags/tag_write_service.py`: 迁移 TagFormService 的 normalize/validate/assign/after_save(日志)逻辑.
- [x] routes 迁移: `app/routes/tags/manage.py` 的 create/update 改为调用 `TagWriteService`, 并纳入 `safe_route_call`.
- [x] HTML 表单迁移: 从 `ResourceFormDefinition.service_class` 逐步切换到"表单适配层"(详见 Phase F4).

### Phase F2: Credentials / Users(包含 message_key 兼容)

- [x] `CredentialWriteService`: 保留"密码非必填(更新)"等校验规则与 db 错误归一化语义.
- [x] `UserWriteService`: 保留"最后一个管理员不可禁用/降级"防御逻辑与 `message_key`.
- [x] 迁移 routes: `app/routes/credentials.py`, `app/routes/users.py`.
- [x] 更新单测: 将 `tests/unit/services/test_user_form_service.py` 迁移为 write service/validator 测试.

### Phase F3: Instances(处理标签同步与关系写入)

- [x] 迁移 InstanceFormService 的 "tag_names 规范化 + 标签同步" 到 repository(关系维护)或专用同步服务.
- [x] 彻底移除 `_sync_tags()` 内的 commit/rollback; 关系写入仅做 `flush()`, 统一由事务边界 commit.
- [x] HTML 表单链路验证: 实例创建/编辑表单流程可用.

### Phase F4: 表单系统解耦(移除 BaseResourceService 依赖)

- [x] 将 `app/forms/definitions/base.py` 的 `service_class` 类型从 `BaseResourceService` 改为更窄的 Protocol(如 `ResourceFormHandler`).
- [x] `ResourceFormView` 改为依赖新 Protocol, 并在 view 内接入 `safe_route_call` 事务包装(HTML 表单也统一 commit/rollback).
- [x] 为各表单资源提供 handler/adapters(只做 payload 适配 + 调用 write services + build_context).

### Phase F5: Scheduler Jobs(从 form_service 迁出)

- [x] 将 `SchedulerJobFormService` 迁移到 `app/services/scheduler/`(例如 `scheduler_job_write_service.py`), 去除对 `BaseResourceService/ServiceResult` 的依赖.
- [x] `app/views/scheduler_forms.py` 改为调用新服务, 并维持现有错误封装结构.

### Phase F6: 删除 form_service 与清理导出入口

- [x] 删除 `app/services/form_service/**`, 并清理:
  - `app/services/auth/__init__.py`
  - `app/services/users/__init__.py`
  - `app/services/scheduler/__init__.py`
  - 以及所有引用路径
- [x] 更新/迁移单测: 移除对旧路径的 import.
- [x] 增加门禁(脚本或 CI 检查): 禁止出现 `app.services.form_service` import.

### 附录 A: 兼容/防御/回退/适配逻辑承接清单(迁移时逐条勾选)

- [x] `app/services/form_service/resource_service.py:130`: 兼容/防御 - payload 为空时回退空 dict(`payload or {}`). (已迁移至 `app/views/mixins/resource_forms.py`)
- [x] `app/services/form_service/resource_service.py:211`: 防御/回退 - `resource or self._create_instance()` 兜底实例来源. (已由 handler 的 create/update 分支承接,不再需要 `_create_instance`)
- [x] `app/services/form_service/tag_service.py:193`: 兼容 - 颜色字段空值回退默认(`... or "primary"`). (已迁移至 `app/services/tags/tag_write_service.py`)
- [x] `app/services/form_service/tag_service.py:209`: 防御/Workaround - `_create_instance()` 使用占位值规避构造函数必填约束. (已移除 BaseResourceService, 不再依赖占位实例)
- [x] `app/services/form_service/instance_service.py:123`: 防御 - 端口赋值避免空值覆盖(`... or instance.port`). (已迁移至 `app/services/instances/instance_write_service.py`)
- [x] `app/services/form_service/instance_service.py:213`: 兼容 - `tag_names` 缺失/空值回退空列表. (已迁移至 `app/services/instances/instance_write_service.py`)
- [x] `app/services/form_service/instance_service.py:242`: 防御/回退 - `_sync_tags()` 内部 commit/rollback 与异常吞吐(失败降级记录). (已迁移至 `app/services/instances/instance_write_service.py`)
- [x] `app/services/form_service/credential_service.py:207`: 兼容 - update 场景字段缺失回退旧值(`data.get(...) is not None else resource.db_type`). (已迁移至 `app/services/credentials/credential_write_service.py`)
- [x] `app/services/form_service/credential_service.py:239`: 防御/回退 - 占位密码优先读取 `WHF_PLACEHOLDER_CREDENTIAL_SECRET`, 否则随机生成. (已移除 BaseResourceService, HTML/Modal 表单更新口令可留空)
- [x] `app/services/form_service/user_service.py:253`: 防御(guard clause) - `_ensure_last_admin` 防止禁用/降级最后管理员. (已迁移至 `app/services/users/user_write_service.py`)
- [x] `app/services/form_service/password_service.py:58`: 防御 - `resource is None` 直接失败(未登录修改密码). (已迁移至 `app/services/auth/change_password_service.py`)
- [x] `app/services/form_service/scheduler_job_service.py:254`: 数据字段兼容(字段别名) - Cron 字段 `_pick(cron_weekday, cron_day_of_week, day_of_week, weekday)`. (已迁移至 `app/services/scheduler/scheduler_job_write_service.py`)
- [x] `app/services/form_service/scheduler_job_service.py:322`: 兼容/回退 - `pick_value or part` 分段兜底缺失字段. (已迁移至 `app/services/scheduler/scheduler_job_write_service.py`)
- [x] `app/services/form_service/classification_rule_service.py:218`: 数据结构兼容 - 缺失时回退旧表达式/空对象(`data.get(...) or (...)`). (已迁移至 `app/services/accounts/account_classifications_write_service.py`)
- [x] `app/services/form_service/classification_rule_service.py:242`: 规范化(canonicalization) - `json.dumps(..., sort_keys=True)` 表达式规范化与去重. (已迁移至 `app/services/accounts/account_classifications_write_service.py`)
- [x] `app/views/mixins/resource_forms.py:134`: 适配/兼容 - `_resolve_resource_id` 支持多 URL 参数名 + str->int.
- [x] `app/views/mixins/resource_forms.py:155`: 兼容/防御 - `req.get_json(silent=True) or {}` JSON 解析失败回退空 dict.
- [x] `app/utils/data_validator.py:405`: 兼容/适配 - `sanitize_form_data` 支持 MultiDict `getlist` 并压缩单值 list.
- [x] `app/utils/data_validator.py:492`: 回退(failsafe) - 动态数据库类型读取失败时回退静态白名单(并记录 warning).

## 变更记录

- 2025-12-26: 创建 `003-backend-form-service-removal-progress.md`, 同步 Phase F0-F6 Checklist 与附录 A 承接清单.
- 2025-12-26: 完成 Phase F0-F6 主链路改造, 删除 `app/services/form_service/**`, 引入 handler 适配层与 write services, 补齐门禁与单测回归.
- 2025-12-26: 补齐 Instances HTML 表单路由(create/edit)与模板,更新 Phase F3 勾选与附录 A 未决项说明.
