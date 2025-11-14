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

## 5. 拆分示例与优先级
| 顺序 | 目标脚本 | 主要场景 | 关键拆分动作 |
| --- | --- | --- | --- |
| P0 | `pages/accounts/account_classification.js` | 分类与规则管理 | - `modules/services/account_classifications_service.js`：封装分类、规则、权限 API<br>- `modules/stores/account_classification_store.js`：集中管理 `classifications`, `rulesByDbType`, `permissions` 等状态<br>- 视图拆为 `classification_list_view.js`, `rule_table_view.js`, `modals/form_controller.js` |
| P1 | `pages/admin/scheduler.js` | 定时任务 | - 提供 `scheduler_service.js`（jobs CRUD、reload）<br>- `scheduler_store.js` 管理 `currentJobs`, 表单初始值<br>- 视图组件：`jobs_table_view.js`, `cron_form.js`；移除模板中的独立 jQuery 依赖，入口内按需加载 |
| P1 | `components/tag_selector.js` | 标签选择组件 | - `tag_service.js` 提供 tags/categories 数据<br>- `tag_selector_store.js` 负责筛选、统计<br>- DOM 组件拆成列表、统计卡、选中列，入口返回 `TagSelector` 类供其他页面复用 |
| P2 | `pages/tags/batch_assign.js` | 批量分配 | - 服务：实例、标签、批量操作<br>- Store：选中集合、当前模式<br>- 视图：实例列表、标签列表、操作条、表单 |
| P3 | `common/capacity_stats/manager.js` | 容量统计仪表 | - 服务：统计数据查询<br>- Store：期间、过滤器、图表缓存<br>- 视图：摘要卡、图表渲染器、筛选条 |

## 6. 渐进式迁移策略
1. **建立模块目录与导出规范**：新增 `app/static/js/modules/{services,stores,views}`，补充 `README` 说明命名与依赖（引用命名规范指南）。
2. **复制式迁移**：首个目标页面（账户分类）创建 bootstrap，内部先导入旧脚本的一部分逻辑；拆分完成后删除原 `pages/...` 文件。
3. **公共依赖封装**：将 `httpU`、`DOMHelpers`、`EventBus` 改为 ESM 形式并在全局入口上临时挂载（减少 break change），最终页面只通过 import 使用。
4. **模板减负**：`base.html` 保留第三方库（Bootstrap、FontAwesome），业务脚本只加载入口文件；入口内部再引用共享模块。
5. **验证流程**：每个阶段需执行 `pytest -k <module>`（如有相关后端）、`npm run lint`（未来引入打包器后）或现有 `make quality`，并运行 `./scripts/refactor_naming.sh --dry-run` 确认命名。

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

