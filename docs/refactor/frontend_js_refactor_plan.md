# 前端 JS 分层重构蓝图

> 目的：把 `app/static/js` 中超大、全局变量密集的脚本迁移到清晰的“视图/组件/服务/工具/状态”分层体系，和 Flask 后端的 routes/services/utils 对应，从而降低耦合并提升可维护性。

## 0. 相关重构文档索引

| 文档 | 聚焦范围 | 关联层次 |
| --- | --- | --- |
| `docs/refactor/account_classification_api_modularization.md` | 账户分类前端 API 拆分 | 服务层示例 |
| `docs/reports/account_classification_service_refactor.md` | 账户分类后端服务拆分 | 与前端服务层协同 |
| `docs/refactor/capacity_aggregation_tasks_refactor.md` | 容量聚合任务 | 供 views/components 获取指标 |
| `docs/refactor/permissions_type_specific_重构文档.md` | 权限字段规范 | 组件层 & 服务层公用的 schema |
| `docs/refactor/type_specific字段统一重构方案.md` | type_specific 统一方案 | 服务/工具层校验基线 |
| `docs/refactor/变更历史描述信息优化重构文档.md` | 变更历史信息结构 | 组件层展示逻辑 |
| `docs/database_size_stats_refactoring.md` | 数据库容量统计 | 服务层 API、store 数据形态 |
| `docs/database_filters_refactoring.md` | 数据库筛选器 | 工具 + 组件抽象 |
| `docs/统计服务重构方案.md` | 统计服务 | 服务层依赖 |
| `数据库管理页面重构文档.md` | 数据库管理界面 | Views/Components 分层 |
| `去除移动端响应式设计重构文档.md` | 响应式策略调整 | 组件层样式基线 |

## 1. 推荐目录结构

参考 `textfrontend/` 示意（可依项目形态调整命名）：

```
app/static/js/
├── components/        # 纯 UI 组件（模态、表头、TagSelector 等）
│   ├── header.js
│   └── modal.js
├── views/             # 页面/路由层，负责装配组件与服务
│   ├── accounts/
│   │   └── account_classification.view.js
│   └── dashboard/
├── services/          # 业务逻辑 + API 调用
│   ├── api.js         # http/axios 二次封装
│   └── accountClassification.service.js
├── utils/             # 纯工具函数（时间、存储、格式化）
│   ├── helpers.js
│   └── storage.js
├── store/             # 全局或跨视图共享状态（可选）
│   └── state.js
├── main.js            # 入口，做初始化、路由挂载
└── index.html         # 对应模板（Flask 渲染）
```

### 层职责映射（与 Flask 对齐）
| 前端层 | 职责 | Flask 对应 | 落地要点 |
| --- | --- | --- | --- |
| Components | 仅负责 UI 渲染与交互，输入/输出通过 props/event | `templates/` | 禁止直接发请求；复用 modal、form、toast 等模式 |
| Views | 页面级 orchestrator，决定组件组合与路由切换 | `routes/` | 只通过 services 获取数据，通过 store 管理页面局部状态 |
| Services | 处理业务规则、封装 API、聚合数据 | `services/` | 统一 http 实例、错误处理、缓存；暴露 Promise 接口 |
| Utils | 纯函数工具库，无副作用 | `utils/` | 可共用在后端/前端，如格式化、校验 |
| Store | 共享状态管理（可简单对象 + 发布订阅） | `models/`/配置 | 存放登陆态、筛选条件、异步任务状态 |
| Main/Entry | 初始化、注册全局组件、挂载视图 | `app.py` | 负责把视图绑定到 DOM，注入全局配置 |

## 2. 分层改造步骤

1. **服务层统一（Services）**  
   - 建 `app/static/js/services/api.js`，承接 `http-client.js`。  
   - 按域拆分 service，引用 `api.js`；例如 `accountClassification.service.js`、`instances.service.js`。  
   - 所有视图脚本不再直接 `http.get`，统一调用 service。

2. **组件层沉淀（Components）**  
   - 列出重复 UI（TagSelector、权限 modal、通用表格/空态），迁移至 `components/`。  
   - 组件暴露 init(renderTarget, props) 或 class，供不同视图复用。  
   - 样式和事件绑定局限在组件内部，外部仅传入数据/回调。

3. **视图层拆分（Views）**  
   - 每个页面保留一个 `.view.js`，负责：初始化 store、实例化组件、调用 service。  
   - 视图层只处理业务流程（如“加载分类 → 渲染列表 → 打开编辑 modal”），不包含 DOM 细节。

4. **状态与工具（Store/Utils）**  
   - 若页面状态复杂（账户筛选、规则列表、分页），抽到 `store/`，视图与组件通过订阅方式共享。  
   - 工具函数（格式化数字、拼接查询参数）抽到 `utils/`，确保可单元测试。

