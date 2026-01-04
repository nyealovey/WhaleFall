# DataValidator 第三方替换与请求解析统一设计

> 状态: Active
> 负责人: WhaleFall Team
> 创建: 2026-01-04
> 更新: 2026-01-04
> 范围: `app/utils/data_validator.py`, `app/forms/handlers/**`, `app/routes/**`, `app/api/v1/**`, `app/services/**`
> 关联: `docs/changes/refactor/021-dependency-and-utils-library-refactor-plan.md`, `docs/plans/2026-01-03-third-party-library-adoption-and-dependency-pruning.md`

## 摘要

目标是用成熟的 schema 库替换 `app/utils/data_validator.py::DataValidator` 的大部分职责, 并把请求取参(form/json/query, 以及 MultiDict)统一成单一入口, 让服务层只面对"已解析, 已规范化, 已校验"的 payload.

本设计选择以 `pydantic` 作为核心校验与类型转换引擎, 同时新增一个轻量的 request payload adapter 来兼容 Flask/Werkzeug 的 MultiDict 与多来源取参. 迁移完成后, `DataValidator` 已删除, 业务写链路统一走 schema + adapter.

## 目标 / 非目标

### 目标

- 单一入口: JSON, form(MultiDict), querystring 的 payload 提取与 canonicalization 统一到一个模块.
- 单一真源: 写路径的字段定义, 默认值, 类型转换, 约束校验集中在 schema.
- 一致错误口径: 继续对外抛出项目现有 `ValidationError` 文案与 `message_key`, 避免前端提示漂移.
- 兼容策略可审计: 字段别名, "空字符串转 None", 可选字段的缺失语义, 都写在 schema 层, 并有单测.

### 非目标

- 不在本阶段改动 API response envelope 结构.
- 不在本阶段重写 Flask-RESTX 的文档模型.
- 不追求一次性迁移所有路由, 以分阶段落地为准.

## 现状盘点

### DataValidator 当前职责

- 表单清洗: `sanitize_form_data` 处理 `MultiDict.getlist`, 并对 password 类字段保留原始值.
- 输入规范化: `sanitize_string` 做 strip 与 NUL 去除.
- 业务字段校验: instance/credential 相关的 name/db_type/host/port/credential_type/username/password 等.
- 批量校验: `validate_batch_data` 对 list 逐条校验并拼装错误.

### 调用点摘要

- `sanitize_form_data`: 被 `app/forms/handlers/**` 与多个 `app/services/**` 复用.
- `validate_instance_data`: 被 `InstanceWriteService` 与 `InstanceBatchCreationService` 使用.
- 其它 validate_xxx: 被 credential/password 等服务路径使用.

## 发现清单: 防御 / 兼容 / 回退 / 适配

说明: 本节以"可迁移到 schema 的规则"与"迁移时必须保留的兼容语义"为主, 重点记录 `or` 兜底与 MultiDict 适配.

- 位置: `app/utils/data_validator.py:79`
  - 类型: 防御
  - 描述: `validate_instance_data` 捕获 `ValueError/TypeError/KeyError/AttributeError` 并返回 `(False, message)`, 避免上层直接抛异常.
  - 建议: 迁移后改为捕获 schema 的 `ValidationError` 并映射为项目 `ValidationError`; 不要吞掉未知异常, 以免掩盖 bug.

- 位置: `app/utils/data_validator.py:105`
  - 类型: 防御/兼容
  - 描述: 必填字段用 `not data.get(field)` 判断缺失, `0/False` 会被当成缺失.
  - 建议: schema 层用类型与 required 表达必填, 避免 truthy/falsy 误判; 若允许 `0/False`, 必须写单测锁定.

- 位置: `app/utils/data_validator.py:113`
  - 类型: 回退
  - 描述: 可选字段只在 `if value:` 时校验, `""/0` 会直接跳过校验.
  - 建议: schema 中用 "空字符串转 None" 的 canonicalization, 再做 Optional 字段校验, 避免隐式跳过.

