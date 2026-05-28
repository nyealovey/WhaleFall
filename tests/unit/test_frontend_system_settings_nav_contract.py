from __future__ import annotations

import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_base_nav_moves_unified_settings_items_into_admin_center() -> None:
    base_template = _read_text("app/templates/base.html")
    admin_dropdown = re.search(
        r'<ul class="app-nav__dropdown dropdown-menu" aria-labelledby="adminDropdown">(?P<body>.*?)</ul>',
        base_template,
        re.S,
    )

    assert "settingsDropdown" not in base_template
    assert ">统一设置<" not in base_template
    assert admin_dropdown is not None

    admin_body = admin_dropdown.group("body")
    for fragment in (
        "url_for('credentials.index')",
        "url_for('tags.index')",
        "url_for('accounts_classifications.index')",
        "url_for('partition.partitions_page')",
    ):
        assert fragment in admin_body


def test_system_settings_template_base_nav_and_assets_contract() -> None:
    template = _read_text("app/templates/admin/system-settings/index.html")
    base_template = _read_text("app/templates/base.html")
    nav_js = _read_text("app/static/js/modules/views/admin/system-settings/index.js")
    nav_css = _read_text("app/static/css/pages/admin/system-settings.css")

    template_fragments = (
        'data-system-settings-nav="true"',
        'data-system-settings-nav-link="system-settings-email-alerts"',
        'data-system-settings-nav-link="system-settings-risk-rules"',
        'data-system-settings-nav-link="system-settings-jumpserver"',
        'data-system-settings-nav-link="system-settings-veeam"',
        'role="tablist"',
        'role="tab"',
        'role="tabpanel"',
        'aria-selected="true"',
        'aria-selected="false"',
        'href="#system-settings-email-alerts"',
        'href="#system-settings-risk-rules"',
        'href="#system-settings-jumpserver"',
        'href="#system-settings-veeam"',
        'id="system-settings-email-alerts"',
        'id="system-settings-risk-rules"',
        'id="system-settings-jumpserver"',
        'id="system-settings-veeam"',
        "hidden",
    )
    for fragment in template_fragments:
        assert fragment in template

    assert "告警设置" in template
    assert "风险规则" in template
    assert "邮件设置" not in template

    assert "系统设置" in base_template
    assert "url_for('system_settings.index')" in base_template
    assert "url_for('alerts.email_settings')" not in base_template
    assert "url_for('jumpserver_source.source_settings')" not in base_template

    js_fragments = (
        "hashchange",
        "replaceState",
        "panel.hidden",
        "aria-selected",
        "data-system-settings-nav",
        "data-system-settings-nav-link",
        "is-active",
    )
    for fragment in js_fragments:
        assert fragment in nav_js

    assert "IntersectionObserver" not in nav_js
    assert "scrollIntoView" not in nav_js

    css_fragments = (
        ".system-settings-page",
        ".system-settings-page__tabs-card",
        ".system-settings-page__panel",
        ".system-settings-page__nav-link.is-active",
    )
    for fragment in css_fragments:
        assert fragment in nav_css
