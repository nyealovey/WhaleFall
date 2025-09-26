/**
 * 统计聚合页面脚本
 * 基于 jQuery 3.7.1 和 Chart.js 4.4.0
 */

class AggregationsManager {
    constructor() {
        this.chart = null;
        this.detailChart = null;
        this.currentData = [];
        this.currentSummary = null;
        this.currentFilters = {
            instance: '',
            periodType: 'monthly',
            database: '',
            dateRange: 6
        };
        this.currentSortBy = 'period_start';
        this.currentChartType = 'line';
        
        this.init();
    }
    
    /**
     * 初始化页面
     */
    init() {
        this.bindEvents();
        this.loadInstances();
        this.loadSummaryData();
        this.loadChartData();
        this.loadTableData();
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
        
        // 应用筛选按钮
        $('#applyFilters').on('click', () => {
            this.applyFilters();
        });
        
        // 清除筛选按钮
        $('#clearFilters').on('click', () => {
            this.clearFilters();
        });
        
        // 筛选器变化
        $('#instanceFilter, #periodTypeFilter, #databaseFilter, #dateRangeFilter').on('change', () => {
            this.updateFilters();
        });
        
        // 统计周期变化时调整时间范围选项
        $('#periodTypeFilter').on('change', (e) => {
            this.adjustDateRangeOptions(e.target.value);
        });
        
        // 图表类型切换
        $('input[name="chartType"]').on('change', (e) => {
            this.currentChartType = e.target.value;
            this.updateChart();
        });
        
        // 表格搜索
        $('#searchTable').on('input', (e) => {
            this.filterTable(e.target.value);
        });
        
        // 表格排序
        $('#sortTable').on('change', (e) => {
            this.currentSortBy = e.target.value;
            this.sortTable();
        });
        
        // 详情模态框
        $('#detailModal').on('show.bs.modal', (e) => {
            const button = $(e.relatedTarget);
            const aggregationId = button.data('aggregation-id');
            this.showAggregationDetail(aggregationId);
        });
    }
    
    /**
     * 加载实例列表
     */
    async loadInstances() {
        try {
            const response = await fetch('/instances/api/list');
            const data = await response.json();
            
            if (response.ok) {
                const select = $('#instanceFilter');
                select.empty();
                select.append('<option value="">所有实例</option>');
                
                data.instances.forEach(instance => {
                    select.append(`<option value="${instance.id}">${instance.name} (${instance.db_type})</option>`);
                });
            }
        } catch (error) {
            console.error('加载实例列表时出错:', error);
        }
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
        $('#averageSize').text(this.formatSize(data.average_size_mb || 0));
        $('#maxSize').text(this.formatSize(data.max_size_mb || 0));
    }
    
