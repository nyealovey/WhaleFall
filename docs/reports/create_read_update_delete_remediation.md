# Create/Read/Update/Delete 全面修复方案

## 背景
- 近期在用户、凭据和实例的增删改查流程中反复出现接口不可用、数据被错误修改以及敏感信息泄露的问题，直接阻断日常运营。
- 现有测试仅覆盖 `tests/unit/services/test_database_ledger_service.py`，上述高风险路径完全缺乏自动化守护，导致缺陷容易回归。
- 本文梳理每个领域的具体现状、根因、修复动作与验证步骤，指导后续集中整改。

## 高优先级问题概览
| 范畴 | 问题摘要 | 影响 |
| --- | --- | --- |
| 用户 CRUD | 操作日志直接落盘整个请求体（含明文密码） | 密码泄露、违反合规要求 |
| 用户 CRUD | 更新接口允许将最后一个管理员降级或停用 | 可能导致系统无人可管理 |
| 凭据 CRUD | `HttpStatus` 未导入即被调用 | 创建接口直接抛 `NameError` |
| 凭据 CRUD | 前端调用 `/credentials/api/credentials`，后端只接受 `/api/create`、`/api/<id>/edit` | 创建/更新 100% 404 |
| 实例 CRUD | 删除接口引用未定义的 `batch_deletion_service` | 任意单删调用即 500 |
| 实例 CRUD | 前端走 `/instances/api/edit/<id>`，后端实现 `/instances/api/<id>/edit` | 编辑实例全部失败 |
| 实例 CRUD | `DataValidator.SUPPORTED_DB_TYPES` 固定为 5 种类型 | 运营新增的自定义数据库类型无法创建或更新实例 |
| 标签 CRUD | 缺失 `/tags/api/batch_delete`；删除接口在 JSON 请求下只返回重定向 HTML | 批量删除永远 404，单条删除前端无法感知失败 |
| 账户分类 CRUD | 不校验重名、删除不检测关联、日志动作恒为“创建” | 分类策略易被误删，审计记录失真 |
| 分类规则 CRUD | `DB_TYPE_OPTIONS` 写死且缺少唯一性校验 | 新数据库类型无法建规则，重复规则导致自动分类混乱 |

以下章节逐一展开。

---

## 用户 CRUD 修复

### 1. 日志写入明文凭据
- 现状：`create_user` 与 `update_user` 在写审计日志时直接附带 `request_data=payload`，其中包含 `password` 字段（`app/routes/users.py:177-234`）。这会把新密码落入结构化日志，既违反安全基线又难以通过日志脱敏工具补救。
- 影响：具有日志访问权限的任何人都能读取明文密码；如果日志被集中到第三方存储，还会放大泄露面。
- 修复动作：
  1. 在 `UserFormService` 或路由层引入通用 `scrub_sensitive_fields`（可复用到凭据模块），将 `password`、`confirm_password` 等字段替换为 "***" 后再写日志。
  2. 联动 Structlog 配置，在 `processor` 中兜底屏蔽常见敏感键，防止遗漏分支。
  3. 回溯现有日志索引，确认是否需要批量清理历史记录。

### 2. 缺少“最后管理员”保护
- 现状：删除接口会检查管理员数量（`app/routes/users.py:293-305`），但更新接口没有类似保护（`app/routes/users.py:211-256`）。只要把最后一个管理员的 `role` 改成 `user` 或把 `is_active` 设为 False，系统将再无可登录的管理员。
- 影响：一旦最后的管理员被误操作降级或停用，只能通过数据库手工回滚；在生产环境这属于 Sev-1。
- 修复动作：
  1. 在 `UserFormService.validate` 中判断：当 `resource.is_admin()` 且提交后的 `role` 非管理员或 `is_active` 变 False 时，先统计是否还存在其它活跃管理员，否则返回校验失败。
  2. 补充数据库层防线：可以在 `users` 表上引入部分索引或触发器，确保至少有一条 `role='admin' AND is_active=true` 的记录。
  3. 前端在降级管理员时弹出二次确认，提示风险。

