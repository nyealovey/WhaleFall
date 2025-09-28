# 数据库统计功能技术文档

## 功能概述

数据库统计功能提供数据库级别的统计信息和分析，包括容量分析、增长趋势、性能指标等。该功能主要通过统计聚合和分区管理来实现数据库容量的监控和分析。

## 技术架构

### 前端架构

#### 页面结构
- **统计聚合页面**: `app/templates/database_sizes/aggregations.html`
- **分区管理页面**: `app/templates/database_sizes/partitions.html`
- **样式文件**: 
  - `app/static/css/pages/database_sizes/aggregations.css`
  - `app/static/css/pages/database_sizes/partitions.css`
- **脚本文件**: 
  - `app/static/js/pages/database_sizes/aggregations.js`
  - `app/static/js/pages/database_sizes/partitions.js`

#### 前端组件
1. **统计概览卡片**: 显示总实例数、总数据库数、平均大小、最大大小
2. **聚合趋势图**: 使用Chart.js绘制数据库容量趋势图
3. **筛选控制面板**: 支持按实例、数据库类型、周期类型等筛选
4. **分区管理表**: 显示数据库分区信息和状态
5. **聚合数据表**: 显示最新的聚合统计数据

### 后端架构

#### 路由定义
- **聚合页面**: `/database-sizes/aggregations` (GET)
- **聚合API**: `/database-sizes/aggregations` (GET, API)
- **聚合汇总**: `/database-sizes/aggregations/summary` (GET)
- **今日聚合**: `/database-sizes/aggregate-today` (POST)
- **分区管理**: `/partition-management/partitions` (GET)
- **分区状态**: `/partition-management/partitions/status` (GET)
- **最新聚合**: `/partition-management/aggregations/latest` (GET)

#### 核心服务
- **`DatabaseSizeAggregationService`**: 数据库大小统计聚合服务
- **`DatabaseSizeCollectorService`**: 数据库大小采集服务
- **`PartitionManagementService`**: 分区管理服务

## 前端实现

### 统计聚合页面HTML结构

```html
<!-- 页面标题 -->
<div class="row mb-4">
    <div class="col-12">
        <div class="d-flex justify-content-between align-items-center">
            <div>
                <h1 class="h3 mb-0">
                    <i class="fas fa-chart-bar me-2"></i>
                    统计聚合
                </h1>
                <p class="text-muted mb-0">数据库大小统计聚合分析</p>
            </div>
            <div>
                <button class="btn btn-outline-primary" id="refreshData">
                    <i class="fas fa-sync-alt me-1"></i>
                    刷新数据
                </button>
                <button class="btn btn-primary" id="calculateAggregations">
                    <i class="fas fa-calculator me-1"></i>
                    聚合今日数据
                </button>
            </div>
        </div>
    </div>
</div>

<!-- 统一搜索筛选 -->
<div class="row mb-4">
    <div class="col-12">
        <div class="aggregations-page">
            {% set show_search_input = false %}
            {% set search_button_text = '筛选' %}
            {% set show_instance_filter = true %}
            {% set show_period_type_filter = true %}
            {% set show_database_filter = true %}
            {% set show_time_range_filter = true %}
            {% set show_db_type_filter = true %}
            {% include 'components/unified_search_form.html' %}
        </div>
    </div>
</div>

<!-- 统计概览 -->
<div class="row mb-4">
    <div class="col-md-3">
        <div class="card bg-primary text-white">
            <div class="card-body">
                <div class="d-flex justify-content-between">
                    <div>
                        <h6 class="card-title">总实例数</h6>
                        <h3 class="mb-0" id="totalInstances">-</h3>
                    </div>
                    <div class="align-self-center">
                        <i class="fas fa-server fa-2x opacity-75"></i>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <!-- 其他统计卡片... -->
</div>

<!-- 图表区域 -->
<div class="row mb-4">
    <div class="col-12">
        <div class="card">
            <div class="card-header">
                <div class="row align-items-center">
                    <div class="col-md-6">
                        <h5 class="card-title mb-0">
                            <i class="fas fa-chart-area me-2"></i>
                            聚合趋势图
                        </h5>
                    </div>
                    <div class="col-md-6">
                        <div class="d-flex gap-2">
                            <div class="btn-group" role="group">
                                <input type="radio" class="btn-check" name="chartMode" id="chartModeDatabase" value="database" checked>
                                <label class="btn btn-outline-success" for="chartModeDatabase">数据库</label>
                                
                                <input type="radio" class="btn-check" name="chartMode" id="chartModeInstance" value="instance">
                                <label class="btn btn-outline-success" for="chartModeInstance">实例</label>
                            </div>
                            
                            <div class="btn-group" role="group">
                                <input type="radio" class="btn-check" name="chartType" id="chartTypeLine" value="line" checked>
                                <label class="btn btn-outline-primary" for="chartTypeLine">折线图</label>
                                
                                <input type="radio" class="btn-check" name="chartType" id="chartTypeBar" value="bar">
                                <label class="btn btn-outline-primary" for="chartTypeBar">柱状图</label>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="card-body">
                <div class="position-relative">
                    <div id="aggregationChart" style="height: 500px; width: 100%;"></div>
                    <div id="chartLoading" class="position-absolute top-50 start-50 translate-middle d-none">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">加载中...</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
```

### 分区管理页面HTML结构

```html
<!-- 分区状态概览 -->
<div class="row mb-4">
    <div class="col-lg-3 col-md-6 mb-3">
        <div class="card bg-primary text-white">
            <div class="card-body">
                <div class="d-flex justify-content-between">
                    <div>
                        <h4 class="card-title" id="totalPartitions">-</h4>
                        <p class="card-text">总分区数</p>
                    </div>
                    <div class="align-self-center">
                        <i class="fas fa-layer-group fa-2x"></i>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <!-- 其他状态卡片... -->
</div>

<!-- 分区列表 -->
<div class="card mb-4">
    <div class="card-header">
        <h5 class="mb-0"><i class="fas fa-list me-2"></i>分区列表</h5>
    </div>
    <div class="card-body">
        <div class="table-responsive">
            <table class="table table-hover" id="partitionsTable">
                <thead>
                    <tr>
                        <th>分区名称</th>
                        <th>日期</th>
                        <th>大小</th>
                        <th>记录数</th>
                        <th>状态</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody id="partitionsTableBody">
                    <!-- 动态加载分区数据 -->
                </tbody>
            </table>
        </div>
    </div>
</div>

<!-- 聚合数据表 -->
<div class="card">
    <div class="card-header">
        <div class="row align-items-center">
            <div class="col-md-6">
                <h5 class="mb-0">
                    <i class="fas fa-chart-bar me-2"></i>
                    聚合数据表
                </h5>
            </div>
            <div class="col-md-6">
                <div class="row g-2">
                    <div class="col-md-4">
                        <input type="text" class="form-control form-control-sm" id="searchAggregationTable" placeholder="搜索实例或数据库...">
                    </div>
                    <div class="col-md-4">
                        <select class="form-select form-select-sm" id="periodTypeFilter">
                            <option value="daily">日聚合数据</option>
                            <option value="weekly">周聚合数据</option>
                            <option value="monthly">月聚合数据</option>
                            <option value="quarterly">季聚合数据</option>
                        </select>
                    </div>
                    <div class="col-md-4">
                        <select class="form-select form-select-sm" id="sortAggregationTable">
                            <option value="instance_name">按实例排序</option>
                            <option value="database_name">按数据库排序</option>
                            <option value="avg_size_mb">按平均大小排序</option>
                            <option value="max_size_mb">按最大大小排序</option>
                        </select>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <div class="card-body">
        <div class="table-responsive">
            <table class="table table-hover" id="aggregationTable">
                <thead>
                    <tr>
                        <th>周期类型</th>
                        <th>实例名称</th>
                        <th>数据库名称</th>
                        <th>统计周期</th>
                        <th>平均大小</th>
                        <th>最大大小</th>
                        <th>最小大小</th>
                        <th>数据点数</th>
                        <th>计算时间</th>
                    </tr>
                </thead>
                <tbody id="aggregationTableBody">
                    <!-- 动态加载聚合数据 -->
                </tbody>
            </table>
        </div>
    </div>
</div>
```

