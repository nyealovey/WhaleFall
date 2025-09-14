"""
泰摸鱼吧定时任务调度器
使用APScheduler实现轻量级定时任务
"""

import logging
import os

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler

# 配置日志
logger = logging.getLogger(__name__)


class TaskScheduler:
    """定时任务调度器"""

    def __init__(self, app=None):
        self.app = app
        self.scheduler = None
        self._setup_scheduler()

    def _setup_scheduler(self):
        """设置调度器"""
        # 任务存储配置
        jobstores = {"default": SQLAlchemyJobStore(url="sqlite:///userdata/scheduler.db")}

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

    def _job_executed(self, event):
        """任务执行成功事件"""
        logger.info(f"任务执行成功: {event.job_id} - {event.retval}")

    def _job_error(self, event):
        """任务执行错误事件"""
        logger.error(f"任务执行失败: {event.job_id} - {event.exception}")

    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("定时任务调度器已启动")

    def stop(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("定时任务调度器已停止")

    def add_job(self, func, trigger, **kwargs):
        """添加任务"""
        return self.scheduler.add_job(func, trigger, **kwargs)

    def remove_job(self, job_id):
        """删除任务"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"任务已删除: {job_id}")
        except Exception as e:
            logger.error(f"删除任务失败: {job_id} - {e}")

    def get_jobs(self):
        """获取所有任务"""
        return self.scheduler.get_jobs()

    def get_job(self, job_id):
        """获取指定任务"""
        return self.scheduler.get_job(job_id)

    def pause_job(self, job_id):
        """暂停任务"""
        self.scheduler.pause_job(job_id)
        logger.info(f"任务已暂停: {job_id}")

    def resume_job(self, job_id):
        """恢复任务"""
        self.scheduler.resume_job(job_id)
        logger.info(f"任务已恢复: {job_id}")


# 全局调度器实例
scheduler = TaskScheduler()


# 确保scheduler实例可以被正确访问
def get_scheduler():
    """获取调度器实例"""
    return scheduler.scheduler


def init_scheduler(app):
    """初始化调度器"""
    scheduler.app = app
    scheduler.start()

    # 添加默认任务
    _add_default_jobs()

    return scheduler


def _add_default_jobs():
    """添加默认任务（仅当数据库中没有任务时）"""
    import yaml

    from app.tasks import cleanup_old_logs, sync_accounts

    # 检查是否已有任务
    existing_jobs = scheduler.get_jobs()
    if existing_jobs:
        logger.info(f"发现 {len(existing_jobs)} 个现有任务，跳过创建默认任务")
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
                logger.warning(f"未知的任务函数: {function_name}")
                continue

            # 创建任务
            scheduler.add_job(
                func,
                trigger_type,
                id=task_id,
                name=task_name,
                replace_existing=True,
                **trigger_params,
            )

            logger.info(f"添加默认任务: {task_name} ({task_id})")

    except FileNotFoundError:
        logger.warning(f"配置文件不存在: {config_file}，使用硬编码默认任务")
        # 回退到硬编码方式
        _add_hardcoded_default_jobs()
    except Exception as e:
        logger.error(f"读取配置文件失败: {e}，使用硬编码默认任务")
        # 回退到硬编码方式
        _add_hardcoded_default_jobs()

    logger.info("默认定时任务已添加")


def _add_hardcoded_default_jobs():
    """添加硬编码的默认任务（备用方案）"""
    from app.tasks import cleanup_old_logs, sync_accounts

    # 清理旧日志 - 每天凌晨2点执行
    scheduler.add_job(
        cleanup_old_logs,
        "cron",
        hour=2,
        minute=0,
        id="cleanup_logs",
        name="清理旧日志",
        replace_existing=True,
    )

    # 账户同步 - 每30分钟执行
    scheduler.add_job(
        sync_accounts,
        "interval",
        minutes=30,
        id="sync_accounts",
        name="账户同步",
        replace_existing=True,
    )


# 装饰器：用于标记任务函数
def scheduled_task(job_id=None, name=None):
    """定时任务装饰器"""

    def decorator(func):
        func._is_scheduled_task = True
        func._job_id = job_id or func.__name__
        func._job_name = name or func.__name__
        return func

    return decorator
