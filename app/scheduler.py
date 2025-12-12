"""鲸落定时任务调度器.

使用 APScheduler 实现轻量级定时任务,并通过文件锁控制单实例运行.
"""

from __future__ import annotations

import atexit
import os
import time
from collections.abc import Callable
from importlib import import_module
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any

import yaml
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, JobExecutionEvent
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.base import JobLookupError
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.base import BaseTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.exc import SQLAlchemyError
from yaml import YAMLError

try:
    import fcntl  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - Windows 环境不会加载
    fcntl = None

from app.utils.structlog_config import get_system_logger

if TYPE_CHECKING:
    from apscheduler.job import Job
    from flask import Flask

logger = get_system_logger()

JobFunc = Callable[..., object]
TriggerArg = BaseTrigger | str


class _SchedulerLockState:
    """记录调度器文件锁的句柄与所属进程."""

    def __init__(self) -> None:
        self.handle: IO[str] | None = None
        self.pid: int | None = None


_LOCK_STATE = _SchedulerLockState()

LOCK_IO_EXCEPTIONS: tuple[type[BaseException], ...] = (OSError,)
JOB_REMOVAL_EXCEPTIONS: tuple[type[BaseException], ...] = (JobLookupError, LookupError)
JOBSTORE_OPERATION_EXCEPTIONS: tuple[type[BaseException], ...] = (
    SQLAlchemyError,
    JobLookupError,
    LookupError,
    RuntimeError,
)
SCHEDULER_INIT_EXCEPTIONS: tuple[type[BaseException], ...] = (
    OSError,
    SQLAlchemyError,
    RuntimeError,
    LookupError,
    ValueError,
)
DEFAULT_TASK_CREATION_EXCEPTIONS: tuple[type[BaseException], ...] = (
    ValueError,
    LookupError,
    RuntimeError,
    SQLAlchemyError,
    TypeError,
)
CONFIG_IO_EXCEPTIONS: tuple[type[BaseException], ...] = (OSError, YAMLError)
CRON_FIELDS = ("second", "minute", "hour", "day", "month", "day_of_week", "year")
TASK_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "scheduler_tasks.yaml"
TASK_FUNCTIONS: dict[str, JobFunc | str] = {
    "sync_accounts": "app.tasks.accounts_sync_tasks:sync_accounts",
    "cleanup_old_logs": "app.tasks.log_cleanup_tasks:cleanup_old_logs",
    "monitor_partition_health": "app.tasks.partition_management_tasks:monitor_partition_health",
    "collect_database_sizes": "app.tasks.capacity_collection_tasks:collect_database_sizes",
    "calculate_database_size_aggregations": "app.tasks.capacity_aggregation_tasks:calculate_database_size_aggregations",
}


def _load_task_callable(function_name: str) -> JobFunc | None:
    """按需加载任务函数,避免在导入阶段触发循环依赖."""
    target = TASK_FUNCTIONS.get(function_name)
    if callable(target):
        return target
    if isinstance(target, str):
        module_path, attr_name = target.split(":", 1)
        module = import_module(module_path)
        func = getattr(module, attr_name)
        TASK_FUNCTIONS[function_name] = func
        return func
    return None


