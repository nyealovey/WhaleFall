# Compat, Defense, and Fallback Audit Report

> 状态: Draft
> 负责人: WhaleFall Team
> 创建: 2025-12-31
> 更新: 2025-12-31
> 范围: backend(app/**) + frontend(app/static/js/**, app/templates/**)
> 关联: docs/standards/documentation-standards.md, docs/standards/backend/configuration-and-secrets.md

## 摘要结论

本次审计聚焦 "兼容/防御/回退/适配" 逻辑(尤其是 `or`/`||` 兜底) 的可维护性与隐藏风险. 已完成一轮清理, 目标是: (1) 统一数据契约, (2) 消除过渡用分支, (3) 避免 `or` 误伤合法 falsy 值.

已落地的关键修复:
- 后端: 修复 `or` 兜底导致的语义错误(空对象无法落库, timeout=0 被覆盖).
- 前端: 统一 API success envelope 的消费方式, 删除多结构兼容分支.
- 清理: 移除未被引用的过渡实现与冗余 CSRF 工具, 降低重复与分叉风险.

## 范围与方法

范围:
- Python: `app/**/*.py`
- Frontend: `app/static/js/**/*.js`, `app/templates/**/*.html`
- Docs: 仅修复与删除项直接相关的引用

方法:
- 全仓库检索: `兼容`, `legacy`, `fallback`, `deprecated`, `or`, `||`, `get(... ) or get(... )`
- 针对命中点做人工语义审查, 判断其属于: 兼容/防御/回退/适配
- 优先修复: (a) 产生行为歧义的 `or`/`||` 兜底, (b) 造成契约不一致的 "多结构兼容"

## 发现清单

### P0

- 位置: app/services/accounts/account_classifications_write_service.py:416
  类型: 兼容
  描述: 规则表达式归一化使用 `expression or fallback`, 会把合法空对象 `{}` 误判为缺失并回退到旧值, 导致 "无法清空/重置表达式" 的行为分叉.
  建议: 用显式 None/空字符串判断替代 `or`, 并对解析结果做类型约束(必须为 object/dict).
  状态: 已修复

- 位置: app/utils/cache_utils.py:109
  类型: 防御
  描述: `timeout = timeout or self.default_timeout` 会把 `timeout=0` 覆盖为默认值, 使调用方无法表达 "不缓存/立即过期" 等语义.
  建议: 仅在 `timeout is None` 时回退默认值.
  状态: 已修复

- 位置: app/static/js/modules/services/account_classification_service.js:161
  类型: 兼容
  描述: `ruleStats`/`fetchPermissions` 在参数为空时返回非统一结构, 导致调用方必须兼容 `response.data.*` 与 `response.*` 两套读取方式.
  建议: service 层始终返回统一 success envelope, 允许调用方删除兼容分支并集中做错误处理.
  状态: 已修复

### P1

- 位置: app/static/js/modules/views/components/permissions/permission-viewer.js:88
  类型: 兼容
  描述: 旧实现允许 `data.data` 或 `data` 两种 payload 结构, 且包含无效的 CSRF 读取调用(返回值未使用, 与 httpU 注入逻辑重复).
  建议: 强制仅接受 success envelope, 并删除冗余 CSRF 兼容逻辑.
  状态: 已修复

- 位置: app/static/js/modules/stores/account_classification_store.js:165
  类型: 兼容
  描述: store 层存在 `response.data.* ?? response.*` 的多结构兼容读取, 会把历史债务扩散到更多调用点.
  建议: 统一只读 `response.data.*`, 若结构不符合则尽早失败并上报.
  状态: 已修复

- 位置: app/static/js/modules/views/accounts/account-classification/index.js:275
  类型: 兼容
  描述: 页面层同样存在多结构兼容读取, 与 store 重复, 增加维护成本.
  建议: 删除旧字段分支, 仅消费 v1 success envelope.
  状态: 已修复

- 位置: app/views/instance_forms.py:28
  类型: 兼容
  描述: 通过 `resource_id or instance_id` 判断表单模式, 属于过渡命名兼容, 会让 "模式判断" 依赖路由实现细节.
  建议: 实例表单仅以 `instance_id` 判断 edit mode, 并移除 create 路由的 `resource_id` 默认注入.
  状态: 已修复

- 位置: app/services/database_sync/coordinator.py:167
  类型: 兼容
  描述: `synchronize_database_inventory` 作为旧接口别名会制造 API 面增长, 增加调用歧义与文档负担.
  建议: 删除别名并统一使用 `synchronize_inventory`.
  状态: 已修复

### P2

- 位置: app/api/__init__.py:17
  类型: 回退
  描述: 通过 `before_request` 对旧 `*/api/*` 路径统一返回 410, 用于强下线阶段的用户引导与防止误调用.
  建议: 保留到 "无 legacy 调用 + 文档完成迁移" 后, 再评估是否降级为 404 或移除.
  状态: 保留

- 位置: app/utils/pagination_utils.py:45
  类型: 兼容
  描述: 兼容 `page_size -> pageSize -> limit` 的历史分页参数, 并在提供 module/action 时记录旧字段使用.
  建议: 通过日志统计确认无 legacy 参数后, 删除 `_LEGACY_PAGE_SIZE_KEYS` 及相关分支.
  状态: 保留

- 位置: app/models/permission_config.py:92
  类型: 兼容
  描述: 通过运行时探测列是否存在, 兼容 "代码已上线但迁移未完成" 的窗口期, 避免 SELECT 不存在列导致接口不可用.
  建议: 明确迁移完成时间点后移除探测逻辑, 让 schema 作为强约束, 避免长期隐藏数据漂移.
  状态: 保留

- 位置: app/services/accounts_permissions/legacy_adapter.py:51
  类型: 适配
  描述: 将 v4 snapshot view 适配为 legacy 形态(供 UI/API DTO 使用), 并在字段结构差异处做 fallback.
  建议: 以 "UI 直接消费 snapshot view" 为目标, 推进 DTO 与前端渲染升级后删除该 adapter.
  状态: 保留

- 位置: app/static/js/common/grid-wrapper.js:74
  类型: 兼容
  描述: 前端列表页对 `pageSize`/`limit` 做兼容读取与参数清理, 防止历史 URL 参数污染新分页契约.
  建议: 在确认所有入口仅产生 `page_size` 后, 删除 legacy key 处理并减少日志噪声.
  状态: 保留

## 建议与后续行动

短期(本周):
- 把 "success envelope 为唯一契约" 写入前端调用规范, 新代码禁止再引入 `response.*` 的兼容读取.
- 针对 `legacy_adapter` 设定删除门槛: UI 完成 snapshot view 渲染, 后端 DTO 去 legacy 字段.

中期(1-2 周):
- 统计 `pageSize`/`limit` 的真实使用量(前端 URL, 以及后端日志), 然后删除分页兼容分支.
- 明确 permission_configs 迁移完成时间点, 关闭 column 探测兼容逻辑.

长期(下个版本):
- 以模块为单位清理 adapter/shim, 将兼容逻辑收敛到 "入口层"(request parsing, DTO mapping), 避免散落在业务逻辑中.

## 证据与数据来源

检索命令示例:
- `rg -n \"兼容\" app -g'*.py'`
- `rg -n \"legacy|deprecated|fallback\" app -S`
- `rg -n \"\\\\|\\\\|\" app/static/js -g'*.js'`
- `rg -n \"\\\\.get\\\\(.*\\\\)\\\\s+or\\\\s+.*\\\\.get\\\\(\" app -g'*.py'`

关键文件:
- `app/api/__init__.py`
- `app/utils/pagination_utils.py`
- `app/models/permission_config.py`
- `app/services/accounts_permissions/legacy_adapter.py`
- `app/static/js/core/http-u.js`
