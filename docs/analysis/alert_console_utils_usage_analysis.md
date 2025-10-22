# 前端提示工具使用现状（更新）

**更新时间**：2025-10-17  
**扫描范围**：`app/templates/**`、`app/static/js/**`

---

## 1. 引用情况总览

| 工具 | 引入方式 | 当前使用情况 |
|------|----------|--------------|
| Toastr (`vendor/toastr`) | `base.html` 全局引入 | ✅ 实际在容量统计页面等少量模块使用 |
| 自定义 `alert-utils` | ❌ 文件已不存在 | - |
| 自定义 `console-utils` | ❌ 文件已不存在 | - |
| 页面级 `showAlert/showSuccessAlert` | 各页面内联定义 | ✅ 广泛使用（表单、列表等页面） |

> 结论：当前项目处于“部分页面使用 Toastr，其余页面自定义 Bootstrap Modal 弹框”的混合状态。

---

## 2. 页面级提示函数统计

### 2.1 内联 `showAlert` / `showSuccessAlert` 系列

| 函数 | 使用文件（节选） | 说明 |
|------|------------------|------|
| `showAlert(type, message)` | `pages/instances/list.js`、`pages/admin/scheduler.js`、`components/tag_selector.js` 等 17 个文件 | 同名函数在不同页面重复实现，参数顺序/样式存在差异 |
| `showSuccessAlert(message)` | `pages/auth/login.js`、`pages/credentials/list.js`、`pages/tags/index.js` 等 7 个文件 | 多用于表单提交成功提示 |
| `showErrorAlert(message)` | 同上 | 错误提示，通常配合 `showSuccessAlert` 出现 |
| `showWarningAlert(message)` | 同上 | 警告提示，如删除确认前 |
| `showInfoAlert` / `showConfirmAlert` / `showToast` | 未发现实际使用 | - |

**共性问题**：
- 每个页面都内联定义一套相似函数，逻辑高度重复。
- 有的使用 Bootstrap Modal，有的使用 `alert()`，缺乏一致的用户体验。
- 无集中维护点，修改样式需要逐个文件调整。

### 2.2 Toastr 使用情况

仅在容量统计相关页面发现直接调用：

| 文件 | 调用示例 |
|------|----------|
| `pages/capacity_stats/database_aggregations.js` | `toastr.success(message)` / `toastr.error(message)` |
| `pages/capacity_stats/instance_aggregations.js` | 同上 |

> 当前 Toastr 主要用于容量仪表盘页面，其他业务页面仍保留自定义弹框。

---

## 3. 建议与后续行动

### 4.1 提示统一策略

| 级别 | 建议 | 说明 |
|------|------|------|
| P0 | 统一前端提示为 Toastr | 将页面内联的 `showSuccessAlert`/`showErrorAlert` 等逐步替换为 Toastr 包装函数，避免重复实现 |
| P1 | 提供统一封装（可选） | 在 `app/static/js/common/` 下新增轻量封装，例如 `notify.success(message)` 内部调用 Toastr，便于未来调整样式 |
| P2 | 自定义弹框迁移 | 对仍需模态确认的场景（如批量删除）统一封装确认对话框，避免每页重复写 Bootstrap 代码 |

---

## 4. 核心发现总结

1. **Toastr 已全局加载，但仅少数页面调用**，大部分业务仍使用自定义 `showAlert` 弹框。
2. **提示函数重复实现严重**：多个页面内联定义 `showSuccessAlert` 等函数，建议统一封装到 `common` 目录并逐页替换。
3. **旧文档提到的 `alert-utils.js` / `console-utils.js` 已不存在**，当前代码应以 Toastr + 页面封装的弹框函数为主。

---

## 5. 参考清单

| 类型 | 文件示例 |
|------|----------|
| 自定义弹框（准备迁移到 Toastr） | `app/static/js/pages/credentials/list.js`, `app/static/js/pages/instances/*.js`, `app/static/js/pages/auth/*.js`, `app/static/js/pages/tags/*.js`, `app/static/js/pages/accounts/*.js` 等 |
| Toastr 使用样板 | `app/static/js/pages/capacity_stats/database_aggregations.js`, `app/static/js/pages/capacity_stats/instance_aggregations.js` |

---

> 建议后续由前端统一梳理“提示”封装层。例如：新增 `app/static/js/common/notify.js`，内部调用 Toastr。这样可逐步替换现有页面内联实现，提升维护效率。***
