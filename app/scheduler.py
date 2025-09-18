"""
鲸落定时任务调度器
使用APScheduler实现轻量级定时任务
"""

import os
from typing import Any

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

from app.utils.structlog_config import get_system_logger

logger = get_system_logger()


# 配置日志
class TaskScheduler:
    """定时任务调度器"""

    def __init__(self, app: Any = None) -> None:  # noqa: ANN401
        self.app = app
        self.scheduler = None
        self._setup_scheduler()

    def _setup_scheduler(self) -> None:
        """设置调度器"""
        # 任务存储配置 - 使用PostgreSQL
        from app.config import Config

        jobstores = {"default": SQLAlchemyJobStore(url=Config.SQLALCHEMY_DATABASE_URI)}

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
        """任务执行成功事件"""
        logger.info("任务执行成功: %s - %s", event.job_id, event.retval)

    def _job_error(self, event: Any) -> None:  # noqa: ANN401
        """任务执行错误事件"""
        exception_str = str(event.exception) if event.exception else "未知错误"
        logger.error("任务执行失败: %s - %s", event.job_id, exception_str)

    def start(self) -> None:
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("定时任务调度器已启动")
        else:
            logger.warning("定时任务调度器已经在运行，跳过启动")

    def stop(self) -> None:
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("定时任务调度器已停止")

    def add_job(self, func: Any, trigger: Any, **kwargs: Any) -> None:  # noqa: ANN401
        """添加任务"""
        return self.scheduler.add_job(func, trigger, **kwargs)

    def remove_job(self, job_id: str) -> None:
        """删除任务"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info("任务已删除: %s", job_id)
        except Exception as e:
            error_str = str(e) if e else "未知错误"
            logger.error("删除任务失败: %s - %s", job_id, error_str)

    def get_jobs(self) -> list:
        """获取所有任务"""
        return self.scheduler.get_jobs()

    def get_job(self, job_id: str) -> Any:  # noqa: ANN401
        """获取指定任务"""
        return self.scheduler.get_job(job_id)

    def pause_job(self, job_id: str) -> None:
        """暂停任务"""
        self.scheduler.pause_job(job_id)
        logger.info("任务已暂停: %s", job_id)

    def resume_job(self, job_id: str) -> None:
        """恢复任务"""
        self.scheduler.resume_job(job_id)
        logger.info("任务已恢复: %s", job_id)


# 全局调度器实例
scheduler = TaskScheduler()


# 确保scheduler实例可以被正确访问
def get_scheduler() -> Any:  # noqa: ANN401
    """获取调度器实例"""
    return scheduler.scheduler


def init_scheduler(app: Any) -> None:  # noqa: ANN401
    """初始化调度器"""
    # 检查是否已经初始化过
    if hasattr(scheduler, "app") and scheduler.app is not None:
        logger.warning("调度器已经初始化过，跳过重复初始化")
        return scheduler

    scheduler.app = app
    scheduler.start()

    # 从数据库加载现有任务（不自动创建默认任务）
    _load_existing_jobs()

    return scheduler


def _load_existing_jobs() -> None:
    """从数据库加载现有任务"""
    try:
        # 获取数据库中的所有任务
        existing_jobs = scheduler.get_jobs()
        if existing_jobs:
            logger.info("从数据库加载了 %d 个现有任务", len(existing_jobs))
            for job in existing_jobs:
                logger.info("加载任务: %s (%s)", job.name, job.id)
        else:
            logger.info("数据库中没有找到任务")
    except Exception as e:
        logger.error("加载现有任务失败: %s", str(e))


def _add_default_jobs() -> None:
    """添加默认任务（仅当数据库中没有任务时）"""
    import yaml

    from app.tasks import cleanup_old_logs, sync_accounts

    # 检查是否已有任务
    existing_jobs = scheduler.get_jobs()
    if existing_jobs:
        logger.info("发现 %d 个现有任务，跳过创建默认任务", len(existing_jobs))
        return

    # 从配置文件读取默认任务
    config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "scheduler_tasks.yaml")

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
            if function_name == "sync_accounts":
                func = sync_accounts
            elif function_name == "cleanup_old_logs":
                func = cleanup_old_logs
            else:
                logger.warning("未知的任务函数: %s", function_name)
                continue

            # 创建任务（不覆盖现有任务）
            try:
                scheduler.add_job(
                    func,
                    trigger_type,
                    id=task_id,
                    name=task_name,
                    **trigger_params,
                )
                logger.info("添加默认任务: %s (%s)", task_name, task_id)
            except Exception as e:
                logger.warning("任务已存在，跳过创建: %s (%s) - %s", task_name, task_id, str(e))

    except FileNotFoundError:
        logger.warning("配置文件不存在: %s，使用硬编码默认任务", config_file)
        # 回退到硬编码方式
        _add_hardcoded_default_jobs()
    except Exception as e:
        logger.error("读取配置文件失败: %s，使用硬编码默认任务", str(e))
        # 回退到硬编码方式
        _add_hardcoded_default_jobs()

    logger.info("默认定时任务已添加")


def _add_hardcoded_default_jobs() -> None:
    """添加硬编码的默认任务（备用方案）"""
    from app.tasks import cleanup_old_logs, sync_accounts

    # 清理旧日志 - 每天凌晨2点执行
    try:
        scheduler.add_job(
            cleanup_old_logs,
            "cron",
            hour=2,
            minute=0,
            id="cleanup_logs",
            name="清理旧日志",
        )
        logger.info("添加硬编码任务: 清理旧日志")
    except Exception as e:
        logger.warning("任务已存在，跳过创建: cleanup_logs - %s", str(e))

    # 账户同步 - 每30分钟执行
    try:
        scheduler.add_job(
            sync_accounts,
            "interval",
            minutes=30,
            id="sync_accounts",
            name="账户同步",
        )
        logger.info("添加硬编码任务: 账户同步")
    except Exception as e:
        logger.warning("任务已存在，跳过创建: sync_accounts - %s", str(e))


# 装饰器：用于标记任务函数
def scheduled_task(job_id: str | None = None, name: str | None = None) -> Any:  # noqa: ANN401
    """定时任务装饰器"""

    def decorator(func: Any) -> Any:  # noqa: ANN401
        func._is_scheduled_task = True  # noqa: SLF001
        func._job_id = job_id or func.__name__  # noqa: SLF001
        func._job_name = name or func.__name__  # noqa: SLF001
        return func

    return decorator
