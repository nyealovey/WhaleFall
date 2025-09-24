"""
TaskScheduler单元测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.scheduler import TaskScheduler


@pytest.mark.unit
def test_task_scheduler_init():
    """Test TaskScheduler initialization."""
    scheduler = TaskScheduler()
    assert scheduler is not None
    assert scheduler.app is None
    assert scheduler.scheduler is not None


@pytest.mark.unit
def test_task_scheduler_init_with_app():
    """Test TaskScheduler initialization with app."""
    mock_app = Mock()
    scheduler = TaskScheduler(app=mock_app)
    assert scheduler.app == mock_app
    assert scheduler.scheduler is not None


@pytest.mark.unit
@patch('app.scheduler.Path')
def test_setup_scheduler(mock_path):
    """Test scheduler setup."""
    # 1. Arrange
    mock_path_instance = Mock()
    mock_path_instance.mkdir.return_value = None
    mock_path.return_value = mock_path_instance
    
    # 2. Act
    scheduler = TaskScheduler()
    
    # 3. Assert
    assert scheduler.scheduler is not None
    mock_path_instance.mkdir.assert_called_once_with(exist_ok=True)


@pytest.mark.unit
def test_add_job_success():
    """Test adding job successfully."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    scheduler.scheduler = mock_scheduler
    
    def test_job():
        return "test"
    
    # 2. Act
    result = scheduler.add_job(
        func=test_job,
        job_id="test_job",
        trigger="interval",
        seconds=60
    )
    
    # 3. Assert
    assert result is True
    mock_scheduler.add_job.assert_called_once()


@pytest.mark.unit
def test_add_job_failure():
    """Test adding job with failure."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    mock_scheduler.add_job.side_effect = Exception("Job add error")
    scheduler.scheduler = mock_scheduler
    
    def test_job():
        return "test"
    
    # 2. Act
    result = scheduler.add_job(
        func=test_job,
        job_id="test_job",
        trigger="interval",
        seconds=60
    )
    
    # 3. Assert
    assert result is False


@pytest.mark.unit
def test_remove_job_success():
    """Test removing job successfully."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    scheduler.scheduler = mock_scheduler
    
    # 2. Act
    result = scheduler.remove_job("test_job")
    
    # 3. Assert
    assert result is True
    mock_scheduler.remove_job.assert_called_once_with("test_job")


@pytest.mark.unit
def test_remove_job_failure():
    """Test removing job with failure."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    mock_scheduler.remove_job.side_effect = Exception("Job remove error")
    scheduler.scheduler = mock_scheduler
    
    # 2. Act
    result = scheduler.remove_job("test_job")
    
    # 3. Assert
    assert result is False


@pytest.mark.unit
def test_pause_job_success():
    """Test pausing job successfully."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    scheduler.scheduler = mock_scheduler
    
    # 2. Act
    result = scheduler.pause_job("test_job")
    
    # 3. Assert
    assert result is True
    mock_scheduler.pause_job.assert_called_once_with("test_job")


@pytest.mark.unit
def test_pause_job_failure():
    """Test pausing job with failure."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    mock_scheduler.pause_job.side_effect = Exception("Job pause error")
    scheduler.scheduler = mock_scheduler
    
    # 2. Act
    result = scheduler.pause_job("test_job")
    
    # 3. Assert
    assert result is False


@pytest.mark.unit
def test_resume_job_success():
    """Test resuming job successfully."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    scheduler.scheduler = mock_scheduler
    
    # 2. Act
    result = scheduler.resume_job("test_job")
    
    # 3. Assert
    assert result is True
    mock_scheduler.resume_job.assert_called_once_with("test_job")


@pytest.mark.unit
def test_resume_job_failure():
    """Test resuming job with failure."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    mock_scheduler.resume_job.side_effect = Exception("Job resume error")
    scheduler.scheduler = mock_scheduler
    
    # 2. Act
    result = scheduler.resume_job("test_job")
    
    # 3. Assert
    assert result is False


@pytest.mark.unit
def test_get_job_success():
    """Test getting job successfully."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    mock_job = Mock()
    mock_scheduler.get_job.return_value = mock_job
    scheduler.scheduler = mock_scheduler
    
    # 2. Act
    result = scheduler.get_job("test_job")
    
    # 3. Assert
    assert result == mock_job
    mock_scheduler.get_job.assert_called_once_with("test_job")


@pytest.mark.unit
def test_get_job_not_found():
    """Test getting job when not found."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    mock_scheduler.get_job.return_value = None
    scheduler.scheduler = mock_scheduler
    
    # 2. Act
    result = scheduler.get_job("test_job")
    
    # 3. Assert
    assert result is None


@pytest.mark.unit
def test_get_jobs_success():
    """Test getting all jobs successfully."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    mock_jobs = [Mock(), Mock()]
    mock_scheduler.get_jobs.return_value = mock_jobs
    scheduler.scheduler = mock_scheduler
    
    # 2. Act
    result = scheduler.get_jobs()
    
    # 3. Assert
    assert result == mock_jobs
    mock_scheduler.get_jobs.assert_called_once()


