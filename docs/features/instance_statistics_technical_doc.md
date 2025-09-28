# 实例统计功能技术文档

## 功能概述

实例统计功能提供数据库实例的统计信息和监控数据，包括实例数量统计、数据库类型分布、端口分布、版本统计等。该功能支持实时统计、性能监控和趋势分析。

## 技术架构

### 前端架构

#### 页面结构
- **主页面**: `app/templates/instances/statistics.html`
- **样式文件**: `app/static/css/pages/instances/statistics.css`
- **脚本文件**: `app/static/js/pages/instances/statistics.js`

#### 前端组件
1. **统计卡片**: 显示总实例数、活跃实例、禁用实例、数据库类型数
2. **数据库类型分布表**: 显示各数据库类型的数量和百分比
3. **端口分布表**: 显示端口使用情况统计
4. **版本统计表**: 显示数据库版本分布
5. **版本分布图**: 使用Chart.js绘制饼图

### 后端架构

#### 路由定义
- **主路由**: `/instances/statistics` (GET)
- **API路由**: `/instances/api/statistics` (GET)

#### 核心函数
- **`statistics()`**: 实例统计页面路由
- **`api_statistics()`**: 获取实例统计API
- **`get_instance_statistics()`**: 获取实例统计数据

## 前端实现

### HTML模板结构

```html
<!-- 统计卡片 -->
<div class="row mb-4">
    <div class="col-md-3">
        <div class="card bg-primary text-white">
            <div class="card-body">
                <div class="d-flex justify-content-between">
                    <div>
                        <h4 class="card-title">{{ stats.total_instances }}</h4>
                        <p class="card-text">总实例数</p>
                    </div>
                    <div class="align-self-center">
                        <i class="fas fa-database fa-2x"></i>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <!-- 其他统计卡片... -->
</div>

<!-- 数据库类型分布 -->
<div class="col-md-6">
    <div class="card mb-4">
        <div class="card-header">
            <h5 class="card-title mb-0">
                <i class="fas fa-chart-pie me-2"></i>数据库类型分布
            </h5>
        </div>
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>数据库类型</th>
                            <th>数量</th>
                            <th>百分比</th>
                            <th>进度条</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for stat in stats.db_type_stats %}
                        <tr>
                            <td>
                                <span class="badge bg-{{ 'primary' if stat.db_type == 'postgresql' else 'success' if stat.db_type == 'mysql' else 'warning' if stat.db_type == 'sqlserver' else 'info' if stat.db_type == 'oracle' else 'secondary' }}">
                                    {{ stat.db_type.upper() }}
                                </span>
                            </td>
                            <td>{{ stat.count }}</td>
                            <td>{{ "%.1f"|format((stat.count / stats.total_instances * 100) if stats.total_instances > 0 else 0) }}%</td>
                            <td>
                                <div class="progress" style="height: 20px;">
                                    <div class="progress-bar bg-{{ 'primary' if stat.db_type == 'postgresql' else 'success' if stat.db_type == 'mysql' else 'warning' if stat.db_type == 'sqlserver' else 'info' if stat.db_type == 'oracle' else 'secondary' }}" 
                                         role="progressbar" style="width: {{ (stat.count / stats.total_instances * 100) if stats.total_instances > 0 else 0 }}%">
                                    </div>
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<!-- 版本分布图 -->
<div class="col-md-6">
    <div class="card">
        <div class="card-header">
            <h5 class="card-title mb-0">
                <i class="fas fa-chart-pie me-2"></i>版本分布图
            </h5>
        </div>
        <div class="card-body">
            <canvas id="versionChart" height="300"></canvas>
        </div>
    </div>
</div>
```

### CSS样式设计

```css
/* 统计卡片样式 */
.stats-card {
    transition: all 0.3s ease;
    border: none;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.stats-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.stats-number {
    font-size: 2.5rem;
    font-weight: bold;
    margin-bottom: 0.5rem;
}

.stats-label {
    font-size: 1rem;
    opacity: 0.9;
    margin-bottom: 0;
}

.stats-icon {
    font-size: 2.5rem;
    opacity: 0.8;
}

/* 图表容器样式 */
.chart-container {
    position: relative;
    height: 400px;
    margin: 1rem 0;
}

.chart-container canvas {
    max-height: 100%;
}

/* 数据库类型徽章 */
.db-type-badge {
    font-size: 0.8em;
    padding: 0.4em 0.8em;
    border-radius: 0.25rem;
}

.db-type-badge.mysql {
    background-color: #28a745;
    color: white;
}

.db-type-badge.postgresql {
    background-color: #007bff;
    color: white;
}

.db-type-badge.sqlserver {
    background-color: #ffc107;
    color: #212529;
}

.db-type-badge.oracle {
    background-color: #17a2b8;
    color: white;
}

/* 状态指示器 */
.status-indicator {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    display: inline-block;
    margin-right: 8px;
}

.status-indicator.active {
    background-color: #28a745;
    box-shadow: 0 0 6px rgba(40, 167, 69, 0.5);
}

.status-indicator.inactive {
    background-color: #dc3545;
    box-shadow: 0 0 6px rgba(220, 53, 69, 0.5);
}
```

