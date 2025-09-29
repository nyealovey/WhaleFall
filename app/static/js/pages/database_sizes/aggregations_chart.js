/**
 * 聚合数据图表管理器
 * 基于 Chart.js 4.4.0 和 jQuery 3.7.1
 */

class AggregationsChartManager {
    constructor() {
        this.chart = null;
        this.currentData = [];
        this.currentChartType = 'line';
        this.currentPeriodType = 'daily';
        this.chartColors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
            '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF',
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
            '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F'
        ];
        
        this.init();
    }
    
    init() {
        console.log('初始化聚合数据图表管理器');
        this.bindEvents();
        this.loadSummaryData();
        this.loadChartData();
        this.loadTableData();
    }
    
    bindEvents() {
        // 图表类型切换
        $('input[name="chartType"]').on('change', (e) => {
            this.currentChartType = e.target.value;
            this.renderChart(this.currentData);
        });
        
        // 周期类型切换
        $('input[name="periodType"]').on('change', (e) => {
            this.currentPeriodType = e.target.value;
            this.updateChartInfo();
            this.loadChartData();
            this.loadTableData();
        });
        
        // 刷新按钮
        $('#refreshAggregations').on('click', () => {
            this.refreshAllData();
        });
        
        // 排序选择
        $('#sortBy').on('change', () => {
            this.loadTableData();
        });
        
        // 导出按钮
        $('#exportData').on('click', () => {
            this.exportData();
        });
    }
    
    /**
     * 加载统计概览数据
     */
    async loadSummaryData() {
        try {
            const response = await fetch('/api/aggregations/summary');
            if (response.ok) {
                const data = await response.json();
                this.updateSummaryCards(data);
            } else {
                console.error('加载统计概览失败:', response.statusText);
            }
        } catch (error) {
            console.error('加载统计概览异常:', error);
        }
    }
    
    /**
     * 更新统计卡片
     */
    updateSummaryCards(data) {
        $('#dailyCount').text(data.daily || 0);
        $('#weeklyCount').text(data.weekly || 0);
        $('#monthlyCount').text(data.monthly || 0);
        $('#quarterlyCount').text(data.quarterly || 0);
    }
    
    /**
     * 更新图表信息
     */
    updateChartInfo() {
        const periodNames = {
            'daily': '日聚合数据趋势',
            'weekly': '周聚合数据趋势', 
            'monthly': '月聚合数据趋势',
            'quarterly': '季度聚合数据趋势'
        };
        
        const periodSubtitles = {
            'daily': '最近7天的数据统计',
            'weekly': '最近7周的数据统计',
            'monthly': '最近7个月的数据统计', 
            'quarterly': '最近7个季度的数据统计'
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
            
            const response = await fetch(`/api/aggregations/chart?${params}`);
            if (response.ok) {
                const data = await response.json();
                this.currentData = data;
                this.renderChart(data);
                this.updateChartStats(data);
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
                                const value = AggregationsChartManager.formatSizeFromMB(context.parsed.y);
                                return `${label}: ${value}`;
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
                            text: '大小 (MB)',
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
        if (!data || !data.length) {
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
            
            datasets.push({
                label: dbName,
                data: dataPoints,
                borderColor: this.chartColors[colorIndex % this.chartColors.length],
                backgroundColor: this.chartColors[colorIndex % this.chartColors.length] + '20',
                fill: false,
                tension: 0.1,
                pointRadius: 4,
                pointHoverRadius: 6,
                borderWidth: 2
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
            const date = item.period_start;
            if (!date) {
                console.warn('数据项缺少period_start:', item);
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
        if (!data || !data.length) {
            $('#dataPointCount').text('0');
            $('#timeRange').text('-');
            return;
        }
        
        const dates = data.map(item => item.period_start).filter(Boolean).sort();
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
     * 加载表格数据
     */
    async loadTableData() {
        try {
            const params = new URLSearchParams({
                period_type: this.currentPeriodType,
                days: 7,
                sort_by: $('#sortBy').val() || 'period_start'
            });
            
            const response = await fetch(`/api/aggregations/table?${params}`);
            if (response.ok) {
                const data = await response.json();
                this.renderTable(data);
            } else {
                console.error('加载表格数据失败:', response.statusText);
            }
        } catch (error) {
            console.error('加载表格数据异常:', error);
        }
    }
    
    /**
     * 渲染表格
     */
    renderTable(data) {
        const tbody = $('#aggregationsTableBody');
        tbody.empty();
        
        if (!data || !data.length) {
            tbody.append(`
                <tr>
                    <td colspan="10" class="text-center text-muted">
                        <i class="fas fa-inbox me-2"></i>
                        暂无数据
                    </td>
                </tr>
            `);
            return;
        }
        
        data.forEach(item => {
            const row = `
                <tr>
                    <td>
                        <span class="badge bg-secondary">${item.table_type || 'undefined'}</span>
                    </td>
                    <td>
                        <span class="badge bg-primary">${this.getPeriodTypeName(item.period_type)}</span>
                    </td>
                    <td>${item.instance_name || '-'}</td>
                    <td>${item.database_name || '-'}</td>
                    <td>${item.period_range || '-'}</td>
                    <td>${this.formatSizeFromMB(item.avg_size_mb || 0)}</td>
                    <td>${this.formatSizeFromMB(item.max_size_mb || 0)}</td>
                    <td>${this.formatSizeFromMB(item.min_size_mb || 0)}</td>
                    <td>
                        <span class="badge bg-info">${item.data_count || 0}</span>
                    </td>
                    <td>${this.formatDateTime(item.calculated_at)}</td>
                </tr>
            `;
            tbody.append(row);
        });
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
        await Promise.all([
            this.loadSummaryData(),
            this.loadChartData(),
            this.loadTableData()
        ]);
    }
    
    /**
     * 导出数据
     */
    exportData() {
        if (!this.currentData || !this.currentData.length) {
            alert('暂无数据可导出');
            return;
        }
        
        // 创建CSV内容
        const headers = ['表类型', '周期类型', '实例名称', '数据库名称', '统计周期', '平均大小', '最大大小', '最小大小', '数据点数', '计算时间'];
        const csvContent = [
            headers.join(','),
            ...this.currentData.map(item => [
                item.table_type || '',
                this.getPeriodTypeName(item.period_type),
                item.instance_name || '',
                item.database_name || '',
                item.period_range || '',
                item.avg_size_mb || 0,
                item.max_size_mb || 0,
                item.min_size_mb || 0,
                item.data_count || 0,
                this.formatDateTime(item.calculated_at)
            ].join(','))
        ].join('\n');
        
        // 下载文件
        const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `aggregations_${this.currentPeriodType}_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
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
     * 显示错误信息
     */
    showError(message) {
        const tbody = $('#aggregationsTableBody');
        tbody.empty();
        tbody.append(`
            <tr>
                <td colspan="10" class="text-center text-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${message}
                </td>
            </tr>
        `);
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
