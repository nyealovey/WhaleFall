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
    instance_detail_css = _read_text("app/static/css/pages/instances/detail.css")

    source_fragments = (
        "function mountVeeamSourcePage",
        "veeamMatchDomains",
        "linesToDomains",
        "saveVeeamSourceBtn",
        "syncVeeamBackupsBtn",
        "同步 Veeam 备份",
        "resolveAsyncActionOutcome",
        'action: "veeam:syncBackups"',
        'resultUrl: "/history/sessions"',
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
        "备份状态",
        "最近备份时间",
        "备份链完整大小",
        "恢复点数量",
        "恢复点明细",
        "backup_metrics_coverage",
        "部分覆盖",
        "Backup ID",
        "restore_point_times",
        "restore_points",
        "backup_size_bytes",
        "compress_ratio",
        "creation_time",
        "table table-hover instance-audit-table",
        "恢复点名称",
        "备份方式",
        "数据大小",
        "备份大小",
        "压缩率",
        "创建时间",
        "instance-overview-band",
    )
    for fragment in detail_fragments:
        assert fragment in instance_detail_js

    removed_detail_fragments = (
        "最近还原点大小",
        "最近同步时间",
        "备份摘要",
        "全部恢复点时间",
        "instance-backup-timeline",
        "恢复点 ID",
    )
    for fragment in removed_detail_fragments:
        assert fragment not in instance_detail_js

    assert "候选机器名" not in instance_detail_js
    assert "Backup ${item.backup_id}" not in instance_detail_js
    assert "item.name || item.id ||" not in instance_detail_js
    assert "restorePointSizeBytes" not in instance_detail_js
    assert "storageSizeBytes" not in instance_detail_js
    assert "compressionRatio" not in instance_detail_js
    assert "当前快照缺少恢复点时间，请重新执行一次 Veeam 同步。" in instance_detail_js
    assert "const displayedRestorePointCount = restorePoints.length || restorePointTimes.length || Number(data.restore_point_count) || 0;" in instance_detail_js
    assert "#databaseInfoTabContent > .instance-data-pane" in instance_detail_css
    assert "display: none;" in instance_detail_css
    assert "#databaseInfoTabContent > .instance-data-pane.active" in instance_detail_css
