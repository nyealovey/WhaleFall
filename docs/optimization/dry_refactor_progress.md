# Repo DRY Refactor Progress

> 目标：在不改变对外行为/API/错误口径的前提下，对仓库做系统性 DRY 重构（识别重复→抽象→替换→验证），以“渐进式、小批次、可回滚”的方式落地。

## Hard Constraints（硬约束）

- 默认不改变对外行为/API/错误口径；若必须变更，需先列出影响与迁移/回滚方案并等待确认
- 不修改历史 `migrations/`
- 新增/调整配置项必须走 `app/settings.py`；`.env` 禁止提交；`env.example` 禁止写真实密钥/口令
- 后台任务必须运行在 Flask `app.app_context()` 内
- 禁止无依据的防御性分支 / silent fallback / 吞异常继续执行
- 每个 Batch 必须：
  - 补齐必要的单元测试（以行为锁定为准）
  - 执行并记录 `uv run pytest -m unit` 与 `make typecheck` 的结果

## Related Docs（关联文档）

- 计划：`docs/plans/2026-01-18-dry-refactor-whalefall.md`

## Latest Verification（最近一次验证）

- Date: 2026-01-18T09:17:10+0800
- Result: PASS (`uv run pytest -m unit`, `make typecheck`)

## Batches（按风险→影响面排序）

- [x] Batch 0: Baseline（unit + typecheck）
- [x] Batch 1: internal_contracts DRY（versioned dict normalizer + permission_snapshot(v4) parse）
- [ ] Batch 2: API 层重复响应/错误消息构造（先从局部热点开始）
- [ ] Batch 3: Service 层重复校验/参数规整入口（与 schema/validation 对齐）
- [ ] Batch 4+: 其他重复热点（按扫描结果滚动补充）

## Hotspot Backlog（候选重复点，滚动维护）

> 说明：该列表用于“下一批做什么”的排序；每个 Batch 最多处理 1-2 个热点，避免把无关重构揉在一起。

- [x] internal_contracts: v1 versioned dict payload（`sync_details_v1` / `type_specific_v1`）
- [x] internal_contracts: permission_snapshot(v4) parse（categories/type_specific）
- [ ] API: connection test 失败时的统一错误响应构造（`app/api/v1/namespaces/instances_connections.py`）
- [ ] utils: rate_limiter 两个 decorator 的重复错误响应 + header 设置（`app/utils/rate_limiter.py`）

## Verification Log（每批一条）

<!--
格式（示例）：
- 2026-01-18 Batch 2 <topic>: PASS (uv run pytest -m unit; make typecheck)
-->

- 2026-01-18 Batch 0 baseline: PASS (uv run pytest -m unit; make typecheck)
- 2026-01-18 Batch 1 internal_contracts: PASS (uv run pytest -m unit; make typecheck)

## Batch Report Template（批次汇报模板）

```text
Batch N: 目标/范围 |
重复点(文件:行) |
抽象设计(接口+可变/不变) |
替换点数量 |
兼容性/风险 |
测试新增/调整 |
运行命令及结果
```

