from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_system_settings_template_includes_ad_domain_tab_and_assets() -> None:
    content = _read_text("app/templates/admin/system-settings/index.html")

    assert 'id="system-settings-ad-domain-tab"' in content
    assert 'href="#system-settings-ad-domain"' in content
    assert 'data-system-settings-nav-link="system-settings-ad-domain"' in content
    assert 'id="system-settings-ad-domain"' in content
    assert "AD 域账户同步设置" in content
    assert "{% include 'admin/system-settings/_ad-domain-configs-section.html' %}" in content
    assert "js/modules/services/ad_domain_configs_service.js" in content
    assert "js/modules/views/integrations/ad-domain/configs.js" in content


def test_ad_domain_settings_partial_defines_config_controls() -> None:
    content = _read_text("app/templates/admin/system-settings/_ad-domain-configs-section.html")

    required_fragments = (
        'id="ad-domain-configs-page"',
        'data-api-url="/api/v1/ad-domain-configs"',
        'data-credentials-api-url="/api/v1/credentials"',
        'id="adDomainConfigName"',
        'id="adDomainNetbiosName"',
        'id="adDomainControllers"',
        'id="adDomainLdapPort"',
        'id="adDomainUseSsl"',
        'id="adDomainVerifySsl"',
        'id="adDomainBaseDn"',
        'id="adDomainCredentialId"',
        'id="adDomainIsEnabled"',
        'id="adDomainDescription"',
        'id="saveAdDomainConfigBtn"',
        'id="syncAdDomainAccountsBtn"',
        'id="adDomainConfigsList"',
    )
    for fragment in required_fragments:
        assert fragment in content


def test_ad_domain_settings_js_defines_crud_and_sync_behaviors() -> None:
    service_js = _read_text("app/static/js/modules/services/ad_domain_configs_service.js")
    view_js = _read_text("app/static/js/modules/views/integrations/ad-domain/configs.js")

    service_fragments = (
        "class AdDomainConfigsService",
        "loadConfigs",
        "loadLdapCredentials",
        "createConfig",
        "updateConfig",
        "deleteConfig",
        "setEnabled",
        "testConnection",
        "syncAccounts",
    )
    for fragment in service_fragments:
        assert fragment in service_js

    view_fragments = (
        "function mountAdDomainConfigsPage",
        "controllersToList",
        "verifySslToPayload",
        "saveAdDomainConfigBtn",
        "syncAdDomainAccountsBtn",
        "adDomainConfigsList",
        "data-ad-domain-action",
        "last_sync_metrics",
        "renderLastSyncMetrics",
        "AD对象",
        "SQL账户",
        "孤账户",
        "AD 域账户同步",
    )
    for fragment in view_fragments:
        assert fragment in view_js
