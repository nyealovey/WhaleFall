# 系统监控功能技术文档

## 1. 功能概述

### 1.1 功能描述
系统监控功能是鲸落系统的核心运维模块，负责实时监控系统资源使用情况、服务状态、性能指标等关键信息。该模块提供全面的系统健康监控、性能分析和告警通知功能，确保系统稳定运行。

### 1.2 主要特性
- **资源监控**：CPU、内存、磁盘使用率监控
- **服务监控**：数据库、Redis、应用服务状态监控
- **性能监控**：响应时间、吞吐量、并发数监控
- **实时告警**：资源超阈值自动告警
- **历史数据**：监控数据历史记录和趋势分析
- **可视化展示**：丰富的图表和仪表板展示
- **健康检查**：系统健康状态自动检查
- **自定义监控**：支持自定义监控指标

### 1.3 技术特点
- 基于psutil的系统资源监控
- 实时数据采集和存储
- 多维度性能分析
- 智能告警机制
- 可视化图表展示

## 2. 技术架构

### 2.1 整体架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   数据采集层    │    │   数据处理层    │    │   展示层        │
│                 │    │                 │    │                 │
│ - 系统资源      │◄──►│ - 数据聚合      │◄──►│ - 监控仪表板    │
│ - 服务状态      │    │ - 告警分析      │    │ - 图表展示      │
│ - 性能指标      │    │ - 数据存储      │    │ - 告警通知      │
│ - 自定义指标    │    │ - 趋势分析      │    │ - 报告生成      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2.2 核心组件
- **监控采集器**：实时采集系统指标
- **数据处理引擎**：数据聚合和分析
- **告警引擎**：智能告警和通知
- **可视化引擎**：图表和仪表板展示

## 3. 前端实现

### 3.1 页面结构
- **主页面**：`app/templates/monitoring/dashboard.html`
- **样式文件**：`app/static/css/pages/monitoring/dashboard.css`
- **脚本文件**：`app/static/js/pages/monitoring/dashboard.js`

### 3.2 核心组件

#### 3.2.1 系统概览组件
```html
<!-- 系统监控仪表板 -->
<div class="container-fluid">
    <div class="row">
        <!-- 系统状态卡片 -->
        <div class="col-md-3">
            <div class="card bg-primary text-white">
                <div class="card-body">
                    <div class="d-flex justify-content-between">
                        <div>
                            <h4 class="card-title" id="cpu-usage">0%</h4>
                            <p class="card-text">CPU使用率</p>
                        </div>
                        <div class="align-self-center">
                            <i class="fas fa-microchip fa-2x"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-md-3">
            <div class="card bg-success text-white">
                <div class="card-body">
                    <div class="d-flex justify-content-between">
                        <div>
                            <h4 class="card-title" id="memory-usage">0%</h4>
                            <p class="card-text">内存使用率</p>
                        </div>
                        <div class="align-self-center">
                            <i class="fas fa-memory fa-2x"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-md-3">
            <div class="card bg-warning text-white">
                <div class="card-body">
                    <div class="d-flex justify-content-between">
                        <div>
                            <h4 class="card-title" id="disk-usage">0%</h4>
                            <p class="card-text">磁盘使用率</p>
                        </div>
                        <div class="align-self-center">
                            <i class="fas fa-hdd fa-2x"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-md-3">
            <div class="card bg-info text-white">
                <div class="card-body">
                    <div class="d-flex justify-content-between">
                        <div>
                            <h4 class="card-title" id="uptime">0天</h4>
                            <p class="card-text">系统运行时间</p>
                        </div>
                        <div class="align-self-center">
                            <i class="fas fa-clock fa-2x"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- 服务状态监控 -->
    <div class="row mt-4">
        <div class="col-12">
            <div class="card">
                <div class="card-header">
                    <h5 class="card-title mb-0">
                        <i class="fas fa-server me-2"></i>服务状态监控
                    </h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-4">
                            <div class="d-flex align-items-center mb-3">
                                <span class="status-indicator" id="db-indicator"></span>
                                <div class="ms-3">
                                    <h6 class="mb-0">数据库</h6>
                                    <small class="text-muted" id="db-status">检查中...</small>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="d-flex align-items-center mb-3">
                                <span class="status-indicator" id="redis-indicator"></span>
                                <div class="ms-3">
                                    <h6 class="mb-0">Redis缓存</h6>
                                    <small class="text-muted" id="redis-status">检查中...</small>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="d-flex align-items-center mb-3">
                                <span class="status-indicator" id="app-indicator"></span>
                                <div class="ms-3">
                                    <h6 class="mb-0">应用服务</h6>
                                    <small class="text-muted" id="app-status">运行中</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- 性能图表 -->
    <div class="row mt-4">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h5 class="card-title mb-0">
                        <i class="fas fa-chart-line me-2"></i>CPU使用率趋势
                    </h5>
                </div>
                <div class="card-body">
                    <canvas id="cpu-chart" height="200"></canvas>
                </div>
            </div>
        </div>
        
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h5 class="card-title mb-0">
                        <i class="fas fa-chart-area me-2"></i>内存使用率趋势
                    </h5>
                </div>
                <div class="card-body">
                    <canvas id="memory-chart" height="200"></canvas>
                </div>
            </div>
        </div>
    </div>
</div>
```

