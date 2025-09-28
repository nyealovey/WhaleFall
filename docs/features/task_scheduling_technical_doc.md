# 任务调度功能技术文档

## 功能概述

任务调度功能是鲸落系统中的核心基础设施模块，负责管理和执行各种定时任务。该功能基于APScheduler（Advanced Python Scheduler）实现，提供轻量级、高可靠性的任务调度能力，支持任务的创建、编辑、删除、暂停、恢复和监控等操作。

## 技术架构

### 调度器架构

#### APScheduler组件
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Job Stores    │    │   Executors     │    │   Schedulers    │
│                 │    │                 │    │                 │
│ SQLAlchemy      │◄──►│ ThreadPool      │◄──►│ Background      │
│ (SQLite)        │    │ (5 workers)     │    │ Scheduler       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Task Management                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Events    │  │   Triggers  │  │   Jobs      │            │
│  │             │  │             │  │             │            │
│  │ Executed    │  │ Cron        │  │ Functions   │            │
│  │ Error       │  │ Interval    │  │ Metadata    │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

#### 核心组件说明
- **Job Stores**: 任务持久化存储，使用SQLite数据库
- **Executors**: 任务执行器，使用线程池执行任务
- **Schedulers**: 调度器核心，管理任务生命周期
- **Events**: 事件监听，记录任务执行状态
- **Triggers**: 触发器，定义任务执行时间
- **Jobs**: 任务实体，包含执行函数和元数据

### 前端架构

#### 主要页面
- **任务管理页面** (`/scheduler/`)：任务列表、状态监控、操作控制
- **任务编辑页面**：任务配置、触发器设置、代码编辑

#### JavaScript文件
```
app/static/js/
├── pages/scheduler/
│   └── management.js               # 任务管理页面逻辑
└── components/
    ├── cron_editor.js              # Cron表达式编辑器
    └── task_monitor.js             # 任务监控组件
```

#### CSS样式文件
```
app/static/css/
├── pages/scheduler/
│   └── management.css              # 任务管理页面样式
└── components/
    └── task_card.css               # 任务卡片样式
```

### 后端架构

#### 路由定义
```python
# app/routes/scheduler.py
@scheduler_bp.route("/")                              # 任务管理首页
@scheduler_bp.route("/api/jobs")                      # 获取任务列表API
@scheduler_bp.route("/api/jobs", methods=["POST"])    # 创建任务API
@scheduler_bp.route("/api/jobs/<job_id>")             # 获取任务详情API
@scheduler_bp.route("/api/jobs/<job_id>", methods=["PUT"])    # 更新任务API
@scheduler_bp.route("/api/jobs/<job_id>", methods=["DELETE"]) # 删除任务API
@scheduler_bp.route("/api/jobs/<job_id>/pause")       # 暂停任务API
@scheduler_bp.route("/api/jobs/<job_id>/resume")      # 恢复任务API
@scheduler_bp.route("/api/jobs/<job_id>/run")         # 立即执行任务API
```

#### 调度器核心类
```python
# app/scheduler.py
class TaskScheduler:
    """定时任务调度器"""
    
    def __init__(self, app=None):
        self.app = app
        self.scheduler = None
        self._setup_scheduler()
    
    def _setup_scheduler(self):
        """设置调度器"""
        # 任务存储配置 - 使用本地SQLite
        userdata_dir = Path("userdata")
        userdata_dir.mkdir(exist_ok=True)
        
        sqlite_path = userdata_dir / "scheduler.db"
        database_url = f"sqlite:///{sqlite_path.absolute()}"
        
        jobstores = {"default": SQLAlchemyJobStore(url=database_url)}
        
        # 执行器配置
        executors = {"default": ThreadPoolExecutor(max_workers=5)}
        
        # 任务默认配置
        job_defaults = {
            "coalesce": True,           # 合并相同任务
            "max_instances": 1,         # 最大实例数
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
        logger.info("任务执行成功: %s - %s", event.job_id, event.retval)
    
    def _job_error(self, event):
        """任务执行错误事件"""
        exception_str = str(event.exception) if event.exception else "未知错误"
        logger.error("任务执行失败: %s - %s", event.job_id, exception_str)
```

#### 任务配置文件
```yaml
# app/config/scheduler_tasks.yaml
default_tasks:
  - id: sync_accounts
    name: 账户同步
    function: sync_accounts
    trigger_type: cron
    trigger_params:
      hour: 1
      minute: 0
    enabled: true
    description: 每日同步所有数据库实例的账户信息
    
  - id: collect_database_sizes
    name: 容量同步
    function: collect_database_sizes
    trigger_type: cron
    trigger_params:
      hour: 3
      minute: 0
    enabled: true
    description: 每日同步所有数据库实例的容量信息
    
  - id: calculate_database_size_aggregations
    name: 计算统计聚合
    function: calculate_database_size_aggregations
    trigger_type: cron
    trigger_params:
      hour: 4
      minute: 0
    enabled: true
    description: 每日计算数据库大小的日、周、月、季度统计聚合
```

#### 任务模块组织
```python
# app/tasks/__init__.py
__all__ = [
    # 现有任务
    'cleanup_old_logs',
    'sync_accounts',
    
    # 数据库大小采集任务
    'collect_database_sizes',
    'collect_specific_instance_database_sizes',
    'collect_database_sizes_by_type',
    'get_collection_status',
    'validate_collection_config',
    
    # 数据库大小聚合任务
    'calculate_database_size_aggregations',
    'calculate_instance_aggregations',
    'calculate_period_aggregations',
    'get_aggregation_status',
    'validate_aggregation_config',
    'cleanup_old_aggregations',
    
    # 分区管理任务
    'create_database_size_partitions',
    'cleanup_database_size_partitions',
    'monitor_partition_health',
    'get_partition_management_status'
]
```

## 核心功能实现

### 1. 调度器初始化

#### 调度器启动
```python
# app/scheduler.py
def init_scheduler(app):
    """初始化调度器"""
    global scheduler
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
        logger.error("调度器初始化失败: %s", str(e))
        return None
```

