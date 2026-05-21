import pytest

from app import db
from app.models.account_classification import AccountClassification
from app.models.account_classification_daily_stats import (  # noqa: F401
    AccountClassificationDailyClassificationMatchStat,
    AccountClassificationDailyRuleMatchStat,
)
from app.models.account_permission import AccountPermission
from app.models.instance import Instance
from app.models.instance_account import InstanceAccount
from app.models.sqlserver_cluster import SQLServerAvailabilityGroup, SQLServerCluster, SQLServerClusterInstance
from app.utils.time_utils import time_utils


def _ensure_account_statistics_tables(app) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["instance_accounts"],
                db.metadata.tables["account_permission"],
                db.metadata.tables["account_classifications"],
                db.metadata.tables["classification_rules"],
                db.metadata.tables["account_classification_assignments"],
                db.metadata.tables["account_classification_daily_rule_match_stats"],
                db.metadata.tables["account_classification_daily_classification_match_stats"],
                db.metadata.tables["sqlserver_clusters"],
                db.metadata.tables["sqlserver_cluster_instances"],
                db.metadata.tables["sqlserver_availability_groups"],
            ],
        )


@pytest.mark.unit
def test_api_v1_accounts_statistics_requires_auth(client) -> None:
    response = client.get("/api/v1/accounts/statistics")
    assert response.status_code == 401

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("error") is True
    assert payload.get("success") is False
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_accounts_statistics_endpoints_contract(app, auth_client) -> None:
    _ensure_account_statistics_tables(app)

    statistics_response = auth_client.get("/api/v1/accounts/statistics")
    assert statistics_response.status_code == 200
    statistics_payload = statistics_response.get_json()
    assert isinstance(statistics_payload, dict)
    assert statistics_payload.get("success") is True
    assert statistics_payload.get("error") is False
    statistics_data = statistics_payload.get("data")
    assert isinstance(statistics_data, dict)
    assert isinstance(statistics_data.get("stats"), dict)

    summary_response = auth_client.get("/api/v1/accounts/statistics/summary")
    assert summary_response.status_code == 200
    summary_payload = summary_response.get_json()
    assert isinstance(summary_payload, dict)
    assert summary_payload.get("success") is True
    summary_data = summary_payload.get("data")
    assert isinstance(summary_data, dict)
    assert {
        "total_accounts",
        "active_accounts",
        "locked_accounts",
        "normal_accounts",
        "deleted_accounts",
        "total_instances",
        "active_instances",
        "disabled_instances",
        "normal_instances",
        "deleted_instances",
    }.issubset(summary_data.keys())

    db_types_response = auth_client.get("/api/v1/accounts/statistics/db-types")
    assert db_types_response.status_code == 200
    db_types_payload = db_types_response.get_json()
    assert isinstance(db_types_payload, dict)
    assert db_types_payload.get("success") is True
    db_types_data = db_types_payload.get("data")
    assert isinstance(db_types_data, dict)
    assert {"mysql", "postgresql", "oracle", "sqlserver"}.issubset(db_types_data.keys())

    classifications_response = auth_client.get("/api/v1/accounts/statistics/classifications")
    assert classifications_response.status_code == 200
    classifications_payload = classifications_response.get_json()
    assert isinstance(classifications_payload, dict)
    assert classifications_payload.get("success") is True
    classifications_data = classifications_payload.get("data")
    assert isinstance(classifications_data, dict)

    rules_response = auth_client.get("/api/v1/accounts/statistics/rules")
    assert rules_response.status_code == 200
    rules_payload = rules_response.get_json()
    assert isinstance(rules_payload, dict)
    assert rules_payload.get("success") is True
    rules_data = rules_payload.get("data")
    assert isinstance(rules_data, dict)
    assert isinstance(rules_data.get("rule_stats"), list)

    # 新增：账户分类每日统计趋势/贡献接口（需要 query 参数）
    classification_trend = auth_client.get(
        "/api/v1/accounts/statistics/classifications/trend?classification_id=1&period_type=daily&periods=7",
    )
    assert classification_trend.status_code == 200
    trend_payload = classification_trend.get_json()
    assert isinstance(trend_payload, dict)
    assert trend_payload.get("success") is True
    assert isinstance(trend_payload.get("data"), dict)
    assert isinstance(trend_payload["data"].get("trend"), list)

    rule_trend = auth_client.get(
        "/api/v1/accounts/statistics/rules/trend?rule_id=1&period_type=daily&periods=7",
    )
    assert rule_trend.status_code == 200
    rule_trend_payload = rule_trend.get_json()
    assert isinstance(rule_trend_payload, dict)
    assert rule_trend_payload.get("success") is True
    assert isinstance(rule_trend_payload.get("data"), dict)
    assert isinstance(rule_trend_payload["data"].get("trend"), list)

    contributions = auth_client.get(
        "/api/v1/accounts/statistics/rules/contributions?classification_id=1&period_type=daily",
    )
    assert contributions.status_code == 200
    contrib_payload = contributions.get_json()
    assert isinstance(contrib_payload, dict)
    assert contrib_payload.get("success") is True
    assert isinstance(contrib_payload.get("data"), dict)
    assert isinstance(contrib_payload["data"].get("contributions"), list)

    overview = auth_client.get(
        "/api/v1/accounts/statistics/rules/overview?classification_id=1&period_type=daily&periods=7",
    )
    assert overview.status_code == 200
    overview_payload = overview.get_json()
    assert isinstance(overview_payload, dict)
    assert overview_payload.get("success") is True
    assert isinstance(overview_payload.get("data"), dict)
    overview_data = overview_payload["data"]
    assert isinstance(overview_data.get("rules"), list)
    # latest 周期字段: 用于规则列表展示"最后一次命中"(最新周期均值/当日值)
    assert isinstance(overview_data.get("latest_period_start"), str)
    assert isinstance(overview_data.get("latest_period_end"), str)
    assert isinstance(overview_data.get("latest_coverage_days"), int)
    assert isinstance(overview_data.get("latest_expected_days"), int)

    # 新增：全分类趋势接口(未选分类时使用, 受 period/db_type/instance 筛选影响)
    all_trends = auth_client.get(
        "/api/v1/accounts/statistics/classifications/trends?period_type=daily&periods=7",
    )
    assert all_trends.status_code == 200
    all_trends_payload = all_trends.get_json()
    assert isinstance(all_trends_payload, dict)
    assert all_trends_payload.get("success") is True
    assert isinstance(all_trends_payload.get("data"), dict)
    assert isinstance(all_trends_payload["data"].get("buckets"), list)
    assert isinstance(all_trends_payload["data"].get("series"), list)


