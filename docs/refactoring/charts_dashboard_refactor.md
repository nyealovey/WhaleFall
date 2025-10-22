# 图表展示与仪表盘重构计划（详细版）

## 目标
- 统一图表数据契约与时间序列格式（UTC 时间戳、统一单位）。
- 规范前端图表库使用与交互（加载态、空态、错误态）。
- 实施客户端与服务端缓存策略，减少重复拉取与计算负载。

## 范围与涉及代码位置
- 后端：`app/routes/dashboard.py`（统一接口与数据契约）
- 模板：`app/templates/dashboard/*`（统一布局与状态展示）
- 前端：`app/static/js/**`（统一请求层与图表渲染调用）

## 现状（问题点）
- 数据契约不一致：各图表使用的字段命名不统一（如 `x/y`、`time/value`、`t/v` 混用）。
- 时间语义不统一：存在本地时区与 UTC 混用，导致排序与窗口计算不一致。
- 接口散乱：缺少统一的 `/api/dashboard/*` 前缀与参数规范。
- 交互状态不统一：加载、空数据、错误提示样式和流程不一致。

## 风险
- 数据契约不一致导致前端适配成本高、错误率高。
- 缓存缺失引发后端高负载；分页/筛选缺少统一策略。

## 数据契约（统一格式）
- 时间序列统一为 UTC，字段：
  - `series`: 数组，元素为 `{ name: string, points: Array<{ t: string(ISO-UTC), v: number }> }`
  - `unit`: 字符串，统一度量单位（如 `count`, `ms`, `MB`, `%`）
  - `window`: 字符串，窗口描述（如 `24h`, `7d`，或 `{ start, end, granularity }`）
  - `meta`: 可选，包含 `granularity`, `source`, `legend` 等附加信息
- 示例：
```json
{
  "success": true,
  "message": "ok",
  "data": {
    "series": [
      { "name": "同步错误", "points": [ { "t": "2025-10-15T01:00:00Z", "v": 3 }, { "t": "2025-10-15T02:00:00Z", "v": 5 } ] },
      { "name": "成功同步", "points": [ { "t": "2025-10-15T01:00:00Z", "v": 20 }, { "t": "2025-10-15T02:00:00Z", "v": 25 } ] }
    ],
    "unit": "count",
    "window": { "start": "2025-10-14T02:00:00Z", "end": "2025-10-15T02:00:00Z", "granularity": "hour" },
    "meta": { "legend": ["成功同步", "同步错误"] }
  }
}
```

## 后端接口设计（统一 `/api/dashboard/*`）
- 约定参数（查询字符串）：
  - `start`, `end`: ISO8601 UTC，建议带 `Z` 后缀；如缺省，按 `range` 推导。
  - `range`: 枚举 `1h|24h|7d|30d`，默认 `24h`。
  - `granularity`: 枚举 `minute|hour|day`，默认按 `range` 自动选择（`<=24h` 用 `hour`，否则 `day`）。
  - `metric`: 指标键（如 `sync_success`, `sync_error`, `instance_count`）。
  - `group_by`: 可选分组键（如 `instance`, `credential`, `tag`）。
- 统一响应：使用 `APIResponse.success_response(data=...)`；错误使用 `APIResponse.error_response(code=<HTTP数值>, data={error_key, details})`。
- 示例（后端片段）：
```python
from flask import Blueprint, request
from app.utils.api_response import APIResponse
from app.utils.time_utils import TimeUtils
from app.utils.cache_manager import cache_manager

bp = Blueprint("dashboard", __name__)

@bp.route("/api/dashboard/metrics")
def api_dashboard_metrics():
    metric = request.args.get("metric", "sync_success")
    gran = (request.args.get("granularity") or "hour").lower()
    rng = (request.args.get("range") or "24h").lower()
    start = request.args.get("start")
    end = request.args.get("end")

    # 参数校验与时间窗口归一
    # 缺省时以 now()-range 推导，输入一律转 UTC
    now_utc = TimeUtils.now()
    if not end:
        end = now_utc.isoformat()
    if not start:
        # 仅示例：实际按 rng 计算
        start = TimeUtils.to_utc(end).isoformat()  # 保持UTC

    # 缓存键统一
    key = f"dashboard:{metric}:{gran}:{rng}:{start}:{end}"
    cached = cache_manager.get(key)
    if cached is not None:
        return APIResponse.success_response(data=cached)

    # 查询与组装（伪代码）
    series = [
        {"name": "成功同步", "points": [{"t": end, "v": 25}]},
        {"name": "同步错误", "points": [{"t": end, "v": 5}]},
    ]
    payload = {
        "series": series,
        "unit": "count",
        "window": {"start": start, "end": end, "granularity": gran},
    }

    cache_manager.set(key, payload, ttl=60)
    return APIResponse.success_response(data=payload)
```

