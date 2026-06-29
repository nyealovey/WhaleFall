import re
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


def test_react_app_is_mounted_at_site_root() -> None:
    vite_config = _read_project_file("frontend/vite.config.ts")
    app_entry = _read_project_file("frontend/src/App.tsx")

    assert 'base: "/console/"' not in vite_config
    assert 'base: "/"' in vite_config
    assert 'basename="/console"' not in app_entry
    assert "<BrowserRouter>" in app_entry


def test_legacy_static_js_does_not_hardcode_root_page_redirects() -> None:
    page_segments = (
        "dashboard",
        "instances",
        "accounts",
        "databases",
        "capacity",
        "scheduler",
        "history",
        "admin",
        "tags",
        "partition",
        "cluster",
        "risk",
        "credentials",
        "users",
        "auth",
        "about",
    )
    route_group = "|".join(page_segments)
    root_redirect_pattern = re.compile(
        rf"(?:(?:window\.)?location(?:\.href)?\s*=\s*|location\.(?:assign|replace)\(\s*)"
        rf"['\"]/(?:{route_group})(?:/|['\"]|\?)"
    )
    offenders: list[str] = []
    for path in (ROOT_DIR / "app/static/js").rglob("*.js"):
        if ".map" in path.suffixes:
            continue
        content = path.read_text(encoding="utf-8")
        for match in root_redirect_pattern.finditer(content):
            line_number = content[: match.start()].count("\n") + 1
            offenders.append(f"{path.relative_to(ROOT_DIR)}:{line_number}: {match.group(0)}")

    assert offenders == []


def test_shadcn_utility_module_does_not_use_ignored_lib_directory() -> None:
    frontend_files = list((ROOT_DIR / "frontend").rglob("*"))
    text_files = [
        path
        for path in frontend_files
        if path.is_file()
        and "node_modules" not in path.parts
        and "dist" not in path.parts
        and path.suffix in {".json", ".ts", ".tsx"}
    ]

    assert (ROOT_DIR / "frontend/src/utils/cn.ts").is_file()
    assert not (ROOT_DIR / "frontend/src/lib").exists()
    for path in text_files:
        content = path.read_text(encoding="utf-8")
        assert "@/lib" not in content


def test_prod_nginx_domain_and_tls_are_rendered_from_env() -> None:
    dockerfile = _read_project_file("Dockerfile.prod")
    compose = _read_project_file("docker-compose.prod.yml")
    env_example = _read_project_file("env.example")
    prod_nginx = _read_project_file("nginx/sites-available/whalefall-prod")
    start_script = _read_project_file("scripts/ops/docker/start-prod-services.sh")

    assert "gettext-base" in dockerfile
    assert "/etc/nginx/templates/whalefall-prod.template" in dockerfile
    assert "${WHALEFALL_NGINX_SSL_HOST_DIR:-./nginx/local/ssl}:/etc/nginx/ssl:ro" in compose
    assert 'WHALEFALL_NGINX_SERVER_NAMES="example.com www.example.com"' in env_example
    assert "server_name ${WHALEFALL_NGINX_SERVER_NAMES};" in prod_nginx
    assert "ssl_certificate ${WHALEFALL_NGINX_SSL_CERTIFICATE};" in prod_nginx
    assert "ssl_certificate_key ${WHALEFALL_NGINX_SSL_CERTIFICATE_KEY};" in prod_nginx
    assert "envsubst" in start_script
    assert "render_nginx_site_config" in start_script
    assert "nginx -t" in start_script


def test_nginx_serves_react_app_at_root_and_legacy_flask_under_old() -> None:
    configs = {
        "nginx/sites-available/whalefall-dev": 1,
        "nginx/sites-available/whalefall-prod": 2,
    }

    for relative_path, expected_server_count in configs.items():
        config = _read_project_file(relative_path)

        assert "location = /console" in config
        assert "location ^~ /console/" in config
        assert "return 404;" in config
        assert config.count("location ^~ /assets/") >= expected_server_count
        assert config.count("alias /app/frontend/dist/assets/;") >= expected_server_count
        assert config.count("location ^~ /old/static/") >= expected_server_count
        assert config.count("location ^~ /old/") >= expected_server_count
        assert config.count("proxy_set_header X-Forwarded-Prefix /old;") >= expected_server_count
        assert config.count("location ^~ /api/") >= expected_server_count
        assert config.count("alias /app/frontend/dist/index.html;") >= expected_server_count
        assert config.index("location ^~ /api/") < config.index("location / {")
        assert config.index("location ^~ /old/") < config.index("location / {")
        assert config.index("location ^~ /assets/") < config.index("location / {")


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

    assert "构建生产镜像（包含 React 默认前端）" in prod_makefile
    assert "部署生产环境（包含 React 默认前端）" in prod_makefile


def test_hot_update_script_can_publish_react_console_assets() -> None:
    script = _read_project_file("scripts/deploy/update-prod-flask.sh")

    assert "copy_frontend_files_to_temp_dir" in script
    assert '[ ! -d "frontend" ]' in script
    assert "frontend/node_modules" in script
    assert "frontend/coverage" in script
    assert "frontend/dist/index.html" in script
    assert "/app/frontend/dist/index.html" in script
    assert "rendered=/etc/nginx/sites-available/whalefall" in script
    assert "envsubst" in script
    assert "http://localhost/" in script
    assert "http://localhost/old/" in script
    assert "http://localhost/console" not in script
    assert "npm --prefix frontend run build" not in script
