"""
AccountClassification模型单元测试
"""
import pytest
from app.models.account_classification import AccountClassification


@pytest.mark.unit
def test_create_account_classification(db):
    """Test creating account classification."""
    # 1. Arrange
    classification = AccountClassification(
        name="特权账户",
        description="具有特殊权限的账户",
        risk_level="high",
        color="danger",
        icon_name="fa-crown",
        priority=10,
        is_system=False,
        is_active=True
    )
    
    # 2. Act
    db.session.add(classification)
    db.session.commit()
    
    # 3. Assert
    assert classification.id is not None
    assert classification.name == "特权账户"
    assert classification.description == "具有特殊权限的账户"
    assert classification.risk_level == "high"
    assert classification.color == "danger"
    assert classification.icon_name == "fa-crown"
    assert classification.priority == 10
    assert classification.is_system is False
    assert classification.is_active is True
    assert classification.created_at is not None
    assert classification.updated_at is not None


@pytest.mark.unit
def test_create_account_classification_with_defaults(db):
    """Test creating account classification with default values."""
    # 1. Arrange
    classification = AccountClassification(name="普通账户")
    
    # 2. Act
    db.session.add(classification)
    db.session.commit()
    
    # 3. Assert
    assert classification.id is not None
    assert classification.name == "普通账户"
    assert classification.description is None
    assert classification.risk_level == "medium"
    assert classification.color is None
    assert classification.icon_name == "fa-tag"
    assert classification.priority == 0
    assert classification.is_system is False
    assert classification.is_active is True


@pytest.mark.unit
def test_account_classification_to_dict(db):
    """Test account classification to_dict method."""
    # 1. Arrange
    classification = AccountClassification(
        name="测试分类",
        description="测试描述",
        risk_level="critical",
        color="warning",
        icon_name="fa-test",
        priority=5,
        is_system=True,
        is_active=False
    )
    
    db.session.add(classification)
    db.session.commit()
    
    # 2. Act
    result = classification.to_dict()
    
    # 3. Assert
    assert result["id"] == classification.id
    assert result["name"] == "测试分类"
    assert result["description"] == "测试描述"
    assert result["risk_level"] == "critical"
    assert result["color"] == "warning"
    assert result["icon_name"] == "fa-test"
    assert result["priority"] == 5
    assert result["is_system"] is True
    assert result["is_active"] is False
    assert "created_at" in result
    assert "updated_at" in result


@pytest.mark.unit
def test_account_classification_repr(db):
    """Test account classification string representation."""
    # 1. Arrange
    classification = AccountClassification(name="测试分类")
    
    # 2. Act
    result = str(classification)
    
    # 3. Assert
    assert "AccountClassification" in result
    assert "测试分类" in result


@pytest.mark.unit
def test_account_classification_unique_name(db):
    """Test account classification unique name constraint."""
    # 1. Arrange
    classification1 = AccountClassification(name="唯一分类")
    classification2 = AccountClassification(name="唯一分类")
    
    db.session.add(classification1)
    db.session.commit()
    
    # 2. Act & Assert
    with pytest.raises(Exception):  # Should raise integrity error
        db.session.add(classification2)
        db.session.commit()


@pytest.mark.unit
def test_account_classification_required_fields(db):
    """Test account classification required fields."""
    # 1. Arrange
    classification = AccountClassification()  # Missing required name field
    
    # 2. Act & Assert
    with pytest.raises(Exception):  # Should raise integrity error
        db.session.add(classification)
        db.session.commit()


@pytest.mark.unit
def test_account_classification_risk_levels(db):
    """Test account classification different risk levels."""
    risk_levels = ["low", "medium", "high", "critical"]
    
    for risk_level in risk_levels:
        # 1. Arrange
        classification = AccountClassification(
            name=f"测试分类_{risk_level}",
            risk_level=risk_level
        )
        
        # 2. Act
        db.session.add(classification)
        db.session.commit()
        
        # 3. Assert
        assert classification.risk_level == risk_level
        
        # Clean up
        db.session.delete(classification)
        db.session.commit()


@pytest.mark.unit
def test_account_classification_priority_ordering(db):
    """Test account classification priority ordering."""
    # 1. Arrange
    classification1 = AccountClassification(name="低优先级", priority=1)
    classification2 = AccountClassification(name="高优先级", priority=10)
    classification3 = AccountClassification(name="中优先级", priority=5)
    
    # 2. Act
    db.session.add_all([classification1, classification2, classification3])
    db.session.commit()
    
    # 3. Assert
    classifications = AccountClassification.query.order_by(AccountClassification.priority.desc()).all()
    assert classifications[0].name == "高优先级"
    assert classifications[1].name == "中优先级"
    assert classifications[2].name == "低优先级"


@pytest.mark.unit
def test_account_classification_system_vs_user(db):
    """Test account classification system vs user created."""
    # 1. Arrange
    system_classification = AccountClassification(
        name="系统分类",
        is_system=True
    )
    user_classification = AccountClassification(
        name="用户分类",
        is_system=False
    )
    
    # 2. Act
    db.session.add_all([system_classification, user_classification])
    db.session.commit()
    
    # 3. Assert
    assert system_classification.is_system is True
    assert user_classification.is_system is False


