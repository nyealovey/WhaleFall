"""SQL Server cluster AG 自动同步前端契约测试."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_cluster_ag_tab_exposes_sync_action() -> None:
    content = _read_text("app/templates/cluster/list.html")

    required_fragments = (
        'data-action="sync-ag"',
        "同步 AG 信息",
        "使用已绑定实例凭据读取 AG/listener 信息。",
        "clusterDomainNameInput",
        "群集域名",
        "连接地址",
    )
    for fragment in required_fragments:
        assert fragment in content

    forbidden_fragments = (
        "clusterAgNameInput",
        "clusterAgListenerNameInput",
        "clusterAgHostInput",
        "clusterAgPortInput",
        "clusterAgDatabaseInput",
        "clusterAgContainedInput",
        "clusterAgEnabledInput",
        "clusterAgCredentialInput",
        'data-action="save-ag-draft"',
        "保存 AG",
    )
    for fragment in forbidden_fragments:
        assert fragment not in content


def test_cluster_frontend_calls_sync_ag_endpoint_from_ag_tab() -> None:
    service_content = _read_text("app/static/js/modules/services/sqlserver_clusters_service.js")
    store_content = _read_text("app/static/js/modules/stores/sqlserver_clusters_store.js")
    view_content = _read_text("app/static/js/modules/views/cluster/list.js")

    assert "syncAvailabilityGroups(clusterId, payload)" in service_content
    assert "`${BASE_PATH}/${clusterId}/availability-groups/actions/sync`" in service_content

    assert '"syncAvailabilityGroups",' in store_content
    assert "syncAvailabilityGroups(clusterId, payload)" in store_content

    required_view_fragments = (
        '[data-action="sync-ag"]',
        "syncAvailabilityGroups(clusterId, {})",
        "AG 信息同步完成",
        "store.actions.load(clusterId)",
        'data-action="update-ag-account-credential"',
        'data-action="toggle-ag-collection"',
        "account_credential_id",
        "非 contained AG 不允许启用采集",
        "domain_name",
        "clusterDomainNameInput",
        "connection_endpoint",
    )
    for fragment in required_view_fragments:
        assert fragment in view_content

    forbidden_view_fragments = (
        "saveAgDraft",
        "buildAgPayload",
        "populateAgForm",
        "disableAg",
        "findAg",
        "pendingAgDrafts",
        "clusterAgContainedInput",
        "clusterAgDatabaseInput",
        "connection_database:",
        "请选择 AG 凭据后同步",
        "edit-ag",
        "disable-ag",
    )
    for fragment in forbidden_view_fragments:
        assert fragment not in view_content