### CSS样式设计

```css
/**
 * 统计聚合页面样式
 * 基于 Bootstrap 5.3.2 的响应式设计
 */

/* 页面整体布局 */
.aggregations-page {
    min-height: auto;
    background-color: #f8f9fa;
}

.aggregations-page .container-fluid {
    padding: 1.5rem;
    max-width: 100%;
}

/* 统计概览卡片 */
.summary-cards .card {
    border: none;
    border-radius: 0.75rem;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease;
    overflow: hidden;
}

.summary-cards .card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.summary-cards .card-body {
    padding: 1.5rem;
}

.summary-cards .card h3 {
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0;
}

/* 卡片颜色主题 */
.summary-cards .card.bg-primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
}

.summary-cards .card.bg-success {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%) !important;
}

.summary-cards .card.bg-info {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
}

.summary-cards .card.bg-warning {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%) !important;
}

/* 图表区域 */
.chart-container {
    background: white;
    border-radius: 0.75rem;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    overflow: hidden;
    margin-bottom: 2rem;
}

.chart-header {
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    border-bottom: 1px solid #dee2e6;
    padding: 1.25rem 1.5rem;
}

.chart-body {
    padding: 1.5rem;
    position: relative;
}

.chart-loading {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 10;
    background: rgba(255, 255, 255, 0.9);
    padding: 1rem;
    border-radius: 0.5rem;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* 数据表格 */
.table thead th {
    background-color: #f8f9fa;
    border-bottom: 2px solid #dee2e6;
    font-weight: 600;
    color: #495057;
    padding: 0.75rem 0.5rem;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    white-space: nowrap;
}

.table tbody td {
    padding: 0.75rem 0.5rem;
    vertical-align: middle;
    border-bottom: 1px solid #f1f3f4;
    font-size: 0.8rem;
}

.table tbody tr:hover {
    background-color: #f8f9fa;
    transition: background-color 0.2s ease;
}

/* 实例名称样式 */
.instance-name {
    font-weight: 600;
    color: #495057;
}

/* 数据库名称样式 */
.database-name {
    font-weight: 500;
    color: #6c757d;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    word-break: break-all;
    word-wrap: break-word;
    white-space: normal;
    line-height: 1.2;
    max-width: 150px;
    min-width: 100px;
}

/* 大小显示样式 */
.size-display {
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-weight: 500;
}

/* 空状态 */
.empty-state {
    text-align: center;
    padding: 3rem 1.5rem;
    color: #6c757d;
}

.empty-state i {
    font-size: 3rem;
    margin-bottom: 1rem;
    opacity: 0.5;
}

.empty-state h5 {
    margin-bottom: 0.5rem;
    color: #495057;
}

/* 图表容器 */
#aggregationChart {
    max-height: 500px;
    min-height: 400px;
}

/* 响应式设计 */
@media (max-width: 768px) {
    .aggregations-page .container-fluid {
        padding: 1rem;
    }
    
    .summary-cards .card-body {
        padding: 1rem;
    }
    
    .summary-cards .card h3 {
        font-size: 1.5rem;
    }
    
    .table-responsive {
        font-size: 0.8rem;
    }
    
    .table thead th,
    .table tbody td {
        padding: 0.5rem 0.25rem;
    }
}
```

### JavaScript功能实现

#### 统计聚合页面脚本

