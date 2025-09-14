"""
泰摸鱼吧 - 任务执行引擎
负责执行各种类型的同步任务
"""

from datetime import datetime

from app import db

# 移除SyncData导入，使用新的同步会话模型
from app.models.task import Task
from app.utils.structlog_config import get_task_logger
from app.utils.timezone import now


class TaskExecutor:
    """任务执行器"""

    def __init__(self) -> None:
        self.task_logger = get_task_logger()

    def execute_task(self, task_id: int, timeout: int = 300) -> dict:
        """
        执行指定任务

        Args:
            task_id: 任务ID
            timeout: 执行超时时间（秒）

        Returns:
            dict: 执行结果
        """
        from app import create_app

        # 创建应用上下文
        app = create_app()
        with app.app_context():
            import threading

            task = Task.query.get(task_id)
            if not task:
                return {"success": False, "error": f"任务 {task_id} 不存在"}

            if not task.is_active:
                return {"success": False, "error": f"任务 {task.name} 已禁用"}

            # 获取匹配的实例
            instances = task.get_matching_instances()
            if not instances:
                return {
                    "success": False,
                    "error": f"没有找到匹配的 {task.db_type} 类型实例",
                }

            self.task_logger.info(
                "开始执行任务",
                task_name=task.name,
                instance_count=len(instances),
                timeout=timeout,
            )

            # 使用超时机制执行任务
            result = {"success": False, "error": "任务执行超时"}

            def run_task() -> None:
                nonlocal result
                try:
                    total_success = 0
                    total_failed = 0
                    results = []

                    # 逐一执行实例
                    for instance in instances:
                        try:
                            instance_result = self._execute_task_for_instance(task, instance)
                            if instance_result["success"]:
                                total_success += 1
                            else:
                                total_failed += 1

                            results.append(
                                {
                                    "instance_name": instance.name,
                                    "result": instance_result,
                                }
                            )

                            # 记录同步数据
                            self._record_sync_data(task, instance, instance_result)

                        except Exception as e:
                            self.task_logger.error(
                                "执行任务在实例时出错",
                                task_name=task.name,
                                instance_name=instance.name,
                                exception=e,
                            )
                            total_failed += 1
                            results.append(
                                {
                                    "instance_name": instance.name,
                                    "result": {"success": False, "error": str(e)},
                                }
                            )

                    result = {
                        "success": total_failed == 0,
                        "message": f"任务执行完成，成功: {total_success}, 失败: {total_failed}",
                        "total_success": total_success,
                        "total_failed": total_failed,
                        "results": results,
                    }
                except Exception as e:
                    self.task_logger.error("任务执行失败", task_name=task.name, exception=e)
                    result = {"success": False, "error": str(e)}

            # 使用线程执行任务，支持超时

            thread = threading.Thread(target=run_task)
            thread.daemon = True
            thread.start()
            thread.join(timeout=timeout)

            if thread.is_alive():
                self.task_logger.warning("任务执行超时", task_name=task.name, timeout=timeout)
                return {"success": False, "error": f"任务执行超时 ({timeout}秒)"}

            # 更新任务状态 - 重新查询任务对象确保是最新的
            task = Task.query.get(task_id)
            if result["success"]:
                self._update_task_status(
                    task,
                    result["total_success"],
                    result["total_failed"],
                    result["results"],
                )
                # 记录任务执行汇总
                self._record_task_execution_summary(
                    task,
                    result["total_success"],
                    result["total_failed"],
                    result["results"],
                )
            else:
                self._update_task_status(task, 0, 1, [{"instance_name": "unknown", "result": result}])
                # 记录任务执行汇总（失败情况）
                self._record_task_execution_summary(
                    task,
                    0,
                    1,
                    [{"success": False, "error": result.get("error", "未知错误")}],
                )

            return result

    def _execute_task_for_instance(self, task: "Any", instance: "Any") -> dict:
        """
        为指定实例执行任务

        Args:
            task: 任务对象
            instance: 实例对象

        Returns:
            dict: 执行结果
        """
        from app import create_app

        # 创建应用上下文
        app = create_app()
        with app.app_context():
            try:
                # 对于账户同步任务，使用统一的账户同步服务
                if task.task_type == "sync_accounts":
                    from app.services.account_sync_service import account_sync_service

                    # 执行账户同步（同步时自动清理多余账户）
                    result = account_sync_service.sync_accounts(instance, sync_type="task")
                    return result

                # 对于数据库大小同步任务，使用数据库大小同步服务
                if task.task_type == "sync_size":
                    from app.services.database_size_service import database_size_service

                    result = database_size_service.sync_database_size(instance, sync_type="task")
                    return result

                # 对于其他任务类型，使用原有的动态执行方式
                # 创建执行环境
                exec_globals = {
                    "instance": instance,
                    "config": task.config or {},
                    "datetime": datetime,
                    "logging": logging,
                }

                # 执行Python代码
                exec(task.python_code, exec_globals)

                # 获取执行函数
                if task.task_type == "sync_version":
                    func_name = f"sync_{task.db_type}_version"
                elif task.task_type == "sync_size":
                    func_name = f"sync_{task.db_type}_size"
                else:
                    func_name = f"sync_{task.db_type}_{task.task_type}"

                if func_name not in exec_globals:
                    return {"success": False, "error": f"未找到执行函数: {func_name}"}

                # 调用执行函数
                sync_func = exec_globals[func_name]
                result = sync_func(instance, task.config or {})

                return result

            except Exception as e:
                self.logger.error(f"执行任务代码时出错: {e}")
                return {"success": False, "error": f"执行任务代码失败: {str(e)}"}

    def _record_task_execution_summary(self, task: "Any", success_count: int, failed_count: int, results: list) -> None:
        """
        记录任务执行汇总数据

        Args:
            task: 任务对象
            success_count: 成功实例数
            failed_count: 失败实例数
            results: 执行结果列表
        """
        from app import create_app

        # 创建应用上下文
        app = create_app()
        with app.app_context():
            try:
                # 计算汇总数据
                total_synced = sum(r.get("synced_count", 0) for r in results if r.get("success", False))
                total_added = sum(r.get("added_count", 0) for r in results if r.get("success", False))
                total_removed = sum(r.get("removed_count", 0) for r in results if r.get("success", False))
                total_modified = sum(r.get("modified_count", 0) for r in results if r.get("success", False))

                # 构建汇总消息
                if failed_count == 0:
                    status = "success"
                    message = f"任务执行完成，成功:{success_count}，失败:{failed_count}"
                else:
                    status = "failed"
                    message = f"任务执行完成，成功:{success_count}，失败:{failed_count}"

                # 同步会话记录已通过sync_session_service管理，无需额外创建记录

                self.logger.info(f"记录任务执行汇总: {task.name}, 成功:{success_count}, 失败:{failed_count}")
            except Exception as e:
                self.logger.error(f"记录任务执行汇总失败: {e}")

    def _update_task_status(self, task: "Any", success_count: int, failed_count: int, results: list) -> None:
        """
        更新任务状态

        Args:
            task: 任务对象
            success_count: 成功次数
            failed_count: 失败次数
            results: 执行结果列表
        """
        try:
            self.logger.info(f"更新任务状态: {task.name}, 成功: {success_count}, 失败: {failed_count}")

            task.run_count += 1
            if failed_count == 0:
                task.success_count += 1
                task.last_status = "success"
                task.last_message = f"成功执行，处理了 {success_count} 个实例"
            else:
                task.last_status = "failed"
                task.last_message = f"执行失败，成功: {success_count}, 失败: {failed_count}"

            task.last_run = now()
            task.last_run_at = now()  # 兼容字段

            db.session.commit()
            self.logger.info(f"任务状态更新完成: 运行次数={task.run_count}, 成功次数={task.success_count}")
        except Exception as e:
            self.logger.error(f"更新任务状态失败: {e}")
            db.session.rollback()

    def execute_all_active_tasks(self) -> dict:
        """
        执行所有活跃任务

        Returns:
            dict: 执行结果
        """
        tasks = Task.get_active_tasks()
        if not tasks:
            return {
                "success": True,
                "message": "没有活跃任务需要执行",
                "executed_count": 0,
            }

        executed_count = 0
        results = []

        for task in tasks:
            try:
                result = self.execute_task(task.id)
                results.append({"task_name": task.name, "result": result})
                executed_count += 1
            except Exception as e:
                self.logger.error(f"执行任务 {task.name} 时出错: {e}")
                results.append(
                    {
                        "task_name": task.name,
                        "result": {"success": False, "error": str(e)},
                    }
                )

        return {
            "success": True,
            "message": f"批量执行完成，处理了 {executed_count} 个任务",
            "executed_count": executed_count,
            "results": results,
        }

    def create_builtin_tasks(self) -> None:
        """
        创建内置任务

        Returns:
            dict: 创建结果
        """
        from app.templates.tasks.builtin_tasks import BUILTIN_TASKS

        created_count = 0
        skipped_count = 0

        for task_config in BUILTIN_TASKS:
            try:
                # 检查任务是否已存在
                existing_task = Task.query.filter_by(name=task_config["name"]).first()

                if existing_task:
                    skipped_count += 1
                    continue

                # 创建新任务
                task = Task(
                    name=task_config["name"],
                    task_type=task_config["task_type"],
                    db_type=task_config["db_type"],
                    description=task_config["description"],
                    python_code=task_config["python_code"],
                    config=task_config["config"],
                    schedule=task_config["schedule"],
                    is_builtin=True,
                    is_active=True,
                )

                db.session.add(task)
                created_count += 1

            except Exception as e:
                self.logger.error(f"创建内置任务 {task_config['name']} 失败: {e}")

        try:
            db.session.commit()
            return {
                "success": True,
                "message": f"内置任务创建完成，新增: {created_count}, 跳过: {skipped_count}",
                "created_count": created_count,
                "skipped_count": skipped_count,
            }
        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": f"创建内置任务失败: {str(e)}"}
