/**
 * 实例统计页面脚本
 * 基于 jQuery 3.7.1 和 Chart.js 4.4.0
 */

class InstanceAggregationsManager {
    constructor() {
        this.chart = null;
        this.changeChart = null;
        this.currentData = [];
        this.changeChartData = [];
        this.currentChartType = 'line';
        this.currentTopCount = 5; // 默认显示TOP5
        this.currentStatisticsPeriod = 7; // 默认7个周期
        this.changeChartType = 'line';
        this.changeTopCount = 5;
        this.changeStatisticsPeriod = 7;
        this.changeFilters = {
            start_date: null,
            end_date: null,
            override: false,
            period_type: 'daily'
        };
        this.changePercentChart = null;
        this.changePercentChartData = [];
        this.changePercentChartType = 'line';
        this.changePercentTopCount = 5;
        this.changePercentStatisticsPeriod = 7;
        this.changePercentFilters = {
            start_date: null,
            end_date: null,
            override: false,
            period_type: 'daily'
        };
        this.currentFilters = {
            instance_id: null,
            db_type: null,
            period_type: 'daily',
            start_date: null,
            end_date: null
        };
        
        this.init();
    }
    
    init() {
        console.log('初始化实例统计管理器');
        this.initializeCurrentFilters();
        this.bindEvents();
        this.initializeDatabaseFilter();
        this.updateTimeRangeFromPeriod(); // 初始化时间范围
        this.syncUIState(); // 同步UI状态
        this.loadSummaryData();
        this.loadChartData();
        this.loadChangeChartData();
        this.loadChangePercentChartData();
    }

    initializeCurrentFilters() {
        const dbTypeValue = $('#db_type').val();
        const instanceValue = $('#instance').val();
        this.currentFilters.db_type = dbTypeValue ? dbTypeValue.toLowerCase() : null;
        this.currentFilters.instance_id = instanceValue || null;
        this.currentFilters.period_type = $('#period_type').val() || 'daily';
        this.currentFilters.start_date = $('#start_date').val() || null;
        this.currentFilters.end_date = $('#end_date').val() || null;
        if (instanceValue) {
            $('#instance').data('selected', instanceValue);
        }
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
        
        // TOP选择器切换
        $('input[name="topSelector"]').on('change', (e) => {
            this.currentTopCount = parseInt(e.target.value);
            this.renderChart(this.currentData);
        });

        // 容量变化图表类型切换
        $('input[name="changeChartType"]').on('change', (e) => {
            this.changeChartType = e.target.value;
            this.renderChangeChart(this.changeChartData);
        });
        
        // 容量变化TOP选择器切换
        $('input[name="changeTopSelector"]').on('change', (e) => {
            this.changeTopCount = parseInt(e.target.value);
            this.renderChangeChart(this.changeChartData);
        });
        
        // 容量变化统计周期选择器切换
        $('input[name="changeStatisticsPeriod"]').on('change', (e) => {
            this.changeStatisticsPeriod = parseInt(e.target.value, 10);
            this.updateChangeChartOverrideRange();
            this.loadChangeChartData();
        });
        
        // 容量变化百分比图表类型切换
        $('input[name="changePercentChartType"]').on('change', (e) => {
            this.changePercentChartType = e.target.value;
            this.renderChangePercentChart(this.changePercentChartData);
        });
        
        // 容量变化百分比TOP选择器切换
        $('input[name="changePercentTopSelector"]').on('change', (e) => {
            this.changePercentTopCount = parseInt(e.target.value, 10);
            this.renderChangePercentChart(this.changePercentChartData);
        });
        
        // 容量变化百分比统计周期切换
        $('input[name="changePercentStatisticsPeriod"]').on('change', (e) => {
            this.changePercentStatisticsPeriod = parseInt(e.target.value, 10);
            this.updateChangePercentChartOverrideRange();
            this.loadChangePercentChartData();
        });
        
        // 统计周期选择器切换
        $('input[name="statisticsPeriod"]').on('change', (e) => {
            this.currentStatisticsPeriod = parseInt(e.target.value);
            this.updateTimeRangeFromPeriod();
            this.loadSummaryData(); // 更新统计卡片
            this.loadChartData();   // 更新趋势图
            this.loadChangeChartData(); // 更新变化趋势图
        });
        
        // 统计周期选择器切换
        $('#period_type').on('change', (e) => {
            this.currentFilters.period_type = e.target.value;
            this.updateTimeRangeFromPeriod();
            if (this.changeFilters.override) {
                this.updateChangeChartOverrideRange();
            }
            if (this.changePercentFilters.override) {
                this.updateChangePercentChartOverrideRange();
            }
            this.loadSummaryData(); // 更新统计卡片
            this.loadChartData();   // 更新趋势图
            this.loadChangeChartData(); // 更新变化趋势图
            this.loadChangePercentChartData(); // 更新百分比变化趋势图
        });
        
        // 筛选按钮
        $('#searchButton, #applyFilters').on('click', () => {
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
            console.log('更新后的筛选条件:', this.currentFilters);
            this.loadSummaryData(); // 更新统计卡片
            this.loadChartData();   // 更新趋势图
            this.loadChangeChartData(); // 更新变化趋势图
        });
        
        // 实例变化时自动刷新
        $('#instance').on('change', () => {
            this.updateFilters();
            this.loadSummaryData(); // 更新统计卡片
            this.loadChartData();   // 更新趋势图
            this.loadChangeChartData(); // 更新变化趋势图
        });
    }
    
