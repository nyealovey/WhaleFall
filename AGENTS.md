# Repository Guidelines

## Project Structure & Module Organization
- `app/` contains Flask services split into `api/`, `routes/`, `models/`, `utils/`, `tasks/`, and `scheduler.py`; client assets live under `templates/` and `static/`.
- `tests/` mirrors runtime modules via `unit/` and `integration/`, sharing fixtures through `tests/conftest.py`.
- Tooling scripts stay in `scripts/` (e.g., `scripts/dev/start-dev-db.sh`, `scripts/validate_env.sh`), while migrations, seed data, and docs reside in `migrations/`, `sql/`, and `docs/` respectively.
- Environment presets live at the repo root (`env.development`, `env.production`), and keep secrets in `.env` outside version control.

## Build, Test, and Development Commands
- `make install` installs Python dependencies (`uv sync` preferred; falls back to `pip install -r requirements.txt`).
- `make dev start` launches the PostgreSQL + Redis stack; follow with `make dev start-flask` to run the app and `make dev stop` to tear it down.
- `make test` (or `make dev test`) executes pytest; pass `pytest -k expression` or `-m marker` for targeted runs.
- `make quality` runs `ruff` and `mypy`, and `make format` applies `black` + `isort`.

## Coding Style & Naming Conventions
- Use 4-space indentation and keep lines ≤120 characters; run `make format` before pushing.
- Treat `app` as first-party in imports; rely on `black`, `isort`, and `ruff` to enforce style.
- Name modules, functions, and variables in `snake_case`; classes in `CapWords`; align Flask blueprint names with their route modules.
- Use structured logging utilities instead of `print`.

## Testing Guidelines
- Mark tests with `@pytest.mark.unit`, `integration`, or `slow` to enable `pytest -m "unit"` style filters.
- Run integration suites against the Docker stack (`make dev start`), and ensure tests clean up external state.
- For critical areas, run `pytest --cov=app --cov-report=term-missing` and keep fixtures reusable within `tests/conftest.py`.

## Commit & Pull Request Guidelines
- Follow commit prefixes like `fix:`, `feat:`, `refactor:` or concise Chinese verbs; keep subjects under 72 characters.
- Reference relevant issues, note verification steps (e.g., `make test`, manual flows), and add UI screenshots for template changes.
- Document configuration updates in the PR body, keep `.env`, `instance/`, and other secrets local, and update `nginx/` configs when exposing new ports or APIs.
