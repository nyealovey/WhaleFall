# Compat/Fallback/Migration Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 全面清点并清理项目中的兼容/回退/防御/迁移残留代码，收敛行为与契约，避免“静默兜底”导致问题长期潜伏。

**Architecture:** 先做静态扫描产出清单 → 按风险分组（无行为影响/低风险/高风险）→ 先清理“无行为影响”的残留 → 再逐步收敛兼容/兜底逻辑并补齐契约测试 → 最后跑门禁与单元测试验证。

**Tech Stack:** Flask, Flask-RESTX, SQLAlchemy, APScheduler, Jinja2, Vanilla JS/ES Modules, pytest, `scripts/ci/*` guards.

---

## Audit Findings (Checklist)

### A) 兼容 / 回退（Backward-compat / Fallback）

- `app/settings.py:103`：`_resolve_sqlite_fallback_url()` 在 `DATABASE_URL` 缺失时回退到本地 `userdata/whalefall_dev.db`（隐式默认 DB）。  
  - 现状：production 缺失 `DATABASE_URL` 会直接失败；非 production 缺失会回退 SQLite 并记录 warning（避免静默误用）。
- `app/settings.py`：已移除运行时修改 `DYLD_LIBRARY_PATH` 的兼容逻辑。  
  - 现状：应用不会在运行时注入/补全 `DYLD_LIBRARY_PATH`；Oracle thick mode 客户端库定位请使用 `ORACLE_CLIENT_LIB_DIR` / `ORACLE_HOME`（见 `app/services/connection_adapters/adapters/oracle_adapter.py` 与 `docs/reference/database/database-drivers.md`）。
- `app/services/account_classification/dsl_v4.py:42`：Prometheus 指标 `prometheus_client` optional dependency，缺失时走 Noop metrics。  
  - 风险：监控“悄悄失效”；但对轻量部署友好（可保留，需明确策略）。
- `app/services/accounts_sync/permission_manager.py:76`：同类 Prometheus optional dependency + Noop metrics。
- `app/static/js/modules/stores/logs_store.js:146`：分页字段兼容读取 `limit ?? per_page ?? perPage`。  
  - 风险：前端契约不收敛；后端返回字段漂移难被发现。
- `app/views/mixins/resource_forms.py:236`：fallback redirect：`url_for()` 异常时回退首页。  
  - 风险：异常被吞后只表现为“跳回首页”，可观测性不足；建议捕获更具体异常并记录日志。
- `app/__init__.py:125`：调度器初始化失败不影响应用启动（启动阶段兜底继续）。  
  - 风险：生产环境可能“看似启动成功但任务全失效”；建议按环境决定是否 fail-fast。

### B) 迁移残留（Migration Residue）

- `app/templates/instances/detail.html:325`：包含大段已废弃的服务端渲染账户表格（Jinja 注释块）。  
  - 风险：文件噪声巨大，后续维护易误改/误读；建议删除并在文档中保留历史记录（若需要）。
- `app/__init__.py:97`：注释“迁移期新旧并行”与当前 `app/api/__init__.py`（仅注册 `/api/v1`）不一致。  
  - 风险：误导维护者判断系统状态。
- `/api/v1` 模块大量 docstring 标记 Phase（如 `app/api/v1/__init__.py:41`、各 namespace 顶部）。  
  - 风险：Phase 信息不一致/过期时会成为“迁移幽灵”；建议统一来源（例如移到 `docs/changes/*`）或删除过期表述。
- `tmp_ble_test.py`：仓库根目录临时文件（疑似本地实验残留）。  
  - 风险：污染仓库、误导使用者；建议删除或迁移到 `scripts/dev/` 并改名。

### C) 防御性兜底（Defensive Coding / Degradation）

> 这类代码不应“全删”，但需要分层：哪些必须保留（保证系统可用），哪些应收敛为“可观测的失败”。

- `app/api/v1/namespaces/instances.py:648`：对聚合计算 `except Exception: pass` 静默吞掉所有异常。  
  - 风险：关键链路失败无日志；建议至少记录 warning/error（或按开关决定是否影响请求结果）。
- `app/utils/cache_utils.py:24`：`except Exception` 捕获导入 `redis.exceptions.RedisError` 的所有异常。  
  - 风险：掩盖真实 import 失败原因；建议改为 `ModuleNotFoundError/ImportError`。
- `app/utils/database_batch_manager.py:140`：批量提交时单条操作失败仅记录日志并继续，最后整体 commit。  
  - 风险：部分写入导致数据不一致；需要明确“允许部分成功”还是“全或无”。