#### 默认任务加载
```python
# app/scheduler.py
def _add_default_jobs(force=False):
    """添加默认任务"""
    try:
        # 检查是否需要跳过
        if not force:
            try:
                existing_jobs = scheduler.get_jobs()
                if existing_jobs:
                    logger.info("发现 %d 个现有任务，跳过创建默认任务", len(existing_jobs))
                    return
            except Exception as e:
                logger.warning("检查现有任务时出错: %s", str(e))
        
        # 读取配置文件
        config_path = Path("app/config/scheduler_tasks.yaml")
        if not config_path.exists():
            logger.warning("任务配置文件不存在: %s", config_path)
            return
        
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        default_tasks = config.get('default_tasks', [])
        logger.info("从配置文件加载 %d 个默认任务", len(default_tasks))
        
        # 添加任务
        for task_config in default_tasks:
            try:
                _add_task_from_config(task_config)
            except Exception as e:
                logger.error("添加任务失败 %s: %s", task_config.get('id', 'unknown'), str(e))
                continue
        
        logger.info("默认任务添加完成")
        
    except Exception as e:
        logger.error("添加默认任务失败: %s", str(e))

def _add_task_from_config(task_config):
    """从配置添加任务"""
    task_id = task_config['id']
    function_name = task_config['function']
    
    # 检查任务是否已存在
    existing_job = scheduler.get_job(task_id)
    if existing_job:
        logger.info("任务已存在，跳过: %s", task_id)
        return
    
    # 动态导入任务函数
    try:
        from app.tasks import *
        task_function = globals().get(function_name)
        if not task_function:
            logger.error("任务函数不存在: %s", function_name)
            return
    except ImportError as e:
        logger.error("导入任务函数失败 %s: %s", function_name, str(e))
        return
    
    # 构建触发器
    trigger_type = task_config.get('trigger_type', 'cron')
    trigger_params = task_config.get('trigger_params', {})
    
    if trigger_type == 'cron':
        from apscheduler.triggers.cron import CronTrigger
        trigger = CronTrigger(**trigger_params)
    else:
        logger.error("不支持的触发器类型: %s", trigger_type)
        return
    
    # 添加任务
    scheduler.add_job(
        func=task_function,
        trigger=trigger,
        id=task_id,
        name=task_config.get('name', task_id),
        misfire_grace_time=task_config.get('misfire_grace_time', 300),
        max_instances=task_config.get('max_instances', 1)
    )
    
    logger.info("任务添加成功: %s (%s)", task_id, task_config.get('name', task_id))
```

### 2. 任务管理

#### 任务列表获取
```python
# app/routes/scheduler.py
@scheduler_bp.route("/api/jobs")
@login_required
@scheduler_view_required
def get_jobs():
    """获取所有任务"""
    try:
        scheduler = get_scheduler()
        if not scheduler:
            return APIResponse.error("调度器未启动", code=500)
        
        jobs = scheduler.get_jobs()
        jobs_data = []
        
        for job in jobs:
            # 获取下次执行时间
            next_run_time = None
            if job.next_run_time:
                next_run_time = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # 构建任务数据
            job_data = {
                'id': job.id,
                'name': job.name,
                'func_name': job.func.__name__ if hasattr(job.func, '__name__') else str(job.func),
                'trigger': str(job.trigger),
                'next_run_time': next_run_time,
                'misfire_grace_time': job.misfire_grace_time,
                'max_instances': job.max_instances,
                'coalesce': job.coalesce,
                'args': job.args,
                'kwargs': job.kwargs
            }
            jobs_data.append(job_data)
        
        return APIResponse.success({
            'jobs': jobs_data,
            'total': len(jobs_data)
        })
        
    except Exception as e:
        return APIResponse.error(f"获取任务列表失败: {str(e)}")
```

#### 任务创建
```python
# app/routes/scheduler.py
@scheduler_bp.route("/api/jobs", methods=["POST"])
@login_required
@scheduler_manage_required
def create_job():
    """创建新的定时任务"""
    try:
        data = request.get_json()
        
        # 验证必需字段
        required_fields = ["id", "name", "code", "trigger_type"]
        for field in required_fields:
            if field not in data:
                return APIResponse.error(f"缺少必需字段: {field}", code=400)
        
        # 构建触发器
        trigger = _build_trigger(data)
        if not trigger:
            return APIResponse.error("无效的触发器配置", code=400)
        
        # 验证代码格式
        code = data["code"].strip()
        if not code:
            return APIResponse.error("任务代码不能为空", code=400)
        
        # 检查代码是否包含execute_task函数
        if "def execute_task():" not in code:
            return APIResponse.error("代码必须包含 'def execute_task():' 函数", code=400)
        
        # 创建动态任务函数
        task_func = _create_dynamic_task_function(data["id"], code)
        if not task_func:
            return APIResponse.error("代码格式错误，请检查语法", code=400)
        
        # 添加任务
        scheduler = get_scheduler()
        if not scheduler.running:
            return APIResponse.error("调度器未启动", code=500)
        
        job = scheduler.add_job(
            func=task_func,
            trigger=trigger,
            id=data["id"],
            name=data["name"],
            args=[],
            kwargs={},
        )
        
        return APIResponse.success({
            "message": "任务创建成功",
            "job_id": job.id
        })
        
    except Exception as e:
        return APIResponse.error(f"创建任务失败: {str(e)}")

def _build_trigger(data):
    """构建触发器"""
    trigger_type = data.get("trigger_type", "cron")
    
    if trigger_type == "cron":
        from apscheduler.triggers.cron import CronTrigger
        
        # 从数据中提取cron参数
        cron_params = {}
        for field in ['second', 'minute', 'hour', 'day', 'month', 'day_of_week', 'year']:
            value = data.get(f"cron_{field}")
            if value is not None and value != "":
                cron_params[field] = value
        
        return CronTrigger(**cron_params)
    
    elif trigger_type == "interval":
        from apscheduler.triggers.interval import IntervalTrigger
        
        interval_params = {}
        for field in ['weeks', 'days', 'hours', 'minutes', 'seconds']:
            value = data.get(f"interval_{field}")
            if value is not None and value != "":
                interval_params[field] = int(value)
        
        return IntervalTrigger(**interval_params)
    
    return None

def _create_dynamic_task_function(job_id, code):
    """创建动态任务函数"""
    try:
        # 创建一个新的命名空间
        namespace = {
            '__builtins__': __builtins__,
            'logger': get_system_logger(),
        }
        
        # 执行用户代码
        exec(code, namespace)
        
        # 获取execute_task函数
        if 'execute_task' not in namespace:
            return None
        
        execute_task = namespace['execute_task']
        
        # 创建包装函数
        def wrapped_task():
            try:
                result = execute_task()
                logger.info("动态任务执行成功: %s", job_id)
                return result
            except Exception as e:
                logger.error("动态任务执行失败: %s - %s", job_id, str(e))
                raise
        
        wrapped_task.__name__ = f"dynamic_task_{job_id}"
        return wrapped_task
        
    except Exception as e:
        logger.error("创建动态任务函数失败: %s", str(e))
        return None
```

