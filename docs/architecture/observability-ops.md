# 可观测性与运维(Observability & Ops)

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2026-01-06
> 更新: 2026-01-06
> 范围: API v1 health/history logs/cache/admin, request_id/error_id 排障链路
> 关联: ./cross-cutting-capabilities.md; ../standards/backend/api-response-envelope.md; ../standards/backend/error-message-schema-unification.md

## 1. 目标

- 让研发在 5 分钟内回答: 出错了怎么定位, 该看哪些日志, 哪些 ops API 可以自助排障.

## 2. 约定与落点

- 统一错误封套: `app/utils/response_utils.py::unified_error_response` (详见 `docs/architecture/cross-cutting-capabilities.md`).
- 统一事务边界与日志: `app/utils/route_safety.py::safe_route_call` (详见 `docs/architecture/cross-cutting-capabilities.md`).
- 日志落库模型: `app/models/unified_log.py` (API 读取见 `/api/v1/logs/*`).

## 3. API 契约: `/api/v1/health`

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET | `/api/v1/health/ping` | no | 最小探活. |
| GET | `/api/v1/health/basic` | no | 基础信息, `version` 当前为硬编码值. |
| GET | `/api/v1/health` | no | DB/cache 探测 + uptime. |
| GET | `/api/v1/health/detailed` | no | 分组件健康, DB/cache/system. |
| GET | `/api/v1/health/cache` | session | cache 健康探测(需要登录). |

## 4. API 契约: `/api/v1/admin`

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET | `/api/v1/admin/app-info` | no | 返回 `APP_NAME`/`APP_VERSION`. |

## 5. API 契约: `/api/v1/logs`

权限: endpoints 目前使用 `api_permission_required("admin")`, 以 `has_permission` 的现状实现来看等价于 admin-only.

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/api/v1/logs` | 日志列表/搜索(支持 query filters). |
| GET | `/api/v1/logs/statistics` | 日志统计, 参数: `hours` (1..2160, 默认 24). |
| GET | `/api/v1/logs/modules` | module 列表. |
| GET | `/api/v1/logs/{log_id}` | 单条日志详情. |

### 5.1 查询参数(适用于 `/api/v1/logs`)

- `page`: default 1.
- `limit`: default 20, range 1..200.
- `sort`: one of `id|timestamp|level|module|message`, default `timestamp`.
- `order`: `asc|desc`, default `desc`.
- `level`: one of `DEBUG|INFO|WARNING|ERROR|CRITICAL`.
- `module`: substring match.
- `search`: substring match on `message` and `context` (JSON cast to text).
- `start_time`/`end_time`: ISO8601, optional.
- `hours`: when `start_time` and `end_time` both missing, default window is last 24 hours, max 90 days.

## 6. API 契约: `/api/v1/cache`

| Method | Path | Permission | CSRF | Notes |
| --- | --- | --- | --- | --- |
| GET | `/api/v1/cache/stats` | login | no | cache backend 统计. |
| POST | `/api/v1/cache/actions/clear-user` | `admin` | yes | payload: `instance_id`, `username`. |
| POST | `/api/v1/cache/actions/clear-instance` | `admin` | yes | payload: `instance_id`. |
| POST | `/api/v1/cache/actions/clear-all` | `admin` | yes | best-effort 清理所有 active instances. |
| POST | `/api/v1/cache/actions/clear-classification` | `update` | yes | payload: `db_type` optional (`mysql|postgresql|sqlserver|oracle`). |
| GET | `/api/v1/cache/classification/stats` | `view` | no | 分类缓存命中情况. |

## 7. 排障最短路径

1. 先从客户端拿到 `request_id`/`error_id`(来自统一错误封套).
2. 用 `GET /api/v1/logs?search=<request_id>&hours=24` 反查日志上下文.
3. 若窗口不够, 增大 `hours` 或改用 `start_time`/`end_time`.
4. 若怀疑依赖异常, 先看 `/api/v1/health/detailed`, 再结合 logs 的 `module`/`context` 继续下钻.
