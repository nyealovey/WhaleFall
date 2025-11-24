# 日志中心 Grid.js 重构方案

> 依据 `docs/refactoring/new/gridjs-migration-standard.md`，将日志中心卡片式视图统一迁移到 Grid.js + GridWrapper，实现分页/筛选/排序一致体验。

## 1. 范围与目标
- 替换 `app/templates/history/logs/logs.html` 中的卡片列表为 Grid.js 表格，同时保留统计面板、筛选器、详情弹窗。
- 后端提供标准化接口 `{ items, total, page, pages }`，并兼容既有 `/logs/api/search` 调用。
- 复用既有日志级别颜色/图标体系，并确保详情查看、复制等交互仍可用。
- 接入 filter-card 统一筛选（时间范围、级别、模块、关键词等），由 GridWrapper 承担 URL 参数拼接与刷新。

## 2. 现状概览
| 层级 | 文件 | 说明 |
| --- | --- | --- |
| 路由 | `app/routes/logs.py` | `/logs/` 页面、`/logs/api/search` 列表、`/logs/api/stats` 统计 |
| 模板 | `app/templates/history/logs/logs.html` | 统计 + 筛选 + 卡片式日志列表 |
| 前端 | `app/static/js/modules/views/history/logs/logs.js` | 手写 DOM 渲染（`createLogEntryElement`）和虚拟滚动 |
| 样式 | `app/static/css/pages/history/logs.css` | 日志卡片、级别色块、详情浮层 |

痛点：
- 没有统一分页/排序协议，后端查询参数与其他模块不一致。
- 自定义 DOM 渲染维护成本高，滚动/刷新逻辑重复。
- 与命名规范/组件标准脱节，难以复用 GridWrapper 的缓存、过滤能力。

## 3. 重构蓝图

### 3.1 后端 API 调整
- **新增** `GET /logs/api/list`：
  - 支持参数 `page`, `limit`, `sort`, `order`（默认 `timestamp desc`）以及业务参数 `level`, `module`, `search`, `hours`。
  - 查询数据来源仍为 `UnifiedLog`（或当前日志模型），查询语义保持一致。
  - 响应示例：
    ```json
    {
      "success": true,
      "data": {
        "items": [
          {
            "id": 1,
            "timestamp": "2025-03-12T15:16:08+08:00",
            "timestamp_display": "2025-03-12 15:16:08",
            "level": "ERROR",
            "module": "audit",
            "message": "login failed",
            "context": {"user_id": 12}
          }
        ],
        "total": 1524,
        "page": 1,
        "pages": 31
      }
    }
    ```
  - `items.0` 需包含展示所需的 metadata（格式化时间、上下文 JSON、定位链接等），最后一列可附加原始对象供前端 formatter 使用。
- 原 `/logs/api/search` 继续保留，用于兼容旧页面或导出接口。
- 若已有 stats 端点，可继续返回统计卡片数据；如需新增字段（例如最近 24h 错误计数）应在这里扩展。

### 3.2 前端模板与样式
- 模板中将日志列表容器替换为 `<div id="logs-grid"></div>`，并确保引入：
  ```html
  <link rel="stylesheet" href="{{ url_for('static', 'vendor/gridjs/mermaid.min.css') }}">
  <script src="{{ url_for('static', 'vendor/gridjs/gridjs.umd.js') }}"></script>
  <script src="{{ url_for('static', 'js/common/grid-wrapper.js') }}"></script>
  ```
- 保留原筛选表单结构，配合 `filter-card` 宏生成统一 UI。过滤表单应具备：级别 select、模块输入、关键词输入、最近N小时选择器。
- 样式层只需保留级别色值、上下文展示（例如 JSON view）。卡片布局相关样式可迁移/删除。

### 3.3 Grid.js 控制器
- 新建 `app/static/js/modules/views/history/logs/grid.js`（或 `list.js`）导出 `mount()`：
  - 初始化 GridWrapper：
    ```javascript
    const logsGrid = new global.GridWrapper(container, {
      columns: [
        { name: '时间', id: 'timestamp', formatter: formatTimestamp },
        { name: '级别', id: 'level', formatter: formatLevelBadge },
        { name: '模块', id: 'module' },
        { name: '消息', id: 'message', formatter: formatMessageCell },
        { id: '__meta__', hidden: true },
      ],
      server: {
        url: '/logs/api/list?sort=timestamp&order=desc',
        then: (response) => {
          const payload = response?.data || response || {};
          return (payload.items || []).map((item) => [
            item.timestamp_display || '-',
            item.level,
            item.module,
            item.message,
            item,
          ]);
        },
        total: (response) => (response?.data?.total ?? response?.total ?? 0),
      },
    });
    ```
  - `formatLevelBadge` 将 level 映射至 `badge bg-${color}`（DEBUG-secondary, INFO-info, WARNING-warning, ERROR-danger, CRITICAL-dark）。
  - `formatMessageCell` 支持点击打开详情模态（复用原 `logDetailModal`），可通过 `row.cells[last].data` 获取完整上下文。
- 通过 `GridWrapper.setFilters()` 接入筛选：
  - 绑定 `filter-card` 表单 `submit` 和 auto-change 事件。
  - 过滤参数序列化逻辑与凭据/分区模块一致，避免重复实现。
- 删除旧的 DOM 渲染逻辑（`createLogEntryElement`, 无限滚动等）。

### 3.4 交互与辅助功能
- 保持“查看详情”“复制 JSON”功能：
  - 在 grid formatter 中触发 `openLogDetail(item)`，内部调用既有模态控制器。
- 保留“导出 CSV / 刷新”等按钮，如依赖旧 store，需改为基于当前 filters 调用新 API。
- 若有实时轮询，可在 GridWrapper 上调用 `logsGrid.refresh()` 并沿用现有定时器。

## 4. 回归与测试
- ✅ `GET /logs/api/list` 支持分页/排序/筛选，返回结构满足标准。
- ✅ Grid.js 加载后发起网络请求，分页/排序按钮生效，并能带上 filter 参数。
- ✅ 不同日志级别颜色正确显示；详情模态内容一致。
- ✅ 原 `/logs/api/stats`、`/logs/api/search` 行为不变。
- ✅ 批量导出/刷新/轮询等附加功能与旧版本一致。
- 建议执行：`make test`（或 `pytest tests/integration/logs`）+ 浏览器手测。

## 5. 实施清单
1. 路由：实现 `/logs/api/list`（含单元测试/文档更新）。
2. 模板：引入 Grid.js 资源，替换日志列表容器。
3. JS：创建 `grid.js` 控制器、接入 filter-card、保留详情交互；删除旧 DOM 逻辑。
4. 样式：整理日志级别样式与表格适配，移除卡片布局 CSS。
5. 文档：更新 `docs/api/` & `docs/refactoring/` 相关章节，记录迁移影响。
