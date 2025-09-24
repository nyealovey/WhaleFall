"""
SyncSessionService单元测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.sync_session_service import SyncSessionService
from app.models.sync_session import SyncSession
from app.models.sync_instance_record import SyncInstanceRecord
from app.models.instance import Instance


@pytest.mark.unit
def test_sync_session_service_init():
    """Test SyncSessionService initialization."""
    service = SyncSessionService()
    assert service is not None
    assert service.system_logger is not None
    assert service.sync_logger is not None


@pytest.mark.unit
def test_create_session_success(db):
    """Test creating sync session successfully."""
    # 1. Arrange
    service = SyncSessionService()
    
    # 2. Act
    session = service.create_session(
        sync_type="manual_batch",
        sync_category="account",
        created_by=1
    )
    
    # 3. Assert
    assert session is not None
    assert session.sync_type == "manual_batch"
    assert session.sync_category == "account"
    assert session.created_by == 1
    assert session.session_id is not None
    assert session.status == "pending"


@pytest.mark.unit
def test_create_session_without_created_by(db):
    """Test creating sync session without created_by."""
    # 1. Arrange
    service = SyncSessionService()
    
    # 2. Act
    session = service.create_session(
        sync_type="scheduled_task",
        sync_category="account"
    )
    
    # 3. Assert
    assert session is not None
    assert session.sync_type == "scheduled_task"
    assert session.sync_category == "account"
    assert session.created_by is None


@pytest.mark.unit
def test_create_session_database_error(db):
    """Test creating sync session with database error."""
    # 1. Arrange
    service = SyncSessionService()
    
    # Mock database error
    with patch('app.services.sync_session_service.db') as mock_db:
        mock_db.session.commit.side_effect = Exception("Database error")
        
        # 2. Act & Assert
        with pytest.raises(Exception):
            service.create_session(
                sync_type="manual_batch",
                sync_category="account",
                created_by=1
            )


@pytest.mark.unit
def test_get_session_by_id_success(db):
    """Test getting sync session by ID successfully."""
    # 1. Arrange
    service = SyncSessionService()
    session = service.create_session(
        sync_type="manual_batch",
        sync_category="account",
        created_by=1
    )
    
    # 2. Act
    result = service.get_session_by_id(session.session_id)
    
    # 3. Assert
    assert result is not None
    assert result.session_id == session.session_id
    assert result.sync_type == "manual_batch"


@pytest.mark.unit
def test_get_session_by_id_not_found(db):
    """Test getting sync session by ID when not found."""
    # 1. Arrange
    service = SyncSessionService()
    
    # 2. Act
    result = service.get_session_by_id("nonexistent-session-id")
    
    # 3. Assert
    assert result is None


@pytest.mark.unit
def test_get_session_by_id_none():
    """Test getting sync session by ID with None."""
    # 1. Arrange
    service = SyncSessionService()
    
    # 2. Act
    result = service.get_session_by_id(None)
    
    # 3. Assert
    assert result is None


@pytest.mark.unit
def test_update_session_status_success(db):
    """Test updating session status successfully."""
    # 1. Arrange
    service = SyncSessionService()
    session = service.create_session(
        sync_type="manual_batch",
        sync_category="account",
        created_by=1
    )
    
    # 2. Act
    result = service.update_session_status(session.session_id, "running", "开始同步")
    
    # 3. Assert
    assert result is True
    
    # Verify the update
    updated_session = service.get_session_by_id(session.session_id)
    assert updated_session.status == "running"
    assert updated_session.message == "开始同步"


@pytest.mark.unit
def test_update_session_status_not_found(db):
    """Test updating session status when session not found."""
    # 1. Arrange
    service = SyncSessionService()
    
    # 2. Act
    result = service.update_session_status("nonexistent-session-id", "running", "开始同步")
    
    # 3. Assert
    assert result is False


@pytest.mark.unit
def test_update_session_status_database_error(db):
    """Test updating session status with database error."""
    # 1. Arrange
    service = SyncSessionService()
    session = service.create_session(
        sync_type="manual_batch",
        sync_category="account",
        created_by=1
    )
    
    # Mock database error
    with patch('app.services.sync_session_service.db') as mock_db:
        mock_db.session.commit.side_effect = Exception("Database error")
        
        # 2. Act
        result = service.update_session_status(session.session_id, "running", "开始同步")
    
    # 3. Assert
    assert result is False


@pytest.mark.unit
def test_add_instance_record_success(db):
    """Test adding instance record successfully."""
    # 1. Arrange
    service = SyncSessionService()
    session = service.create_session(
        sync_type="manual_batch",
        sync_category="account",
        created_by=1
    )
    
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    db.session.add(instance)
    db.session.commit()
    
    # 2. Act
    result = service.add_instance_record(
        session.session_id,
        instance.id,
        "pending",
        "等待同步"
    )
    
    # 3. Assert
    assert result is True
    
    # Verify the record was created
    record = SyncInstanceRecord.query.filter_by(
        session_id=session.session_id,
        instance_id=instance.id
    ).first()
    assert record is not None
    assert record.status == "pending"
    assert record.message == "等待同步"


@pytest.mark.unit
def test_add_instance_record_session_not_found(db):
    """Test adding instance record when session not found."""
    # 1. Arrange
    service = SyncSessionService()
    
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    db.session.add(instance)
    db.session.commit()
    
    # 2. Act
    result = service.add_instance_record(
        "nonexistent-session-id",
        instance.id,
        "pending",
        "等待同步"
    )
    
    # 3. Assert
    assert result is False


@pytest.mark.unit
def test_add_instance_record_database_error(db):
    """Test adding instance record with database error."""
    # 1. Arrange
    service = SyncSessionService()
    session = service.create_session(
        sync_type="manual_batch",
        sync_category="account",
        created_by=1
    )
    
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    db.session.add(instance)
    db.session.commit()
    
    # Mock database error
    with patch('app.services.sync_session_service.db') as mock_db:
        mock_db.session.commit.side_effect = Exception("Database error")
        
        # 2. Act
        result = service.add_instance_record(
            session.session_id,
            instance.id,
            "pending",
            "等待同步"
        )
    
    # 3. Assert
    assert result is False


@pytest.mark.unit
def test_update_instance_record_success(db):
    """Test updating instance record successfully."""
    # 1. Arrange
    service = SyncSessionService()
    session = service.create_session(
        sync_type="manual_batch",
        sync_category="account",
        created_by=1
    )
    
    instance = Instance(
        name="test-mysql",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb"
    )
    db.session.add(instance)
    db.session.commit()
    
    # Add initial record
    service.add_instance_record(
        session.session_id,
        instance.id,
        "pending",
        "等待同步"
    )
    
    # 2. Act
    result = service.update_instance_record(
        session.session_id,
        instance.id,
        "running",
        "正在同步",
        accounts_count=10
    )
    
    # 3. Assert
    assert result is True
    
    # Verify the update
    record = SyncInstanceRecord.query.filter_by(
        session_id=session.session_id,
        instance_id=instance.id
    ).first()
    assert record.status == "running"
    assert record.message == "正在同步"
    assert record.accounts_count == 10


@pytest.mark.unit
def test_update_instance_record_not_found(db):
    """Test updating instance record when not found."""
    # 1. Arrange
    service = SyncSessionService()
    
    # 2. Act
    result = service.update_instance_record(
        "nonexistent-session-id",
        999,
        "running",
        "正在同步"
    )
    
    # 3. Assert
    assert result is False


@pytest.mark.unit
def test_get_session_records_success(db):
    """Test getting session records successfully."""
    # 1. Arrange
    service = SyncSessionService()
    session = service.create_session(
        sync_type="manual_batch",
        sync_category="account",
        created_by=1
    )
    
    instance1 = Instance(
        name="test-mysql1",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb1"
    )
    instance2 = Instance(
        name="test-mysql2",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb2"
    )
    
    db.session.add_all([instance1, instance2])
    db.session.commit()
    
    # Add records
    service.add_instance_record(session.session_id, instance1.id, "pending", "等待同步")
    service.add_instance_record(session.session_id, instance2.id, "running", "正在同步")
    
    # 2. Act
    records = service.get_session_records(session.session_id)
    
    # 3. Assert
    assert len(records) == 2
    assert any(r.instance_id == instance1.id for r in records)
    assert any(r.instance_id == instance2.id for r in records)


@pytest.mark.unit
def test_get_session_records_empty(db):
    """Test getting session records when empty."""
    # 1. Arrange
    service = SyncSessionService()
    session = service.create_session(
        sync_type="manual_batch",
        sync_category="account",
        created_by=1
    )
    
    # 2. Act
    records = service.get_session_records(session.session_id)
    
    # 3. Assert
    assert len(records) == 0


@pytest.mark.unit
def test_get_session_records_nonexistent_session(db):
    """Test getting session records for nonexistent session."""
    # 1. Arrange
    service = SyncSessionService()
    
    # 2. Act
    records = service.get_session_records("nonexistent-session-id")
    
    # 3. Assert
    assert len(records) == 0


@pytest.mark.unit
def test_get_session_statistics_success(db):
    """Test getting session statistics successfully."""
    # 1. Arrange
    service = SyncSessionService()
    session = service.create_session(
        sync_type="manual_batch",
        sync_category="account",
        created_by=1
    )
    
    instance1 = Instance(
        name="test-mysql1",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb1"
    )
    instance2 = Instance(
        name="test-mysql2",
        db_type="mysql",
        host="localhost",
        port=3306,
        database_name="testdb2"
    )
    
    db.session.add_all([instance1, instance2])
    db.session.commit()
    
    # Add records with different statuses
    service.add_instance_record(session.session_id, instance1.id, "completed", "同步完成", accounts_count=10)
    service.add_instance_record(session.session_id, instance2.id, "failed", "同步失败", accounts_count=0)
    
    # 2. Act
    stats = service.get_session_statistics(session.session_id)
    
    # 3. Assert
    assert stats is not None
    assert stats["total_instances"] == 2
    assert stats["completed_instances"] == 1
    assert stats["failed_instances"] == 1
    assert stats["pending_instances"] == 0
    assert stats["total_accounts"] == 10


@pytest.mark.unit
def test_get_session_statistics_empty(db):
    """Test getting session statistics when empty."""
    # 1. Arrange
    service = SyncSessionService()
    session = service.create_session(
        sync_type="manual_batch",
        sync_category="account",
        created_by=1
    )
    
    # 2. Act
    stats = service.get_session_statistics(session.session_id)
    
    # 3. Assert
    assert stats is not None
    assert stats["total_instances"] == 0
    assert stats["completed_instances"] == 0
    assert stats["failed_instances"] == 0
    assert stats["pending_instances"] == 0
    assert stats["total_accounts"] == 0


@pytest.mark.unit
def test_get_session_statistics_nonexistent_session(db):
    """Test getting session statistics for nonexistent session."""
    # 1. Arrange
    service = SyncSessionService()
    
    # 2. Act
    stats = service.get_session_statistics("nonexistent-session-id")
    
    # 3. Assert
    assert stats is None


@pytest.mark.unit
def test_complete_session_success(db):
    """Test completing session successfully."""
    # 1. Arrange
    service = SyncSessionService()
    session = service.create_session(
        sync_type="manual_batch",
        sync_category="account",
        created_by=1
    )
    
    # 2. Act
    result = service.complete_session(session.session_id, "同步完成", 100)
    
    # 3. Assert
    assert result is True
    
    # Verify the completion
    updated_session = service.get_session_by_id(session.session_id)
    assert updated_session.status == "completed"
    assert updated_session.message == "同步完成"
    assert updated_session.total_accounts == 100


@pytest.mark.unit
def test_complete_session_not_found(db):
    """Test completing session when not found."""
    # 1. Arrange
    service = SyncSessionService()
    
    # 2. Act
    result = service.complete_session("nonexistent-session-id", "同步完成", 100)
    
    # 3. Assert
    assert result is False


@pytest.mark.unit
def test_fail_session_success(db):
    """Test failing session successfully."""
    # 1. Arrange
    service = SyncSessionService()
    session = service.create_session(
        sync_type="manual_batch",
        sync_category="account",
        created_by=1
    )
    
    # 2. Act
    result = service.fail_session(session.session_id, "同步失败")
    
    # 3. Assert
    assert result is True
    
    # Verify the failure
    updated_session = service.get_session_by_id(session.session_id)
    assert updated_session.status == "failed"
    assert updated_session.message == "同步失败"


@pytest.mark.unit
def test_fail_session_not_found(db):
    """Test failing session when not found."""
    # 1. Arrange
    service = SyncSessionService()
    
    # 2. Act
    result = service.fail_session("nonexistent-session-id", "同步失败")
    
    # 3. Assert
    assert result is False


@pytest.mark.unit
def test_get_recent_sessions_success(db):
    """Test getting recent sessions successfully."""
    # 1. Arrange
    service = SyncSessionService()
    
    # Create multiple sessions
    session1 = service.create_session("manual_batch", "account", 1)
    session2 = service.create_session("scheduled_task", "account", 1)
    session3 = service.create_session("manual_single", "account", 1)
    
    # 2. Act
    sessions = service.get_recent_sessions(limit=2)
    
    # 3. Assert
    assert len(sessions) == 2
    # Should be ordered by created_at desc
    assert sessions[0].session_id in [session1.session_id, session2.session_id, session3.session_id]


@pytest.mark.unit
def test_get_recent_sessions_empty(db):
    """Test getting recent sessions when empty."""
    # 1. Arrange
    service = SyncSessionService()
    
    # 2. Act
    sessions = service.get_recent_sessions(limit=10)
    
    # 3. Assert
    assert len(sessions) == 0


@pytest.mark.unit
def test_get_recent_sessions_with_limit(db):
    """Test getting recent sessions with limit."""
    # 1. Arrange
    service = SyncSessionService()
    
    # Create multiple sessions
    for i in range(5):
        service.create_session("manual_batch", "account", 1)
    
    # 2. Act
    sessions = service.get_recent_sessions(limit=3)
    
    # 3. Assert
    assert len(sessions) == 3


@pytest.mark.unit
def test_cleanup_old_sessions_success(db):
    """Test cleaning up old sessions successfully."""
    # 1. Arrange
    service = SyncSessionService()
    
    # Create a session
    session = service.create_session("manual_batch", "account", 1)
    
    # 2. Act
    result = service.cleanup_old_sessions(days=0)  # Clean up all sessions
    
    # 3. Assert
    assert result is True
    
    # Verify the session was cleaned up
    cleaned_session = service.get_session_by_id(session.session_id)
    assert cleaned_session is None


@pytest.mark.unit
def test_cleanup_old_sessions_none_to_cleanup(db):
    """Test cleaning up old sessions when none to cleanup."""
    # 1. Arrange
    service = SyncSessionService()
    
    # 2. Act
    result = service.cleanup_old_sessions(days=30)
    
    # 3. Assert
    assert result is True


@pytest.mark.unit
def test_cleanup_old_sessions_database_error(db):
    """Test cleaning up old sessions with database error."""
    # 1. Arrange
    service = SyncSessionService()
    
    # Mock database error
    with patch('app.services.sync_session_service.db') as mock_db:
        mock_db.session.commit.side_effect = Exception("Database error")
        
        # 2. Act
        result = service.cleanup_old_sessions(days=30)
    
    # 3. Assert
    assert result is False
