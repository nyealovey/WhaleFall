# 实例/凭据/标签等资源的 Create/Edit 合并重构方案

## 背景与动因

目前多个后台实体（实例、凭据、标签、账户分类/规则、用户）在“新建 vs 编辑”场景下维护了**两套模板、两套路由、两套校验与提示逻辑**。典型例子：

- 模板层：`app/templates/instances/create.html` 与 `app/templates/instances/edit.html`（行 6-154）只有按钮文案不同；凭据、标签、用户等页面同样复制了一整份 DOM。
- 视图层：`app/routes/instance.py:262-393` 与 `app/routes/instance_detail.py:294-434` 的 `create()/edit()` 几乎逐行重复；`app/routes/credentials.py:345-437`、`app/routes/tags.py:186-365` 等亦如此。
- JS 层：`app/static/js/pages/instances/create.js` 与 `edit.js`（前 80 行）仅差“创建中/保存中”提示；凭据、标签、用户的表单脚本也分别维护两份。
- 表单校验：实例创建调用 `DataValidator.validate_instance_data`，编辑则重新写一套 `validate_required_fields/validate_db_type`；其它资源同理。
- 错误处理：每个路由都手写 try/except + flash，且文案/日志 keys 不一致。

这些重复导致：

1. **维护成本高**：字段增删需要在 4 个层级（模板/JS/校验/路由）× 多个资源 × 2 套场景里同步修改。
2. **行为不一致**：例如实例创建使用严格校验器，而编辑仅检查必填字段，埋下数据质量隐患。
3. **扩展困难**：想给所有表单新增“草稿保存/统一内联错误提示”等特性，需要在几十个文件里复制粘贴。

## 重构目标

1. **单一表单来源**：相同字段只描述一次，即可驱动模板渲染、默认值填充、前后端校验、错误提示。
2. **统一路由/服务**：每种资源仅保留一个 `upsert` 视图函数（或类视图），通过 `resource_id` 是否存在决定创建/更新。
3. **一致的交互体验**：前端采用共享的 `ResourceFormController`，统一 loading、错误提示、TagSelector/权限等可插拔组件。
4. **最小侵入**：遵循“如无必要，勿增实体”——复用现有蓝图、模板目录结构，只抽象公共能力。

## 核心设计

### 1. 资源表单定义（ResourceFormDefinition）

在 `app/forms/definitions.py` 中为每个资源定义一个轻量结构（可用 `TypedDict` 或 dataclass）：

```python
class ResourceFormDefinition(TypedDict):
    fields: list[Field]
    template: str  # form partial
    service: Type[BaseResourceService]
    permissions: PermissionConfig
```

每个 Field 描述 `name/label/type/required/choices/default/transform`，这样即可：

- 自动生成 HTML（Jinja 宏读取 definition，渲染 input/select/checkbox）。
- 生成前端校验规则（JS 读取 `data-form-definition` 中的 JSON）。
- 生成后端 schema（`pydantic` 或 Marshmallow 根据 definition 产出校验器）。

### 2. 基础服务与结果模型

新增 `app/services/resource_service.py`：

```python
class BaseResourceService(Generic[T]):
    schema: Type[BaseSchema]

    def upsert(self, payload: dict, resource: T | None = None) -> ServiceResult[T]:
        data = self.schema(**payload)     # 校验 & 归一化
        instance = resource or self.model()
        instance.assign(data)
        db.session.add(instance)
        db.session.commit()
        return ServiceResult.ok(instance)
```

各模块（实例/凭据/标签/分类/用户）只需实现少量 hook（例如标签需要校验颜色、实例需要处理标签关联等）。

### 3. 统一路由/视图

创建 `app/routes/mixins/resource_form_view.py`，封装 GET/POST：

