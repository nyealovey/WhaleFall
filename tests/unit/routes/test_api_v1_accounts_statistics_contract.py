import pytest

from app import db
from app.models.account_classification_daily_stats import (  # noqa: F401
    AccountClassificationDailyClassificationMatchStat,
    AccountClassificationDailyRuleMatchStat,
)


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
    assert isinstance(overview_payload["data"].get("rules"), list)