@pytest.mark.unit
def test_account_classification_active_status(db):
    """Test account classification active status."""
    # 1. Arrange
    active_classification = AccountClassification(
        name="活跃分类",
        is_active=True
    )
    inactive_classification = AccountClassification(
        name="非活跃分类",
        is_active=False
    )
    
    # 2. Act
    db.session.add_all([active_classification, inactive_classification])
    db.session.commit()
    
    # 3. Assert
    assert active_classification.is_active is True
    assert inactive_classification.is_active is False


@pytest.mark.unit
def test_account_classification_color_validation(db):
    """Test account classification color validation."""
    # 1. Arrange
    colors = ["primary", "secondary", "success", "danger", "warning", "info", "light", "dark"]
    
    for color in colors:
        classification = AccountClassification(
            name=f"测试分类_{color}",
            color=color
        )
        
        # 2. Act
        db.session.add(classification)
        db.session.commit()
        
        # 3. Assert
        assert classification.color == color
        
        # Clean up
        db.session.delete(classification)
        db.session.commit()


@pytest.mark.unit
def test_account_classification_icon_names(db):
    """Test account classification icon names."""
    # 1. Arrange
    icon_names = ["fa-tag", "fa-crown", "fa-shield", "fa-user", "fa-database"]
    
    for icon_name in icon_names:
        classification = AccountClassification(
            name=f"测试分类_{icon_name}",
            icon_name=icon_name
        )
        
        # 2. Act
        db.session.add(classification)
        db.session.commit()
        
        # 3. Assert
        assert classification.icon_name == icon_name
        
        # Clean up
        db.session.delete(classification)
        db.session.commit()


@pytest.mark.unit
def test_account_classification_long_description(db):
    """Test account classification with long description."""
    # 1. Arrange
    long_description = "这是一个非常长的描述" * 100  # 300+ characters
    classification = AccountClassification(
        name="长描述分类",
        description=long_description
    )
    
    # 2. Act
    db.session.add(classification)
    db.session.commit()
    
    # 3. Assert
    assert classification.description == long_description
    assert len(classification.description) > 300


@pytest.mark.unit
def test_account_classification_empty_strings(db):
    """Test account classification with empty strings."""
    # 1. Arrange
    classification = AccountClassification(
        name="空字符串测试",
        description="",
        color="",
        icon_name=""
    )
    
    # 2. Act
    db.session.add(classification)
    db.session.commit()
    
    # 3. Assert
    assert classification.name == "空字符串测试"
    assert classification.description == ""
    assert classification.color == ""
    assert classification.icon_name == ""


@pytest.mark.unit
def test_account_classification_unicode_name(db):
    """Test account classification with unicode name."""
    # 1. Arrange
    unicode_name = "测试分类🚀🔥💯"
    classification = AccountClassification(name=unicode_name)
    
    # 2. Act
    db.session.add(classification)
    db.session.commit()
    
    # 3. Assert
    assert classification.name == unicode_name


@pytest.mark.unit
def test_account_classification_unicode_description(db):
    """Test account classification with unicode description."""
    # 1. Arrange
    unicode_description = "这是一个包含中文、英文English和特殊符号@#$%的描述"
    classification = AccountClassification(
        name="Unicode测试",
        description=unicode_description
    )
    
    # 2. Act
    db.session.add(classification)
    db.session.commit()
    
    # 3. Assert
    assert classification.description == unicode_description


@pytest.mark.unit
def test_account_classification_negative_priority(db):
    """Test account classification with negative priority."""
    # 1. Arrange
    classification = AccountClassification(
        name="负优先级测试",
        priority=-5
    )
    
    # 2. Act
    db.session.add(classification)
    db.session.commit()
    
    # 3. Assert
    assert classification.priority == -5


@pytest.mark.unit
def test_account_classification_large_priority(db):
    """Test account classification with large priority."""
    # 1. Arrange
    classification = AccountClassification(
        name="大优先级测试",
        priority=999999
    )
    
    # 2. Act
    db.session.add(classification)
    db.session.commit()
    
    # 3. Assert
    assert classification.priority == 999999


@pytest.mark.unit
def test_account_classification_boolean_fields(db):
    """Test account classification boolean fields."""
    # 1. Arrange
    classification = AccountClassification(
        name="布尔字段测试",
        is_system=True,
        is_active=False
    )
    
    # 2. Act
    db.session.add(classification)
    db.session.commit()
    
    # 3. Assert
    assert classification.is_system is True
    assert classification.is_active is False


@pytest.mark.unit
def test_account_classification_timestamps(db):
    """Test account classification timestamps."""
    # 1. Arrange
    classification = AccountClassification(name="时间戳测试")
    
    # 2. Act
    db.session.add(classification)
    db.session.commit()
    
    # 3. Assert
    assert classification.created_at is not None
    assert classification.updated_at is not None
    assert classification.created_at == classification.updated_at


