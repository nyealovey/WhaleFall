"""
DatabaseTypeService单元测试
"""
import pytest
from unittest.mock import Mock, patch
from app.services.database_type_service import DatabaseTypeService
from app.models.database_type_config import DatabaseTypeConfig


@pytest.mark.unit
def test_get_all_types(db):
    """Test getting all database types."""
    # 1. Arrange: Create test data
    type1 = DatabaseTypeConfig(
        name="mysql",
        display_name="MySQL",
        driver="mysql+pymysql",
        default_port=3306,
        default_schema="information_schema",
        is_active=True,
        sort_order=1
    )
    
    type2 = DatabaseTypeConfig(
        name="postgresql",
        display_name="PostgreSQL",
        driver="postgresql+psycopg2",
        default_port=5432,
        default_schema="public",
        is_active=True,
        sort_order=2
    )
    
    db.session.add_all([type1, type2])
    db.session.commit()
    
    # 2. Act
    result = DatabaseTypeService.get_all_types()
    
    # 3. Assert
    assert len(result) == 2
    assert result[0].name == "mysql"
    assert result[1].name == "postgresql"


@pytest.mark.unit
def test_get_active_types(db):
    """Test getting active database types."""
    # 1. Arrange: Create test data
    type1 = DatabaseTypeConfig(
        name="mysql",
        display_name="MySQL",
        driver="mysql+pymysql",
        default_port=3306,
        default_schema="information_schema",
        is_active=True,
        sort_order=1
    )
    
    type2 = DatabaseTypeConfig(
        name="postgresql",
        display_name="PostgreSQL",
        driver="postgresql+psycopg2",
        default_port=5432,
        default_schema="public",
        is_active=False,
        sort_order=2
    )
    
    db.session.add_all([type1, type2])
    db.session.commit()
    
    # 2. Act
    result = DatabaseTypeService.get_active_types()
    
    # 3. Assert
    assert len(result) == 1
    assert result[0].name == "mysql"
    assert result[0].is_active is True


@pytest.mark.unit
def test_get_type_by_name(db):
    """Test getting database type by name."""
    # 1. Arrange: Create test data
    db_type = DatabaseTypeConfig(
        name="mysql",
        display_name="MySQL",
        driver="mysql+pymysql",
        default_port=3306,
        default_schema="information_schema",
        is_active=True,
        sort_order=1
    )
    
    db.session.add(db_type)
    db.session.commit()
    
    # 2. Act
    result = DatabaseTypeService.get_type_by_name("mysql")
    
    # 3. Assert
    assert result is not None
    assert result.name == "mysql"
    assert result.display_name == "MySQL"


@pytest.mark.unit
def test_get_type_by_name_not_found(db):
    """Test getting database type by name when not found."""
    # 2. Act
    result = DatabaseTypeService.get_type_by_name("nonexistent")
    
    # 3. Assert
    assert result is None


@pytest.mark.unit
def test_get_type_by_id(db):
    """Test getting database type by ID."""
    # 1. Arrange: Create test data
    db_type = DatabaseTypeConfig(
        name="mysql",
        display_name="MySQL",
        driver="mysql+pymysql",
        default_port=3306,
        default_schema="information_schema",
        is_active=True,
        sort_order=1
    )
    
    db.session.add(db_type)
    db.session.commit()
    
    # 2. Act
    result = DatabaseTypeService.get_type_by_id(db_type.id)
    
    # 3. Assert
    assert result is not None
    assert result.name == "mysql"
    assert result.id == db_type.id


@pytest.mark.unit
def test_get_type_by_id_not_found(db):
    """Test getting database type by ID when not found."""
    # 2. Act
    result = DatabaseTypeService.get_type_by_id(999)
    
    # 3. Assert
    assert result is None


@pytest.mark.unit
def test_create_type_success(db):
    """Test creating database type successfully."""
    # 1. Arrange
    data = {
        "name": "mysql",
        "display_name": "MySQL",
        "driver": "mysql+pymysql",
        "default_port": 3306,
        "default_schema": "information_schema",
        "is_active": True,
        "sort_order": 1,
        "description": "MySQL database"
    }
    
    # 2. Act
    result = DatabaseTypeService.create_type(data)
    
    # 3. Assert
    assert result["success"] is True
    assert result["message"] == "数据库类型创建成功"
    assert "data" in result
    
    # Verify the type was created in database
    created_type = DatabaseTypeConfig.query.filter_by(name="mysql").first()
    assert created_type is not None
    assert created_type.display_name == "MySQL"


@pytest.mark.unit
def test_create_type_missing_required_fields(db):
    """Test creating database type with missing required fields."""
    # 1. Arrange
    data = {
        "name": "mysql",
        # Missing required fields
    }
    
    # 2. Act
    result = DatabaseTypeService.create_type(data)
    
    # 3. Assert
    assert result["success"] is False
    assert "必填字段" in result["message"]


@pytest.mark.unit
def test_create_type_duplicate_name(db):
    """Test creating database type with duplicate name."""
    # 1. Arrange: Create existing type
    existing_type = DatabaseTypeConfig(
        name="mysql",
        display_name="MySQL",
        driver="mysql+pymysql",
        default_port=3306,
        default_schema="information_schema",
        is_active=True,
        sort_order=1
    )
    
    db.session.add(existing_type)
    db.session.commit()
    
    # Try to create another type with same name
    data = {
        "name": "mysql",  # Duplicate name
        "display_name": "MySQL 2",
        "driver": "mysql+pymysql",
        "default_port": 3306,
        "default_schema": "information_schema",
        "is_active": True,
        "sort_order": 2
    }
    
    # 2. Act
    result = DatabaseTypeService.create_type(data)
    
    # 3. Assert
    assert result["success"] is False
    assert "已存在" in result["message"]