```javascript
/**
 * 统计聚合页面脚本
 * 基于 jQuery 3.7.1 和 Chart.js 4.4.0
 */

class AggregationsManager {
    constructor() {
        this.chart = null;
        this.detailChart = null;
        this.isRenderingChart = false;
        this.currentData = [];
        this.currentSummary = null;
        this.currentFilters = {
            instance: '',
            dbType: '',
            periodType: 'daily',
            database: '',
            dateRange: 7
        };
        this.currentChartType = 'line';
        this.currentChartMode = 'database'; // 'database' 或 'instance'
        
        this.init();
    }
    
    /**
     * 初始化页面
     */
    init() {
        this.bindEvents();
        this.initializeDatabaseFilter();
        this.loadSummaryData();
        this.loadChartData();
    }
    
    /**
     * 绑定事件监听器
     */
    bindEvents() {
        // 刷新数据按钮
        $('#refreshData').on('click', () => {
            this.refreshAllData();
        });
        
        // 重新计算按钮
        $('#calculateAggregations').on('click', () => {
            this.calculateAggregations();
        });
        
        // 筛选器变化
        $('#period_type, #timeRange').on('change', () => {
            this.updateFilters();
            this.loadChartData();
        });
        
        // 数据库类型变化时更新实例选项
        $('#db_type').on('change', async (e) => {
            const dbType = e.target.value;
            await this.updateInstanceOptions(dbType);
            this.updateFilters();
            this.loadChartData();
        });
        
        // 图表类型切换
        $('input[name="chartType"]').on('change', (e) => {
            this.currentChartType = e.target.value;
            this.updateChart();
        });
        
        // 图表模式切换
        $('input[name="chartMode"]').on('change', (e) => {
            this.currentChartMode = e.target.value;
            this.updateChart();
        });
    }
    
    /**
     * 加载汇总数据
     */
    async loadSummaryData() {
        try {
            this.showLoading('#totalInstances, #totalDatabases, #averageSize, #maxSize');
            
            const response = await fetch('/database-sizes/aggregations/summary?api=true');
            const data = await response.json();
            
            if (response.ok) {
                this.currentSummary = data.data;
                this.updateSummaryCards(data.data);
            } else {
                this.showError('加载汇总数据失败: ' + data.error);
            }
        } catch (error) {
            console.error('加载汇总数据时出错:', error);
            this.showError('加载汇总数据时出错: ' + error.message);
        }
    }
    
    /**
     * 更新汇总卡片
     */
    updateSummaryCards(data) {
        $('#totalInstances').text(data.total_instances || 0);
        $('#totalDatabases').text(data.total_databases || 0);
        $('#averageSize').text(this.formatSizeFromMB(data.average_size_mb || 0));
        $('#maxSize').text(this.formatSizeFromMB(data.max_size_mb || 0));
    }
    
    /**
     * 加载图表数据
     */
    async loadChartData() {
        try {
            this.showChartLoading();
            
            const params = this.buildFilterParams();
            params.append('chart_mode', this.currentChartMode);
            
            const response = await fetch(`/database-sizes/aggregations?api=true&get_all=true&${params}`);
            const data = await response.json();
            
            if (response.ok) {
                this.currentData = data.data;
                this.updateDatabaseFilter(data.data);
                this.renderChart(data.data);
            } else {
                this.showError('加载图表数据失败: ' + data.error);
            }
        } catch (error) {
            console.error('加载图表数据时出错:', error);
            this.showError('加载图表数据时出错: ' + error.message);
        } finally {
            this.hideChartLoading();
        }
    }
    
    /**
     * 渲染图表
     */
    renderChart(data) {
        const chartContainer = document.getElementById('aggregationChart');
        if (!chartContainer) {
            console.error('图表容器 #aggregationChart 不存在！');
            return;
        }

        if (this.isRenderingChart) {
            console.warn('图表正在渲染中，跳过本次渲染请求');
            return;
        }
        this.isRenderingChart = true;

        try {
            // 销毁现有图表
            if (this.chart) {
                this.chart.destroy();
                this.chart = null;
            }

            // 清空容器
            chartContainer.innerHTML = '';
            
            // 创建新的canvas元素
            const canvas = document.createElement('canvas');
            canvas.id = 'aggregationChartCanvas';
            canvas.style.width = '100%';
            canvas.style.height = '100%';
            chartContainer.appendChild(canvas);

            const ctx = canvas.getContext('2d');
            if (!ctx) {
                console.error('无法获取canvas上下文');
                return;
            }

            // 处理数据
            let labels, datasets;
            
            if (!data || data.length === 0) {
                // 空数据情况
                labels = ['暂无数据'];
                datasets = [{
                    label: '无数据',
                    data: [0],
                    backgroundColor: 'rgba(200, 200, 200, 0.2)',
                    borderColor: 'rgba(200, 200, 200, 0.8)',
                    borderWidth: 1
                }];
            } else {
                // 有数据情况
                const groupedData = this.groupDataByDate(data);
                labels = Object.keys(groupedData).sort();
                
                if (labels.length === 0) {
                    labels = ['暂无数据'];
                    datasets = [{
                        label: '无数据',
                        data: [0],
                        backgroundColor: 'rgba(200, 200, 200, 0.2)',
                        borderColor: 'rgba(200, 200, 200, 0.8)',
                        borderWidth: 1
                    }];
                } else {
                    datasets = this.prepareChartDatasets(groupedData, labels);
                    
                    if (!datasets || datasets.length === 0) {
                        labels = ['暂无数据'];
                        datasets = [{
                            label: '无数据',
                            data: [0],
                            backgroundColor: 'rgba(200, 200, 200, 0.2)',
                            borderColor: 'rgba(200, 200, 200, 0.8)',
                            borderWidth: 1
                        }];
                    }
                }
            }

            // 根据数据情况调整图表类型
            let chartType = this.currentChartType;
            if (labels.length === 1 && labels[0] !== '暂无数据') {
                if (chartType === 'line') {
                    chartType = 'bar';
                }
            }

            const chartConfig = {
                type: chartType,
                data: { labels, datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    layout: { padding: { right: 120 } },
                    interaction: { intersect: false, mode: 'index' },
                    plugins: {
                        title: {
                            display: true,
                            text: this.getChartTitle(labels.length, data?.length || 0),
                            font: { size: 16, weight: 'bold' }
                        },
                        legend: {
                            display: labels.length > 1 || (labels.length === 1 && labels[0] !== '暂无数据'),
                            position: 'right',
                            align: 'start',
                            maxHeight: 500,
                            labels: {
                                usePointStyle: true,
                                padding: 4,
                                boxWidth: 8,
                                boxHeight: 8,
                                font: { size: 10 },
                                generateLabels: function(chart) {
                                    const original = Chart.defaults.plugins.legend.labels.generateLabels;
                                    const labels = original.call(this, chart);
                                    labels.sort((a, b) => a.text.localeCompare(b.text));
                                    return labels.slice(0, 23);
                                }
                            }
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                label: function(context) {
                                    const label = context.dataset.label || '';
                                    const value = context.parsed.y;
                                    return `${label}: ${AggregationsManager.prototype.formatSizeFromMB(value)}`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: { 
                            display: true, 
                            title: { display: true, text: this.getXAxisTitle(labels.length) }, 
                            grid: { display: false } 
                        },
                        y: {
                            display: true,
                            title: { display: true, text: '存储大小' },
                            beginAtZero: true,
                            grid: { color: 'rgba(0, 0, 0, 0.1)' },
                            ticks: { callback: (v) => AggregationsManager.prototype.formatSizeFromMB(v) }
                        }
                    },
                    elements: { 
                        point: { radius: 4, hoverRadius: 6 }, 
                        line: { tension: 0.1 } 
                    }
                }
            };

            // 检查Chart.js是否可用
            if (typeof Chart === 'undefined') {
                console.error('Chart.js 未加载！');
                this.showError('图表库未加载，请刷新页面重试');
                return;
            }

            try {
                this.chart = new Chart(ctx, chartConfig);
                console.log('图表创建成功');
            } catch (chartErr) {
                console.error('Chart 创建失败:', chartErr);
                this.showError('图表创建失败: ' + chartErr.message);
                this.showEmptyChart();
                return;
            }
            
        } catch (err) {
            console.error('渲染图表时出错:', err);
            this.showError('渲染图表时出错: ' + (err && err.message ? err.message : ''));
        } finally {
            this.isRenderingChart = false;
        }
    }
    
    /**
     * 聚合今日数据
     */
    async calculateAggregations() {
        try {
            // 显示计算进度模态框
            const modal = new bootstrap.Modal(document.getElementById('calculationModal'));
            modal.show();
            
            // 调用API聚合今日数据
            const csrfToken = this.getCSRFToken();
            const response = await fetch('/database-sizes/aggregate-today', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.showSuccess('今日数据聚合完成');
            } else {
                this.showError('聚合今日数据失败: ' + data.error);
            }
            
        } catch (error) {
            console.error('聚合今日数据时出错:', error);
            this.showError('聚合今日数据时出错: ' + error.message);
        }
    }
    
    /**
     * 格式化文件大小（从MB开始）
     */
    formatSizeFromMB(mb) {
        if (mb === 0) return '0 MB';
        
        const k = 1024;
        const sizes = ['MB', 'GB', 'TB'];
        
        if (mb < k) {
            return parseFloat(mb.toFixed(2)) + ' MB';
        }
        
        let i = 0;
        let size = mb;
        
        while (size >= k && i < sizes.length - 1) {
            size = size / k;
            i++;
        }
        
        return parseFloat(size.toFixed(2)) + ' ' + sizes[i];
    }
}

// 页面加载完成后初始化
$(document).ready(function() {
    new AggregationsManager();
});
```

#### 分区管理页面脚本

```javascript
// app/static/js/pages/database_sizes/partitions.js

document.addEventListener('DOMContentLoaded', function() {
    // 初始化页面
    initializePartitionsPage();
    
    // 绑定事件
    bindEvents();
    
    // 加载数据
    loadPartitionData();
    
    // 加载聚合数据
    loadAggregationData();
});

/**
 * 初始化分区管理页面
 */
function initializePartitionsPage() {
    console.log('初始化分区管理页面...');
    
    // 初始化年份选择器
    initializeYearSelector();
    
    // 设置默认月份为下个月
    const nextMonth = new Date();
    nextMonth.setMonth(nextMonth.getMonth() + 1);
    document.getElementById('partitionYear').value = nextMonth.getFullYear();
    document.getElementById('partitionMonth').value = nextMonth.getMonth() + 1;
}

/**
 * 加载分区数据
 */
async function loadPartitionData() {
    try {
        console.log('开始加载分区数据...');
        showLoadingState();
        
        // 获取CSRF token
        const csrfToken = getCSRFToken();
        
        // 并行加载分区信息和状态
        const [partitionInfoResponse, partitionStatusResponse] = await Promise.all([
            fetch('/partition-management/partitions?api=true', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            }),
            fetch('/partition-management/partitions/status', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            })
        ]);
        
        if (!partitionInfoResponse.ok) {
            const errorText = await partitionInfoResponse.text();
            throw new Error(`分区信息请求失败: ${partitionInfoResponse.status} ${errorText}`);
        }
        
        if (!partitionStatusResponse.ok) {
            const errorText = await partitionStatusResponse.text();
            throw new Error(`分区状态请求失败: ${partitionStatusResponse.status} ${errorText}`);
        }
        
        const partitionInfo = await partitionInfoResponse.json();
        const partitionStatus = await partitionStatusResponse.json();
        
        if (partitionInfo.success && partitionStatus.success) {
            updatePartitionOverview(partitionStatus.data);
            updatePartitionsTable(partitionInfo.data.partitions);
            console.log('分区数据加载成功');
        } else {
            const errorMsg = partitionInfo.error || partitionStatus.error || '加载分区数据失败';
            throw new Error(errorMsg);
        }
        
    } catch (error) {
        console.error('加载分区数据失败:', error);
        showError('加载分区数据失败: ' + error.message);
        
        // 显示错误状态
        const tbody = document.getElementById('partitionsTableBody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>加载失败: ${error.message}
                    </td>
                </tr>
            `;
        }
    }
}

