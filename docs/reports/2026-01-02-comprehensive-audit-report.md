# Comprehensive Audit Report - 2026-01-02

> Status: Draft
> Owner: WhaleFall Audit (Codex)
> Created: 2026-01-02
> Updated: 2026-01-02
> Scope: app/, docs/, scripts/, nginx/, docker-compose*.yml, Dockerfile.prod, tests/unit/
> Related: docs/reports/2025-12-26_architecture-audit-report.md, docs/reports/2025-12-26_database-audit-report.md, docs/reports/2025-12-25_performance-audit-report.md, docs/reports/2025-12-25_frontend-ui-ux-audit-report.md, docs/standards/documentation-standards.md, docs/standards/halfwidth-character-standards.md

## I. Summary

- Unit tests (unit) pass locally via `uv run pytest -m unit`
- Linting and typecheck are not at a passing baseline yet (Ruff style errors, Pyright errors)
- Code security scan (Bandit) passes with repo config, but dependency vulnerabilities exist (pip-audit)
- Several production hardening items remain P0 (cookie security, ports exposure, TLS boundary, Redis healthcheck)

## II. Scope and Method

### A. What was executed

- Env template gate: `./scripts/ci/secrets-guard.sh`
- Naming gate: `./scripts/ci/refactor-naming.sh --dry-run`
- Ruff report: `./scripts/ci/ruff-report.sh style`
- Pyright: `make typecheck` and `./scripts/ci/pyright-report.sh`
- Unit tests: `uv run pytest -m unit`
- Bandit (with repo config): `uv run bandit -r app -c pyproject.toml -f json -o ...`
- JS deps and eslint: `npm ci` and `./scripts/ci/eslint-report.sh quick`
- Python deps vulnerability scan (project venv path): `uv tool run pip-audit --path .venv/lib/python3.13/site-packages -f json -o ...`

### B. Evidence artifacts

Raw outputs are placed under:

- `docs/reports/artifacts/2026-01-02-audit/`

## III. Findings (P0/P1/P2)

### P0

#### P0-01 Cookie security policy and TLS boundary are inconsistent

Why it matters:

- Session cookies can be sent over plaintext HTTP if any HTTP path exists
- This is amplified if Gunicorn port is reachable directly

Evidence:

- `app/__init__.py` sets `SESSION_COOKIE_SECURE = False`
- `nginx/sites-available/whalefall-prod` only listens on port 80
- `docker-compose.prod.yml` exposes `443:443` but no TLS server block exists in nginx config

Related prior report:

- `docs/reports/2025-12-26_architecture-audit-report.md`

#### P0-02 Production compose exposes internal service ports

Why it matters:

- Direct access can bypass nginx controls (timeouts, buffering, error pages)
- Increases attack surface (DoS, misconfig, bypass of proxy policy)

Evidence:

- `docker-compose.prod.yml` exposes `5001:5001` (Gunicorn)
- `docker-compose.prod.yml` exposes `5432:5432` (PostgreSQL) and `6379:6379` (Redis)

#### P0-03 Redis healthcheck likely fails under `requirepass`

Why it matters:

- `depends_on: condition: service_healthy` can block app start or create false health assumptions

Evidence:

- `docker-compose.prod.yml` starts Redis with `--requirepass ${REDIS_PASSWORD}`
- Redis healthcheck uses `redis-cli --raw incr ping` without auth

### P1

#### P1-01 Type safety baseline is not passing (Pyright errors)

Impact:

- Refactors become riskier due to low signal from typecheck
- Errors hide real regressions

Observed:

- Pyright reports 467 errors (see artifact output)
- A concrete root cause is `app/api/v1/resources/base.py` using `**options: RouteSafetyOptions` without `Unpack`, which makes kwarg typing incorrect and cascades into many errors

#### P1-02 Style and import hygiene baseline is not passing (Ruff style errors)

Impact:

- Review noise and higher merge conflict rate
- Harder to enforce docstring and import standards consistently

Observed:

- Ruff style reports 602 errors (see artifact output)

#### P1-03 Dependency vulnerabilities detected (pip-audit)

Observed CVEs and suggested fixed versions:

- `filelock==3.19.1` -> fix to `3.20.1` (CVE-2025-68146)
- `urllib3==2.5.0` -> fix to `2.6.0` (CVE-2025-66418, CVE-2025-66471)
- `werkzeug==3.1.3` -> fix to `3.1.4` (CVE-2025-66221)

Note:

- `npm ci` reports 0 vulnerabilities for JS deps (at audit time)

### P2

#### P2-01 Local run docs are inconsistent on ports and python version

Examples:

- `README.md` and runtime defaults disagree on port (5000 vs 5001)
- Docker image installs Python 3.11 while README highlights Python 3.13

## IV. Recommendations and Follow-ups

### A. P0 remediation (suggested order)

- Define TLS termination ownership (nginx in-container vs upstream LB) and align: ports exposure, cookie flags, redirects, HSTS
- Remove exposure of internal ports in production compose (at minimum: Gunicorn, DB, Redis)
- Fix Redis healthcheck to authenticate or change health strategy

### B. P1 remediation

- Fix kwarg typing in `BaseResource.safe_call` (use `Unpack[RouteSafetyOptions]`) and close the top-level typecheck gaps
- Establish a lint/typecheck ratchet: start from "report mode", then enforce a budget that decreases per PR
- Update vulnerable dependencies and regenerate lockfile (`uv.lock`)

### C. Suggested next step for the planned rewrite (option A selected)

- Keep current code as a reference baseline
- Create a new isolated worktree for the rewrite and treat current repo as "read-only reference" during the first phase

## V. Artifact Index

- Ruff: `docs/reports/artifacts/2026-01-02-audit/ruff_style_2026-01-02_195556.txt`
- Pyright: `docs/reports/artifacts/2026-01-02-audit/pyright_full_2026-01-02_195755.txt`
- Bandit: `docs/reports/artifacts/2026-01-02-audit/bandit_2026-01-02.json`
- Pip audit: `docs/reports/artifacts/2026-01-02-audit/pip_audit_2026-01-02.json`
- ESLint: `docs/reports/artifacts/2026-01-02-audit/eslint_quick_2026-01-02_195841.txt`
- Naming guard: `docs/reports/artifacts/2026-01-02-audit/naming_guard_report.txt`