#### 任务控制操作
```python
# app/routes/scheduler.py
@scheduler_bp.route("/api/jobs/<job_id>/pause", methods=["POST"])
@login_required
@scheduler_manage_required
def pause_job(job_id: str):
    """暂停任务"""
    try:
        scheduler = get_scheduler()
        if not scheduler:
            return APIResponse.error("调度器未启动", code=500)
        
        job = scheduler.get_job(job_id)
        if not job:
            return APIResponse.error("任务不存在", code=404)
        
        scheduler.pause_job(job_id)
        
        log_info(
            "任务已暂停",
            module="scheduler",
            job_id=job_id,
            user_id=current_user.id
        )
        
        return APIResponse.success({"message": "任务已暂停"})
        
    except Exception as e:
        return APIResponse.error(f"暂停任务失败: {str(e)}")

@scheduler_bp.route("/api/jobs/<job_id>/resume", methods=["POST"])
@login_required
@scheduler_manage_required
def resume_job(job_id: str):
    """恢复任务"""
    try:
        scheduler = get_scheduler()
        if not scheduler:
            return APIResponse.error("调度器未启动", code=500)
        
        job = scheduler.get_job(job_id)
        if not job:
            return APIResponse.error("任务不存在", code=404)
        
        scheduler.resume_job(job_id)
        
        log_info(
            "任务已恢复",
            module="scheduler",
            job_id=job_id,
            user_id=current_user.id
        )
        
        return APIResponse.success({"message": "任务已恢复"})
        
    except Exception as e:
        return APIResponse.error(f"恢复任务失败: {str(e)}")

@scheduler_bp.route("/api/jobs/<job_id>/run", methods=["POST"])
@login_required
@scheduler_manage_required
def run_job_now(job_id: str):
    """立即执行任务"""
    try:
        scheduler = get_scheduler()
        if not scheduler:
            return APIResponse.error("调度器未启动", code=500)
        
        job = scheduler.get_job(job_id)
        if not job:
            return APIResponse.error("任务不存在", code=404)
        
        # 立即执行任务
        job.func()
        
        log_info(
            "任务立即执行",
            module="scheduler",
            job_id=job_id,
            user_id=current_user.id
        )
        
        return APIResponse.success({"message": "任务已立即执行"})
        
    except Exception as e:
        return APIResponse.error(f"执行任务失败: {str(e)}")
```

### 3. 任务定义

#### 基础任务示例
```python
# app/tasks/legacy_tasks.py
def sync_accounts():
    """同步账户任务"""
    try:
        from app.services.account_sync_service import AccountSyncService
        from app.models.instance import Instance
        
        logger = get_system_logger()
        logger.info("开始执行账户同步任务")
        
        # 获取所有活跃实例
        instances = Instance.query.filter_by(is_active=True).all()
        
        sync_service = AccountSyncService()
        total_synced = 0
        
        for instance in instances:
            try:
                result = sync_service.sync_accounts(
                    instance=instance,
                    sync_type="scheduled_task"
                )
                
                if result.get('success'):
                    total_synced += result.get('accounts_synced', 0)
                    logger.info(
                        "实例账户同步成功: %s",
                        instance.name,
                        accounts_synced=result.get('accounts_synced', 0)
                    )
                else:
                    logger.error(
                        "实例账户同步失败: %s - %s",
                        instance.name,
                        result.get('error', '未知错误')
                    )
            except Exception as e:
                logger.error(
                    "实例账户同步异常: %s - %s",
                    instance.name,
                    str(e)
                )
                continue
        
        logger.info("账户同步任务完成，总计同步: %d 个账户", total_synced)
        return f"同步完成，总计: {total_synced} 个账户"
        
    except Exception as e:
        logger.error("账户同步任务失败: %s", str(e))
        raise

def cleanup_old_logs():
    """清理旧日志任务"""
    try:
        import os
        import time
        from pathlib import Path
        
        logger = get_system_logger()
        logger.info("开始执行日志清理任务")
        
        # 清理30天前的日志文件
        log_dir = Path("logs")
        if not log_dir.exists():
            logger.info("日志目录不存在，跳过清理")
            return "日志目录不存在"
        
        cutoff_time = time.time() - (30 * 24 * 60 * 60)  # 30天前
        cleaned_count = 0
        
        for log_file in log_dir.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    cleaned_count += 1
                    logger.info("删除旧日志文件: %s", log_file.name)
                except Exception as e:
                    logger.error("删除日志文件失败: %s - %s", log_file.name, str(e))
        
        logger.info("日志清理任务完成，删除文件数: %d", cleaned_count)
        return f"清理完成，删除 {cleaned_count} 个文件"
        
    except Exception as e:
        logger.error("日志清理任务失败: %s", str(e))
        raise
```

#### 复杂任务示例
```python
# app/tasks/database_size_collection_tasks.py
def collect_database_sizes():
    """
    容量同步定时任务
    每天凌晨3点执行，同步所有活跃实例的数据库容量信息
    """
    try:
        from app.models.instance import Instance
        from app.services.database_size_collector_service import DatabaseSizeCollectorService
        from app.services.sync_session_service import SyncSessionService
        
        sync_logger = get_sync_logger()
        sync_logger.info("开始执行容量同步任务", module="capacity_sync")
        
        # 创建同步会话
        sync_session_service = SyncSessionService()
        session = sync_session_service.create_session(
            sync_type="scheduled_task",
            sync_category="capacity"
        )
        
        # 获取所有活跃实例
        active_instances = Instance.query.filter_by(is_active=True).all()
        
        if not active_instances:
            sync_logger.warning("没有找到活跃的实例", module="capacity_sync")
            sync_session_service.complete_session(session.id, "没有活跃实例")
            return "没有活跃实例"
        
        # 为每个实例创建同步记录
        records = []
        for instance in active_instances:
            record = sync_session_service.add_instance_record(
                session_id=session.id,
                instance_id=instance.id,
                sync_category="capacity"
            )
            records.append(record)
        
        sync_session_service.update_session_total_instances(session.id, len(active_instances))
        
        # 执行容量同步
        total_processed = 0
        total_failed = 0
        
        for i, instance in enumerate(active_instances):
            record = records[i] if i < len(records) else None
            
            try:
                if record:
                    sync_session_service.start_instance_sync(record.id)
                
                sync_logger.info(
                    f"开始同步实例容量: {instance.name}",
                    module="capacity_sync",
                    session_id=session.session_id,
                    instance_id=instance.id,
                    instance_name=instance.name
                )
                
                # 创建采集器
                collector = DatabaseSizeCollectorService(instance)
                
                # 连接数据库
                if not collector.connect():
                    error_msg = f"无法连接到实例: {instance.name}"
                    sync_logger.error(
                        error_msg,
                        module="capacity_sync",
                        session_id=session.session_id,
                        instance_id=instance.id
                    )
                    if record:
                        sync_session_service.fail_instance_sync(record.id, error_msg)
                    total_failed += 1
                    continue
                
                # 采集数据库大小数据
                data = collector.collect_database_sizes()
                
                # 保存数据
                saved_count = collector.save_collected_data(data)
                
                sync_logger.info(
                    f"实例容量同步完成: {instance.name}",
                    module="capacity_sync",
                    session_id=session.session_id,
                    instance_id=instance.id,
                    databases_collected=len(data),
                    records_saved=saved_count
                )
                
                if record:
                    sync_session_service.complete_instance_sync(
                        record.id,
                        accounts_synced=len(data),
                        accounts_created=0,
                        accounts_updated=saved_count,
                        accounts_deleted=0,
                        sync_details={
                            'databases_collected': len(data),
                            'records_saved': saved_count
                        }
                    )
                
                total_processed += 1
                
            except Exception as e:
                error_msg = f"同步实例容量失败: {instance.name} - {str(e)}"
                sync_logger.error(
                    error_msg,
                    module="capacity_sync",
                    session_id=session.session_id,
                    instance_id=instance.id,
                    error=str(e)
                )
                
                if record:
                    sync_session_service.fail_instance_sync(record.id, error_msg)
                
                total_failed += 1
                continue
        
        # 完成会话
        if total_failed == 0:
            message = f"容量同步完成，成功: {total_processed} 个实例"
            sync_session_service.complete_session(session.id, message)
        else:
            message = f"容量同步完成，成功: {total_processed} 个，失败: {total_failed} 个"
            sync_session_service.complete_session(session.id, message)
        
        sync_logger.info(
            message,
            module="capacity_sync",
            session_id=session.session_id,
            total_processed=total_processed,
            total_failed=total_failed
        )
        
        return message
        
    except Exception as e:
        sync_logger.error(
            "容量同步任务执行失败",
            module="capacity_sync",
            error=str(e)
        )
        raise
```