### 用户验证计划
- **单元测试**：在 `tests/unit/services` 新增 `test_user_form_service.py`，覆盖
  1. `scrub_sensitive_fields` 输出；
  2. 禁止降级/停用最后管理员的校验逻辑（使用 `pytest.mark.unit`）。
- **接口测试**：在 `tests/integration` 增加用户 CRUD 场景，校验 201/200/400/409 分支。
- **手工回归**：
  1. 通过 UI 创建/编辑用户各 1 次，抓取日志验证无密码明文；
  2. 尝试降级最后管理员，确认前端弹窗+后端 400。

---

## 凭据 CRUD 修复

### 1. 缺少 `HttpStatus` 导入
- 现状：`create_credential` 返回体引用 `HttpStatus.CREATED`（`app/routes/credentials.py:275-295`），但文件头部导入列表没有 `HttpStatus`（`app/routes/credentials.py:10-35`）。
- 影响：命中接口立即抛 `NameError`，前端收到 500。
- 修复动作：
  1. 在 import 列表补充 `HttpStatus`，并加入单元测试覆盖 201 分支；
  2. 统一 `SuccessMessages`/`HttpStatus` 使用方式，避免类似遗漏。

### 2. 前后端接口路径不一致
- 现状：前端 `CredentialsService` 通过 `POST /credentials/api/credentials` 创建、`PUT /credentials/api/credentials/{id}` 更新（`app/static/js/modules/services/credentials_service.js:63-107`），但后端只接受 `/credentials/api/create` 与 `/credentials/api/<id>/edit`（`app/routes/credentials.py:275-317`）。删除接口倒是匹配，所以仅 C/U 功能完全不可用。
- 修复动作：
  1. 后端补齐 RESTful 路由：新增 `POST /credentials/api/credentials`、`PUT /credentials/api/credentials/<int:credential_id>`，沿用 `CredentialFormService`；现有旧路径暂时保留并标记弃用，前端切换完再移除。
  2. 若决定保留旧路径，则需要同步前端服务和模态脚本（`app/static/js/modules/views/credentials/modals/credential-modals.js:164-270`）改为调用 `/api/create`、`/api/<id>/edit`，并说明为何不走 RESTful。
  3. 给两种路径都加上 `pytest` 集成测试，确保 404 不再出现。

### 凭据验证计划
- **接口测试**：新增 `tests/integration/routes/test_credentials_crud.py`，覆盖创建/更新/删除、重复名称冲突、状态筛选。
- **前端冒烟**：在凭据列表中通过模态新增、编辑、删除一条记录，确认 Grid 刷新正常。

---

## 实例 CRUD 修复

### 1. 删除接口缺失依赖
- 现状：`instances.manage.delete` 直接调用 `batch_deletion_service.delete_instances(...)`（`app/routes/instances/manage.py:195-236`），但本模块既没实例化也没导入 `InstanceBatchDeletionService`。同名对象只在 `app/routes/instances/batch.py:23-55` 中定义。
- 影响：任何删除请求都会抛 `NameError: name 'batch_deletion_service' is not defined`。
- 修复动作：
  1. 在 `instances/manage.py` 顶部引入 `from app.routes.instances.batch import batch_deletion_service`，或局部实例化 `InstanceBatchDeletionService()`。
  2. 为避免循环依赖，可把服务实例化提到 `app/services/instances/batch_service.py` 并在两个路由共享。
  3. 配套补上接口测试验证删除统计字段。

### 2. 编辑接口路径颠倒
- 现状：前端模态请求 `POST /instances/api/edit/{id}`（`app/static/js/modules/views/instances/modals/instance-modals.js:205-223`），但后端真正的编辑路由是 `/instances/api/<int:instance_id>/edit`，定义在 `instances_detail_bp`（`app/routes/instances/detail.py:225-317`）。因此所有编辑都返回 404。
- 修复动作：
  1. 统一 URL。首选方式是让路由新增 `/api/edit/<int:instance_id>` 的别名，短期避免前端改动范围过大；随后在前端改为 `/api/<id>/edit`。
  2. 无论采取哪种方式，都要在模板和 `InstanceService` 里集中维护基础路径，避免字符串拼接分散在多文件。

