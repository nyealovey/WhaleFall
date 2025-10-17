"""
健康检查路由单元测试
"""

from unittest.mock import Mock, patch

import pytest
from flask import Flask

from app.routes.health import health_bp


@pytest.fixture
def app():
    """构建用于测试的 Flask 应用"""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(health_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.mark.unit
def test_health_check_success(client):
    """基础健康检查返回统一成功结构"""
    response = client.get("/")

    assert response.status_code == 200
    data = response.get_json()
    assert data["error"] is False
    assert data["message"] == "服务运行正常"
    assert data["data"]["status"] == "healthy"
    assert "timestamp" in data["data"]
    assert data["data"]["version"] == "1.0.7"


@pytest.mark.unit
@patch("app.routes.health.jsonify_unified_success")
def test_health_check_exception(mock_success, client):
    """基础健康检查内部异常时返回统一错误结构"""
    mock_success.side_effect = Exception("boom")

    response = client.get("/")

    assert response.status_code == 500
    data = response.get_json()
    assert data["error"] is True
    assert data["message"] == "健康检查失败"


@pytest.mark.unit
@patch("app.routes.health.cache.get")
@patch("app.routes.health.cache.set")
@patch("app.routes.health.psutil.disk_usage")
@patch("app.routes.health.psutil.virtual_memory")
@patch("app.routes.health.psutil.cpu_percent")
@patch("app.routes.health.db.session.execute")
def test_detailed_health_check_success(
    mock_db_execute,
    mock_cpu_percent,
    mock_virtual_memory,
    mock_disk_usage,
    mock_cache_set,
    mock_cache_get,
    client,
):
    """详细健康检查返回各组件信息"""
    mock_db_execute.return_value = Mock()
    mock_cpu_percent.return_value = 20.0
    mock_virtual_memory.return_value = Mock(percent=40.0)
    mock_disk_usage.return_value = Mock(total=100.0, used=20.0)
    mock_cache_set.return_value = True
    mock_cache_get.return_value = "ok"

    response = client.get("/detailed")

    assert response.status_code == 200
    data = response.get_json()
    assert data["error"] is False
    components = data["data"]["components"]
    assert components["database"]["healthy"] is True
    assert components["cache"]["healthy"] is True
    assert components["system"]["healthy"] is True


@pytest.mark.unit
@patch("app.routes.health.check_database_health", side_effect=Exception("db fail"))
def test_detailed_health_check_failure(mock_db_health, client):
    """详细健康检查失败时返回统一错误结构"""
    response = client.get("/detailed")

    assert mock_db_health.called
    assert response.status_code == 500
    data = response.get_json()
    assert data["error"] is True
    assert data["message"] == "详细健康检查失败"


@pytest.mark.unit
@patch("app.routes.health.check_cache_health", return_value={"healthy": False})
@patch("app.routes.health.check_database_health", return_value={"healthy": True})
def test_readiness_check_not_ready(mock_db_health, mock_cache_health, client):
    """就绪检查在组件未就绪时返回 503"""
    response = client.get("/readiness")

    assert response.status_code == 503
    data = response.get_json()
    assert data["error"] is True
    assert data["message"] == "服务未就绪"


@pytest.mark.unit
def test_liveness_check_success(client):
    """存活检查返回成功结构"""
    response = client.get("/liveness")

    assert response.status_code == 200
    data = response.get_json()
    assert data["error"] is False
    assert data["data"]["status"] == "alive"
