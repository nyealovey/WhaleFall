"""
PermissionConfig模型单元测试
"""
import pytest
from app.models.permission_config import PermissionConfig


@pytest.mark.unit
def test_create_permission_config(db):
    """Test creating permission config."""
    # 1. Arrange
    permission_config = PermissionConfig(
        db_type="mysql",
        category="global_privileges",
        permission_name="SELECT",
        description="查询权限",
        is_active=True,
        sort_order=1
    )
    
    # 2. Act
    db.session.add(permission_config)
    db.session.commit()
    
    # 3. Assert
    assert permission_config.id is not None
    assert permission_config.db_type == "mysql"
    assert permission_config.category == "global_privileges"
    assert permission_config.permission_name == "SELECT"
    assert permission_config.description == "查询权限"
    assert permission_config.is_active is True
    assert permission_config.sort_order == 1
    assert permission_config.created_at is not None
    assert permission_config.updated_at is not None


@pytest.mark.unit
def test_create_permission_config_with_defaults(db):
    """Test creating permission config with default values."""
    # 1. Arrange
    permission_config = PermissionConfig(
        db_type="postgresql",
        category="database_privileges",
        permission_name="INSERT"
    )
    
    # 2. Act
    db.session.add(permission_config)
    db.session.commit()
    
    # 3. Assert
    assert permission_config.id is not None
    assert permission_config.db_type == "postgresql"
    assert permission_config.category == "database_privileges"
    assert permission_config.permission_name == "INSERT"
    assert permission_config.description is None
    assert permission_config.is_active is True
    assert permission_config.sort_order == 0


@pytest.mark.unit
def test_permission_config_to_dict(db):
    """Test permission config to_dict method."""
    # 1. Arrange
    permission_config = PermissionConfig(
        db_type="sqlserver",
        category="server_roles",
        permission_name="sysadmin",
        description="系统管理员角色",
        is_active=False,
        sort_order=10
    )
    
    db.session.add(permission_config)
    db.session.commit()
    
    # 2. Act
    result = permission_config.to_dict()
    
    # 3. Assert
    assert result["id"] == permission_config.id
    assert result["db_type"] == "sqlserver"
    assert result["category"] == "server_roles"
    assert result["permission_name"] == "sysadmin"
    assert result["description"] == "系统管理员角色"
    assert result["is_active"] is False
    assert result["sort_order"] == 10
    assert "created_at" in result
    assert "updated_at" in result


@pytest.mark.unit
def test_permission_config_repr(db):
    """Test permission config string representation."""
    # 1. Arrange
    permission_config = PermissionConfig(
        db_type="oracle",
        category="system_permissions",
        permission_name="CREATE SESSION"
    )
    
    # 2. Act
    result = str(permission_config)
    
    # 3. Assert
    assert "PermissionConfig" in result
    assert "oracle" in result
    assert "system_permissions" in result
    assert "CREATE SESSION" in result


@pytest.mark.unit
def test_permission_config_unique_constraint(db):
    """Test permission config unique constraint."""
    # 1. Arrange
    config1 = PermissionConfig(
        db_type="mysql",
        category="global_privileges",
        permission_name="SELECT"
    )
    config2 = PermissionConfig(
        db_type="mysql",
        category="global_privileges",
        permission_name="SELECT"  # Same combination
    )
    
    db.session.add(config1)
    db.session.commit()
    
    # 2. Act & Assert
    with pytest.raises(Exception):  # Should raise integrity error
        db.session.add(config2)
        db.session.commit()


@pytest.mark.unit
def test_permission_config_different_db_types(db):
    """Test permission config with different database types."""
    # 1. Arrange
    config1 = PermissionConfig(
        db_type="mysql",
        category="global_privileges",
        permission_name="SELECT"
    )
    config2 = PermissionConfig(
        db_type="postgresql",
        category="global_privileges",
        permission_name="SELECT"  # Same permission, different DB type
    )
    
    # 2. Act
    db.session.add_all([config1, config2])
    db.session.commit()
    
    # 3. Assert
    assert config1.id is not None
    assert config2.id is not None
    assert config1.db_type != config2.db_type