@pytest.mark.unit
def test_account_classification_update_timestamp(db):
    """Test account classification update timestamp."""
    # 1. Arrange
    classification = AccountClassification(name="更新时间戳测试")
    db.session.add(classification)
    db.session.commit()
    
    original_updated_at = classification.updated_at
    
    # 2. Act
    import time
    time.sleep(0.1)  # Small delay to ensure timestamp difference
    classification.name = "更新的名称"
    db.session.commit()
    
    # 3. Assert
    assert classification.updated_at > original_updated_at


@pytest.mark.unit
def test_account_classification_query_by_risk_level(db):
    """Test querying account classifications by risk level."""
    # 1. Arrange
    high_risk = AccountClassification(name="高风险", risk_level="high")
    low_risk = AccountClassification(name="低风险", risk_level="low")
    medium_risk = AccountClassification(name="中风险", risk_level="medium")
    
    db.session.add_all([high_risk, low_risk, medium_risk])
    db.session.commit()
    
    # 2. Act
    high_risk_classifications = AccountClassification.query.filter_by(risk_level="high").all()
    low_risk_classifications = AccountClassification.query.filter_by(risk_level="low").all()
    
    # 3. Assert
    assert len(high_risk_classifications) == 1
    assert len(low_risk_classifications) == 1
    assert high_risk_classifications[0].name == "高风险"
    assert low_risk_classifications[0].name == "低风险"


@pytest.mark.unit
def test_account_classification_query_by_active_status(db):
    """Test querying account classifications by active status."""
    # 1. Arrange
    active = AccountClassification(name="活跃", is_active=True)
    inactive = AccountClassification(name="非活跃", is_active=False)
    
    db.session.add_all([active, inactive])
    db.session.commit()
    
    # 2. Act
    active_classifications = AccountClassification.query.filter_by(is_active=True).all()
    inactive_classifications = AccountClassification.query.filter_by(is_active=False).all()
    
    # 3. Assert
    assert len(active_classifications) == 1
    assert len(inactive_classifications) == 1
    assert active_classifications[0].name == "活跃"
    assert inactive_classifications[0].name == "非活跃"


@pytest.mark.unit
def test_account_classification_query_by_system_status(db):
    """Test querying account classifications by system status."""
    # 1. Arrange
    system = AccountClassification(name="系统", is_system=True)
    user = AccountClassification(name="用户", is_system=False)
    
    db.session.add_all([system, user])
    db.session.commit()
    
    # 2. Act
    system_classifications = AccountClassification.query.filter_by(is_system=True).all()
    user_classifications = AccountClassification.query.filter_by(is_system=False).all()
    
    # 3. Assert
    assert len(system_classifications) == 1
    assert len(user_classifications) == 1
    assert system_classifications[0].name == "系统"
    assert user_classifications[0].name == "用户"


@pytest.mark.unit
def test_account_classification_query_by_priority_range(db):
    """Test querying account classifications by priority range."""
    # 1. Arrange
    low_priority = AccountClassification(name="低优先级", priority=1)
    medium_priority = AccountClassification(name="中优先级", priority=5)
    high_priority = AccountClassification(name="高优先级", priority=10)
    
    db.session.add_all([low_priority, medium_priority, high_priority])
    db.session.commit()
    
    # 2. Act
    medium_priority_classifications = AccountClassification.query.filter(
        AccountClassification.priority >= 3,
        AccountClassification.priority <= 7
    ).all()
    
    # 3. Assert
    assert len(medium_priority_classifications) == 1
    assert medium_priority_classifications[0].name == "中优先级"


@pytest.mark.unit
def test_account_classification_query_by_name_like(db):
    """Test querying account classifications by name pattern."""
    # 1. Arrange
    test1 = AccountClassification(name="测试分类1")
    test2 = AccountClassification(name="测试分类2")
    other = AccountClassification(name="其他分类")
    
    db.session.add_all([test1, test2, other])
    db.session.commit()
    
    # 2. Act
    test_classifications = AccountClassification.query.filter(
        AccountClassification.name.like("测试%")
    ).all()
    
    # 3. Assert
    assert len(test_classifications) == 2
    assert all(c.name.startswith("测试") for c in test_classifications)


@pytest.mark.unit
def test_account_classification_count(db):
    """Test counting account classifications."""
    # 1. Arrange
    classifications = [
        AccountClassification(name=f"分类{i}")
        for i in range(5)
    ]
    
    db.session.add_all(classifications)
    db.session.commit()
    
    # 2. Act
    count = AccountClassification.query.count()
    
    # 3. Assert
    assert count == 5


@pytest.mark.unit
def test_account_classification_pagination(db):
    """Test paginating account classifications."""
    # 1. Arrange
    classifications = [
        AccountClassification(name=f"分类{i}")
        for i in range(10)
    ]
    
    db.session.add_all(classifications)
    db.session.commit()
    
    # 2. Act
    page1 = AccountClassification.query.paginate(page=1, per_page=5).items
    page2 = AccountClassification.query.paginate(page=2, per_page=5).items
    
    # 3. Assert
    assert len(page1) == 5
    assert len(page2) == 5
    assert page1 != page2  # Different items on different pages
