# Admin Scheduler 重构方案

## 1. 背景概述

当前 `app/static/js/pages/admin/scheduler.js` 体积接近 1K 行，集中了任务列表渲染、Cron 配置、表单校验、操作按钮、批量重载、日志提示等所有逻辑，且仍依赖 jQuery/原生 DOM。随着调度功能扩展，维护成本和可读性急剧上升，需要拆分为可复用模块并接入 Umbrella/DOMHelpers 体系。

## 2. 主要问题

1. **职责耦合严重**：同一文件处理 API 调用、状态管理、表单校验和 UI 渲染，缺乏分层。
2. **大量重复代码**：Cron 预览、加载态/恢复、按钮状态切换在多个场景复制；未抽公用工具。
3. **DOM 操作混乱**：遍布 `$(...)`、`document.getElementById`、内联 HTML 拼接，难以读写。
4. **可测试性差**：逻辑全写在事件回调中，无法单独测试任务数据转换或 Cron 生成。
5. **缺少服务层**：HTTP 请求散落各处，既有 `$.ajax` 又有 `httpU`，错误处理不统一。

## 3. 重构目标

1. **分层架构**：拆分“服务（API 调用）/状态管理/视图组件（列表、表单、Cron 面板）”三层。
2. **统一 DOM 与事件**：全部改用 `DOMHelpers.selectOne/select/ready` + Umbrella 事件，移除 jQuery 依赖。
3. **封装公共逻辑**：提取 Cron 预览生成器、Loading/按钮状态辅助、模态框控制器等工具。
4. **统一 HTTP**：仅通过 `httpU` 封装请求，集中处理 CSRF/错误提示。
5. **可组合模块**：将任务表、表单、批量操作拆成独立模块，便于后续增删功能。

## 4. 目标架构

```
app/static/js/pages/admin/
├── scheduler/
│   ├── index.js              // 页面入口：ready -> mount SchedulerPage
│   ├── services.js           // 任务 API 封装：list/enable/disable/run/reload...
│   ├── cron-preview.js       // Cron 输入 -> 表达式生成 & 预览
│   ├── form-controller.js    // 新增/编辑表单逻辑、Validator 集成
│   ├── job-table.js          // 列表渲染 & 行内操作按钮绑定
│   ├── batch-ops.js          // 批量操作、重载按钮等
│   └── utils.js              // Loading/按钮状态/模态控制等工具
```

## 5. 迁移步骤

1. **基础设施**：
   - 抽离 `SchedulerServices`（基于 `httpU`）并集中处理错误提示。
   - 编写 `CronPreview` 模块，支撑新增/编辑两处输入。
2. **视图组件**：
   - `JobTable`：负责列表渲染、绑定启停/执行/编辑按钮，内部仅接受数据和事件回调。
   - `FormController`：封装新增/编辑表单、Validator 回调、按钮 Loading。
   - `BatchOps`：管理批量重载、批量启停按钮的状态与事件。
3. **入口重写**：
   - `scheduler/index.js` 中通过 `ready()` 初始化页面实例，订阅 EventBus 时机统一。
   - 入口负责注入依赖（服务/组件）并协调刷新。
4. **清理遗留**：
   - 移除 jQuery 依赖、全局 `$(document).ready` 与 `$(document).on`。
   - 清理内联 HTML 拼接，改用模板函数或 `DOMHelpers` 创建节点。
5. **验证 & 文档**：
   - 更新 Umbrella 迁移文档中对 scheduler 的状态说明。
   - 补充 README 或调度页面开发指南，描述新模块结构与扩展方法。

## 6. 风险与注意事项

1. **批量操作/重载**：需要确认后台接口幂等性及错误返回格式，避免 UI 状态错乱。
2. **Cron 表达式兼容**：重构后需覆盖 5/6/7 段 Cron 的输入测试，以防生成表达式有偏差。
3. **Validator 集成**：在拆分表单控制器时要保持现有 `addJobValidator`、`editJobValidator` 的行为一致。
4. **国际化/提示**：当前提示文本较多，重构时留意是否抽取常量或支持多语言。

## 7. 验收标准

- `scheduler.js` 页面入口 < 200 行，主要负责装配组件。
- DOM 操作全部通过 DOMHelpers，代码中不再出现 `$()` 或 `document.getElementById`。
- 所有 HTTP 请求走 `SchedulerServices`，且具备一致的 Loading/错误提示。
- Cron 预览逻辑统一由 `cron-preview.js` 提供，新增/编辑共享实现。
- PR 通过既有单测/集成场景，功能与现状保持一致或更佳。