@pytest.mark.unit
def test_permission_config_different_categories(db):
    """Test permission config with different categories."""
    # 1. Arrange
    config1 = PermissionConfig(
        db_type="mysql",
        category="global_privileges",
        permission_name="SELECT"
    )
    config2 = PermissionConfig(
        db_type="mysql",
        category="database_privileges",
        permission_name="SELECT"  # Same permission, different category
    )
    
    # 2. Act
    db.session.add_all([config1, config2])
    db.session.commit()
    
    # 3. Assert
    assert config1.id is not None
    assert config2.id is not None
    assert config1.category != config2.category


@pytest.mark.unit
def test_permission_config_required_fields(db):
    """Test permission config required fields."""
    # 1. Arrange
    permission_config = PermissionConfig()  # Missing required fields
    
    # 2. Act & Assert
    with pytest.raises(Exception):  # Should raise integrity error
        db.session.add(permission_config)
        db.session.commit()


@pytest.mark.unit
def test_permission_config_db_types(db):
    """Test permission config different database types."""
    db_types = ["mysql", "postgresql", "sqlserver", "oracle"]
    
    for db_type in db_types:
        # 1. Arrange
        permission_config = PermissionConfig(
            db_type=db_type,
            category="global_privileges",
            permission_name=f"TEST_{db_type.upper()}"
        )
        
        # 2. Act
        db.session.add(permission_config)
        db.session.commit()
        
        # 3. Assert
        assert permission_config.db_type == db_type
        
        # Clean up
        db.session.delete(permission_config)
        db.session.commit()


@pytest.mark.unit
def test_permission_config_categories(db):
    """Test permission config different categories."""
    categories = [
        "global_privileges",
        "database_privileges",
        "server_roles",
        "database_roles",
        "server_permissions"
    ]
    
    for category in categories:
        # 1. Arrange
        permission_config = PermissionConfig(
            db_type="mysql",
            category=category,
            permission_name=f"TEST_{category.upper()}"
        )
        
        # 2. Act
        db.session.add(permission_config)
        db.session.commit()
        
        # 3. Assert
        assert permission_config.category == category
        
        # Clean up
        db.session.delete(permission_config)
        db.session.commit()


@pytest.mark.unit
def test_permission_config_permission_names(db):
    """Test permission config different permission names."""
    permission_names = [
        "SELECT", "INSERT", "UPDATE", "DELETE",
        "CREATE", "DROP", "ALTER", "INDEX",
        "GRANT", "REVOKE", "EXECUTE", "REFERENCES"
    ]
    
    for permission_name in permission_names:
        # 1. Arrange
        permission_config = PermissionConfig(
            db_type="mysql",
            category="global_privileges",
            permission_name=permission_name
        )
        
        # 2. Act
        db.session.add(permission_config)
        db.session.commit()
        
        # 3. Assert
        assert permission_config.permission_name == permission_name
        
        # Clean up
        db.session.delete(permission_config)
        db.session.commit()


@pytest.mark.unit
def test_permission_config_descriptions(db):
    """Test permission config with different descriptions."""
    descriptions = [
        "查询权限",
        "插入权限",
        "更新权限",
        "删除权限",
        "创建权限",
        "删除权限",
        "修改权限",
        "索引权限",
        "授权权限",
        "撤销权限",
        "执行权限",
        "引用权限"
    ]
    
    for i, description in enumerate(descriptions):
        # 1. Arrange
        permission_config = PermissionConfig(
            db_type="mysql",
            category="global_privileges",
            permission_name=f"TEST_{i}",
            description=description
        )
        
        # 2. Act
        db.session.add(permission_config)
        db.session.commit()
        
        # 3. Assert
        assert permission_config.description == description
        
        # Clean up
        db.session.delete(permission_config)
        db.session.commit()


