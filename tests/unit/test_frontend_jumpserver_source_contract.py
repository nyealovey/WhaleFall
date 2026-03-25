"""JumpServer 数据源页面与实例托管展示契约测试."""

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_jumpserver_source_template_and_system_settings_nav_contract() -> None:
    section_partial = _read_text("app/templates/admin/system-settings/_jumpserver-source-section.html")
    base_template = _read_text("app/templates/base.html")

    template_fragments = (
        'id="jumpserver-source-page"',
        'data-api-url="/api/v1/integrations/jumpserver/source"',
        'data-sync-api-url="/api/v1/integrations/jumpserver/actions/sync"',
        'id="jumpserverCredentialId"',
        'id="jumpserverBaseUrl"',
        'id="jumpserverOrgId"',
        'id="jumpserverVerifySsl"',
        'id="saveJumpserverSourceBtn"',
        'id="syncJumpserverAssetsBtn"',
    )
    for fragment in template_fragments:
        assert fragment in section_partial

    assert "系统设置" in base_template
    assert "url_for('system_settings.index')" in base_template
    assert "url_for('jumpserver_source.source_settings')" not in base_template


def test_jumpserver_source_js_and_instances_list_define_managed_behaviors() -> None:
    source_js = _read_text("app/static/js/modules/views/integrations/jumpserver/source.js")
    instance_list_js = _read_text("app/static/js/modules/views/instances/list.js")

    source_fragments = (
        "function mountJumpServerSourcePage",
        "saveJumpserverSourceBtn",
        "jumpserverBaseUrl",
        "jumpserverOrgId",
        "jumpserverVerifySsl",
        "syncJumpserverAssetsBtn",
        "组织 ID",
        "SSL 证书验证",
        "解绑数据源",
        "同步 JumpServer 资源",
    )
    for fragment in source_fragments:
        assert fragment in source_js

    instance_fragments = (
        "name: '已托管'",
        "id: 'jumpserver_managed'",
        "renderJumpServerManagedBadge",
        "is_jumpserver_managed",
        "已托管于 JumpServer",
    )
    for fragment in instance_fragments:
        assert fragment in instance_list_js