### 3.3 JavaScript实现

#### 3.3.1 监控数据管理器
```javascript
// 系统监控数据管理器
class SystemMonitoringManager {
    constructor() {
        this.refreshInterval = 5000; // 5秒刷新一次
        this.chartData = {
            cpu: [],
            memory: [],
            disk: []
        };
        this.maxDataPoints = 20; // 最多显示20个数据点
        this.charts = {};
        
        this.init();
    }
    
    init() {
        this.initCharts();
        this.startMonitoring();
        this.bindEvents();
    }
    
    initCharts() {
        // 初始化CPU图表
        const cpuCtx = document.getElementById('cpu-chart').getContext('2d');
        this.charts.cpu = new Chart(cpuCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'CPU使用率 (%)',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
        
        // 初始化内存图表
        const memoryCtx = document.getElementById('memory-chart').getContext('2d');
        this.charts.memory = new Chart(memoryCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '内存使用率 (%)',
                    data: [],
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }
    
    startMonitoring() {
        // 立即执行一次
        this.updateSystemStatus();
        
        // 定时更新
        setInterval(() => {
            this.updateSystemStatus();
        }, this.refreshInterval);
    }
    
    async updateSystemStatus() {
        try {
            const response = await fetch('/api/monitoring/status');
            const data = await response.json();
            
            if (data.success) {
                this.updateSystemOverview(data.data);
                this.updateServiceStatus(data.data);
                this.updateCharts(data.data);
            } else {
                this.showError('获取系统状态失败');
            }
        } catch (error) {
            console.error('更新系统状态失败:', error);
            this.showError('网络错误，请稍后重试');
        }
    }
    
    updateSystemOverview(data) {
        // 更新CPU使用率
        const cpuUsage = data.system.cpu;
        document.getElementById('cpu-usage').textContent = `${cpuUsage.toFixed(1)}%`;
        this.updateCardColor('cpu-usage', cpuUsage, 80, 90);
        
        // 更新内存使用率
        const memoryUsage = data.system.memory.percent;
        document.getElementById('memory-usage').textContent = `${memoryUsage.toFixed(1)}%`;
        this.updateCardColor('memory-usage', memoryUsage, 80, 90);
        
        // 更新磁盘使用率
        const diskUsage = data.system.disk.percent;
        document.getElementById('disk-usage').textContent = `${diskUsage.toFixed(1)}%`;
        this.updateCardColor('disk-usage', diskUsage, 80, 90);
        
        // 更新运行时间
        const uptime = data.uptime;
        document.getElementById('uptime').textContent = this.formatUptime(uptime);
    }
    
    updateServiceStatus(data) {
        const services = data.services;
        
        // 更新数据库状态
        this.updateServiceIndicator('db', services.database);
        
        // 更新Redis状态
        this.updateServiceIndicator('redis', services.redis);
        
        // 更新应用状态
        this.updateServiceIndicator('app', services.application);
    }
    
    updateServiceIndicator(serviceName, status) {
        const indicator = document.getElementById(`${serviceName}-indicator`);
        const statusText = document.getElementById(`${serviceName}-status`);
        
        if (status === 'healthy') {
            indicator.className = 'status-indicator bg-success';
            statusText.textContent = '正常';
        } else if (status === 'warning') {
            indicator.className = 'status-indicator bg-warning';
            statusText.textContent = '警告';
        } else {
            indicator.className = 'status-indicator bg-danger';
            statusText.textContent = '异常';
        }
    }
    
    updateCharts(data) {
        const now = new Date();
        const timeLabel = now.toLocaleTimeString();
        
        // 更新CPU图表
        this.updateChart('cpu', timeLabel, data.system.cpu);
        
        // 更新内存图表
        this.updateChart('memory', timeLabel, data.system.memory.percent);
    }
    
    updateChart(chartName, label, value) {
        const chart = this.charts[chartName];
        const data = chart.data;
        
        // 添加新数据点
        data.labels.push(label);
        data.datasets[0].data.push(value);
        
        // 保持最大数据点数量
        if (data.labels.length > this.maxDataPoints) {
            data.labels.shift();
            data.datasets[0].data.shift();
        }
        
        // 更新图表
        chart.update('none');
    }
    
    updateCardColor(elementId, value, warningThreshold, dangerThreshold) {
        const element = document.getElementById(elementId).closest('.card');
        
        // 移除现有颜色类
        element.classList.remove('bg-success', 'bg-warning', 'bg-danger');
        
        // 根据值设置颜色
        if (value >= dangerThreshold) {
            element.classList.add('bg-danger');
        } else if (value >= warningThreshold) {
            element.classList.add('bg-warning');
        } else {
            element.classList.add('bg-success');
        }
    }
    
    formatUptime(seconds) {
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        if (days > 0) {
            return `${days}天${hours}小时`;
        } else if (hours > 0) {
            return `${hours}小时${minutes}分钟`;
        } else {
            return `${minutes}分钟`;
        }
    }
    
    bindEvents() {
        // 手动刷新按钮
        document.getElementById('refresh-btn')?.addEventListener('click', () => {
            this.updateSystemStatus();
        });
        
        // 自动刷新开关
        document.getElementById('auto-refresh-toggle')?.addEventListener('change', (e) => {
            if (e.target.checked) {
                this.startMonitoring();
            } else {
                this.stopMonitoring();
            }
        });
    }
    
    stopMonitoring() {
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
            this.monitoringInterval = null;
        }
    }
    
    showError(message) {
        // 显示错误消息
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger alert-dismissible fade show position-fixed';
        alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alertDiv.innerHTML = `
            <i class="fas fa-exclamation-triangle me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// 初始化系统监控管理器
