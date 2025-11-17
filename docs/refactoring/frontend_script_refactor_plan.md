# 前端脚本分层重构方案

## 1. 背景与诊断
- 现有页面脚本集中在 `app/static/js/pages/**` 中，以千行 IIFE 文件存在，服务访问、状态管理、DOM 操作和事件绑定交织在一起，导致协作和测试成本高。
- 多处依赖通过 `window.*` 传递，页面模板需要手工维护 `<script>` 顺序，一旦加入新依赖容易互相覆盖。
- 同一项目内同时存在 Umbrella 与 jQuery 两套 DOM/HTTP 工具，部分组件（标签选择器、批量分配、容量统计管理器）承担了组件、网关、数据整理等多重职责。

## 2. 重构目标
1. 建立 **服务层 / 状态层 / 视图层** 分层结构，实现职责内聚。
2. 统一依赖注入的方式，逐步清理 `window.*` 全局暴露。
3. 可在不中断现有功能的情况下渐进式迁移，优先拆分大文件（>600 LOC）。
4. 与 `docs/refactoring/命名规范重构指南.md` 保持一致，新模块命名采用 `snake_case`（文件）与 `CapWords`（类）原则。

## 3. 目标目录结构
```
app/static/js/
├── modules/
│   ├── services/        # 纯数据访问，封装 httpU/fetch
│   ├── stores/          # 状态管理，导出 hooks/类
│   └── views/           # 视图组件（DOM 渲染、事件）
├── bootstrap/           # 页面入口（按路由拆分）
└── legacy/              # 迁移过渡期间保留旧脚本
```
- 页面模板仅加载对应 `bootstrap/<page>.js`，在入口内部按需导入服务、store、视图。
- 共享组件（如标签选择器、权限策略中心）移动到 `modules/views/**`，禁止直接操作全局命名空间。

## 4. 分层定义
### 4.1 服务层（数据访问）
- 职责：封装接口路径、参数校验、错误转换；不包含 DOM 或状态。
- 形式：纯函数或类，例如 `account_classifications_service.js` 导出 `fetchClassifications`, `createRule`.
- 依赖：`httpU` 或未来的 `fetch` 包装器，通过显式导入。

### 4.2 状态层（store/hooks）
- 职责：维护页面状态、派发事件、组合服务层数据，向视图层暴露订阅 API。
- 形式：`createAccountClassificationStore()` 或轻量对象 + `mitt` 事件；需提供 `init()`, `subscribe()`, `getState()`, `actions`.
- 不直接触碰 DOM，可在内部缓存派生数据（例如规则统计 Map）。

### 4.3 视图层（组件/渲染器）
- 职责：渲染 DOM、绑定事件、调用 store actions，提供 `mount(el, store)` / `destroy()`。
- 组件拆分：例如列表渲染器、筛选条、表单对话框分别在独立文件中暴露 `render(listState)`。
- 可以继续基于 Umbrella/JQuery，但推荐统一为 Umbrella + 原生 API；迁移期间允许提供 `adapter/jquery.js` 封装以兼容旧代码。

### 4.4 页面入口（bootstrap）
- 每个路由入口（如 `accounts/account_classification/bootstrap.js`）负责：
  1. 解析服务器注入的初始化数据（例如 `data-*` 或 JSON script）。
  2. 初始化服务 + store。
  3. 挂载各视图组件。
  4. 在 `DOMContentLoaded`/`document.ready` 触发。

## 5. 阶段规划（服务层优先）
服务层是所有页面的“共同地基”，一旦提炼到位，其余层的拆分才能共享接口约定并复用缓存逻辑。因此按先服务、后 store、再视图的顺序推进：

### 阶段 S0：统一服务层
- **资产盘点**：梳理所有 `httpClient`/`httpU` 请求，按领域（账户分类、调度任务、标签管理、同步会话、容量统计等）归档到表格，并记录 API 地址、HTTP 方法、调用位置。
- **抽离实现**：在 `app/static/js/modules/services/` 下创建领域服务文件，例如：
  - `account_classifications_service.js`
  - `scheduler_service.js`
  - `tag_management_service.js`
  - `sync_sessions_service.js`
  - `capacity_stats_service.js`
- **进度同步**：当前 S0 所列服务已全部下沉至 `modules/services/`（详见 `docs/refactoring/service_layer_inventory.md`），后续接入新页面时保持同一入口。
- **对接方式**：每个服务导出纯函数或类，接受 `httpClient` 以及可选的配置；文件内仅包含请求与错误处理，禁止引用 DOM。
- **落地顺序**：优先覆盖“公共 API 多页面共用”的领域（标签、权限、会话、容量统计），然后处理只被单页使用的接口。
- **验收**：现有页面仍保留大文件结构，只需将内部 `httpClient.xxx` 调用替换为新服务，确保功能一致并通过 `make quality`。

