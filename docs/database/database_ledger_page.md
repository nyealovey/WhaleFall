# 数据库台账页面交付说明（v1.2.3）

> 依据《docs/standards/new_feature_delivery_standard.md》，数据库台账页面必须优先复用既有组件（账户管理页面为蓝本），并完整对齐目录/命名规范。本文档提供设计意图、目录落点、接口与测试要求，供研发/评审复用。

## 1. 目标与适用范围
- 面向数据库资产运营人员，集中展示**数据库台账**（库实例、标签、负责人、容量、同步状态等）。
- 提供与“账户管理”页面一致的布局、筛选交互与 Grid.js 表格体验，便于运营团队迁移。
- 作为容量治理的基础台账，页面必须展示“数据库大小（最新采集值 + 单位）”。

## 2. 复用基线（与账户管理保持一致）
| 能力 | 账户管理引用 | 数据库台账复用策略 |
| --- | --- | --- |
| 模板继承 | `app/templates/accounts/list.html` -> `base.html` | 新建 `app/templates/databases/ledger.html`，沿用 `base.html`、`page-header`、`filter_card` 结构。 |
| 筛选面板 | `components/filters/macros.html` (`filter_card`, `search_input`) | 保留搜索/类型筛选，如需扩展环境、同步状态等过滤条件，仍统一放入 filter 卡片。 |
| Grid.js 样式/脚本 | `vendor/gridjs/*` + `js/common/grid-wrapper.js` + `accounts/list.js` | 创建 `app/static/js/modules/views/databases/ledger.js` 与 `app/static/js/bootstrap/databases/ledger.js`；样式放入 `app/static/css/pages/databases/ledger.css`，网格容器 id 统一命名为 `databases-ledger-grid`。 |
| 服务/Store | `modules/services/account_service.js` + `modules/stores/account_store.js` | 复用 `DatabaseManagementService`（若缺失则以 `instance_management_service` 为基础扩展 `fetchDatabasesLedger`）与 `DatabaseStore`；禁止把 API 调用写在 view 层。 |
| 权限相关 | `components/permission_modal.html` | 台账页面不含 TagSelector、权限操作，可按需引用权限模态。 |
| 路由蓝图 | `app/routes/account.py`（`account_bp`） | 在 `app/routes/database.py` 或新建 `app/routes/database_ledger.py`，蓝图命名 `database_ledger_bp`，函数命名 `list_databases`, `export_databases` 等动词式名称。 |

## 3. 页面结构
1. **页面头部**：
   - 标题：`<i class="fas fa-database"></i> 数据库台账`。
   - 操作按钮：导出 CSV、跳转到容量统计（沿用账户管理按钮组风格）。
2. **筛选区域**：
   - 搜索框：模糊匹配数据库名称 / 所属实例。
   - 数据库类型切换：复用账户页面的 `data-db-type-btn` 按钮逻辑。
3. **统计卡片（可选）**：如需展示总数据库数、总容量，直接使用 `components/ui/stat-card.html`；数据来源 `capacity_aggregation_tasks`。
4. **Grid.js 列定义**：（列顺序在前端 `ledger.js` 中配置）

   | 列 | 显示内容 | 备注 |
   | --- | --- | --- |
   | `database_name` | 数据库名称 + 所属实例 | 左侧主键列，点击进入详情。 |
   | `db_type` | 数据库类型图标 + 文本 | 复用 `database_type_options`。 |
   | `capacity` | **数据库大小（最新MB/GB）** | 从 `database_size_snapshots` 读取最近一条记录，格式示例：`128.4 GB (2025-11-26 23:00)`；在后端聚合后返回。 |
   | `sync_status` | 同步/监控状态 | 复用 `status_badge_renderer`。 |
   | `actions` | 查看详情、导出单条 | “查看详情”按钮弹出容量趋势模态；导出逻辑沿用账户管理。 |

## 4. 数据流与接口
### 4.1 路由/服务
- `app/routes/database.py`：新增 `@database_bp.route('/ledger')` -> `list_databases()`，渲染模板并注入：`database_type_options`, `size_unit` 等上下文。
- `app/api/databases.py`（若已有）或 `app/routes/database.py` 下 API：`GET /api/databases/ledger` 返回分页 JSON，字段与列配置一致。
- 服务层：`app/services/instances/instance_service.py` 或 `database_sync` 模块新增 `DatabaseLedgerService.get_ledger_items()`，负责聚合数据库元数据 + 最新容量（通过 `CapacityAggregationService` 获取 `latest_size_bytes`）。
- “查看详情”模态：通过 `DatabaseLedgerService.get_capacity_trend(database_id, days=30)` 聚合近 30 天按日的容量数据，格式与 `app/services/statistics/capacity_service.py` 输出保持一致。

### 4.2 ORM/查询
- 复用 `app/models/database.py`、`DatabaseSizeSnapshot`；禁止在路由拼接 SQL。
- 若需额外字段：在 `Database` 模型添加 `environment`（举例），并通过 Alembic 迁移实现。

### 4.3 前端 Store
- `app/static/js/modules/stores/database_store.js`：新增 `state.databases`, `actions.fetchLedger(params)`，响应 Grid.js 的分页/筛选；返回数据结构 `{ rows, total }`。
- View 层 `ledger.js`：
  ```js
  import { createGrid } from '../../common/grid-wrapper.js';
  import { DatabaseStore } from '../../stores/database_store.js';

  const columns = [
    { id: 'database_name', name: '数据库/实例', formatter: DatabaseNameCell },
    { id: 'db_type', name: '类型', formatter: DbTypeCell },
    { id: 'capacity', name: '数据库大小', formatter: CapacityCell },
    { id: 'sync_status', name: '状态', formatter: StatusBadgeCell },
    { id: 'actions', name: '操作', formatter: ActionsCell },
  ];
  ```
- `CapacityCell` 显示 `formatted_size` + `collected_at`。
- “查看详情”行为在 `actions` 列触发：点击后调用 `DatabaseStore.fetchCapacityTrend(databaseId)`，并复用容量统计页面中的图表组件（如 `capacity-stats/capacity-chart.js`）渲染模态框，展示近一个月每日容量变化。

## 5. 验证清单
- [ ] `make dev start` 后，`/databases/ledger` 页面加载成功，Grid.js 页签与账户管理交互一致。
- [ ] API `GET /api/databases/ledger` 支持 `search`, `db_type`, `page`, `per_page` 参数；返回体含 `database_size_bytes`, `formatted_size`, `collected_at`。
- [ ] `make test -k database_ledger`：新增的 service / route 单测需标记 `@pytest.mark.unit`；如含 API 级测试则放入 `tests/integration/databases/test_ledger.py` 并标记 `@pytest.mark.integration`。
- [ ] 运行 `make format && make quality && ./scripts/refactor_naming.sh --dry-run`，确保命名/格式通过。
- [ ] PR 描述中附带数据库台账界面截图与验证步骤。

## 6. 后续迭代建议
1. **容量趋势联动**：在行操作中提供“查看容量趋势”按钮，复用 `capacity_collection_tasks` 的 API。
2. **批量导出**：参照账户管理的 CSV 导出实现，将数据库台账字段（含容量）导出。
3. **自定义列**：未来可通过 `localStorage` 记录列显隐偏好，与 Grid.js 的 `columns` 配置联动。

> 若后续功能触达更多模块（如任务调度、同步策略），请及时更新本文档，并同步至 `README` / `About` / `CHANGELOG`。