### 3. 数据库类型白名单过时
- 现状：`DataValidator.SUPPORTED_DB_TYPES` 被硬编码为 `["mysql","postgresql","sqlserver","oracle","sqlite"]`（`app/utils/data_validator.py:35-80`），而数据库类型其实由 `database_type_configs` 表驱动（`app/models/database_type_config.py:15-86`，`app/services/database_type_service.py:13-52`）。当业务在后台新增诸如 `mongodb`、`clickhouse` 等类型时，实例创建/编辑都会因为 “不支持的数据库类型” 被拒绝。
- 修复动作：
  1. 替换 `_validate_db_type`，改为查询 `DatabaseTypeConfig.get_active_types()` 或缓存的 `DatabaseTypeService` 结果；若未命中，再检查是否属于旧白名单。
  2. 给 `DataValidator` 注入一个可配置集合，方便在单测中注入自定义类型。
  3. 在 UI 的数据库类型选择器中同步读取后端提供的列表，确保端到端一致。

### 实例验证计划
- **单元测试**：在 `tests/unit/utils/test_data_validator.py` 覆盖新数据库类型通过验证、非法类型被拒。
- **接口测试**：新增 `tests/integration/routes/test_instances_crud.py`，验证创建、编辑（含 path alias）、删除（含批量服务调用）。
- **前端冒烟**：通过模态创建一台自定义类型实例 → 编辑 → 删除，观察 Grid 与同步统计是否更新。

---

## 标签 CRUD 修复

### 1. `/tags/api/batch_delete` 缺失
- 现状：`TagManagementService` 默认端点包含 `batchDelete: "/tags/api/batch_delete"`（`app/static/js/modules/services/tag_management_service.js:5-12`），并被 `TagManagementStore.deleteTags` 直接调用（`app/static/js/modules/stores/tag_management_store.js:402-421`）。然而 `app/routes/tags/` 下不存在对应路由（`rg -n "batch_delete" app/routes` 返回空），任何批量删除都会收到 404。
- 影响：标签列表页的“批量删除”与批量操作组件完全不可用，Promise 被 reject 但 UI 只显示泛化错误，导致运营手动逐个删除，效率极低。
- 修复动作：
  1. 在 `tags_bp` 中新增 `POST /tags/api/batch_delete`，接受 `tag_ids`，校验 CSRF/权限并循环调用 `_tag_form_service`，同时检查标签是否仍被实例占用。
  2. 返回每个 ID 的处理结果（已删/跳过/因绑定失败），便于前端提示；当所有删除成功时返回 200，否则 207 Multi-Status 或 409，具体行为要在接口文档中注明。
  3. 将相同逻辑提炼为 `TagBulkService`，这样批量和单条删除共用一套校验，避免分支漂移。

### 2. 删除接口无法向 AJAX 请求返回结构化错误
- 现状：`delete(tag_id)` 在发现标签仍被实例引用时直接走 `flash + redirect`（`app/routes/tags/manage.py:81-137`），即便请求头包含 `X-Requested-With: XMLHttpRequest` 也不会返回 JSON。前端 `TagsIndexActions.confirmDelete` 是通过 `http.post('/tags/api/delete/<id>')` 调用的（`app/static/js/modules/views/tags/index.js:262-274`），导致浏览器拿到整页 HTML，当作成功处理或抛出解析异常。
- 影响：使用中的标签被删除会出现“删除成功”Toast，但实际什么都没发生，极易造成误解；控制台同时打印 `Unexpected token < in JSON`。
- 修复动作：
  1. 在进入 `flash` 分支前检测 `prefers_json`（`request.is_json` 或 `XMLHttpRequest`），命中时直接返回 `jsonify_unified_error`，HTTP 设为 `HttpStatus.CONFLICT` 并包含 `instance_count`。
  2. 将数据库删除与响应包裹在 try/except 并共用 `prefers_json` 分支，保证所有失败场景都能返回结构化错误。
  3. 前端捕获 409 后展示“仍有 N 个实例使用该标签”的提示，并引导用户先批量移除。

