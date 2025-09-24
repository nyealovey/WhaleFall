"""
健康检查路由单元测试
"""
import pytest
from unittest.mock import Mock, patch
from flask import Flask
from app.routes.health import health_bp


@pytest.fixture
def app():
    """Create test app."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(health_bp)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.mark.unit
def test_health_check_success(client):
    """Test basic health check success."""
    # 2. Act
    response = client.get('/')
    
    # 3. Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['message'] == '服务运行正常'
    assert data['data']['status'] == 'healthy'
    assert 'timestamp' in data['data']
    assert data['data']['version'] == '1.0.7'


@pytest.mark.unit
def test_health_check_root_success(client):
    """Test health check root route success."""
    # 2. Act
    response = client.get('')
    
    # 3. Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['message'] == '服务运行正常'
    assert data['data']['status'] == 'healthy'


@pytest.mark.unit
@patch('app.routes.health.time.time')
def test_health_check_timestamp(mock_time, client):
    """Test health check timestamp."""
    # 1. Arrange
    mock_time.return_value = 1234567890.123
    
    # 2. Act
    response = client.get('/')
    
    # 3. Assert
    data = response.get_json()
    assert data['data']['timestamp'] == 1234567890.123


@pytest.mark.unit
@patch('app.routes.health.APIResponse.success')
def test_health_check_exception(mock_api_response, client):
    """Test health check with exception."""
    # 1. Arrange
    mock_api_response.side_effect = Exception("API Response error")
    
    # 2. Act
    response = client.get('/')
    
    # 3. Assert
    assert response.status_code == 500
    data = response.get_json()
    assert data['success'] is False
    assert '健康检查失败' in data['error']


@pytest.mark.unit
@patch('app.routes.health.psutil.virtual_memory')
@patch('app.routes.health.psutil.cpu_percent')
@patch('app.routes.health.psutil.disk_usage')
@patch('app.routes.health.db.session.execute')
def test_detailed_health_check_success(mock_db_execute, mock_disk_usage, mock_cpu_percent, mock_virtual_memory, client):
    """Test detailed health check success."""
    # 1. Arrange
    mock_virtual_memory.return_value = Mock(percent=50.0, available=1000000000)
    mock_cpu_percent.return_value = 25.0
    mock_disk_usage.return_value = Mock(percent=30.0, free=2000000000)
    mock_db_execute.return_value.fetchone.return_value = (1,)
    
    # 2. Act
    response = client.get('/detailed')
    
    # 3. Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['message'] == '详细健康检查完成'
    assert 'system_info' in data['data']
    assert 'database_status' in data['data']
    assert 'cache_status' in data['data']


@pytest.mark.unit
@patch('app.routes.health.psutil.virtual_memory')
@patch('app.routes.health.psutil.cpu_percent')
@patch('app.routes.health.psutil.disk_usage')
@patch('app.routes.health.db.session.execute')
def test_detailed_health_check_system_info(mock_db_execute, mock_disk_usage, mock_cpu_percent, mock_virtual_memory, client):
    """Test detailed health check system info."""
    # 1. Arrange
    mock_virtual_memory.return_value = Mock(percent=60.0, available=2000000000)
    mock_cpu_percent.return_value = 40.0
    mock_disk_usage.return_value = Mock(percent=25.0, free=5000000000)
    mock_db_execute.return_value.fetchone.return_value = (1,)
    
    # 2. Act
    response = client.get('/detailed')
    
    # 3. Assert
    data = response.get_json()
    system_info = data['data']['system_info']
    assert system_info['memory_usage'] == 60.0
    assert system_info['memory_available'] == 2000000000
    assert system_info['cpu_usage'] == 40.0
    assert system_info['disk_usage'] == 25.0
    assert system_info['disk_free'] == 5000000000


@pytest.mark.unit
@patch('app.routes.health.psutil.virtual_memory')
@patch('app.routes.health.psutil.cpu_percent')
@patch('app.routes.health.psutil.disk_usage')
@patch('app.routes.health.db.session.execute')
def test_detailed_health_check_database_status(mock_db_execute, mock_disk_usage, mock_cpu_percent, mock_virtual_memory, client):
    """Test detailed health check database status."""
    # 1. Arrange
    mock_virtual_memory.return_value = Mock(percent=50.0, available=1000000000)
    mock_cpu_percent.return_value = 25.0
    mock_disk_usage.return_value = Mock(percent=30.0, free=2000000000)
    mock_db_execute.return_value.fetchone.return_value = (1,)
    
    # 2. Act
    response = client.get('/detailed')
    
    # 3. Assert
    data = response.get_json()
    database_status = data['data']['database_status']
    assert database_status['status'] == 'healthy'
    assert database_status['response_time'] > 0


@pytest.mark.unit
@patch('app.routes.health.psutil.virtual_memory')
@patch('app.routes.health.psutil.cpu_percent')
@patch('app.routes.health.psutil.disk_usage')
@patch('app.routes.health.db.session.execute')
def test_detailed_health_check_database_failure(mock_db_execute, mock_disk_usage, mock_cpu_percent, mock_virtual_memory, client):
    """Test detailed health check database failure."""
    # 1. Arrange
    mock_virtual_memory.return_value = Mock(percent=50.0, available=1000000000)
    mock_cpu_percent.return_value = 25.0
    mock_disk_usage.return_value = Mock(percent=30.0, free=2000000000)
    mock_db_execute.side_effect = Exception("Database error")
    
    # 2. Act
    response = client.get('/detailed')
    
    # 3. Assert
    data = response.get_json()
    database_status = data['data']['database_status']
    assert database_status['status'] == 'unhealthy'
    assert 'Database error' in database_status['error']


@pytest.mark.unit
@patch('app.routes.health.psutil.virtual_memory')
@patch('app.routes.health.psutil.cpu_percent')
@patch('app.routes.health.psutil.disk_usage')
@patch('app.routes.health.db.session.execute')
@patch('app.routes.health.cache.get')
def test_detailed_health_check_cache_status(mock_cache_get, mock_db_execute, mock_disk_usage, mock_cpu_percent, mock_virtual_memory, client):
    """Test detailed health check cache status."""
    # 1. Arrange
    mock_virtual_memory.return_value = Mock(percent=50.0, available=1000000000)
    mock_cpu_percent.return_value = 25.0
    mock_disk_usage.return_value = Mock(percent=30.0, free=2000000000)
    mock_db_execute.return_value.fetchone.return_value = (1,)
    mock_cache_get.return_value = 'test_value'
    
    # 2. Act
    response = client.get('/detailed')
    
    # 3. Assert
    data = response.get_json()
    cache_status = data['data']['cache_status']
    assert cache_status['status'] == 'healthy'
    assert cache_status['response_time'] > 0


@pytest.mark.unit
@patch('app.routes.health.psutil.virtual_memory')
@patch('app.routes.health.psutil.cpu_percent')
@patch('app.routes.health.psutil.disk_usage')
@patch('app.routes.health.db.session.execute')
@patch('app.routes.health.cache.get')
def test_detailed_health_check_cache_failure(mock_cache_get, mock_db_execute, mock_disk_usage, mock_cpu_percent, mock_virtual_memory, client):
    """Test detailed health check cache failure."""
    # 1. Arrange
    mock_virtual_memory.return_value = Mock(percent=50.0, available=1000000000)
    mock_cpu_percent.return_value = 25.0
    mock_disk_usage.return_value = Mock(percent=30.0, free=2000000000)
    mock_db_execute.return_value.fetchone.return_value = (1,)
    mock_cache_get.side_effect = Exception("Cache error")
    
    # 2. Act
    response = client.get('/detailed')
    
    # 3. Assert
    data = response.get_json()
    cache_status = data['data']['cache_status']
    assert cache_status['status'] == 'unhealthy'
    assert 'Cache error' in cache_status['error']


@pytest.mark.unit
@patch('app.routes.health.psutil.virtual_memory')
@patch('app.routes.health.psutil.cpu_percent')
@patch('app.routes.health.psutil.disk_usage')
@patch('app.routes.health.db.session.execute')
def test_detailed_health_check_exception(mock_db_execute, mock_disk_usage, mock_cpu_percent, mock_virtual_memory, client):
    """Test detailed health check with exception."""
    # 1. Arrange
    mock_virtual_memory.side_effect = Exception("System info error")
    
    # 2. Act
    response = client.get('/detailed')
    
    # 3. Assert
    assert response.status_code == 500
    data = response.get_json()
    assert data['success'] is False
    assert '详细健康检查失败' in data['error']


@pytest.mark.unit
@patch('app.routes.health.psutil.virtual_memory')
@patch('app.routes.health.psutil.cpu_percent')
@patch('app.routes.health.psutil.disk_usage')
@patch('app.routes.health.db.session.execute')
def test_detailed_health_check_high_memory_usage(mock_db_execute, mock_disk_usage, mock_cpu_percent, mock_virtual_memory, client):
    """Test detailed health check with high memory usage."""
    # 1. Arrange
    mock_virtual_memory.return_value = Mock(percent=95.0, available=100000000)
    mock_cpu_percent.return_value = 25.0
    mock_disk_usage.return_value = Mock(percent=30.0, free=2000000000)
    mock_db_execute.return_value.fetchone.return_value = (1,)
    
    # 2. Act
    response = client.get('/detailed')
    
    # 3. Assert
    data = response.get_json()
    system_info = data['data']['system_info']
    assert system_info['memory_usage'] == 95.0
    assert system_info['memory_available'] == 100000000


@pytest.mark.unit
@patch('app.routes.health.psutil.virtual_memory')
@patch('app.routes.health.psutil.cpu_percent')
@patch('app.routes.health.psutil.disk_usage')
@patch('app.routes.health.db.session.execute')
def test_detailed_health_check_high_cpu_usage(mock_db_execute, mock_disk_usage, mock_cpu_percent, mock_virtual_memory, client):
    """Test detailed health check with high CPU usage."""
    # 1. Arrange
    mock_virtual_memory.return_value = Mock(percent=50.0, available=1000000000)
    mock_cpu_percent.return_value = 95.0
    mock_disk_usage.return_value = Mock(percent=30.0, free=2000000000)
    mock_db_execute.return_value.fetchone.return_value = (1,)
    
    # 2. Act
    response = client.get('/detailed')
    
    # 3. Assert
    data = response.get_json()
    system_info = data['data']['system_info']
    assert system_info['cpu_usage'] == 95.0


@pytest.mark.unit
@patch('app.routes.health.psutil.virtual_memory')
@patch('app.routes.health.psutil.cpu_percent')
@patch('app.routes.health.psutil.disk_usage')
@patch('app.routes.health.db.session.execute')
def test_detailed_health_check_high_disk_usage(mock_db_execute, mock_disk_usage, mock_cpu_percent, mock_virtual_memory, client):
    """Test detailed health check with high disk usage."""
    # 1. Arrange
    mock_virtual_memory.return_value = Mock(percent=50.0, available=1000000000)
    mock_cpu_percent.return_value = 25.0
    mock_disk_usage.return_value = Mock(percent=95.0, free=100000000)
    mock_db_execute.return_value.fetchone.return_value = (1,)
    
    # 2. Act
    response = client.get('/detailed')
    
    # 3. Assert
    data = response.get_json()
    system_info = data['data']['system_info']
    assert system_info['disk_usage'] == 95.0
    assert system_info['disk_free'] == 100000000


@pytest.mark.unit
@patch('app.routes.health.psutil.virtual_memory')
@patch('app.routes.health.psutil.cpu_percent')
@patch('app.routes.health.psutil.disk_usage')
@patch('app.routes.health.db.session.execute')
def test_detailed_health_check_zero_values(mock_db_execute, mock_disk_usage, mock_cpu_percent, mock_virtual_memory, client):
    """Test detailed health check with zero values."""
    # 1. Arrange
    mock_virtual_memory.return_value = Mock(percent=0.0, available=0)
    mock_cpu_percent.return_value = 0.0
    mock_disk_usage.return_value = Mock(percent=0.0, free=0)
    mock_db_execute.return_value.fetchone.return_value = (1,)
    
    # 2. Act
    response = client.get('/detailed')
    
    # 3. Assert
    data = response.get_json()
    system_info = data['data']['system_info']
    assert system_info['memory_usage'] == 0.0
    assert system_info['memory_available'] == 0
    assert system_info['cpu_usage'] == 0.0
    assert system_info['disk_usage'] == 0.0
    assert system_info['disk_free'] == 0


@pytest.mark.unit
@patch('app.routes.health.psutil.virtual_memory')
@patch('app.routes.health.psutil.cpu_percent')
@patch('app.routes.health.psutil.disk_usage')
@patch('app.routes.health.db.session.execute')
def test_detailed_health_check_negative_values(mock_db_execute, mock_disk_usage, mock_cpu_percent, mock_virtual_memory, client):
    """Test detailed health check with negative values."""
    # 1. Arrange
    mock_virtual_memory.return_value = Mock(percent=-10.0, available=-1000000)
    mock_cpu_percent.return_value = -5.0
    mock_disk_usage.return_value = Mock(percent=-20.0, free=-2000000)
    mock_db_execute.return_value.fetchone.return_value = (1,)
    
    # 2. Act
    response = client.get('/detailed')
    
    # 3. Assert
    data = response.get_json()
    system_info = data['data']['system_info']
    assert system_info['memory_usage'] == -10.0
    assert system_info['memory_available'] == -1000000
    assert system_info['cpu_usage'] == -5.0
    assert system_info['disk_usage'] == -20.0
    assert system_info['disk_free'] == -2000000


@pytest.mark.unit
@patch('app.routes.health.psutil.virtual_memory')
@patch('app.routes.health.psutil.cpu_percent')
@patch('app.routes.health.psutil.disk_usage')
@patch('app.routes.health.db.session.execute')
def test_detailed_health_check_large_values(mock_db_execute, mock_disk_usage, mock_cpu_percent, mock_virtual_memory, client):
    """Test detailed health check with large values."""
    # 1. Arrange
    mock_virtual_memory.return_value = Mock(percent=100.0, available=1000000000000)
    mock_cpu_percent.return_value = 100.0
    mock_disk_usage.return_value = Mock(percent=100.0, free=1000000000000)
    mock_db_execute.return_value.fetchone.return_value = (1,)
    
    # 2. Act
    response = client.get('/detailed')
    
    # 3. Assert
    data = response.get_json()
    system_info = data['data']['system_info']
    assert system_info['memory_usage'] == 100.0
    assert system_info['memory_available'] == 1000000000000
    assert system_info['cpu_usage'] == 100.0
    assert system_info['disk_usage'] == 100.0
    assert system_info['disk_free'] == 1000000000000


@pytest.mark.unit
@patch('app.routes.health.psutil.virtual_memory')
@patch('app.routes.health.psutil.cpu_percent')
@patch('app.routes.health.psutil.disk_usage')
@patch('app.routes.health.db.session.execute')
def test_detailed_health_check_float_precision(mock_db_execute, mock_disk_usage, mock_cpu_percent, mock_virtual_memory, client):
    """Test detailed health check with float precision."""
    # 1. Arrange
    mock_virtual_memory.return_value = Mock(percent=50.123456789, available=1234567890)
    mock_cpu_percent.return_value = 25.987654321
    mock_disk_usage.return_value = Mock(percent=30.555555555, free=9876543210)
    mock_db_execute.return_value.fetchone.return_value = (1,)
    
    # 2. Act
    response = client.get('/detailed')
    
    # 3. Assert
    data = response.get_json()
    system_info = data['data']['system_info']
    assert system_info['memory_usage'] == 50.123456789
    assert system_info['memory_available'] == 1234567890
    assert system_info['cpu_usage'] == 25.987654321
    assert system_info['disk_usage'] == 30.555555555
    assert system_info['disk_free'] == 9876543210


@pytest.mark.unit
@patch('app.routes.health.psutil.virtual_memory')
@patch('app.routes.health.psutil.cpu_percent')
@patch('app.routes.health.psutil.disk_usage')
@patch('app.routes.health.db.session.execute')
def test_detailed_health_check_response_time(mock_db_execute, mock_disk_usage, mock_cpu_percent, mock_virtual_memory, client):
    """Test detailed health check response time."""
    # 1. Arrange
    mock_virtual_memory.return_value = Mock(percent=50.0, available=1000000000)
    mock_cpu_percent.return_value = 25.0
    mock_disk_usage.return_value = Mock(percent=30.0, free=2000000000)
    mock_db_execute.return_value.fetchone.return_value = (1,)
    
    # 2. Act
    response = client.get('/detailed')
    
    # 3. Assert
    data = response.get_json()
    assert 'response_time' in data['data']
    assert data['data']['response_time'] > 0


@pytest.mark.unit
@patch('app.routes.health.psutil.virtual_memory')
@patch('app.routes.health.psutil.cpu_percent')
@patch('app.routes.health.psutil.disk_usage')
@patch('app.routes.health.db.session.execute')
def test_detailed_health_check_timestamp(mock_db_execute, mock_disk_usage, mock_cpu_percent, mock_virtual_memory, client):
    """Test detailed health check timestamp."""
    # 1. Arrange
    mock_virtual_memory.return_value = Mock(percent=50.0, available=1000000000)
    mock_cpu_percent.return_value = 25.0
    mock_disk_usage.return_value = Mock(percent=30.0, free=2000000000)
    mock_db_execute.return_value.fetchone.return_value = (1,)
    
    # 2. Act
    response = client.get('/detailed')
    
    # 3. Assert
    data = response.get_json()
    assert 'timestamp' in data['data']
    assert isinstance(data['data']['timestamp'], float)
    assert data['data']['timestamp'] > 0


@pytest.mark.unit
@patch('app.routes.health.psutil.virtual_memory')
@patch('app.routes.health.psutil.cpu_percent')
@patch('app.routes.health.psutil.disk_usage')
@patch('app.routes.health.db.session.execute')
def test_detailed_health_check_version(mock_db_execute, mock_disk_usage, mock_cpu_percent, mock_virtual_memory, client):
    """Test detailed health check version."""
    # 1. Arrange
    mock_virtual_memory.return_value = Mock(percent=50.0, available=1000000000)
    mock_cpu_percent.return_value = 25.0
    mock_disk_usage.return_value = Mock(percent=30.0, free=2000000000)
    mock_db_execute.return_value.fetchone.return_value = (1,)
    
    # 2. Act
    response = client.get('/detailed')
    
    # 3. Assert
    data = response.get_json()
    assert 'version' in data['data']
    assert data['data']['version'] == '1.0.7'


@pytest.mark.unit
def test_health_check_route_methods(client):
    """Test health check route methods."""
    # Test GET method
    response = client.get('/')
    assert response.status_code == 200
    
    # Test POST method (should work)
    response = client.post('/')
    assert response.status_code == 200
    
    # Test PUT method (should work)
    response = client.put('/')
    assert response.status_code == 200


@pytest.mark.unit
def test_health_check_root_route_methods(client):
    """Test health check root route methods."""
    # Test GET method
    response = client.get('')
    assert response.status_code == 200
    
    # Test POST method (should work)
    response = client.post('')
    assert response.status_code == 200


@pytest.mark.unit
def test_detailed_health_check_route_methods(client):
    """Test detailed health check route methods."""
    # Test GET method
    response = client.get('/detailed')
    assert response.status_code == 200
    
    # Test POST method (should work)
    response = client.post('/detailed')
    assert response.status_code == 200


@pytest.mark.unit
def test_health_check_blueprint_registration(app):
    """Test health check blueprint registration."""
    # 3. Assert
    assert 'health' in app.blueprints
    assert app.blueprints['health'] == health_bp


@pytest.mark.unit
def test_health_check_blueprint_name():
    """Test health check blueprint name."""
    assert health_bp.name == 'health'


@pytest.mark.unit
def test_health_check_blueprint_url_prefix():
    """Test health check blueprint URL prefix."""
    assert health_bp.url_prefix is None
