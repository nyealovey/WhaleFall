from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def _relative(path: Path) -> str:
    return path.relative_to(ROOT_DIR).as_posix()


def test_auth_stack_has_no_jwt_runtime_or_deployment_residue() -> None:
    """认证栈收敛到 Flask-Login session + CSRF 后, 不再保留 JWT 配置/依赖口径."""
    scanned_paths = [
        "README.md",
        "requirements.txt",
        "requirements-prod.txt",
        "docker-compose.prod.yml",
        "docker-compose.flask-only.yml",
        "scripts/setup/validate-env.sh",
        "scripts/deploy/deploy-prod-all.sh",
        "scripts/test/run-unit-tests.sh",
        "docs/Obsidian/architecture/spec.md",
        "docs/Obsidian/canvas/global-business-capability-map.canvas",
    ]
    forbidden_tokens = (
        "JWT_SECRET_KEY",
        "Flask-JWT-Extended",
        "flask-jwt-extended",
        "pyjwt",
        "PyJWT",
        "签发 JWT",
        "部分 JWT",
    )

    offenders = []
    for relative_path in scanned_paths:
        content = _read_text(relative_path)
        hits = [token for token in forbidden_tokens if token in content]
        if hits:
            offenders.append(f"{relative_path}: {', '.join(hits)}")

    assert offenders == []


def test_frontend_business_modules_use_httpu_instead_of_direct_fetch() -> None:
    """业务 JS 统一走 httpU, 让 CSRF/错误封套/超时处理保持同一口径."""
    scanned_roots = [
        ROOT_DIR / "app/static/js/modules/services",
        ROOT_DIR / "app/static/js/modules/views",
    ]
    offenders = []

    for root in scanned_roots:
        for path in sorted(root.rglob("*.js")):
            content = path.read_text(encoding="utf-8", errors="ignore")
            if "fetch(" in content:
                offenders.append(_relative(path))

    assert offenders == []


def test_visible_frontend_stack_matches_loaded_vendor_assets() -> None:
    about_template = _read_text("app/templates/about.html")
    readme = _read_text("README.md")
    vendor_versions = _read_text("app/static/vendor/VERSIONS.txt")

    expected_stack = (
        "Bootstrap 5",
        "Grid.js",
        "Chart.js",
        "Umbrella JS",
        "Font Awesome",
        "Jinja2 模板引擎",
    )
    for label in expected_stack:
        assert label in about_template
        assert label in readme or label == "Jinja2 模板引擎"

    stale_labels = ("jQuery", "Tom Select", "Toastr", "NProgress")
    for label in stale_labels:
        assert label not in about_template
        assert label not in readme
        assert label not in vendor_versions


def test_logging_stack_does_not_advertise_loguru() -> None:
    """运行时只使用 structlog, 文档不应继续展示 loguru 双栈."""
    scanned_paths = [
        "README.md",
        "pyproject.toml",
        "requirements.txt",
        "requirements-prod.txt",
    ]
    offenders = []
    for relative_path in scanned_paths:
        content = _read_text(relative_path)
        if "loguru" in content.lower():
            offenders.append(relative_path)

    assert offenders == []


def test_http_csrf_header_is_owned_by_httpu_only() -> None:
    """CSRF header 统一由 httpU 注入, 业务 service/view 不再重复传 token."""
    allowed_path = "app/static/js/core/http-u.js"
    scanned_roots = [
        ROOT_DIR / "app/static/js/modules/services",
        ROOT_DIR / "app/static/js/modules/views",
    ]
    forbidden_tokens = (
        "X-CSRFToken",
        "function csrfHeaders",
        'meta[name="csrf-token"]',
        "meta[name='csrf-token']",
    )
    offenders = []

    for root in scanned_roots:
        for path in sorted(root.rglob("*.js")):
            relative_path = _relative(path)
            if relative_path == allowed_path:
                continue
            content = path.read_text(encoding="utf-8", errors="ignore")
            hits = [token for token in forbidden_tokens if token in content]
            if hits:
                offenders.append(f"{relative_path}: {', '.join(hits)}")

    assert offenders == []


def test_views_do_not_directly_depend_on_global_httpu() -> None:
    """View 层通过 service/store 调 HTTP, 不直接访问 window.httpU."""
    offenders = []
    for path in sorted((ROOT_DIR / "app/static/js/modules/views").rglob("*.js")):
        content = path.read_text(encoding="utf-8", errors="ignore")
        if "window.httpU" in content or "global.httpU" in content:
            offenders.append(_relative(path))

    assert offenders == []


def test_dashboard_web_route_is_html_only() -> None:
    """Dashboard 页面路由只渲染 HTML, JSON 统一走 /api/v1/dashboard/*."""
    content = _read_text("app/routes/dashboard.py")

    assert "request.is_json" not in content
    assert "jsonify_unified_success" not in content


def test_write_payload_validation_is_not_performed_in_api_resources() -> None:
    """写路径 payload 的 canonical 校验落在 service/schema, API resource 只取 raw."""
    alerts_api = _read_text("app/api/v1/namespaces/alerts.py")
    risk_center_api = _read_text("app/api/v1/namespaces/risk_center.py")
    risk_center_service = _read_text("app/services/risk_center/risk_center_rule_settings_service.py")

    assert "validate_or_raise" not in alerts_api
    assert "request.get_json(silent=True) or {}" not in risk_center_api
    assert "validate_or_raise" in risk_center_service


def test_backend_examples_do_not_reference_wtforms_runtime_forms() -> None:
    """后端示例应展示 Pydantic schema, 不再教授已移除的 WTForms 表单栈."""
    content = _read_text("docs/Obsidian/reference/examples/backend-layer-examples.md")
    forbidden_tokens = (
        "from wtforms",
        "BaseFormDefinition",
        "DataRequired",
        "NumberRange",
        "StringField",
        "SelectField",
    )
    offenders = [token for token in forbidden_tokens if token in content]

    assert offenders == []
