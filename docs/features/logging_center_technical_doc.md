# 日志中心功能技术文档

## 1. 功能概述

### 1.1 功能描述
日志中心是鲸落系统的核心基础设施模块，提供统一的日志管理、记录、存储和分析功能。该模块基于结构化日志设计，支持多种日志类型、级别和输出方式，为系统监控、问题诊断和审计提供完整的日志支持。

### 1.2 主要特性
- **统一日志管理**：集成多种日志类型（应用、错误、访问、安全、数据库、任务、结构化）
- **多级别日志**：支持DEBUG、INFO、WARNING、ERROR、CRITICAL五个级别
- **结构化日志**：基于JSON格式的结构化日志记录
- **多输出方式**：支持控制台、文件、数据库多种输出方式
- **日志轮转**：自动日志文件轮转和压缩
- **实时监控**：提供日志实时查看和搜索功能
- **性能优化**：异步日志写入，避免阻塞主业务

### 1.3 技术特点
- 基于loguru的高性能日志框架
- 结构化日志记录和查询
- 多类型日志分类管理
- 异步日志写入机制
- 数据库日志存储
- 日志检索和过滤

## 2. 技术架构

### 2.1 整体架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   日志记录层    │    │   日志处理层    │    │   日志存储层    │
│                 │    │                 │    │                 │
│ - 应用日志      │◄──►│ - 日志格式化    │◄──►│ - 文件存储      │
│ - 错误日志      │    │ - 级别过滤      │    │ - 数据库存储    │
│ - 访问日志      │    │ - 上下文注入    │    │ - 控制台输出    │
│ - 安全日志      │    │ - 异步处理      │    │ - 日志轮转      │
│ - 数据库日志    │    │ - 性能优化      │    │ - 压缩归档      │
│ - 任务日志      │    │ - 错误处理      │    │ - 清理策略      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2.2 核心组件
- **日志配置管理器**：统一管理日志配置和初始化
- **结构化日志处理器**：处理结构化日志记录和存储
- **日志类型枚举**：定义各种日志类型和级别
- **数据库日志模型**：统一日志数据模型
- **日志路由**：提供日志查看和搜索API

## 3. 前端实现

### 3.1 页面结构
- **主页面**：`app/templates/unified_logs/dashboard.html`
- **样式文件**：`app/static/css/pages/unified_logs/dashboard.css`
- **脚本文件**：`app/static/js/pages/unified_logs/dashboard.js`

### 3.2 核心组件

#### 3.2.1 日志仪表板组件
```html
<!-- 日志概览卡片 -->
<div class="row mb-4">
    <div class="col-md-3">
        <div class="card bg-primary text-white">
            <div class="card-body">
                <div class="d-flex justify-content-between">
                    <div>
                        <h4 class="card-title" id="total-logs">0</h4>
                        <p class="card-text">总日志数</p>
                    </div>
                    <div class="align-self-center">
                        <i class="fas fa-file-alt fa-2x"></i>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <!-- 其他统计卡片... -->
</div>
```

#### 3.2.2 日志搜索组件
```html
<!-- 搜索和过滤区域 -->
<div class="card mb-4">
    <div class="card-header">
        <h5 class="card-title mb-0">
            <i class="fas fa-search me-2"></i>日志搜索
        </h5>
    </div>
    <div class="card-body">
        <form id="log-search-form">
            <div class="row">
                <div class="col-md-3">
                    <label for="log-level" class="form-label">日志级别</label>
                    <select class="form-select" id="log-level" name="level">
                        <option value="">全部级别</option>
                        <option value="DEBUG">DEBUG</option>
                        <option value="INFO">INFO</option>
                        <option value="WARNING">WARNING</option>
                        <option value="ERROR">ERROR</option>
                        <option value="CRITICAL">CRITICAL</option>
                    </select>
                </div>
                <div class="col-md-3">
                    <label for="log-module" class="form-label">模块</label>
                    <select class="form-select" id="log-module" name="module">
                        <option value="">全部模块</option>
                        <option value="auth">认证模块</option>
                        <option value="database">数据库模块</option>
                        <option value="task">任务模块</option>
                        <option value="sync">同步模块</option>
                    </select>
                </div>
                <div class="col-md-4">
                    <label for="log-message" class="form-label">消息内容</label>
                    <input type="text" class="form-control" id="log-message" name="message" placeholder="搜索日志消息...">
                </div>
                <div class="col-md-2">
                    <label class="form-label">&nbsp;</label>
                    <button type="submit" class="btn btn-primary w-100">
                        <i class="fas fa-search me-1"></i>搜索
                    </button>
                </div>
            </div>
        </form>
    </div>
</div>
```