### JavaScript功能实现

```javascript
/**
 * 实例统计页面JavaScript
 * 处理统计数据的显示、图表渲染和自动刷新功能
 */

// 全局变量
let versionChart = null;
let refreshInterval = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    createVersionChart();
    startAutoRefresh();
});

// 创建版本分布图表
function createVersionChart() {
    const ctx = document.getElementById('versionChart');
    if (!ctx) return;
    
    // 获取版本统计数据
    const versionStats = getVersionStats();
    
    if (!versionStats || versionStats.length === 0) {
        showEmptyChart(ctx);
        return;
    }
    
    // 按数据库类型分组
    const groupedStats = groupStatsByDbType(versionStats);
    
    // 创建图表数据
    const chartData = createChartData(groupedStats);
    
    // 创建图表
    versionChart = new Chart(ctx, {
        type: 'doughnut',
        data: chartData,
        options: getChartOptions()
    });
}

// 获取版本统计数据
function getVersionStats() {
    // 从页面中获取版本统计数据
    const versionStatsElement = document.querySelector('[data-version-stats]');
    if (versionStatsElement) {
        try {
            return JSON.parse(versionStatsElement.dataset.versionStats);
        } catch (error) {
            console.error('解析版本统计数据失败:', error);
            return null;
        }
    }
    
    // 如果没有data属性，尝试从全局变量获取
    if (typeof window.versionStats !== 'undefined') {
        return window.versionStats;
    }
    
    return null;
}

// 按数据库类型分组统计数据
function groupStatsByDbType(versionStats) {
    const groupedStats = {};
    versionStats.forEach(stat => {
        if (!groupedStats[stat.db_type]) {
            groupedStats[stat.db_type] = [];
        }
        groupedStats[stat.db_type].push(stat);
    });
    return groupedStats;
}

// 创建图表数据
function createChartData(groupedStats) {
    const labels = [];
    const data = [];
    const colors = [];
    const dbTypeColors = {
        'mysql': 'rgba(40, 167, 69, 0.8)',
        'postgresql': 'rgba(0, 123, 255, 0.8)',
        'sqlserver': 'rgba(255, 193, 7, 0.8)',
        'oracle': 'rgba(23, 162, 184, 0.8)'
    };
    
    Object.keys(groupedStats).forEach(dbType => {
        groupedStats[dbType].forEach(stat => {
            labels.push(`${stat.db_type.toUpperCase()} ${stat.version}`);
            data.push(stat.count);
            colors.push(dbTypeColors[stat.db_type] || 'rgba(108, 117, 125, 0.8)');
        });
    });
    
    return {
        labels: labels,
        datasets: [{
            data: data,
            backgroundColor: colors,
            borderColor: colors.map(color => color.replace('0.8', '1')),
            borderWidth: 2
        }]
    };
}

// 获取图表配置选项
function getChartOptions() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom',
                labels: {
                    usePointStyle: true,
                    padding: 20
                }
            },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        const total = context.dataset.data.reduce((a, b) => a + b, 0);
                        const percentage = ((context.parsed / total) * 100).toFixed(1);
                        return `${context.label}: ${context.parsed} 个实例 (${percentage}%)`;
                    }
                }
            }
        }
    };
}

// 开始自动刷新
function startAutoRefresh() {
    // 每60秒刷新一次统计数据
    refreshInterval = setInterval(() => {
        refreshStatistics();
    }, 60000);
}

// 刷新统计数据
function refreshStatistics() {
    fetch('/instances/api/statistics')
        .then(response => response.json())
        .then(data => {
            // 更新统计数据显示
            updateStatistics(data);
            showDataUpdatedNotification();
        })
        .catch(error => {
            console.error('刷新统计数据失败:', error);
            showErrorNotification('刷新统计数据失败');
        });
}

// 更新统计数据显示
function updateStatistics(stats) {
    // 更新统计卡片
    const totalInstancesElement = document.querySelector('.card.bg-primary .card-title');
    const activeInstancesElement = document.querySelector('.card.bg-success .card-title');
    const inactiveInstancesElement = document.querySelector('.card.bg-warning .card-title');
    const dbTypesCountElement = document.querySelector('.card.bg-info .card-title');
    
    if (totalInstancesElement) totalInstancesElement.textContent = stats.total_instances;
    if (activeInstancesElement) activeInstancesElement.textContent = stats.active_instances;
    if (inactiveInstancesElement) inactiveInstancesElement.textContent = stats.inactive_instances;
    if (dbTypesCountElement) dbTypesCountElement.textContent = stats.db_types_count;
    
    // 更新版本统计图表
    if (stats.version_stats && versionChart) {
        updateVersionChart(stats.version_stats);
    }
}

// 更新版本统计图表
function updateVersionChart(versionStats) {
    if (!versionChart || !versionStats || versionStats.length === 0) return;
    
    const groupedStats = groupStatsByDbType(versionStats);
    const chartData = createChartData(groupedStats);
    
    versionChart.data = chartData;
    versionChart.update();
}

// 手动刷新数据
function manualRefresh() {
    const refreshBtn = document.querySelector('.refresh-btn');
    if (refreshBtn) {
        const originalContent = refreshBtn.innerHTML;
        refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>刷新中...';
        refreshBtn.disabled = true;
        
        refreshStatistics();
        
        // 2秒后恢复按钮状态
        setTimeout(() => {
            refreshBtn.innerHTML = originalContent;
            refreshBtn.disabled = false;
        }, 2000);
    }
}
```