### 标签验证计划
- **接口测试**：新增 `tests/integration/routes/test_tags_batch_delete.py`，覆盖成功删除/部分失败/无效 ID 的返回体；为单条删除补充“标签仍被使用”分支。
- **前端冒烟**：在标签页勾选若干条执行批量删除，并尝试删除仍被实例引用的标签，确认 Toast 信息准确、Grid 自动刷新。

---

## 账户分类 CRUD 修复

### 1. 缺少重名校验
- 现状：`ClassificationFormService.validate` 只检查必填项与颜色、图标、风险等级合法性（`app/services/form_service/classification_service.py:33-90`），但是模型层的 `AccountClassification.name` 带有 `unique=True`（`app/models/account_classification.py:35-74`）。一旦创建/编辑提交重名，SQLAlchemy 抛 `IntegrityError`，`BaseResourceService.upsert` 只返回通用的“保存失败”，最终接口 500。
- 影响：运营在 UI 上看不到“名称重复”的提示，重复点击会反复触发 500，并且日志里只有数据库错误堆栈，排查成本高。
- 修复动作：
  1. 在 `validate` 中新增唯一性查询：`AccountClassification.query.filter(AccountClassification.name == normalized["name"])`，编辑时排除自身。
  2. 命中时返回 `ServiceResult.fail("分类名称已存在")` 并附带 `message_key="NAME_EXISTS"`，方便前端定制文案。
  3. 为保证事务一致性，依旧保留数据库层唯一索引并针对 `IntegrityError` 做兜底映射。

### 2. 删除未检查关联
- 现状：`delete_classification` 只禁止 `is_system` 为 True 的记录（`app/routes/accounts/classifications.py:226-272`），但没有确认该分类是否仍绑定规则或账号；虽然模型关系声明了 `cascade="all, delete-orphan"`，但这会在没有提示的情况下直接把所有规则和分配记录硬删除。
- 影响：误删线上某个高优分类会同时清空其规则与账号分配，自动分类随即退化，难以及时发现。
- 修复动作：
  1. 删除前统计 `rules.count()` 与 `account_assignments.filter_by(is_active=True).count()`，如果大于 0，直接返回 409 并提示需要先迁移或使用 `force=true`。
  2. 若确实提供强制删除能力，必须在请求体中要求 `confirm_name` 字段等二次确认，并记录操作者与删除数量。

### 3. 审计日志动作恒为“创建”
- 现状：`ClassificationFormService.after_save` 使用 `action = "创建账户分类成功" if instance.id else "更新账户分类成功"`（`app/services/form_service/classification_service.py:62-90`），由于 SQLAlchemy 在新建完成后立刻填充 `instance.id`，该条件在创建和更新场景下都为 True，导致所有日志都写成“创建”。
- 影响：审计面板无法区分是真正的创建还是编辑，安全、运营无法追溯修改历史。
- 修复动作：
  1. 复用 `_is_create` 标记（可在 `validate`/`assign` 阶段注入），按标记而非 `instance.id` 选择日志文案。
  2. 顺便补充日志字段（旧值/新值 diff 或至少 `priority`、`color`）以便后续审计。

### 分类验证计划
- **单元测试**：新增 `tests/unit/services/test_classification_form_service.py`，覆盖重名校验、`_is_create` 日志分支、删除前关联检测。
- **接口测试**：新增 `tests/integration/routes/test_account_classifications_crud.py`，验证创建/更新/删除（含强制删除）以及 409 分支。
- **手工回归**：通过 UI 删除仍有规则的分类，确认前端收到阻断提示并保持原数据。

---

## 分类规则 CRUD 修复

