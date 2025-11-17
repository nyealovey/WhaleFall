## 账户分类管理页面拆分方案

### 背景问题
- `app/static/js/modules/views/accounts/account-classification/index.js` 体积约千行，集成分类 CRUD、规则 CRUD、模态管理、权限加载、自动分类等多项职责，可读性与可维护性差。
- 入口脚本与模态逻辑强耦合，测试/复用成本高，且曾多次出现初始化顺序问题（`DOMContentLoaded` 嵌套导致脚本不执行）。
- 模态的输入输出未抽象，列表刷新、表单提交之间通过全局函数交互，缺乏清晰的依赖约束。

### 拆分目标
1. **组合页面（主列表页）**  
   - 负责页面入口、分类/规则列表渲染、筛选和权限加载。  
   - 提供“新建分类/新建规则/自动分类”等入口，统一调度模态组件。  
   - 暴露 refresh 回调供模态在提交成功后调用。
2. **规则模态模块**  
   - 管理“新建规则”“编辑规则”“查看规则详情”三种场景。  
   - 内部处理表单校验、权限配置面板、规则统计展示。  
   - 通过依赖注入获取 service、toast、权限中心、成功回调。
3. **分类模态模块**  
   - 管理“新建分类”“编辑分类”。  
   - 复用颜色预览、表单校验等逻辑，并在提交后回调主页面刷新。
4. **权限配置模块/页面**  
   - 将权限配置抽离到 `permissions/policy-center-view.js`，独立处理权限数据加载、渲染和交互。  
   - 通过依赖注入与主页面/模态交互，避免在模态内直接耦合权限中心细节；如需单独路由，可在模板添加入口。

### 目录与命名规划
```
app/static/js/modules/views/accounts/account-classification/
├── index.js                          # 主组合页面（轻量入口）
├── modals/
│   ├── rule-modals.js               # 新建/编辑/查看规则
│   └── classification-modals.js     # 新建/编辑分类
├── permissions/
│   └── policy-center-view.js        # 权限配置独立模块（复杂度高，单独解耦）
```
- 继续复用 `app/static/js/modules/services/account_classification_service.js` 与 `.../stores/account_classification_store.js`（如后续要拆 store，可在 stores 目录内扩展）。
- 模态模板可放入 `templates/accounts/partials/`，主模板通过 `{% include %}` 引入。
- 命名沿用 snake_case/kebab-case，禁止 `_api` 前后缀；提交前运行 `./scripts/refactor_naming.sh --dry-run`。

### 逻辑拆分步骤
1. **抽离服务层包装**  
   - 在主入口中初始化 service，并以模块化方式向模态注入所需的 CRUD 方法（已修复的 API 包装保持不变）。
2. **迁移模态逻辑**  
   - 将 `initializeModals`、`reset*Form`、`updateColorPreview`、表单提交/填充等函数移动到新建的 `modals/*.js`。  
   - 在这些模块内创建工厂函数 `createRuleModals(deps)` / `createClassificationModals(deps)`，返回 `openCreateRuleModal()` 等方法。
3. **组合页面调用**  
   - `index.js` 只负责：
     - 启动时加载列表（调用 service/store）、初始化过滤器、绑定按钮。  
     - 接收模态模块返回的 open/close 方法，将其挂到按钮和全局兼容接口（`window.createRule` 等）。  
     - 在模态回调中刷新数据、更新下拉/权限配置。
4. **权限与校验依赖**  
   - 通过依赖注入传入 `toast`、`PermissionPolicyCenter`、`FormValidator`、`ValidationRules` 等对象，避免在模块内部直接访问全局。
5. **模板与全局函数兼容**  
   - 主页面继续暴露 `window.createRule`, `window.editRule` 等旧接口，内部委派到新模块，避免破坏现有模板中的 `onclick`。

### 验收与测试
- 在本地 `make dev start` 环境下手动验证：
  1. 分类列表加载、分页/筛选、删除、更新。
  2. 规则列表加载、查看详情、创建/编辑/删除、自动分类触发。
  3. 权限配置面板与规则统计渲染。
  4. 模态打开关闭、表单校验与 toast 行为。
- 运行 `make test` 或至少 `pytest -k account_classification`（若存在相应用例）。  
- 变更前后执行 `./scripts/refactor_naming.sh --dry-run` 确认命名符合规范。

### 风险与缓解
- **模块依赖缺失**：通过显式注入依赖并在模块初始化时校验（缺失直接抛错/提示）。  
- **全局函数兼容性**：保留原有 `window.*` API，必要时加 deprecation 日志。  
- **权限中心耦合**：新增封装以便在模块化后仍可定制 PermissionPolicyCenter 的容器与前缀。  
- **模板同步**：拆分模态 HTML 后需同步更新 Jinja/HTML 模板，避免 ID/selector 变化导致脚本失效。

### 后续优化方向
- 将列表渲染接入统一的 UI 组件库或虚拟 DOM，减少字符串拼接。  
- 评估是否需要引入更细粒度的 store（例如将规则/分类分离），方便按需刷新。  
- 若权限策略复杂，可考虑将 `PermissionPolicyCenter` 抽象为独立模块并配套测试。
