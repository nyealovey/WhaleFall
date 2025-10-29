# 表单验证重构方案：全面统一为 Just-Validate

## 1. 文档概览
- **创建日期**：2025-10-29  
- **维护人**：前端团队  
- **目标**：在整个项目中统一采用 [Just-Validate](https://just-validate.dev/) 作为唯一的表单验证库  
- **当前状态**：规划阶段（预计工期 2–3 周，穿插开发不超过四个迭代）

---

## 2. 背景与问题
| 问题 | 现象 | 影响 |
| --- | --- | --- |
| 验证逻辑分散 | 各页面手写 `validateXxx` 函数 | 规则难复用，修改成本高 |
| UI 状态不一致 | 手动切换 `is-valid / is-invalid`、`toast` 提示混用 | 用户体验割裂 |
| 消息文案散落 | 错误提示直接硬编码在脚本中 | 难以统一语言与风格 |
| 复杂度失控 | 某些页面（如 `unified_search.js`）验证相关代码超过 200 行 | 增量需求风险大 |

---

## 3. 重构目标
1. **统一验证库**：全局仅保留 Just-Validate，移除手写验证与旧工具。
2. **统一交互体验**：成功状态使用 `is-valid`，错误状态使用 `is-invalid` + `.invalid-feedback`，辅助提示交给 `toast`。
3. **统一配置入口**：新增验证工具模块，集中声明规则与文案。
4. **降低重复代码**：减少 40% 以上的验证脚本行数，后续表单仅需引入工具类。
5. **保障可维护性**：形成校验用例与回归清单，降低验证相关问题。

---

## 4. Just-Validate 选型要点
- **零依赖**：无需 jQuery，可直接与当前 Bootstrap 5 + 原生 JS 栈配合。
- **体积小**：生产包 ~5KB，对前端加载影响可忽略。
- **声明式配置**：链式 API 便于阅读，支持自定义验证器与异步校验。
- **与 Bootstrap 兼容**：可配置成功/失败类名及错误标签，符合现有 UI。
- **国际化友好**：允许集中管理中文提示文案。

> 现状评估表明，使用 Just-Validate 可让典型表单脚本从 50+ 行下降至 10–15 行，验证逻辑清晰且易于扩展。

---

## 5. 统一实施策略

### 5.1 项目结构调整
```
app/static/js/
└── utils/
    ├── form-validator.js         # Just-Validate 轻封装（新增）
    └── validation-rules.js       # 通用规则 & 消息（新增）
```

- `form-validator.js`：包装 Just-Validate，提供 `addRequired`、`addMinLength`、`addPassword`、`addAsync` 等统一方法，并在内部设置默认 `errorFieldCssClass`、`successFieldCssClass`、`errorLabelCssClass`。
- `validation-rules.js`：集中定义常用规则（凭据名、实例名、端口、数据库类型、邮箱、数字区间等）和提示文案。
- 页面脚本仅负责：
  ```javascript
  const validator = window.FormValidator.create('#credentialForm');
  validator
      .useRules('#name', window.ValidationRules.credential.name)
      .onSuccess((event) => {
          event.target.submit();
      });
  ```

### 5.2 标准化交互约束
- **错误显示**：优先在字段旁通过 `.invalid-feedback` 呈现；阻塞性错误再用 `toast.error`。
- **成功状态**：通过 `is-valid` 表示，避免长期高亮，可在 `validator.onSuccess` 后统一清理。
- **异步验证**：如用户名唯一性校验，通过 `addAsync` 规则，并在后台接口增加节流。
- **禁用 submit 重复提交**：框架层自动 `lockForm: true`，页面不再手写按钮状态逻辑。

### 5.3 迁移范围与优先级
| 阶段 | 主要页面 | 备注 |
| --- | --- | --- |
| P0 | `credentials/create.js`、`credentials/edit.js`、`auth/login.js` | 高频入口，重复逻辑最多 |
| P1 | `instances/create.js`、`instances/edit.js`、`auth/change_password.js` | 规则较多，适合作为工具库验证的试金石 |
| P2 | `accounts/account_classification.js`、`admin/scheduler.js`、`unified_search.js` | 待梳理的复杂表单 |
| P3 | 低频或查询类表单 | 依赖上阶段经验，逐步统一 |

> 每个阶段结束后更新基线脚本和文档，确保后续页面按新套路实现。
>
> **当前进展**：P0（凭据创建/编辑、登录）与 P1（实例创建/编辑、修改密码）已完成迁移，下一步聚焦标签、分类、统一搜索等 P2 场景。

---

## 6. 实施步骤

1. **基础设施准备**
   - 引入 Just-Validate（静态资源或包管理）。
   - 新增 `form-validator.js`、`validation-rules.js`。
   - 在 `base.html` 中加载 Just-Validate 生产版本。

2. **编写统一规则**
   - 梳理常见字段（名称、用户名、密码、端口、数据库类型、邮箱、数字区间等）。
   - 设计错误消息模板，包含标题、正文与 `toast` 提示策略。

3. **批量迁移页面**
   - 按优先级替换旧的 `validateXxx` 函数。
   - 移除手写 DOM 操作、`toast.warning` 验证提示。
   - 编写每页对应的 `validator.onSuccess` 处理逻辑。

4. **回归与验收**
   - 运行 `make test` + 手动走查关键表单。
   - 覆盖用例：必填、长度、手机号/邮箱、异步验证失败、网络异常。
   - 收集 QA 反馈并迭代调整规则。

5. **清理与防回退**
   - 删除遗留的 `notify.warning` 等验证提示代码。
   - 在代码规范中写入“表单验证必须使用 Just-Validate 封装”。
   - 新增 ESLint/Review Checklist：禁止新增手写验证函数。

---

## 7. 交付清单
- [ ] `app/static/vendor/just-validate/just-validate.production.min.js`
- [ ] `app/static/js/utils/form-validator.js`
- [ ] `app/static/js/utils/validation-rules.js`
- [ ] 已迁移页面脚本（按优先级清单）
- [ ] 更新后的 `docs/frontend_local_setup_guide.md` 与开发规范
- [ ] QA 回归用例与 Checklist

---

## 8. 风险与规避
| 风险 | 描述 | 规避措施 |
| --- | --- | --- |
| 旧代码未彻底清理 | 某些页面仍调用手写验证 | 引入 lint 规则 & code review checklist |
| 自定义需求过多 | 特殊业务需要复杂校验 | 在 `validation-rules.js` 中扩展自定义规则，禁止直接手写 |
| QA 回归不足 | 验证逻辑变化大，需覆盖率高 | 提前编写测试脚本，执行重点路径手测 |
| 与第三方组件冲突 | 部分页面使用自定义组件 | 在试点阶段重点验证此类页面，必要时封装适配器 |

---

## 9. 验证清单
- [ ] 所有脚本中无 `validateXxx`、`notify.warning`、`is-invalid` 手工操作残留。
- [ ] `toast` 仅用于展示整体验证失败，不再承担字段错误提示。
- [ ] 新增表单遵循统一初始化模板，并引用规则模块。
- [ ] QA 覆盖新增/编辑/批量操作等关键流程，记录测试结果。
- [ ] 文档与示例代码均更新为 Just-Validate 使用方法。

> 完成以上检查后，方可宣布验证重构上线，并锁定 Just-Validate 作为唯一表单验证库。