### 阶段 S1：store 抽离
- 在确保所有数据请求都经过服务层后，再创建 `modules/stores/**`。Store 只依赖前述服务，任何页面状态（筛选条件、分页、模态显隐等）在 store 内集中管理。
- 先为“服务层覆盖完成 + 业务复杂度高”的场景提供 store（如账户分类、调度任务、容量统计）；简单页面暂时直接调用服务层。

### 阶段 S2：视图与入口拆分
- 当某个页面的服务层和 store 都具备后，再将原页面脚本拆成视图组件与 `bootstrap` 入口。
- 视图层文件放在 `modules/views/**` 并由 `bootstrap/<page>.js` 调用。
- 完成拆分的页面可把旧 `pages/*.js` 移至 `legacy/`，最终统一删掉。

### 服务层优先顺序建议
| 顺序 | 领域服务 | 涉及 API | 当前主要消费方 |
| --- | --- | --- | --- |
| S0-1 | `sync_sessions_service` | `/sync_sessions/api/**` | 会话中心、告警通知 |
| S0-2 | `tag_management_service` | `/tags/api/**` | 标签管理、批量分配、标签选择器 |
| S0-3 | `account_classifications_service` | `/account_classification/api/**` | 账户分类、账户统计 |
| S0-4 | `scheduler_service` | `/scheduler/api/**` | 定时任务页面 |
| S0-5 | `capacity_stats_service` | `/capacity_stats/api/**` | 容量仪表盘、统计页面 |

## 6. 渐进式迁移策略
1. **建立模块目录与导出规范**：新增 `app/static/js/modules/{services,stores,views}`，补充 `README` 说明命名与依赖（引用命名规范指南）。
2. **服务层替换行动**：按 S0 顺序，将页面中的 `httpClient` 调用逐个替换为新服务；替换后立即回归测试，保持页面剩余逻辑不变。
3. **Store/视图拆分准入**：只有当相关服务层完成且被页面稳定使用后，才启动 store 与视图的拆分，避免“边拆视图边调 API”造成的反复。
4. **公共依赖封装**：将 `httpU`、`DOMHelpers`、`EventBus` 改为 ESM 形式并在全局入口上临时挂载（减少 break change），最终页面只通过 import 使用。
5. **模板减负**：`base.html` 保留第三方库（Bootstrap、FontAwesome），业务脚本只加载入口文件；入口内部再引用共享模块。
6. **验证流程**：每轮替换需执行 `make quality`、相关 `pytest`，并运行 `./scripts/refactor_naming.sh --dry-run` 确认命名。

## 7. 页面接入指南
1. 在模板中插入 `<script type="application/json" id="page-context">...</script>`，由后端填充初始状态（如当前用户角色、默认筛选），入口读取 JSON。
2. 入口文件示例：
   ```js
   import { createAccountClassificationStore } from '../../modules/stores/account_classification_store.js';
   import { mountClassificationList } from '../../modules/views/classification_list_view.js';
   import { AccountClassificationService } from '../../modules/services/account_classifications_service.js';

   document.addEventListener('DOMContentLoaded', () => {
     const service = new AccountClassificationService(httpU);
     const store = createAccountClassificationStore(service);
     store.init();
     mountClassificationList(document.querySelector('#classificationsList'), store);
   });
   ```
3. 所有视图组件暴露 `mount`/`unmount`，避免直接操纵全局事件，提升可测试性。

## 8. 验收指标
- 每个重构页面的业务脚本分为 ≤300 行的小文件，且导入图可视化后扇出清晰。
- 模板中不再出现大量 `window.*` 注入，核心上下文通过 `data-*` 或 JSON script 传递。
- 新增代码通过 `make quality`、`make test`，并在 PR 模版中补充“命名规范”与“分层遵循”自检项。
- 组件文档补充到 `docs/refactoring/SUMMARY.md`，记录迁移状态（进行中 / 已完成）。

## 9. 后续工作
- 评估引入 Vite/ESBuild 以支持原生 ES Modules 和 Tree-shaking。
- 输出 `modules/README.md` 与代码示例，降低新成员学习成本。
- 根据迁移进度调整 `重构优先级清单.md`，保持与后端改造工作的依赖关系同步。