### 1. 数据库类型选项写死
- 现状：`account_classification_rule_constants.DB_TYPE_OPTIONS` 永远只包含 MySQL/PostgreSQL/SQLServer/Oracle（`app/forms/definitions/account_classification_rule_constants.py:5-12`）。一旦在数据库类型配置里新增 `mongodb`、`clickhouse` 等类型（`database_type_configs` 表），规则表单就无法选择，`ClassificationRuleFormService` 也会以 “数据库类型取值无效” 拒绝（`app/services/form_service/classification_rule_service.py:33-84`）。
- 影响：新数据源即使已经可以在实例模块使用，也无法纳入分类规则，自动分类覆盖率被限制在老四种数据库。
- 修复动作：
  1. 将 `DB_TYPE_OPTIONS` 改为运行时从 `DatabaseTypeService.get_active_types()` 拉取，并在前端（规则表单、筛选器）复用统一 API。
  2. 在校验阶段允许传入自定义类型列表，便于单测注入。

### 2. 缺少唯一性与冲突校验
- 现状：`ClassificationRuleFormService.validate` 没有检查 (rule_name, classification_id, db_type) 组合是否重复，也没有校验同一分类下是否已有同一 `rule_expression`（`app/services/form_service/classification_rule_service.py:33-112`），同一字段可以被多条规则重复命中，导致自动分类服务一口气打多个标签。
- 影响：运营多次导入 Excel 或复制规则时会悄悄生成重复规则，自动分类统计出现翻倍数据，定位困难。
- 修复动作：
  1. 在校验阶段增加查询：`ClassificationRule.query.filter_by(classification_id=..., db_type=..., rule_name=...)`，编辑时排除自身。
  2. 对 `rule_expression`（JSON）做 Canonical 排序后参与比较，阻止表达式完全一致的重复规则。
  3. 数据库层可补充联合唯一索引 `(classification_id, db_type, rule_name)`；若表达式需要唯一，可额外存储哈希字段。

### 分类规则验证计划
- **单元测试**：在 `tests/unit/services/test_classification_rule_form_service.py` 中覆盖新增的类型来源、重复规则检测、表达式哈希校验。
- **接口测试**：新增 `tests/integration/routes/test_classification_rules_crud.py`，验证创建新类型规则、重复规则返回 409、更新后缓存被刷新。
- **自动分类回归**：运行 `app/services/account_classification/auto_classify_service` 的集成测试，确保重复规则不再产生重复 assignment。

---

## 共性改进与流程要求
- **命名规范**：所有重构前后都要执行 `./scripts/refactor_naming.sh --dry-run`，并在 PR 描述附上“输出为无需要替换的内容”的截图或日志。
- **质量门禁**：
  1. 在 `make quality` 中新增针对用户/凭据/实例路由的 `pytest -m "unit"`、`pytest -m "integration"`；
  2. `make test` 至少包含新增的 CRUD 测试模块，确保 CI 能捕获回归。
- **日志与监控**：为关键 CRUD 接口补充结构化字段（entity_id、operator_id、elapsed_ms），并在统一告警面板中设置 5xx 阈值。

---

## 推进计划（建议）
1. **第 1 天：补齐依赖与路由**
   - 导入 `HttpStatus`、`batch_deletion_service`，新增实例编辑别名路由，打通凭据接口（RESTful 别名）。
2. **第 2 天：安全与校验**
   - 实现日志脱敏、管理员保护、动态数据库类型校验；同步前端接口路径。
3. **第 3 天：测试与验证**
   - 补上所有单元/集成测试，执行 `make test`、`make quality`、`./scripts/refactor_naming.sh --dry-run` 并整理验证记录。
4. **持续治理**
   - PR 模板增加“CRUD 命名/路径检查”项，避免同类问题回归；定期审查日志确认无明文凭据。

完成以上步骤后，用户、凭据、实例、标签以及分类/规则的 CRUD 全链路才能恢复稳定，并具备足够的自动化覆盖来防止再次回归。
