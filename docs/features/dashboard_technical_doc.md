# 仪表板功能技术文档

## 1. 功能概述

### 1.1 功能描述
仪表板功能是鲸落系统的核心展示模块，提供系统概览、关键指标展示、数据可视化等功能。该模块集成了系统监控、用户管理、数据库统计等多个功能模块的数据，为用户提供一站式的系统管理界面。

### 1.2 主要特性
- **系统概览**：展示系统整体运行状态和关键指标
- **数据可视化**：丰富的图表和统计信息展示
- **实时更新**：数据实时刷新和状态监控
- **个性化配置**：支持用户自定义仪表板布局
- **多维度统计**：用户、实例、任务、日志等多维度统计
- **趋势分析**：数据趋势分析和预测
- **快速操作**：常用功能的快速访问入口

### 1.3 技术特点
- 基于Bootstrap的响应式设计
- Chart.js图表可视化
- 实时数据更新
- 模块化组件设计

## 2. 技术架构

### 2.1 整体架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   数据层        │    │   业务层        │    │   展示层        │
│                 │    │                 │    │                 │
│ - 系统数据      │◄──►│ - 数据聚合      │◄──►│ - 仪表板组件    │
│ - 用户数据      │    │ - 统计分析      │    │ - 图表组件      │
│ - 实例数据      │    │ - 实时更新      │    │ - 状态组件      │
│ - 任务数据      │    │ - 缓存管理      │    │ - 操作组件      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2.2 核心组件
- **数据聚合器**：整合多模块数据
- **图表引擎**：数据可视化处理
- **实时更新器**：数据实时刷新
- **布局管理器**：仪表板布局管理

## 3. 前端实现

### 3.1 页面结构
- **主页面**：`app/templates/dashboard/overview.html`
- **样式文件**：`app/static/css/pages/dashboard/overview.css`
- **脚本文件**：`app/static/js/pages/dashboard/overview.js`

### 3.2 核心组件

#### 3.2.1 系统概览卡片
```html
<!-- 系统概览卡片 -->
<div class="row mb-4">
    <div class="col-md-3">
        <div class="card bg-primary text-white">
            <div class="card-body">
                <div class="d-flex justify-content-between">
                    <div>
                        <h4 class="card-title" id="total-users">0</h4>
                        <p class="card-text">总用户数</p>
                    </div>
                    <div class="align-self-center">
                        <i class="fas fa-users fa-2x"></i>
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
                        <h4 class="card-title" id="total-instances">0</h4>
                        <p class="card-text">数据库实例</p>
                    </div>
                    <div class="align-self-center">
                        <i class="fas fa-database fa-2x"></i>
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
                        <h4 class="card-title" id="active-tasks">0</h4>
                        <p class="card-text">活跃任务</p>
                    </div>
                    <div class="align-self-center">
                        <i class="fas fa-tasks fa-2x"></i>
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
                        <h4 class="card-title" id="total-logs">0</h4>
                        <p class="card-text">日志总数</p>
                    </div>
                    <div class="align-self-center">
                        <i class="fas fa-file-alt fa-2x"></i>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
```

#### 3.2.2 系统状态监控
```html
<!-- 系统状态监控 -->
<div class="row mb-4">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5 class="card-title mb-0">
                    <i class="fas fa-server me-2"></i>系统状态
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
    
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5 class="card-title mb-0">
                    <i class="fas fa-chart-pie me-2"></i>资源使用率
                </h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-4">
                        <div class="text-center">
                            <h6>CPU使用率</h6>
                            <div class="progress mb-2" style="height: 20px;">
                                <div class="progress-bar" id="cpu-progress" role="progressbar" style="width: 0%">0%</div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="text-center">
                            <h6>内存使用率</h6>
                            <div class="progress mb-2" style="height: 20px;">
                                <div class="progress-bar" id="memory-progress" role="progressbar" style="width: 0%">0%</div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="text-center">
                            <h6>磁盘使用率</h6>
                            <div class="progress mb-2" style="height: 20px;">
                                <div class="progress-bar" id="disk-progress" role="progressbar" style="width: 0%">0%</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
```