### 4. 事件监听和日志

#### 事件监听器
```python
# app/scheduler.py
def _job_executed(self, event):
    """任务执行成功事件"""
    logger.info(
        "任务执行成功",
        module="scheduler",
        job_id=event.job_id,
        return_value=str(event.retval) if event.retval else None,
        execution_time=event.scheduled_run_time.strftime('%Y-%m-%d %H:%M:%S') if event.scheduled_run_time else None
    )

def _job_error(self, event):
    """任务执行错误事件"""
    exception_str = str(event.exception) if event.exception else "未知错误"
    logger.error(
        "任务执行失败",
        module="scheduler",
        job_id=event.job_id,
        error=exception_str,
        traceback=event.traceback if hasattr(event, 'traceback') else None,
        execution_time=event.scheduled_run_time.strftime('%Y-%m-%d %H:%M:%S') if event.scheduled_run_time else None
    )
```

#### 任务执行日志
```python
# 任务内部日志记录
def example_task():
    """示例任务"""
    logger = get_system_logger()
    
    try:
        logger.info("任务开始执行", module="example_task")
        
        # 任务逻辑
        result = perform_task_logic()
        
        logger.info(
            "任务执行成功",
            module="example_task",
            result=result,
            execution_duration="5.2s"
        )
        
        return f"任务完成: {result}"
        
    except Exception as e:
        logger.error(
            "任务执行失败",
            module="example_task",
            error=str(e),
            exc_info=True
        )
        raise
```

## 前端交互流程

### 1. 任务管理页面交互
```javascript
// app/static/js/pages/scheduler/management.js

// 页面初始化
$(document).ready(function() {
    initializeSchedulerPage();
});

function initializeSchedulerPage() {
    loadJobs();
    initializeEventHandlers();
    console.log('定时任务管理页面已加载');
}

// 加载任务列表
function loadJobs() {
    $('#loadingRow').show();
    $('#jobsContainer').empty();
    $('#emptyRow').hide();
    
    $.ajax({
        url: '/scheduler/api/jobs',
        method: 'GET',
        headers: {
            'X-CSRFToken': $('meta[name="csrf-token"]').attr('content')
        },
        success: function(response) {
            $('#loadingRow').hide();
            if (response.success === true) {
                console.log('Received jobs:', response.data);
                currentJobs = response.data;
                displayJobs(response.data);
            } else {
                showAlert('加载任务失败: ' + response.message, 'danger');
            }
        },
        error: function(xhr) {
            $('#loadingRow').hide();
            if (xhr.status === 401 || xhr.status === 403 || xhr.status === 302) {
                showAlert('请先登录或检查管理员权限', 'warning');
                window.location.href = '/auth/login';
            } else {
                const error = xhr.responseJSON;
                showAlert('加载任务失败: ' + (error ? error.message : '未知错误'), 'danger');
            }
        }
    });
}

// 显示任务列表
function displayJobs(jobs) {
    if (jobs.length === 0) {
        $('#emptyRow').show();
        return;
    }
    
    const container = $('#jobsContainer');
    container.empty();
    
    jobs.forEach(job => {
        const jobCard = createJobCard(job);
        container.append(jobCard);
    });
}

// 创建任务卡片
function createJobCard(job) {
    const statusBadge = getStatusBadge(job);
    const nextRunTime = job.next_run_time || '未安排';
    
    return $(`
        <div class="col-lg-6 col-xl-4 mb-4">
            <div class="card job-card h-100">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h6 class="card-title mb-0">${job.name}</h6>
                    ${statusBadge}
                </div>
                <div class="card-body">
                    <div class="job-info">
                        <div class="info-item">
                            <i class="fas fa-tag text-muted"></i>
                            <span>ID: ${job.id}</span>
                        </div>
                        <div class="info-item">
                            <i class="fas fa-code text-muted"></i>
                            <span>函数: ${job.func_name}</span>
                        </div>
                        <div class="info-item">
                            <i class="fas fa-clock text-muted"></i>
                            <span>触发器: ${job.trigger}</span>
                        </div>
                        <div class="info-item">
                            <i class="fas fa-calendar-alt text-muted"></i>
                            <span>下次执行: ${nextRunTime}</span>
                        </div>
                    </div>
                </div>
                <div class="card-footer">
                    <div class="btn-group w-100" role="group">
                        <button class="btn btn-sm btn-outline-success" onclick="runJobNow('${job.id}')">
                            <i class="fas fa-play"></i> 立即执行
                        </button>
                        <button class="btn btn-sm btn-outline-warning" onclick="pauseJob('${job.id}')">
                            <i class="fas fa-pause"></i> 暂停
                        </button>
                        <button class="btn btn-sm btn-outline-primary" onclick="editJob('${job.id}')">
                            <i class="fas fa-edit"></i> 编辑
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteJob('${job.id}')">
                            <i class="fas fa-trash"></i> 删除
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `);
}

// 任务控制操作
function runJobNow(jobId) {
    if (!confirm('确定要立即执行此任务吗？')) {
        return;
    }
    
    $.ajax({
        url: `/scheduler/api/jobs/${jobId}/run`,
        method: 'POST',
        headers: {
            'X-CSRFToken': $('meta[name="csrf-token"]').attr('content')
        },
        success: function(response) {
            if (response.success) {
                showAlert('任务已立即执行', 'success');
                loadJobs(); // 刷新任务列表
            } else {
                showAlert('执行任务失败: ' + response.message, 'danger');
            }
        },
        error: function(xhr) {
            const error = xhr.responseJSON;
            showAlert('执行任务失败: ' + (error ? error.message : '未知错误'), 'danger');
        }
    });
}

function pauseJob(jobId) {
    $.ajax({
        url: `/scheduler/api/jobs/${jobId}/pause`,
        method: 'POST',
        headers: {
            'X-CSRFToken': $('meta[name="csrf-token"]').attr('content')
        },
        success: function(response) {
            if (response.success) {
                showAlert('任务已暂停', 'success');
                loadJobs(); // 刷新任务列表
            } else {
                showAlert('暂停任务失败: ' + response.message, 'danger');
            }
        },
        error: function(xhr) {
            const error = xhr.responseJSON;
            showAlert('暂停任务失败: ' + (error ? error.message : '未知错误'), 'danger');
        }
    });
}

function resumeJob(jobId) {
    $.ajax({
        url: `/scheduler/api/jobs/${jobId}/resume`,
        method: 'POST',
        headers: {
            'X-CSRFToken': $('meta[name="csrf-token"]').attr('content')
        },
        success: function(response) {
            if (response.success) {
                showAlert('任务已恢复', 'success');
                loadJobs(); // 刷新任务列表
            } else {
                showAlert('恢复任务失败: ' + response.message, 'danger');
            }
        },
        error: function(xhr) {
            const error = xhr.responseJSON;
            showAlert('恢复任务失败: ' + (error ? error.message : '未知错误'), 'danger');
        }
    });
}

function deleteJob(jobId) {
    if (!confirm('确定要删除此任务吗？此操作不可恢复。')) {
        return;
    }
    
    $.ajax({
        url: `/scheduler/api/jobs/${jobId}`,
        method: 'DELETE',
        headers: {
            'X-CSRFToken': $('meta[name="csrf-token"]').attr('content')
        },
        success: function(response) {
            if (response.success) {
                showAlert('任务已删除', 'success');
                loadJobs(); // 刷新任务列表
            } else {
                showAlert('删除任务失败: ' + response.message, 'danger');
            }
        },
        error: function(xhr) {
            const error = xhr.responseJSON;
            showAlert('删除任务失败: ' + (error ? error.message : '未知错误'), 'danger');
        }
    });
}
```