#### 3.2.3 日志列表组件
```html
<!-- 日志列表 -->
<div class="card">
    <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="card-title mb-0">
            <i class="fas fa-list me-2"></i>日志列表
        </h5>
        <div class="btn-group" role="group">
            <button type="button" class="btn btn-outline-primary btn-sm" id="refresh-logs">
                <i class="fas fa-sync-alt me-1"></i>刷新
            </button>
            <button type="button" class="btn btn-outline-danger btn-sm" id="clear-logs">
                <i class="fas fa-trash me-1"></i>清空
            </button>
        </div>
    </div>
    <div class="card-body p-0">
        <div class="table-responsive">
            <table class="table table-hover mb-0" id="logs-table">
                <thead class="table-light">
                    <tr>
                        <th>时间</th>
                        <th>级别</th>
                        <th>模块</th>
                        <th>消息</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody id="logs-tbody">
                    <!-- 日志数据通过JavaScript动态加载 -->
                </tbody>
            </table>
        </div>
    </div>
    <div class="card-footer">
        <nav aria-label="日志分页">
            <ul class="pagination pagination-sm mb-0" id="logs-pagination">
                <!-- 分页组件通过JavaScript动态生成 -->
            </ul>
        </nav>
    </div>
</div>
```

### 3.3 JavaScript实现

#### 3.3.1 日志搜索功能
```javascript
// 日志搜索和过滤
class LogSearchManager {
    constructor() {
        this.currentPage = 1;
        this.pageSize = 20;
        this.filters = {};
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadLogs();
    }

    bindEvents() {
        // 搜索表单提交
        document.getElementById('log-search-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.applyFilters();
        });

        // 刷新按钮
        document.getElementById('refresh-logs').addEventListener('click', () => {
            this.loadLogs();
        });

        // 清空按钮
        document.getElementById('clear-logs').addEventListener('click', () => {
            this.clearLogs();
        });
    }

    applyFilters() {
        const formData = new FormData(document.getElementById('log-search-form'));
        this.filters = {};
        
        for (let [key, value] of formData.entries()) {
            if (value.trim()) {
                this.filters[key] = value.trim();
            }
        }
        
        this.currentPage = 1;
        this.loadLogs();
    }

    async loadLogs() {
        try {
            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: this.pageSize,
                ...this.filters
            });

            const response = await fetch(`/api/logs/search?${params}`);
            const data = await response.json();

            if (data.success) {
                this.renderLogs(data.data.logs);
                this.renderPagination(data.data.pagination);
            } else {
                this.showError(data.message || '加载日志失败');
            }
        } catch (error) {
            console.error('加载日志失败:', error);
            this.showError('网络错误，请稍后重试');
        }
    }

    renderLogs(logs) {
        const tbody = document.getElementById('logs-tbody');
        tbody.innerHTML = '';

        if (logs.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-muted py-4">
                        <i class="fas fa-inbox fa-2x mb-2"></i>
                        <p class="mb-0">暂无日志数据</p>
                    </td>
                </tr>
            `;
            return;
        }

        logs.forEach(log => {
            const row = this.createLogRow(log);
            tbody.appendChild(row);
        });
    }

    createLogRow(log) {
        const row = document.createElement('tr');
        
        // 根据日志级别设置行样式
        const levelClass = this.getLevelClass(log.level);
        row.className = levelClass;

        row.innerHTML = `
            <td>
                <small class="text-muted">${this.formatTimestamp(log.timestamp)}</small>
            </td>
            <td>
                <span class="badge ${this.getLevelBadgeClass(log.level)}">
                    ${log.level}
                </span>
            </td>
            <td>
                <code class="text-primary">${log.module}</code>
            </td>
            <td>
                <div class="log-message" style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    ${this.escapeHtml(log.message)}
                </div>
            </td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="logManager.viewLogDetails(${log.id})">
                    <i class="fas fa-eye"></i>
                </button>
            </td>
        `;

        return row;
    }

    getLevelClass(level) {
        const levelClasses = {
            'DEBUG': '',
            'INFO': '',
            'WARNING': 'table-warning',
            'ERROR': 'table-danger',
            'CRITICAL': 'table-danger'
        };
        return levelClasses[level] || '';
    }

    getLevelBadgeClass(level) {
        const badgeClasses = {
            'DEBUG': 'bg-secondary',
            'INFO': 'bg-info',
            'WARNING': 'bg-warning',
            'ERROR': 'bg-danger',
            'CRITICAL': 'bg-dark'
        };
        return badgeClasses[level] || 'bg-secondary';
    }

    formatTimestamp(timestamp) {
        return new Date(timestamp).toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async clearLogs() {
        if (!confirm('确定要清空所有日志吗？此操作不可恢复！')) {
            return;
        }

        try {
            const response = await fetch('/api/logs/clear', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccess('日志清空成功');
                this.loadLogs();
            } else {
                this.showError(data.message || '清空日志失败');
            }
        } catch (error) {
            console.error('清空日志失败:', error);
            this.showError('网络错误，请稍后重试');
        }
    }

    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    }

    showSuccess(message) {
        // 显示成功消息
        this.showAlert(message, 'success');
    }

    showError(message) {
        // 显示错误消息
        this.showAlert(message, 'danger');
    }

    showAlert(message, type) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        const container = document.querySelector('.container-fluid');
        container.insertBefore(alertDiv, container.firstChild);

        // 自动隐藏
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// 初始化日志管理器
const logManager = new LogSearchManager();
```

## 4. 后端实现

### 4.1 数据模型

#### 4.1.1 统一日志模型
```python
# app/models/unified_log.py
from enum import Enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Index
from sqlalchemy.dialects.postgresql import ENUM as SQLEnum

