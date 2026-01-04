# DataValidator 第三方替换与请求解析统一进度

> 状态: Active
> 负责人: WhaleFall Team
> 创建: 2026-01-04
> 更新: 2026-01-04
> 范围: `app/schemas/**`, `app/types/request_payload.py`, `app/forms/handlers/**`, `app/api/v1/**`, `app/services/**`
> 关联方案: `docs/plans/2026-01-04-data-validator-third-party-replacement-design.md`
> 关联: `docs/changes/refactor/021-dependency-and-utils-library-refactor-plan.md`, `docs/changes/refactor/021-dependency-and-utils-library-refactor-progress.md`

---

## 当前状态(摘要)

- 决策已锁定: Option A(pydantic + request payload adapter).
- 已完成迁移: services/forms 写链路已切换到 schema + adapter, `DataValidator` 已删除.
- 已补齐单测与门禁: `uv run pytest -m unit`, `make typecheck`.
- 已生成 Ruff style 报告: 当前仓库基线存在 docstring 缺口(非本次变更引入), 见 `docs/reports/ruff_style_2026-01-04_152853.txt`.

## Checklist

### Phase 0: 决策与基线

- [x] 决策锁定: Option A(pydantic + request payload adapter)
- [x] 跑通门禁: `make typecheck`
- [ ] 跑通门禁: `./scripts/ci/ruff-report.sh style`(当前仓库基线失败, 非本次变更引入)
- [x] 跑通门禁: `uv run pytest -m unit`
- [x] 记录现有行为基线: MultiDict(getlist), password raw 保留, list 字段形状, 错误文案

### Phase 1: Request payload adapter(统一取参)

- [x] 新增模块: `app/types/request_payload.py`, 统一 JSON mapping 与 MultiDict 的基础规范化
- [x] 规则: MultiDict.getlist, list 字段形状固定, password 字段 raw 策略(显式字段集合)
- [x] 单测: adapter 的 MultiDict 与 list 形状用例
- [x] 路由/handler/service 侧收敛: 移除 `DataValidator.sanitize_form_data` 调用

### Phase 2: Schema 基建(pydantic)

- [x] 引入依赖: `pydantic`
- [x] 新增目录: `app/schemas/`, 按 domain 拆分 schema 文件
- [x] 新增错误映射 helper: pydantic error -> 项目 `ValidationError`(含 message_key 规则)
- [x] 单测: 错误映射与中文错误文案锁定

### Phase 3: Instance 写链路迁移

- [x] 新增 schema: InstanceCreatePayload, InstanceUpdatePayload
- [x] 迁移 `app/services/instances/instance_write_service.py` 写路径, 移除重复 strip/parse
- [x] 迁移 `app/services/instances/batch_service.py` 批量校验与错误拼装
- [x] 单测: instance create/update/batch(含 db_type alias, tag_names 形状)

### Phase 4: Credential/Tag/User/Auth 写链路迁移

- [x] credentials: 必填/username/password/db_type/credential_type 迁到 schema
- [x] tags: required + color 默认值 + name pattern 迁到 schema
- [x] users: username/role/password 规则迁到 schema
- [x] auth(change_password): password 规则与 message_key 映射迁到 schema
- [x] 单测: 每条写链路的 schema 校验与错误文案

### Phase 5: 删除 DataValidator 与旧入口

- [x] 迁移所有引用点(含 forms handlers 与 services)
- [x] 删除 `app/utils/data_validator.py` 与 `tests/unit/utils/test_data_validator.py`(确认无引用后)
- [x] 更新参考文档: `docs/reference/api/services-utils-documentation.md`

### Phase 6: 发现清单闭环(迁移完成后清理)

说明: 本 Phase 对应设计文档 `## 发现清单: 防御 / 兼容 / 回退 / 适配`. 要求在迁移完成后逐项关闭, 避免把临时兼容逻辑长期保留.

- [x] 原位置: `app/utils/data_validator.py:79`
  - 类型: 防御
  - 问题: 捕获运行时异常并返回错误字符串, 可能掩盖非校验类 bug.
  - 处理: 只捕获 schema 校验错误并映射为 `ValidationError`; 未知异常直接抛出并记录日志.

- [x] 原位置: `app/utils/data_validator.py:105`
  - 类型: 防御/兼容
  - 问题: 必填字段用 truthy 判断, `0/False` 可能被误判为缺失.
  - 处理: schema 明确 required 与可选, 并为 `0/False` 场景补单测(若业务允许).

- [x] 原位置: `app/utils/data_validator.py:113`
  - 类型: 回退
  - 问题: 可选字段只在 truthy 时校验, `""/0` 可能跳过校验.
  - 处理: schema canonicalize(`"" -> None`) 后再做 Optional 校验, 禁止依赖 truthy 分支.

- [x] 原位置: `app/utils/data_validator.py:348`
  - 类型: 回退
  - 问题: `None -> ""` 可能抹平 "缺失" 与 "空串" 的语义; NUL 清理策略需明确.
  - 处理: 统一定义 canonicalization 规则(哪些字段 `"" -> None`, 哪些字段保留空串); 对 password 明确是否允许首尾空白与 NUL, 并用单测锁定.

- [x] 原位置: `app/utils/data_validator.py:368`
  - 类型: 回退
  - 问题: `(data or {})` 在深层兜底, 容易隐藏调用方传参错误.
  - 处理: adapter/schema 的入参类型签名明确是否允许 None; 非法类型直接报错, 不做 silent fallback.

- [x] 原位置: `app/utils/data_validator.py:396`
  - 类型: 适配
  - 问题: MultiDict 识别与处理逻辑散落在业务代码中.
  - 处理: MultiDict 适配只存在于 request payload adapter, 业务层只接收 canonical dict 或 schema 对象.

- [x] 原位置: `app/utils/data_validator.py:401`
  - 类型: 回退/适配
  - 问题: 单值折叠为 scalar, 多值为 list, 导致 payload 形状随输入数量漂移.
  - 处理: adapter/schema 固定 list 字段形状(单值也输出 list), 并为关键字段(tag_names 等)补单测.

- [x] 原位置: `app/utils/data_validator.py:417`
  - 类型: 适配/防御
  - 问题: password 字段保留 raw 的规则依赖字段名包含 "password", 语义隐式.
  - 处理: 在 schema/adapter 明确列出 password 字段集合或按 schema 字段元信息驱动, 禁止依赖字符串包含判断.

- [x] 原位置: `app/constants/database_types.py:136`
  - 类型: 兼容/适配
  - 问题: db_type alias normalize 与 allowlist 校验分散, 容易出现 "校验通过但写入值不 canonical" 的分裂.
  - 处理: schema 中统一执行 `DatabaseType.normalize` 后再校验 allowlist, 输出 canonical db_type.

- [x] 原位置: `app/services/tags/tag_write_service.py:224`
  - 类型: 回退
  - 问题: `strip() or "primary"` 由业务代码兜底默认值.
  - 处理: schema 提供默认值与空串 canonicalize, 移除业务层 `or` 兜底.

- [x] 原位置: `app/forms/handlers/instance_form_handler.py:33`
  - 类型: 适配
  - 问题: handler 层对 `tag_names` 做 str -> list 的补丁, 说明 payload 形状不稳定.
  - 处理: adapter/schema 统一接受 `str | list[str]` 并输出 `list[str]`, 删除 handler 层补丁.

## 变更记录

- 2026-01-04: 完成 Option A 迁移, 删除 `DataValidator`, 新增 schema + adapter, 通过 `uv run pytest -m unit` 与 `make typecheck`.
