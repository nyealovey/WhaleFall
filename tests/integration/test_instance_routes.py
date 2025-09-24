"""
实例路由集成测试
"""
import pytest
from flask import Flask
from app import create_app
from app.models.instance import Instance
from app.models.credential import Credential


@pytest.mark.integration
def test_get_instances_success(client, auth_headers, db):
    """Test getting instances successfully."""
    # 1. Arrange: Create test instances
    instance1 = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb1"
    )
    instance2 = Instance(
        name="test-postgres",
        db_type="postgresql",
        host="localhost",
        port=5432,
        database_name="testdb2"
    )
    
    db.session.add_all([instance1, instance2])
    db.session.commit()
    
    # 2. Act: Get instances
    response = client.get('/instances/', headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "instances" in data
    assert len(data["instances"]) == 2


@pytest.mark.integration
def test_get_instances_unauthorized(client):
    """Test getting instances without authentication."""
    # 2. Act: Get instances without auth
    response = client.get('/instances/')
    
    # 3. Assert
    assert response.status_code == 401


@pytest.mark.integration
def test_get_instance_by_id_success(client, auth_headers, db):
    """Test getting instance by ID successfully."""
    # 1. Arrange: Create test instance
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    db.session.add(instance)
    db.session.commit()
    
    # 2. Act: Get instance by ID
    response = client.get(f'/instances/{instance.id}', headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["instance"]["name"] == "test-mysql"
    assert data["instance"]["db_type"] == "mysql"


@pytest.mark.integration
def test_get_instance_by_id_not_found(client, auth_headers):
    """Test getting instance by ID when not found."""
    # 2. Act: Get nonexistent instance
    response = client.get('/instances/999', headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 404
    data = response.get_json()
    assert data["success"] is False
    assert "未找到" in data["message"]


@pytest.mark.integration
def test_create_instance_success(client, auth_headers, db):
    """Test creating instance successfully."""
    # 2. Act: Create instance
    response = client.post('/instances/', 
                          json={
                              "name": "new-mysql",
                              "db_type": "mysql",
                              "host": "localhost",
                              "port": 3306,
                              "database_name": "newdb",
                              "description": "New MySQL instance"
                          },
                          headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    assert "创建成功" in data["message"]
    
    # Verify instance was created
    instance = Instance.query.filter_by(name="new-mysql").first()
    assert instance is not None
    assert instance.db_type == "mysql"
    assert instance.host == "localhost"


@pytest.mark.integration
def test_create_instance_duplicate_name(client, auth_headers, db):
    """Test creating instance with duplicate name."""
    # 1. Arrange: Create existing instance
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    db.session.add(instance)
    db.session.commit()
    
    # 2. Act: Create instance with same name
    response = client.post('/instances/', 
                          json={
                              "name": "test-mysql",
                              "db_type": "mysql",
                              "host": "localhost",
                              "port": 3306,
                              "database_name": "testdb"
                          },
                          headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "已存在" in data["message"]


@pytest.mark.integration
def test_create_instance_missing_fields(client, auth_headers):
    """Test creating instance with missing fields."""
    # 2. Act: Create instance without required fields
    response = client.post('/instances/', 
                          json={
                              "name": "new-mysql"
                              # Missing db_type, host, port
                          },
                          headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "必填字段" in data["message"]


@pytest.mark.integration
def test_create_instance_invalid_db_type(client, auth_headers):
    """Test creating instance with invalid database type."""
    # 2. Act: Create instance with invalid db_type
    response = client.post('/instances/', 
                          json={
                              "name": "new-mysql",
                              "db_type": "invalid_db",
                              "host": "localhost",
                              "port": 3306
                          },
                          headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "数据库类型" in data["message"]


@pytest.mark.integration
def test_create_instance_invalid_port(client, auth_headers):
    """Test creating instance with invalid port."""
    # 2. Act: Create instance with invalid port
    response = client.post('/instances/', 
                          json={
                              "name": "new-mysql",
                              "db_type": "mysql",
                              "host": "localhost",
                              "port": 99999
                          },
                          headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "端口" in data["message"]


@pytest.mark.integration
def test_update_instance_success(client, auth_headers, db):
    """Test updating instance successfully."""
    # 1. Arrange: Create test instance
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    db.session.add(instance)
    db.session.commit()
    
    # 2. Act: Update instance
    response = client.put(f'/instances/{instance.id}', 
                         json={
                             "name": "updated-mysql",
                             "db_type": "mysql",
                             "host": "localhost",
                             "port": 3306,
                             "database_name": "updateddb",
                             "description": "Updated instance"
                         },
                         headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "更新成功" in data["message"]
    
    # Verify instance was updated
    updated_instance = Instance.query.get(instance.id)
    assert updated_instance.name == "updated-mysql"
    assert updated_instance.database_name == "updateddb"
    assert updated_instance.description == "Updated instance"


@pytest.mark.integration
def test_update_instance_not_found(client, auth_headers):
    """Test updating instance when not found."""
    # 2. Act: Update nonexistent instance
    response = client.put('/instances/999', 
                         json={
                             "name": "updated-mysql",
                             "db_type": "mysql",
                             "host": "localhost",
                             "port": 3306
                         },
                         headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 404
    data = response.get_json()
    assert data["success"] is False
    assert "未找到" in data["message"]


@pytest.mark.integration
def test_update_instance_invalid_data(client, auth_headers, db):
    """Test updating instance with invalid data."""
    # 1. Arrange: Create test instance
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    db.session.add(instance)
    db.session.commit()
    
    # 2. Act: Update instance with invalid data
    response = client.put(f'/instances/{instance.id}', 
                         json={
                             "name": "",  # Empty name
                             "db_type": "mysql",
                             "host": "localhost",
                             "port": 3306
                         },
                         headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "名称" in data["message"]


@pytest.mark.integration
def test_delete_instance_success(client, auth_headers, db):
    """Test deleting instance successfully."""
    # 1. Arrange: Create test instance
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    db.session.add(instance)
    db.session.commit()
    
    # 2. Act: Delete instance
    response = client.delete(f'/instances/{instance.id}', headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "删除成功" in data["message"]
    
    # Verify instance was deleted
    deleted_instance = Instance.query.get(instance.id)
    assert deleted_instance is None


@pytest.mark.integration
def test_delete_instance_not_found(client, auth_headers):
    """Test deleting instance when not found."""
    # 2. Act: Delete nonexistent instance
    response = client.delete('/instances/999', headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 404
    data = response.get_json()
    assert data["success"] is False
    assert "未找到" in data["message"]


@pytest.mark.integration
def test_test_connection_success(client, auth_headers, db):
    """Test testing instance connection successfully."""
    # 1. Arrange: Create test instance
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    db.session.add(instance)
    db.session.commit()
    
    # Mock successful connection
    with patch('app.services.connection_test_service.ConnectionTestService.test_connection') as mock_test:
        mock_test.return_value = {
            "success": True,
            "message": "连接成功",
            "version": "8.0.32"
        }
        
        # 2. Act: Test connection
        response = client.post(f'/instances/{instance.id}/test-connection', headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "连接成功" in data["message"]


@pytest.mark.integration
def test_test_connection_failure(client, auth_headers, db):
    """Test testing instance connection failure."""
    # 1. Arrange: Create test instance
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    db.session.add(instance)
    db.session.commit()
    
    # Mock failed connection
    with patch('app.services.connection_test_service.ConnectionTestService.test_connection') as mock_test:
        mock_test.return_value = {
            "success": False,
            "message": "连接失败",
            "error": "无法连接到数据库"
        }
        
        # 2. Act: Test connection
        response = client.post(f'/instances/{instance.id}/test-connection', headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "连接失败" in data["message"]


@pytest.mark.integration
def test_test_connection_not_found(client, auth_headers):
    """Test testing connection for nonexistent instance."""
    # 2. Act: Test connection for nonexistent instance
    response = client.post('/instances/999/test-connection', headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 404
    data = response.get_json()
    assert data["success"] is False
    assert "未找到" in data["message"]


@pytest.mark.integration
def test_get_instance_with_credential(client, auth_headers, db):
    """Test getting instance with credential."""
    # 1. Arrange: Create test instance with credential
    credential = Credential(
        name="test-cred",
        credential_type="database",
        username="testuser",
        password="testpass",
        db_type="mysql"
    )
    db.session.add(credential)
    db.session.commit()
    
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb",
        credential_id=credential.id
    )
    db.session.add(instance)
    db.session.commit()
    
    # 2. Act: Get instance
    response = client.get(f'/instances/{instance.id}', headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["instance"]["credential_id"] == credential.id


@pytest.mark.integration
def test_get_instance_with_tags(client, auth_headers, db):
    """Test getting instance with tags."""
    # 1. Arrange: Create test instance
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    db.session.add(instance)
    db.session.commit()
    
    # Add tags to instance
    from app.models.tag import Tag
    tag1 = Tag(name="production", display_name="生产环境", category="environment")
    tag2 = Tag(name="mysql", display_name="MySQL", category="database")
    
    db.session.add_all([tag1, tag2])
    db.session.commit()
    
    instance.tags.append(tag1)
    instance.tags.append(tag2)
    db.session.commit()
    
    # 2. Act: Get instance
    response = client.get(f'/instances/{instance.id}', headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert len(data["instance"]["tags"]) == 2


@pytest.mark.integration
def test_get_instances_with_filters(client, auth_headers, db):
    """Test getting instances with filters."""
    # 1. Arrange: Create test instances
    instance1 = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb1"
    )
    instance2 = Instance(
        name="test-postgres",
        db_type="postgresql",
        host="localhost",
        port=5432,
        database_name="testdb2"
    )
    
    db.session.add_all([instance1, instance2])
    db.session.commit()
    
    # 2. Act: Get instances with db_type filter
    response = client.get('/instances/?db_type=mysql', headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert len(data["instances"]) == 1
    assert data["instances"][0]["db_type"] == "mysql"


@pytest.mark.integration
def test_get_instances_with_pagination(client, auth_headers, db):
    """Test getting instances with pagination."""
    # 1. Arrange: Create multiple test instances
    instances = []
    for i in range(15):
        instance = Instance(
            name=f"test-mysql-{i}",
            db_type="mysql",
            host="localhost",
            port=3306,
            database_name=f"testdb{i}"
        )
        instances.append(instance)
    
    db.session.add_all(instances)
    db.session.commit()
    
    # 2. Act: Get instances with pagination
    response = client.get('/instances/?page=1&per_page=10', headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert len(data["instances"]) == 10
    assert "pagination" in data


@pytest.mark.integration
def test_get_instances_with_search(client, auth_headers, db):
    """Test getting instances with search."""
    # 1. Arrange: Create test instances
    instance1 = Instance(
        name="production-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="prod_db"
    )
    instance2 = Instance(
        name="test-postgres",
        db_type="postgresql",
        host="localhost",
        port=5432,
        database_name="test_db"
    )
    
    db.session.add_all([instance1, instance2])
    db.session.commit()
    
    # 2. Act: Get instances with search
    response = client.get('/instances/?search=production', headers=auth_headers)
    
    # 3. Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert len(data["instances"]) == 1
    assert data["instances"][0]["name"] == "production-mysql"


@pytest.mark.integration
def test_create_instance_unauthorized(client):
    """Test creating instance without authentication."""
    # 2. Act: Create instance without auth
    response = client.post('/instances/', 
                          json={
                              "name": "new-mysql",
                              "db_type": "mysql",
                              "host": "localhost",
                              "port": 3306
                          })
    
    # 3. Assert
    assert response.status_code == 401


@pytest.mark.integration
def test_update_instance_unauthorized(client):
    """Test updating instance without authentication."""
    # 2. Act: Update instance without auth
    response = client.put('/instances/1', 
                         json={
                             "name": "updated-mysql",
                             "db_type": "mysql",
                             "host": "localhost",
                             "port": 3306
                         })
    
    # 3. Assert
    assert response.status_code == 401


@pytest.mark.integration
def test_delete_instance_unauthorized(client):
    """Test deleting instance without authentication."""
    # 2. Act: Delete instance without auth
    response = client.delete('/instances/1')
    
    # 3. Assert
    assert response.status_code == 401


@pytest.mark.integration
def test_test_connection_unauthorized(client):
    """Test testing connection without authentication."""
    # 2. Act: Test connection without auth
    response = client.post('/instances/1/test-connection')
    
    # 3. Assert
    assert response.status_code == 401