## 缓存策略（服务端与客户端）
- 服务端：
  - 统一使用 `app/utils/cache_manager.py`；禁止路由直接操作底层缓存。
  - Key：`dashboard:<metric>:<gran>:<range>:<start>:<end>`。
  - TTL：默认 `60s`；重计算型统计 `300s`；稳定枚举/配置 `3600s`。
  - 失效策略：写操作不主动失效图表缓存（避免复杂耦合），短 TTL 保证近实时刷新。
- 客户端：
  - 请求合并（去抖/节流）与前端短期内存缓存；避免同窗口重复拉取。

## 权限与防护
- 鉴权：仪表盘接口默认 `login_required`；管理视图（含全局统计）使用 `admin_required`。
- 速率限制：对高频接口使用 `login_rate_limit` 等装饰器（见 `app/utils/rate_limiter.py`），并输出统一的限制响应。

## 前端接入与交互规范
- 请求层：统一使用一个数据获取器模块（如 `dashboardData.ts/js`），封装参数与错误处理。
- UI 状态：
  - 加载态：骨架或 spinner；首次加载与切换筛选项必须展示。
  - 空态：统一空数据提示与占位（如 "暂无数据"）。
  - 错误态：统一错误提示组件，解析 `APIResponse.error_response` 的 `data.error_key` 与消息。
- 图表渲染：
  - 输入统一为 `series/points` 结构；时间轴使用 UTC，页面显示时使用 `time_utils` 转中国时区（如需）。
  - 颜色与主题：从 `app/constants/colors.py` 引用统一色板；模块独立不自定义随机颜色。

## 分页与筛选（列表混合视图）
- 对需要列表/明细的子视图统一使用 `page`, `per_page`, `q`, `order` 参数；返回 `data = { items, meta }`。
- 避免在图表接口中混入大量表格数据；表格接口独立为 `/api/dashboard/table/*`。

## 迁移步骤
1) 在 `app/routes/dashboard.py` 增加统一接口 `/api/dashboard/metrics` 与 `/api/dashboard/overview`，按数据契约输出。
2) 将现有散落接口迁移到统一命名与参数规范，并统一响应到 `APIResponse`。
3) 接入 `cache_manager`，关键接口加入短 TTL 缓存；高频接口按需加速率限制。
4) 更新 `app/templates/dashboard/*` 与 `app/static/js/**`，统一状态与数据解析。
5) 清单化模块内图表与数据来源，删除重复实现与不一致契约。

## 验收标准
- 随机抽查 5 个图表接口，响应均为统一结构：`series/points/unit/window`。
- 参数：`start/end/range/granularity` 行为一致且为 UTC 语义；无本地时区混用。
- 路由层无直接 `jsonify`；统一用 `APIResponse.success_response / error_response`。
- 界面加载/空/错误态表现统一；颜色与主题引用一致。
- 服务端缓存命中生效（短时间重复请求不重复计算）。

## 风险与回滚
- 风险：调整数据契约需前端同步适配；短 TTL 缓存可能在高并发下仍存在峰值。
- 回滚：按接口维度回滚到旧实现；保留新接口与契约在独立路径以便逐步迁移。

## 产出与检查清单
- 图表数据契约与示例；交互规范与 UI 指南。
- 缓存策略说明与接口列表；导出/分享安全建议。