```python
class ResourceFormView(MethodView):
    form_definition: ResourceFormDefinition

    def get(self, resource_id=None):
        ctx = self._build_context(resource_id)
        return render_template(self.form_definition["template"], **ctx)

    def post(self, resource_id=None):
        payload = request.form | request.files
        result = self.form_definition["service"]().upsert(payload, self._get_instance(resource_id))
        if result.ok:
            flash(self.form_definition["messages"]["success"], FlashCategory.SUCCESS)
            return redirect(self.form_definition["redirect_to"])
        flash(result.error, FlashCategory.ERROR)
        return render_template(self.form_definition["template"], **self._build_context(resource_id, payload))
```

各资源蓝图只需注册：

```python
instance_bp.add_url_rule(
    "/form", view_func=InstanceFormView.as_view("instance_form"), methods=["GET", "POST"],
    defaults={"resource_id": None}
)
instance_bp.add_url_rule(
    "/<int:resource_id>/form", view_func=InstanceFormView.as_view("instance_edit_form"), methods=["GET", "POST"])
```

这样 `create`/`edit` 页面都复用同一个模板和视图，只通过 URL 区分模式。

### 4. 模板与组件

- 将 `create.html` / `edit.html` 合并为 `form.html`，通过上下文变量 `form_mode`（`"create"`/`"edit"`）调整标题、按钮文案。
- 通用字段抽成宏：`components/form/fields.html` 提供 `text_input(field, value)` 等；TagSelector、权限策略等复杂区域按照“组件 + 挂钩”模式注入。
- 模板入口示例：

```jinja
{% extends "base.html" %}
{% import "components/forms/macros.html" as forms %}
{% set form_mode = 'edit' if resource.id else 'create' %}

{{ forms.render(self.form_definition, resource=resource) }}
```

### 5. 前端控制器

引入 `app/static/js/core/resource-form-controller.js`：

```js
export class ResourceFormController {
  constructor(root, config) {
    this.root = root;
    this.config = config;
    this.validator = FormValidator.create(root.querySelector('form'), config.validation);
    this.setupCommonListeners();
  }

  submit(url, method = 'POST') {
    const payload = serializeFormData(this.form);
    return http[method.toLowerCase()](url, payload)
      .then(this.handleSuccess)
      .catch(this.handleError);
  }
}
```

各页面仅需：

```js
import { ResourceFormController } from '@/core/resource-form-controller';
new ResourceFormController('#instanceForm', window.__INSTANCE_FORM__);
```

标签/权限/TagSelector 等差异化逻辑通过插件注入（同一控制器提供 `useTagSelector`, `useConnectionTest` 钩子），从而去掉 `create.js` vs `edit.js` 的分叉。

### 6. 错误与提示

统一使用 `ServiceResult`，包含 `error_code`、`message_key`，前端也读取 JSON 决定 toast/inline errors。后端 flash 语句全部走 `result.display_message`.

## 资源覆盖策略

| 资源 | 模板重复 | 视图重复 | JS 重复 | 备注 |
| --- | --- | --- | --- | --- |
| 实例 | 已合并：`app/templates/instances/form.html` | 已合并：`app/routes/instance_form_view.py` + 蓝图注册 | 已合并：`app/static/js/pages/instances/form.js` | `app/services/instances/form_service.py` 负责校验/标签 |
| 凭据 | 已合并：`app/templates/credentials/form.html` | 已合并：`app/routes/credential_form_view.py` + `credentials.py` 注册 | 已合并：`app/static/js/pages/credentials/form.js` | 服务层在 `app/services/credentials/form_service.py` |
| 标签 | `app/templates/tags/create.html` vs `edit.html` | `app/routes/tags.py:186-365` | `app/static/js/pages/tags/form.js`（已复用） | 模板仍 95% 重复，可直接切 form partial |
| 账户分类 & 规则 | `app/templates/accounts/account_classification.html:212-360`（创建/编辑模态字段重复） | JS 中 `createClassification` vs `updateClassification`、`createRule` vs `updateRule` 逻辑一致 | 可改为 `ClassificationFormModal` 组件 |
| 账户分类规则 | 同上 | 同上 | 同上 |  |
| 用户 | `app/templates/auth/list.html:112-198` 两个模态高度相似 | `app/static/js/pages/auth/list.js` 中 add/edit API 调用重复 | 可通过 `UserFormModal` 统一 |

