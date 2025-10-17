/**
 * 聚合数据图表管理器
 * 基于 Chart.js 4.4.0 和 jQuery 3.7.1
 */

class AggregationsChartManager {
    constructor() {
        this.chart = null;
        this.currentData = [];
        this.currentChartType = 'line'; // 固定为折线图
        this.currentPeriodType = 'daily';
        this.chartColors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
            '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF',
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
            '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F'
        ];
        
        // 为不同类型的聚合数据定义颜色和样式
        this.dataTypeStyles = {
            '数据库聚合': { color: '#FF6384', borderDash: [], pointStyle: 'circle' },
            '实例聚合': { color: '#36A2EB', borderDash: [5, 5], pointStyle: 'rect' },
            '数据库统计': { color: '#FFCE56', borderDash: [10, 5], pointStyle: 'triangle' },
            '实例统计': { color: '#4BC0C0', borderDash: [2, 2], pointStyle: 'star' }
        };
        
        this.init();
    }
    
    init() {
        console.log('初始化聚合数据图表管理器');
        this.bindEvents();
        this.loadChartData();
        this.createLegend();
    }
    
    /**
     * 创建图例说明
     */
    createLegend() {
        const legendContainer = document.getElementById('chartLegend');
        if (!legendContainer) return;
        
        // 根据当前统计周期生成图例说明
        const periodType = this.currentPeriodType;
        let legendHtml = '';
        
        if (periodType === 'daily') {
            legendHtml = `
                <div class="chart-legend">
                    <h6>核心指标说明：</h6>
                    <div class="legend-items">
                        <div class="legend-item">
                            <span class="legend-color" style="background: linear-gradient(90deg, rgba(54, 162, 235, 0.7) 0%, rgba(255, 99, 132, 0.7) 100%); width: 30px; height: 4px; display: inline-block; margin-right: 8px; border-radius: 2px;"></span>
                            <span class="legend-text">📊 实例数总量（蓝色实线，70%透明度）+ 实例日统计数量（红色实线，70%透明度）→ 紫色偏粉红混合效果</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background: linear-gradient(90deg, rgba(75, 192, 192, 0.7) 0%, rgba(255, 159, 64, 0.7) 100%); width: 30px; height: 4px; display: inline-block; margin-right: 8px; border-radius: 2px;"></span>
                            <span class="legend-text">🗄️ 数据库数总量（绿色实线，70%透明度）+ 数据库日统计数量（橙色实线，70%透明度）→ 黄绿色混合效果</span>
                        </div>
                    </div>
                    <div class="alert alert-info mt-2" style="font-size: 0.85em;">
                        <i class="fas fa-info-circle me-1"></i>
                        <strong>颜色混合设计：</strong>每条组合线由两条高透明度的实线叠加而成，产生真正的颜色混合效果。蓝色+红色=紫色偏粉红，绿色+橙色=黄绿色。
                    </div>
                </div>
            `;
        } else if (periodType === 'weekly') {
            legendHtml = `
                <div class="chart-legend">
                    <h6>核心指标说明：</h6>
                    <div class="legend-items">
                        <div class="legend-item">
                            <span class="legend-color" style="background: linear-gradient(90deg, #36A2EB 0%, #FF6384 100%); width: 30px; height: 4px; display: inline-block; margin-right: 8px; border-radius: 2px;"></span>
                            <span class="legend-text">📊 实例数平均值（周）（蓝色实线）+ 实例周统计数量（红色虚线）→ 紫色偏粉红混合效果</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background: linear-gradient(90deg, #4BC0C0 0%, #FF9F40 100%); width: 30px; height: 4px; display: inline-block; margin-right: 8px; border-radius: 2px;"></span>
                            <span class="legend-text">🗄️ 数据库数平均值（周）（绿色实线）+ 数据库周统计数量（橙色虚线）→ 黄绿色混合效果</span>
                        </div>
                    </div>
                    <div class="alert alert-info mt-2" style="font-size: 0.85em;">
                        <i class="fas fa-info-circle me-1"></i>
                        <strong>颜色混合设计：</strong>每条组合线由两种不同颜色的线叠加而成，产生颜色混合效果。粗实线表示原始数据，细虚线表示聚合数据，叠加时形成新的混合颜色。
                    </div>
                </div>
            `;
        } else if (periodType === 'monthly') {
            legendHtml = `
                <div class="chart-legend">
                    <h6>核心指标说明：</h6>
                    <div class="legend-items">
                        <div class="legend-item">
                            <span class="legend-color" style="background-color: #FF6384;"></span>
                            <span class="legend-text">📊 实例数平均值（月） - 每月采集的实例数量平均值</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background-color: #36A2EB;"></span>
                            <span class="legend-text">🗄️ 数据库数平均值（月） - 每月采集的数据库数量平均值</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background-color: #FFCE56; border-style: dashed;"></span>
                            <span class="legend-text">📈 实例月统计数量 - 聚合统计下的实例月统计数量</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background-color: #4BC0C0; border-style: dashed;"></span>
                            <span class="legend-text">📈 数据库月统计数量 - 聚合统计下的数据库月统计数量</span>
                        </div>
                    </div>
                </div>
            `;
        } else if (periodType === 'quarterly') {
            legendHtml = `
                <div class="chart-legend">
                    <h6>核心指标说明：</h6>
                    <div class="legend-items">
                        <div class="legend-item">
                            <span class="legend-color" style="background-color: #FF6384;"></span>
                            <span class="legend-text">📊 实例数平均值（季） - 每季采集的实例数量平均值</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background-color: #36A2EB;"></span>
                            <span class="legend-text">🗄️ 数据库数平均值（季） - 每季采集的数据库数量平均值</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background-color: #FFCE56; border-style: dashed;"></span>
                            <span class="legend-text">📈 实例季统计数量 - 聚合统计下的实例季统计数量</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background-color: #4BC0C0; border-style: dashed;"></span>
                            <span class="legend-text">📈 数据库季统计数量 - 聚合统计下的数据库季统计数量</span>
                        </div>
                    </div>
                </div>
            `;
        }
        
        legendContainer.innerHTML = legendHtml;
    }
    
    bindEvents() {
        // 周期类型切换
        $('input[name="periodType"]').on('change', (e) => {
            this.currentPeriodType = e.target.value;
            this.updateChartInfo();
            this.createLegend(); // 重新创建图例
            this.loadChartData();
        });
        
        // 刷新按钮
        $('#refreshAggregations').on('click', () => {
            this.refreshAllData();
        });
    }
    
    
    /**
     * 更新图表信息
     */
    updateChartInfo() {
        const periodNames = {
            'daily': '日核心指标趋势',
            'weekly': '周核心指标趋势', 
            'monthly': '月核心指标趋势',
            'quarterly': '季度核心指标趋势'
        };
        
        const periodSubtitles = {
            'daily': '最近7天的核心指标统计',
            'weekly': '最近7周的核心指标统计',
            'monthly': '最近7个月的核心指标统计', 
            'quarterly': '最近7个季度的核心指标统计'
        };
        
        $('#chartTitle').text(periodNames[this.currentPeriodType]);
        $('#chartSubtitle').text(periodSubtitles[this.currentPeriodType]);
    }
    
    /**
     * 加载图表数据
     */
    async loadChartData() {
        this.showChartLoading(true);
        
        try {
            const params = new URLSearchParams({
                period_type: this.currentPeriodType,
                days: 7
            });
            
            const response = await fetch(`/partition/api/aggregations/core-metrics?${params}`);
            const raw = await response.json();
            if (response.ok && raw.success !== false) {
                const payload = raw?.data ?? raw ?? {};
                this.currentData = payload;
                this.renderChart(payload);
                this.updateChartStats(payload);
            } else {
                console.error('加载图表数据失败:', response.statusText);
                this.showError('加载图表数据失败');
            }
        } catch (error) {
            console.error('加载图表数据异常:', error);
            this.showError('加载图表数据异常');
        } finally {
            this.showChartLoading(false);
        }
    }
    
    /**
     * 渲染图表
     */
    renderChart(data) {
        const ctx = document.getElementById('aggregationsChart').getContext('2d');
        
        // 销毁现有图表
        if (this.chart) {
            this.chart.destroy();
        }
        
        const chartData = this.prepareChartData(data);
        
        // 如果有数据，隐藏消息
        if (chartData.labels.length > 0 && chartData.datasets.length > 0) {
            this.hideChartMessage();
        }
        
        this.chart = new Chart(ctx, {
            type: this.currentChartType,
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: false
                    },
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: 20,
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#007bff',
                        borderWidth: 1,
                        callbacks: {
                            title: function(context) {
                                return '时间: ' + context[0].label;
                            },
                            label: function(context) {
                                const label = context.dataset.label || '';
                                const value = context.parsed.y;
                                // 如果是聚合数据数量，直接显示数字
                                if (data.yAxisLabel && data.yAxisLabel.includes('数量')) {
                                    return `${label}: ${value} 条`;
                                }
                                // 否则使用原来的大小格式化
                                return `${label}: ${AggregationsChartManager.formatSizeFromMB(value)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: '时间',
                            font: {
                                size: 14,
                                weight: 'bold'
                            }
                        },
                        grid: {
                            display: true,
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: data.yAxisLabel || '聚合数据数量',
                            font: {
                                size: 14,
                                weight: 'bold'
                            }
                        },
                        beginAtZero: true,
                        grid: {
                            display: true,
                            color: 'rgba(0, 0, 0, 0.1)'
                        },
                        ticks: {
                            callback: function(value) {
                                // 如果是聚合数据数量，直接显示数字
                                if (data.yAxisLabel && data.yAxisLabel.includes('数量')) {
                                    return value;
                                }
                                // 否则使用原来的大小格式化
                                return AggregationsChartManager.formatSizeFromMB(value);
                            }
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                },
                animation: {
                    duration: 1000,
                    easing: 'easeInOutQuart'
                }
            }
        });
    }
    
    /**
     * 准备图表数据
     */
    prepareChartData(data) {
        // 检查数据格式 - 新API直接返回Chart.js格式
        if (data.labels && data.datasets) {
            // 新格式：直接返回Chart.js数据
            if (data.labels.length === 0 || data.datasets.length === 0) {
                this.showChartMessage(data.message || '暂无聚合数据');
                return {
                    labels: [],
                    datasets: []
                };
            }
            return {
                labels: data.labels || [],
                datasets: data.datasets || []
            };
        }
        
        // 旧格式：处理原始数据
        if (!data || !data.length) {
            this.showChartMessage('暂无数据');
            return {
                labels: [],
                datasets: []
            };
        }
        
        // 按日期分组数据
        const groupedData = this.groupDataByDate(data);
        const labels = Object.keys(groupedData).sort();
        
        // 收集所有数据库名称
        const allDatabases = new Set();
        Object.values(groupedData).forEach(dateData => {
            Object.keys(dateData).forEach(dbName => {
                allDatabases.add(dbName);
            });
        });
        
        const datasets = [];
        let colorIndex = 0;
        
        // 为每个数据库创建数据集
        allDatabases.forEach(dbName => {
            const dataPoints = labels.map(date => groupedData[date][dbName] || 0);
            
            // 根据数据类型确定样式
            let style = this.dataTypeStyles['数据库聚合']; // 默认样式
            for (const [type, typeStyle] of Object.entries(this.dataTypeStyles)) {
                if (dbName.includes(type)) {
                    style = typeStyle;
                    break;
                }
            }
            
            datasets.push({
                label: dbName,
                data: dataPoints,
                borderColor: style.color,
                backgroundColor: style.color + '20',
                fill: false,
                tension: 0.1,
                pointRadius: 4,
                pointHoverRadius: 6,
                borderWidth: 2,
                borderDash: style.borderDash,
                pointStyle: style.pointStyle
            });
            
            colorIndex++;
        });
        
        return {
            labels: labels,
            datasets: datasets
        };
    }
    
    /**
     * 按日期分组数据
     */
    groupDataByDate(data) {
        const grouped = {};
        
        data.forEach(item => {
            // 统一使用period_end作为X轴显示日期
            const date = item.period_end;
            if (!date) {
                console.warn('数据项缺少period_end:', item);
                return;
            }
            
            if (!grouped[date]) {
                grouped[date] = {};
            }
            
            // 按数据库分组，使用avg_size_mb作为显示值
            const dbName = item.database_name || '未知数据库';
            if (!grouped[date][dbName]) {
                grouped[date][dbName] = 0;
            }
            // 累加平均值，处理同一天多条记录的情况
            grouped[date][dbName] += item.avg_size_mb || 0;
        });
        
        return grouped;
    }
    
    /**
     * 更新图表统计信息
     */
    updateChartStats(data) {
        // 检查新格式数据
        if (data.dataPointCount !== undefined && data.timeRange !== undefined) {
            $('#dataPointCount').text(data.dataPointCount);
            $('#timeRange').text(data.timeRange);
            return;
        }
        
        // 旧格式数据处理
        if (!data || !data.length) {
            $('#dataPointCount').text('0');
            $('#timeRange').text('-');
            return;
        }
        
        // 统一使用period_end作为日期显示
        const dates = data.map(item => item.period_end).filter(Boolean).sort();
        const dataPointCount = data.length;
        
        let timeRange = '-';
        if (dates.length > 0) {
            const startDate = new Date(dates[0]).toLocaleDateString();
            const endDate = new Date(dates[dates.length - 1]).toLocaleDateString();
            timeRange = `${startDate} - ${endDate}`;
        }
        
        $('#dataPointCount').text(dataPointCount);
        $('#timeRange').text(timeRange);
    }
    
    
    /**
     * 获取周期类型名称
     */
    getPeriodTypeName(periodType) {
        const names = {
            'daily': '日',
            'weekly': '周',
            'monthly': '月',
            'quarterly': '季'
        };
        return names[periodType] || periodType;
    }
    
    /**
     * 刷新所有数据
     */
    async refreshAllData() {
        await this.loadChartData();
    }
    
    
    /**
     * 显示图表加载状态
     */
    showChartLoading(show) {
        const loading = $('#chartLoading');
        if (show) {
            loading.removeClass('d-none');
        } else {
            loading.addClass('d-none');
        }
    }
    
    /**
     * 显示图表消息
     */
    showChartMessage(message) {
        const messageDiv = $('#chartMessage');
        const messageText = $('#chartMessageText');
        messageText.text(message);
        messageDiv.removeClass('d-none');
    }
    
    /**
     * 隐藏图表消息
     */
    hideChartMessage() {
        const messageDiv = $('#chartMessage');
        messageDiv.addClass('d-none');
    }
    
    /**
     * 显示错误信息
     */
    showError(message) {
        console.error('图表错误:', message);
    }
    
    /**
     * 格式化大小（从MB）
     */
    static formatSizeFromMB(mb) {
        if (mb === 0) return '0 B';
        if (mb < 1024) return `${mb.toFixed(2)} MB`;
        if (mb < 1024 * 1024) return `${(mb / 1024).toFixed(2)} GB`;
        return `${(mb / (1024 * 1024)).toFixed(2)} TB`;
    }
    
    /**
     * 格式化日期时间
     */
    formatDateTime(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 等待Chart.js加载完成
    function initManager() {
        if (typeof Chart !== 'undefined' && typeof AggregationsChartManager !== 'undefined') {
            // 初始化聚合数据图表管理器
            window.aggregationsChartManager = new AggregationsChartManager();
        } else {
            // 如果依赖还没加载完成，等待100ms后重试
            setTimeout(initManager, 100);
        }
    }
    
    initManager();
});
