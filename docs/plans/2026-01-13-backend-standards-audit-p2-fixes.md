# Backend Standards Audit P2 Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 按 `docs/reports/2026-01-13-backend-standards-audit-report.md` 的 P2 建议，补齐写操作边界标准的 MUST/MUST NOT 关键词，并清理审计点名的“语义不明确 `or` 链”实现，降低后续语义漂移风险。

**Architecture:** 以最小改动方式把“强约束”文档显式化（便于门禁抽取），并把已点名的 `or` 链替换为显式 `None` 判定/类型转换，避免把 `0/""/[]/{}` 等合法值误判为缺省。

**Tech Stack:** Python, pytest(`-m unit`).

---

### Task 1: 为写边界标准补齐 MUST/MUST NOT 关键词

**Files:**
- Modify: `docs/Obsidian/standards/backend/write-operation-boundary.md:19`

**Step 1: 将“只发生/不允许/禁止”等表述补齐为 MUST/MUST NOT**

Action:
- 在“事务提交/回滚只发生在提交点”处补 `MUST`。
- 在 services/routes 禁止 commit/rollback 等处补 `MUST NOT`，保持与其它 layer 标准一致。

---

### Task 2: 清理审计点名的“危险 `or` 兜底链”

**Files:**
- Modify: `app/repositories/capacity_databases_repository.py:29`
- Modify: `app/utils/logging/handlers.py:150`

**Step 1: repository 返回值用显式 `None` 判定替代 `or` 链**

Action:
- 将 `int(getattr(row, "id", 0) or 0) or None` 改为显式读取/转换（避免把 `0` 或其它 falsy 值当作缺省）。

**Step 2: logging handler 的 module 回退改为显式判定**

Action:
- 将 `event_dict.get("module") or ... or "app"` 改为可读的显式判定，避免把合法但 falsy 的值误当缺省（并提高可维护性）。

---

### Task 3: 回归验证

**Files:**
- (none)

**Step 1: 跑 unit**

Run: `uv run pytest -m unit`
Expected: PASS