- 任务/调度类兜底较多（例如 `app/tasks/capacity_collection_tasks.py:453`、`app/tasks/partition_management_tasks.py:75` 的 `suppress(Exception)` 等）。  
  - 风险：系统可用性优先，但需确保日志/告警完善，避免长期静默失败。

### D) 防御性门禁/Guard Scripts（CI/脚本层）

- `scripts/ci/*` 下存在大量“门禁”脚本（命名、UI、DB session 边界、分页参数、错误文案漂移、CSS token 等）。  
  - 结论：这是“防御体系”的一部分，不属于迁移残留；但可评估是否有过期门禁、重复门禁、或可合并的门禁。

---

## Cleanup Tasks (Executable Checklist)

### Task 1: 清理无行为影响的残留（优先做）

**Files:**
- Delete: `tmp_ble_test.py`
- Modify: `app/templates/instances/detail.html:325`
- Modify: `app/__init__.py:97`（更新/移除过期注释）

**Steps:**
1. 删除 `tmp_ble_test.py`（确认无引用）。
2. 删除 `detail.html` 中大段 legacy Jinja 注释块（保留当前 Grid.js 渲染逻辑）。
3. 校准 `app/__init__.py` 中“迁移期新旧并行”注释为真实状态。

**Verify:**
- Run: `uv run pytest -m unit`

### Task 2: 消除“静默吞错”（最小化改动）

**Files:**
- Modify: `app/api/v1/namespaces/instances.py:648`

**Steps:**
1. 将 `except Exception: pass` 替换为记录日志（至少 warning，带 instance_id / action / error）。
2. 明确策略：聚合失败是否影响该请求的成功返回（建议：默认不影响，但要可观测）。

**Verify:**
- Run: `uv run pytest -m unit`

### Task 3: 收敛 import-time 广义兜底

**Files:**
- Modify: `app/utils/cache_utils.py:24`

**Steps:**
1. 将 `except Exception` 改为 `except ModuleNotFoundError`（或 `ImportError`），避免吞掉真实错误。

**Verify:**
- Run: `make typecheck`

### Task 4: 明确并收敛“配置缺失兜底”策略（需要决策）

**Files:**
- Modify: `app/settings.py`

**Decisions (已执行):**
- 不允许 production 缺失 `DATABASE_URL` 时回退 sqlite（缺失直接启动失败）。
- 不允许运行时修改 `DYLD_LIBRARY_PATH`（仅允许启动前由外部环境显式配置）。

**Verify:**
- Run: `make typecheck`
- Run: `uv run pytest -m unit`

### Task 5: 统一分页契约（前后端协同，风险中等）

**Files:**
- Modify: `app/static/js/modules/stores/logs_store.js:146`
- Potentially modify: 对应 API 返回结构（待定位具体 endpoint）

**Steps:**
1. 盘点后端分页返回字段（统一 `per_page` 或 `limit`，不要多套并存）。
2. 前端删除多字段兼容读取，仅保留一种字段名。
3. 增加/更新 contract tests（类似 `tests/unit/test_frontend_no_legacy_pagination_params.py` 的思路）。

**Verify:**
- Run: `uv run pytest -m unit`
- Run: `./scripts/ci/pagination-param-guard.sh --dry-run`（如脚本支持）

### Task 6: 评估“部分成功”批量写入策略（需要决策）

**Files:**
- Review: `app/utils/database_batch_manager.py:119`

**Decision Points:**
- 允许部分成功：需要明确返回/统计/告警，避免“静默丢数据”。
- 全或无：单条失败应触发整体 rollback（或拆分批次）。

---

## Repro / Inventory Commands (用于持续更新清单)

> 这些命令用于重新生成“命中点”列表，避免人工漏扫（建议在每轮清理前后都跑一次）。

- 兼容/回退/迁移关键词扫描：  
  - `rg -n \"(compat(ibility)?|fallback|legacy|deprecated|deprecat|backward|shim|workaround|TEMP|temporary|transitional|v1|v2|兼容|回退|废弃|临时|过渡|迁移期)\" app scripts tests docs -S --glob '!app/static/vendor/**'`
- 静默吞错扫描：  
  - `rg -n -U \"except Exception:\\\\s*\\\\n\\\\s*pass\" app --glob \"*.py\"`
- 广义 `except Exception` 扫描（需要人工分级）：  
  - `rg -n \"except Exception\" app --glob \"*.py\" -S`
- `suppress(Exception)` / `pass` 防御扫描：  
  - `rg -n \"suppress\\\\(Exception\\\\)|except Exception\" app --glob \"*.py\" -S`