### 2. Cron表达式编辑器
```javascript
// Cron表达式编辑功能
function updateEditCronPreview() {
    const second = $('#editCronSecond').val() || '0';
    const minute = $('#editCronMinute').val() || '0';
    const hour = $('#editCronHour').val() || '0';
    const day = $('#editCronDay').val() || '*';
    const month = $('#editCronMonth').val() || '*';
    const weekday = $('#editCronWeekday').val() || '*';
    const year = $('#editCronYear').val() || '';
    
    const base = `${second} ${minute} ${hour} ${day} ${month} ${weekday}`;
    const cronExpression = year && year.trim() !== '' ? `${base} ${year}` : base;
    
    $('#editCronPreview').val(cronExpression);
    
    // 显示Cron表达式说明
    updateCronDescription(cronExpression);
}

function updateCronDescription(cronExpression) {
    const parts = cronExpression.split(' ');
    let description = '执行时间: ';
    
    if (parts.length >= 6) {
        const [second, minute, hour, day, month, weekday] = parts;
        
        // 构建人性化描述
        if (hour === '*' && minute === '*') {
            description += '每秒执行';
        } else if (hour === '*') {
            description += `每小时的第 ${minute} 分钟执行`;
        } else if (day === '*' && weekday === '*') {
            description += `每天 ${hour}:${minute.padStart(2, '0')} 执行`;
        } else if (weekday !== '*') {
            const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
            const dayNames = weekday.split(',').map(d => weekdays[parseInt(d)] || d).join('、');
            description += `每 ${dayNames} ${hour}:${minute.padStart(2, '0')} 执行`;
        } else {
            description += `每月 ${day} 日 ${hour}:${minute.padStart(2, '0')} 执行`;
        }
    }
    
    $('#cronDescription').text(description);
}

// 预设Cron表达式
function setPresetCron(preset) {
    const presets = {
        'daily': { second: '0', minute: '0', hour: '2', day: '*', month: '*', weekday: '*' },
        'weekly': { second: '0', minute: '0', hour: '2', day: '*', month: '*', weekday: '0' },
        'monthly': { second: '0', minute: '0', hour: '2', day: '1', month: '*', weekday: '*' },
        'hourly': { second: '0', minute: '0', hour: '*', day: '*', month: '*', weekday: '*' }
    };
    
    const config = presets[preset];
    if (config) {
        Object.keys(config).forEach(key => {
            $(`#editCron${key.charAt(0).toUpperCase() + key.slice(1)}`).val(config[key]);
        });
        updateEditCronPreview();
    }
}
```

### 3. 任务监控组件
```javascript
// 任务监控功能
class TaskMonitor {
    constructor() {
        this.monitoringInterval = null;
        this.isMonitoring = false;
    }
    
    startMonitoring() {
        if (this.isMonitoring) {
            return;
        }
        
        this.isMonitoring = true;
        this.monitoringInterval = setInterval(() => {
            this.checkTaskStatus();
        }, 30000); // 每30秒检查一次
        
        console.log('任务监控已启动');
    }
    
    stopMonitoring() {
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
            this.monitoringInterval = null;
        }
        this.isMonitoring = false;
        console.log('任务监控已停止');
    }
    
    async checkTaskStatus() {
        try {
            const response = await fetch('/scheduler/api/jobs');
            const data = await response.json();
            
            if (data.success) {
                this.updateTaskStatus(data.data);
            }
        } catch (error) {
            console.error('检查任务状态失败:', error);
        }
    }
    
    updateTaskStatus(jobs) {
        jobs.forEach(job => {
            const jobCard = $(`.job-card[data-job-id="${job.id}"]`);
            if (jobCard.length > 0) {
                // 更新下次执行时间
                const nextRunTime = job.next_run_time || '未安排';
                jobCard.find('.next-run-time').text(nextRunTime);
                
                // 更新状态徽章
                const statusBadge = this.getStatusBadge(job);
                jobCard.find('.status-badge').replaceWith(statusBadge);
            }
        });
    }
    
    getStatusBadge(job) {
        if (job.next_run_time) {
            return '<span class="badge bg-success status-badge">运行中</span>';
        } else {
            return '<span class="badge bg-secondary status-badge">已暂停</span>';
        }
    }
}

// 全局任务监控实例
window.taskMonitor = new TaskMonitor();

// 页面加载时启动监控
$(document).ready(function() {
    window.taskMonitor.startMonitoring();
});