#### 3.2.3 数据图表
```html
<!-- 数据图表 -->
<div class="row mb-4">
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5 class="card-title mb-0">
                    <i class="fas fa-chart-line me-2"></i>用户增长趋势
                </h5>
            </div>
            <div class="card-body">
                <canvas id="user-growth-chart" height="200"></canvas>
            </div>
        </div>
    </div>
    
    <div class="col-md-6">
        <div class="card">
            <div class="card-header">
                <h5 class="card-title mb-0">
                    <i class="fas fa-chart-bar me-2"></i>数据库类型分布
                </h5>
            </div>
            <div class="card-body">
                <canvas id="database-type-chart" height="200"></canvas>
            </div>
        </div>
    </div>
</div>
```

### 3.3 JavaScript实现

#### 3.3.1 仪表板管理器
```javascript
// 仪表板管理器
class DashboardManager {
    constructor() {
        this.refreshInterval = 30000; // 30秒刷新一次
        this.charts = {};
        this.timer = null;
        
        this.init();
    }
    
    init() {
        this.initCharts();
        this.loadDashboardData();
        this.startAutoRefresh();
        this.bindEvents();
    }
    
    initCharts() {
        // 初始化用户增长趋势图
        this.initUserGrowthChart();
        
        // 初始化数据库类型分布图
        this.initDatabaseTypeChart();
    }
    
    initUserGrowthChart() {
        const ctx = document.getElementById('user-growth-chart').getContext('2d');
        this.charts.userGrowth = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '用户数量',
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
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    initDatabaseTypeChart() {
        const ctx = document.getElementById('database-type-chart').getContext('2d');
        this.charts.databaseType = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(255, 205, 86, 0.8)',
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(153, 102, 255, 0.8)'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
    
    async loadDashboardData() {
        try {
            const response = await fetch('/dashboard/api/overview');
            const data = await response.json();
            
            if (data.success) {
                this.updateOverviewCards(data.data);
                this.updateSystemStatus(data.data);
                this.updateCharts(data.data);
            } else {
                this.showError('加载仪表板数据失败');
            }
        } catch (error) {
            console.error('加载仪表板数据失败:', error);
            this.showError('网络错误，请稍后重试');
        }
    }
    
    updateOverviewCards(data) {
        // 更新用户数
        document.getElementById('total-users').textContent = data.total_users || 0;
        
        // 更新实例数
        document.getElementById('total-instances').textContent = data.total_instances || 0;
        
        // 更新任务数
        document.getElementById('active-tasks').textContent = data.active_tasks || 0;
        
        // 更新日志数
        document.getElementById('total-logs').textContent = data.total_logs || 0;
    }
    
    updateSystemStatus(data) {
        // 更新数据库状态
        this.updateServiceIndicator('db', data.status?.services?.database);
        
        // 更新Redis状态
        this.updateServiceIndicator('redis', data.status?.services?.redis);
        
        // 更新应用状态
        this.updateServiceIndicator('app', data.status?.services?.application);
        
        // 更新资源使用率
        this.updateResourceUsage('cpu', data.status?.system?.cpu);
        this.updateResourceUsage('memory', data.status?.system?.memory?.percent);
        this.updateResourceUsage('disk', data.status?.system?.disk?.percent);
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
    
    updateResourceUsage(type, percent) {
        const progressBar = document.getElementById(`${type}-progress`);
        if (progressBar) {
            progressBar.style.width = `${percent}%`;
            progressBar.textContent = `${percent.toFixed(1)}%`;
            
            // 根据使用率设置颜色
            if (percent > 90) {
                progressBar.className = 'progress-bar bg-danger';
            } else if (percent > 80) {
                progressBar.className = 'progress-bar bg-warning';
            } else {
                progressBar.className = 'progress-bar bg-success';
            }
        }
    }
    
    updateCharts(data) {
        // 更新用户增长趋势图
        if (data.charts?.userGrowth) {
            this.updateUserGrowthChart(data.charts.userGrowth);
        }
        
        // 更新数据库类型分布图
        if (data.charts?.databaseType) {
            this.updateDatabaseTypeChart(data.charts.databaseType);
        }
    }
    
    updateUserGrowthChart(data) {
        const chart = this.charts.userGrowth;
        chart.data.labels = data.labels;
        chart.data.datasets[0].data = data.values;
        chart.update();
    }
    
    updateDatabaseTypeChart(data) {
        const chart = this.charts.databaseType;
        chart.data.labels = data.labels;
        chart.data.datasets[0].data = data.values;
        chart.update();
    }
    
    startAutoRefresh() {
        this.timer = setInterval(() => {
            this.loadDashboardData();
        }, this.refreshInterval);
    }
    
    stopAutoRefresh() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
    }
    
    bindEvents() {
        // 手动刷新按钮
        document.getElementById('refresh-btn')?.addEventListener('click', () => {
            this.loadDashboardData();
        });
        
        // 自动刷新开关
        document.getElementById('auto-refresh-toggle')?.addEventListener('change', (e) => {
            if (e.target.checked) {
                this.startAutoRefresh();
            } else {
                this.stopAutoRefresh();
            }
        });
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

// 初始化仪表板管理器
const dashboardManager = new DashboardManager();
```

