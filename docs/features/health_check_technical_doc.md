# 健康检查功能技术文档

## 1. 功能概述

### 1.1 功能描述
健康检查功能是鲸落系统的运维监控模块，负责检查系统各组件的健康状态，包括数据库连接、Redis缓存、应用服务等。该模块提供实时健康状态监控、自动故障检测和健康报告生成功能。

### 1.2 主要特性
- **多组件检查**：数据库、Redis、应用服务健康检查
- **实时监控**：持续监控系统健康状态
- **故障检测**：自动检测和报告系统故障
- **健康报告**：生成详细的健康状态报告
- **告警通知**：健康状态异常时自动告警
- **API接口**：提供健康检查API接口
- **容器支持**：支持Kubernetes等容器编排

### 1.3 技术特点
- 基于Flask的健康检查框架
- 多维度健康状态评估
- 自动故障恢复检测
- 容器就绪性检查

## 2. 技术架构

### 2.1 整体架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   检查器层      │    │   评估层        │    │   报告层        │
│                 │    │                 │    │                 │
│ - 数据库检查    │◄──►│ - 健康评估      │◄──►│ - 状态报告      │
│ - 缓存检查      │    │ - 故障检测      │    │ - 告警通知      │
│ - 服务检查      │    │ - 性能分析      │    │ - API响应       │
│ - 资源检查      │    │ - 风险评估      │    │ - 日志记录      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2.2 核心组件
- **健康检查器**：各组件健康状态检查
- **评估引擎**：健康状态综合评估
- **告警系统**：异常状态告警通知
- **报告生成器**：健康状态报告生成

## 3. 后端实现