    /**
     * 渲染容量变化百分比趋势图
     */
    renderChangePercentChart(data) {
        const canvas = document.getElementById('instanceChangePercentChart');
        if (!canvas) {
            return;
        }
        
        const ctx = canvas.getContext('2d');
        
        if (this.changePercentChart) {
            this.changePercentChart.destroy();
        }
        
        if (!data || data.length === 0) {
            this.showEmptyChangePercentChart();
            return;
        }
        
        const groupedData = this.groupChangePercentDataByDate(data);
        const chartData = this.prepareChangePercentChartData(groupedData);
        
        if (!chartData || chartData.labels.length === 0 || chartData.datasets.length === 0) {
            this.showEmptyChangePercentChart();
            return;
        }
        
        const allValues = [];
        chartData.datasets.forEach(dataset => {
            dataset.data.forEach(value => {
                if (typeof value === 'number' && !Number.isNaN(value)) {
                    allValues.push(value);
                }
            });
        });
        const minValue = allValues.length ? Math.min(...allValues, 0) : 0;
        const maxValue = allValues.length ? Math.max(...allValues, 0) : 0;
        const rangePadding = Math.max((maxValue - minValue) * 0.1, 1);
        const suggestedMin = Math.min(minValue - rangePadding, -5);
        const suggestedMax = Math.max(maxValue + rangePadding, 5);
        
        this.changePercentChart = new Chart(ctx, {
            type: this.changePercentChartType,
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '容量变化趋势图 (百分比)'
                    },
                    legend: {
                        display: true,
                        position: 'right'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: (context) => {
                                const label = context.dataset.label || '';
                                const value = context.parsed.y;
                                if (value === null || value === undefined || Number.isNaN(value)) {
                                    return `${label}: 无数据`;
                                }
                                const formatted = `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
                                return `${label}: ${formatted}`;
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
                            text: '变化率 (%)'
                        },
                        suggestedMin,
                        suggestedMax,
                        grid: {
                            color: (context) => {
                                if (context.tick && context.tick.value === 0) {
                                    return '#212529';
                                }
                                return 'rgba(0, 0, 0, 0.08)';
                            },
                            lineWidth: (context) => (context.tick && context.tick.value === 0 ? 2 : 1),
                            borderDash: (context) => (context.tick && context.tick.value === 0 ? [] : [2, 2]),
                            drawTicks: true
                        }
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
     * 初始化数据库筛选器
     */
    initializeDatabaseFilter() {
        const instanceSelect = $('#instance');
        
        // 如果已有数据库类型选中，则先加载对应实例列表
        const initialDbType = $('#db_type').val();
        if (initialDbType) {
            this.updateInstanceOptions(initialDbType, { preserveSelection: true }).then(() => {
                // 恢复已选实例
                const initialInstance = this.currentFilters.instance_id || $('#instance').data('selected');
                if (initialInstance) {
                    $('#instance').val(initialInstance);
                }
            });
        } else {
            instanceSelect.empty();
            instanceSelect.append('<option value="">请先选择数据库类型</option>');
            instanceSelect.prop('disabled', true);
        }
        
        // 保存当前实例选择
        const instanceSelectElement = document.getElementById('instance');
        if (instanceSelectElement) {
            const selectedValue = instanceSelectElement.value;
            $('#instance').data('selected', selectedValue);
        }
    }
    
    /**
     * 根据选择的数据库类型更新实例选项
     */
    async updateInstanceOptions(dbType, options = {}) {
        const { preserveSelection = false } = options;
        const instanceSelect = $('#instance');
        const normalizedDbType = dbType ? dbType.toLowerCase() : null;
        
        const storedSelection = preserveSelection
            ? (this.currentFilters.instance_id || instanceSelect.data('selected') || '')
            : '';
        
        if (!preserveSelection) {
            // 切换数据库类型时清空已选实例
            this.currentFilters.instance_id = null;
            instanceSelect.data('selected', '');
            instanceSelect.val('');
        }
        
        try {
            instanceSelect.prop('disabled', false);
            let url = '/instance_stats/api/instance-options';
            if (normalizedDbType) {
                url += `?db_type=${encodeURIComponent(normalizedDbType)}`;
            }
            const response = await fetch(url);
            const data = await response.json();
            
            if (response.ok && data.success) {
                instanceSelect.empty();
                instanceSelect.append('<option value="">所有实例</option>');
                const selectedInstance = preserveSelection ? storedSelection : null;
                let matchedInstance = null;
                const instances = data?.data?.instances ?? data.instances ?? [];
                instances.forEach(instance => {
                    const option = document.createElement('option');
                    option.value = String(instance.id);
                    option.textContent = `${instance.name} (${instance.db_type})`;
                    if (selectedInstance && String(selectedInstance) === String(instance.id)) {
                        option.selected = true;
                        matchedInstance = String(instance.id);
                    }
                    instanceSelect.append(option);
                });
                
                if (matchedInstance) {
                    instanceSelect.val(matchedInstance);
                    this.currentFilters.instance_id = matchedInstance;
                    instanceSelect.data('selected', matchedInstance);
                }
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
     * 加载实例列表
     */
    async loadInstances(dbType = null) {
        try {
            const normalizedDbType = dbType ? dbType.toLowerCase() : null;
            let url = '/instance_stats/api/instance-options';
            if (normalizedDbType) {
                url += `?db_type=${encodeURIComponent(normalizedDbType)}`;
            }
            
            const response = await fetch(url);
            const data = await response.json();
            
            if (response.ok && data.success) {
                const select = $('#instance');
                select.empty();
                select.append('<option value="">所有实例</option>');
                const selectedInstance = this.currentFilters.instance_id;
                
                const instances = data?.data?.instances ?? data.instances ?? [];
                instances.forEach(instance => {
                    const option = document.createElement('option');
                    option.value = String(instance.id);
                    option.textContent = `${instance.name} (${instance.db_type})`;
                    if (selectedInstance && String(selectedInstance) === String(instance.id)) {
                        option.selected = true;
                    }
                    select.append(option);
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
        const dbTypeValue = $('#db_type').val();
        const instanceValue = $('#instance').val();
        this.currentFilters.db_type = dbTypeValue ? dbTypeValue.toLowerCase() : null;
        this.currentFilters.instance_id = instanceValue || null;
        $('#instance').data('selected', this.currentFilters.instance_id || '');
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
        
        // 使用用户指定的时间范围并清除容量变化图的独立覆盖
        this.changeFilters.start_date = this.currentFilters.start_date || null;
        this.changeFilters.end_date = this.currentFilters.end_date || null;
        this.changeFilters.override = false;
        this.changeFilters.period_type = this.currentFilters.period_type || 'daily';
        this.changePercentFilters.start_date = this.currentFilters.start_date || null;
        this.changePercentFilters.end_date = this.currentFilters.end_date || null;
        this.changePercentFilters.override = false;
        this.changePercentFilters.period_type = this.currentFilters.period_type || 'daily';
        
        // 重新加载数据
        this.loadSummaryData();
        this.loadChartData();
        this.loadChangeChartData();
        this.loadChangePercentChartData();
    }
    
    /**
     * 重置筛选条件
     */
    resetFilters() {
        console.log('重置筛选条件');
        
        // 清空所有筛选器
        $('#instance').val('');
        $('#db_type').val('');
        $('#period_type').val('daily');
        $('#start_date').val('');
        $('#end_date').val('');
        
        // 重置筛选条件
        this.currentFilters = {
            instance_id: null,
            db_type: null,
            period_type: 'daily',
            start_date: null,
            end_date: null
        };
        this.changeStatisticsPeriod = 7;
        this.changeFilters = {
            start_date: null,
            end_date: null,
            override: false,
            period_type: 'daily'
        };
        this.changePercentChartType = 'line';
        this.changePercentTopCount = 5;
        this.changePercentStatisticsPeriod = 7;
        this.changePercentFilters = {
            start_date: null,
            end_date: null,
            override: false,
            period_type: 'daily'
        };
        
        // 重新加载数据
        this.loadSummaryData();
        this.loadChartData();
        this.loadChangeChartData();
        this.loadChangePercentChartData();
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
                this.loadChangeChartData(),
                this.loadChangePercentChartData()
            ]);
            this.syncUIState(); // 同步UI状态
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
            console.log('加载汇总数据，参数:', params.toString());
            const response = await fetch(`/instance_stats/api/instances/aggregations/summary?${params}`);
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
        // 从统一响应体中提取 summary 数据
        const summaryData = data?.data?.summary ?? data?.data ?? data ?? {};
        console.log('更新统计卡片数据:', summaryData);
        $('#totalInstances').text(summaryData.total_instances ?? 0);
        $('#totalDatabases').text(this.formatSizeFromMB(summaryData.total_size_mb ?? 0));
        $('#averageSize').text(this.formatSizeFromMB(summaryData.avg_size_mb ?? 0));
        $('#maxSize').text(this.formatSizeFromMB(summaryData.max_size_mb ?? 0));
    }
    
    /**
     * 加载图表数据
     */
    async loadChartData() {
        try {
            this.showChartLoading();
            
            const params = this.buildFilterParams();
            params.append('chart_mode', 'instance');
            params.append('get_all', 'true');
            
            console.log('加载图表数据，参数:', params.toString());
            const response = await fetch(`/instance_stats/api/instances/aggregations?${params}`);
            const data = await response.json();
            
            console.log('图表数据响应:', data);
            
            if (response.ok) {
                // 使用所有数据，不进行前端限制
                const payload = data?.data?.items ?? data?.data ?? data ?? [];
                this.currentData = Array.isArray(payload) ? payload : [];
                console.log('当前图表数据:', this.currentData.length);
                this.renderChart(this.currentData);
                // 重新同步UI状态
                this.syncUIState();
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
     * 加载容量变化图表数据
     */
    async loadChangeChartData() {
        try {
            this.showChangeChartLoading();
            
            const params = this.buildChangeChartParams();
            console.log('加载容量变化图表数据，参数:', params.toString());
            const response = await fetch(`/instance_stats/api/instances/aggregations?${params}`);
            const data = await response.json();
            
            if (response.ok) {
                const payload = data?.data?.items ?? data?.data ?? data ?? [];
                this.changeChartData = Array.isArray(payload) ? payload : [];
                console.log('容量变化图表数据条目:', this.changeChartData.length);
                this.renderChangeChart(this.changeChartData);
                this.syncUIState();
            } else {
                console.error('容量变化图表数据加载失败:', data.error);
                this.showError('容量变化趋势数据加载失败: ' + data.error);
            }
        } catch (error) {
            console.error('加载容量变化数据时出错:', error);
            this.showError('加载容量变化数据时出错: ' + error.message);
        } finally {
            this.hideChangeChartLoading();
        }
    }
    
    /**
     * 加载容量变化百分比图表数据
     */
    async loadChangePercentChartData() {
        try {
            this.showChangePercentChartLoading();
            
            const params = this.buildChangePercentChartParams();
            console.log('加载容量变化百分比图表数据，参数:', params.toString());
            const response = await fetch(`/instance_stats/api/instances/aggregations?${params}`);
            const data = await response.json();
            
            if (response.ok) {
                const payload = data?.data?.items ?? data?.data ?? data ?? [];
                this.changePercentChartData = Array.isArray(payload) ? payload : [];
                console.log('容量变化百分比图表数据条目:', this.changePercentChartData.length);
                this.renderChangePercentChart(this.changePercentChartData);
                this.syncUIState();
            } else {
                console.error('容量变化百分比数据加载失败:', data.error);
                this.showError('容量变化百分比数据加载失败: ' + data.error);
            }
        } catch (error) {
            console.error('加载容量变化百分比数据时出错:', error);
            this.showError('加载容量变化百分比数据时出错: ' + error.message);
        } finally {
            this.hideChangePercentChartLoading();
        }
    }
    
    /**
     * 渲染图表
     */
    renderChart(data) {
        console.log('渲染实例统计图表，数据:', data);
        
        const ctx = document.getElementById('instanceChart').getContext('2d');
        
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
                        text: '实例统计趋势图'
                    },
                    legend: {
                        display: true,
                        position: 'right'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: (context) => {
                                const label = context.dataset.label || '';
                                const value = `${context.parsed.y.toFixed(2)} GB`;
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
                            text: '大小 (GB)'
                        },
                        beginAtZero: true,
                        grid: {
                            color: (ctx) => (ctx.tick && ctx.tick.value === 0 ? '#212529' : 'rgba(0,0,0,0.08)'),
                            lineWidth: (ctx) => (ctx.tick && ctx.tick.value === 0 ? 2 : 1),
                            borderDash: (ctx) => (ctx.tick && ctx.tick.value === 0 ? [] : [2, 2])
                        }
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
     * 渲染容量变化趋势图
     */
    renderChangeChart(data) {
        const canvas = document.getElementById('instanceChangeChart');
        if (!canvas) {
            return;
        }
        
        const ctx = canvas.getContext('2d');
        
        if (this.changeChart) {
            this.changeChart.destroy();
        }
        
        if (!data || data.length === 0) {
            this.showEmptyChangeChart();
            return;
        }
        
        const groupedData = this.groupChangeDataByDate(data);
        const chartData = this.prepareChangeChartData(groupedData);
        
        if (!chartData || chartData.labels.length === 0 || chartData.datasets.length === 0) {
            this.showEmptyChangeChart();
            return;
        }
        
        const allValues = [];
        chartData.datasets.forEach(dataset => {
            dataset.data.forEach(value => {
                if (typeof value === 'number' && !Number.isNaN(value)) {
                    allValues.push(value);
                }
            });
        });
        const minValue = allValues.length ? Math.min(...allValues, 0) : 0;
        const maxValue = allValues.length ? Math.max(...allValues, 0) : 0;
        const rangePadding = Math.max((maxValue - minValue) * 0.1, 1);
        const suggestedMin = Math.min(minValue - rangePadding, 0);
        const suggestedMax = Math.max(maxValue + rangePadding, 0);
        
        this.changeChart = new Chart(ctx, {
            type: this.changeChartType,
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '容量变化趋势图'
                    },
                    legend: {
                        display: true,
                        position: 'right'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: (context) => {
                                const label = context.dataset.label || '';
                                const value = context.parsed.y;
                                if (value === null || value === undefined || Number.isNaN(value)) {
                                    return `${label}: 无数据`;
                                }
                                const formatted = `${value >= 0 ? '+' : ''}${value.toFixed(2)} GB`;
                                return `${label}: ${formatted}`;
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
                            text: '变化量 (GB)'
                        },
                        suggestedMin,
                        suggestedMax,
                        grid: {
                            color: (context) => {
                                if (context.tick && context.tick.value === 0) {
                                    return '#212529';
                                }
                                return 'rgba(0, 0, 0, 0.08)';
                            },
                            lineWidth: (context) => (context.tick && context.tick.value === 0 ? 2 : 1),
                            borderDash: (context) => (context.tick && context.tick.value === 0 ? [] : [2, 2]),
                            drawTicks: true
                        }
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
            // 统一使用period_end作为X轴显示日期
            const date = item.period_end;
            if (!date) {
                console.warn('数据项缺少period_end:', item);
                return;
            }
            
            if (!grouped[date]) {
                grouped[date] = {};
            }
            
            // 按实例分组，使用实例的总容量
            const instanceName = item.instance?.name || '未知实例';
            if (!Object.prototype.hasOwnProperty.call(grouped[date], instanceName)) {
                grouped[date][instanceName] = null;
            }
            // 使用total_size_mb，表示实例的总容量（直接赋值，因为每个实例每天只有一条记录）
            const sizeValue = Number(item.total_size_mb);
            grouped[date][instanceName] = Number.isFinite(sizeValue) ? sizeValue : null;
        });
        
        console.log('分组后的数据:', grouped);
        return grouped;
    }
    
    /**
     * 按日期分组容量变化数据
     */
    groupChangeDataByDate(data) {
        const grouped = {};
        
        data.forEach(item => {
            // 统一使用period_end作为X轴显示日期
            const date = item.period_end;
            if (!date) {
                console.warn('容量变化数据缺少period_end:', item);
                return;
            }
            
            if (!grouped[date]) {
                grouped[date] = {};
            }
            
            const instanceName = item.instance?.name || '未知实例';
            const changeValue = Number(item.total_size_change_mb ?? 0);
            grouped[date][instanceName] = Number.isNaN(changeValue) ? 0 : changeValue;
        });
        
        console.log('容量变化分组数据:', grouped);
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
            '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF',
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
            '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
            '#BB8FCE', '#85C1E9', '#F8C471', '#82E0AA'
        ];
        
        // 收集所有实例名称和它们的最大容量
        const instanceMaxSizes = new Map();
        Object.values(groupedData).forEach(dateData => {
            Object.keys(dateData).forEach(instanceName => {
                const currentSize = dateData[instanceName] || 0;
                const existingMax = instanceMaxSizes.get(instanceName) || 0;
                instanceMaxSizes.set(instanceName, Math.max(existingMax, currentSize));
            });
        });
        
        // 按最大容量排序，获取TOP N实例
        const sortedInstances = Array.from(instanceMaxSizes.entries())
            .sort((a, b) => b[1] - a[1])
            .slice(0, this.currentTopCount)
            .map(([name]) => name);
        
        console.log(`显示TOP ${this.currentTopCount}实例:`, sortedInstances);
        
        let colorIndex = 0;
        
        // 为TOP N实例创建数据集
        sortedInstances.forEach(instanceName => {
            let lastKnownValue = null;
            // 将MB转换为GB用于图表显示
            const data = labels.map(date => {
                const dateData = groupedData[date] || {};
                const mbValue = dateData[instanceName];
                if (mbValue === undefined || mbValue === null) {
                    return lastKnownValue !== null ? lastKnownValue / 1024 : null;
                }
                lastKnownValue = mbValue;
                return mbValue / 1024; // 转换为GB
            });
            
            const baseColor = colors[colorIndex % colors.length];
            datasets.push({
                label: instanceName,
                data: data,
                borderColor: baseColor,
                backgroundColor: this.currentChartType === 'line' ? this.colorWithAlpha(baseColor, 0.1) : this.colorWithAlpha(baseColor, 0.65),
                fill: this.currentChartType !== 'line',
                tension: 0.1,
                hidden: false // 确保数据点可见
            });
            
            colorIndex++;
        });
        
        return {
            labels: labels,
            datasets: datasets
        };
    }
    
    /**
     * 准备容量变化图表数据
     */
    prepareChangeChartData(groupedData) {
        const labels = Object.keys(groupedData).sort();
        const datasets = [];
        const colors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
            '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF',
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
            '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
            '#BB8FCE', '#85C1E9', '#F8C471', '#82E0AA'
        ];
        
        const instanceMaxChanges = new Map();
        Object.values(groupedData).forEach(dateData => {
            Object.entries(dateData).forEach(([instanceName, changeValue]) => {
                const absValue = Math.abs(changeValue || 0);
                const existingMax = instanceMaxChanges.get(instanceName) || 0;
                instanceMaxChanges.set(instanceName, Math.max(existingMax, absValue));
            });
        });
        
        const sortedInstances = Array.from(instanceMaxChanges.entries())
            .sort((a, b) => b[1] - a[1])
            .slice(0, this.changeTopCount)
            .map(([name]) => name);
        
        console.log(`容量变化TOP ${this.changeTopCount}实例:`, sortedInstances);
        
        let colorIndex = 0;
        const manager = this;
        
        sortedInstances.forEach(instanceName => {
            const data = labels.map(date => {
                const rawValue = groupedData[date][instanceName];
                if (rawValue === undefined || rawValue === null) {
                    return 0;
                }
                const numericValue = Number(rawValue);
                if (Number.isNaN(numericValue)) {
                    return 0;
                }
                return numericValue / 1024;
            });
            
            const baseColor = colors[colorIndex % colors.length];
            const dataset = {
                label: instanceName,
                data: data,
                borderColor: baseColor,
                backgroundColor: (ctx) => {
                    const value = ctx.parsed?.y ?? 0;
                    if (manager.changeChartType === 'line') {
                        return manager.colorWithAlpha(baseColor, 0.1);
                    }
                    return value >= 0
                        ? manager.colorWithAlpha(baseColor, 0.65)
                        : manager.colorWithAlpha(baseColor, 0.35);
                },
                fill: manager.changeChartType !== 'line',
                tension: manager.changeChartType === 'line' ? 0.3 : 0
            };
            
            if (manager.changeChartType === 'line') {
                dataset.segment = {
                    borderDash: (ctx) => {
                        const prev = ctx.p0?.parsed?.y ?? 0;
                        const curr = ctx.p1?.parsed?.y ?? 0;
                        const bothPositive = prev >= 0 && curr >= 0;
                        return bothPositive ? [] : [6, 4];
                    },
                    borderColor: () => baseColor
                };
                dataset.pointRadius = (ctx) => (Math.abs(ctx.parsed?.y ?? 0) < 0.001 ? 3 : 4);
                dataset.pointHoverRadius = 5;
                dataset.pointBackgroundColor = (ctx) => {
                    const value = ctx.parsed?.y ?? 0;
                    return value >= 0 ? manager.colorWithAlpha(baseColor, 0.85) : '#ffffff';
                };
                dataset.pointBorderColor = baseColor;
                dataset.pointBorderWidth = (ctx) => (ctx.parsed?.y ?? 0) >= 0 ? 1 : 2;
            } else {
                dataset.borderWidth = 1.5;
                dataset.borderDash = (ctx) => ((ctx.parsed?.y ?? 0) >= 0 ? [] : [6, 4]);
            }
            
            datasets.push(dataset);
            
            colorIndex++;
        });
        
        return {
            labels,
            datasets
        };
    }
    
    /**
     * 按日期分组容量变化百分比数据
     */
    groupChangePercentDataByDate(data) {
        const grouped = {};
        
        data.forEach(item => {
            // 统一使用period_end作为X轴显示日期
            const date = item.period_end;
            if (!date) {
                console.warn('容量变化百分比数据缺少period_end:', item);
                return;
            }
            
            if (!grouped[date]) {
                grouped[date] = {};
            }
            
            const instanceName = item.instance?.name || '未知实例';
            const changePercent = Number(item.total_size_change_percent ?? 0);
            grouped[date][instanceName] = Number.isNaN(changePercent) ? 0 : changePercent;
        });
        
        console.log('容量变化百分比分组数据:', grouped);
        return grouped;
    }
    
    /**
     * 准备容量变化百分比图表数据
     */
    prepareChangePercentChartData(groupedData) {
        const labels = Object.keys(groupedData).sort();
        const datasets = [];
        const colors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
            '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF',
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
            '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
            '#BB8FCE', '#85C1E9', '#F8C471', '#82E0AA'
        ];
        
        const instanceMaxPercents = new Map();
        Object.values(groupedData).forEach(dateData => {
            Object.entries(dateData).forEach(([instanceName, percentValue]) => {
                const absValue = Math.abs(percentValue || 0);
                const existingMax = instanceMaxPercents.get(instanceName) || 0;
                instanceMaxPercents.set(instanceName, Math.max(existingMax, absValue));
            });
        });
        
        const sortedInstances = Array.from(instanceMaxPercents.entries())
            .sort((a, b) => b[1] - a[1])
            .slice(0, this.changePercentTopCount)
            .map(([name]) => name);
        
        console.log(`容量变化百分比TOP ${this.changePercentTopCount}实例:`, sortedInstances);
        
        let colorIndex = 0;
        const manager = this;
        
        sortedInstances.forEach(instanceName => {
            const data = labels.map(date => {
                const rawValue = groupedData[date][instanceName];
                if (rawValue === undefined || rawValue === null) {
                    return 0;
                }
                const numericValue = Number(rawValue);
                if (Number.isNaN(numericValue)) {
                    return 0;
                }
                return numericValue;
            });
            
            const baseColor = colors[colorIndex % colors.length];
            const dataset = {
                label: instanceName,
                data: data,
                borderColor: baseColor,
                backgroundColor: (ctx) => {
                    const value = ctx.parsed?.y ?? 0;
                    if (manager.changePercentChartType === 'line') {
                        return manager.colorWithAlpha(baseColor, 0.1);
                    }
                    return value >= 0
                        ? manager.colorWithAlpha(baseColor, 0.65)
                        : manager.colorWithAlpha(baseColor, 0.35);
                },
                fill: manager.changePercentChartType !== 'line',
                tension: manager.changePercentChartType === 'line' ? 0.3 : 0
            };
            
            if (manager.changePercentChartType === 'line') {
                dataset.segment = {
                    borderDash: (ctx) => {
                        const prev = ctx.p0?.parsed?.y ?? 0;
                        const curr = ctx.p1?.parsed?.y ?? 0;
                        const bothPositive = prev >= 0 && curr >= 0;
                        return bothPositive ? [] : [6, 4];
                    },
                    borderColor: () => baseColor
                };
                dataset.pointRadius = (ctx) => (Math.abs(ctx.parsed?.y ?? 0) < 0.001 ? 3 : 4);
                dataset.pointHoverRadius = 5;
                dataset.pointBackgroundColor = (ctx) => {
                    const value = ctx.parsed?.y ?? 0;
                    return value >= 0 ? manager.colorWithAlpha(baseColor, 0.85) : '#ffffff';
                };
                dataset.pointBorderColor = baseColor;
                dataset.pointBorderWidth = (ctx) => (ctx.parsed?.y ?? 0) >= 0 ? 1 : 2;
            } else {
                dataset.borderWidth = 1.5;
                dataset.borderDash = (ctx) => ((ctx.parsed?.y ?? 0) >= 0 ? [] : [6, 4]);
            }
            
            datasets.push(dataset);
            colorIndex++;
        });
        
        return { labels, datasets };
    }
    
    /**
     * 显示空图表
     */
    showEmptyChart() {
        const ctx = document.getElementById('instanceChart').getContext('2d');
        
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
                        text: '实例统计趋势图 - 暂无数据'
                    }
                }
            }
        });
    }
    
    /**
     * 显示空的容量变化图表
     */
    showEmptyChangeChart() {
        const canvas = document.getElementById('instanceChangeChart');
        if (!canvas) {
            return;
        }
        
        const ctx = canvas.getContext('2d');
        
        if (this.changeChart) {
            this.changeChart.destroy();
        }
        
        this.changeChart = new Chart(ctx, {
            type: this.changeChartType,
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
                        text: '容量变化趋势图 - 暂无数据'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    /**
     * 显示空的容量变化百分比图表
     */
    showEmptyChangePercentChart() {
        const canvas = document.getElementById('instanceChangePercentChart');
        if (!canvas) {
            return;
        }
        
        const ctx = canvas.getContext('2d');
        
        if (this.changePercentChart) {
            this.changePercentChart.destroy();
        }
        
        this.changePercentChart = new Chart(ctx, {
            type: this.changePercentChartType,
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
                        text: '容量变化趋势图 (百分比) - 暂无数据'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
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
            const response = await fetch('/aggregations/api/aggregate-today', {
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
     * 根据统计周期更新时间范围
     */
    updateTimeRangeFromPeriod() {
        const periodType = this.currentFilters.period_type || 'daily';
        const range = this.calculateDateRange(periodType, this.currentStatisticsPeriod);
        this.currentFilters.start_date = range.startDate;
        this.currentFilters.end_date = range.endDate;
        if (!this.changeFilters.override) {
            this.changeFilters.start_date = range.startDate;
            this.changeFilters.end_date = range.endDate;
            this.changeFilters.period_type = periodType;
        }
        if (!this.changePercentFilters.override) {
            this.changePercentFilters.start_date = range.startDate;
            this.changePercentFilters.end_date = range.endDate;
            this.changePercentFilters.period_type = periodType;
        }
        
        console.log(`更新时间范围: ${this.currentStatisticsPeriod}个${periodType}周期`, {
            start_date: this.currentFilters.start_date,
            end_date: this.currentFilters.end_date
        });
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
     * 构建容量变化图表的筛选参数
     */
    buildChangeChartParams() {
        const params = new URLSearchParams();
        
        if (this.currentFilters.instance_id) {
            params.append('instance_id', this.currentFilters.instance_id);
        }
        if (this.currentFilters.db_type) {
            params.append('db_type', this.currentFilters.db_type);
        }
        
        const periodType = this.currentFilters.period_type || 'daily';
        params.append('period_type', periodType);
        
        const { startDate, endDate } = this.getChangeChartDateRange(periodType);
        if (startDate) {
            params.append('start_date', startDate);
        }
        if (endDate) {
            params.append('end_date', endDate);
        }
        
        params.append('get_all', 'true');
        return params;
    }
    
    /**
     * 构建容量变化百分比图表的筛选参数
     */
    buildChangePercentChartParams() {
        const params = new URLSearchParams();
        
        if (this.currentFilters.instance_id) {
            params.append('instance_id', this.currentFilters.instance_id);
        }
        if (this.currentFilters.db_type) {
            params.append('db_type', this.currentFilters.db_type);
        }
        
        const periodType = this.currentFilters.period_type || 'daily';
        params.append('period_type', periodType);
        
        const { startDate, endDate } = this.getChangePercentChartDateRange(periodType);
        if (startDate) {
            params.append('start_date', startDate);
        }
        if (endDate) {
            params.append('end_date', endDate);
        }
        
        params.append('get_all', 'true');
        return params;
    }
    
    /**
     * 获取容量变化图表的时间范围
     */
    getChangeChartDateRange(periodType) {
        if (this.changeFilters.override) {
            return {
                startDate: this.changeFilters.start_date,
                endDate: this.changeFilters.end_date
            };
        }
        
        let startDate = this.currentFilters.start_date || null;
        let endDate = this.currentFilters.end_date || null;
        
        if (!startDate || !endDate) {
            const computedRange = this.calculateDateRange(
                periodType,
                this.changeStatisticsPeriod,
                { respectExistingStart: false, respectExistingEnd: false }
            );
            if (!startDate) {
                startDate = computedRange.startDate;
            }
            if (!endDate) {
                endDate = computedRange.endDate;
            }
        }
        
        this.changeFilters.start_date = startDate;
        this.changeFilters.end_date = endDate;
        this.changeFilters.period_type = periodType;
        
        return { startDate, endDate };
    }
    
    /**
     * 获取容量变化百分比图表的时间范围
     */
    getChangePercentChartDateRange(periodType) {
        if (this.changePercentFilters.override) {
            return {
                startDate: this.changePercentFilters.start_date,
                endDate: this.changePercentFilters.end_date
            };
        }
        
        let startDate = this.currentFilters.start_date || null;
        let endDate = this.currentFilters.end_date || null;
        
        if (!startDate || !endDate) {
            const computedRange = this.calculateDateRange(
                periodType,
                this.changePercentStatisticsPeriod,
                { respectExistingStart: false, respectExistingEnd: false }
            );
            if (!startDate) {
                startDate = computedRange.startDate;
            }
            if (!endDate) {
                endDate = computedRange.endDate;
            }
        }
        
        this.changePercentFilters.start_date = startDate;
        this.changePercentFilters.end_date = endDate;
        this.changePercentFilters.period_type = periodType;
        
        return { startDate, endDate };
    }
    
    /**
     * 按周期类型计算时间范围
     */
    calculateDateRange(periodType, periodsCount = this.currentStatisticsPeriod || 1, options = {}) {
        const { respectExistingStart = false, respectExistingEnd = false } = options;
        const normalizedPeriodType = periodType || 'daily';
        const hasStart = Boolean(this.currentFilters.start_date) && respectExistingStart;
        const hasEnd = Boolean(this.currentFilters.end_date) && respectExistingEnd;
        const today = new Date();
        const endDate = hasEnd ? new Date(this.currentFilters.end_date) : today;
        const startDate = hasStart ? new Date(this.currentFilters.start_date) : new Date(endDate);
        const periods = Math.max(1, periodsCount || 1);
        
        if (!hasStart) {
            switch (normalizedPeriodType) {
                case 'weekly':
                    startDate.setDate(endDate.getDate() - periods * 7);
                    break;
                case 'monthly':
                    startDate.setMonth(endDate.getMonth() - periods);
                    break;
                case 'quarterly':
                    startDate.setMonth(endDate.getMonth() - periods * 3);
                    break;
                default:
                    startDate.setDate(endDate.getDate() - periods);
                    break;
            }
        }
        
        return {
            startDate: this.formatDateOnly(startDate),
            endDate: this.formatDateOnly(endDate)
        };
    }

    /**
     * 更新容量变化图的独立时间范围
     */
    updateChangeChartOverrideRange() {
        const periodType = this.currentFilters.period_type || 'daily';
        const range = this.calculateDateRange(periodType, this.changeStatisticsPeriod, {
            respectExistingStart: false,
            respectExistingEnd: false
        });
        this.changeFilters.start_date = range.startDate;
        this.changeFilters.end_date = range.endDate;
        this.changeFilters.override = true;
        this.changeFilters.period_type = periodType;
    }
    
    /**
     * 更新容量变化百分比图的独立时间范围
     */
    updateChangePercentChartOverrideRange() {
        const periodType = this.currentFilters.period_type || 'daily';
        const range = this.calculateDateRange(periodType, this.changePercentStatisticsPeriod, {
            respectExistingStart: false,
            respectExistingEnd: false
        });
        this.changePercentFilters.start_date = range.startDate;
        this.changePercentFilters.end_date = range.endDate;
        this.changePercentFilters.override = true;
        this.changePercentFilters.period_type = periodType;
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
     * 显示容量变化图表加载状态
     */
    showChangeChartLoading() {
        $('#changeChartLoading').removeClass('d-none');
    }
    
    /**
     * 隐藏容量变化图表加载状态
     */
    hideChangeChartLoading() {
        $('#changeChartLoading').addClass('d-none');
    }
    
    /**
     * 显示容量变化百分比图表加载状态
     */
    showChangePercentChartLoading() {
        $('#changePercentChartLoading').removeClass('d-none');
    }
    
    /**
     * 隐藏容量变化百分比图表加载状态
     */
    hideChangePercentChartLoading() {
        $('#changePercentChartLoading').addClass('d-none');
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
     * 同步UI状态
     * 确保UI控件状态与内部状态一致
     */
    syncUIState() {
        // 同步图表类型选择器
        $(`input[name="chartType"][value="${this.currentChartType}"]`).prop('checked', true);
        
        // 同步TOP选择器
        $(`input[name="topSelector"][value="${this.currentTopCount}"]`).prop('checked', true);
        
        // 同步统计周期选择器
        $(`input[name="statisticsPeriod"][value="${this.currentStatisticsPeriod}"]`).prop('checked', true);
        
        // 同步容量变化图表类型
        $(`input[name="changeChartType"][value="${this.changeChartType}"]`).prop('checked', true);
        
        // 同步容量变化TOP选择器
        $(`input[name="changeTopSelector"][value="${this.changeTopCount}"]`).prop('checked', true);
        
        // 同步容量变化统计周期选择器
        $(`input[name="changeStatisticsPeriod"][value="${this.changeStatisticsPeriod}"]`).prop('checked', true);
        
        // 同步容量变化百分比图表类型
        $(`input[name="changePercentChartType"][value="${this.changePercentChartType}"]`).prop('checked', true);
        
        // 同步容量变化百分比TOP选择器
        $(`input[name="changePercentTopSelector"][value="${this.changePercentTopCount}"]`).prop('checked', true);
        
        // 同步容量变化百分比统计周期选择器
        $(`input[name="changePercentStatisticsPeriod"][value="${this.changePercentStatisticsPeriod}"]`).prop('checked', true);
        
        console.log('UI状态已同步:', {
            chartType: this.currentChartType,
            topCount: this.currentTopCount,
            statisticsPeriod: this.currentStatisticsPeriod,
            changeChartType: this.changeChartType,
            changeTopCount: this.changeTopCount,
            changeStatisticsPeriod: this.changeStatisticsPeriod,
            changePercentChartType: this.changePercentChartType,
            changePercentTopCount: this.changePercentTopCount,
            changePercentStatisticsPeriod: this.changePercentStatisticsPeriod
        });
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
     * 将HEX颜色转换为包含透明度的RGBA
     */
    colorWithAlpha(hexColor, alpha = 1) {
        const normalized = hexColor.startsWith('#') ? hexColor.slice(1) : hexColor;
        if (normalized.length !== 6) {
            return `rgba(0, 0, 0, ${alpha})`;
        }
        const r = parseInt(normalized.slice(0, 2), 16);
        const g = parseInt(normalized.slice(2, 4), 16);
        const b = parseInt(normalized.slice(4, 6), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    }
    
    /**
     * 格式化日期（仅日期部分）
     */
    formatDateOnly(date) {
        const target = date instanceof Date ? date : new Date(date);
        const year = target.getFullYear();
        const month = String(target.getMonth() + 1).padStart(2, '0');
        const day = String(target.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }
    
    /**
     * 格式化日期
     */
    formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        // 后端已经返回东八区时间，前端直接格式化，不进行时区转换
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
    }
    
    /**
     * 获取CSRF令牌 - 使用全局函数
     */
    getCSRFToken() {
        return window.getCSRFToken();
    }

    // 原来的实现（已废弃）
    _getCSRFTokenOld() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }
}