/**
 * 加载聚合数据
 */
async function loadAggregationData() {
    try {
        console.log('开始加载最新聚合数据...');
        showAggregationLoadingState();
        
        // 获取选中的周期类型
        const periodTypeFilter = document.getElementById('periodTypeFilter');
        const selectedPeriodType = periodTypeFilter ? periodTypeFilter.value : 'daily';
        
        const response = await fetch('/partition-management/aggregations/latest?api=true');
        const data = await response.json();
        
        if (response.ok) {
            // 根据选中的周期类型筛选数据
            let filteredData = [];
            if (data.data && data.data[selectedPeriodType]) {
                filteredData = data.data[selectedPeriodType];
            }
            
            window.aggregationData = filteredData;
            window.filteredAggregationData = [...window.aggregationData];
            window.totalAggregationRecords = filteredData.length;
            window.totalAggregationPages = 1; // 最新数据不需要分页
            
            renderLatestAggregationTable(filteredData, data.summary);
            console.log('聚合数据加载完成');
        } else {
            console.error('API响应失败:', response.status, data);
            showError('加载聚合数据失败: ' + data.error);
        }
    } catch (error) {
        console.error('加载聚合数据时出错:', error);
        showError('加载聚合数据时出错: ' + (error.message || '未知错误'));
    }
}
```

## 后端实现

### 路由定义

```python
# app/routes/database_sizes.py

@database_sizes_bp.route('/aggregations', methods=['GET'])
@login_required
@view_required
def aggregations():
    """
    统计聚合页面或API
    
    如果是页面请求（无查询参数），返回HTML页面
    如果是API请求（有查询参数），返回JSON数据
    """
    # 检查是否有查询参数，如果有则返回API数据
    if request.args:
        try:
            # 获取查询参数
            instance_id = request.args.get('instance_id', type=int)
            db_type = request.args.get('db_type')
            database_name = request.args.get('database_name')
            period_type = request.args.get('period_type')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            # 分页参数
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            # 是否返回所有数据（用于图表显示）
            get_all = request.args.get('get_all', 'false').lower() == 'true'
            
            # 计算offset
            offset = (page - 1) * per_page
            limit = per_page
            
            # 构建查询
            query = DatabaseSizeAggregation.query.join(Instance)
            
            # 过滤掉已删除的数据库
            from app.models.database_size_stat import DatabaseSizeStat
            from sqlalchemy import and_, or_, func
            
            # 子查询：获取每个实例-数据库组合的最新状态
            latest_stats_subquery = db.session.query(
                DatabaseSizeStat.instance_id,
                DatabaseSizeStat.database_name,
                DatabaseSizeStat.is_deleted,
                func.row_number().over(
                    partition_by=[DatabaseSizeStat.instance_id, DatabaseSizeStat.database_name],
                    order_by=DatabaseSizeStat.collected_date.desc()
                ).label('rn')
            ).subquery()
            
            # 主查询：只获取最新状态且未删除的数据库
            active_databases_subquery = db.session.query(
                latest_stats_subquery.c.instance_id,
                latest_stats_subquery.c.database_name
            ).filter(
                and_(
                    latest_stats_subquery.c.rn == 1,
                    latest_stats_subquery.c.is_deleted == False
                )
            ).subquery()
            
            # 关联聚合表和活跃数据库子查询
            query = query.join(
                active_databases_subquery,
                and_(
                    DatabaseSizeAggregation.instance_id == active_databases_subquery.c.instance_id,
                    DatabaseSizeAggregation.database_name == active_databases_subquery.c.database_name
                )
            )
            
            # 应用筛选条件
            if instance_id:
                query = query.filter(DatabaseSizeAggregation.instance_id == instance_id)
            
            if db_type:
                query = query.filter(Instance.db_type == db_type)
            
            if database_name:
                query = query.filter(DatabaseSizeAggregation.database_name == database_name)
            
            if period_type:
                query = query.filter(DatabaseSizeAggregation.period_type == period_type)
            
            if start_date:
                try:
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                    query = query.filter(DatabaseSizeAggregation.period_start >= start_date_obj)
                except ValueError:
                    pass
            
            if end_date:
                try:
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                    query = query.filter(DatabaseSizeAggregation.period_end <= end_date_obj)
                except ValueError:
                    pass
            
            # 排序
            query = query.order_by(
                DatabaseSizeAggregation.period_start.desc(),
                DatabaseSizeAggregation.avg_size_mb.desc()
            )
            
            # 分页或获取所有数据
            if get_all:
                # 图表模式：获取TOP 20数据库或实例
                chart_mode = request.args.get('chart_mode', 'database')
                if chart_mode == 'instance':
                    # 按实例聚合，获取TOP 20实例
                    aggregations = query.limit(500).all()  # 先获取足够多的数据
                    # 按实例分组并计算总大小
                    instance_totals = {}
                    for agg in aggregations:
                        instance_name = agg.instance.name
                        if instance_name not in instance_totals:
                            instance_totals[instance_name] = 0
                        instance_totals[instance_name] += agg.avg_size_mb
                    
                    # 获取TOP 20实例
                    top_instances = sorted(instance_totals.items(), key=lambda x: x[1], reverse=True)[:20]
                    top_instance_names = [name for name, _ in top_instances]
                    
                    # 筛选出TOP 20实例的聚合数据
                    aggregations = [agg for agg in aggregations if agg.instance.name in top_instance_names]
                else:
                    # 按数据库聚合，获取TOP 20数据库
                    aggregations = query.limit(500).all()  # 先获取足够多的数据
                    # 按数据库分组并计算总大小
                    database_totals = {}
                    for agg in aggregations:
                        db_key = f"{agg.instance.name}:{agg.database_name}"
                        if db_key not in database_totals:
                            database_totals[db_key] = 0
                        database_totals[db_key] += agg.avg_size_mb
                    
                    # 获取TOP 20数据库
                    top_databases = sorted(database_totals.items(), key=lambda x: x[1], reverse=True)[:20]
                    top_db_keys = [key for key, _ in top_databases]
                    
                    # 筛选出TOP 20数据库的聚合数据
                    aggregations = [agg for agg in aggregations 
                                  if f"{agg.instance.name}:{agg.database_name}" in top_db_keys]
            else:
                # 分页模式
                total = query.count()
                aggregations = query.offset(offset).limit(limit).all()
            
            # 转换为字典格式
            result = []
            for agg in aggregations:
                result.append({
                    'id': agg.id,
                    'instance': {
                        'id': agg.instance.id,
                        'name': agg.instance.name,
                        'db_type': agg.instance.db_type
                    },
                    'database_name': agg.database_name,
                    'period_type': agg.period_type,
                    'period_start': agg.period_start.isoformat(),
                    'period_end': agg.period_end.isoformat(),
                    'avg_size_mb': float(agg.avg_size_mb) if agg.avg_size_mb else 0,
                    'max_size_mb': float(agg.max_size_mb) if agg.max_size_mb else 0,
                    'min_size_mb': float(agg.min_size_mb) if agg.min_size_mb else 0,
                    'avg_data_size_mb': float(agg.avg_data_size_mb) if agg.avg_data_size_mb else 0,
                    'avg_log_size_mb': float(agg.avg_log_size_mb) if agg.avg_log_size_mb else 0,
                    'data_count': agg.data_count,
                    'calculated_at': agg.calculated_at.isoformat() if agg.calculated_at else None
                })
            
            response_data = {
                'success': True,
                'data': result
            }
            
            if not get_all:
                response_data.update({
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total,
                        'pages': (total + per_page - 1) // per_page
                    }
                })
            
            return jsonify(response_data)
            
        except Exception as e:
            log_error(f"获取聚合数据失败: {e}", module="database_sizes", exc_info=True)
            return jsonify({
                'success': False,
                'error': f'获取聚合数据失败: {str(e)}'
            }), 500
    
    # 返回HTML页面
    return render_template('database_sizes/aggregations.html')


