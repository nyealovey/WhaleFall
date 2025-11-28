"""
鲸落定时任务调度器
使用APScheduler实现轻量级定时任务
"""

import atexit
import os
from pathlib import Path
from typing import Any

try:
    import fcntl  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - Windows 环境不会加载
    fcntl = None

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from app.utils.structlog_config import get_system_logger

logger = get_system_logger()
_scheduler_lock_handle = None
_scheduler_lock_pid: int | None = None


# 配置日志
class TaskScheduler:
    """定时任务调度器"""

    def __init__(self, app: Any = None) -> None:  # noqa: ANN401
        self.app = app
        self.scheduler = None
        self._setup_scheduler()

    def _setup_scheduler(self) -> None:
        """配置 APScheduler 并注册事件监听。

        准备 SQLite jobstore、线程执行器与默认任务参数，随后创建后台调度器实例并
        绑定成功/失败事件，确保所有调度器行为集中在同一处完成。

        Returns:
            None: 初始化完成后立即返回。
        """
        # 任务存储配置 - 使用本地SQLite
        
        # 创建userdata目录
        userdata_dir = Path("userdata")
        userdata_dir.mkdir(exist_ok=True)
        
        # 使用本地SQLite数据库
        sqlite_path = userdata_dir / "scheduler.db"
        database_url = f"sqlite:///{sqlite_path.absolute()}"
        
        jobstores = {"default": SQLAlchemyJobStore(url=database_url)}

        # 执行器配置
        executors = {"default": ThreadPoolExecutor(max_workers=5)}

        # 任务默认配置
        job_defaults = {
            "coalesce": True,  # 合并相同任务
            "max_instances": 1,  # 最大实例数
            "misfire_grace_time": 300,  # 错过执行时间容忍度（秒）
        }

        # 创建调度器
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="Asia/Shanghai",
        )

        # 添加事件监听器
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)

    def _job_executed(self, event: Any) -> None:  # noqa: ANN401
        """处理任务成功事件。

        Args:
            event: APScheduler 事件对象，包含 job_id 与返回值。

        Returns:
            None: 仅记录日志。
        """
        logger.info(f"任务执行成功: {event.job_id} - {event.retval}")

    def _job_error(self, event: Any) -> None:  # noqa: ANN401
        """处理任务失败事件。

        Args:
            event: APScheduler 事件对象，包含异常信息。

        Returns:
            None: 仅记录错误日志。
        """
        exception_str = str(event.exception) if event.exception else "未知错误"
        logger.error(f"任务执行失败: {event.job_id} - {exception_str}")

    def start(self) -> None:
        """启动调度器。

        Returns:
            None: 调度器启动或确认已运行后返回。
        """
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("定时任务调度器已启动")
        else:
            logger.warning("定时任务调度器已经在运行，跳过启动")

    def stop(self) -> None:
        """停止调度器。

        Returns:
            None: 调度器关闭后返回。
        """
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("定时任务调度器已停止")

    def add_job(self, func: Any, trigger: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        """向调度器注册任务。

        Args:
            func: 需要调度的可调用对象。
            trigger: APScheduler 触发器或触发器关键字参数。
            **kwargs: 传递给 `scheduler.add_job` 的其它参数，如 id/name。

        Returns:
            Job: APScheduler 新建任务对象。
        """
        return self.scheduler.add_job(func, trigger, **kwargs)

    def remove_job(self, job_id: str) -> None:
        """删除任务。

        Args:
            job_id: 任务唯一 ID。

        Returns:
            None: 删除或记录失败信息后返回。
        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"任务已删除: {job_id}")
        except Exception as e:
            error_str = str(e) if e else "未知错误"
            logger.error(f"删除任务失败: {job_id} - {error_str}")

    def get_jobs(self) -> list:
        """列出所有任务。

        Returns:
            list: APScheduler job 列表。
        """
        return self.scheduler.get_jobs()

    def get_job(self, job_id: str) -> Any:  # noqa: ANN401
        """获取指定任务。

        Args:
            job_id: 任务 ID。

        Returns:
            Job | None: 匹配的 APScheduler 任务对象。
        """
        return self.scheduler.get_job(job_id)

    def pause_job(self, job_id: str) -> None:
        """暂停任务。

        Args:
            job_id: 任务 ID。

        Returns:
            None: 任务被暂停后返回。
        """
        self.scheduler.pause_job(job_id)
        logger.info(f"任务已暂停: {job_id}")

    def resume_job(self, job_id: str) -> None:
        """恢复任务。

        Args:
            job_id: 任务 ID。

        Returns:
            None: 任务被恢复后返回。
        """
        self.scheduler.resume_job(job_id)
        logger.info(f"任务已恢复: {job_id}")


# 全局调度器实例
scheduler = TaskScheduler()


# 确保scheduler实例可以被正确访问
def get_scheduler() -> Any:  # noqa: ANN401
    """获取底层 APScheduler 实例。

    Returns:
        BackgroundScheduler | None: 正在运行的调度器对象。
    """
    return scheduler.scheduler


def _acquire_scheduler_lock() -> bool:
    """尝试获取文件锁，确保单进程运行调度器。

    Returns:
        bool: 成功获取锁返回 True，否则返回 False。
    """
    global _scheduler_lock_handle, _scheduler_lock_pid

    if fcntl is None:
        logger.warning("当前平台不支持fcntl，无法加文件锁，可能存在多个调度器实例并发运行")
        return True

    current_pid = os.getpid()

    if _scheduler_lock_handle:
        if _scheduler_lock_pid == current_pid:
            return True
        # 子进程继承了锁句柄，但并未真正持有锁，需要重新获取
        try:
            _scheduler_lock_handle.close()
        except Exception:  # pragma: no cover - 防御性释放
            pass
        _scheduler_lock_handle = None
        _scheduler_lock_pid = None

    if _scheduler_lock_handle:
        return True

    lock_path = Path("userdata") / "scheduler.lock"
    lock_path.parent.mkdir(exist_ok=True)
    handle = open(lock_path, "w+")  # noqa: P202
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        handle.write(str(os.getpid()))
        handle.flush()
        _scheduler_lock_handle = handle
        _scheduler_lock_pid = current_pid
        logger.info("调度器锁已获取，当前进程负责运行定时任务", pid=os.getpid())
        return True
    except BlockingIOError:
        handle.close()
        logger.info("检测到其他进程正在运行调度器，跳过当前进程的调度器初始化")
        return False
    except Exception as exc:  # pragma: no cover - 极端情况
        handle.close()
        logger.error(f"获取调度器锁失败: {exc}")
        return False


def _release_scheduler_lock() -> None:
    """释放调度器文件锁并清理句柄。

    Returns:
        None: 锁释放或无需释放时直接返回。
    """
    global _scheduler_lock_handle, _scheduler_lock_pid
    if fcntl is None or not _scheduler_lock_handle:
        return
    try:
        fcntl.flock(_scheduler_lock_handle, fcntl.LOCK_UN)
    except Exception:  # pragma: no cover
        pass
    try:
        _scheduler_lock_handle.close()
    except Exception:  # pragma: no cover
        pass
    finally:
        _scheduler_lock_handle = None
        _scheduler_lock_pid = None


atexit.register(_release_scheduler_lock)


def _should_start_scheduler() -> bool:
    """根据环境变量及进程角色判断是否需启动调度器。

    Returns:
        bool: True 表示可以启动，False 表示跳过。
    """
    enable_flag = os.environ.get("ENABLE_SCHEDULER", "true").strip().lower()
    if enable_flag not in ("true", "1", "yes"):
        logger.info(f"检测到 ENABLE_SCHEDULER={enable_flag}，跳过调度器初始化")
        return False

    server_software = os.environ.get("SERVER_SOFTWARE", "")
    if server_software.startswith("gunicorn"):
        parent_pid = os.getppid()
        logger.info(f"检测到 gunicorn 环境，ppid={parent_pid}，将通过文件锁保证单实例")

    # Flask reloader: 只有子进程 (WERKZEUG_RUN_MAIN=true) 才运行调度器
    if os.environ.get("FLASK_RUN_FROM_CLI") == "true":
        reloader_flag = os.environ.get("WERKZEUG_RUN_MAIN")
        if reloader_flag not in ("true", "1"):
            logger.info("检测到 Flask reloader 父进程，跳过调度器初始化")
            return False

    return True


def init_scheduler(app: Any) -> None:  # noqa: ANN401
    """初始化调度器（仅在允许的进程中启动）。

    Args:
        app: Flask 应用实例，用于任务上下文。

    Returns:
        TaskScheduler | None: 初始化成功时返回 TaskScheduler，否则返回 None。
    """
    global scheduler

    if not _should_start_scheduler():
        return None

    if not _acquire_scheduler_lock():
        return None

    try:
        # 检查是否已经初始化过
        if hasattr(scheduler, "app") and scheduler.app is not None:
            logger.warning("调度器已经初始化过，跳过重复初始化")
            return scheduler

        scheduler.app = app
        
        # 确保SQLite数据库文件存在
        sqlite_path = Path("userdata/scheduler.db")
        if not sqlite_path.exists():
            logger.info("创建SQLite调度器数据库文件")
            sqlite_path.parent.mkdir(exist_ok=True)
            sqlite_path.touch()
        
        scheduler.start()

        # 等待调度器完全启动
        import time
        time.sleep(2)
        
        # 从数据库加载现有任务
        _load_existing_jobs()
        
        # 如果没有现有任务，则添加默认任务
        _add_default_jobs()

        logger.info("调度器初始化完成")
        return scheduler
    except Exception as e:
        logger.error(f"调度器初始化失败: {e}")
        # 不抛出异常，让应用继续启动
        return None


def _load_existing_jobs() -> None:
    """从 SQLite jobstore 恢复既有任务。

    Returns:
        None: 任务加载结束或被跳过后返回。
    """
    try:
        # 检查调度器是否已启动
        if not scheduler.scheduler or not scheduler.scheduler.running:
            logger.warning("调度器未启动，跳过加载现有任务")
            return
            
        # 检查调度器是否完全就绪
        if not hasattr(scheduler.scheduler, '_jobstores_lock'):
            logger.warning("调度器未完全就绪，跳过加载现有任务")
            return
            
        # 检查SQLite数据库文件是否存在
        sqlite_path = Path("userdata/scheduler.db")
        if not sqlite_path.exists():
            logger.warning("SQLite数据库文件不存在，跳过加载现有任务")
            return
            
        # 使用try-except包装get_jobs调用，避免KeyboardInterrupt
        try:
            existing_jobs = scheduler.get_jobs()
            if existing_jobs:
                logger.info(f"从SQLite数据库加载了 {len(existing_jobs)} 个现有任务")
                for job in existing_jobs:
                    logger.info(f"加载任务: {job.name} ({job.id})")
            else:
                logger.info("SQLite数据库中没有找到任务")
        except KeyboardInterrupt:
            logger.warning("加载任务时被中断，跳过加载现有任务")
            return
        except Exception as e:
            logger.error(f"获取任务列表失败: {e}")
            return
    except Exception as e:
        logger.error(f"加载现有任务失败: {e}")
        # 不抛出异常，让应用继续启动


def _add_default_jobs() -> None:
    """在 jobstore 为空时添加默认任务。

    Returns:
        None: 调用 `_load_tasks_from_config` 后返回。
    """
    _load_tasks_from_config(force=False)


def _reload_all_jobs() -> None:
    """强制重新加载全部任务配置。

    Returns:
        None: 触发 `_load_tasks_from_config` 后返回。
    """
    _load_tasks_from_config(force=True)


def _load_tasks_from_config(force: bool = False) -> None:
    """从配置文件加载默认任务并注册。

    Args:
        force: True 表示强制重建（会删除已有任务）。

    Returns:
        None: 读取配置并尝试创建任务后返回。
    """
    import yaml

    from app.tasks.log_cleanup_tasks import cleanup_old_logs
    from app.tasks.accounts_sync_tasks import sync_accounts
    from app.tasks.partition_management_tasks import monitor_partition_health
    from app.tasks.capacity_collection_tasks import collect_database_sizes
    from app.tasks.capacity_aggregation_tasks import calculate_database_size_aggregations

    # 如果不是强制模式，检查是否已有任务
    if not force:
        try:
            existing_jobs = scheduler.get_jobs()
            if existing_jobs:
                logger.info(f"发现 {len(existing_jobs)} 个现有任务，跳过创建默认任务")
                return
        except KeyboardInterrupt:
            logger.warning("检查现有任务时被中断，跳过创建默认任务")
            return
        except Exception as e:
            logger.error(f"检查现有任务失败: {e}")
            return

    # 从配置文件读取默认任务
    config_file = os.path.join(os.path.dirname(__file__), "config", "scheduler_tasks.yaml")

    try:
        with open(config_file, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        default_tasks = config.get("default_tasks", [])

        for task_config in default_tasks:
            if not task_config.get("enabled", True):
                continue

            task_id = task_config["id"]
            task_name = task_config["name"]
            function_name = task_config["function"]
            trigger_type = task_config["trigger_type"]
            trigger_params = task_config.get("trigger_params", {})

            # 获取函数对象
            task_func_map = {
                "sync_accounts": sync_accounts,
                "cleanup_old_logs": cleanup_old_logs,
                "monitor_partition_health": monitor_partition_health,
                "collect_database_sizes": collect_database_sizes,
                "calculate_database_size_aggregations": calculate_database_size_aggregations,
            }

            func = task_func_map.get(function_name)
            if not func:
                logger.warning(f"未知的任务函数: {function_name}")
                continue

            # 创建任务
            try:
                # 如果是强制模式，先删除现有任务
                if force:
                    try:
                        scheduler.remove_job(task_id)
                        logger.info(f"强制模式-删除现有任务: {task_name} ({task_id})")
                    except Exception:
                        pass  # 任务不存在，忽略错误
                
                # 对于cron触发器，确保使用正确的时区
                if trigger_type == "cron":
                    from apscheduler.triggers.cron import CronTrigger
                    # 只传递实际配置的字段，避免APScheduler自动填充默认值
                    cron_kwargs = {}
                    if "second" in trigger_params:
                        cron_kwargs["second"] = trigger_params["second"]
                    if "minute" in trigger_params:
                        cron_kwargs["minute"] = trigger_params["minute"]
                    if "hour" in trigger_params:
                        cron_kwargs["hour"] = trigger_params["hour"]
                    if "day" in trigger_params:
                        cron_kwargs["day"] = trigger_params["day"]
                    if "month" in trigger_params:
                        cron_kwargs["month"] = trigger_params["month"]
                    if "day_of_week" in trigger_params:
                        cron_kwargs["day_of_week"] = trigger_params["day_of_week"]
                    if "year" in trigger_params:
                        cron_kwargs["year"] = trigger_params["year"]
                    
                    cron_kwargs["timezone"] = "Asia/Shanghai"
                    trigger = CronTrigger(**cron_kwargs)
                    scheduler.add_job(
                        func,
                        trigger,
                        id=task_id,
                        name=task_name,
                    )
                else:
                    scheduler.add_job(
                        func,
                        trigger_type,
                        id=task_id,
                        name=task_name,
                        **trigger_params,
                    )
                logger.info(f"添加任务: {task_name} ({task_id})")
            except Exception as e:
                if force:
                    logger.error(f"强制模式-创建任务失败: {task_name} ({task_id}) - {e}")
                else:
                    logger.warning(f"任务已存在，跳过创建: {task_name} ({task_id}) - {e}")

    except FileNotFoundError:
        logger.error(f"配置文件不存在: {config_file}，无法加载默认任务")
        return
    except Exception as e:
        logger.error(f"读取配置文件失败: {e}")
        return

    logger.info("默认定时任务已添加")