@pytest.mark.unit
def test_api_v1_accounts_statistics_summary_includes_disabled_instances(app, auth_client) -> None:
    _ensure_account_statistics_tables(app)

    with app.app_context():
        disabled_instance = Instance(
            name="instance-disabled",
            db_type="mysql",
            host="127.0.0.1",
            port=3306,
            is_active=False,
        )
        deleted_instance = Instance(
            name="instance-deleted",
            db_type="mysql",
            host="127.0.0.2",
            port=3307,
            is_active=True,
            deleted_at=time_utils.now(),
        )
        db.session.add_all([disabled_instance, deleted_instance])
        db.session.flush()

        disabled_account = InstanceAccount(
            instance_id=disabled_instance.id,
            username="reader",
            db_type="mysql",
            is_active=True,
        )
        deleted_account = InstanceAccount(
            instance_id=deleted_instance.id,
            username="ghost",
            db_type="mysql",
            is_active=True,
        )
        db.session.add_all([disabled_account, deleted_account])
        db.session.flush()

        db.session.add_all(
            [
                AccountPermission(
                    instance_id=disabled_instance.id,
                    instance_account_id=disabled_account.id,
                    db_type="mysql",
                    username="reader",
                    permission_facts={"capabilities": []},
                ),
                AccountPermission(
                    instance_id=deleted_instance.id,
                    instance_account_id=deleted_account.id,
                    db_type="mysql",
                    username="ghost",
                    permission_facts={"capabilities": []},
                ),
            ],
        )
        db.session.commit()

    summary_response = auth_client.get("/api/v1/accounts/statistics/summary")
    assert summary_response.status_code == 200
    summary_payload = summary_response.get_json()
    assert isinstance(summary_payload, dict)
    summary_data = summary_payload.get("data")
    assert isinstance(summary_data, dict)
    assert summary_data.get("total_accounts") == 1
    assert summary_data.get("active_accounts") == 1
    assert summary_data.get("total_instances") == 1
    assert summary_data.get("active_instances") == 0
    assert summary_data.get("disabled_instances") == 1
    assert summary_data.get("deleted_instances") == 1


