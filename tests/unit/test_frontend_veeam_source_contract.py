"""Veeam 数据源页面与实例备份展示契约测试."""

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_veeam_source_template_contract() -> None:
    section_partial = _read_text("app/templates/admin/system-settings/_veeam-source-section.html")

    template_fragments = (
        'id="veeam-source-page"',
        'data-api-url="/api/v1/integrations/veeam/source"',
        'id="veeamCredentialId"',
        'id="veeamServerHost"',
        'id="veeamServerPort"',
        'id="veeamApiVersion"',
        'id="veeamVerifySsl"',
        'id="veeamMatchDomains"',
        'id="saveVeeamSourceBtn"',
        'id="syncVeeamBackupsBtn"',
        "Veeam IP",
        "域名列表",
        "同步 Veeam 备份",
    )
    for fragment in template_fragments:
        assert fragment in section_partial


def test_veeam_source_js_and_instance_views_define_backup_behaviors() -> None:
    source_js = _read_text("app/static/js/modules/views/integrations/veeam/source.js")
    instance_list_js = _read_text("app/static/js/modules/views/instances/list.js")
    instance_detail_js = _read_text("app/static/js/modules/views/instances/detail.js")

    source_fragments = (
        "function mountVeeamSourcePage",
        "veeamMatchDomains",
        "linesToDomains",
        "saveVeeamSourceBtn",
        "syncVeeamBackupsBtn",
        "同步 Veeam 备份",
    )
    for fragment in source_fragments:
        assert fragment in source_js

    list_fragments = (
        "name: '备份'",
        "id: 'backup'",
        "renderBackupBadge",
        "backup_status",
    )
    for fragment in list_fragments:
        assert fragment in instance_list_js

    detail_fragments = (
        "loadBackupInfo",
        "renderBackupInfo",
        "#backupInfoContent",
        "backup-tab",
    )
    for fragment in detail_fragments:
        assert fragment in instance_detail_js
