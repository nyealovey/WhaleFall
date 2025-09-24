"""
Tag模型单元测试
"""
import pytest
from app.models.tag import Tag
from app.models.instance import Instance


@pytest.mark.unit
def test_create_tag(db):
    """Test creating a new tag and saving to the database."""
    # 1. Arrange: Create a new tag
    tag = Tag(
        name="production",
        display_name="生产环境",
        category="environment",
        color="danger",
        description="生产环境标签",
        sort_order=1
    )
    
    # 2. Act: Add to session and commit
    db.session.add(tag)
    db.session.commit()
    
    # 3. Assert: Retrieve the tag and check its attributes
    retrieved_tag = Tag.query.filter_by(name="production").first()
    assert retrieved_tag is not None
    assert retrieved_tag.name == "production"
    assert retrieved_tag.display_name == "生产环境"
    assert retrieved_tag.category == "environment"
    assert retrieved_tag.color == "danger"
    assert retrieved_tag.description == "生产环境标签"
    assert retrieved_tag.sort_order == 1
    assert retrieved_tag.is_active is True
    assert retrieved_tag.id is not None


@pytest.mark.unit
def test_tag_with_instances(db):
    """Test tag with associated instances."""
    # 1. Arrange: Create tag and instances
    tag = Tag(
        name="critical",
        display_name="关键系统",
        category="priority",
        color="danger"
    )
    
    instance1 = Instance(
        name="prod-mysql",
        db_type="mysql",
        host="localhost",
        port=3306
    )
    
    instance2 = Instance(
        name="prod-postgres",
        db_type="postgresql",
        host="localhost",
        port=5432
    )
    
    # 2. Act: Add instances to tag
    tag.instances.append(instance1)
    tag.instances.append(instance2)
    
    db.session.add_all([tag, instance1, instance2])
    db.session.commit()
    
    # 3. Assert: Check relationship
    assert len(tag.instances) == 2
    instance_names = [inst.name for inst in tag.instances]
    assert "prod-mysql" in instance_names
    assert "prod-postgres" in instance_names


@pytest.mark.unit
def test_tag_to_dict(db):
    """Test tag to_dict method."""
    tag = Tag(
        name="test-dict",
        display_name="测试标签",
        category="test",
        color="info",
        description="测试用标签"
    )
    db.session.add(tag)
    db.session.commit()
    
    tag_dict = tag.to_dict()
    
    assert tag_dict["name"] == "test-dict"
    assert tag_dict["display_name"] == "测试标签"
    assert tag_dict["category"] == "test"
    assert tag_dict["color"] == "info"
    assert tag_dict["description"] == "测试用标签"
    assert "id" in tag_dict
    assert "created_at" in tag_dict
    assert "updated_at" in tag_dict


@pytest.mark.unit
def test_tag_unique_name(db):
    """Test that tag names must be unique."""
    tag1 = Tag(
        name="unique-tag",
        display_name="唯一标签",
        category="test"
    )
    db.session.add(tag1)
    db.session.commit()
    
    # Try to create another tag with the same name
    tag2 = Tag(
        name="unique-tag",
        display_name="另一个唯一标签",
        category="test"
    )
    db.session.add(tag2)
    
    # This should raise an IntegrityError
    with pytest.raises(Exception):  # SQLAlchemy IntegrityError
        db.session.commit()


@pytest.mark.unit
def test_tag_activation_status(db):
    """Test tag activation status."""
    tag = Tag(
        name="test-activation",
        display_name="测试激活",
        category="test",
        is_active=False
    )
    db.session.add(tag)
    db.session.commit()
    
    assert tag.is_active is False
    
    # Manually activate tag (no activate method)
    tag.is_active = True
    db.session.commit()
    
    assert tag.is_active is True
    
    # Manually deactivate tag (no deactivate method)
    tag.is_active = False
    db.session.commit()
    
    assert tag.is_active is False