const systemMonitor = new SystemMonitoringManager();
```

## 4. 后端实现

### 4.1 监控服务
```python
# app/services/monitoring_service.py
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from app import db
from app.utils.structlog_config import log_info, log_error


class SystemMonitoringService:
    """系统监控服务"""
    
    @staticmethod
    def get_system_status() -> Dict[str, Any]:
        """获取系统状态"""
        try:
            # 系统资源状态
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            
            # 数据库状态
            db_status = SystemMonitoringService._check_database_health()
            
            # Redis状态
            redis_status = SystemMonitoringService._check_redis_health()
            
            # 应用状态
            app_status = "running"
            
            # 系统运行时间
            uptime = SystemMonitoringService._get_system_uptime()
            
            return {
                "system": {
                    "cpu": cpu_percent,
                    "memory": {
                        "used": memory.used,
                        "total": memory.total,
                        "percent": memory.percent,
                    },
                    "disk": {
                        "used": disk.used,
                        "total": disk.total,
                        "percent": (disk.used / disk.total) * 100,
                    },
                },
                "services": {
                    "database": db_status,
                    "redis": redis_status,
                    "application": app_status,
                },
                "uptime": uptime,
            }
            
        except Exception as e:
            log_error(f"获取系统状态失败: {str(e)}", module="monitoring")
            return {
                "system": {
                    "cpu": 0,
                    "memory": {"used": 0, "total": 0, "percent": 0},
                    "disk": {"used": 0, "total": 0, "percent": 0},
                },
                "services": {
                    "database": "error",
                    "redis": "error",
                    "application": "error",
                },
                "uptime": 0,
            }
    
    @staticmethod
    def _check_database_health() -> str:
        """检查数据库健康状态"""
        try:
            db.session.execute(text("SELECT 1"))
            return "healthy"
        except Exception:
            return "error"
    
    @staticmethod
    def _check_redis_health() -> str:
        """检查Redis健康状态"""
        try:
            from app.services.cache_manager_simple import simple_cache_manager
            
            if simple_cache_manager and simple_cache_manager.health_check():
                return "healthy"
            else:
                return "error"
        except Exception:
            return "error"
    
    @staticmethod
    def _get_system_uptime() -> int:
        """获取系统运行时间（秒）"""
        try:
            return int(time.time() - psutil.boot_time())
        except Exception:
            return 0
    
    @staticmethod
    def get_performance_metrics() -> Dict[str, Any]:
        """获取性能指标"""
        try:
            # CPU使用率历史
            cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
            cpu_avg = sum(cpu_percent) / len(cpu_percent)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            
            # 磁盘使用情况
            disk = psutil.disk_usage("/")
            
            # 网络IO
            network = psutil.net_io_counters()
            
            # 进程信息
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # 按CPU使用率排序
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            
            return {
                "cpu": {
                    "percent": cpu_avg,
                    "per_cpu": cpu_percent,
                    "count": psutil.cpu_count(),
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percent": memory.percent,
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100,
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv,
                },
                "processes": processes[:10],  # 前10个进程
            }
            
        except Exception as e:
            log_error(f"获取性能指标失败: {str(e)}", module="monitoring")
            return {}
    
    @staticmethod
    def check_alerts() -> List[Dict[str, Any]]:
        """检查告警条件"""
        alerts = []
        
        try:
            status = SystemMonitoringService.get_system_status()
            
            # CPU使用率告警
            cpu_percent = status["system"]["cpu"]
            if cpu_percent > 90:
                alerts.append({
                    "type": "cpu",
                    "level": "critical",
                    "message": f"CPU使用率过高: {cpu_percent:.1f}%",
                    "value": cpu_percent,
                    "threshold": 90,
                })
            elif cpu_percent > 80:
                alerts.append({
                    "type": "cpu",
                    "level": "warning",
                    "message": f"CPU使用率较高: {cpu_percent:.1f}%",
                    "value": cpu_percent,
                    "threshold": 80,
                })
            
            # 内存使用率告警
            memory_percent = status["system"]["memory"]["percent"]
            if memory_percent > 90:
                alerts.append({
                    "type": "memory",
                    "level": "critical",
                    "message": f"内存使用率过高: {memory_percent:.1f}%",
                    "value": memory_percent,
                    "threshold": 90,
                })
            elif memory_percent > 80:
                alerts.append({
                    "type": "memory",
                    "level": "warning",
                    "message": f"内存使用率较高: {memory_percent:.1f}%",
                    "value": memory_percent,
                    "threshold": 80,
                })
            
            # 磁盘使用率告警
            disk_percent = status["system"]["disk"]["percent"]
            if disk_percent > 90:
                alerts.append({
                    "type": "disk",
                    "level": "critical",
                    "message": f"磁盘使用率过高: {disk_percent:.1f}%",
                    "value": disk_percent,
                    "threshold": 90,
                })
            elif disk_percent > 80:
                alerts.append({
                    "type": "disk",
                    "level": "warning",
                    "message": f"磁盘使用率较高: {disk_percent:.1f}%",
                    "value": disk_percent,
                    "threshold": 80,
                })
            
            # 服务状态告警
            services = status["services"]
            for service_name, service_status in services.items():
                if service_status == "error":
                    alerts.append({
                        "type": "service",
                        "level": "critical",
                        "message": f"{service_name}服务异常",
                        "value": service_status,
                        "threshold": "healthy",
                    })
            
        except Exception as e:
            log_error(f"检查告警失败: {str(e)}", module="monitoring")
        
        return alerts