## 4. 后端实现

### 4.1 仪表板服务
```python
# app/services/dashboard_service.py
from typing import Dict, Any
from sqlalchemy import text, func
from app import db
from app.models.user import User
from app.models.instance import Instance
from app.models.unified_log import UnifiedLog
from app.utils.structlog_config import log_info, log_error


class DashboardService:
    """仪表板服务"""
    
    @staticmethod
    def get_system_overview() -> Dict[str, Any]:
        """获取系统概览数据"""
        try:
            # 基础统计
            total_users = User.query.count()
            total_instances = Instance.query.count()
            
            # 从APScheduler获取任务统计
            try:
                result = db.session.execute(text("SELECT COUNT(*) FROM apscheduler_jobs"))
                total_tasks = result.scalar() or 0
                result = db.session.execute(text("SELECT COUNT(*) FROM apscheduler_jobs WHERE next_run_time IS NOT NULL"))
                active_tasks = result.scalar() or 0
            except Exception:
                total_tasks = 0
                active_tasks = 0
            
            total_logs = UnifiedLog.query.count()
            
            return {
                "total_users": total_users,
                "total_instances": total_instances,
                "total_tasks": total_tasks,
                "active_tasks": active_tasks,
                "total_logs": total_logs
            }
            
        except Exception as e:
            log_error(f"获取系统概览失败: {str(e)}", module="dashboard")
            return {
                "total_users": 0,
                "total_instances": 0,
                "total_tasks": 0,
                "active_tasks": 0,
                "total_logs": 0
            }
    
    @staticmethod
    def get_system_status() -> Dict[str, Any]:
        """获取系统状态"""
        try:
            import psutil
            
            # 系统资源状态
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            
            # 数据库状态
            db_status = "healthy"
            try:
                db.session.execute(text("SELECT 1"))
            except Exception:
                db_status = "error"
            
            # Redis状态
            redis_status = "healthy"
            try:
                from app.services.cache_manager_simple import simple_cache_manager
                if not simple_cache_manager or not simple_cache_manager.health_check():
                    redis_status = "error"
            except Exception:
                redis_status = "error"
            
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
                    "application": "running",
                }
            }
            
        except Exception as e:
            log_error(f"获取系统状态失败: {str(e)}", module="dashboard")
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
                }
            }
    
    @staticmethod
    def get_chart_data() -> Dict[str, Any]:
        """获取图表数据"""
        try:
            # 用户增长趋势（最近30天）
            user_growth = DashboardService._get_user_growth_data()
            
            # 数据库类型分布
            database_type = DashboardService._get_database_type_data()
            
            return {
                "userGrowth": user_growth,
                "databaseType": database_type
            }
            
        except Exception as e:
            log_error(f"获取图表数据失败: {str(e)}", module="dashboard")
            return {
                "userGrowth": {"labels": [], "values": []},
                "databaseType": {"labels": [], "values": []}
            }
    
    @staticmethod
    def _get_user_growth_data() -> Dict[str, Any]:
        """获取用户增长数据"""
        try:
            from datetime import datetime, timedelta
            
            # 获取最近30天的用户增长数据
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            # 这里应该实现具体的查询逻辑
            # 暂时返回模拟数据
            labels = []
            values = []
            
            for i in range(30):
                date = start_date + timedelta(days=i)
                labels.append(date.strftime('%m-%d'))
                values.append(i + 1)  # 模拟数据
            
            return {
                "labels": labels,
                "values": values
            }
            
        except Exception as e:
            log_error(f"获取用户增长数据失败: {str(e)}", module="dashboard")
            return {"labels": [], "values": []}
    
    @staticmethod
    def _get_database_type_data() -> Dict[str, Any]:
        """获取数据库类型分布数据"""
        try:
            # 查询各类型数据库实例数量
            result = db.session.execute(text("""
                SELECT database_type, COUNT(*) as count
                FROM instances
                WHERE is_deleted = false
                GROUP BY database_type
            """))
            
            labels = []
            values = []
            
            for row in result:
                labels.append(row.database_type)
                values.append(row.count)
            
            return {
                "labels": labels,
                "values": values
            }
            
        except Exception as e:
            log_error(f"获取数据库类型数据失败: {str(e)}", module="dashboard")
            return {"labels": [], "values": []}
```

