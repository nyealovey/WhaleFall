# db.md Verifiable Rewrite Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite `docs/changes/refactor/artifacts/db.md` into a usable, source-backed document where every “新增权限/角色” claim is verifiable via official documentation links (or explicitly marked unknown/removed).

**Architecture:** Keep the document as Markdown, split by database vendor (Oracle / MySQL / SQL Server / PostgreSQL). For each vendor, provide (1) a concise versioned change table with sources, and (2) a small “How to verify locally” section with SQL queries.

**Tech Stack:** Markdown, official vendor documentation (docs.oracle.com, postgresql.org, learn.microsoft.com, dev.mysql.com).

---

### Task 1: Collect authoritative sources (Oracle)

**Files:**
- Modify: `docs/changes/refactor/artifacts/db.md`

**Steps:**
1. Locate Oracle official docs for SYSASM, SYSBACKUP/SYSDG/SYSKM, READ/READ ANY TABLE, ENABLE DIAGNOSTICS + DIAGNOSTICS_CONTROL, and 23ai schema-level privileges / GRANT ANY SCHEMA PRIVILEGE.
2. Decide which original rows are unverifiable and should be removed or reworded.

**Verification:**
- Each retained Oracle claim has at least 1 official URL.

---

### Task 2: Collect authoritative sources (MySQL)

**Files:**
- Modify: `docs/changes/refactor/artifacts/db.md`

**Steps:**
1. Use MySQL reference manual and release notes to confirm versioned privilege changes mentioned in the current file (esp. 8.2/8.3/8.4).
2. Avoid claiming “introduced in 8.0” unless a source explicitly states that; otherwise phrase as “present in <version> manual”.

**Verification:**
- Each retained MySQL version claim links to the relevant release notes/manual page.

---

### Task 3: Collect authoritative sources (SQL Server)

**Files:**
- Modify: `docs/changes/refactor/artifacts/db.md`

**Steps:**
1. Verify UNMASK permission and “granular UNMASK” in SQL Server 2022 via Microsoft docs.
2. Verify ledger-related permissions via Microsoft docs; remove any non-existent permission names.

**Verification:**
- Each retained SQL Server claim links to learn.microsoft.com.

---

### Task 4: Collect authoritative sources (PostgreSQL)

**Files:**
- Modify: `docs/changes/refactor/artifacts/db.md`

**Steps:**
1. Use PostgreSQL docs/release notes to confirm roles/privileges that were incorrectly attributed (e.g., MAINTAIN, server-file roles).
2. Prefer the “earliest doc version where it appears” approach when a precise “introduced in” statement is not in release notes.

**Verification:**
- Each retained PostgreSQL row links to `postgresql.org/docs/<version>/...`.

---

### Task 5: Rewrite `db.md` into a clean, verifiable Markdown doc

**Files:**
- Replace content: `docs/changes/refactor/artifacts/db.md`

**Steps:**
1. Add a short intro defining “可核验”的标准（每条必须有来源链接）。
2. Add per-DB sections with versioned change tables and source links.
3. Add per-DB “local verification” snippets (SQL) for checking privileges/roles on a running instance.
4. Add a “Removed/Corrected items” section listing major fixes from the original doc (no sources needed, but be explicit).

**Verification:**
- Markdown renders: headings + tables are readable.
- No un-sourced “新增” claims remain.