from app import db
from app.utils.timezone import now, utc_to_china


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class UnifiedLog(db.Model):
    """统一日志表"""
    
    __tablename__ = "unified_logs"
    
    # 主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 日志时间戳 (UTC)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # 日志级别
    level = Column(SQLEnum(LogLevel, name="log_level"), nullable=False, index=True)
    
    # 模块/组件名
    module = Column(String(100), nullable=False, index=True)
    
    # 日志消息
    message = Column(Text, nullable=False)
    
    # 错误堆栈追踪 (仅ERROR/CRITICAL)
    traceback = Column(Text, nullable=True)
    
    # 附加上下文 (JSON格式)
    context = Column(JSON, nullable=True)
    
    # 记录创建时间
    created_at = Column(DateTime(timezone=True), default=now, nullable=False)
    
    # 复合索引优化查询性能
    __table_args__ = (
        Index("idx_timestamp_level_module", "timestamp", "level", "module"),
        Index("idx_timestamp_module", "timestamp", "module"),
        Index("idx_level_timestamp", "level", "timestamp"),
    )
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        # 将UTC时间转换为东八区时间显示
        china_timestamp = utc_to_china(self.timestamp)
        china_created_at = utc_to_china(self.created_at) if self.created_at else None
        
        return {
            "id": self.id,
            "timestamp": china_timestamp.isoformat() if china_timestamp else None,
            "level": self.level.value if self.level else None,
            "module": self.module,
            "message": self.message,
            "traceback": self.traceback,
            "context": self.context,
            "created_at": china_created_at.isoformat() if china_created_at else None,
        }
    
    @classmethod
    def create_log_entry(
        cls,
        level: LogLevel,
        module: str,
        message: str,
        traceback: str = None,
        context: dict = None,
        timestamp: datetime = None,
    ) -> "UnifiedLog":
        """创建日志条目"""
        return cls(
            level=level,
            module=module,
            message=message,
            traceback=traceback,
            context=context,
            timestamp=timestamp or now()
        )
```

#### 4.1.2 日志类型枚举
```python
# app/utils/logging_config.py
from enum import Enum
from dataclasses import dataclass
from typing import Any, Dict
from pathlib import Path
import os