### 3.1 健康检查服务
```python
# app/services/health_check_service.py
import psutil
import time
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy import text
from app import db
from app.utils.structlog_config import log_info, log_error


class HealthCheckService:
    """健康检查服务"""
    
    @staticmethod
    def check_database_health() -> Dict[str, Any]:
        """检查数据库健康状态"""
        try:
            start_time = time.time()
            db.session.execute(text("SELECT 1"))
            response_time = (time.time() - start_time) * 1000  # 毫秒
            
            return {
                "healthy": True,
                "status": "healthy",
                "response_time": round(response_time, 2),
                "message": "数据库连接正常"
            }
        except Exception as e:
            log_error(f"数据库健康检查失败: {str(e)}", module="health_check")
            return {
                "healthy": False,
                "status": "error",
                "response_time": None,
                "message": f"数据库连接失败: {str(e)}"
            }
    
    @staticmethod
    def check_redis_health() -> Dict[str, Any]:
        """检查Redis健康状态"""
        try:
            from app.services.cache_manager_simple import simple_cache_manager
            
            if not simple_cache_manager:
                return {
                    "healthy": False,
                    "status": "error",
                    "message": "Redis缓存管理器未初始化"
                }
            
            start_time = time.time()
            health_check = simple_cache_manager.health_check()
            response_time = (time.time() - start_time) * 1000
            
            if health_check:
                return {
                    "healthy": True,
                    "status": "healthy",
                    "response_time": round(response_time, 2),
                    "message": "Redis连接正常"
                }
            else:
                return {
                    "healthy": False,
                    "status": "error",
                    "response_time": round(response_time, 2),
                    "message": "Redis连接失败"
                }
        except Exception as e:
            log_error(f"Redis健康检查失败: {str(e)}", module="health_check")
            return {
                "healthy": False,
                "status": "error",
                "response_time": None,
                "message": f"Redis连接失败: {str(e)}"
            }
    
    @staticmethod
    def check_system_health() -> Dict[str, Any]:
        """检查系统资源健康状态"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 磁盘使用率
            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100
            
            # 判断是否健康
            healthy = all([
                cpu_percent < 90,  # CPU使用率低于90%
                memory_percent < 90,  # 内存使用率低于90%
                disk_percent < 90,  # 磁盘使用率低于90%
            ])
            
            return {
                "healthy": healthy,
                "status": "healthy" if healthy else "warning",
                "cpu_percent": round(cpu_percent, 2),
                "memory_percent": round(memory_percent, 2),
                "disk_percent": round(disk_percent, 2),
                "message": "系统资源正常" if healthy else "系统资源使用率较高"
            }
        except Exception as e:
            log_error(f"系统健康检查失败: {str(e)}", module="health_check")
            return {
                "healthy": False,
                "status": "error",
                "message": f"系统健康检查失败: {str(e)}"
            }
    
    @staticmethod
    def check_application_health() -> Dict[str, Any]:
        """检查应用健康状态"""
        try:
            # 检查应用是否正常运行
            app_status = "running"
            
            # 检查关键服务
            services_status = {
                "database": HealthCheckService.check_database_health(),
                "redis": HealthCheckService.check_redis_health(),
                "system": HealthCheckService.check_system_health()
            }
            
            # 综合评估应用健康状态
            all_healthy = all(service["healthy"] for service in services_status.values())
            
            return {
                "healthy": all_healthy,
                "status": "healthy" if all_healthy else "warning",
                "services": services_status,
                "message": "应用运行正常" if all_healthy else "应用存在异常"
            }
        except Exception as e:
            log_error(f"应用健康检查失败: {str(e)}", module="health_check")
            return {
                "healthy": False,
                "status": "error",
                "message": f"应用健康检查失败: {str(e)}"
            }
    
    @staticmethod
    def get_overall_health() -> Dict[str, Any]:
        """获取整体健康状态"""
        try:
            # 执行各项健康检查
            database_health = HealthCheckService.check_database_health()
            redis_health = HealthCheckService.check_redis_health()
            system_health = HealthCheckService.check_system_health()
            app_health = HealthCheckService.check_application_health()
            
            # 计算整体健康状态
            all_healthy = all([
                database_health["healthy"],
                redis_health["healthy"],
                system_health["healthy"],
                app_health["healthy"]
            ])
            
            # 确定状态级别
            if all_healthy:
                overall_status = "healthy"
            elif any(service["status"] == "error" for service in [database_health, redis_health, system_health, app_health]):
                overall_status = "error"
            else:
                overall_status = "warning"
            
            return {
                "healthy": all_healthy,
                "status": overall_status,
                "timestamp": datetime.utcnow().isoformat(),
                "components": {
                    "database": database_health,
                    "redis": redis_health,
                    "system": system_health,
                    "application": app_health
                },
                "summary": {
                    "total_checks": 4,
                    "healthy_checks": sum(1 for service in [database_health, redis_health, system_health, app_health] if service["healthy"]),
                    "unhealthy_checks": sum(1 for service in [database_health, redis_health, system_health, app_health] if not service["healthy"])
                }
            }
        except Exception as e:
            log_error(f"获取整体健康状态失败: {str(e)}", module="health_check")
            return {
                "healthy": False,
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"健康检查失败: {str(e)}",
                "components": {},
                "summary": {"total_checks": 0, "healthy_checks": 0, "unhealthy_checks": 0}
            }
```