@pytest.mark.unit
def test_permission_config_active_status(db):
    """Test permission config active status."""
    # 1. Arrange
    active_config = PermissionConfig(
        db_type="mysql",
        category="global_privileges",
        permission_name="ACTIVE_TEST",
        is_active=True
    )
    inactive_config = PermissionConfig(
        db_type="mysql",
        category="global_privileges",
        permission_name="INACTIVE_TEST",
        is_active=False
    )
    
    # 2. Act
    db.session.add_all([active_config, inactive_config])
    db.session.commit()
    
    # 3. Assert
    assert active_config.is_active is True
    assert inactive_config.is_active is False


@pytest.mark.unit
def test_permission_config_sort_orders(db):
    """Test permission config sort orders."""
    # 1. Arrange
    configs = []
    for i in range(5):
        config = PermissionConfig(
            db_type="mysql",
            category="global_privileges",
            permission_name=f"SORT_TEST_{i}",
            sort_order=i
        )
        configs.append(config)
    
    # 2. Act
    db.session.add_all(configs)
    db.session.commit()
    
    # 3. Assert
    for i, config in enumerate(configs):
        assert config.sort_order == i


@pytest.mark.unit
def test_permission_config_long_permission_name(db):
    """Test permission config with long permission name."""
    # 1. Arrange
    long_permission_name = "A" * 255  # Maximum length
    permission_config = PermissionConfig(
        db_type="mysql",
        category="global_privileges",
        permission_name=long_permission_name
    )
    
    # 2. Act
    db.session.add(permission_config)
    db.session.commit()
    
    # 3. Assert
    assert permission_config.permission_name == long_permission_name
    assert len(permission_config.permission_name) == 255


@pytest.mark.unit
def test_permission_config_long_description(db):
    """Test permission config with long description."""
    # 1. Arrange
    long_description = "这是一个非常长的描述" * 100  # 300+ characters
    permission_config = PermissionConfig(
        db_type="mysql",
        category="global_privileges",
        permission_name="LONG_DESC_TEST",
        description=long_description
    )
    
    # 2. Act
    db.session.add(permission_config)
    db.session.commit()
    
    # 3. Assert
    assert permission_config.description == long_description
    assert len(permission_config.description) > 300


@pytest.mark.unit
def test_permission_config_empty_strings(db):
    """Test permission config with empty strings."""
    # 1. Arrange
    permission_config = PermissionConfig(
        db_type="mysql",
        category="global_privileges",
        permission_name="EMPTY_TEST",
        description=""
    )
    
    # 2. Act
    db.session.add(permission_config)
    db.session.commit()
    
    # 3. Assert
    assert permission_config.description == ""


@pytest.mark.unit
def test_permission_config_unicode_permission_name(db):
    """Test permission config with unicode permission name."""
    # 1. Arrange
    unicode_permission_name = "测试权限🚀🔥💯"
    permission_config = PermissionConfig(
        db_type="mysql",
        category="global_privileges",
        permission_name=unicode_permission_name
    )
    
    # 2. Act
    db.session.add(permission_config)
    db.session.commit()
    
    # 3. Assert
    assert permission_config.permission_name == unicode_permission_name


@pytest.mark.unit
def test_permission_config_unicode_description(db):
    """Test permission config with unicode description."""
    # 1. Arrange
    unicode_description = "这是一个包含中文、英文English和特殊符号@#$%的描述"
    permission_config = PermissionConfig(
        db_type="mysql",
        category="global_privileges",
        permission_name="UNICODE_TEST",
        description=unicode_description
    )
    
    # 2. Act
    db.session.add(permission_config)
    db.session.commit()
    
    # 3. Assert
    assert permission_config.description == unicode_description


@pytest.mark.unit
def test_permission_config_negative_sort_order(db):
    """Test permission config with negative sort order."""
    # 1. Arrange
    permission_config = PermissionConfig(
        db_type="mysql",
        category="global_privileges",
        permission_name="NEGATIVE_SORT_TEST",
        sort_order=-5
    )
    
    # 2. Act
    db.session.add(permission_config)
    db.session.commit()
    
    # 3. Assert
    assert permission_config.sort_order == -5