@database_sizes_bp.route('/aggregations/summary', methods=['GET'])
@login_required
@view_required
def aggregations_summary():
    """获取聚合数据汇总"""
    try:
        # 获取实例数量
        total_instances = Instance.query.filter_by(is_active=True).count()
        
        # 获取数据库数量（从最新的聚合数据中统计）
        from sqlalchemy import func, distinct
        
        # 获取最新的聚合数据
        latest_aggregations = db.session.query(
            DatabaseSizeAggregation.instance_id,
            DatabaseSizeAggregation.database_name,
            func.max(DatabaseSizeAggregation.calculated_at).label('latest_calculated_at')
        ).group_by(
            DatabaseSizeAggregation.instance_id,
            DatabaseSizeAggregation.database_name
        ).subquery()
        
        # 关联获取最新聚合数据的详细信息
        latest_agg_details = db.session.query(DatabaseSizeAggregation).join(
            latest_aggregations,
            and_(
                DatabaseSizeAggregation.instance_id == latest_aggregations.c.instance_id,
                DatabaseSizeAggregation.database_name == latest_aggregations.c.database_name,
                DatabaseSizeAggregation.calculated_at == latest_aggregations.c.latest_calculated_at
            )
        ).all()
        
        total_databases = len(latest_agg_details)
        
        # 计算平均大小和最大大小
        if latest_agg_details:
            avg_sizes = [agg.avg_size_mb for agg in latest_agg_details if agg.avg_size_mb]
            max_sizes = [agg.max_size_mb for agg in latest_agg_details if agg.max_size_mb]
            
            average_size_mb = sum(avg_sizes) / len(avg_sizes) if avg_sizes else 0
            max_size_mb = max(max_sizes) if max_sizes else 0
        else:
            average_size_mb = 0
            max_size_mb = 0
        
        return jsonify({
            'success': True,
            'data': {
                'total_instances': total_instances,
                'total_databases': total_databases,
                'average_size_mb': average_size_mb,
                'max_size_mb': max_size_mb
            }
        })
        
    except Exception as e:
        log_error(f"获取聚合汇总失败: {e}", module="database_sizes", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'获取聚合汇总失败: {str(e)}'
        }), 500


@database_sizes_bp.route('/aggregate-today', methods=['POST'])
@login_required
@update_required
def aggregate_today():
    """手动触发今日数据聚合"""
    try:
        from app.services.database_size_aggregation_service import DatabaseSizeAggregationService
        
        service = DatabaseSizeAggregationService()
        result = service.calculate_today_aggregations()
        
        if result.get('status') == 'success':
            return jsonify({
                'success': True,
                'message': '今日数据聚合完成',
                'data': result
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', '聚合失败')
            }), 500
            
    except Exception as e:
        log_error(f"手动聚合今日数据失败: {e}", module="database_sizes", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'聚合今日数据失败: {str(e)}'
        }), 500
```

### 核心服务实现

#### 数据库大小统计聚合服务

```python
# app/services/database_size_aggregation_service.py