class LogType(Enum):
    """日志类型枚举"""
    APP = "app"
    ERROR = "error"
    ACCESS = "access"
    SECURITY = "security"
    DATABASE = "database"
    TASK = "task"
    STRUCTURED = "structured"


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogConfig:
    """日志配置类"""
    
    # 基础配置
    app_name: str = "whalefall"
    log_dir: str = "userdata/logs"
    level: LogLevel = LogLevel.INFO
    
    # 文件配置
    max_file_size: str = "10 MB"
    retention_days: int = 30
    compression: str = "zip"
    
    # 性能配置
    enqueue: bool = True  # 异步写入
    backtrace: bool = True
    diagnose: bool = True
    
    # 格式配置
    console_format: str = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    file_format: str = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}"
    
    # 各类型日志配置
    log_types: Dict[LogType, Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.log_types is None:
            self.log_types = {
                LogType.APP: {
                    "rotation": "1 day",
                    "retention": f"{self.retention_days} days",
                    "compression": self.compression,
                    "serialize": True,
                },
                LogType.ERROR: {
                    "rotation": "1 day",
                    "retention": f"{self.retention_days} days",
                    "compression": self.compression,
                    "serialize": True,
                },
                LogType.ACCESS: {
                    "rotation": "1 day",
                    "retention": f"{self.retention_days} days",
                    "compression": self.compression,
                    "serialize": True,
                },
                LogType.SECURITY: {
                    "rotation": "1 day",
                    "retention": f"{self.retention_days} days",
                    "compression": self.compression,
                    "serialize": True,
                },
                LogType.DATABASE: {
                    "rotation": "1 day",
                    "retention": f"{self.retention_days} days",
                    "compression": self.compression,
                    "serialize": True,
                },
                LogType.TASK: {
                    "rotation": "1 day",
                    "retention": f"{self.retention_days} days",
                    "compression": self.compression,
                    "serialize": True,
                },
                LogType.STRUCTURED: {
                    "rotation": "1 day",
                    "retention": f"{self.retention_days} days",
                    "compression": self.compression,
                    "serialize": True,
                },
            }
```

### 4.2 服务层

#### 4.2.1 日志配置管理器
```python
# app/utils/logging_config.py
class LoggingConfigManager:
    """日志配置管理器"""
    
    def __init__(self):
        self.config = self._load_config()
    
    def _load_config(self) -> LogConfig:
        """从环境变量加载配置"""
        return LogConfig(
            app_name=os.getenv("LOG_APP_NAME", "whalefall"),
            log_dir=os.getenv("LOG_DIR", "userdata/logs"),
            level=LogLevel(os.getenv("LOG_LEVEL", "INFO")),
            max_file_size=os.getenv("LOG_MAX_FILE_SIZE", "10 MB"),
            retention_days=int(os.getenv("LOG_RETENTION_DAYS", "30")),
            compression=os.getenv("LOG_COMPRESSION", "zip"),
            enqueue=os.getenv("LOG_ENQUEUE", "true").lower() == "true",
            backtrace=os.getenv("LOG_BACKTRACE", "true").lower() == "true",
            diagnose=os.getenv("LOG_DIAGNOSE", "true").lower() == "true",
        )
    
    def get_log_file_path(self, log_type: LogType) -> Path:
        """获取日志文件路径"""
        log_dir = Path(self.config.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        file_mapping = {
            LogType.APP: "app.log",
            LogType.ERROR: "error.log",
            LogType.ACCESS: "access.log",
            LogType.SECURITY: "security.log",
            LogType.DATABASE: "database.log",
            LogType.TASK: "tasks.log",
            LogType.STRUCTURED: "structured.log",
        }
        
        return log_dir / file_mapping[log_type]
    
    def get_log_config(self, log_type: LogType) -> Dict[str, Any]:
        """获取指定类型的日志配置"""
        base_config = {
            "format": self.config.file_format,
            "level": self.config.level.value,
            "enqueue": self.config.enqueue,
            "backtrace": self.config.backtrace,
            "diagnose": self.config.diagnose,
        }
        
        type_config = self.config.log_types.get(log_type, {})
        base_config.update(type_config)
        
        return base_config
    
    def is_development(self) -> bool:
        """判断是否为开发环境"""
        return os.getenv("FLASK_ENV", "development") == "development"
```

#### 4.2.2 结构化日志处理器
```python
# app/utils/structlog_config.py
import structlog
from typing import Any, Dict
from flask import current_app, has_request_context
from app import db
from app.models.unified_log import UnifiedLog, LogLevel
from app.utils.time_utils import time_utils


class SQLAlchemyLogHandler:
    """SQLAlchemy 日志处理器"""
    
    def __init__(self, batch_size: int = 100, flush_interval: float = 5.0):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._shutdown = False
        
        # 启动后台线程处理日志
        import threading
        self._thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._thread.start()
    
    def __call__(self, logger, method_name, event_dict):
        """处理日志事件"""
        if self._shutdown:
            return event_dict
        
        # 过滤DEBUG级别日志
        level = event_dict.get("level", "INFO")
        level_priority = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
        
        # 如果级别低于INFO，则丢弃日志
        if level_priority.get(level, 20) < 20:  # INFO级别
            raise structlog.DropEvent
        
        # 构建日志条目
        log_entry = self._build_log_entry(event_dict)
        if log_entry:
            # 直接同步写入数据库
            try:
                # 检查是否有应用上下文
                if has_request_context() or current_app:
                    with current_app.app_context():
                        # 确保时间戳是datetime对象，使用东八区时间
                        if isinstance(log_entry.get("timestamp"), str):
                            from datetime import datetime
                            try:
                                log_entry["timestamp"] = datetime.fromisoformat(
                                    log_entry["timestamp"].replace("Z", "+00:00")
                                )
                            except ValueError:
                                log_entry["timestamp"] = time_utils.now()
                        
                        # 创建并保存日志条目
                        unified_log = UnifiedLog.create_log_entry(**log_entry)
                        db.session.add(unified_log)
                        db.session.commit()
                else:
                    # 如果没有应用上下文，跳过数据库写入
                    pass
            except Exception:
                # 使用标准logging避免循环依赖
                import logging
                logging.error("Error writing log to database: {e}")
        
        return event_dict
    
    def _build_log_entry(self, event_dict: Dict[str, Any]) -> Dict[str, Any] | None:
        """构建日志条目"""
        try:
            # 提取基本信息
            level = event_dict.get("level", "INFO")
            message = event_dict.get("event", "")
            module = event_dict.get("module", "unknown")
            timestamp = event_dict.get("timestamp", time_utils.now())
            
            # 提取上下文信息
            context = {}
            for key, value in event_dict.items():
                if key not in ["level", "event", "module", "timestamp", "logger"]:
                    context[key] = value
            
            # 提取堆栈追踪
            traceback = None
            if "exception" in event_dict:
                import traceback as tb
                traceback = tb.format_exc()
            
            return {
                "level": LogLevel(level),
                "module": module,
                "message": str(message),
                "traceback": traceback,
                "context": context if context else None,
                "timestamp": timestamp,
            }
        except Exception:
            return None
    
    def _flush_loop(self):
        """后台刷新循环"""
        import time
        while not self._shutdown:
            time.sleep(self.flush_interval)
            # 这里可以实现批量处理逻辑
    
    def shutdown(self):
        """关闭处理器"""
        self._shutdown = True
        if self._thread.is_alive():
            self._thread.join(timeout=5.0)


def configure_structlog():
    """配置结构化日志"""
    # 配置structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            SQLAlchemyLogHandler(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
```

### 4.3 路由层

#### 4.3.1 日志管理路由
```python
# app/routes/unified_logs.py
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, desc, asc
from sqlalchemy.orm import Query

from app import db
from app.models.unified_log import UnifiedLog, LogLevel
from app.utils.api_response import APIResponse
from app.utils.decorators import admin_required
from app.utils.structlog_config import log_info, log_error


# 创建蓝图
unified_logs_bp = Blueprint("unified_logs", __name__)


@unified_logs_bp.route("/")
@login_required
def logs_dashboard() -> str:
    """日志中心首页"""
    try:
        return render_template("unified_logs/dashboard.html")
    except Exception as e:
        log_error(f"加载日志中心失败: {str(e)}", module="unified_logs")
        return render_template("unified_logs/dashboard.html", error="页面加载失败")


@unified_logs_bp.route("/api/search")
@login_required
def search_logs() -> tuple[dict, int]:
    """搜索日志API"""
    try:
        # 获取查询参数
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        level = request.args.get("level", "").strip()
        module = request.args.get("module", "").strip()
        message = request.args.get("message", "").strip()
        start_date = request.args.get("start_date", "").strip()
        end_date = request.args.get("end_date", "").strip()
        
        # 构建查询
        query = UnifiedLog.query
        
        # 应用过滤条件
        filters = []
        
        if level:
            try:
                log_level = LogLevel(level)
                filters.append(UnifiedLog.level == log_level)
            except ValueError:
                pass
        
        if module:
            filters.append(UnifiedLog.module.ilike(f"%{module}%"))
        
        if message:
            filters.append(UnifiedLog.message.ilike(f"%{message}%"))
        
        if start_date:
            try:
                from datetime import datetime
                start_dt = datetime.fromisoformat(start_date)
                filters.append(UnifiedLog.timestamp >= start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                from datetime import datetime
                end_dt = datetime.fromisoformat(end_date)
                filters.append(UnifiedLog.timestamp <= end_dt)
            except ValueError:
                pass
        
        if filters:
            query = query.filter(and_(*filters))
        
        # 排序和分页
        query = query.order_by(desc(UnifiedLog.timestamp))
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # 转换为字典格式
        logs = [log.to_dict() for log in pagination.items]
        
        # 记录查询日志
        log_info(
            "日志查询",
            module="unified_logs",
            user_id=current_user.id,
            query_params={
                "level": level,
                "module": module,
                "message": message,
                "start_date": start_date,
                "end_date": end_date,
                "page": page,
                "per_page": per_page
            },
            result_count=len(logs)
        )
        
        return APIResponse.success({
            "logs": logs,
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_prev": pagination.has_prev,
                "has_next": pagination.has_next,
                "prev_num": pagination.prev_num,
                "next_num": pagination.next_num,
            }
        })
        
    except Exception as e:
        log_error(f"搜索日志失败: {str(e)}", module="unified_logs")
        return APIResponse.error(f"搜索日志失败: {str(e)}"), 500


@unified_logs_bp.route("/api/stats")
@login_required
def get_log_stats() -> tuple[dict, int]:
    """获取日志统计信息API"""
    try:
        from sqlalchemy import func
        
        # 总日志数
        total_logs = UnifiedLog.query.count()
        
        # 按级别统计
        level_stats = db.session.query(
            UnifiedLog.level,
            func.count(UnifiedLog.id).label('count')
        ).group_by(UnifiedLog.level).all()
        
        level_counts = {level.value: count for level, count in level_stats}
        
        # 按模块统计（前10个）
        module_stats = db.session.query(
            UnifiedLog.module,
            func.count(UnifiedLog.id).label('count')
        ).group_by(UnifiedLog.module).order_by(
            func.count(UnifiedLog.id).desc()
        ).limit(10).all()
        
        module_counts = {module: count for module, count in module_stats}
        
        # 最近24小时日志数
        from datetime import datetime, timedelta
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_logs = UnifiedLog.query.filter(
            UnifiedLog.timestamp >= yesterday
        ).count()
        
        # 错误日志数（最近24小时）
        recent_errors = UnifiedLog.query.filter(
            and_(
                UnifiedLog.timestamp >= yesterday,
                UnifiedLog.level.in_([LogLevel.ERROR, LogLevel.CRITICAL])
            )
        ).count()
        
        stats = {
            "total_logs": total_logs,
            "level_counts": level_counts,
            "module_counts": module_counts,
            "recent_logs": recent_logs,
            "recent_errors": recent_errors,
        }
        
        return APIResponse.success(stats)
        
    except Exception as e:
        log_error(f"获取日志统计失败: {str(e)}", module="unified_logs")
        return APIResponse.error(f"获取日志统计失败: {str(e)}"), 500


@unified_logs_bp.route("/api/clear", methods=["POST"])
@login_required
@admin_required
def clear_logs() -> tuple[dict, int]:
    """清空日志API"""
    try:
        # 获取清空参数
        data = request.get_json() or {}
        older_than_days = data.get("older_than_days", 30)
        
        from datetime import datetime, timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        
        # 删除旧日志
        deleted_count = UnifiedLog.query.filter(
            UnifiedLog.timestamp < cutoff_date
        ).delete()
        
        db.session.commit()
        
        # 记录清空操作
        log_info(
            "清空日志",
            module="unified_logs",
            user_id=current_user.id,
            older_than_days=older_than_days,
            deleted_count=deleted_count
        )
        
        return APIResponse.success({
            "message": f"成功清空 {deleted_count} 条日志",
            "deleted_count": deleted_count
        })
        
    except Exception as e:
        log_error(f"清空日志失败: {str(e)}", module="unified_logs")
        return APIResponse.error(f"清空日志失败: {str(e)}"), 500


@unified_logs_bp.route("/api/<int:log_id>")
@login_required
def get_log_details(log_id: int) -> tuple[dict, int]:
    """获取日志详情API"""
    try:
        log = UnifiedLog.query.get_or_404(log_id)
        
        return APIResponse.success(log.to_dict())
        
    except Exception as e:
        log_error(f"获取日志详情失败: {str(e)}", module="unified_logs")
        return APIResponse.error(f"获取日志详情失败: {str(e)}"), 500
```

## 5. 配置管理

### 5.1 环境变量配置
```bash
# 日志配置
LOG_APP_NAME=whalefall
LOG_DIR=userdata/logs
LOG_LEVEL=INFO
LOG_MAX_FILE_SIZE=10 MB
LOG_RETENTION_DAYS=30
LOG_COMPRESSION=zip
LOG_ENQUEUE=true
LOG_BACKTRACE=true
LOG_DIAGNOSE=true
```

### 5.2 日志配置初始化
```python
# app/__init__.py
def configure_logging(app: Flask) -> None:
    """配置日志系统"""
    if not app.debug and not app.testing:
        # 创建日志目录
        log_dir = os.path.dirname(app.config["LOG_FILE"])
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 配置文件日志处理器
        file_handler = RotatingFileHandler(
            app.config["LOG_FILE"],
            maxBytes=app.config["LOG_MAX_SIZE"],
            backupCount=app.config["LOG_BACKUP_COUNT"],
        )
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]")
        )
        file_handler.setLevel(getattr(logging, app.config["LOG_LEVEL"]))
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(getattr(logging, app.config["LOG_LEVEL"]))
        app.logger.info("鲸落应用启动")