@pytest.mark.unit
def test_api_v1_accounts_statistics_treats_ag_listener_as_virtual_instance(app, auth_client) -> None:
    _ensure_account_statistics_tables(app)

    with app.app_context():
        instance = Instance(
            name="sql-prod-01",
            db_type="sqlserver",
            host="10.0.0.11",
            port=1433,
            is_active=True,
        )
        db.session.add(instance)
        db.session.flush()

        cluster = SQLServerCluster(name="cluster-a", domain_name="corp.local", is_enabled=True)
        db.session.add(cluster)
        db.session.flush()
        db.session.add(SQLServerClusterInstance(cluster_id=cluster.id, instance_id=instance.id))
        ag = SQLServerAvailabilityGroup(
            cluster_id=cluster.id,
            name="ag-pay",
            listener_name="ag-pay-listener",
            listener_host="10.0.0.50",
            listener_port=1433,
            contained_enabled=True,
            is_enabled=True,
        )
        db.session.add(ag)
        db.session.flush()

        physical_account = InstanceAccount(
            instance_id=instance.id,
            owner_type="instance",
            owner_id=instance.id,
            username="svc_physical",
            db_type="sqlserver",
            is_active=True,
        )
        ag_account = InstanceAccount(
            instance_id=instance.id,
            owner_type="sqlserver_ag",
            owner_id=ag.id,
            cluster_id=cluster.id,
            availability_group_id=ag.id,
            username="svc_ag",
            db_type="sqlserver",
            is_active=True,
        )
        db.session.add_all([physical_account, ag_account])
        db.session.flush()

        db.session.add_all(
            [
                AccountPermission(
                    instance_id=instance.id,
                    instance_account_id=physical_account.id,
                    owner_type="instance",
                    owner_id=instance.id,
                    db_type="sqlserver",
                    username="svc_physical",
                    permission_facts={"capabilities": []},
                ),
                AccountPermission(
                    instance_id=instance.id,
                    instance_account_id=ag_account.id,
                    owner_type="sqlserver_ag",
                    owner_id=ag.id,
                    cluster_id=cluster.id,
                    availability_group_id=ag.id,
                    db_type="sqlserver",
                    username="svc_ag",
                    permission_facts={"capabilities": []},
                ),
            ],
        )
        db.session.commit()
        ag_id = ag.id

    summary_response = auth_client.get("/api/v1/accounts/statistics/summary?db_type=sqlserver")
    assert summary_response.status_code == 200
    summary = summary_response.get_json()["data"]
    assert summary["total_accounts"] == 2
    assert summary["total_instances"] == 2
    assert summary["physical_instances"] == 1
    assert summary["ag_virtual_instances"] == 1

    scoped_response = auth_client.get(
        f"/api/v1/accounts/statistics/summary?account_scope=sqlserver_ag:{ag_id}",
    )
    assert scoped_response.status_code == 200
    scoped_summary = scoped_response.get_json()["data"]
    assert scoped_summary["total_accounts"] == 1
    assert scoped_summary["total_instances"] == 1
    assert scoped_summary["physical_instances"] == 0
    assert scoped_summary["ag_virtual_instances"] == 1


@pytest.mark.unit
def test_api_v1_account_classification_trend_filters_by_ag_account_scope(app, auth_client) -> None:
    _ensure_account_statistics_tables(app)

    with app.app_context():
        instance = Instance(
            name="sql-prod-01",
            db_type="sqlserver",
            host="10.0.0.11",
            port=1433,
            is_active=True,
        )
        db.session.add(instance)
        db.session.flush()

        cluster = SQLServerCluster(name="cluster-trend", is_enabled=True)
        db.session.add(cluster)
        db.session.flush()
        ag = SQLServerAvailabilityGroup(
            cluster_id=cluster.id,
            name="ag-trend",
            listener_name="ag-trend-listener",
            listener_host="10.0.0.51",
            listener_port=1433,
            contained_enabled=True,
            is_enabled=True,
        )
        classification = AccountClassification(
            code="admin",
            display_name="管理员",
            priority=10,
            is_active=True,
        )
        db.session.add_all([ag, classification])
        db.session.flush()
        db.session.add_all(
            [
                AccountClassificationDailyClassificationMatchStat(
                    stat_date=time_utils.now_china().date(),
                    classification_id=classification.id,
                    db_type="sqlserver",
                    instance_id=instance.id,
                    owner_type="instance",
                    owner_id=instance.id,
                    matched_accounts_distinct_count=3,
                ),
                AccountClassificationDailyClassificationMatchStat(
                    stat_date=time_utils.now_china().date(),
                    classification_id=classification.id,
                    db_type="sqlserver",
                    instance_id=instance.id,
                    owner_type="sqlserver_ag",
                    owner_id=ag.id,
                    matched_accounts_distinct_count=5,
                ),
            ]
        )
        db.session.commit()
        classification_id = classification.id
        ag_id = ag.id

    response = auth_client.get(
        "/api/v1/accounts/statistics/classifications/trend"
        f"?classification_id={classification_id}&period_type=daily&periods=1&account_scope=sqlserver_ag:{ag_id}",
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["trend"][0]["value_sum"] == 5