- 位置: `app/utils/data_validator.py:348`
  - 类型: 回退
  - 描述: `sanitize_string` 将 `None -> ""`, 并移除 NUL 后 `strip()`.
  - 建议: schema 中区分 "缺失(None)" 与 "空字符串('')"; 对安全敏感字段(如 password)优先 reject NUL 而不是悄悄改写.

- 位置: `app/utils/data_validator.py:368`
  - 类型: 回退
  - 描述: `(data or {})` 兜底, 防止 `None.items()`.
  - 建议: 新入口的类型签名明确是否允许 `None`; 不要在深层无声兜底.

- 位置: `app/utils/data_validator.py:396`
  - 类型: 适配
  - 描述: 通过 `hasattr(data, "getlist")` 识别 Werkzeug `MultiDict`, 走 `getlist` 路径.
  - 建议: 迁移到统一 payload adapter 模块, 把 MultiDict 处理从业务校验中剥离.

- 位置: `app/utils/data_validator.py:401`
  - 类型: 回退/适配
  - 描述: `multi_dict.getlist(key) or []` 兜底, 并把单元素折叠为 scalar, 多元素保留 list.
  - 建议: schema 层通过字段定义决定 "标量 vs 列表" 语义, 避免 payload 形状随输入数量变化; 对需要 list 的字段统一输出 list.

- 位置: `app/utils/data_validator.py:417`
  - 类型: 适配/防御
  - 描述: password 字段名命中 `password` 时保留 raw 值(不 strip), 以免改变用户输入.
  - 建议: schema 层对 password 字段关闭 normalize/strip, 并明确是否允许首尾空白; 行为必须有单测.

- 位置: `app/constants/database_types.py:136`
  - 类型: 兼容/适配
  - 描述: `DatabaseType.normalize` 通过别名表 `aliases.get(normalized, normalized)` 兼容 `pg/postgres/mssql/...` 输入.
  - 建议: 把 normalize 作为 schema 的 canonicalization 步骤, 输出统一 canonical 值, 并用 allowlist 校验.

- 位置: `app/services/tags/tag_write_service.py:224`
  - 类型: 回退
  - 描述: `strip() or "primary"` 使用 `or` 兜底默认值, 空字符串被强制替换为默认.
  - 建议: schema 给默认值并将空字符串 canonicalize, 从业务代码移除 `or` 兜底.

- 位置: `app/forms/handlers/instance_form_handler.py:33`
  - 类型: 适配
  - 描述: `tag_names` 被折叠为 str 时手动转换为 list, 修复 payload 形状漂移.
  - 建议: schema 统一接受 `str | list[str]` 并输出 `list[str]`, 删除 handler 层补丁.

## 方案选型

### Option A: `pydantic` + 自定义 request payload adapter(推荐)

优点:

- 强类型, schema 即类型签名, 更利于 `pyright` 与重构.
- 内置 coercion, validator, alias 支持, 适合做字段兼容与 canonicalization.
- 依赖集中, 只引入一个核心库.

代价:

- Flask request 的多来源取参仍需项目内 adapter(但可保持非常薄).
- 需要把现有中文错误文案嵌入到 validator 的 `ValueError` 中, 并约束输出格式.

### Option B: `webargs` + `marshmallow`

优点:

- request parsing 更开箱即用, 对 MultiDict/query/json 的取参更成熟.
- schema 与 request decorator 可以直接放在 route 层.

代价:

- 类型信息较弱, service 层仍多是 dict, 与当前项目的类型收敛目标不完全一致.
- 引入 2 个新依赖, 并可能与未来 `pydantic` 方案竞争.

### 选择结论

本设计选 Option A, 与 `docs/changes/refactor/021-dependency-and-utils-library-refactor-plan.md` 的 Phase 3 方向一致. 若后续发现 adapter 复杂度失控, 再评估引入 `webargs`.

## 目标架构

### 模块拆分

- `app/schemas/`(新增): 写路径 payload schema, 按 domain 分文件.
  - `instances.py`: InstanceCreatePayload, InstanceUpdatePayload, BatchCreatePayload.
  - `credentials.py`: CredentialCreatePayload, CredentialUpdatePayload.
  - `tags.py`, `users.py`, `auth.py` 等.