@pytest.mark.unit
def test_permission_config_large_sort_order(db):
    """Test permission config with large sort order."""
    # 1. Arrange
    permission_config = PermissionConfig(
        db_type="mysql",
        category="global_privileges",
        permission_name="LARGE_SORT_TEST",
        sort_order=999999
    )
    
    # 2. Act
    db.session.add(permission_config)
    db.session.commit()
    
    # 3. Assert
    assert permission_config.sort_order == 999999


@pytest.mark.unit
def test_permission_config_timestamps(db):
    """Test permission config timestamps."""
    # 1. Arrange
    permission_config = PermissionConfig(
        db_type="mysql",
        category="global_privileges",
        permission_name="TIMESTAMP_TEST"
    )
    
    # 2. Act
    db.session.add(permission_config)
    db.session.commit()
    
    # 3. Assert
    assert permission_config.created_at is not None
    assert permission_config.updated_at is not None
    assert permission_config.created_at == permission_config.updated_at


@pytest.mark.unit
def test_permission_config_update_timestamp(db):
    """Test permission config update timestamp."""
    # 1. Arrange
    permission_config = PermissionConfig(
        db_type="mysql",
        category="global_privileges",
        permission_name="UPDATE_TIMESTAMP_TEST"
    )
    db.session.add(permission_config)
    db.session.commit()
    
    original_updated_at = permission_config.updated_at
    
    # 2. Act
    import time
    time.sleep(0.1)  # Small delay to ensure timestamp difference
    permission_config.description = "Updated description"
    db.session.commit()
    
    # 3. Assert
    assert permission_config.updated_at > original_updated_at


@pytest.mark.unit
def test_permission_config_query_by_db_type(db):
    """Test querying permission configs by database type."""
    # 1. Arrange
    mysql_config = PermissionConfig(
        db_type="mysql",
        category="global_privileges",
        permission_name="MYSQL_TEST"
    )
    postgresql_config = PermissionConfig(
        db_type="postgresql",
        category="global_privileges",
        permission_name="POSTGRESQL_TEST"
    )
    
    db.session.add_all([mysql_config, postgresql_config])
    db.session.commit()
    
    # 2. Act
    mysql_configs = PermissionConfig.query.filter_by(db_type="mysql").all()
    postgresql_configs = PermissionConfig.query.filter_by(db_type="postgresql").all()
    
    # 3. Assert
    assert len(mysql_configs) == 1
    assert len(postgresql_configs) == 1
    assert mysql_configs[0].permission_name == "MYSQL_TEST"
    assert postgresql_configs[0].permission_name == "POSTGRESQL_TEST"


@pytest.mark.unit
def test_permission_config_query_by_category(db):
    """Test querying permission configs by category."""
    # 1. Arrange
    global_config = PermissionConfig(
        db_type="mysql",
        category="global_privileges",
        permission_name="GLOBAL_TEST"
    )
    database_config = PermissionConfig(
        db_type="mysql",
        category="database_privileges",
        permission_name="DATABASE_TEST"
    )
    
    db.session.add_all([global_config, database_config])
    db.session.commit()
    
    # 2. Act
    global_configs = PermissionConfig.query.filter_by(category="global_privileges").all()
    database_configs = PermissionConfig.query.filter_by(category="database_privileges").all()
    
    # 3. Assert
    assert len(global_configs) == 1
    assert len(database_configs) == 1
    assert global_configs[0].permission_name == "GLOBAL_TEST"
    assert database_configs[0].permission_name == "DATABASE_TEST"


@pytest.mark.unit
def test_permission_config_query_by_active_status(db):
    """Test querying permission configs by active status."""
    # 1. Arrange
    active_config = PermissionConfig(
        db_type="mysql",
        category="global_privileges",
        permission_name="ACTIVE_TEST",
        is_active=True
    )
    inactive_config = PermissionConfig(
        db_type="mysql",
        category="global_privileges",
        permission_name="INACTIVE_TEST",
        is_active=False
    )
    
    db.session.add_all([active_config, inactive_config])
    db.session.commit()
    
    # 2. Act
    active_configs = PermissionConfig.query.filter_by(is_active=True).all()
    inactive_configs = PermissionConfig.query.filter_by(is_active=False).all()
    
    # 3. Assert
    assert len(active_configs) == 1
    assert len(inactive_configs) == 1
    assert active_configs[0].permission_name == "ACTIVE_TEST"
    assert inactive_configs[0].permission_name == "INACTIVE_TEST"