# 配置日志
class TaskScheduler:
    """定时任务调度器."""

    def __init__(self, app: Flask | None = None) -> None:
        """初始化调度器包装类.

        Args:
            app: 可选的 Flask 应用实例,用于后续加载任务时获取上下文.

        """
        self.app = app
        self.scheduler: BackgroundScheduler = self._setup_scheduler()

    def _setup_scheduler(self) -> BackgroundScheduler:
        """配置 APScheduler 并注册事件监听.

        准备 SQLite jobstore、线程执行器与默认任务参数,随后创建后台调度器实例并
        绑定成功/失败事件,确保所有调度器行为集中在同一处完成.

        Returns:
            None: 初始化完成后立即返回.

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
            "misfire_grace_time": 300,  # 错过执行时间容忍度(秒)
        }

        # 创建调度器
        scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="Asia/Shanghai",
        )

        # 添加事件监听器
        scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)
        return scheduler

    def _job_executed(self, event: JobExecutionEvent) -> None:
        """处理任务成功事件.

        Args:
            event: APScheduler 事件对象,包含 job_id 与返回值.

        Returns:
            None: 仅记录日志.

        """
        logger.info(
            "任务执行成功",
            job_id=event.job_id,
            retval=str(event.retval),
        )

    def _job_error(self, event: JobExecutionEvent) -> None:
        """处理任务失败事件.

        Args:
            event: APScheduler 事件对象,包含异常信息.

        Returns:
            None: 仅记录错误日志.

        """
        exception_str = str(event.exception) if event.exception else "未知错误"
        logger.error(
            "任务执行失败",
            job_id=event.job_id,
            error=exception_str,
        )

    def start(self) -> None:
        """启动调度器.

        Returns:
            None: 调度器启动或确认已运行后返回.

        """
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("定时任务调度器已启动")
        else:
            logger.warning("定时任务调度器已经在运行,跳过启动")

    def stop(self) -> None:
        """停止调度器.

        Returns:
            None: 调度器关闭后返回.

        """
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("定时任务调度器已停止")

    def add_job(self, func: JobFunc, trigger: TriggerArg, **kwargs: object) -> Job:
        """向调度器注册任务.

        Args:
            func: 需要调度的可调用对象.
            trigger: APScheduler 触发器或触发器关键字参数.
            **kwargs: 传递给 `scheduler.add_job` 的其它参数,如 id/name.

        Returns:
            Job: APScheduler 新建任务对象.

        """
        return self.scheduler.add_job(func, trigger, **kwargs)

    def remove_job(self, job_id: str) -> None:
        """删除任务.

        Args:
            job_id: 任务唯一 ID.

        Returns:
            None: 删除或记录失败信息后返回.

        """
        try:
            self.scheduler.remove_job(job_id)
            logger.info("任务已删除", job_id=job_id)
        except JOB_REMOVAL_EXCEPTIONS as remove_error:
            logger.exception(
                "删除任务失败",
                job_id=job_id,
                error=str(remove_error),
            )

    def get_jobs(self) -> list[Job]:
        """列出所有任务.

        Returns:
            list: APScheduler job 列表.

        """
        return self.scheduler.get_jobs()

    def get_job(self, job_id: str) -> Job | None:
        """获取指定任务.

        Args:
            job_id: 任务 ID.

        Returns:
            Job | None: 匹配的 APScheduler 任务对象.

        """
        return self.scheduler.get_job(job_id)

    def pause_job(self, job_id: str) -> None:
        """暂停任务.

        Args:
            job_id: 任务 ID.

        Returns:
            None: 任务被暂停后返回.

        """
        self.scheduler.pause_job(job_id)
        logger.info("任务已暂停", job_id=job_id)

    def resume_job(self, job_id: str) -> None:
        """恢复任务.

        Args:
            job_id: 任务 ID.

        Returns:
            None: 任务被恢复后返回.

        """
        self.scheduler.resume_job(job_id)
        logger.info("任务已恢复", job_id=job_id)


# 全局调度器实例
scheduler = TaskScheduler()


# 确保scheduler实例可以被正确访问
def get_scheduler() -> BackgroundScheduler | None:
    """获取底层 APScheduler 实例.

    Returns:
        BackgroundScheduler | None: 正在运行的调度器对象.

    """
    return scheduler.scheduler


def _acquire_scheduler_lock() -> bool:
    """尝试获取文件锁,确保单进程运行调度器.

    Returns:
        bool: 成功获取锁返回 True,否则返回 False.

    """
    if fcntl is None:
        logger.warning("当前平台不支持fcntl,无法加文件锁,可能存在多个调度器实例并发运行")
        return True

    current_pid = os.getpid()

    if _LOCK_STATE.handle:
        if _LOCK_STATE.pid == current_pid:
            return True
        # 子进程继承了锁句柄,但并未真正持有锁,需要重新获取
        try:  # pragma: no cover - 防御性释放
            _LOCK_STATE.handle.close()
        except LOCK_IO_EXCEPTIONS as close_error:
            logger.warning("继承的调度器锁句柄关闭失败", error=str(close_error))
        _LOCK_STATE.handle = None
        _LOCK_STATE.pid = None

    if _LOCK_STATE.handle:
        return True

    lock_path = Path("userdata") / "scheduler.lock"
    lock_path.parent.mkdir(exist_ok=True)
    handle = lock_path.open("w+")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        logger.info("检测到其他进程正在运行调度器,跳过当前进程的调度器初始化")
        return False
    except LOCK_IO_EXCEPTIONS as lock_error:  # pragma: no cover - 极端情况
        handle.close()
        logger.exception("获取调度器锁失败", error=str(lock_error))
        return False
    else:
        handle.write(str(os.getpid()))
        handle.flush()
        _LOCK_STATE.handle = handle
        _LOCK_STATE.pid = current_pid
        logger.info("调度器锁已获取,当前进程负责运行定时任务", pid=os.getpid())
        return True


def _release_scheduler_lock() -> None:
    """释放调度器文件锁并清理句柄.

    Returns:
        None: 锁释放或无需释放时直接返回.

    """
    if fcntl is None or not _LOCK_STATE.handle:
        return
    try:  # pragma: no cover
        fcntl.flock(_LOCK_STATE.handle, fcntl.LOCK_UN)
    except LOCK_IO_EXCEPTIONS as unlock_error:
        logger.warning("释放调度器文件锁失败", error=str(unlock_error))
    try:  # pragma: no cover
        _LOCK_STATE.handle.close()
    except LOCK_IO_EXCEPTIONS as close_error:
        logger.warning("关闭调度器锁文件失败", error=str(close_error))
    finally:
        _LOCK_STATE.handle = None
        _LOCK_STATE.pid = None


atexit.register(_release_scheduler_lock)


def _should_start_scheduler() -> bool:
    """根据环境变量及进程角色判断是否需启动调度器.

    Returns:
        bool: True 表示可以启动,False 表示跳过.

    """
    enable_flag = os.environ.get("ENABLE_SCHEDULER", "true").strip().lower()
    if enable_flag not in ("true", "1", "yes"):
        logger.info(
            "检测到调度器禁用标记,跳过初始化",
            env_flag=enable_flag,
        )
        return False

    server_software = os.environ.get("SERVER_SOFTWARE", "")
    if server_software.startswith("gunicorn"):
        logger.info(
            "检测到 gunicorn 环境,通过文件锁保持单实例",
            parent_pid=os.getppid(),
        )

    # Flask reloader: 只有子进程 (WERKZEUG_RUN_MAIN=true) 才运行调度器
    if os.environ.get("FLASK_RUN_FROM_CLI") == "true":
        reloader_flag = os.environ.get("WERKZEUG_RUN_MAIN")
        if reloader_flag not in ("true", "1"):
            logger.info("检测到 Flask reloader 父进程,跳过调度器初始化")
            return False

    return True


def init_scheduler(app: Flask) -> TaskScheduler | None:
    """初始化调度器(仅在允许的进程中启动).

    Args:
        app: Flask 应用实例,用于任务上下文.

    Returns:
        TaskScheduler | None: 初始化成功时返回 TaskScheduler,否则返回 None.

    """
    if not _should_start_scheduler():
        return None

    if not _acquire_scheduler_lock():
        return None

    if scheduler.app is not None:
        logger.warning("调度器已经初始化过,跳过重复初始化")
        return scheduler

    try:
        scheduler.app = app

        sqlite_path = Path("userdata/scheduler.db")
        if not sqlite_path.exists():
            logger.info("创建SQLite调度器数据库文件")
            sqlite_path.parent.mkdir(exist_ok=True)
            sqlite_path.touch()

        scheduler.start()
        time.sleep(2)
        _load_existing_jobs()
        _add_default_jobs()
    except SCHEDULER_INIT_EXCEPTIONS as init_error:
        logger.exception("调度器初始化失败", error=str(init_error))
        return None
    else:
        logger.info("调度器初始化完成")
        return scheduler


def _load_existing_jobs() -> None:
    """从 SQLite jobstore 恢复既有任务.

    Returns:
        None: 任务加载结束或被跳过后返回.

    """
    try:
        # 检查调度器是否已启动
        if not scheduler.scheduler or not scheduler.scheduler.running:
            logger.warning("调度器未启动,跳过加载现有任务")
            return

        # 检查调度器是否完全就绪
        if not hasattr(scheduler.scheduler, "_jobstores_lock"):
            logger.warning("调度器未完全就绪,跳过加载现有任务")
            return

        # 检查SQLite数据库文件是否存在
        sqlite_path = Path("userdata/scheduler.db")
        if not sqlite_path.exists():
            logger.warning("SQLite数据库文件不存在,跳过加载现有任务")
            return

        # 使用try-except包装get_jobs调用,避免KeyboardInterrupt
        try:
            existing_jobs = scheduler.get_jobs()
            if existing_jobs:
                logger.info(
                    "从SQLite数据库加载既有任务完成",
                    job_count=len(existing_jobs),
                )
                for job in existing_jobs:
                    logger.info(
                        "加载任务配置",
                        job_name=job.name,
                        job_id=job.id,
                    )
            else:
                logger.info("SQLite数据库中没有找到任务")
        except KeyboardInterrupt:
            logger.warning("加载任务时被中断,跳过加载现有任务")
            return
        except JOBSTORE_OPERATION_EXCEPTIONS as load_error:
            logger.exception("获取任务列表失败", error=str(load_error))
            return
    except SCHEDULER_INIT_EXCEPTIONS as load_error:
        logger.exception("加载现有任务失败", error=str(load_error))
        # 不抛出异常,让应用继续启动


def _add_default_jobs() -> None:
    """在 jobstore 为空时添加默认任务.

    Returns:
        None: 调用 `_load_tasks_from_config` 后返回.

    """
    _load_tasks_from_config(force=False)


def _reload_all_jobs() -> None:
    """强制重新加载全部任务配置.

    Returns:
        None: 触发 `_load_tasks_from_config` 后返回.

    """
    _load_tasks_from_config(force=True)


def _load_tasks_from_config(*, force: bool = False) -> None:
    """从配置文件加载默认任务并注册."""
    if not force and _should_skip_default_task_creation():
        return

    try:
        task_configs = _read_default_task_configs()
    except FileNotFoundError:
        logger.exception("配置文件不存在,无法加载默认任务", config_file=str(TASK_CONFIG_PATH))
        return
    except CONFIG_IO_EXCEPTIONS as config_error:
        logger.exception("读取配置文件失败", config_file=str(TASK_CONFIG_PATH), error=str(config_error))
        return

    for task_config in task_configs:
        _register_task_from_config(task_config, force=force)

    logger.info("默认定时任务已添加")


def _should_skip_default_task_creation() -> bool:
    """是否需要跳过默认任务创建."""
    try:
        existing_jobs = scheduler.get_jobs()
    except KeyboardInterrupt:
        logger.warning("检查现有任务时被中断,跳过创建默认任务")
        return True
    except JOBSTORE_OPERATION_EXCEPTIONS as query_error:
        logger.exception("检查现有任务失败", error=str(query_error))
        return True

    if existing_jobs:
        logger.info("发现现有任务,跳过默认任务创建", job_count=len(existing_jobs))
        return True
    return False


def _read_default_task_configs() -> list[dict[str, Any]]:
    """读取调度任务配置."""
    with TASK_CONFIG_PATH.open(encoding="utf-8") as config_buffer:
        config = yaml.safe_load(config_buffer) or {}
    return config.get("default_tasks", [])


def _register_task_from_config(task_config: dict[str, Any], *, force: bool) -> None:
    """根据配置注册单个任务."""
    if not task_config.get("enabled", True):
        return

    task_id = task_config["id"]
    task_name = task_config["name"]
    function_name = task_config["function"]
    trigger_type = task_config["trigger_type"]
    trigger_params = task_config.get("trigger_params", {})

    func = _load_task_callable(function_name)
    if not func:
        logger.warning("未知的任务函数", function_name=function_name)
        return

    if force:
        _remove_existing_job(task_id, task_name)

    try:
        _schedule_job(func, task_id, task_name, trigger_type, trigger_params)
        logger.info("添加调度任务", task_name=task_name, task_id=task_id)
    except DEFAULT_TASK_CREATION_EXCEPTIONS as error:
        _log_task_creation_failure(
            error,
            force=force,
            task_id=task_id,
            task_name=task_name,
        )


def _remove_existing_job(task_id: str, task_name: str) -> None:
    """在强制模式下删除已存在的任务."""
    try:
        scheduler.remove_job(task_id)
        logger.info("强制模式删除现有任务", task_name=task_name, task_id=task_id)
    except JOB_REMOVAL_EXCEPTIONS as remove_error:
        logger.warning(
            "强制模式-删除现有任务失败",
            task_name=task_name,
            task_id=task_id,
            error=str(remove_error),
        )


def _schedule_job(
    func: JobFunc,
    task_id: str,
    task_name: str,
    trigger_type: str,
    trigger_params: dict[str, Any],
) -> None:
    """将任务注册到调度器."""
    if trigger_type == "cron":
        trigger = _build_cron_trigger(trigger_params)
        scheduler.add_job(func, trigger, id=task_id, name=task_name)
        return
    scheduler.add_job(func, trigger_type, id=task_id, name=task_name, **trigger_params)


def _build_cron_trigger(trigger_params: dict[str, Any]) -> CronTrigger:
    """构建 CronTrigger,避免 APScheduler 自动填充默认值."""
    cron_kwargs = {field: trigger_params[field] for field in CRON_FIELDS if field in trigger_params}
    cron_kwargs["timezone"] = "Asia/Shanghai"
    return CronTrigger(**cron_kwargs)


def _log_task_creation_failure(
    error: BaseException,
    *,
    force: bool,
    task_id: str,
    task_name: str,
) -> None:
    """记录任务创建失败的日志."""
    log_method = logger.exception if force else logger.warning
    log_method(
        "创建调度任务失败" if force else "任务已存在,跳过创建",
        task_name=task_name,
        task_id=task_id,
        error=str(error),
    )