## 后端实现

### 路由定义

```python
# app/routes/instances.py

@instances_bp.route("/statistics")
@login_required
@view_required
def statistics() -> str | Response:
    """实例统计页面"""
    stats = get_instance_statistics()

    if request.is_json:
        return jsonify(stats)

    return render_template("instances/statistics.html", stats=stats)


@instances_bp.route("/api/statistics")
@login_required
@view_required
def api_statistics() -> Response:
    """获取实例统计API"""
    stats = get_instance_statistics()
    return jsonify(stats)
```

### 核心业务逻辑

```python
def get_instance_statistics() -> dict[str, Any]:
    """获取实例统计数据"""
    try:
        # 基础统计
        total_instances = Instance.query.count()
        active_instances = Instance.query.filter_by(is_active=True).count()
        inactive_instances = Instance.query.filter_by(is_active=False).count()

        # 数据库类型统计
        db_type_stats = (
            db.session.query(Instance.db_type, db.func.count(Instance.id).label("count"))
            .group_by(Instance.db_type)
            .all()
        )

        # 端口统计
        port_stats = (
            db.session.query(Instance.port, db.func.count(Instance.id).label("count"))
            .group_by(Instance.port)
            .order_by(db.func.count(Instance.id).desc())
            .limit(10)
            .all()
        )

        # 数据库版本统计（使用主版本信息）
        version_stats = (
            db.session.query(
                Instance.db_type,
                Instance.main_version,
                db.func.count(Instance.id).label("count"),
            )
            .group_by(Instance.db_type, Instance.main_version)
            .all()
        )

        # 转换为版本统计格式
        version_stats = [
            {
                "db_type": stat.db_type,
                "version": stat.main_version or "未知版本",
                "count": stat.count,
            }
            for stat in version_stats
        ]

        # 数据库类型数量
        db_types_count = len(db_type_stats)

        return {
            "total_instances": total_instances,
            "active_instances": active_instances,
            "inactive_instances": inactive_instances,
            "db_types_count": db_types_count,
            "db_type_stats": [{"db_type": stat.db_type, "count": stat.count} for stat in db_type_stats],
            "port_stats": [{"port": stat.port, "count": stat.count} for stat in port_stats],
            "version_stats": version_stats,
        }

    except Exception as e:
        log_error(f"获取实例统计失败: {e}", module="instances", exc_info=True)
        return {
            "total_instances": 0,
            "active_instances": 0,
            "inactive_instances": 0,
            "db_types_count": 0,
            "db_type_stats": [],
            "port_stats": [],
            "version_stats": [],
            "recent_connections": [],
        }
```

### 数据模型

```python
# app/models/instance.py

class Instance(db.Model):
    """数据库实例模型"""
    __tablename__ = "instances"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True, index=True)
    db_type = db.Column(db.String(50), nullable=False, index=True)
    host = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    main_version = db.Column(db.String(50))
    full_version = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now)
    
    # 关系
    credential = db.relationship("Credential", backref="instances")
    tags = db.relationship("Tag", secondary="instance_tags", back_populates="instances", lazy="dynamic")
```

## 核心功能

### 1. 基础统计
- **总实例数**: 统计所有数据库实例数量
- **活跃实例**: 统计启用状态的实例数量
- **禁用实例**: 统计禁用状态的实例数量
- **数据库类型数**: 统计不同数据库类型的数量

### 2. 数据库类型分布
- **类型统计**: 按数据库类型分组统计实例数量
- **百分比计算**: 计算每种类型占总数的百分比
- **可视化展示**: 使用进度条和徽章显示分布情况

### 3. 端口分布统计
- **端口统计**: 统计各端口的使用情况
- **TOP 10**: 显示使用最多的前10个端口
- **使用频率**: 显示每个端口的实例数量