// 页面卸载时停止监控
$(window).on('beforeunload', function() {
    window.taskMonitor.stopMonitoring();
});
```

## 数据库设计

### APScheduler数据库表
```sql
-- APScheduler自动创建的表结构
CREATE TABLE apscheduler_jobs (
    id VARCHAR(191) NOT NULL,
    next_run_time DOUBLE,
    job_state BLOB NOT NULL,
    PRIMARY KEY (id),
    KEY ix_apscheduler_jobs_next_run_time (next_run_time)
);
```

### 任务执行日志表（扩展）
```sql
-- 可选的任务执行历史表
CREATE TABLE task_execution_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(191) NOT NULL,
    job_name VARCHAR(255),
    execution_time DATETIME NOT NULL,
    duration_seconds FLOAT,
    status VARCHAR(20) NOT NULL,  -- success, failed, timeout
    return_value TEXT,
    error_message TEXT,
    traceback TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_task_logs_job_id (job_id),
    INDEX idx_task_logs_execution_time (execution_time),
    INDEX idx_task_logs_status (status)
);
```

## 配置管理

### 调度器配置
```python
# app/config/scheduler_config.py
SCHEDULER_CONFIG = {
    # 数据库配置
    'jobstore_url': 'sqlite:///userdata/scheduler.db',
    
    # 执行器配置
    'executor_max_workers': 5,
    'executor_type': 'thread',
    
    # 任务默认配置
    'job_defaults': {
        'coalesce': True,           # 合并相同任务
        'max_instances': 1,         # 最大实例数
        'misfire_grace_time': 300,  # 错过执行时间容忍度（秒）
    },
    
    # 时区配置
    'timezone': 'Asia/Shanghai',
    
    # 监控配置
    'enable_monitoring': True,
    'log_execution_history': True,
    'cleanup_old_logs_days': 30,
}
```

### 任务配置文件
```yaml
# app/config/scheduler_tasks.yaml
default_tasks:
  # 系统维护任务
  - id: cleanup_old_logs
    name: 清理旧日志
    function: cleanup_old_logs
    trigger_type: cron
    trigger_params:
      hour: 2
      minute: 0
    enabled: true
    description: 清理30天前的日志和临时文件
    category: maintenance
    
  # 数据同步任务
  - id: sync_accounts
    name: 账户同步
    function: sync_accounts
    trigger_type: cron
    trigger_params:
      hour: 1
      minute: 0
    enabled: true
    description: 每日同步所有数据库实例的账户信息
    category: sync
    
  - id: collect_database_sizes
    name: 容量同步
    function: collect_database_sizes
    trigger_type: cron
    trigger_params:
      hour: 3
      minute: 0
    enabled: true
    description: 每日同步所有数据库实例的容量信息
    category: sync
    
  # 数据处理任务
  - id: calculate_database_size_aggregations
    name: 计算统计聚合
    function: calculate_database_size_aggregations
    trigger_type: cron
    trigger_params:
      hour: 4
      minute: 0
    enabled: true
    description: 每日计算数据库大小的日、周、月、季度统计聚合
    category: processing
    
  # 监控任务
  - id: monitor_partition_health
    name: 监控分区健康状态
    function: monitor_partition_health
    trigger_type: cron
    trigger_params:
      hour: 0
      minute: 30
    enabled: true
    description: 每日监控分区健康状态和性能
    category: monitoring
```

## 错误处理

### 任务执行错误处理
```python
# 任务内部错误处理
def robust_task_wrapper(task_func):
    """任务执行包装器，提供统一的错误处理"""
    def wrapper(*args, **kwargs):
        logger = get_system_logger()
        task_name = task_func.__name__
        
        try:
            logger.info(f"任务开始执行: {task_name}")
            start_time = time.time()
            
            result = task_func(*args, **kwargs)
            
            duration = time.time() - start_time
            logger.info(
                f"任务执行成功: {task_name}",
                duration=f"{duration:.2f}s",
                result=str(result)[:200] if result else None
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"任务执行失败: {task_name}",
                duration=f"{duration:.2f}s",
                error=str(e),
                exc_info=True
            )
            
            # 可选：发送告警通知
            send_task_failure_alert(task_name, str(e))
            
            # 重新抛出异常，让APScheduler处理
            raise
    
    wrapper.__name__ = task_func.__name__
    return wrapper

# 使用装饰器
@robust_task_wrapper
def example_task():
    """示例任务"""
    # 任务逻辑
    pass