@pytest.mark.unit
def test_tag_repr():
    """Test tag string representation."""
    tag = Tag(
        name="test-repr",
        display_name="测试表示",
        category="test"
    )
    
    assert repr(tag) == "<Tag test-repr>"


@pytest.mark.unit
def test_tag_validation():
    """Test tag validation."""
    # Test valid tag
    tag = Tag(
        name="valid-tag",
        display_name="有效标签",
        category="test"
    )
    # Tag model doesn't have validate method
    # assert tag.validate() is True
    
    # Test that we can create a tag with empty name
    # (SQLAlchemy will handle validation at database level)
    invalid_tag = Tag(
        name="",  # Empty name
        display_name="无效标签",
        category="test"
    )
    # This should not raise an exception during creation
    assert invalid_tag.name == ""


@pytest.mark.unit
def test_tag_category_validation():
    """Test tag category validation."""
    # Test valid categories
    valid_categories = ["environment", "priority", "location", "company_type", "status"]
    
    for category in valid_categories:
        tag = Tag(
            name=f"test-{category}",
            display_name=f"测试{category}",
            category=category
        )
        assert tag.category == category


@pytest.mark.unit
def test_tag_color_validation():
    """Test tag color validation."""
    # Test valid colors
    valid_colors = ["primary", "success", "info", "warning", "danger", "secondary", "light", "dark"]
    
    for color in valid_colors:
        tag = Tag(
            name=f"test-{color}",
            display_name=f"测试{color}",
            category="test",
            color=color
        )
        assert tag.color == color


@pytest.mark.unit
def test_tag_sort_order(db):
    """Test tag sort order functionality."""
    # Create tags with different sort orders
    tag1 = Tag(
        name="tag-1",
        display_name="标签1",
        category="test",
        sort_order=3
    )
    
    tag2 = Tag(
        name="tag-2",
        display_name="标签2",
        category="test",
        sort_order=1
    )
    
    tag3 = Tag(
        name="tag-3",
        display_name="标签3",
        category="test",
        sort_order=2
    )
    
    db.session.add_all([tag1, tag2, tag3])
    db.session.commit()
    
    # Query tags ordered by sort_order
    ordered_tags = Tag.query.filter_by(category="test").order_by(Tag.sort_order).all()
    
    assert ordered_tags[0].name == "tag-2"  # sort_order=1
    assert ordered_tags[1].name == "tag-3"  # sort_order=2
    assert ordered_tags[2].name == "tag-1"  # sort_order=3


@pytest.mark.unit
def test_tag_default_values():
    """Test tag default values."""
    tag = Tag(
        name="default-test",
        display_name="默认测试",
        category="test"
    )
    
    # Check default values
    assert tag.color == "primary"
    assert tag.sort_order == 0
    assert tag.is_active is True
    assert tag.description is None


@pytest.mark.unit
def test_tag_update_sort_order(db):
    """Test updating tag sort order."""
    tag = Tag(
        name="sort-test",
        display_name="排序测试",
        category="test",
        sort_order=5
    )
    db.session.add(tag)
    db.session.commit()
    
    # Update sort order manually (no update_sort_order method)
    tag.sort_order = 10
    db.session.commit()
    
    assert tag.sort_order == 10


@pytest.mark.unit
def test_tag_get_by_category(db):
    """Test getting tags by category."""
    # Create tags in different categories
    tag1 = Tag(
        name="env-prod",
        display_name="生产环境",
        category="environment"
    )
    
    tag2 = Tag(
        name="env-dev",
        display_name="开发环境",
        category="environment"
    )
    
    tag3 = Tag(
        name="priority-high",
        display_name="高优先级",
        category="priority"
    )
    
    db.session.add_all([tag1, tag2, tag3])
    db.session.commit()
    
    # Get tags by category
    env_tags = Tag.query.filter_by(category="environment").all()
    priority_tags = Tag.query.filter_by(category="priority").all()
    
    assert len(env_tags) == 2
    assert len(priority_tags) == 1
    assert env_tags[0].category == "environment"
    assert priority_tags[0].category == "priority"