@pytest.mark.unit
def test_permission_config_query_by_sort_order(db):
    """Test querying permission configs by sort order."""
    # 1. Arrange
    configs = []
    for i in range(5):
        config = PermissionConfig(
            db_type="mysql",
            category="global_privileges",
            permission_name=f"SORT_QUERY_TEST_{i}",
            sort_order=i
        )
        configs.append(config)
    
    db.session.add_all(configs)
    db.session.commit()
    
    # 2. Act
    ordered_configs = PermissionConfig.query.order_by(PermissionConfig.sort_order).all()
    
    # 3. Assert
    assert len(ordered_configs) == 5
    for i, config in enumerate(ordered_configs):
        assert config.sort_order == i


@pytest.mark.unit
def test_permission_config_query_by_permission_name_like(db):
    """Test querying permission configs by permission name pattern."""
    # 1. Arrange
    select_config = PermissionConfig(
        db_type="mysql",
        category="global_privileges",
        permission_name="SELECT"
    )
    insert_config = PermissionConfig(
        db_type="mysql",
        category="global_privileges",
        permission_name="INSERT"
    )
    other_config = PermissionConfig(
        db_type="mysql",
        category="global_privileges",
        permission_name="OTHER"
    )
    
    db.session.add_all([select_config, insert_config, other_config])
    db.session.commit()
    
    # 2. Act
    select_configs = PermissionConfig.query.filter(
        PermissionConfig.permission_name.like("SEL%")
    ).all()
    
    # 3. Assert
    assert len(select_configs) == 1
    assert select_configs[0].permission_name == "SELECT"


@pytest.mark.unit
def test_permission_config_count(db):
    """Test counting permission configs."""
    # 1. Arrange
    configs = []
    for i in range(5):
        config = PermissionConfig(
            db_type="mysql",
            category="global_privileges",
            permission_name=f"COUNT_TEST_{i}"
        )
        configs.append(config)
    
    db.session.add_all(configs)
    db.session.commit()
    
    # 2. Act
    count = PermissionConfig.query.count()
    
    # 3. Assert
    assert count == 5


@pytest.mark.unit
def test_permission_config_pagination(db):
    """Test paginating permission configs."""
    # 1. Arrange
    configs = []
    for i in range(10):
        config = PermissionConfig(
            db_type="mysql",
            category="global_privileges",
            permission_name=f"PAGINATION_TEST_{i}"
        )
        configs.append(config)
    
    db.session.add_all(configs)
    db.session.commit()
    
    # 2. Act
    page1 = PermissionConfig.query.paginate(page=1, per_page=5).items
    page2 = PermissionConfig.query.paginate(page=2, per_page=5).items
    
    # 3. Assert
    assert len(page1) == 5
    assert len(page2) == 5
    assert page1 != page2  # Different items on different pages


@pytest.mark.unit
def test_permission_config_combined_query(db):
    """Test combined query with multiple filters."""
    # 1. Arrange
    configs = []
    for db_type in ["mysql", "postgresql"]:
        for category in ["global_privileges", "database_privileges"]:
            for i in range(2):
                config = PermissionConfig(
                    db_type=db_type,
                    category=category,
                    permission_name=f"COMBINED_TEST_{db_type}_{category}_{i}",
                    is_active=True
                )
                configs.append(config)
    
    db.session.add_all(configs)
    db.session.commit()
    
    # 2. Act
    mysql_global_configs = PermissionConfig.query.filter(
        PermissionConfig.db_type == "mysql",
        PermissionConfig.category == "global_privileges",
        PermissionConfig.is_active == True
    ).all()
    
    # 3. Assert
    assert len(mysql_global_configs) == 2
    assert all(config.db_type == "mysql" for config in mysql_global_configs)
    assert all(config.category == "global_privileges" for config in mysql_global_configs)
    assert all(config.is_active == True for config in mysql_global_configs)