## 迁移计划

1. **基础设施（约 1 天）**
   - 落地 `ResourceFormDefinition`、`BaseResourceService`、`ResourceFormView`、`ResourceFormController`。
   - 提供示例（如一个简化 Tag form）验证链路。
2. **实例模块（约 2 天）**
   - 定义 `InstanceFormDefinition`，整合 `DataValidator` & `_parse_is_active_value`。
   - 合并模板为 `instances/form.html`，迁移 JS 到 `pages/instances/form.js`。
   - 将 `/create` 与 `/<id>/edit` 指向新视图；保留旧 URL（301 或渲染 alias）确保链接不失效。
3. **凭据 & 标签（约 1 天）**
   - 由于字段简单，可直接套用基础设施；删除旧模板与路由。
4. **账户分类 & 规则（约 1.5 天）**
   - 将创建/编辑模态抽象成 `ClassificationFormModal`、`RuleFormModal`，前端共享 `ResourceFormController`。
   - 后端暴露 `/classifications/<id?>/upsert`、`/rules/<id?>/upsert` API。
5. **用户管理（约 0.5 天）**
   - 合并 `addUserModal`/`editUserModal`，复用 `UserFormModal`。
6. **回归与文档（约 0.5 天）**
   - 更新 README/AGENTS 里关于新建/编辑的开发指南。
   - 编写回归测试（pytest + Selenium/Playwright smoke）覆盖统一表单的主要流。

## 风险与应对

| 风险 | 影响 | 对策 |
| --- | --- | --- |
| 旧 JS 依赖全局函数，迁移到模块后可能出现加载顺序问题 | 页面交互失效 | 在功能迁移前先建立 `window.ResourceFormController = ResourceFormController` 的垫片，逐步移除 |
| 表单字段存在细微差异（如编辑多一个“测试连接”按钮） | 难以完全复用 | `form_definition` 支持 `slots`，特定页面可插入额外按钮；JS 插件化处理（例如 `useConnectionTest`） |
| 统一 schema 后不可避免出现字段严格校验导致历史脏数据保存失败 | 用户无法编辑旧记录 | 在 schema 中为可选字段提供 `allow_legacy_null=True`，并在迁移阶段运行数据清洗脚本 |
| 大量模板改动影响翻译与可读性 | PR 复杂 | 分模块提交，每个 PR 附带 before/after 截图与测试记录 |

## 成功标准

1. 每个资源的“新建/编辑”只剩 **1 个模板 + 1 个视图类 + 1 个 JS 入口**。
2. 新增字段只需修改 `ResourceFormDefinition` 和对应 schema/service。
3. 表单交互统一（loading 文案、错误提示、TagSelector 等），手工测试通过；`pytest -m "unit and (instances or tags or credentials)"` 全绿。
4. 文档（本文件 + README“前端/后端约定”）已更新，开发者能按指引扩展。

## 附：命名建议

| 组件 | 建议路径 | 说明 |
| --- | --- | --- |
| 表单定义 | `app/forms/definitions/instance.py` | 返回 `InstanceFormDefinition` |
| 服务层 | `app/services/instance_form_service.py` | 负责 upsert |
| 视图层 | `app/routes/instance_form_view.py` | 继承 `ResourceFormView` |
| 模板 | `app/templates/instances/form.html` | 使用 `form_mode` 控制标题 |
| JS | `app/static/js/pages/instances/form.js` | 导出 `initInstanceForm()` |

通过以上重构，既能清理 95% 的重复代码，又能为后续“模块化前端 + 统一验证”奠定基础，真正做到“如无必要，勿增实体”。***
