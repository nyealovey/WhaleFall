/**
 * 实例存储监控页面脚本
 * 基于 jQuery 3.7.1 和 Chart.js 4.4.0
 */

class StorageMonitor {
    constructor() {
        this.instanceId = window.instanceId;
        this.chart = null;
        this.modalChart = null;
        this.currentData = [];
        this.currentSummary = null;
        this.currentDateRange = 30;
        this.currentDatabaseFilter = '';
        this.currentSortBy = 'name';
        
        this.init();
    }
    
    /**
     * 初始化页面
     */
    init() {
        this.bindEvents();
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
        
        // 图表更新按钮
        $('#updateChart').on('click', () => {
            this.updateChart();
        });
        
        // 日期范围选择
        $('#dateRange').on('change', (e) => {
            this.currentDateRange = parseInt(e.target.value);
            this.updateChart();
        });
        
        // 数据库筛选
        $('#databaseFilter').on('change', (e) => {
            this.currentDatabaseFilter = e.target.value;
            this.updateChart();
        });
        
        // 数据库搜索
        $('#searchDatabase').on('input', (e) => {
            this.filterTable(e.target.value);
        });
        
        // 排序选择
        $('#sortBy').on('change', (e) => {
            this.currentSortBy = e.target.value;
            this.sortTable();
        });
        
        // 数据库详情模态框
        $('#databaseDetailModal').on('show.bs.modal', (e) => {
            const button = $(e.relatedTarget);
            const databaseName = button.data('database');
            this.showDatabaseDetail(databaseName);
        });
    }
    
