# 用户管理 CRUD 修复基线

## 背景

近期在“用户管理”页面定位并修复了以下问题：

- 浏览器提示用户名输入未声明 `autocomplete` 属性，影响账号输入体验。
- 创建场景校验密码必填，但编辑场景也被强制要求填写密码，导致无法“保持原密码”。
- Grid 操作列在内联 `onclick` 中直接插入用户名，遇到带引号或特殊字符的用户名会触发 `Unexpected end of input`，删除交互完全失效。

针对上述问题形成了一套更通用的修复策略，后续在凭据、分类、规则、实例、标签等模块出现类似缺陷时，可直接复用本文档作为基线，快速对齐实现。

## 目标

1. 表单输入属性、占位符、自动填充、校验规则在“创建/编辑”模式下保持一致语义。
2. JS 验证器与 DOM 状态同步，避免模式切换后沿用旧规则。
3. Grid 操作按钮的事件绑定安全、可重复使用，并且能被其它逻辑（如 Loading 状态）准确定位。
4. 形成跨模块的复用清单，便于凭据、分类、规则、实例、标签等界面照此排查。

## 通用修复策略

### 表单层

- **自动填充**：所有用户名、账号、邮箱等输入框补齐 `autocomplete`，遵循 HTML 标准关键字（如 `username`、`email`）。
- **占位符与描述**：在编辑场景需允许保持原值的输入框（密码、密钥等）明确提示“留空则保持不变”。
- **必填标记**：通过 `required` 属性和校验器双重控制，切换模式时同步更新 DOM 属性与 JS 规则。
- **CSRF 与隐藏字段**：确保 `csrf_token` 和实体 ID 使用独立隐藏输入，便于 httpU 请求复用。

### 校验器

- 使用工厂方法（如 `FormValidator.create`）初始化一次，封装 `setupValidator(mode)` 用于切换。
- 根据模式选择不同规则集，例如 `ValidationRules.user.passwordRequired` 与 `passwordOptional`。
- 模态关闭时重置表单、模式、必填标记，并调用 `validator.destroy()` 释放旧实例。

### 数据请求

- 统一通过 `httpU`（或服务层）访问 `/api` 端点，保证 CSRF 头自动带入。
- `buildPayload` 仅在有值时包含 `password`/`secret`，避免发送空字符串。

### Grid 操作列

- 每个按钮附带 `data-action`、`data-entity-id`，便于查找 DOM 元素切换 Loading 状态。
- 传递用户输入内容时使用 `encodeURIComponent`/`decodeURIComponent` 组合，禁止直接拼接到内联 JS 中。
- 若可行，优先绑定事件而非内联 `onclick`，减少注入风险。

## 迁移步骤（适用于凭据、分类、规则、实例、标签等）

1. **梳理表单**：列出每个模式下的字段，核对需要差异化校验的字段（如密码/密钥），更新占位符和 `autocomplete`。
2. **实现 `setupValidator(mode)`**：复用用户管理的模式切换模板，按模块替换对应规则（例如 `ValidationRules.credential.password`）。
3. **重置逻辑**：模态/抽屉关闭时调用 `resetForm`，除了清空表单，还需恢复 `data-form-mode`、`required`、按钮文案、提示语。
4. **Grid 按钮**：为编辑、删除、启停等按钮补充 `data-action` 和经过编码的文字参数；同时在交互函数里使用 `selectOne('[data-action="delete-xxx"][data-entity-id="${id}"]')` 获取触发源。
5. **Payload 构建**：仅拼入真实需要更新的字段，特别是敏感字段应 `trim()` 后判断空值。
6. **提示语统一**：所有 Toast/confirm 文案使用中文，含风险提示时保持一致措辞，便于全局搜索。

## 验收清单

- [ ] 创建、编辑、删除各流程在浏览器控制台无警告/错误。
- [ ] 编辑时可留空密码/密钥且后端保持原值。
- [ ] Grid 按钮在含引号、空格、中文的实体名称下仍可点击。
- [ ] Loading 状态能够依赖 `data-action` 精准还原按钮文案。
- [ ] 运行 `./scripts/refactor_naming.sh --dry-run` 无新增命名告警。

## 进一步建议

- 在 `make quality` 中加入对模板 `autocomplete`、JS 直插字符串的 lint 检查，避免再次出现类似问题。
- 针对凭据、实例、标签页，可先复制本文件作为“对照项目”，完成一处后用差异对比工具确保其它模块实现一致。