@pytest.mark.unit
def test_get_jobs_empty():
    """Test getting jobs when empty."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    mock_scheduler.get_jobs.return_value = []
    scheduler.scheduler = mock_scheduler
    
    # 2. Act
    result = scheduler.get_jobs()
    
    # 3. Assert
    assert result == []


@pytest.mark.unit
def test_start_scheduler_success():
    """Test starting scheduler successfully."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    scheduler.scheduler = mock_scheduler
    
    # 2. Act
    result = scheduler.start()
    
    # 3. Assert
    assert result is True
    mock_scheduler.start.assert_called_once()


@pytest.mark.unit
def test_start_scheduler_failure():
    """Test starting scheduler with failure."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    mock_scheduler.start.side_effect = Exception("Scheduler start error")
    scheduler.scheduler = mock_scheduler
    
    # 2. Act
    result = scheduler.start()
    
    # 3. Assert
    assert result is False


@pytest.mark.unit
def test_stop_scheduler_success():
    """Test stopping scheduler successfully."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    scheduler.scheduler = mock_scheduler
    
    # 2. Act
    result = scheduler.stop()
    
    # 3. Assert
    assert result is True
    mock_scheduler.shutdown.assert_called_once()


@pytest.mark.unit
def test_stop_scheduler_failure():
    """Test stopping scheduler with failure."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    mock_scheduler.shutdown.side_effect = Exception("Scheduler stop error")
    scheduler.scheduler = mock_scheduler
    
    # 2. Act
    result = scheduler.stop()
    
    # 3. Assert
    assert result is False


@pytest.mark.unit
def test_is_running_true():
    """Test checking if scheduler is running."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    mock_scheduler.running = True
    scheduler.scheduler = mock_scheduler
    
    # 2. Act
    result = scheduler.is_running()
    
    # 3. Assert
    assert result is True


@pytest.mark.unit
def test_is_running_false():
    """Test checking if scheduler is not running."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    mock_scheduler.running = False
    scheduler.scheduler = mock_scheduler
    
    # 2. Act
    result = scheduler.is_running()
    
    # 3. Assert
    assert result is False


@pytest.mark.unit
def test_add_cron_job():
    """Test adding cron job."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    scheduler.scheduler = mock_scheduler
    
    def test_job():
        return "test"
    
    # 2. Act
    result = scheduler.add_job(
        func=test_job,
        job_id="cron_job",
        trigger="cron",
        hour=9,
        minute=0
    )
    
    # 3. Assert
    assert result is True
    mock_scheduler.add_job.assert_called_once()


@pytest.mark.unit
def test_add_date_job():
    """Test adding date job."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    scheduler.scheduler = mock_scheduler
    
    def test_job():
        return "test"
    
    # 2. Act
    result = scheduler.add_job(
        func=test_job,
        job_id="date_job",
        trigger="date",
        run_date="2024-12-31 23:59:59"
    )
    
    # 3. Assert
    assert result is True
    mock_scheduler.add_job.assert_called_once()


@pytest.mark.unit
def test_add_job_with_args():
    """Test adding job with arguments."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    scheduler.scheduler = mock_scheduler
    
    def test_job(arg1, arg2):
        return f"{arg1}_{arg2}"
    
    # 2. Act
    result = scheduler.add_job(
        func=test_job,
        job_id="args_job",
        trigger="interval",
        seconds=60,
        args=["value1", "value2"]
    )
    
    # 3. Assert
    assert result is True
    mock_scheduler.add_job.assert_called_once()


@pytest.mark.unit
def test_add_job_with_kwargs():
    """Test adding job with keyword arguments."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    scheduler.scheduler = mock_scheduler
    
    def test_job(**kwargs):
        return kwargs
    
    # 2. Act
    result = scheduler.add_job(
        func=test_job,
        job_id="kwargs_job",
        trigger="interval",
        seconds=60,
        kwargs={"key1": "value1", "key2": "value2"}
    )
    
    # 3. Assert
    assert result is True
    mock_scheduler.add_job.assert_called_once()


@pytest.mark.unit
def test_add_job_with_replace_existing():
    """Test adding job with replace_existing."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    scheduler.scheduler = mock_scheduler
    
    def test_job():
        return "test"
    
    # 2. Act
    result = scheduler.add_job(
        func=test_job,
        job_id="replace_job",
        trigger="interval",
        seconds=60,
        replace_existing=True
    )
    
    # 3. Assert
    assert result is True
    mock_scheduler.add_job.assert_called_once()