```

### 4.2 路由层
```python
# app/routes/monitoring.py
from flask import Blueprint, jsonify, render_template
from flask_login import login_required, current_user
from app.services.monitoring_service import SystemMonitoringService
from app.utils.api_response import APIResponse
from app.utils.decorators import admin_required
from app.utils.structlog_config import log_info, log_error


monitoring_bp = Blueprint("monitoring", __name__)


@monitoring_bp.route("/")
@login_required
@admin_required
def index() -> str:
    """系统监控首页"""
    try:
        return render_template("monitoring/dashboard.html")
    except Exception as e:
        log_error(f"加载监控页面失败: {str(e)}", module="monitoring")
        return render_template("monitoring/dashboard.html", error="页面加载失败")


@monitoring_bp.route("/api/status")
@login_required
@admin_required
def api_system_status() -> tuple[dict, int]:
    """获取系统状态API"""
    try:
        status = SystemMonitoringService.get_system_status()
        
        return APIResponse.success(status)
        
    except Exception as e:
        log_error(f"获取系统状态失败: {str(e)}", module="monitoring")
        return APIResponse.error(f"获取系统状态失败: {str(e)}"), 500


@monitoring_bp.route("/api/performance")
@login_required
@admin_required
def api_performance_metrics() -> tuple[dict, int]:
    """获取性能指标API"""
    try:
        metrics = SystemMonitoringService.get_performance_metrics()
        
        return APIResponse.success(metrics)
        
    except Exception as e:
        log_error(f"获取性能指标失败: {str(e)}", module="monitoring")
        return APIResponse.error(f"获取性能指标失败: {str(e)}"), 500


