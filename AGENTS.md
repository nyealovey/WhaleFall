# Repository Guidelines

## Project Structure & Module Organization
The Flask services live in `app/`, split into focused modules: `api/` for service endpoints, `routes/` for blueprints, `models/` for ORM entities, `utils/` for shared helpers, `tasks/` for async jobs, and `scheduler.py` for scheduled runs. Client templates and static assets stay in `templates/` and `static/`. Tests mirror this layout under `tests/unit/` and `tests/integration/`, reusing fixtures from `tests/conftest.py`. Supporting assets belong in `scripts/`, `migrations/`, `sql/`, and `docs/`. Environment presets such as `env.development` sit at the repo root; keep secrets in an untracked `.env`.

## Build, Test, and Development Commands
Run `make install` to sync Python dependencies (prefers `uv sync`, falls back to `pip install -r requirements.txt`). Use `make dev start` to boot the PostgreSQL + Redis stack, `make dev start-flask` to launch the API, and `make dev stop` to tear everything down. For validation, `make test` (or `make dev test`) executes pytest; filter suites with `pytest -k pattern` or `-m unit`. Quality gates run via `make quality`, while `make format` applies `black` and `isort`.

## Coding Style & Naming Conventions
Follow 4-space indentation and keep lines within 120 characters. Treat `app` as a first-party import root and rely on `black`, `isort`, and `ruff` for formatting and linting. Use `snake_case` for modules, functions, and variables, `CapWords` for classes, and align blueprint names with their route modules. Prefer structured logging helpers over `print`.

## Testing Guidelines
Annotate tests with `@pytest.mark.unit`, `integration`, or `slow` so contributors can run `pytest -m "unit"` selectively. Execute integration tests against the Docker stack after `make dev start`, and ensure fixtures leave external systems clean. For critical code paths, target `pytest --cov=app --cov-report=term-missing` to watch coverage gaps.

## Commit & Pull Request Guidelines
Commit subjects follow prefixes such as `fix:`, `feat:`, `refactor:`, or concise Chinese verbs, staying under 72 characters. Reference related issues, document verification steps (e.g., `make test`, manual flows), and attach UI screenshots for template changes. In PR descriptions, highlight configuration updates, note any new ports or APIs, and keep `.env`, `instance/`, and other secrets out of version control.

## Security & Configuration Tips
Load environment variables from local `.env` files rather than committing secrets. When modifying ingress or service topology, update `nginx/` configs alongside application changes. Confirm that migrations in `migrations/` and SQL data in `sql/` match the environments referenced in `env.production` before deploying.