    /**
     * 加载汇总数据
     */
    async loadSummaryData() {
        try {
            this.showLoading('#totalDatabases, #totalSize, #averageSize, #growthRate');
            
            const response = await fetch(`/instances/${this.instanceId}/database-sizes/summary`);
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
        $('#totalDatabases').text(data.total_databases || 0);
        $('#totalSize').text(this.formatSize(data.total_size_mb || 0));
        $('#averageSize').text(this.formatSize(data.average_size_mb || 0));
        
        const growthRate = data.growth_rate || 0;
        const growthElement = $('#growthRate');
        growthElement.text(growthRate >= 0 ? `+${growthRate.toFixed(1)}%` : `${growthRate.toFixed(1)}%`);
        
        // 根据增长率设置颜色
        if (growthRate > 0) {
            growthElement.removeClass('text-danger').addClass('text-success');
        } else if (growthRate < 0) {
            growthElement.removeClass('text-success').addClass('text-danger');
        } else {
            growthElement.removeClass('text-success text-danger');
        }
    }
    
    /**
     * 加载图表数据
     */
    async loadChartData() {
        try {
            this.showChartLoading();
            
            const endDate = new Date();
            const startDate = new Date();
            startDate.setDate(startDate.getDate() - this.currentDateRange);
            
            const params = new URLSearchParams({
                start_date: startDate.toISOString().split('T')[0],
                end_date: endDate.toISOString().split('T')[0],
                limit: 1000
            });
            
            if (this.currentDatabaseFilter) {
                params.append('database_name', this.currentDatabaseFilter);
            }
            
            const response = await fetch(`/instances/${this.instanceId}/database-sizes?${params}`);
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
        
        select.val(this.currentDatabaseFilter);
    }
    
    /**
     * 渲染图表
     */
    renderChart(data) {
        const ctx = document.getElementById('storageTrendChart').getContext('2d');
        
        // 销毁现有图表
        if (this.chart) {
            this.chart.destroy();
        }
        
        // 按日期分组数据
        const groupedData = this.groupDataByDate(data);
        
        // 准备图表数据
        const labels = Object.keys(groupedData).sort();
        const datasets = this.prepareChartDatasets(groupedData, labels);
        
        this.chart = new Chart(ctx, {
            type: 'line',
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
                        text: '数据库存储大小趋势',
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
                                return `${label}: ${StorageMonitor.prototype.formatSize(value)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: '日期'
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
        });
    }
    
    /**
     * 按日期分组数据
     */
    groupDataByDate(data) {
        const grouped = {};
        
        data.forEach(item => {
            const date = item.collected_date;
            if (!grouped[date]) {
                grouped[date] = {};
            }
            grouped[date][item.database_name] = item.size_mb;
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
            fill: false,
            tension: 0.1
        }));
    }
    
    /**
     * 加载表格数据
     */
    async loadTableData() {
        try {
            this.showTableLoading();
            
            const endDate = new Date();
            const startDate = new Date();
            startDate.setDate(startDate.getDate() - 30);
            
            const params = new URLSearchParams({
                start_date: startDate.toISOString().split('T')[0],
                end_date: endDate.toISOString().split('T')[0],
                limit: 1000
            });
            
            const response = await fetch(`/instances/${this.instanceId}/database-sizes?${params}`);
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
        const tbody = $('#databaseTableBody');
        tbody.empty();
        
        if (data.length === 0) {
            tbody.append(`
                <tr>
                    <td colspan="6" class="text-center">
                        <div class="empty-state">
                            <i class="fas fa-database"></i>
                            <h5>暂无数据</h5>
                            <p>该实例还没有数据库大小数据</p>
                        </div>
                    </td>
                </tr>
            `);
            return;
        }
        
        // 按数据库分组，获取最新数据
        const latestData = this.getLatestDataByDatabase(data);
        
        // 排序
        const sortedData = this.sortData(latestData, this.currentSortBy);
        
        sortedData.forEach(item => {
            const row = this.createTableRow(item);
            tbody.append(row);
        });
    }
    
    /**
     * 获取每个数据库的最新数据
     */
    getLatestDataByDatabase(data) {
        const grouped = {};
        
        data.forEach(item => {
            const dbName = item.database_name;
            if (!grouped[dbName] || new Date(item.collected_at) > new Date(grouped[dbName].collected_at)) {
                grouped[dbName] = item;
            }
        });
        
        return Object.values(grouped);
    }
    
    /**
     * 排序数据
     */
    sortData(data, sortBy) {
        return data.sort((a, b) => {
            switch (sortBy) {
                case 'name':
                    return a.database_name.localeCompare(b.database_name);
                case 'size':
                    return b.size_mb - a.size_mb;
                case 'date':
                    return new Date(b.collected_at) - new Date(a.collected_at);
                default:
                    return 0;
            }
        });
    }
    
    /**
     * 创建表格行
     */
    createTableRow(item) {
        const lastUpdate = new Date(item.collected_at).toLocaleString('zh-CN');
        
        return `
            <tr>
                <td>
                    <span class="database-name">${item.database_name}</span>
                </td>
                <td>
                    <span class="size-display">${this.formatSize(item.size_mb)}</span>
                </td>
                <td>
                    <span class="size-display">${item.data_size_mb ? this.formatSize(item.data_size_mb) : '-'}</span>
                </td>
                <td>
                    <span class="size-display">${item.log_size_mb ? this.formatSize(item.log_size_mb) : '-'}</span>
                </td>
                <td>
                    <small class="text-muted">${lastUpdate}</small>
                </td>
                <td>
                    <div class="action-buttons">
                        <button class="btn btn-outline-info btn-sm" 
                                data-bs-toggle="modal" 
                                data-bs-target="#databaseDetailModal"
                                data-database="${item.database_name}">
                            <i class="fas fa-info-circle"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }
    
    /**
     * 筛选表格
     */
    filterTable(searchTerm) {
        const rows = $('#databaseTableBody tr');
        const term = searchTerm.toLowerCase();
        
        rows.each(function() {
            const row = $(this);
            const databaseName = row.find('.database-name').text().toLowerCase();
            
            if (databaseName.includes(term)) {
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
     * 显示数据库详情
     */
    async showDatabaseDetail(databaseName) {
        try {
            // 更新模态框标题
            $('#modalDatabaseName').text(databaseName);
            
            // 获取该数据库的详细信息
            const response = await fetch(`/instances/${this.instanceId}/database-sizes?database_name=${encodeURIComponent(databaseName)}&limit=30`);
            const data = await response.json();
            
            if (response.ok && data.data.length > 0) {
                const latest = data.data[0];
                
                // 更新基本信息
                $('#modalTotalSize').text(this.formatSize(latest.size_mb));
                $('#modalDataSize').text(latest.data_size_mb ? this.formatSize(latest.data_size_mb) : '-');
                $('#modalLogSize').text(latest.log_size_mb ? this.formatSize(latest.log_size_mb) : '-');
                
                // 渲染详情图表
                this.renderModalChart(data.data);
            } else {
                this.showError('获取数据库详情失败');
            }
        } catch (error) {
            console.error('显示数据库详情时出错:', error);
            this.showError('显示数据库详情时出错: ' + error.message);
        }
    }
    
    /**
     * 渲染模态框图表
     */
    renderModalChart(data) {
        const ctx = document.getElementById('modalChart').getContext('2d');
        
        // 销毁现有图表
        if (this.modalChart) {
            this.modalChart.destroy();
        }
        
        // 准备数据
        const labels = data.map(item => item.collected_date).reverse();
        const sizes = data.map(item => item.size_mb).reverse();
        
        this.modalChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: '存储大小 (MB)',
                    data: sizes,
                    borderColor: '#667eea',
                    backgroundColor: '#667eea20',
                    fill: true,
                    tension: 0.1
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
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: '日期'
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: '大小 (MB)'
                        },
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    /**
     * 更新图表
     */
    updateChart() {
        this.loadChartData();
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
        $('#databaseTableBody').html(`
            <tr>
                <td colspan="6" class="text-center">
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
        
        // 使用 Bootstrap 的 toast 显示错误
        const toast = $(`
            <div class="toast align-items-center text-white bg-danger border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="fas fa-exclamation-triangle me-2"></i>
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
}

// 页面加载完成后初始化
$(document).ready(function() {
    // 检查是否在存储监控页面
    if (window.instanceId) {
        new StorageMonitor();
    }
});