    /**
     * 加载图表数据
     */
    async loadChartData() {
        try {
            this.showChartLoading();
            
            const params = this.buildFilterParams();
            const response = await fetch(`/database-sizes/aggregations?api=true&${params}`);
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
     * 构建筛选参数
     */
    buildFilterParams() {
        const params = new URLSearchParams();
        
        if (this.currentFilters.instance) {
            params.append('instance_id', this.currentFilters.instance);
        }
        
        if (this.currentFilters.periodType) {
            params.append('period_type', this.currentFilters.periodType);
        }
        
        if (this.currentFilters.database) {
            params.append('database_name', this.currentFilters.database);
        }
        
        if (this.currentFilters.dateRange) {
            const endDate = new Date();
            const startDate = new Date();
            
            // 根据统计周期类型调整时间范围计算
            if (this.currentFilters.periodType === 'daily') {
                // 日统计：按天数计算
                if (this.currentFilters.dateRange <= 30) {
                    startDate.setDate(startDate.getDate() - this.currentFilters.dateRange);
                } else {
                    // 超过30天按月份计算
                    startDate.setMonth(startDate.getMonth() - Math.floor(this.currentFilters.dateRange / 30));
                }
            } else {
                // 周、月、季统计：按月份计算
                startDate.setMonth(startDate.getMonth() - this.currentFilters.dateRange);
            }
            
            params.append('start_date', startDate.toISOString().split('T')[0]);
            params.append('end_date', endDate.toISOString().split('T')[0]);
        }
        
        return params.toString();
    }
    
    /**
     * 更新数据库筛选选项
     */
    updateDatabaseFilter(data) {
        const databases = [...new Set(data.map(item => item.database_name))].sort();
        const select = $('#databaseFilter');
        
        select.empty();
        select.append('<option value="">所有数据库</option>');
        
        databases.forEach(db => {
            select.append(`<option value="${db}">${db}</option>`);
        });
        
        select.val(this.currentFilters.database);
    }
    
    /**
     * 渲染图表
     */
    renderChart(data) {
        const ctx = document.getElementById('aggregationChart').getContext('2d');
        
        // 销毁现有图表
        if (this.chart) {
            this.chart.destroy();
        }
        
        // 按日期分组数据
        const groupedData = this.groupDataByDate(data);
        
        // 准备图表数据
        const labels = Object.keys(groupedData).sort();
        const datasets = this.prepareChartDatasets(groupedData, labels);
        
        const chartConfig = {
            type: this.currentChartType,
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    title: {
                        display: true,
                        text: '数据库大小统计聚合趋势',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                const label = context.dataset.label || '';
                                const value = context.parsed.y;
                                return `${label}: ${AggregationsManager.prototype.formatSize(value)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: '统计周期'
                        },
                        grid: {
                            display: false
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: '存储大小 (MB)'
                        },
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    }
                },
                elements: {
                    point: {
                        radius: 4,
                        hoverRadius: 6
                    },
                    line: {
                        tension: 0.1
                    }
                }
            }
        };
        
        // 根据图表类型调整配置
        if (this.currentChartType === 'area') {
            chartConfig.data.datasets.forEach(dataset => {
                dataset.fill = true;
            });
        }
        
        this.chart = new Chart(ctx, chartConfig);
    }
    
    /**
     * 按日期分组数据
     */
    groupDataByDate(data) {
        const grouped = {};
        
        data.forEach(item => {
            const date = item.period_start;
            if (!grouped[date]) {
                grouped[date] = {};
            }
            grouped[date][item.database_name] = item.statistics.avg_size_mb;
        });
        
        return grouped;
    }
    
    /**
     * 准备图表数据集
     */
    prepareChartDatasets(groupedData, labels) {
        const databases = [...new Set(this.currentData.map(item => item.database_name))].sort();
        const colors = [
            '#667eea', '#764ba2', '#f093fb', '#f5576c',
            '#4facfe', '#00f2fe', '#43e97b', '#38f9d7',
            '#fa709a', '#fee140', '#a8edea', '#fed6e3'
        ];
        
        return databases.map((db, index) => ({
            label: db,
            data: labels.map(date => groupedData[date]?.[db] || 0),
            borderColor: colors[index % colors.length],
            backgroundColor: colors[index % colors.length] + '20',
            fill: this.currentChartType === 'area',
            tension: 0.1
        }));
    }
    
    /**
     * 加载表格数据
     */
    async loadTableData() {
        try {
            this.showTableLoading();
            
            const params = this.buildFilterParams();
            const response = await fetch(`/database-sizes/aggregations?api=true&${params}`);
            const data = await response.json();
            
            if (response.ok) {
                this.renderTable(data.data);
            } else {
                this.showError('加载表格数据失败: ' + data.error);
            }
        } catch (error) {
            console.error('加载表格数据时出错:', error);
            this.showError('加载表格数据时出错: ' + error.message);
        } finally {
            this.hideTableLoading();
        }
    }
    
    /**
     * 渲染表格
     */
    renderTable(data) {
        const tbody = $('#aggregationTableBody');
        tbody.empty();
        
        if (data.length === 0) {
            tbody.append(`
                <tr>
                    <td colspan="9" class="text-center">
                        <div class="empty-state">
                            <i class="fas fa-chart-bar"></i>
                            <h5>暂无数据</h5>
                            <p>没有找到符合条件的聚合数据</p>
                        </div>
                    </td>
                </tr>
            `);
            return;
        }
        
        // 排序数据
        const sortedData = this.sortData(data, this.currentSortBy);
        
        sortedData.forEach(item => {
            const row = this.createTableRow(item);
            tbody.append(row);
        });
    }
    
    /**
     * 排序数据
     */
    sortData(data, sortBy) {
        return data.sort((a, b) => {
            switch (sortBy) {
                case 'period_start':
                    return new Date(b.period_start) - new Date(a.period_start);
                case 'instance_name':
                    return a.instance.name.localeCompare(b.instance.name);
                case 'database_name':
                    return a.database_name.localeCompare(b.database_name);
                case 'avg_size_mb':
                    return b.statistics.avg_size_mb - a.statistics.avg_size_mb;
                case 'max_size_mb':
                    return b.statistics.max_size_mb - a.statistics.max_size_mb;
                default:
                    return 0;
            }
        });
    }
    
    /**
     * 创建表格行
     */
    createTableRow(item) {
        const calculatedAt = new Date(item.calculated_at).toLocaleString('zh-CN');
        const periodRange = `${item.period_start} 至 ${item.period_end}`;
        
        return `
            <tr>
                <td>
                    <span class="instance-name">${item.instance.name}</span>
                </td>
                <td>
                    <span class="database-name">${item.database_name}</span>
                </td>
                <td>
                    <span class="period-type ${item.period_type}">${this.getPeriodTypeLabel(item.period_type)}</span>
                </td>
                <td>
                    <span class="size-display">${this.formatSize(item.statistics.avg_size_mb)}</span>
                </td>
                <td>
                    <span class="size-display">${this.formatSize(item.statistics.max_size_mb)}</span>
                </td>
                <td>
                    <span class="size-display">${this.formatSize(item.statistics.min_size_mb)}</span>
                </td>
                <td>
                    <span class="badge bg-info">${item.statistics.data_count}</span>
                </td>
                <td>
                    <small class="text-muted">${calculatedAt}</small>
                </td>
                <td>
                    <div class="action-buttons">
                        <button class="btn btn-outline-info btn-sm" 
                                data-bs-toggle="modal" 
                                data-bs-target="#detailModal"
                                data-aggregation-id="${item.id}">
                            <i class="fas fa-info-circle"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }
    
    /**
     * 获取周期类型标签
     */
    getPeriodTypeLabel(periodType) {
        const labels = {
            'weekly': '周',
            'monthly': '月',
            'quarterly': '季'
        };
        return labels[periodType] || periodType;
    }
    
    /**
     * 筛选表格
     */
    filterTable(searchTerm) {
        const rows = $('#aggregationTableBody tr');
        const term = searchTerm.toLowerCase();
        
        rows.each(function() {
            const row = $(this);
            const instanceName = row.find('.instance-name').text().toLowerCase();
            const databaseName = row.find('.database-name').text().toLowerCase();
            
            if (instanceName.includes(term) || databaseName.includes(term)) {
                row.show();
            } else {
                row.hide();
            }
        });
    }
    
    /**
     * 排序表格
     */
    sortTable() {
        this.loadTableData();
    }
    
    /**
     * 显示聚合详情
     */
    async showAggregationDetail(aggregationId) {
        try {
            // 从当前数据中查找聚合记录
            const aggregation = this.currentData.find(item => item.id === aggregationId);
            
            if (!aggregation) {
                this.showError('未找到聚合记录');
                return;
            }
            
            // 更新模态框内容
            $('#modalInstanceName').text(aggregation.instance.name);
            $('#modalDatabaseName').text(aggregation.database_name);
            $('#modalPeriodType').text(this.getPeriodTypeLabel(aggregation.period_type));
            $('#modalPeriodRange').text(`${aggregation.period_start} 至 ${aggregation.period_end}`);
            $('#modalDataCount').text(aggregation.statistics.data_count);
            $('#modalAvgSize').text(this.formatSize(aggregation.statistics.avg_size_mb));
            $('#modalMaxSize').text(this.formatSize(aggregation.statistics.max_size_mb));
            $('#modalMinSize').text(this.formatSize(aggregation.statistics.min_size_mb));
            $('#modalAvgDataSize').text(aggregation.statistics.avg_data_size_mb ? this.formatSize(aggregation.statistics.avg_data_size_mb) : '-');
            $('#modalAvgLogSize').text(aggregation.statistics.avg_log_size_mb ? this.formatSize(aggregation.statistics.avg_log_size_mb) : '-');
            
            // 渲染详情图表
            this.renderDetailChart(aggregation);
            
        } catch (error) {
            console.error('显示聚合详情时出错:', error);
            this.showError('显示聚合详情时出错: ' + error.message);
        }
    }
    
    /**
     * 渲染详情图表
     */
    renderDetailChart(aggregation) {
        const ctx = document.getElementById('detailChart').getContext('2d');
        
        // 销毁现有图表
        if (this.detailChart) {
            this.detailChart.destroy();
        }
        
        // 这里可以添加更详细的图表数据
        // 目前显示简单的统计信息
        const labels = ['平均大小', '最大大小', '最小大小'];
        const data = [
            aggregation.statistics.avg_size_mb,
            aggregation.statistics.max_size_mb,
            aggregation.statistics.min_size_mb
        ];
        
        this.detailChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: '大小 (MB)',
                    data: data,
                    backgroundColor: [
                        '#667eea',
                        '#f093fb',
                        '#38f9d7'
                    ],
                    borderColor: [
                        '#667eea',
                        '#f093fb',
                        '#38f9d7'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: '大小 (MB)'
                        }
                    }
                }
            }
        });
    }
    
    /**
     * 根据统计周期调整时间范围选项
     */
    adjustDateRangeOptions(periodType) {
        const dateRangeSelect = $('#dateRangeFilter');
        const currentValue = dateRangeSelect.val();
        
        // 清空现有选项
        dateRangeSelect.empty();
        
        if (periodType === 'daily') {
            // 日统计：提供天数和周数选项
            dateRangeSelect.append('<option value="7">最近7天</option>');
            dateRangeSelect.append('<option value="14">最近14天</option>');
            dateRangeSelect.append('<option value="30" selected>最近30天</option>');
            dateRangeSelect.append('<option value="60">最近60天</option>');
            dateRangeSelect.append('<option value="90">最近90天</option>');
        } else if (periodType === 'weekly') {
            // 周统计：提供周数和月数选项
            dateRangeSelect.append('<option value="4">最近4周</option>');
            dateRangeSelect.append('<option value="8">最近8周</option>');
            dateRangeSelect.append('<option value="12" selected>最近12周</option>');
            dateRangeSelect.append('<option value="24">最近24周</option>');
        } else if (periodType === 'monthly') {
            // 月统计：提供月数和年数选项
            dateRangeSelect.append('<option value="3">最近3个月</option>');
            dateRangeSelect.append('<option value="6" selected>最近6个月</option>');
            dateRangeSelect.append('<option value="12">最近1年</option>');
            dateRangeSelect.append('<option value="24">最近2年</option>');
        } else if (periodType === 'quarterly') {
            // 季统计：提供季度和年数选项
            dateRangeSelect.append('<option value="4">最近4个季度</option>');
            dateRangeSelect.append('<option value="8" selected>最近8个季度</option>');
            dateRangeSelect.append('<option value="12">最近12个季度</option>');
        }
        
        // 如果当前值在新选项中存在，保持选中；否则选择默认值
        if (dateRangeSelect.find(`option[value="${currentValue}"]`).length === 0) {
            dateRangeSelect.find('option[selected]').prop('selected', true);
        }
    }
    
    /**
     * 更新筛选器
     */
    updateFilters() {
        this.currentFilters.instance = $('#instanceFilter').val();
        this.currentFilters.periodType = $('#periodTypeFilter').val();
        this.currentFilters.database = $('#databaseFilter').val();
        this.currentFilters.dateRange = parseInt($('#dateRangeFilter').val());
    }
    
    /**
     * 应用筛选
     */
    applyFilters() {
        this.updateFilters();
        this.loadChartData();
        this.loadTableData();
    }
    
    /**
     * 清除筛选
     */
    clearFilters() {
        $('#instanceFilter').val('');
        $('#periodTypeFilter').val('monthly');
        $('#databaseFilter').val('');
        $('#dateRangeFilter').val('6');
        $('#searchTable').val('');
        
        this.currentFilters = {
            instance: '',
            periodType: 'monthly',
            database: '',
            dateRange: 6
        };
        
        this.applyFilters();
    }
    
    /**
     * 更新图表
     */
    updateChart() {
        this.loadChartData();
    }
    
    /**
     * 重新计算聚合
     */
    async calculateAggregations() {
        try {
            // 显示计算进度模态框
            const modal = new bootstrap.Modal(document.getElementById('calculationModal'));
            modal.show();
            
            // 模拟进度更新
            let progress = 0;
            const progressBar = document.querySelector('.progress-bar');
            const interval = setInterval(() => {
                progress += Math.random() * 20;
                if (progress > 100) progress = 100;
                progressBar.style.width = progress + '%';
                
                if (progress >= 100) {
                    clearInterval(interval);
                    setTimeout(() => {
                        modal.hide();
                        this.refreshAllData();
                    }, 1000);
                }
            }, 200);
            
            // 调用API重新计算
            const csrfToken = this.getCSRFToken();
            const response = await fetch('/database-sizes/aggregate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.showSuccess('聚合数据重新计算完成');
            } else {
                this.showError('重新计算失败: ' + data.error);
            }
            
        } catch (error) {
            console.error('重新计算聚合时出错:', error);
            this.showError('重新计算聚合时出错: ' + error.message);
        }
    }
    
    /**
     * 刷新所有数据
     */
    refreshAllData() {
        this.loadSummaryData();
        this.loadChartData();
        this.loadTableData();
    }
    
    /**
     * 格式化文件大小
     */
    formatSize(bytes) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    /**
     * 显示加载状态
     */
    showLoading(selector) {
        $(selector).html('<i class="fas fa-spinner fa-spin"></i>');
    }
    
    /**
     * 显示图表加载状态
     */
    showChartLoading() {
        $('#chartLoading').removeClass('d-none');
    }
    
    /**
     * 隐藏图表加载状态
     */
    hideChartLoading() {
        $('#chartLoading').addClass('d-none');
    }
    
    /**
     * 显示表格加载状态
     */
    showTableLoading() {
        $('#aggregationTableBody').html(`
            <tr>
                <td colspan="9" class="text-center">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">加载中...</span>
                    </div>
                </td>
            </tr>
        `);
    }
    
    /**
     * 隐藏表格加载状态
     */
    hideTableLoading() {
        // 加载状态会在 renderTable 中被替换
    }
    
    /**
     * 显示错误信息
     */
    showError(message) {
        console.error(message);
        this.showToast(message, 'error');
    }
    
    /**
     * 显示成功信息
     */
    showSuccess(message) {
        console.log(message);
        this.showToast(message, 'success');
    }
    
    /**
     * 显示提示信息
     */
    showToast(message, type = 'info') {
        const bgClass = type === 'error' ? 'bg-danger' : type === 'success' ? 'bg-success' : 'bg-info';
        const icon = type === 'error' ? 'fa-exclamation-triangle' : type === 'success' ? 'fa-check-circle' : 'fa-info-circle';
        
        const toast = $(`
            <div class="toast align-items-center text-white ${bgClass} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="fas ${icon} me-2"></i>
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `);
        
        $('body').append(toast);
        
        const bsToast = new bootstrap.Toast(toast[0]);
        bsToast.show();
        
        // 自动移除 toast
        setTimeout(() => {
            toast.remove();
        }, 5000);
    }
    
    /**
     * 获取CSRF Token
     */
    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }
}

// 页面加载完成后初始化
$(document).ready(function() {
    new AggregationsManager();
});