```

## 6. 性能优化

### 6.1 异步日志写入
- 使用loguru的异步写入机制
- 避免阻塞主业务线程
- 批量写入提高性能

### 6.2 数据库优化
- 创建复合索引优化查询性能
- 定期清理旧日志数据
- 使用分区表管理大量日志数据

### 6.3 缓存策略
- 缓存日志统计信息
- 缓存常用查询结果
- 使用Redis缓存热点数据

## 7. 安全考虑

### 7.1 敏感信息保护
- 不在日志中记录密码、令牌等敏感信息
- 对敏感数据进行脱敏处理
- 实现日志访问权限控制

### 7.2 日志完整性
- 使用数字签名确保日志完整性
- 防止日志被篡改
- 实现日志审计功能

## 8. 监控和告警

### 8.1 日志监控
- 监控错误日志数量
- 监控日志写入性能
- 监控存储空间使用

### 8.2 告警机制
- 错误日志数量超过阈值时告警
- 日志写入失败时告警
- 存储空间不足时告警

## 9. 维护和运维

### 9.1 日志轮转
- 按大小和时间轮转日志文件
- 自动压缩旧日志文件
- 定期清理过期日志

### 9.2 性能监控
- 监控日志写入性能
- 监控查询响应时间
- 优化慢查询

## 10. 扩展功能

### 10.1 日志分析
- 提供日志分析工具
- 支持日志模式识别
- 实现异常检测

### 10.2 可视化展示
- 提供日志趋势图表
- 支持实时日志流
- 实现日志仪表板

---

**注意**: 本文档描述了日志中心功能的完整技术实现，包括前端界面、后端服务、数据模型、配置管理等各个方面。该功能为鲸落系统提供了完整的日志管理能力，支持系统监控、问题诊断和审计需求。