@pytest.mark.unit
def test_add_job_with_max_instances():
    """Test adding job with max_instances."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    scheduler.scheduler = mock_scheduler
    
    def test_job():
        return "test"
    
    # 2. Act
    result = scheduler.add_job(
        func=test_job,
        job_id="max_instances_job",
        trigger="interval",
        seconds=60,
        max_instances=3
    )
    
    # 3. Assert
    assert result is True
    mock_scheduler.add_job.assert_called_once()


@pytest.mark.unit
def test_add_job_with_misfire_grace_time():
    """Test adding job with misfire_grace_time."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    scheduler.scheduler = mock_scheduler
    
    def test_job():
        return "test"
    
    # 2. Act
    result = scheduler.add_job(
        func=test_job,
        job_id="misfire_job",
        trigger="interval",
        seconds=60,
        misfire_grace_time=600
    )
    
    # 3. Assert
    assert result is True
    mock_scheduler.add_job.assert_called_once()


@pytest.mark.unit
def test_add_job_with_coalesce():
    """Test adding job with coalesce."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    scheduler.scheduler = mock_scheduler
    
    def test_job():
        return "test"
    
    # 2. Act
    result = scheduler.add_job(
        func=test_job,
        job_id="coalesce_job",
        trigger="interval",
        seconds=60,
        coalesce=True
    )
    
    # 3. Assert
    assert result is True
    mock_scheduler.add_job.assert_called_once()


@pytest.mark.unit
def test_add_job_with_jobstore():
    """Test adding job with specific jobstore."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    scheduler.scheduler = mock_scheduler
    
    def test_job():
        return "test"
    
    # 2. Act
    result = scheduler.add_job(
        func=test_job,
        job_id="jobstore_job",
        trigger="interval",
        seconds=60,
        jobstore="default"
    )
    
    # 3. Assert
    assert result is True
    mock_scheduler.add_job.assert_called_once()


@pytest.mark.unit
def test_add_job_with_executor():
    """Test adding job with specific executor."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    scheduler.scheduler = mock_scheduler
    
    def test_job():
        return "test"
    
    # 2. Act
    result = scheduler.add_job(
        func=test_job,
        job_id="executor_job",
        trigger="interval",
        seconds=60,
        executor="default"
    )
    
    # 3. Assert
    assert result is True
    mock_scheduler.add_job.assert_called_once()


@pytest.mark.unit
def test_add_job_with_name():
    """Test adding job with name."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    scheduler.scheduler = mock_scheduler
    
    def test_job():
        return "test"
    
    # 2. Act
    result = scheduler.add_job(
        func=test_job,
        job_id="name_job",
        trigger="interval",
        seconds=60,
        name="Test Job"
    )
    
    # 3. Assert
    assert result is True
    mock_scheduler.add_job.assert_called_once()


@pytest.mark.unit
def test_add_job_with_description():
    """Test adding job with description."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    scheduler.scheduler = mock_scheduler
    
    def test_job():
        return "test"
    
    # 2. Act
    result = scheduler.add_job(
        func=test_job,
        job_id="desc_job",
        trigger="interval",
        seconds=60,
        description="Test job description"
    )
    
    # 3. Assert
    assert result is True
    mock_scheduler.add_job.assert_called_once()


@pytest.mark.unit
def test_add_job_with_id():
    """Test adding job with custom ID."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    scheduler.scheduler = mock_scheduler
    
    def test_job():
        return "test"
    
    # 2. Act
    result = scheduler.add_job(
        func=test_job,
        job_id="custom_id_job",
        trigger="interval",
        seconds=60
    )
    
    # 3. Assert
    assert result is True
    mock_scheduler.add_job.assert_called_once()


@pytest.mark.unit
def test_add_job_without_id():
    """Test adding job without ID."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    scheduler.scheduler = mock_scheduler
    
    def test_job():
        return "test"
    
    # 2. Act
    result = scheduler.add_job(
        func=test_job,
        trigger="interval",
        seconds=60
    )
    
    # 3. Assert
    assert result is True
    mock_scheduler.add_job.assert_called_once()


@pytest.mark.unit
def test_scheduler_context_manager():
    """Test scheduler as context manager."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    scheduler.scheduler = mock_scheduler
    
    # 2. Act & Assert
    with scheduler:
        assert scheduler.is_running() is True
        mock_scheduler.start.assert_called_once()
    
    mock_scheduler.shutdown.assert_called_once()


@pytest.mark.unit
def test_scheduler_context_manager_exception():
    """Test scheduler context manager with exception."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    scheduler.scheduler = mock_scheduler
    
    # 2. Act & Assert
    with pytest.raises(Exception):
        with scheduler:
            raise Exception("Test exception")
    
    mock_scheduler.start.assert_called_once()
    mock_scheduler.shutdown.assert_called_once()


@pytest.mark.unit
def test_scheduler_context_manager_start_failure():
    """Test scheduler context manager with start failure."""
    # 1. Arrange
    scheduler = TaskScheduler()
    mock_scheduler = Mock()
    mock_scheduler.start.side_effect = Exception("Start error")
    scheduler.scheduler = mock_scheduler
    
    # 2. Act & Assert
    with pytest.raises(Exception):
        with scheduler:
            pass
    
    mock_scheduler.start.assert_called_once()
    # Should not call shutdown if start failed
    mock_scheduler.shutdown.assert_not_called()
