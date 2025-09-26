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
            dbType: '',
            periodType: 'daily',
            database: '',
            dateRange: 7
        };
        this.currentSortBy = 'period_start';
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
        $('#applyFilters').on('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.applyFilters();
        });
        
        // 清除筛选按钮
        $('#clearFilters').on('click', () => {
            this.clearFilters();
        });
        
        // 筛选器变化
        $('#period_type, #timeRange').on('change', () => {
            this.updateFilters();
            // 自动刷新图表
            this.loadChartData();
            this.loadTableData();
        });
        
        // 数据库类型变化时更新实例选项
        $('#db_type').on('change', async (e) => {
            const dbType = e.target.value;
            console.log('数据库类型变化:', dbType);
            await this.updateInstanceOptions(dbType);
            this.updateFilters();
            // 自动刷新图表
            this.loadChartData();
            this.loadTableData();
        });
        
        // 实例变化时更新数据库选项
        $('#instance').on('change', async (e) => {
            const instanceId = e.target.value;
            await this.updateDatabaseOptions(instanceId);
            this.updateFilters();
            // 自动刷新图表
            this.loadChartData();
            this.loadTableData();
        });
        
        // 数据库变化时自动刷新
        $('#database').on('change', () => {
            this.updateFilters();
            // 自动刷新图表
            this.loadChartData();
            this.loadTableData();
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
        
        // 图表模式切换
        $('input[name="chartMode"]').on('change', (e) => {
            this.currentChartMode = e.target.value;
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
    async loadInstances(dbType = null) {
        try {
            let url = '/instances/api/instances';
            if (dbType) {
                url += `?db_type=${dbType}`;
            }
            
            const response = await fetch(url);
            const data = await response.json();
            
            if (response.ok) {
                const select = $('#instance');
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
        
        if (this.currentFilters.dbType) {
            params.append('db_type', this.currentFilters.dbType);
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
        const select = $('#database');
        
        select.empty();
        select.append('<option value="">所有数据库</option>');
        
        databases.forEach(db => {
            select.append(`<option value="${db}">${db}</option>`);
        });
        
        select.val(this.currentFilters.database);
    }
    
    /**
     * 根据选择的实例更新数据库选项
     */
    async updateInstanceOptions(dbType) {
        const instanceSelect = $('#instance');
        const databaseSelect = $('#database');
        
        // 清空数据库选项
        databaseSelect.empty();
        databaseSelect.append('<option value="">请先选择实例</option>');
        databaseSelect.prop('disabled', true);
        
        if (!dbType) {
            // 如果没有选择数据库类型，显示所有实例
            instanceSelect.prop('disabled', false);
            await this.loadInstances();
            return;
        }
        
        try {
            instanceSelect.prop('disabled', false);
            const response = await fetch(`/instances/api/instances?db_type=${dbType}`);
            const data = await response.json();
            
            if (response.ok && data.success) {
                instanceSelect.empty();
                instanceSelect.append('<option value="">所有实例</option>');
                data.instances.forEach(instance => {
                    instanceSelect.append(`<option value="${instance.id}">${instance.name} (${instance.db_type})</option>`);
                });
            } else {
                instanceSelect.empty();
                instanceSelect.append('<option value="">加载失败</option>');
                console.error('实例加载失败:', data);
            }
        } catch (error) {
            console.error('加载实例列表时出错:', error);
            instanceSelect.empty();
            instanceSelect.append('<option value="">加载失败</option>');
        }
    }

    async updateDatabaseOptions(instanceId) {
        const databaseSelect = $('#database');
        
        if (!instanceId) {
            // 如果没有选择实例，清空数据库选项并禁用
            databaseSelect.empty();
            databaseSelect.append('<option value="">请先选择实例</option>');
            databaseSelect.prop('disabled', true);
            return;
        }
        
        try {
            // 启用数据库选择
            databaseSelect.prop('disabled', false);
            
            // 使用聚合数据获取该实例的数据库列表
            const params = this.buildFilterParams();
            params.set('instance_id', instanceId);
            
            const response = await fetch(`/database-sizes/aggregations?api=true&${params}`);
            const data = await response.json();
            
            if (response.ok && data.success) {
                databaseSelect.empty();
                databaseSelect.append('<option value="">所有数据库</option>');
                
                // 从聚合数据中提取数据库列表
                const databases = [...new Set(data.data.map(item => item.database_name))].sort();
                databases.forEach(db => {
                    databaseSelect.append(`<option value="${db}">${db}</option>`);
                });
            } else {
                databaseSelect.empty();
                databaseSelect.append('<option value="">加载失败</option>');
            }
        } catch (error) {
            console.error('加载数据库列表时出错:', error);
            databaseSelect.empty();
            databaseSelect.append('<option value="">加载失败</option>');
        }
    }
    
    /**
     * 初始化数据库筛选器
     */
    initializeDatabaseFilter() {
        const instanceSelect = $('#instance');
        const databaseSelect = $('#database');
        
        // 初始化实例筛选器
        instanceSelect.empty();
        instanceSelect.append('<option value="">请先选择数据库类型</option>');
        instanceSelect.prop('disabled', true);
        
        // 初始化数据库筛选器
        databaseSelect.empty();
        databaseSelect.append('<option value="">请先选择实例</option>');
        databaseSelect.prop('disabled', true);
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
                layout: {
                    padding: {
                        right: 120  // 减少右侧空白，图例圆圈更小
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    title: {
                        display: true,
                        text: this.currentChartMode === 'instance' ? '实例聚合趋势图 (TOP 20)' : '数据库聚合趋势图 (TOP 20)',
                        font: {
                            size: 16,
                            weight: 'bold'
                        }
                    },
                    legend: {
                        display: true,
                        position: 'right',
                        align: 'start',
                        maxHeight: 500,  // 增加图例最大高度以容纳23个名称
                        labels: {
                            usePointStyle: true,
                            padding: 4,  // 减少图例项间距
                            boxWidth: 8,  // 减小图例圆圈宽度
                            boxHeight: 8,  // 减小图例圆圈高度
                            font: {
                                size: 10  // 稍微减小字体大小
                            },
                            generateLabels: function(chart) {
                                const original = Chart.defaults.plugins.legend.labels.generateLabels;
                                const labels = original.call(this, chart);
                                
                                // 按标签名称排序
                                labels.sort((a, b) => a.text.localeCompare(b.text));
                                
                                // 限制显示的图例项数量为23个
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
                            text: '存储大小'
                        },
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        },
                        ticks: {
                            callback: function(value) {
                                return AggregationsManager.prototype.formatSizeFromMB(value);
                            }
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
            // 面积图使用 line 类型，但设置 fill 为 true
            chartConfig.type = 'line';
            chartConfig.data.datasets.forEach(dataset => {
                dataset.fill = true;
                // 确保背景色有透明度
                if (dataset.backgroundColor && !dataset.backgroundColor.includes('20')) {
                    dataset.backgroundColor = dataset.backgroundColor + '20';
                }
            });
            
            // 为面积图添加特殊的配置
            chartConfig.options.scales = chartConfig.options.scales || {};
            chartConfig.options.scales.x = chartConfig.options.scales.x || {};
            chartConfig.options.scales.y = chartConfig.options.scales.y || {};
            
            // 设置面积图的填充配置
            chartConfig.options.elements = chartConfig.options.elements || {};
            chartConfig.options.elements.line = chartConfig.options.elements.line || {};
            chartConfig.options.elements.line.tension = 0.1;
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
            
            if (this.currentChartMode === 'instance') {
                // 按实例分组，累加所有数据库的大小
                const instanceName = item.instance.name;
                if (!grouped[date][instanceName]) {
                    grouped[date][instanceName] = 0;
                }
                // 使用max_size_mb累加，表示实例的总容量
                grouped[date][instanceName] += item.max_size_mb || 0;
            } else {
                // 按数据库分组
                grouped[date][item.database_name] = item.avg_size_mb;
            }
        });
        
        return grouped;
    }
    
    /**
     * 准备图表数据集
     */
    prepareChartDatasets(groupedData, labels) {
        if (this.currentChartMode === 'instance') {
            return this.prepareInstanceDatasets(groupedData, labels);
        } else {
            return this.prepareDatabaseDatasets(groupedData, labels);
        }
    }
    
    /**
     * 准备数据库数据集
     */
    prepareDatabaseDatasets(groupedData, labels) {
        // 计算每个数据库的平均大小，选择TOP 20
        const databaseStats = {};
        
        this.currentData.forEach(item => {
            const dbName = item.database_name;
            if (!databaseStats[dbName]) {
                databaseStats[dbName] = {
                    totalSize: 0,
                    count: 0,
                    maxSize: 0
                };
            }
            databaseStats[dbName].totalSize += item.avg_size_mb || 0;
            databaseStats[dbName].count += 1;
            databaseStats[dbName].maxSize = Math.max(databaseStats[dbName].maxSize, item.max_size_mb || 0);
        });
        
        // 按最大大小排序，选择TOP 20
        const topDatabases = Object.entries(databaseStats)
            .sort(([,a], [,b]) => b.maxSize - a.maxSize)
            .slice(0, 20)
            .map(([dbName]) => dbName);
        
        const colors = [
            '#667eea', '#764ba2', '#f093fb', '#f5576c',
            '#4facfe', '#00f2fe', '#43e97b', '#38f9d7',
            '#fa709a', '#fee140', '#a8edea', '#fed6e3',
            '#ff9a9e', '#fecfef', '#fecfef', '#a8c0ff',
            '#ffecd2', '#fcb69f', '#ff8a80', '#ff80ab'
        ];
        
        return topDatabases.map((db, index) => ({
            label: db,
            data: labels.map(date => groupedData[date]?.[db] || 0),
            borderColor: colors[index % colors.length],
            backgroundColor: colors[index % colors.length] + '20',
            tension: 0.1
        }));
    }
    
    /**
     * 准备实例数据集
     */
    prepareInstanceDatasets(groupedData, labels) {
        // 计算每个实例的平均大小，选择TOP 20
        const instanceStats = {};
        
        this.currentData.forEach(item => {
            const instanceName = item.instance.name;
            if (!instanceStats[instanceName]) {
                instanceStats[instanceName] = {
                    totalSize: 0,
                    count: 0,
                    maxSize: 0
                };
            }
            // 使用max_size_mb累加，表示实例的总容量
            instanceStats[instanceName].totalSize += item.max_size_mb || 0;
            instanceStats[instanceName].count += 1;
            instanceStats[instanceName].maxSize = Math.max(instanceStats[instanceName].maxSize, item.max_size_mb || 0);
        });
        
        // 按总容量排序，选择TOP 20
        const topInstances = Object.entries(instanceStats)
            .sort(([,a], [,b]) => b.totalSize - a.totalSize)
            .slice(0, 20)
            .map(([instanceName]) => instanceName);
        
        const colors = [
            '#667eea', '#764ba2', '#f093fb', '#f5576c',
            '#4facfe', '#00f2fe', '#43e97b', '#38f9d7',
            '#fa709a', '#fee140', '#a8edea', '#fed6e3',
            '#ff9a9e', '#fecfef', '#fecfef', '#a8c0ff',
            '#ffecd2', '#fcb69f', '#ff8a80', '#ff80ab'
        ];
        
        return topInstances.map((instance, index) => ({
            label: instance,
            data: labels.map(date => groupedData[date]?.[instance] || 0),
            borderColor: colors[index % colors.length],
            backgroundColor: colors[index % colors.length] + '20',
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
                    return b.avg_size_mb - a.avg_size_mb;
                case 'max_size_mb':
                    return b.max_size_mb - a.max_size_mb;
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
                    <span class="database-name" title="${item.database_name}">${this.wrapDatabaseName(item.database_name)}</span>
                </td>
                <td>
                    <span class="period-type ${item.period_type}">${this.getPeriodTypeLabel(item.period_type)}</span>
                </td>
                <td>
                    <span class="size-display">${this.formatSizeFromMB(item.avg_size_mb)}</span>
                </td>
                <td>
                    <span class="size-display">${this.formatSizeFromMB(item.max_size_mb)}</span>
                </td>
                <td>
                    <span class="size-display">${this.formatSizeFromMB(item.min_size_mb)}</span>
                </td>
                <td>
                    <span class="badge bg-info">${item.data_count}</span>
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
        this.currentFilters.dbType = $('#db_type').val();
        this.currentFilters.instance = $('#instance').val();
        this.currentFilters.database = $('#database').val();
        this.currentFilters.periodType = $('#period_type').val();
        this.currentFilters.dateRange = parseInt($('#timeRange').val());
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
        // 重置所有筛选器值
        $('#db_type').val('');
        $('#instance').val('');
        $('#database').val('');
        $('#period_type').val('daily');
        $('#timeRange').val('7');
        $('#searchTable').val('');
        
        // 重置筛选器状态
        this.currentFilters = {
            dbType: '',
            instance: '',
            database: '',
            periodType: 'daily',
            dateRange: 7
        };
        
        // 重新加载所有实例（不按类型筛选）
        this.loadInstances();
        
        // 重置数据库选择器
        this.initializeDatabaseFilter();
        
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
     * 格式化文件大小（从字节开始）
     */
    formatSize(bytes) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
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
        
        // 计算应该使用哪个单位
        let i = 0;
        let size = mb;
        
        while (size >= k && i < sizes.length - 1) {
            size = size / k;
            i++;
        }
        
        return parseFloat(size.toFixed(2)) + ' ' + sizes[i];
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
    
    /**
     * 处理数据库名称换行
     */
    wrapDatabaseName(name) {
        if (name.length <= 20) {
            return name;
        }
        
        // 在适当的位置插入换行符
        const words = name.split('_');
        if (words.length > 1) {
            // 如果有下划线，在下划线处换行
            const midPoint = Math.ceil(words.length / 2);
            const firstPart = words.slice(0, midPoint).join('_');
            const secondPart = words.slice(midPoint).join('_');
            return `${firstPart}<br/>${secondPart}`;
        } else {
            // 如果没有下划线，在中间位置换行
            const midPoint = Math.ceil(name.length / 2);
            return `${name.substring(0, midPoint)}<br/>${name.substring(midPoint)}`;
        }
    }
}

// 页面加载完成后初始化
$(document).ready(function() {
    new AggregationsManager();
});