class DatabaseSizeAggregationService:
    """数据库大小统计聚合服务"""
    
    def __init__(self):
        self.period_types = ['daily', 'weekly', 'monthly', 'quarterly']
    
    def calculate_all_aggregations(self) -> Dict[str, Any]:
        """
        计算所有实例的统计聚合数据
        """
        try:
            results = {}
            total_aggregations = 0
            
            for period_type in self.period_types:
                if period_type == 'daily':
                    result = self.calculate_daily_aggregations()
                elif period_type == 'weekly':
                    result = self.calculate_weekly_aggregations()
                elif period_type == 'monthly':
                    result = self.calculate_monthly_aggregations()
                elif period_type == 'quarterly':
                    result = self.calculate_quarterly_aggregations()
                else:
                    continue
                
                results[period_type] = result
                if result.get('status') == 'success':
                    total_aggregations += result.get('total_records', 0)
            
            return {
                'status': 'success',
                'total_aggregations': total_aggregations,
                'results': results
            }
            
        except Exception as e:
            log_error(f"计算所有聚合数据失败: {e}", module="aggregation", exc_info=True)
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def calculate_daily_aggregations(self) -> Dict[str, Any]:
        """
        计算每日统计聚合（定时任务用，处理昨天的数据）
        """
        try:
            # 计算昨天的日期范围
            yesterday = date.today() - timedelta(days=1)
            start_date = yesterday
            end_date = yesterday
            
            return self._calculate_aggregations('daily', start_date, end_date)
            
        except Exception as e:
            log_error(f"计算每日聚合失败: {e}", module="aggregation", exc_info=True)
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def calculate_today_aggregations(self) -> Dict[str, Any]:
        """
        计算今日统计聚合（手动触发用，处理今天的数据）
        """
        try:
            # 计算今天的日期范围
            today = date.today()
            start_date = today
            end_date = today
            
            return self._calculate_aggregations('daily', start_date, end_date)
            
        except Exception as e:
            log_error(f"计算今日聚合失败: {e}", module="aggregation", exc_info=True)
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def calculate_weekly_aggregations(self) -> Dict[str, Any]:
        """
        计算每周统计聚合
        """
        try:
            # 计算上周的日期范围
            today = date.today()
            days_since_monday = today.weekday()
            last_monday = today - timedelta(days=days_since_monday + 7)
            last_sunday = last_monday + timedelta(days=6)
            
            return self._calculate_aggregations('weekly', last_monday, last_sunday)
            
        except Exception as e:
            log_error(f"计算每周聚合失败: {e}", module="aggregation", exc_info=True)
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def calculate_monthly_aggregations(self) -> Dict[str, Any]:
        """
        计算每月统计聚合
        """
        try:
            # 计算上个月的日期范围
            today = date.today()
            first_day_this_month = today.replace(day=1)
            last_day_last_month = first_day_this_month - timedelta(days=1)
            first_day_last_month = last_day_last_month.replace(day=1)
            
            return self._calculate_aggregations('monthly', first_day_last_month, last_day_last_month)
            
        except Exception as e:
            log_error(f"计算每月聚合失败: {e}", module="aggregation", exc_info=True)
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def calculate_quarterly_aggregations(self) -> Dict[str, Any]:
        """
        计算每季度统计聚合
        """
        try:
            # 计算上个季度的日期范围
            today = date.today()
            current_quarter = (today.month - 1) // 3 + 1
            
            if current_quarter == 1:
                # 当前是Q1，上个季度是去年Q4
                last_quarter_year = today.year - 1
                start_month = 10
                end_month = 12
            else:
                # 其他情况
                last_quarter_year = today.year
                start_month = (current_quarter - 2) * 3 + 1
                end_month = (current_quarter - 1) * 3
            
            start_date = date(last_quarter_year, start_month, 1)
            
            # 计算季度最后一天
            if end_month == 12:
                end_date = date(last_quarter_year, 12, 31)
            else:
                next_month_first_day = date(last_quarter_year, end_month + 1, 1)
                end_date = next_month_first_day - timedelta(days=1)
            
            return self._calculate_aggregations('quarterly', start_date, end_date)
            
        except Exception as e:
            log_error(f"计算每季度聚合失败: {e}", module="aggregation", exc_info=True)
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def _calculate_aggregations(self, period_type: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        计算指定周期的统计聚合
        """
        try:
            log_info(f"开始计算 {period_type} 聚合数据: {start_date} 到 {end_date}", module="aggregation")
            
            # 获取所有活跃实例
            active_instances = Instance.query.filter_by(is_active=True).all()
            
            if not active_instances:
                log_warning("没有找到活跃的实例", module="aggregation")
                return {
                    'status': 'success',
                    'message': '没有活跃实例需要聚合',
                    'total_records': 0
                }
            
            total_aggregations = 0
            processed_instances = 0
            failed_instances = 0
            
            for instance in active_instances:
                try:
                    # 获取该实例在指定时间范围内的数据库大小统计
                    stats = DatabaseSizeStat.query.filter(
                        DatabaseSizeStat.instance_id == instance.id,
                        DatabaseSizeStat.collected_date >= start_date,
                        DatabaseSizeStat.collected_date <= end_date,
                        DatabaseSizeStat.is_deleted == False
                    ).all()
                    
                    if not stats:
                        log_debug(f"实例 {instance.name} 在 {start_date} 到 {end_date} 期间没有数据", module="aggregation")
                        continue
                    
                    # 按数据库名称分组
                    database_stats = {}
                    for stat in stats:
                        if stat.database_name not in database_stats:
                            database_stats[stat.database_name] = []
                        database_stats[stat.database_name].append(stat)
                    
                    # 为每个数据库计算聚合数据
                    for database_name, db_stats in database_stats.items():
                        self._calculate_database_aggregation(
                            instance.id, database_name, period_type, 
                            start_date, end_date, db_stats
                        )
                        total_aggregations += 1
                    
                    processed_instances += 1
                    log_debug(f"完成实例 {instance.name} 的聚合计算", module="aggregation")
                    
                except Exception as e:
                    failed_instances += 1
                    log_error(f"实例 {instance.name} 聚合计算失败: {e}", module="aggregation", exc_info=True)
                    continue
            
            # 提交数据库事务
            db.session.commit()
            
            log_info(f"{period_type} 聚合完成: 处理 {processed_instances} 个实例, 失败 {failed_instances} 个, 生成 {total_aggregations} 条聚合记录", 
                    module="aggregation")
            
            return {
                'status': 'success',
                'message': f'{period_type} 聚合计算完成',
                'total_records': total_aggregations,
                'processed_instances': processed_instances,
                'failed_instances': failed_instances,
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat()
            }
            
        except Exception as e:
            db.session.rollback()
            log_error(f"计算 {period_type} 聚合失败: {e}", module="aggregation", exc_info=True)
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def _calculate_database_aggregation(self, instance_id: int, database_name: str, 
                                      period_type: str, start_date: date, end_date: date, 
                                      stats: List[DatabaseSizeStat]) -> None:
        """
        计算单个数据库的统计聚合
        """
        try:
            if not stats:
                return
            
            # 检查是否已存在相同的聚合记录
            existing = DatabaseSizeAggregation.query.filter(
                DatabaseSizeAggregation.instance_id == instance_id,
                DatabaseSizeAggregation.database_name == database_name,
                DatabaseSizeAggregation.period_type == period_type,
                DatabaseSizeAggregation.period_start == start_date,
                DatabaseSizeAggregation.period_end == end_date
            ).first()
            
            # 计算统计指标
            total_sizes = [stat.total_size_mb for stat in stats if stat.total_size_mb is not None]
            data_sizes = [stat.data_size_mb for stat in stats if stat.data_size_mb is not None]
            log_sizes = [stat.log_size_mb for stat in stats if stat.log_size_mb is not None]
            
            if not total_sizes:
                log_warning(f"数据库 {database_name} 没有有效的大小数据", module="aggregation")
                return
            
            # 计算聚合指标
            avg_size_mb = sum(total_sizes) / len(total_sizes)
            max_size_mb = max(total_sizes)
            min_size_mb = min(total_sizes)
            avg_data_size_mb = sum(data_sizes) / len(data_sizes) if data_sizes else None
            avg_log_size_mb = sum(log_sizes) / len(log_sizes) if log_sizes else None
            data_count = len(stats)
            
            if existing:
                # 更新现有记录
                existing.avg_size_mb = avg_size_mb
                existing.max_size_mb = max_size_mb
                existing.min_size_mb = min_size_mb
                existing.avg_data_size_mb = avg_data_size_mb
                existing.avg_log_size_mb = avg_log_size_mb
                existing.data_count = data_count
                existing.calculated_at = now()
                
                log_debug(f"更新聚合记录: {database_name} ({period_type})", module="aggregation")
            else:
                # 创建新记录
                aggregation = DatabaseSizeAggregation(
                    instance_id=instance_id,
                    database_name=database_name,
                    period_type=period_type,
                    period_start=start_date,
                    period_end=end_date,
                    avg_size_mb=avg_size_mb,
                    max_size_mb=max_size_mb,
                    min_size_mb=min_size_mb,
                    avg_data_size_mb=avg_data_size_mb,
                    avg_log_size_mb=avg_log_size_mb,
                    data_count=data_count,
                    calculated_at=now()
                )
                
                db.session.add(aggregation)
                log_debug(f"创建聚合记录: {database_name} ({period_type})", module="aggregation")
            
            # 计算增量/减量统计
            self._calculate_change_statistics(aggregation if not existing else existing, 
                                            instance_id, database_name, period_type, start_date, end_date)
            
        except Exception as e:
            log_error(f"计算数据库 {database_name} 聚合失败: {e}", module="aggregation", exc_info=True)
            raise e
    
    def _calculate_change_statistics(self, aggregation, instance_id: int, database_name: str, 
                                   period_type: str, start_date: date, end_date: date) -> None:
        """
        计算增量/减量统计
        """
        try:
            # 获取上一个周期的聚合数据
            prev_start_date, prev_end_date = self._get_previous_period_dates(period_type, start_date, end_date)
            
            previous_agg = DatabaseSizeAggregation.query.filter(
                DatabaseSizeAggregation.instance_id == instance_id,
                DatabaseSizeAggregation.database_name == database_name,
                DatabaseSizeAggregation.period_type == period_type,
                DatabaseSizeAggregation.period_start == prev_start_date,
                DatabaseSizeAggregation.period_end == prev_end_date
            ).first()
            
            if previous_agg:
                # 计算变化量
                size_change_mb = aggregation.avg_size_mb - previous_agg.avg_size_mb
                size_change_percent = (size_change_mb / previous_agg.avg_size_mb * 100) if previous_agg.avg_size_mb > 0 else 0
                
                # 更新聚合记录的变化统计
                aggregation.size_change_mb = size_change_mb
                aggregation.size_change_percent = size_change_percent
                
                log_debug(f"计算变化统计: {database_name} 变化 {size_change_mb:.2f} MB ({size_change_percent:.2f}%)", 
                         module="aggregation")
            
        except Exception as e:
            log_error(f"计算变化统计失败: {e}", module="aggregation", exc_info=True)
            # 变化统计失败不影响主要聚合过程
            pass
    
    def _get_previous_period_dates(self, period_type: str, start_date: date, end_date: date) -> tuple:
        """
        获取上一个周期的日期范围
        """
        if period_type == 'daily':
            prev_start = start_date - timedelta(days=1)
            prev_end = end_date - timedelta(days=1)
        elif period_type == 'weekly':
            prev_start = start_date - timedelta(weeks=1)
            prev_end = end_date - timedelta(weeks=1)
        elif period_type == 'monthly':
            # 上个月
            if start_date.month == 1:
                prev_year = start_date.year - 1
                prev_month = 12
            else:
                prev_year = start_date.year
                prev_month = start_date.month - 1
            
            prev_start = date(prev_year, prev_month, 1)
            
            # 计算上个月的最后一天
            if prev_month == 12:
                next_month_first = date(prev_year + 1, 1, 1)
            else:
                next_month_first = date(prev_year, prev_month + 1, 1)
            prev_end = next_month_first - timedelta(days=1)
            
        elif period_type == 'quarterly':
            # 上个季度
            current_quarter = (start_date.month - 1) // 3 + 1
            if current_quarter == 1:
                prev_quarter = 4
                prev_year = start_date.year - 1
            else:
                prev_quarter = current_quarter - 1
                prev_year = start_date.year
            
            prev_start_month = (prev_quarter - 1) * 3 + 1
            prev_start = date(prev_year, prev_start_month, 1)
            
            prev_end_month = prev_quarter * 3
            if prev_end_month == 12:
                next_quarter_first = date(prev_year + 1, 1, 1)
            else:
                next_quarter_first = date(prev_year, prev_end_month + 1, 1)
            prev_end = next_quarter_first - timedelta(days=1)
        else:
            raise ValueError(f"不支持的周期类型: {period_type}")
        
        return prev_start, prev_end
    
    def get_aggregations(self, instance_id: int, period_type: str, 
                        start_date: date = None, end_date: date = None,
                        database_name: str = None) -> List[Dict[str, Any]]:
        """
        获取统计聚合数据
        """
        try:
            query = DatabaseSizeAggregation.query.filter(
                DatabaseSizeAggregation.instance_id == instance_id,
                DatabaseSizeAggregation.period_type == period_type
            )
            
            if start_date:
                query = query.filter(DatabaseSizeAggregation.period_start >= start_date)
            
            if end_date:
                query = query.filter(DatabaseSizeAggregation.period_end <= end_date)
            
            if database_name:
                query = query.filter(DatabaseSizeAggregation.database_name == database_name)
            
            aggregations = query.order_by(DatabaseSizeAggregation.period_start.desc()).all()
            
            return [self._format_aggregation(agg) for agg in aggregations]
            
        except Exception as e:
            log_error(f"获取聚合数据失败: {e}", module="aggregation", exc_info=True)
            return []
    
    def get_trends_analysis(self, instance_id: int, period_type: str, 
                           months: int = 12) -> Dict[str, Any]:
        """
        获取趋势分析数据
        """
        try:
            # 计算时间范围
            end_date = date.today()
            start_date = end_date - timedelta(days=months * 30)  # 近似计算
            
            aggregations = self.get_aggregations(instance_id, period_type, start_date, end_date)
            
            if not aggregations:
                return {
                    'status': 'no_data',
                    'message': '没有找到趋势数据'
                }
            
            # 按数据库分组
            database_trends = {}
            for agg in aggregations:
                db_name = agg['database_name']
                if db_name not in database_trends:
                    database_trends[db_name] = []
                database_trends[db_name].append(agg)
            
            # 计算趋势指标
            trends = {}
            for db_name, db_aggs in database_trends.items():
                if len(db_aggs) < 2:
                    continue
                
                # 按时间排序
                db_aggs.sort(key=lambda x: x['period_start'])
                
                # 计算增长率
                first_size = db_aggs[0]['avg_size_mb']
                last_size = db_aggs[-1]['avg_size_mb']
                
                if first_size > 0:
                    growth_rate = (last_size - first_size) / first_size * 100
                else:
                    growth_rate = 0
                
                trends[db_name] = {
                    'growth_rate': growth_rate,
                    'first_size_mb': first_size,
                    'last_size_mb': last_size,
                    'data_points': len(db_aggs),
                    'period_start': db_aggs[0]['period_start'],
                    'period_end': db_aggs[-1]['period_end']
                }
            
            return {
                'status': 'success',
                'trends': trends,
                'analysis_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'months': months
                }
            }
            
        except Exception as e:
            log_error(f"获取趋势分析失败: {e}", module="aggregation", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _format_aggregation(self, aggregation: DatabaseSizeAggregation) -> Dict[str, Any]:
        """
        格式化聚合数据
        """
        return {
            'id': aggregation.id,
            'instance_id': aggregation.instance_id,
            'database_name': aggregation.database_name,
            'period_type': aggregation.period_type,
            'period_start': aggregation.period_start.isoformat(),
            'period_end': aggregation.period_end.isoformat(),
            'avg_size_mb': float(aggregation.avg_size_mb) if aggregation.avg_size_mb else 0,
            'max_size_mb': float(aggregation.max_size_mb) if aggregation.max_size_mb else 0,
            'min_size_mb': float(aggregation.min_size_mb) if aggregation.min_size_mb else 0,
            'avg_data_size_mb': float(aggregation.avg_data_size_mb) if aggregation.avg_data_size_mb else None,
            'avg_log_size_mb': float(aggregation.avg_log_size_mb) if aggregation.avg_log_size_mb else None,
            'data_count': aggregation.data_count,
            'size_change_mb': float(aggregation.size_change_mb) if aggregation.size_change_mb else None,
            'size_change_percent': float(aggregation.size_change_percent) if aggregation.size_change_percent else None,
            'calculated_at': aggregation.calculated_at.isoformat() if aggregation.calculated_at else None
        }
```

### 数据模型

```python
# app/models/database_size_aggregation.py

class DatabaseSizeAggregation(db.Model):
    """数据库大小统计聚合模型"""
    __tablename__ = "database_size_aggregations"
    
    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(db.Integer, db.ForeignKey("instances.id"), nullable=False, index=True)
    database_name = db.Column(db.String(255), nullable=False, index=True)
    period_type = db.Column(db.String(20), nullable=False, index=True)  # daily, weekly, monthly, quarterly
    period_start = db.Column(db.Date, nullable=False, index=True)
    period_end = db.Column(db.Date, nullable=False, index=True)
    
    # 统计指标
    avg_size_mb = db.Column(db.Numeric(15, 2))
    max_size_mb = db.Column(db.Numeric(15, 2))
    min_size_mb = db.Column(db.Numeric(15, 2))
    avg_data_size_mb = db.Column(db.Numeric(15, 2))
    avg_log_size_mb = db.Column(db.Numeric(15, 2))
    data_count = db.Column(db.Integer)
    
    # 变化统计
    size_change_mb = db.Column(db.Numeric(15, 2))
    size_change_percent = db.Column(db.Numeric(8, 4))
    
    calculated_at = db.Column(db.DateTime(timezone=True), default=now)
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now)
    
    # 关系
    instance = db.relationship("Instance", backref="size_aggregations")
    
    # 索引
    __table_args__ = (
        db.Index('idx_aggregation_instance_db_period', 'instance_id', 'database_name', 'period_type'),
        db.Index('idx_aggregation_period_dates', 'period_start', 'period_end'),
        db.Index('idx_aggregation_calculated_at', 'calculated_at'),
    )
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'instance_id': self.instance_id,
            'database_name': self.database_name,
            'period_type': self.period_type,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'avg_size_mb': float(self.avg_size_mb) if self.avg_size_mb else 0,
            'max_size_mb': float(self.max_size_mb) if self.max_size_mb else 0,
            'min_size_mb': float(self.min_size_mb) if self.min_size_mb else 0,
            'avg_data_size_mb': float(self.avg_data_size_mb) if self.avg_data_size_mb else None,
            'avg_log_size_mb': float(self.avg_log_size_mb) if self.avg_log_size_mb else None,
            'data_count': self.data_count,
            'size_change_mb': float(self.size_change_mb) if self.size_change_mb else None,
            'size_change_percent': float(self.size_change_percent) if self.size_change_percent else None,
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None
        }


# app/models/database_size_stat.py

class DatabaseSizeStat(db.Model):
    """数据库大小统计模型"""
    __tablename__ = "database_size_stats"
    
    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(db.Integer, db.ForeignKey("instances.id"), nullable=False, index=True)
    database_name = db.Column(db.String(255), nullable=False, index=True)
    
    # 大小信息
    total_size_mb = db.Column(db.Numeric(15, 2))
    data_size_mb = db.Column(db.Numeric(15, 2))
    log_size_mb = db.Column(db.Numeric(15, 2))
    index_size_mb = db.Column(db.Numeric(15, 2))
    
    # 其他统计信息
    table_count = db.Column(db.Integer)
    row_count = db.Column(db.BigInteger)
    
    # 状态信息
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    collected_date = db.Column(db.Date, nullable=False, index=True)
    collected_at = db.Column(db.DateTime(timezone=True), default=now)
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now)
    
    # 关系
    instance = db.relationship("Instance", backref="size_stats")
    
    # 索引
    __table_args__ = (
        db.Index('idx_size_stat_instance_db', 'instance_id', 'database_name'),
        db.Index('idx_size_stat_collected_date', 'collected_date'),
        db.Index('idx_size_stat_is_deleted', 'is_deleted'),
    )
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'instance_id': self.instance_id,
            'database_name': self.database_name,
            'total_size_mb': float(self.total_size_mb) if self.total_size_mb else 0,
            'data_size_mb': float(self.data_size_mb) if self.data_size_mb else 0,
            'log_size_mb': float(self.log_size_mb) if self.log_size_mb else 0,
            'index_size_mb': float(self.index_size_mb) if self.index_size_mb else 0,
            'table_count': self.table_count,
            'row_count': self.row_count,
            'is_deleted': self.is_deleted,
            'collected_date': self.collected_date.isoformat() if self.collected_date else None,
            'collected_at': self.collected_at.isoformat() if self.collected_at else None
        }
```

## 核心功能

### 1. 统计聚合
- **多周期聚合**: 支持日、周、月、季度统计聚合
- **自动计算**: 定时任务自动计算统计聚合数据
- **手动触发**: 支持手动触发今日数据聚合
- **增量统计**: 计算相比上一周期的变化量和变化百分比

### 2. 数据可视化
- **趋势图表**: 使用Chart.js绘制数据库容量趋势图
- **多种图表**: 支持折线图和柱状图两种显示方式
- **双模式**: 支持按数据库和按实例两种聚合模式
- **TOP 20**: 显示容量最大的前20个数据库或实例

### 3. 筛选和搜索
- **多维筛选**: 支持按实例、数据库类型、周期类型、时间范围筛选
- **实时搜索**: 支持实时搜索数据库和实例名称
- **联动筛选**: 数据库类型和实例选择联动更新

### 4. 分区管理
- **分区状态**: 显示数据库分区的状态和统计信息
- **分区操作**: 支持创建新分区和清理旧分区
- **聚合数据表**: 显示最新的聚合统计数据

### 5. 性能监控
- **容量分析**: 分析数据库容量使用情况和增长趋势
- **性能指标**: 监控数据库大小变化和性能指标
- **告警机制**: 支持容量异常告警和趋势预警

## API接口

### 获取聚合数据

**接口**: `GET /database-sizes/aggregations`

**参数**:
- `instance_id`: 实例ID（可选）
- `db_type`: 数据库类型（可选）
- `database_name`: 数据库名称（可选）
- `period_type`: 周期类型（可选）
- `start_date`: 开始日期（可选）
- `end_date`: 结束日期（可选）
- `page`: 页码（可选，默认1）
- `per_page`: 每页数量（可选，默认20）
- `get_all`: 是否获取所有数据（可选，用于图表）
- `chart_mode`: 图表模式（可选，database/instance）

**响应格式**:
```json
{
    "success": true,
    "data": [
        {
            "id": 1,
            "instance": {
                "id": 1,
                "name": "MySQL-01",
                "db_type": "mysql"
            },
            "database_name": "test_db",
            "period_type": "daily",
            "period_start": "2025-01-01",
            "period_end": "2025-01-01",
            "avg_size_mb": 1024.5,
            "max_size_mb": 1100.0,
            "min_size_mb": 950.0,
            "avg_data_size_mb": 800.0,
            "avg_log_size_mb": 224.5,
            "data_count": 24,
            "calculated_at": "2025-01-02T08:00:00Z"
        }
    ],
    "pagination": {
        "page": 1,
        "per_page": 20,
        "total": 100,
        "pages": 5
    }
}
```

### 获取聚合汇总

**接口**: `GET /database-sizes/aggregations/summary`

**响应格式**:
```json
{
    "success": true,
    "data": {
        "total_instances": 15,
        "total_databases": 120,
        "average_size_mb": 2048.5,
        "max_size_mb": 10240.0
    }
}
```

### 手动聚合今日数据

**接口**: `POST /database-sizes/aggregate-today`

**响应格式**:
```json
{
    "success": true,
    "message": "今日数据聚合完成",
    "data": {
        "status": "success",
        "total_records": 25,
        "processed_instances": 5,
        "failed_instances": 0
    }
}
```

## 性能优化

### 1. 数据库优化
- 使用复合索引优化查询性能
- 分区表存储历史聚合数据
- 定期清理过期数据

### 2. 缓存策略
- 聚合数据缓存1小时
- 汇总数据缓存30分钟
- 图表数据客户端缓存

### 3. 前端优化
- 图表数据懒加载
- 虚拟滚动处理大量数据
- 防抖处理用户输入

## 安全考虑

### 1. 权限控制
- 查看权限验证
- 操作权限验证
- 数据访问权限控制

### 2. 数据安全
- 敏感数据脱敏
- 审计日志记录
- 数据传输加密

## 测试策略

### 1. 单元测试
- 聚合计算逻辑测试
- 数据格式化测试
- 错误处理测试

### 2. 集成测试
- API接口测试
- 数据库操作测试
- 前后端集成测试

### 3. 性能测试
- 大数据量聚合性能测试
- 并发访问测试
- 内存使用测试

## 部署注意事项

### 1. 数据库配置
- 创建必要的索引
- 配置分区表
- 设置数据保留策略

### 2. 定时任务
- 配置聚合任务调度
- 监控任务执行状态
- 设置任务失败告警

### 3. 监控告警
- 配置性能监控
- 设置容量告警阈值
- 监控API响应时间

## 扩展功能

### 1. 高级分析
- 容量预测分析
- 异常检测算法
- 智能告警规则

### 2. 报表功能
- 定期容量报告
- 趋势分析报告
- 自定义报表模板

### 3. 集成功能
- 与监控系统集成
- 与告警系统集成
- 与自动化运维集成

## 维护指南

### 1. 日常维护
- 检查聚合任务执行状态
- 监控数据库性能
- 清理过期数据

### 2. 故障排查
- 聚合任务失败排查
- 数据不一致问题排查
- 性能问题分析

### 3. 数据管理
- 历史数据归档
- 数据备份策略
- 数据恢复流程
