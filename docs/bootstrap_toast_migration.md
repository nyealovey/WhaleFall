# Bootstrap Toast 通知系统迁移方案

## 一、现状分析

### 多源通知实现导致体验不一致

- **Toastr 第三方库**  
  目录：`app/static/vendor/toastr/`。页面通过全局 `toastr` 直接调用，样式与主题脱节且引入额外静态资源。
- **`config.js` 全局函数**  
  文件：`app/static/js/common/config.js`。对外暴露 `showSuccess()` 等方法，并在缺少 `toastr` 时回退到原生 `alert`，交互阻塞且风格突兀。
- **`notify.js` 混合封装**  
  文件：`app/static/js/common/notify.js`。内部仍依赖 Toastr，并在失败时改用 Bootstrap Alert/浏览器弹窗，形成多重降级链路。
- **调用分布松散**  
  `rg "notify\." app/static` 统计约 180 处引用，集中在 `app/static/js/pages/**` 与组件脚本，混用 `notify.*`、`showSuccess()`、`toastr.*` 等写法，统一迁移成本高。

### 现存主要问题

1. UI 体验割裂：同一操作可能触发不同风格的通知。
2. 维护难度大：多套实现并存且存在多层降级逻辑。
3. 资源冗余：需要额外加载 Toastr JS/CSS。
4. API 命名不统一：新同事需要记忆多种调用方式。

## 二、迁移目标

- **只保留一套通知实现**：全面采用 Bootstrap 5.3 Toast，取消任何降级或兼容层。
- **统一开发接口**：全局仅暴露 `toast.success / error / warning / info` 等方法。
- **与现有样式体系一致**：复用 Bootstrap 主题变量，支持图标、自动关闭、位置切换等可配置行为。
- **清理历史包袱**：彻底移除 Toastr、`notify.js` 旧逻辑及 `config.js` 中的通知函数，并批量替换所有引用。

## 三、实施方案

### 3.1 建立统一的 Toast 内核

新增 `app/static/js/common/toast.js`，实现要点如下：

- 初始化单一容器（默认挂载到 `body`，支持 `top-right/top-left/bottom-right/bottom-left` 等定位）。
- 暴露 `toast.success/info/warning/error` 与 `toast.show`，内部统一映射到 Bootstrap Toast。
- 支持 `duration`、`closable`、`position`、`stackLimit`、`icon`、`ariaLive` 等可选参数，默认 4 秒自动关闭。
- 统一管理 DOM 生命周期：创建、展示、隐藏、销毁，处理多条通知堆叠顺序。
- 将 API 挂载到 `window.toast` 供历史脚本直接调用，同时保留模块化扩展空间。

### 3.2 移除旧封装并精简公共脚本

- 删除 `app/static/js/common/notify.js` 或将其改为薄包装：直接导出 `toast.*`，不再保留旧有别名。
- 在 `app/static/js/common/config.js` 中移除 `showSuccess/showError/showWarning/showInfo` 及原生 `alert` 降级逻辑，保留 Axios 配置与 `confirmDelete`。
- 不再设置 Toastr 默认项或引用任何第三方通知库。

### 3.3 模板与静态资源同步调整

- 更新 `app/templates/base.html`：去除 Toastr CSS/JS，引入新的 `toast.js`，并在 `</body>` 前追加空容器（或由脚本动态创建）。
- 删除 `app/static/vendor/toastr/` 目录下的所有文件，确保构建产物只包含 Bootstrap 资源。
- 检查是否存在 Toastr 自定义样式（`rg "toast-" static`），如无必要直接删除。

### 3.4 批量替换页面脚本调用

1. 在所有前端脚本头部声明 `/* global toast */`（若仍使用全局变量模式），确保 ESLint 不报错。
2. 调用统一替换：
   - `notify.success(...)` → `toast.success(...)`，同理处理 `error`、`warning`、`info`、`alert`。
   - `showSuccess(...)` 等函数 → `toast.success(...)`。
   - 直接 `toastr.*` 调用 → `toast.*`，移除 Toastr 专属配置对象。
3. 重点目录：  
   - 凭据与实例管理：`app/static/js/pages/credentials/*.js`、`app/static/js/pages/instances/*.js`。  
   - 管理后台：`app/static/js/pages/admin/scheduler.js`、`app/static/js/pages/accounts/account_classification.js`。  
   - 公共组件：`app/static/js/components/tag_selector.js`、`app/static/js/common/permission-modal.js`、`app/static/js/common/permission-viewer.js`。  
   - 其他涉及通知的页面脚本（可通过 `rg "notify\\.|showSuccess|toastr" app/static/js` 逐一定位）。
4. 逐个确认参数顺序：历史函数支持 `showAlert(type, message)` 与 `showAlert(message, type)` 双写法，迁移时需明确类型与消息位置，统一为 `toast.<type>(message, options)`。

### 3.5 迁移收尾与文档更新

- 移除任何遗留的全局别名（如 `window.showSuccessAlert` 等），确保只保留 `window.toast`。
- 更新开发文档与代码规范，声明“前端通知仅使用 Bootstrap Toast + `toast.*` API”。
- 检查 `scripts/`、`docs/` 等目录是否提及 Toastr，统一替换为新的方案说明。

## 四、交付成果

- `app/static/js/common/toast.js`：Bootstrap Toast 单一实现与全局入口。
- 更新后的 `app/templates/base.html`、`app/static/js/common/config.js`；不再引用 Toastr 或降级代码。
- 所有页面脚本统一使用 `toast.*`，无 `notify.*`、`showSuccess()`、`toastr.*` 残留。
- `app/static/vendor/toastr/` 目录及相关资源已清理。
- 团队文档同步新版通知方案，确保后续开发遵循统一规范。
