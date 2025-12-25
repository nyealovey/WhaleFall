# 001 后端 Repository / Serializer 分层重构 - 进度

> 关联方案：`docs/changes/refactor/001-backend-repository-serializer-boundary-plan.md`
>
> 开始日期：2025-12-25
>
> 最后更新：2025-12-25

## 当前状态

- 已落地样板：`GET /instances/api/instances`（route → service → repository，items 序列化改用 Flask-RESTX marshal）
- 其余域：按计划继续小步迁移（instances/ledgers/tags）

## Checklist

### Phase 0：建立契约与基准

- [x] 引入依赖：`flask-restx`（含锁文件/requirements）
- [x] 契约测试：`GET /instances/api/instances`
- [ ] 契约测试：`GET /databases/api/ledgers`
- [x] 门禁脚本：`./scripts/code_review/error_message_drift_guard.sh`
- [x] 门禁脚本：`./scripts/code_review/pagination_param_guard.sh`

### Phase 1：引入目录与最小样板（instances 列表）

- [x] 新增 `app/repositories/` 与 `InstancesRepository.list_instances`
- [x] 新增 `app/services/instances/InstanceListService.list_instances`
- [x] 新增 `app/types/listing.py` / `app/types/instances.py`（filters/DTO/pagination）
- [x] 新增 RestX marshal fields：`app/routes/instances/restx_models.py`
- [x] 收敛 route：`app/routes/instances/manage.py` 的 `list_instances_data`

## 变更记录

- 2025-12-25：完成 instances 列表样板迁移（新增 repository/service/types/restx marshal + 契约测试）