@pytest.mark.unit
def test_create_type_database_error(db):
    """Test creating database type with database error."""
    # 1. Arrange
    data = {
        "name": "mysql",
        "display_name": "MySQL",
        "driver": "mysql+pymysql",
        "default_port": 3306,
        "default_schema": "information_schema",
        "is_active": True,
        "sort_order": 1
    }
    
    # Mock database error
    with patch('app.services.database_type_service.db') as mock_db:
        mock_db.session.commit.side_effect = Exception("Database error")
        
        # 2. Act
        result = DatabaseTypeService.create_type(data)
    
    # 3. Assert
    assert result["success"] is False
    assert "创建失败" in result["message"]


@pytest.mark.unit
def test_update_type_success(db):
    """Test updating database type successfully."""
    # 1. Arrange: Create existing type
    db_type = DatabaseTypeConfig(
        name="mysql",
        display_name="MySQL",
        driver="mysql+pymysql",
        default_port=3306,
        default_schema="information_schema",
        is_active=True,
        sort_order=1
    )
    
    db.session.add(db_type)
    db.session.commit()
    
    # Update data
    data = {
        "display_name": "MySQL Updated",
        "description": "Updated description"
    }
    
    # 2. Act
    result = DatabaseTypeService.update_type(db_type.id, data)
    
    # 3. Assert
    assert result["success"] is True
    assert result["message"] == "数据库类型更新成功"
    
    # Verify the update
    updated_type = DatabaseTypeConfig.query.get(db_type.id)
    assert updated_type.display_name == "MySQL Updated"
    assert updated_type.description == "Updated description"


@pytest.mark.unit
def test_update_type_not_found(db):
    """Test updating non-existent database type."""
    # 1. Arrange
    data = {
        "display_name": "Updated"
    }
    
    # 2. Act
    result = DatabaseTypeService.update_type(999, data)
    
    # 3. Assert
    assert result["success"] is False
    assert "未找到" in result["message"]


@pytest.mark.unit
def test_delete_type_success(db):
    """Test deleting database type successfully."""
    # 1. Arrange: Create existing type
    db_type = DatabaseTypeConfig(
        name="mysql",
        display_name="MySQL",
        driver="mysql+pymysql",
        default_port=3306,
        default_schema="information_schema",
        is_active=True,
        sort_order=1
    )
    
    db.session.add(db_type)
    db.session.commit()
    
    # 2. Act
    result = DatabaseTypeService.delete_type(db_type.id)
    
    # 3. Assert
    assert result["success"] is True
    assert result["message"] == "数据库类型删除成功"
    
    # Verify the deletion
    deleted_type = DatabaseTypeConfig.query.get(db_type.id)
    assert deleted_type is None


@pytest.mark.unit
def test_delete_type_not_found(db):
    """Test deleting non-existent database type."""
    # 2. Act
    result = DatabaseTypeService.delete_type(999)
    
    # 3. Assert
    assert result["success"] is False
    assert "未找到" in result["message"]


@pytest.mark.unit
def test_delete_type_with_instances(db):
    """Test deleting database type that has associated instances."""
    # 1. Arrange: Create type with instances
    db_type = DatabaseTypeConfig(
        name="mysql",
        display_name="MySQL",
        driver="mysql+pymysql",
        default_port=3306,
        default_schema="information_schema",
        is_active=True,
        sort_order=1
    )
    
    db.session.add(db_type)
    db.session.commit()
    
    # Mock that there are associated instances
    with patch.object(DatabaseTypeConfig, 'has_instances', return_value=True):
        # 2. Act
        result = DatabaseTypeService.delete_type(db_type.id)
    
    # 3. Assert
    assert result["success"] is False
    assert "有关联实例" in result["message"]


@pytest.mark.unit
def test_validate_type_data():
    """Test validating database type data."""
    # Test valid data
    valid_data = {
        "name": "mysql",
        "display_name": "MySQL",
        "driver": "mysql+pymysql",
        "default_port": 3306,
        "default_schema": "information_schema",
        "is_active": True,
        "sort_order": 1
    }
    
    result = DatabaseTypeService._validate_type_data(valid_data)
    assert result["valid"] is True
    assert result["errors"] == []
    
    # Test invalid data
    invalid_data = {
        "name": "",  # Empty name
        "display_name": "MySQL",
        "driver": "mysql+pymysql",
        "default_port": "invalid",  # Invalid port
        "default_schema": "information_schema",
        "is_active": True,
        "sort_order": 1
    }
    
    result = DatabaseTypeService._validate_type_data(invalid_data)
    assert result["valid"] is False
    assert len(result["errors"]) > 0


@pytest.mark.unit
def test_get_type_statistics(db):
    """Test getting database type statistics."""
    # 1. Arrange: Create test data
    type1 = DatabaseTypeConfig(
        name="mysql",
        display_name="MySQL",
        driver="mysql+pymysql",
        default_port=3306,
        default_schema="information_schema",
        is_active=True,
        sort_order=1
    )
    
    type2 = DatabaseTypeConfig(
        name="postgresql",
        display_name="PostgreSQL",
        driver="postgresql+psycopg2",
        default_port=5432,
        default_schema="public",
        is_active=False,
        sort_order=2
    )
    
    db.session.add_all([type1, type2])
    db.session.commit()
    
    # 2. Act
    result = DatabaseTypeService.get_type_statistics()
    
    # 3. Assert
    assert result["total_types"] == 2
    assert result["active_types"] == 1
    assert result["inactive_types"] == 1

