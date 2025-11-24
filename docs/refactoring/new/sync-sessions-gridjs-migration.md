# 会话中心 Grid.js 迁移指南

> 目标：将会话中心列表升级为 Grid.js + GridWrapper 方案，同时完整保留原有进度条样式、会话操作以及自动刷新体验。

## 1. 成果概览
- 统一分页 / 排序 / 筛选实现，所有逻辑通过 GridWrapper 内置的服务端模式完成。
- `/sync_sessions/api/sessions` 提供标准 REST 响应：`items`, `total`, `page`, `pages`，可根据 `page/limit/sort/order` 参数返回数据。
- Grid 列允许自定义 HTML，仍可重用进度条 CSS 与动画。
- 详情模态、取消会话按钮、自动刷新（30s）必须保持可用。
- 手写分页与列表渲染彻底下线。

## 2. 依赖与模板改动
| 位置 | 必须引入 | 说明 |
| --- | --- | --- |
| `templates/history/sessions/sync-sessions.html` | `vendor/gridjs/mermaid.min.css`<br>`vendor/gridjs/gridjs.umd.js`<br>`js/common/grid-wrapper.js` | Grid.js 及封装层，禁止修改 `grid-wrapper.js` |
| `app/static/css/pages/history/sync-sessions.css` | 保留 | 进度条样式来源必须延用 |

> 推荐顺序：先完成 API 调整，再在模板中增加脚本 / 样式引用，最后接入前端脚本。

## 3. 后端 API 规范化
1. **命名**：函数改为 `list_sessions`（动词短语，不得出现 `api_` 前后缀），路由仍使用 `/sync_sessions/api/sessions`。
2. **参数**：支持 `sync_type`、`sync_category`、`status`、`page`、`limit`、`sort`、`order`，默认 `sort=started_at`，`order=desc`。
3. **实现要点**
   ```python
   @sync_sessions_bp.route("/api/sessions")
   @login_required
   @view_required
   def list_sessions() -> Response:
       sync_type = request.args.get("sync_type", "").strip()
       sync_category = request.args.get("sync_category", "").strip()
       status = request.args.get("status", "").strip()
       page = max(int(request.args.get("page", 1)), 1)
       limit = min(max(int(request.args.get("limit", 20)), 1), 100)
       sort = request.args.get("sort", "started_at")
       order = request.args.get("order", "desc").lower()

       sessions = sync_session_service.get_recent_sessions(1000)
       sessions = filter_sessions(sessions, sync_type, sync_category, status)
       sessions = sort_sessions(sessions, sort, order == "desc")

       total = len(sessions)
       start, end = (page - 1) * limit, page * limit
       payload = [session.to_dict() for session in sessions[start:end]]

       return jsonify_unified_success(
           data={
               "items": payload,
               "total": total,
               "page": page,
               "pages": (total + limit - 1) // limit,
           },
           message="获取同步会话列表成功",
       )
   ```
4. **异常处理**：所有错误统一 `log_error(..., module="sync_sessions")` 后抛出 `SystemError("获取会话列表失败")`。

## 4. 前端接入步骤
所有改动位于 `app/static/js/modules/views/history/sessions/sync-sessions.js`。

### 4.1 Grid 初始化
1. `const container = document.getElementById('sessions-grid');` → 若缺失直接中断并打印错误。
2. `new GridWrapper(container, {...})` 使用下列表头定义：
   - `session_info`：组合展示 sessionId + 同步类型/分类文本。
   - 隐藏列 `session_id/sync_type/sync_category` 用于 `formatter` 读取。
   - `status`：根据状态绘制彩色 badge。
   - `progress`：`sort:false`，调用现有 `getProgressInfo`，保持条纹动画和颜色映射。
   - `started_at`、`completed_at`、`duration`、`actions`（包含详情 / 取消按钮）。
3. `server.url` 统一为 `/sync_sessions/api/sessions?sort=started_at&order=desc`。
4. `server.then` 将 `payload.items` 转换成列数组；列表首尾的纯展示列（如 `session_info`、`progress`）在 `formatter` 中生成。
5. `pagination.server.url` 与 `sort.server.url` 均复用 GridWrapper 的默认模式，只需设置 query 参数。

### 4.2 筛选联动
1. 通过 `UI.createFilterCard` 初始化 `syncFilterCard`，表单 ID 为 `#sync-sessions-filter-form`。
2. 所有 `onSubmit/onChange` 回调都调用 `applySyncFilters(values)`。
3. `applySyncFilters` 执行 `sessionsGrid.updateFilters(normalizeFilters(values))`，GridWrapper 将自动拼接到请求 URL。

### 4.3 操作与刷新
- **事件委托**：`document.getElementById('sessions-grid')` 监听 `click`，根据 `data-action=view/cancel` 调用原有 `viewSessionDetail` 与 `cancelSession`。
- **自动刷新**：`setInterval(() => sessionsGrid.refresh({ silent: true }), 30000)`。
- **空状态**：保持 GridWrapper 默认提示即可，不再手工渲染。

## 5. 渐进式迁移检查清单
1. [ ] 模板已引入 Grid.js 与 GridWrapper 资源，旧列表 DOM 删除。
2. [ ] `/sync_sessions/api/sessions` 能根据筛选、分页、排序参数返回数据，并采用 `items/total/page/pages` 格式。
3. [ ] 列表展示包含：会话信息、状态、进度条、开始/完成时间、耗时、操作按钮。
4. [ ] 详情/取消按钮响应正常；正在运行的会话可取消，结束会话不显示取消按钮。
5. [ ] 勾选筛选条件后 URL 同步（可选）且刷新仍保持条件。
6. [ ] 自动刷新不会打断用户操作（查看详情模态不应被强制关闭）。
7. [ ] 旧样式文件未删除，进度条视觉与现版一致。

完成以上步骤后，就可以在 PR 中引用本指南作为迁移说明，确保会话中心列表完全接入 Grid.js 体系。
