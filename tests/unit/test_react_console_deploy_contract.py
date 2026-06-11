from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_project_file(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_prod_dockerfile_builds_react_console_assets() -> None:
    dockerfile = _read_project_file("Dockerfile.prod")

    assert "FROM node:22-alpine AS frontend-build" in dockerfile
    assert "COPY frontend/package.json frontend/package-lock.json /frontend/" in dockerfile
    assert "RUN npm ci" in dockerfile
    assert "RUN npm run build" in dockerfile
    assert "COPY --from=frontend-build /frontend/dist /app/frontend/dist" in dockerfile


def test_nginx_serves_react_console_without_proxying_assets_to_flask() -> None:
    configs = {
        "nginx/sites-available/whalefall-dev": 1,
        "nginx/sites-available/whalefall-prod": 2,
    }

    for relative_path, expected_server_count in configs.items():
        config = _read_project_file(relative_path)

        assert config.count("location ^~ /console/assets/") >= expected_server_count
        assert config.count("alias /app/frontend/dist/assets/;") >= expected_server_count
        assert config.count("location ^~ /console/") >= expected_server_count
        assert config.count("alias /app/frontend/dist/;") >= expected_server_count
        assert config.index("location ^~ /console/assets/") < config.index("location / {")


def test_makefile_exposes_frontend_lifecycle_commands() -> None:
    makefile = _read_project_file("Makefile")
    prod_makefile = _read_project_file("Makefile.prod")

    for target in (
        "frontend-install:",
        "frontend-build:",
        "frontend-lint:",
        "frontend-test:",
        "frontend-typecheck:",
    ):
        assert target in makefile

    assert "构建生产镜像（包含 React /console 前端）" in prod_makefile
    assert "部署生产环境（包含 React /console 前端）" in prod_makefile