@monitoring_bp.route("/api/alerts")
@login_required
@admin_required
def api_check_alerts() -> tuple[dict, int]:
    """检查告警API"""
    try:
        alerts = SystemMonitoringService.check_alerts()
        
        return APIResponse.success({
            "alerts": alerts,
            "count": len(alerts)
        })
        
    except Exception as e:
        log_error(f"检查告警失败: {str(e)}", module="monitoring")
        return APIResponse.error(f"检查告警失败: {str(e)}"), 500
```

## 5. 配置管理

### 5.1 监控配置
```yaml
# app/config/monitoring_config.yaml
monitoring:
  # 监控间隔（秒）
  refresh_interval: 5
  
  # 告警阈值
  thresholds:
    cpu:
      warning: 80
      critical: 90
    memory:
      warning: 80
      critical: 90
    disk:
      warning: 80
      critical: 90
  
  # 数据保留
  retention:
    days: 30
    
  # 告警配置
  alerts:
    enabled: true
    email: true
    webhook: false
```

### 5.2 环境变量配置
```bash
# 监控配置
MONITORING_ENABLED=true
MONITORING_REFRESH_INTERVAL=5
MONITORING_RETENTION_DAYS=30
ALERT_EMAIL_ENABLED=true
ALERT_WEBHOOK_URL=
```

## 6. 性能优化

### 6.1 数据采集优化
- 使用异步数据采集
- 缓存监控数据
- 批量处理数据更新

### 6.2 前端优化
- 使用WebSocket实时更新
- 图表数据分页加载
- 防抖处理频繁更新

### 6.3 存储优化
- 使用时序数据库存储历史数据
- 数据压缩和归档
- 定期清理过期数据

## 7. 告警机制

### 7.1 告警规则
- CPU使用率超过阈值
- 内存使用率超过阈值
- 磁盘使用率超过阈值
- 服务状态异常

### 7.2 告警通知
- 邮件通知
- Webhook通知
- 系统内通知
- 短信通知（可选）

## 8. 扩展功能

### 8.1 自定义监控
- 支持自定义监控指标
- 自定义告警规则
- 监控脚本集成

### 8.2 报告生成
- 定期监控报告
- 性能分析报告
- 趋势分析报告

---

**注意**: 本文档描述了系统监控功能的完整技术实现，包括资源监控、服务监控、性能分析、告警机制等各个方面。该功能为鲸落系统提供了全面的监控能力，确保系统稳定运行和及时发现问题。
