/**
 * 数据库统计页面脚本
 * 基于 jQuery 3.7.1 和 Chart.js 4.4.0
 */

class DatabaseAggregationsManager {
    constructor() {
        this.chart = null;
        this.currentData = [];
        this.currentChartType = 'line';
        this.currentFilters = {
            instance_id: null,
            db_type: null,
            database_name: null,
            period_type: 'daily',
            start_date: null,
            end_date: null
        };
        
        this.init();
    }
    
    init() {
        console.log('初始化数据库统计管理器');
        this.bindEvents();
        this.initializeDatabaseFilter();
        this.loadSummaryData();
        this.loadChartData();
        this.loadTableData();
    }
    
    bindEvents() {
        // 刷新数据按钮
        $('#refreshData').on('click', () => {
            this.refreshAllData();
        });
        
        // 聚合计算按钮
        $('#calculateAggregations').on('click', () => {
            this.calculateAggregations();
        });
        
        // 图表类型切换
        $('input[name="chartType"]').on('change', (e) => {
            this.currentChartType = e.target.value;
            this.renderChart(this.currentData);
        });
        
        // 筛选按钮
        $('#searchButton').on('click', () => {
            this.applyFilters();
        });
        
        // 重置按钮
        $('#resetButton').on('click', () => {
            this.resetFilters();
        });
        
        // 数据库类型变化时更新实例选项
        $('#db_type').on('change', async (e) => {
            const dbType = e.target.value;
            console.log('数据库类型变化:', dbType);
            await this.updateInstanceOptions(dbType);
            this.updateFilters();
            this.loadChartData();
        });
        
        // 实例变化时更新数据库选项
        $('#instance').on('change', async (e) => {
            const instanceId = e.target.value;
            await this.updateDatabaseOptions(instanceId);
            this.updateFilters();
            this.loadChartData();
        });
        
        // 数据库变化时自动刷新
        $('#database').on('change', () => {
            this.updateFilters();
            this.loadChartData();
        });
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
     * 根据选择的数据库类型更新实例选项
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
    
    /**
     * 根据选择的实例更新数据库选项
     */
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
            
            const response = await fetch(`/database-aggregations/?api=true&${params}`);
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
     * 更新筛选器
     */
    updateFilters() {
        this.currentFilters.db_type = $('#db_type').val();
        this.currentFilters.instance_id = $('#instance').val();
        this.currentFilters.database_name = $('#database').val();
        this.currentFilters.period_type = $('#period_type').val();
        this.currentFilters.start_date = $('#start_date').val();
        this.currentFilters.end_date = $('#end_date').val();
    }
    
    /**
     * 应用筛选条件
     */
    applyFilters() {
        console.log('应用筛选条件');
        this.updateFilters();
        console.log('当前筛选条件:', this.currentFilters);
        
        // 重新加载数据
        this.loadSummaryData();
        this.loadChartData();
        this.loadTableData();
    }
    
    /**
     * 重置筛选条件
     */
    resetFilters() {
        console.log('重置筛选条件');
        
        // 清空所有筛选器
        $('#instanceFilter').val('');
        $('#dbTypeFilter').val('');
        $('#databaseFilter').val('');
        $('#periodTypeFilter').val('daily');
        $('#startDateFilter').val('');
        $('#endDateFilter').val('');
        
        // 重置筛选条件
        this.currentFilters = {
            instance_id: null,
            db_type: null,
            database_name: null,
            period_type: 'daily',
            start_date: null,
            end_date: null
        };
        
        // 重新加载数据
        this.loadSummaryData();
        this.loadChartData();
        this.loadTableData();
    }
    
    /**
     * 刷新所有数据
     */
    async refreshAllData() {
        console.log('刷新所有数据');
        this.showLoading();
        
        try {
            await Promise.all([
                this.loadSummaryData(),
                this.loadChartData(),
                this.loadTableData()
            ]);
            this.showSuccess('数据刷新成功');
        } catch (error) {
            console.error('刷新数据失败:', error);
            this.showError('刷新数据失败: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    /**
     * 加载汇总数据
     */
    async loadSummaryData() {
        try {
            const params = this.buildFilterParams();
            const response = await fetch(`/database-aggregations/summary?api=true&${params}`);
            const data = await response.json();
            
            if (response.ok) {
                this.updateSummaryCards(data);
            } else {
                console.error('加载汇总数据失败:', data.error);
            }
        } catch (error) {
            console.error('加载汇总数据时出错:', error);
        }
    }
    
    /**
     * 更新汇总卡片
     */
    updateSummaryCards(data) {
        $('#totalInstances').text(data.total_instances || 0);
        $('#totalDatabases').text(data.total_databases || 0);
        $('#averageSize').text(this.formatSizeFromMB(data.avg_size_mb || 0));
        $('#maxSize').text(this.formatSizeFromMB(data.max_size_mb || 0));
    }
    
    /**
     * 加载图表数据
     */
    async loadChartData() {
        try {
            this.showChartLoading();
            
            const params = this.buildFilterParams();
            params.append('chart_mode', 'database');
            params.append('get_all', 'true');
            
            console.log('加载图表数据，参数:', params.toString());
            const response = await fetch(`/database-aggregations/?api=true&${params}`);
            const data = await response.json();
            
            console.log('图表数据响应:', data);
            
            if (response.ok) {
                this.currentData = data.data;
                console.log('当前图表数据:', this.currentData);
                this.renderChart(data.data);
            } else {
                console.error('图表数据加载失败:', data.error);
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
        console.log('渲染数据库统计图表，数据:', data);
        
        const ctx = document.getElementById('databaseChart').getContext('2d');
        
        // 销毁现有图表
        if (this.chart) {
            this.chart.destroy();
        }
        
        if (!data || data.length === 0) {
            this.showEmptyChart();
            return;
        }
        
        // 按日期分组数据
        const groupedData = this.groupDataByDate(data);
        
        // 准备图表数据
        const chartData = this.prepareChartData(groupedData);
        
        // 创建图表
        this.chart = new Chart(ctx, {
            type: this.currentChartType,
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '数据库统计趋势图'
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: (context) => {
                                const label = context.dataset.label || '';
                                const value = this.formatSizeFromMB(context.parsed.y);
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
                            text: '时间'
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
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
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
        
        console.log('分组后的数据:', grouped);
        return grouped;
    }
    
    /**
     * 准备图表数据
     */
    prepareChartData(groupedData) {
        const labels = Object.keys(groupedData).sort();
        const datasets = [];
        const colors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
            '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
        ];
        
        // 收集所有数据库名称
        const allDatabases = new Set();
        Object.values(groupedData).forEach(dateData => {
            Object.keys(dateData).forEach(dbName => {
                allDatabases.add(dbName);
            });
        });
        
        let colorIndex = 0;
        
        // 为每个数据库创建数据集
        allDatabases.forEach(dbName => {
            const data = labels.map(date => groupedData[date][dbName] || 0);
            
            datasets.push({
                label: dbName,
                data: data,
                borderColor: colors[colorIndex % colors.length],
                backgroundColor: colors[colorIndex % colors.length] + '20',
                fill: false,
                tension: 0.1
            });
            
            colorIndex++;
        });
        
        return {
            labels: labels,
            datasets: datasets
        };
    }
    
    /**
     * 显示空图表
     */
    showEmptyChart() {
        const ctx = document.getElementById('databaseChart').getContext('2d');
        
        if (this.chart) {
            this.chart.destroy();
        }
        
        this.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['暂无数据'],
                datasets: [{
                    label: '暂无数据',
                    data: [0],
                    backgroundColor: '#f8f9fa',
                    borderColor: '#dee2e6'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '数据库统计趋势图 - 暂无数据'
                    }
                }
            }
        });
    }
    
    /**
     * 加载表格数据
     */
    async loadTableData() {
        try {
            const params = this.buildFilterParams();
            const response = await fetch(`/database-aggregations/?api=true&${params}`);
            const data = await response.json();
            
            if (response.ok) {
                this.renderTable(data.data);
            } else {
                console.error('加载表格数据失败:', data.error);
                this.showError('加载表格数据失败: ' + data.error);
            }
        } catch (error) {
            console.error('加载表格数据时出错:', error);
            this.showError('加载表格数据时出错: ' + error.message);
        }
    }
    
    /**
     * 渲染表格
     */
    renderTable(data) {
        const tbody = $('#databaseTable tbody');
        tbody.empty();
        
        if (!data || data.length === 0) {
            tbody.append(`
                <tr>
                    <td colspan="9" class="text-center text-muted">
                        <i class="fas fa-inbox me-2"></i>
                        暂无数据
                    </td>
                </tr>
            `);
            return;
        }
        
        // 按数据库分组并计算统计
        const databaseStats = this.calculateDatabaseStats(data);
        
        databaseStats.forEach(stat => {
            const row = `
                <tr>
                    <td>
                        <span class="instance-name">${stat.instance_name}</span>
                    </td>
                    <td>
                        <span class="database-name">${stat.database_name}</span>
                    </td>
                    <td>
                        <span class="db-type-badge ${stat.db_type.toLowerCase()}">${stat.db_type}</span>
                    </td>
                    <td>
                        <span class="size-display">${this.formatSizeFromMB(stat.avg_size_mb)}</span>
                    </td>
                    <td>
                        <span class="size-display">${this.formatSizeFromMB(stat.max_size_mb)}</span>
                    </td>
                    <td>
                        <span class="size-display">${this.formatSizeFromMB(stat.min_size_mb)}</span>
                    </td>
                    <td>${stat.data_count}</td>
                    <td>${this.formatDate(stat.last_update)}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary btn-action" 
                                onclick="window.databaseAggregationsManager.showDetail('${stat.instance_name}', '${stat.database_name}')">
                            <i class="fas fa-eye"></i>
                        </button>
                    </td>
                </tr>
            `;
            tbody.append(row);
        });
    }
    
    /**
     * 计算数据库统计
     */
    calculateDatabaseStats(data) {
        const databaseMap = {};
        
        data.forEach(item => {
            const key = `${item.instance.name}_${item.database_name}`;
            if (!databaseMap[key]) {
                databaseMap[key] = {
                    instance_name: item.instance.name,
                    database_name: item.database_name,
                    db_type: item.instance.db_type,
                    avg_size_mb: 0,
                    max_size_mb: 0,
                    min_size_mb: Infinity,
                    data_count: 0,
                    last_update: null
                };
            }
            
            const stat = databaseMap[key];
            stat.avg_size_mb = item.avg_size_mb;
            stat.max_size_mb = Math.max(stat.max_size_mb, item.max_size_mb);
            stat.min_size_mb = Math.min(stat.min_size_mb, item.min_size_mb);
            stat.data_count = item.data_count;
            
            if (!stat.last_update || new Date(item.calculated_at) > new Date(stat.last_update)) {
                stat.last_update = item.calculated_at;
            }
        });
        
        // 处理最小值为Infinity的情况
        Object.values(databaseMap).forEach(stat => {
            if (stat.min_size_mb === Infinity) {
                stat.min_size_mb = 0;
            }
        });
        
        return Object.values(databaseMap).sort((a, b) => b.avg_size_mb - a.avg_size_mb);
    }
    
    /**
     * 显示详情
     */
    showDetail(instanceName, databaseName) {
        console.log('显示数据库详情:', instanceName, databaseName);
        
        // 过滤当前数据库的数据
        const databaseData = this.currentData.filter(item => 
            item.instance.name === instanceName && item.database_name === databaseName
        );
        
        if (databaseData.length === 0) {
            this.showError('未找到相关数据');
            return;
        }
        
        // 更新模态框内容
        this.updateDetailModal(databaseData[0], databaseData);
        
        // 显示模态框
        $('#detailModal').modal('show');
    }
    
    /**
     * 更新详情模态框
     */
    updateDetailModal(sampleData, allData) {
        $('#modalInstanceName').text(sampleData.instance.name);
        $('#modalDatabaseName').text(sampleData.database_name);
        $('#modalDbType').text(sampleData.instance.db_type);
        $('#modalPeriodType').text(sampleData.period_type);
        $('#modalPeriodRange').text(`${sampleData.period_start} 至 ${sampleData.period_end}`);
        $('#modalDataCount').text(sampleData.data_count);
        
        // 计算统计信息
        const avgSize = allData.reduce((sum, item) => sum + item.avg_size_mb, 0) / allData.length;
        const maxSize = Math.max(...allData.map(item => item.max_size_mb));
        const minSize = Math.min(...allData.map(item => item.min_size_mb));
        const avgDataSize = allData.reduce((sum, item) => sum + (item.avg_data_size_mb || 0), 0) / allData.length;
        const avgLogSize = allData.reduce((sum, item) => sum + (item.avg_log_size_mb || 0), 0) / allData.length;
        const lastUpdate = allData.reduce((latest, item) => 
            new Date(item.calculated_at) > new Date(latest) ? item.calculated_at : latest, 
            allData[0].calculated_at
        );
        
        $('#modalAvgSize').text(this.formatSizeFromMB(avgSize));
        $('#modalMaxSize').text(this.formatSizeFromMB(maxSize));
        $('#modalMinSize').text(this.formatSizeFromMB(minSize));
        $('#modalAvgDataSize').text(this.formatSizeFromMB(avgDataSize));
        $('#modalAvgLogSize').text(this.formatSizeFromMB(avgLogSize));
        $('#modalLastUpdate').text(this.formatDate(lastUpdate));
        
        // 渲染详情图表
        this.renderDetailChart(allData);
    }
    
    /**
     * 渲染详情图表
     */
    renderDetailChart(data) {
        const ctx = document.getElementById('detailChart').getContext('2d');
        
        // 销毁现有图表
        const existingChart = Chart.getChart(ctx);
        if (existingChart) {
            existingChart.destroy();
        }
        
        const sortedData = data.sort((a, b) => new Date(a.period_start) - new Date(b.period_start));
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: sortedData.map(item => item.period_start),
                datasets: [{
                    label: '平均大小',
                    data: sortedData.map(item => item.avg_size_mb),
                    borderColor: '#0d6efd',
                    backgroundColor: '#0d6efd20',
                    fill: false,
                    tension: 0.1
                }, {
                    label: '最大大小',
                    data: sortedData.map(item => item.max_size_mb),
                    borderColor: '#dc3545',
                    backgroundColor: '#dc354520',
                    fill: false,
                    tension: 0.1
                }, {
                    label: '最小大小',
                    data: sortedData.map(item => item.min_size_mb),
                    borderColor: '#198754',
                    backgroundColor: '#19875420',
                    fill: false,
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '大小趋势图'
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
     * 聚合计算
     */
    async calculateAggregations() {
        console.log('开始聚合计算');
        
        // 显示进度模态框
        $('#calculationModal').modal('show');
        
        try {
            const response = await fetch('/database-sizes/aggregate-today', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.showSuccess('聚合计算完成');
                // 重新加载数据
                this.refreshAllData();
            } else {
                this.showError('聚合计算失败: ' + data.error);
            }
        } catch (error) {
            console.error('聚合计算时出错:', error);
            this.showError('聚合计算时出错: ' + error.message);
        } finally {
            $('#calculationModal').modal('hide');
        }
    }
    
    /**
     * 构建筛选参数
     */
    buildFilterParams() {
        const params = new URLSearchParams();
        
        if (this.currentFilters.instance_id) {
            params.append('instance_id', this.currentFilters.instance_id);
        }
        if (this.currentFilters.db_type) {
            params.append('db_type', this.currentFilters.db_type);
        }
        if (this.currentFilters.database_name) {
            params.append('database_name', this.currentFilters.database_name);
        }
        if (this.currentFilters.period_type) {
            params.append('period_type', this.currentFilters.period_type);
        }
        if (this.currentFilters.start_date) {
            params.append('start_date', this.currentFilters.start_date);
        }
        if (this.currentFilters.end_date) {
            params.append('end_date', this.currentFilters.end_date);
        }
        
        return params;
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
     * 显示加载状态
     */
    showLoading() {
        // 可以添加全局加载状态
    }
    
    /**
     * 隐藏加载状态
     */
    hideLoading() {
        // 可以添加全局加载状态
    }
    
    /**
     * 显示成功消息
     */
    showSuccess(message) {
        toastr.success(message);
    }
    
    /**
     * 显示错误消息
     */
    showError(message) {
        toastr.error(message);
    }
    
    /**
     * 格式化大小
     */
    formatSizeFromMB(mb) {
        if (mb === 0) return '0 B';
        if (mb < 1024) return `${mb.toFixed(2)} MB`;
        if (mb < 1024 * 1024) return `${(mb / 1024).toFixed(2)} GB`;
        return `${(mb / (1024 * 1024)).toFixed(2)} TB`;
    }
    
    /**
     * 格式化日期
     */
    formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleString('zh-CN');
    }
    
    /**
     * 获取CSRF令牌
     */
    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }
}