- `app/types/request_payload.py`(新增): 统一 request payload adapter.
  - 负责: MultiDict -> dict, json/form/query 合并策略, list 字段形状固定, password 字段 raw 保留规则.
  - 不负责: 业务字段校验(全部下沉到 schema).
- `app/utils/data_validator.py`(已删除): 原有 facade 已完成迁移并移除.

### 数据流(写路径)

1. Route/handler 获取 request(或 payload mapping).
2. 通过 `request_payload.parse(...)` 得到 canonical dict(形状稳定).
3. 调用 `Schema.model_validate(payload)` 得到 typed payload 对象.
4. Service 仅使用 payload 对象字段, 不再自己 strip/as_str/as_bool.
5. schema 校验失败时, 抛出项目 `ValidationError`(文案与 message_key 与现有一致).

## 关键规则落地方式(pydantic)

### 1) canonicalization

- 全局: 对非 password 字符串字段做 `strip` 与 NUL reject/cleanup(二选一, 以单测锁定).
- Optional 字段: 将 `""` canonicalize 为 `None`, 以消除 "空字符串 vs 未提供" 的混乱.
- db_type: `DatabaseType.normalize` 后再做 allowlist 校验.
- tag_names: schema 统一输出 `list[str]`, 并过滤空白项.

### 2) 字段别名与兼容

当字段发生重命名或前端提交形状变化时, schema 使用 alias/validation_alias 同时接受新旧字段, 输出统一 canonical 字段名. 迁移期允许 alias, 迁移完成后删除旧 alias 并保留升级说明.

### 3) 错误信息映射

- schema validator 抛出的 `ValueError("中文错误文案")` 作为用户可见 message.
- route/service 捕获 pydantic 的错误, 取第一条(或按字段聚合)映射为项目 `ValidationError`.
- 对现有依赖 `message_key` 的路径(如 password change), 在 schema 层返回稳定的 key 或由调用方按字段选择 key.

## 迁移计划(建议分阶段)

### Phase 0: 基础设施

- 引入依赖: `pydantic`(版本策略写入本节完成后再落库).
- 新增 `app/types/request_payload.py` 与单测, 覆盖:
  - MultiDict.getlist 行为.
  - password 字段 raw 保留.
  - list 字段形状固定(单值也输出 list).

### Phase 1: Instance 写链路

- 新增 instance schema, 替换 `validate_instance_data` 与 batch 校验.
- 更新 `InstanceWriteService` 与 `InstanceBatchCreationService` 使用 schema.
- 删除 service 内部重复的 parse/strip 逻辑, 以 schema 输出为准.

### Phase 2: Credential/Tag/User/Auth 写链路

- credential: required/username/password/db_type/credential_type 迁到 schema.
- tag: required + color 默认值 + name pattern 迁到 schema.
- user/change_password: 统一 password 语义, 删除 DataValidator.validate_password 的多处调用.

### Phase 3: 删除 DataValidator

- 所有调用点迁移后, 删除 `app/utils/data_validator.py` 与对应单测.
- 若仍需 MultiDict 兼容, 只保留 `request_payload` 模块.

## 验证与测试

- 单元测试:
  - request payload adapter 的 MultiDict 行为.
  - 每个 schema 的必填, 类型转换, alias, 默认值, 错误文案.
  - 批量校验: error index 文案与当前一致(或明确允许变更).
- 门禁命令:
  - `make typecheck`
  - `./scripts/ci/ruff-report.sh style`
  - `uv run pytest -m unit`

## 风险与回滚

### 风险

- 错误文案漂移: pydantic 默认错误为英文, 必须通过自定义 validator 固定中文文案.
- 形状漂移: MultiDict 单值/多值的 list 形状必须固定, 否则 handler/service 仍会出现补丁.
- 语义变化: 当前 `None -> ""` 等隐式转换可能影响业务, 必须用单测锁定并逐步收敛.

### 回滚策略

- 每个 Phase 独立 PR, 保持可 revert.
- 迁移期 `DataValidator` 可作为 facade, 出现问题可快速切回旧路径(短期).