5. **入口治理（main.js / 模板）**  
   - 模板中只引入 `main.js` + 编译出的 bundle（或按页面懒加载），禁止无序 `<script>` 依赖。  
   - `main.js` 根据页面 data-attribute 决定挂载哪个 view，保证按需加载。

## 3. 分层落地示例 —— 账户分类

| 层 | 文件 | 说明 |
| --- | --- | --- |
| Services | `services/accountClassification.service.js` | 封装 CRUD、auto classify、rule stats；复用 `api.js` |
| Components | `components/classification/list.js`、`components/rule/table.js` | 负责列表 DOM、交互；通过 props 接收数据 |
| Store | `store/accountClassification.store.js` | 保存分类集合、规则分组、loading 状态 |
| View | `views/accounts/account_classification.view.js` | 初始化 store，调用 service，组合组件 |
| Entry | `main.js` | `data-page="account_classification"` 时加载视图 |

当前 `app/static/js/pages/accounts/account_classification.js` 已重构为 IIFE，可作为过渡版本：下一步将内部逻辑拆分到上述层中，并仅保留一个 view 入口。

## 4. 优先级（行数 > 600 的脚本）

| 文件 | 现状 | 分层动作 |
| --- | --- | --- |
| `app/static/js/pages/accounts/account_classification.js` | 业务/视图/服务耦合 | 已初步抽出 API，继续拆到 components + store |
| `app/static/js/components/tag_selector.js` | 兼有数据拉取与 UI | 拆为 `services/tag.service.js` + `components/tagSelector.js` |
| `app/static/js/pages/admin/scheduler.js` | 任务 API + 多 Tab 逻辑 | 按 Tab 拆组件，统一 `services/scheduler.service.js` |
| `app/static/js/pages/tags/batch_assign.js` | 表单、modal、API 混杂 | Modal 归组件层，流程放 view，API 走 service |
| `app/static/js/common/capacity_stats/manager.js` | Service + Chart 混在一起 | 拆 Chart 组件、数据 service、store |
| `app/static/js/common/permission_policy_center.js` | UI + schema | schema/解析逻辑进 utils/services，UI 部分进 components |
| `app/static/js/pages/instances/detail.js` | 多 Tab 内联逻辑 | 每个 Tab 一个组件 + Shared store |

## 5. 推进路线

1. **基线搭建**：创建 `services/api.js`、`views/`、`components/`、`store/` 目录，迁移通用脚本（http-client、form-validator、toast 等）。
2. **示范页面**：以账户分类/标签管理为 pilot，完整走完“服务层 → 视图层 → 组件层”的抽离流程，形成代码模板。
3. **批量迁移**：按照优先级表，从最复杂的页面开始迭代，确保每次 PR 只聚焦一个域。
4. **工具链对齐**：完善 `docs/frontend/component_guidelines.md`、`docs/frontend/services_guidelines.md`（或沿用现有文档），要求新文件必须符合分层目录与命名规范。
5. **持续校验**：在 `make quality` 中增加 lint 规则/脚本，阻止直接在 `views/` 中出现 `http.*` 或在 `components/` 中引用全局状态的情况。

## 6. 风险与缓解

| 风险 | 描述 | 缓解策略 |
| --- | --- | --- |
| 旧脚本依赖全局变量 | TagSelector、权限弹窗等仍通过 `window.*` 共享 | 分层过程中保留兼容 namespace (`window.TagSelectorHelper`)，待所有视图替换后再移除 |
| 构建链尚未模块化 | 仍使用 `<script>` 顺序加载 | 在 `main.js` 中手动管理依赖；准备引入打包工具（Vite/Rollup）时复用该目录结构 |
| 服务层与后端契约频繁变更 | API 迁移成本高 | 所有请求集中在 `services/`；变更时仅需调整一处，并同步更新契约文档 |
| 状态管理缺乏规范 | Store 若设计不当会变成新的单点瓶颈 | 优先使用简单对象 + 订阅机制，必要时引入 Pinia/Redux；撰写 `store/README.md` 说明 |

## 7. 里程碑

1. 基础目录与 `services/api.js` 上线，完成账户分类 page 的 view/service/component 拆分。
2. TagSelector、权限中心迁移到组件层，所有页面引用新组件。
3. Scheduler & Capacity Stats 场景建立专用 store + services，Tab 逻辑独立成视图组件。
4. 输出《前端视图层开发指南》《服务层 API 约定》，并在代码评审中强制执行。

通过以上分层方案，可让每个页面的职责和 Flask 后端结构保持一致：组件像模板，视图像路由，服务像业务模块，工具像 utils。最终既能保持当前无构建工具的部署方式，又能为后续引入 Vite/模块化打牢基础。***