```

### 调度器错误处理
```python
# app/scheduler.py
def _job_error(self, event):
    """任务执行错误事件"""
    exception_str = str(event.exception) if event.exception else "未知错误"
    
    logger.error(
        "任务执行失败",
        module="scheduler",
        job_id=event.job_id,
        error=exception_str,
        traceback=event.traceback if hasattr(event, 'traceback') else None
    )
    
    # 记录到数据库（可选）
    try:
        from app.models.task_execution_log import TaskExecutionLog
        log_entry = TaskExecutionLog(
            job_id=event.job_id,
            execution_time=event.scheduled_run_time,
            status='failed',
            error_message=exception_str,
            traceback=getattr(event, 'traceback', None)
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        logger.error(f"记录任务执行日志失败: {str(e)}")
    
    # 发送告警（可选）
    send_task_failure_alert(event.job_id, exception_str)
```

## 监控和告警

### 任务执行监控
```python
# app/services/task_monitor_service.py
class TaskMonitorService:
    """任务监控服务"""
    
    @staticmethod
    def get_task_statistics():
        """获取任务统计信息"""
        scheduler = get_scheduler()
        if not scheduler:
            return {}
        
        jobs = scheduler.get_jobs()
        
        stats = {
            'total_jobs': len(jobs),
            'running_jobs': 0,
            'paused_jobs': 0,
            'next_executions': []
        }
        
        for job in jobs:
            if job.next_run_time:
                stats['running_jobs'] += 1
                stats['next_executions'].append({
                    'job_id': job.id,
                    'job_name': job.name,
                    'next_run_time': job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')
                })
            else:
                stats['paused_jobs'] += 1
        
        # 按执行时间排序
        stats['next_executions'].sort(key=lambda x: x['next_run_time'])
        
        return stats
    
    @staticmethod
    def check_task_health():
        """检查任务健康状态"""
        scheduler = get_scheduler()
        if not scheduler or not scheduler.running:
            return {
                'status': 'error',
                'message': '调度器未运行'
            }
        
        jobs = scheduler.get_jobs()
        
        # 检查是否有任务
        if not jobs:
            return {
                'status': 'warning',
                'message': '没有配置任务'
            }
        
        # 检查是否有运行中的任务
        running_jobs = [job for job in jobs if job.next_run_time]
        if not running_jobs:
            return {
                'status': 'warning',
                'message': '所有任务都已暂停'
            }
        
        return {
            'status': 'healthy',
            'message': f'调度器正常运行，{len(running_jobs)} 个任务活跃'
        }
```

### 告警通知
```python
# app/services/alert_service.py
def send_task_failure_alert(job_id, error_message):
    """发送任务失败告警"""
    try:
        # 这里可以集成各种告警方式
        # 例如：邮件、钉钉、企业微信、Slack等
        
        alert_message = f"""
        任务执行失败告警
        
        任务ID: {job_id}
        失败时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        错误信息: {error_message}
        
        请及时检查任务状态并处理。
        """
        
        # 发送邮件告警（示例）
        send_email_alert("任务执行失败", alert_message)
        
        # 发送钉钉告警（示例）
        send_dingtalk_alert(alert_message)
        
    except Exception as e:
        logger.error(f"发送任务失败告警时出错: {str(e)}")

def send_email_alert(subject, message):
    """发送邮件告警"""
    # 邮件发送逻辑
    pass

def send_dingtalk_alert(message):
    """发送钉钉告警"""
    # 钉钉机器人发送逻辑
    pass
```

## 性能优化

### 1. 任务执行优化
```python
# 任务执行性能优化
def optimized_task():
    """优化的任务示例"""
    # 1. 使用连接池
    with get_database_connection_pool() as conn:
        # 数据库操作
        pass
    
    # 2. 批量处理
    batch_size = 1000
    for batch in batch_iterator(data, batch_size):
        process_batch(batch)
    
    # 3. 异步处理（如果适用）
    import asyncio
    async def async_operation():
        # 异步操作
        pass
    
    # 4. 内存管理
    import gc
    gc.collect()  # 手动垃圾回收
```

### 2. 调度器性能优化
```python
# 调度器性能配置
SCHEDULER_CONFIG = {
    # 优化执行器
    'executor_max_workers': min(32, (os.cpu_count() or 1) + 4),
    
    # 优化作业存储
    'jobstore_pool_size': 20,
    'jobstore_pool_recycle': 3600,
    
    # 优化任务配置
    'job_defaults': {
        'coalesce': True,           # 合并相同任务
        'max_instances': 1,         # 限制并发实例
        'misfire_grace_time': 300,  # 合理的容忍时间
    }
}
```

### 3. 前端性能优化
```javascript
// 前端性能优化
class OptimizedTaskManager {
    constructor() {
        this.updateInterval = null;
        this.lastUpdateTime = 0;
        this.updateThrottle = 5000; // 5秒节流
    }
    
    // 节流更新
    throttledUpdate() {
        const now = Date.now();
        if (now - this.lastUpdateTime > this.updateThrottle) {
            this.loadJobs();
            this.lastUpdateTime = now;
        }
    }
    
    // 虚拟滚动（大量任务时）
    renderJobsVirtual(jobs) {
        const visibleJobs = this.getVisibleJobs(jobs);
        this.renderJobs(visibleJobs);
    }
    
    // 缓存任务数据
    cacheJobData(jobs) {
        localStorage.setItem('cached_jobs', JSON.stringify({
            data: jobs,
            timestamp: Date.now()
        }));
    }
    
    getCachedJobData() {
        const cached = localStorage.getItem('cached_jobs');
        if (cached) {
            const { data, timestamp } = JSON.parse(cached);
            // 缓存5分钟有效
            if (Date.now() - timestamp < 300000) {
                return data;
            }
        }
        return null;
    }
}
```

## 测试策略

### 单元测试
```python
# 测试任务执行
def test_sync_accounts_task():
    """测试账户同步任务"""
    from app.tasks.legacy_tasks import sync_accounts
    
    # 模拟数据
    with patch('app.models.instance.Instance.query') as mock_query:
        mock_instance = Mock()
        mock_instance.name = 'test_instance'
        mock_query.filter_by.return_value.all.return_value = [mock_instance]
        
        # 执行任务
        result = sync_accounts()
        
        # 验证结果
        assert result is not None
        assert 'test_instance' in str(result)

# 测试调度器
def test_scheduler_initialization():
    """测试调度器初始化"""
    from app.scheduler import TaskScheduler
    
    scheduler = TaskScheduler()
    assert scheduler.scheduler is not None
    assert not scheduler.scheduler.running
    
    scheduler.start()
    assert scheduler.scheduler.running
    
    scheduler.stop()
    assert not scheduler.scheduler.running
```

### 集成测试
```python
# 测试任务API
def test_create_job_api(client, admin_headers):
    """测试创建任务API"""
    job_data = {
        'id': 'test_job',
        'name': '测试任务',
        'code': '''
def execute_task():
    return "测试成功"
        ''',
        'trigger_type': 'cron',
        'cron_hour': '2',
        'cron_minute': '0'
    }
    
    response = client.post('/scheduler/api/jobs', 
        headers=admin_headers,
        json=job_data
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True

def test_job_execution(client, admin_headers):
    """测试任务执行"""
    # 创建任务
    job_data = {
        'id': 'test_execution',
        'name': '执行测试',
        'code': '''
def execute_task():
    return "执行成功"
        ''',
        'trigger_type': 'cron',
        'cron_hour': '2',
        'cron_minute': '0'
    }
    
    create_response = client.post('/scheduler/api/jobs', 
        headers=admin_headers,
        json=job_data
    )
    assert create_response.status_code == 200
    
    # 立即执行任务
    run_response = client.post('/scheduler/api/jobs/test_execution/run',
        headers=admin_headers
    )
    assert run_response.status_code == 200
```

### 前端测试
```javascript
// 测试任务管理功能
describe('TaskManager', () => {
    let taskManager;
    
    beforeEach(() => {
        taskManager = new TaskManager();
        // 模拟jQuery和DOM
        global.$ = jest.fn(() => ({
            ajax: jest.fn(),
            empty: jest.fn(),
            append: jest.fn()
        }));
    });
    
    test('should load jobs correctly', async () => {
        const mockJobs = [
            { id: 'test1', name: '测试任务1' },
            { id: 'test2', name: '测试任务2' }
        ];
        
        // 模拟AJAX响应
        $.ajax.mockImplementation(({ success }) => {
            success({ success: true, data: mockJobs });
        });
        
        await taskManager.loadJobs();
        
        expect(taskManager.currentJobs).toEqual(mockJobs);
    });
    
    test('should handle job control operations', async () => {
        const jobId = 'test_job';
        
        // 模拟成功响应
        $.ajax.mockImplementation(({ success }) => {
            success({ success: true, message: '操作成功' });
        });
        
        await taskManager.pauseJob(jobId);
        await taskManager.resumeJob(jobId);
        await taskManager.runJobNow(jobId);
        
        expect($.ajax).toHaveBeenCalledTimes(3);
    });
});
```

## 部署和维护

### 生产环境部署
```python
# 生产环境调度器配置
PRODUCTION_SCHEDULER_CONFIG = {
    # 使用PostgreSQL作为作业存储
    'jobstore_url': 'postgresql://user:password@localhost/scheduler_db',
    
    # 增加执行器工作线程
    'executor_max_workers': 10,
    
    # 启用持久化
    'enable_persistence': True,
    
    # 监控配置
    'enable_monitoring': True,
    'log_execution_history': True,
    'cleanup_old_logs_days': 90,
    
    # 告警配置
    'enable_alerts': True,
    'alert_channels': ['email', 'dingtalk'],
}
```

### 监控脚本
```bash
#!/bin/bash
# 调度器健康检查脚本

SCHEDULER_URL="http://localhost:5000/scheduler/api/health"
LOG_FILE="/var/log/scheduler_health.log"

# 检查调度器状态
response=$(curl -s -o /dev/null -w "%{http_code}" $SCHEDULER_URL)

if [ $response -eq 200 ]; then
    echo "$(date): 调度器状态正常" >> $LOG_FILE
else
    echo "$(date): 调度器状态异常 (HTTP $response)" >> $LOG_FILE
    # 发送告警
    echo "调度器状态异常" | mail -s "调度器告警" admin@example.com
fi
```

### 备份和恢复
```python
# 调度器数据备份
def backup_scheduler_data():
    """备份调度器数据"""
    import shutil
    from datetime import datetime
    
    # 备份SQLite数据库
    source_db = "userdata/scheduler.db"
    backup_db = f"backups/scheduler_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    os.makedirs("backups", exist_ok=True)
    shutil.copy2(source_db, backup_db)
    
    logger.info(f"调度器数据已备份到: {backup_db}")
    
    # 清理旧备份（保留30天）
    cleanup_old_backups("backups", days=30)

def restore_scheduler_data(backup_file):
    """恢复调度器数据"""
    import shutil
    
    if not os.path.exists(backup_file):
        raise FileNotFoundError(f"备份文件不存在: {backup_file}")
    
    # 停止调度器
    scheduler = get_scheduler()
    if scheduler and scheduler.running:
        scheduler.shutdown()
    
    # 恢复数据库
    target_db = "userdata/scheduler.db"
    shutil.copy2(backup_file, target_db)
    
    logger.info(f"调度器数据已从 {backup_file} 恢复")
    
    # 重新启动调度器
    init_scheduler(current_app)
```

## 扩展功能

### 1. 任务依赖管理
```python
# 任务依赖系统
class TaskDependencyManager:
    """任务依赖管理器"""
    
    def __init__(self):
        self.dependencies = {}  # job_id -> [dependency_job_ids]
        self.completed_jobs = set()
    
    def add_dependency(self, job_id, dependency_job_id):
        """添加任务依赖"""
        if job_id not in self.dependencies:
            self.dependencies[job_id] = []
        self.dependencies[job_id].append(dependency_job_id)
    
    def can_execute(self, job_id):
        """检查任务是否可以执行"""
        dependencies = self.dependencies.get(job_id, [])
        return all(dep in self.completed_jobs for dep in dependencies)
    
    def mark_completed(self, job_id):
        """标记任务完成"""
        self.completed_jobs.add(job_id)
        
        # 检查是否有等待的任务可以执行
        self.trigger_waiting_jobs()
    
    def trigger_waiting_jobs(self):
        """触发等待中的任务"""
        scheduler = get_scheduler()
        
        for job_id, dependencies in self.dependencies.items():
            if (job_id not in self.completed_jobs and 
                self.can_execute(job_id)):
                
                job = scheduler.get_job(job_id)
                if job:
                    # 立即执行任务
                    scheduler.modify_job(job_id, next_run_time=datetime.now())
```

### 2. 任务分组管理
```python
# 任务分组功能
class TaskGroup:
    """任务分组"""
    
    def __init__(self, group_id, name, description=""):
        self.group_id = group_id
        self.name = name
        self.description = description
        self.jobs = []
    
    def add_job(self, job_id):
        """添加任务到分组"""
        if job_id not in self.jobs:
            self.jobs.append(job_id)
    
    def remove_job(self, job_id):
        """从分组移除任务"""
        if job_id in self.jobs:
            self.jobs.remove(job_id)
    
    def pause_all(self):
        """暂停分组内所有任务"""
        scheduler = get_scheduler()
        for job_id in self.jobs:
            try:
                scheduler.pause_job(job_id)
            except Exception as e:
                logger.error(f"暂停任务失败: {job_id} - {str(e)}")
    
    def resume_all(self):
        """恢复分组内所有任务"""
        scheduler = get_scheduler()
        for job_id in self.jobs:
            try:
                scheduler.resume_job(job_id)
            except Exception as e:
                logger.error(f"恢复任务失败: {job_id} - {str(e)}")
```

### 3. 任务模板系统
```python
# 任务模板
class TaskTemplate:
    """任务模板"""
    
    def __init__(self, template_id, name, code_template, default_config):
        self.template_id = template_id
        self.name = name
        self.code_template = code_template
        self.default_config = default_config
    
    def create_job(self, job_id, job_name, config_overrides=None):
        """从模板创建任务"""
        config = self.default_config.copy()
        if config_overrides:
            config.update(config_overrides)
        
        # 替换模板变量
        code = self.code_template.format(**config)
        
        return {
            'id': job_id,
            'name': job_name,
            'code': code,
            'trigger_type': config.get('trigger_type', 'cron'),
            **{k: v for k, v in config.items() if k.startswith('cron_')}
        }

# 预定义模板
TASK_TEMPLATES = {
    'database_backup': TaskTemplate(
        template_id='database_backup',
        name='数据库备份模板',
        code_template='''
def execute_task():
    import subprocess
    
    # 备份数据库
    cmd = "pg_dump -h {host} -U {username} -d {database} > {backup_path}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        return f"备份成功: {backup_path}"
    else:
        raise Exception(f"备份失败: {result.stderr}")
        ''',
        default_config={
            'trigger_type': 'cron',
            'cron_hour': '2',
            'cron_minute': '0',
            'host': 'localhost',
            'username': 'postgres',
            'database': 'mydb',
            'backup_path': '/backups/db_backup.sql'
        }
    ),
    
    'log_cleanup': TaskTemplate(
        template_id='log_cleanup',
        name='日志清理模板',
        code_template='''
def execute_task():
    import os
    import time
    from pathlib import Path
    
    log_dir = Path("{log_directory}")
    days_to_keep = {days_to_keep}
    cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
    
    cleaned_count = 0
    for log_file in log_dir.glob("*.log*"):
        if log_file.stat().st_mtime < cutoff_time:
            log_file.unlink()
            cleaned_count += 1
    
    return f"清理完成，删除 {cleaned_count} 个日志文件"
        ''',
        default_config={
            'trigger_type': 'cron',
            'cron_hour': '3',
            'cron_minute': '0',
            'log_directory': '/var/log/myapp',
            'days_to_keep': 30
        }
    )
}
```

## 总结

任务调度功能是鲸落系统的重要基础设施，提供了完整的定时任务管理能力。该功能具有以下特点：

1. **基于APScheduler的可靠调度**：使用成熟的Python调度库，提供高可靠性
2. **灵活的任务配置**：支持Cron表达式、间隔触发等多种触发方式
3. **完善的任务管理**：支持任务的创建、编辑、删除、暂停、恢复等操作
4. **实时监控和日志**：提供任务执行状态监控和详细日志记录
5. **可扩展的任务系统**：支持动态任务创建和模板化任务定义
6. **用户友好的界面**：直观的Web界面，支持可视化任务管理
7. **高性能设计**：优化的执行器配置和资源管理
8. **完善的错误处理**：统一的异常处理和告警机制

通过合理的架构设计和功能实现，任务调度功能为整个系统的自动化运维提供了强有力的支撑。