### 4.2 仪表板路由
```python
# app/routes/dashboard.py
from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app.services.dashboard_service import DashboardService
from app.utils.api_response import APIResponse
from app.utils.structlog_config import log_info, log_error


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index() -> str:
    """仪表板首页"""
    try:
        return render_template("dashboard/overview.html")
    except Exception as e:
        log_error(f"加载仪表板页面失败: {str(e)}", module="dashboard")
        return render_template("dashboard/overview.html", error="页面加载失败")


@dashboard_bp.route("/api/overview")
@login_required
def api_overview() -> tuple[dict, int]:
    """获取仪表板概览数据API"""
    try:
        overview_data = DashboardService.get_system_overview()
        status_data = DashboardService.get_system_status()
        chart_data = DashboardService.get_chart_data()
        
        response_data = {
            **overview_data,
            "status": status_data,
            "charts": chart_data
        }
        
        return APIResponse.success(response_data)
        
    except Exception as e:
        log_error(f"获取仪表板数据失败: {str(e)}", module="dashboard")
        return APIResponse.error(f"获取仪表板数据失败: {str(e)}"), 500
```

## 5. 配置管理

### 5.1 仪表板配置
```yaml
# app/config/dashboard_config.yaml
dashboard:
  # 刷新间隔（秒）
  refresh_interval: 30
  
  # 图表配置
  charts:
    user_growth:
      days: 30
      type: "line"
    database_type:
      type: "doughnut"
  
  # 卡片配置
  cards:
    - name: "total_users"
      title: "总用户数"
      icon: "fas fa-users"
      color: "primary"
    - name: "total_instances"
      title: "数据库实例"
      icon: "fas fa-database"
      color: "success"
    - name: "active_tasks"
      title: "活跃任务"
      icon: "fas fa-tasks"
      color: "warning"
    - name: "total_logs"
      title: "日志总数"
      icon: "fas fa-file-alt"
      color: "info"
```

## 6. 性能优化

### 6.1 数据优化
- 缓存仪表板数据
- 异步数据加载
- 分页加载图表数据

### 6.2 前端优化
- 图表懒加载
- 防抖处理频繁更新
- 虚拟滚动处理大量数据

### 6.3 后端优化
- 数据库查询优化
- 缓存策略优化
- 并发处理优化

---

**注意**: 本文档描述了仪表板功能的完整技术实现，包括数据展示、图表可视化、实时更新等各个方面。该功能为鲸落系统提供了直观的数据展示和管理界面。