### 4. 版本统计
- **版本分布**: 按数据库类型和版本统计实例数量
- **图表展示**: 使用饼图显示版本分布
- **详细信息**: 显示具体版本号和实例数量

### 5. 实时监控
- **自动刷新**: 每60秒自动刷新统计数据
- **手动刷新**: 提供手动刷新按钮
- **状态通知**: 显示数据更新状态

## API接口

### 获取实例统计

**接口**: `GET /instances/api/statistics`

**响应格式**:
```json
{
    "total_instances": 15,
    "active_instances": 12,
    "inactive_instances": 3,
    "db_types_count": 4,
    "db_type_stats": [
        {
            "db_type": "mysql",
            "count": 8
        },
        {
            "db_type": "postgresql",
            "count": 4
        }
    ],
    "port_stats": [
        {
            "port": 3306,
            "count": 8
        },
        {
            "port": 5432,
            "count": 4
        }
    ],
    "version_stats": [
        {
            "db_type": "mysql",
            "version": "8.0",
            "count": 5
        },
        {
            "db_type": "mysql",
            "version": "5.7",
            "count": 3
        }
    ]
}
```

## 性能优化

### 1. 数据库查询优化
- 使用索引优化查询性能
- 合理使用GROUP BY和聚合函数
- 避免N+1查询问题

### 2. 前端性能优化
- 使用Chart.js进行图表渲染
- 实现数据缓存机制
- 优化DOM操作和事件处理

### 3. 缓存策略
- 统计数据缓存60秒
- 版本信息缓存更长时间
- 使用浏览器缓存优化加载速度

## 错误处理

### 1. 后端错误处理
```python
try:
    # 统计查询逻辑
    stats = get_instance_statistics()
    return jsonify(stats)
except Exception as e:
    log_error(f"获取实例统计失败: {e}", module="instances", exc_info=True)
    return jsonify({
        "error": "获取统计数据失败",
        "message": str(e)
    }), 500
```

### 2. 前端错误处理
```javascript
function refreshStatistics() {
    fetch('/instances/api/statistics')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            updateStatistics(data);
            showDataUpdatedNotification();
        })
        .catch(error => {
            console.error('刷新统计数据失败:', error);
            showErrorNotification('刷新统计数据失败: ' + error.message);
        });
}
```

## 安全考虑

### 1. 权限控制
- 使用`@login_required`装饰器验证用户登录
- 使用`@view_required`装饰器验证查看权限
- 确保只有授权用户可以访问统计数据

### 2. 数据安全
- 不暴露敏感的实例配置信息
- 统计数据不包含密码等敏感信息
- 使用HTTPS传输统计数据

## 测试策略

### 1. 单元测试
```python
def test_get_instance_statistics():
    """测试获取实例统计数据"""
    # 创建测试数据
    create_test_instances()
    
    # 获取统计数据
    stats = get_instance_statistics()
    
    # 验证统计结果
    assert stats['total_instances'] > 0
    assert stats['active_instances'] >= 0
    assert stats['inactive_instances'] >= 0
    assert len(stats['db_type_stats']) > 0
```

### 2. 集成测试
```python
def test_statistics_api():
    """测试统计API接口"""
    response = client.get('/instances/api/statistics')
    
    assert response.status_code == 200
    data = response.get_json()
    assert 'total_instances' in data
    assert 'db_type_stats' in data
```

### 3. 前端测试
```javascript
describe('Instance Statistics', () => {
    test('should load statistics data', async () => {
        const mockStats = {
            total_instances: 10,
            active_instances: 8,
            inactive_instances: 2
        };
        
        fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(mockStats)
        });
        
        await refreshStatistics();
        
        expect(document.querySelector('.card.bg-primary .card-title').textContent).toBe('10');
    });
});
```

## 部署注意事项

### 1. 数据库索引
确保以下字段有适当的索引：
- `instances.is_active`
- `instances.db_type`
- `instances.port`
- `instances.main_version`

### 2. 监控配置
- 配置统计数据的监控告警
- 设置性能指标阈值
- 监控API响应时间

### 3. 缓存配置
- 配置Redis缓存统计数据
- 设置合适的缓存过期时间
- 实现缓存预热机制

## 扩展功能

### 1. 高级统计
- 实例连接状态统计
- 性能指标统计
- 容量使用统计

### 2. 导出功能
- 统计数据CSV导出
- 图表PNG/PDF导出
- 定期统计报告

### 3. 告警功能
- 实例数量异常告警
- 版本过期告警
- 性能指标告警

## 维护指南

### 1. 日常维护
- 定期检查统计数据准确性
- 监控API性能指标
- 更新图表库版本

### 2. 故障排查
- 检查数据库连接状态
- 验证统计查询性能
- 分析前端错误日志

### 3. 性能调优
- 优化统计查询SQL
- 调整缓存策略
- 优化前端渲染性能