### 3.2 健康检查路由
```python
# app/routes/health.py
from flask import Blueprint, jsonify, Response
from app.services.health_check_service import HealthCheckService
from app.utils.structlog_config import log_info, log_error


health_bp = Blueprint("health", __name__)


@health_bp.route("/health")
def health_check() -> Response:
    """基础健康检查"""
    try:
        health_status = HealthCheckService.get_overall_health()
        
        if health_status["healthy"]:
            return jsonify(health_status), 200
        else:
            return jsonify(health_status), 503
            
    except Exception as e:
        log_error(f"健康检查失败: {str(e)}", module="health_check")
        return jsonify({
            "healthy": False,
            "status": "error",
            "message": f"健康检查失败: {str(e)}"
        }), 500


@health_bp.route("/health/liveness")
def liveness_check() -> Response:
    """存活检查 - 用于Kubernetes等容器编排"""
    try:
        # 简单的存活检查，只检查应用是否在运行
        return jsonify({
            "healthy": True,
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        log_error(f"存活检查失败: {str(e)}", module="health_check")
        return jsonify({
            "healthy": False,
            "status": "dead",
            "message": f"存活检查失败: {str(e)}"
        }), 500


@health_bp.route("/health/readiness")
def readiness_check() -> Response:
    """就绪检查 - 用于Kubernetes等容器编排"""
    try:
        # 检查应用是否准备好接收请求
        database_health = HealthCheckService.check_database_health()
        redis_health = HealthCheckService.check_redis_health()
        
        ready = database_health["healthy"] and redis_health["healthy"]
        
        if ready:
            return jsonify({
                "ready": True,
                "status": "ready",
                "timestamp": datetime.utcnow().isoformat()
            }), 200
        else:
            return jsonify({
                "ready": False,
                "status": "not_ready",
                "timestamp": datetime.utcnow().isoformat(),
                "message": "应用未就绪"
            }), 503
            
    except Exception as e:
        log_error(f"就绪检查失败: {str(e)}", module="health_check")
        return jsonify({
            "ready": False,
            "status": "error",
            "message": f"就绪检查失败: {str(e)}"
        }), 500


@health_bp.route("/health/detailed")
def detailed_health_check() -> Response:
    """详细健康检查"""
    try:
        health_status = HealthCheckService.get_overall_health()
        
        # 记录健康检查日志
        log_info(
            "详细健康检查",
            module="health_check",
            healthy=health_status["healthy"],
            status=health_status["status"]
        )
        
        return jsonify(health_status)
        
    except Exception as e:
        log_error(f"详细健康检查失败: {str(e)}", module="health_check")
        return jsonify({
            "healthy": False,
            "status": "error",
            "message": f"详细健康检查失败: {str(e)}"
        }), 500
```

## 4. 配置管理

### 4.1 健康检查配置
```yaml
# app/config/health_check_config.yaml
health_check:
  # 检查间隔（秒）
  check_interval: 30
  
  # 超时时间（秒）
  timeout: 10
  
  # 重试次数
  retry_count: 3
  
  # 告警阈值
  thresholds:
    cpu_percent: 90
    memory_percent: 90
    disk_percent: 90
    response_time: 5000  # 毫秒
  
  # 告警配置
  alerts:
    enabled: true
    email: true
    webhook: false
```

### 4.2 环境变量配置
```bash
# 健康检查配置
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30
HEALTH_CHECK_TIMEOUT=10
HEALTH_ALERT_ENABLED=true
```

## 5. 监控集成

### 5.1 Prometheus集成
```python
# app/utils/prometheus_metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# 健康检查指标
health_check_total = Counter('health_check_total', 'Total health checks', ['component', 'status'])
health_check_duration = Histogram('health_check_duration_seconds', 'Health check duration', ['component'])
system_cpu_usage = Gauge('system_cpu_usage_percent', 'CPU usage percentage')
system_memory_usage = Gauge('system_memory_usage_percent', 'Memory usage percentage')
system_disk_usage = Gauge('system_disk_usage_percent', 'Disk usage percentage')

@health_bp.route("/metrics")
def metrics():
    """Prometheus指标端点"""
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}
```

### 5.2 容器健康检查
```dockerfile
# Dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1
```

## 6. 告警机制

### 6.1 告警规则
- 数据库连接失败
- Redis连接失败
- 系统资源使用率过高
- 应用响应时间过长

### 6.2 告警通知
- 邮件通知
- Webhook通知
- 系统日志记录
- 监控系统集成

## 7. 性能优化

### 7.1 检查优化
- 异步健康检查
- 缓存检查结果
- 批量检查操作

### 7.2 监控优化
- 减少检查频率
- 智能告警阈值
- 历史数据压缩

---

**注意**: 本文档描述了健康检查功能的完整技术实现，包括多组件检查、容器支持、监控集成等各个方面。该功能为鲸落系统提供了全面的健康监控能力，确保系统稳定运行。
