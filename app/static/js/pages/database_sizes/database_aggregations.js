/**
 * 数据库容量统计页面脚本
 * 基于 jQuery 3.7.1 和 Chart.js 4.4.0
 */

class DatabaseAggregationsManager {
    constructor() {
        this.chart = null;
        this.changeChart = null;
        this.currentData = [];
        this.changeChartData = [];
        this.currentChartType = 'line';
        this.currentTopCount = 5;
        this.currentStatisticsPeriod = 7;
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
        this.databaseLabelMap = {};
        this.databaseIdMap = new Map();
        this.currentFilters = {
            instance_id: null,
            db_type: null,
            database_id: null,
            database_name: null,
            period_type: 'daily',
            start_date: null,
            end_date: null
        };
        
        this.init();
    }
    
    init() {
        console.log('初始化数据库统计管理器');
        this.initializeCurrentFilters();
        this.bindEvents();
        this.initializeFilterOptions();
        this.ensureDatabaseTypesOptions();
        this.updateTimeRangeFromPeriod();
        this.syncUIState();
        this.loadSummaryData();
        this.loadChartData();
        this.loadChangeChartData();
        this.loadChangePercentChartData();
    }
    
    initializeCurrentFilters() {
        const dbTypeValue = $('#db_type').val();
        const instanceValue = $('#instance').val();
        const databaseSelect = $('#database');
        const initialDatabaseValue = databaseSelect.data('initialValue');
        const databaseValue = (initialDatabaseValue !== undefined && initialDatabaseValue !== null && String(initialDatabaseValue).length > 0)
            ? String(initialDatabaseValue)
            : databaseSelect.val();
        this.currentFilters.db_type = dbTypeValue ? dbTypeValue.toLowerCase() : null;
        this.currentFilters.instance_id = instanceValue || null;
        this.currentFilters.database_id = databaseValue || null;
        let databaseName = null;
        if (databaseValue) {
            databaseName = this.databaseIdMap.get(String(databaseValue)) || null;
            if (!databaseName) {
                const selectedOption = databaseSelect.find('option:selected');
                if (selectedOption.length) {
                    const text = selectedOption.text().trim();
                    databaseName = text || null;
                }
            }
        }
        this.currentFilters.database_name = databaseName;
        this.currentFilters.period_type = $('#period_type').val() || 'daily';
        this.currentFilters.start_date = $('#start_date').val() || null;
        this.currentFilters.end_date = $('#end_date').val() || null;
        if (instanceValue) {
            $('#instance').data('selected', instanceValue);
        }
        if (databaseValue) {
            databaseSelect.data('selected', databaseValue);
        }
    }
    
    bindEvents() {
        $('#refreshData').on('click', () => {
            this.refreshAllData();
        });
        
        $('#calculateAggregations').on('click', () => {
            this.calculateAggregations();
        });
        
        $('input[name="chartType"]').on('change', (e) => {
            this.currentChartType = e.target.value;
            this.renderChart(this.currentData);
        });
        
        $('input[name="topSelector"]').on('change', (e) => {
            this.currentTopCount = parseInt(e.target.value, 10);
            this.renderChart(this.currentData);
        });
        
        $('input[name="statisticsPeriod"]').on('change', (e) => {
            this.currentStatisticsPeriod = parseInt(e.target.value, 10);
            this.updateTimeRangeFromPeriod();
            this.loadSummaryData();
            this.loadChartData();
            this.loadChangeChartData();
            this.loadChangePercentChartData();
        });
        
        $('#period_type').on('change', (e) => {
            this.currentFilters.period_type = e.target.value;
            this.updateTimeRangeFromPeriod();
            if (this.changeFilters.override) {
                this.updateChangeChartOverrideRange();
            }
            if (this.changePercentFilters.override) {
                this.updateChangePercentChartOverrideRange();
            }
            this.loadSummaryData();
            this.loadChartData();
            this.loadChangeChartData();
            this.loadChangePercentChartData();
        });

        $('#database').on('change', () => {
            $('#database').data('initialValue', '');
            this.applyFilters();
        });

        $('input[name="changeChartType"]').on('change', (e) => {
            this.changeChartType = e.target.value;
            this.renderChangeChart(this.changeChartData);
        });
        
        $('input[name="changeTopSelector"]').on('change', (e) => {
            this.changeTopCount = parseInt(e.target.value, 10);
            this.renderChangeChart(this.changeChartData);
        });
        
        $('input[name="changeStatisticsPeriod"]').on('change', (e) => {
            this.changeStatisticsPeriod = parseInt(e.target.value, 10);
            this.updateChangeChartOverrideRange();
            this.loadChangeChartData();
        });
        
        $('input[name="changePercentChartType"]').on('change', (e) => {
            this.changePercentChartType = e.target.value;
            this.renderChangePercentChart(this.changePercentChartData);
        });
        
        $('input[name="changePercentTopSelector"]').on('change', (e) => {
            this.changePercentTopCount = parseInt(e.target.value, 10);
            this.renderChangePercentChart(this.changePercentChartData);
        });
        
        $('input[name="changePercentStatisticsPeriod"]').on('change', (e) => {
            this.changePercentStatisticsPeriod = parseInt(e.target.value, 10);
            this.updateChangePercentChartOverrideRange();
            this.loadChangePercentChartData();
        });
        
        $('#searchButton, #applyFilters').on('click', () => {
            this.applyFilters();
        });
        
        $('#resetButton').on('click', () => {
            this.resetFilters();
        });
        
        $('#db_type').on('change', async (e) => {
            const dbType = e.target.value;
            await this.updateInstanceOptions(dbType);
            this.updateFilters();
            this.loadSummaryData();
            this.loadChartData();
            this.loadChangeChartData();
            this.loadChangePercentChartData();
        });
        
        $('#instance').on('change', async (e) => {
            const instanceId = e.target.value;
            await this.updateDatabaseOptions(instanceId);
            this.updateFilters();
            this.loadSummaryData();
            this.loadChartData();
            this.loadChangeChartData();
            this.loadChangePercentChartData();
        });
        
    }
    
    initializeFilterOptions() {
        const initialDbType = $('#db_type').val();
        const instanceSelect = $('#instance');
        const databaseSelect = $('#database');
        
        if (initialDbType) {
            this.updateInstanceOptions(initialDbType, { preserveInstance: true }).then(() => {
                const initialInstance = this.currentFilters.instance_id || instanceSelect.data('selected');
                if (initialInstance) {
                    instanceSelect.val(initialInstance);
                    this.updateDatabaseOptions(initialInstance, { preserveDatabase: true }).then(() => {
                        const initialDatabase = this.currentFilters.database_id || databaseSelect.data('selected') || databaseSelect.data('initialValue');
                        if (initialDatabase) {
                            databaseSelect.val(initialDatabase);
                        }
                    });
                }
            });
        } else {
            instanceSelect.empty();
            instanceSelect.append('<option value="">请先选择数据库类型</option>');
            instanceSelect.prop('disabled', true);
            databaseSelect.empty();
            databaseSelect.append('<option value="">请先选择实例</option>');
            databaseSelect.prop('disabled', true);
        }
    }
    
    async ensureDatabaseTypesOptions() {
        const select = $('#db_type');
        if (!select.length) {
            return;
        }
        const optionCount = select.find('option').length;
        if (optionCount > 1) {
            return;
        }
        try {
            const response = await fetch('/database_types/api/active');
            const result = await response.json();
            if (response.ok && result.success) {
                const selectedType = this.currentFilters.db_type ? this.currentFilters.db_type.toLowerCase() : '';
                select.empty();
                select.append('<option value="">全部类型</option>');
                (result.data || []).forEach(item => {
                    const value = (item.name || '').toLowerCase();
                    const display = item.display_name || item.name || value;
                    const option = document.createElement('option');
                    option.value = value;
                    option.textContent = display;
                    if (selectedType && selectedType === value) {
                        option.selected = true;
                    }
                    select.append(option);
                });
            }
        } catch (error) {
            console.error('加载数据库类型失败:', error);
        }
    }
    
    // 数据库类型选项由服务端模板渲染，此处无需额外加载
    
    async updateInstanceOptions(dbType, options = {}) {
        const { preserveInstance = false } = options;
        const instanceSelect = $('#instance');
        const databaseSelect = $('#database');
        const normalizedDbType = dbType ? dbType.toLowerCase() : null;
        
        const storedInstance = preserveInstance
            ? (this.currentFilters.instance_id || instanceSelect.data('selected') || '')
            : '';
        
        if (!preserveInstance) {
            this.currentFilters.instance_id = null;
            this.currentFilters.database_id = null;
            this.currentFilters.database_name = null;
            instanceSelect.data('selected', '');
            databaseSelect.data('selected', '');
            databaseSelect.data('initialValue', '');
            this.databaseIdMap.clear();
        }

        databaseSelect.empty();
        databaseSelect.append('<option value="">请先选择实例</option>');
        databaseSelect.prop('disabled', true);
        
        try {
            instanceSelect.prop('disabled', false);
            let url = '/database_stats/api/instance-options';
            if (normalizedDbType) {
                url += `?db_type=${encodeURIComponent(normalizedDbType)}`;
            }
            const response = await fetch(url);
            const data = await response.json();
            
            if (response.ok && data.success) {
                instanceSelect.empty();
                instanceSelect.append('<option value="">所有实例</option>');
                let matchedInstance = '';
                data.instances.forEach(instance => {
                    const option = document.createElement('option');
                    option.value = String(instance.id);
                    option.textContent = `${instance.name} (${instance.db_type})`;
                    if (storedInstance && String(storedInstance) === String(instance.id)) {
                        option.selected = true;
                        matchedInstance = String(instance.id);
                    }
                    instanceSelect.append(option);
                });
                
                if (matchedInstance) {
                    instanceSelect.val(matchedInstance);
                    this.currentFilters.instance_id = matchedInstance;
                    instanceSelect.data('selected', matchedInstance);
                } else if (preserveInstance && storedInstance) {
                    this.currentFilters.instance_id = null;
                    instanceSelect.data('selected', '');
                    instanceSelect.val('');
                }
            } else {
                instanceSelect.empty();
                instanceSelect.append('<option value="">加载失败</option>');
            }
        } catch (error) {
            console.error('加载实例列表时出错:', error);
            instanceSelect.empty();
            instanceSelect.append('<option value="">加载失败</option>');
        }
    }
    
    async updateDatabaseOptions(instanceId, options = {}) {
        const { preserveDatabase = false } = options;
        const databaseSelect = $('#database');
        
        if (!instanceId) {
            databaseSelect.empty();
            databaseSelect.append('<option value="">所有数据库</option>');
            databaseSelect.prop('disabled', true);
            if (!preserveDatabase) {
                this.currentFilters.database_id = null;
                this.currentFilters.database_name = null;
                databaseSelect.data('selected', '');
                databaseSelect.data('initialValue', '');
                this.databaseIdMap.clear();
            }
            return;
        }

        const initialAttrValue = databaseSelect.data('initialValue');
        const storedDatabase = preserveDatabase
            ? (this.currentFilters.database_id || databaseSelect.data('selected') || initialAttrValue || '')
            : '';

        if (!preserveDatabase) {
            this.currentFilters.database_id = null;
            this.currentFilters.database_name = null;
            databaseSelect.data('selected', '');
        }

        try {
            databaseSelect.prop('disabled', false);
            const params = new URLSearchParams();
            params.append('limit', '1000');
            const response = await fetch(`/database_stats/api/instances/${encodeURIComponent(instanceId)}/databases?${params.toString()}`);
            const data = await response.json();

            if (response.ok && data.success !== false) {
                const list = data.data || [];
                this.databaseIdMap.clear();
                list.forEach(db => {
                    if (db && db.database_name) {
                        this.databaseIdMap.set(String(db.id), db.database_name);
                    }
                });
                const databases = list
                    .filter(item => item && item.database_name)
                    .sort((a, b) => a.database_name.localeCompare(b.database_name));
                databaseSelect.empty();
                databaseSelect.append('<option value="">所有数据库</option>');
                let matchedDatabase = '';
                databases.forEach(db => {
                    const option = document.createElement('option');
                    option.value = String(db.id);
                    option.textContent = db.database_name;
                    if (storedDatabase && String(storedDatabase) === String(db.id)) {
                        option.selected = true;
                        matchedDatabase = String(db.id);
                    }
                    databaseSelect.append(option);
                });

                if (matchedDatabase) {
                    databaseSelect.val(matchedDatabase);
                    this.currentFilters.database_id = matchedDatabase;
                    this.currentFilters.database_name = this.databaseIdMap.get(matchedDatabase) || null;
                    databaseSelect.data('selected', matchedDatabase);
                    databaseSelect.data('initialValue', '');
                } else if (preserveDatabase && storedDatabase) {
                    this.currentFilters.database_id = null;
                    this.currentFilters.database_name = null;
                    databaseSelect.data('selected', '');
                    databaseSelect.val('');
                    databaseSelect.data('initialValue', '');
                }
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
    
    updateFilters() {
        const dbTypeValue = $('#db_type').val();
        const instanceValue = $('#instance').val();
        const databaseSelect = $('#database');
        const initialDatabaseValue = databaseSelect.data('initialValue');
        const databaseValue = (initialDatabaseValue !== undefined && initialDatabaseValue !== null && String(initialDatabaseValue).length > 0)
            ? String(initialDatabaseValue)
            : databaseSelect.val();
        this.currentFilters.db_type = dbTypeValue ? dbTypeValue.toLowerCase() : null;
        this.currentFilters.instance_id = instanceValue || null;
        this.currentFilters.database_id = databaseValue || null;
        this.currentFilters.database_name = databaseValue ? this.databaseIdMap.get(String(databaseValue)) || null : null;
        $('#instance').data('selected', this.currentFilters.instance_id || '');
        databaseSelect.data('selected', this.currentFilters.database_id ?? '');
        if (initialDatabaseValue !== undefined) {
            databaseSelect.data('initialValue', '');
        }
        this.currentFilters.period_type = $('#period_type').val();
        this.currentFilters.start_date = $('#start_date').val();
        this.currentFilters.end_date = $('#end_date').val();
    }
    
    applyFilters() {
        this.updateFilters();
        this.changeFilters.start_date = this.currentFilters.start_date || null;
        this.changeFilters.end_date = this.currentFilters.end_date || null;
        this.changeFilters.override = false;
        this.changeFilters.period_type = this.currentFilters.period_type || 'daily';
        this.loadSummaryData();
        this.loadChartData();
        this.loadChangeChartData();
        this.changePercentFilters.start_date = this.currentFilters.start_date || null;
        this.changePercentFilters.end_date = this.currentFilters.end_date || null;
        this.changePercentFilters.override = false;
        this.changePercentFilters.period_type = this.currentFilters.period_type || 'daily';
        this.loadChangePercentChartData();
        this.syncUIState();
        $('#database').data('initialValue', '');
    }
    
    resetFilters() {
        $('#db_type').val('');
        $('#instance').val('');
        $('#database').val('');
        $('#period_type').val('daily');
        $('#start_date').val('');
        $('#end_date').val('');
        
        this.currentFilters = {
            instance_id: null,
            db_type: null,
            database_id: null,
            database_name: null,
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
        this.databaseIdMap.clear();
        
        this.initializeFilterOptions();
        this.updateTimeRangeFromPeriod();
        this.loadSummaryData();
        this.loadChartData();
        this.loadChangeChartData();
        this.loadChangePercentChartData();
    }
    
    async refreshAllData() {
        this.showLoading();
        
        try {
            await Promise.all([
                this.loadSummaryData(),
                this.loadChartData(),
                this.loadChangeChartData(),
                this.loadChangePercentChartData()
            ]);
            this.syncUIState();
            this.showSuccess('数据刷新成功');
        } catch (error) {
            console.error('刷新数据失败:', error);
            this.showError('刷新数据失败: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    async loadSummaryData() {
        try {
            const params = this.buildFilterParams();
            const response = await fetch(`/instance_stats/api/databases/aggregations/summary?api=true&${params.toString()}`);
            const data = await response.json();
            
            if (response.ok) {
                const summaryData = data.data || data;
                this.updateSummaryCards(summaryData);
            } else {
                console.error('加载汇总数据失败:', data.error);
            }
        } catch (error) {
            console.error('加载汇总数据时出错:', error);
        }
    }
    
    updateSummaryCards(summaryData) {
        $('#totalInstances').text(summaryData.total_instances || 0);
        $('#totalDatabases').text(summaryData.total_databases || 0);
        $('#averageSize').text(this.formatSizeFromMB(summaryData.avg_size_mb || 0));
        $('#maxSize').text(this.formatSizeFromMB(summaryData.max_size_mb || 0));
    }
    
    async loadChartData() {
        try {
            this.showChartLoading();
            const params = this.buildFilterParams();
            params.append('chart_mode', 'database');
            params.append('get_all', 'true');
            console.log('加载图表数据参数:', params.toString());
            const response = await fetch(`/instance_stats/api/databases/aggregations?api=true&${params.toString()}`);
            const data = await response.json();
            
            if (response.ok) {
                this.databaseLabelMap = {};
                this.currentData = data.data || [];
                this.renderChart(this.currentData);
                this.syncUIState();
            } else {
                console.error('加载图表数据失败:', data.error);
                this.showError('加载图表数据失败: ' + data.error);
            }
        } catch (error) {
            console.error('加载图表数据时出错:', error);
            this.showError('加载图表数据时出错: ' + error.message);
        } finally {
            this.hideChartLoading();
        }
    }
    
    async loadChangeChartData() {
        try {
            this.showChangeChartLoading();
            const params = this.buildChangeChartParams();
            params.append('chart_mode', 'database');
            params.append('get_all', 'true');
            console.log('加载容量变化参数:', params.toString());
            const response = await fetch(`/instance_stats/api/databases/aggregations?api=true&${params.toString()}`);
            const data = await response.json();
            
            if (response.ok) {
                this.changeChartData = data.data || [];
                this.renderChangeChart(this.changeChartData);
            } else {
                console.error('加载容量变化数据失败:', data.error);
                this.showError('加载容量变化数据失败: ' + data.error);
            }
        } catch (error) {
            console.error('加载容量变化数据时出错:', error);
            this.showError('加载容量变化数据时出错: ' + error.message);
        } finally {
            this.hideChangeChartLoading();
        }
    }

    async loadChangePercentChartData() {
        try {
            this.showChangePercentChartLoading();
            const params = this.buildChangePercentChartParams();
            params.append('chart_mode', 'database');
            params.append('get_all', 'true');
            console.log('加载容量变化百分比参数:', params.toString());
            const response = await fetch(`/instance_stats/api/databases/aggregations?api=true&${params.toString()}`);
            const data = await response.json();

            if (response.ok) {
                this.changePercentChartData = data.data || [];
                this.renderChangePercentChart(this.changePercentChartData);
            } else {
                console.error('加载容量变化百分比数据失败:', data.error);
                this.showError('加载容量变化百分比数据失败: ' + data.error);
            }
        } catch (error) {
            console.error('加载容量变化百分比数据时出错:', error);
            this.showError('加载容量变化百分比数据时出错: ' + error.message);
        } finally {
            this.hideChangePercentChartLoading();
        }
    }
    
    renderChart(data) {
        const canvas = document.getElementById('databaseChart');
        if (!canvas) {
            return;
        }
        
        const ctx = canvas.getContext('2d');
        
        if (this.chart) {
            this.chart.destroy();
        }
        
        if (!data || data.length === 0) {
            this.showEmptyChart();
            return;
        }
        
        const groupedData = this.groupSizeDataByDate(data);
        const chartData = this.prepareSizeChartData(groupedData);
        
        this.chart = new Chart(ctx, {
            type: this.currentChartType,
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: '容量统计趋势图'
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

    renderChangePercentChart(data) {
        const canvas = document.getElementById('databaseChangePercentChart');
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
    
    renderChangeChart(data) {
        const canvas = document.getElementById('databaseChangeChart');
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
                            color: (context) => (context.tick && context.tick.value === 0 ? '#212529' : 'rgba(0, 0, 0, 0.08)'),
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
    
    groupSizeDataByDate(data) {
        const grouped = {};
        data.forEach(item => {
            const date = item.period_start;
            if (!date) {
                return;
            }
            if (!grouped[date]) {
                grouped[date] = {};
            }
            const dbName = item.database_name || '未知数据库';
            const instanceName = item.instance?.name || '未知实例';
            const instanceId = item.instance?.id || `unknown-${instanceName}`;
            const key = `${instanceId}::${dbName}`;
            this.databaseLabelMap[key] = `${dbName} (${instanceName})`;
            const sizeValue = Number(item.avg_size_mb);
            grouped[date][key] = Number.isFinite(sizeValue) ? sizeValue : null;
        });
        return grouped;
    }

    groupChangePercentDataByDate(data) {
        const grouped = {};
        data.forEach(item => {
            const date = item.period_start;
            if (!date) {
                return;
            }
            if (!grouped[date]) {
                grouped[date] = {};
            }
            const dbName = item.database_name || '未知数据库';
            const instanceName = item.instance?.name || '未知实例';
            const instanceId = item.instance?.id || `unknown-${instanceName}`;
            const key = `${instanceId}::${dbName}`;
            this.databaseLabelMap[key] = `${dbName} (${instanceName})`;
            const changePercent = Number(item.size_change_percent ?? 0);
            grouped[date][key] = Number.isNaN(changePercent) ? 0 : changePercent;
        });
        return grouped;
    }

    groupChangeDataByDate(data) {
        const grouped = {};
        data.forEach(item => {
            const date = item.period_start;
            if (!date) {
                return;
            }
            if (!grouped[date]) {
                grouped[date] = {};
            }
            const dbName = item.database_name || '未知数据库';
            const instanceName = item.instance?.name || '未知实例';
            const instanceId = item.instance?.id || `unknown-${instanceName}`;
            const key = `${instanceId}::${dbName}`;
            this.databaseLabelMap[key] = `${dbName} (${instanceName})`;
            const changeValue = Number(item.size_change_mb ?? 0);
            grouped[date][key] = Number.isNaN(changeValue) ? 0 : changeValue;
        });
        return grouped;
    }

    prepareSizeChartData(groupedData) {
        const labels = Object.keys(groupedData).sort();
        const datasets = [];
        const colors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
            '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF',
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
            '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
            '#BB8FCE', '#85C1E9', '#F8C471', '#82E0AA'
        ];
        
        const databaseMaxSizes = new Map();
        Object.values(groupedData).forEach(dateData => {
            Object.entries(dateData).forEach(([key, size]) => {
                const numericSize = Number(size);
                if (!Number.isFinite(numericSize)) {
                    return;
                }
                const existingMax = databaseMaxSizes.get(key) || 0;
                databaseMaxSizes.set(key, Math.max(existingMax, numericSize));
            });
        });

        const sortedDatabases = Array.from(databaseMaxSizes.entries())
            .sort((a, b) => b[1] - a[1])
            .slice(0, this.currentTopCount)
            .map(([name]) => name);

        let colorIndex = 0;
        sortedDatabases.forEach(key => {
            let lastKnownValue = null;
            const data = labels.map(date => {
                const dateData = groupedData[date] || {};
                const mbValue = dateData[key];
                if (mbValue === undefined || mbValue === null) {
                    return lastKnownValue !== null ? lastKnownValue / 1024 : null;
                }
                lastKnownValue = mbValue;
                return mbValue / 1024;
            });
            
            datasets.push({
                label: this.databaseLabelMap[key] || key,
                data,
                borderColor: colors[colorIndex % colors.length],
                backgroundColor: this.currentChartType === 'line' ? this.colorWithAlpha(colors[colorIndex % colors.length], 0.1) : this.colorWithAlpha(colors[colorIndex % colors.length], 0.65),
                fill: this.currentChartType !== 'line',
                tension: this.currentChartType === 'line' ? 0.1 : 0
            });
            colorIndex++;
        });
        
        return { labels, datasets };
    }

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

        const databaseMaxPercentChanges = new Map();
        Object.values(groupedData).forEach(dateData => {
            Object.entries(dateData).forEach(([key, changePercent]) => {
                const absValue = Math.abs(changePercent || 0);
                const existingMax = databaseMaxPercentChanges.get(key) || 0;
                databaseMaxPercentChanges.set(key, Math.max(existingMax, absValue));
            });
        });

        const sortedDatabases = Array.from(databaseMaxPercentChanges.entries())
            .sort((a, b) => b[1] - a[1])
            .slice(0, this.changePercentTopCount)
            .map(([name]) => name);

        let colorIndex = 0;
        sortedDatabases.forEach(key => {
            const data = labels.map(date => {
                const rawValue = groupedData[date][key];
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
                label: this.databaseLabelMap[key] || key,
                data,
                borderColor: baseColor,
                backgroundColor: (ctx) => {
                    const value = ctx.parsed?.y ?? 0;
                    if (this.changePercentChartType === 'line') {
                        return this.colorWithAlpha(baseColor, 0.1);
                    }
                    return value >= 0
                        ? this.colorWithAlpha(baseColor, 0.65)
                        : this.colorWithAlpha(baseColor, 0.35);
                },
                fill: this.changePercentChartType !== 'line',
                tension: this.changePercentChartType === 'line' ? 0.3 : 0
            };

            if (this.changePercentChartType === 'line') {
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
                    return value >= 0 ? this.colorWithAlpha(baseColor, 0.85) : '#ffffff';
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
        
        const databaseMaxChanges = new Map();
        Object.values(groupedData).forEach(dateData => {
            Object.entries(dateData).forEach(([key, changeValue]) => {
                const absValue = Math.abs(changeValue || 0);
                const existingMax = databaseMaxChanges.get(key) || 0;
                databaseMaxChanges.set(key, Math.max(existingMax, absValue));
            });
        });

        const sortedDatabases = Array.from(databaseMaxChanges.entries())
            .sort((a, b) => b[1] - a[1])
            .slice(0, this.changeTopCount)
            .map(([name]) => name);

        let colorIndex = 0;
        sortedDatabases.forEach(key => {
            const data = labels.map(date => {
                const rawValue = groupedData[date][key];
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
                label: this.databaseLabelMap[key] || key,
                data,
                borderColor: baseColor,
                backgroundColor: (ctx) => {
                    const value = ctx.parsed?.y ?? 0;
                    if (this.changeChartType === 'line') {
                        return this.colorWithAlpha(baseColor, 0.1);
                    }
                    return value >= 0
                        ? this.colorWithAlpha(baseColor, 0.65)
                        : this.colorWithAlpha(baseColor, 0.35);
                },
                fill: this.changeChartType !== 'line',
                tension: this.changeChartType === 'line' ? 0.3 : 0
            };
            
            if (this.changeChartType === 'line') {
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
                    return value >= 0 ? this.colorWithAlpha(baseColor, 0.85) : '#ffffff';
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
    
    buildFilterParams() {
        const params = new URLSearchParams();
        if (this.currentFilters.instance_id) {
            params.append('instance_id', this.currentFilters.instance_id);
        }
        if (this.currentFilters.db_type) {
            params.append('db_type', this.currentFilters.db_type);
        }
        if (this.currentFilters.database_id) {
            params.append('database_id', this.currentFilters.database_id);
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

    buildChangeChartParams() {
        const params = new URLSearchParams();
        if (this.currentFilters.instance_id) {
            params.append('instance_id', this.currentFilters.instance_id);
        }
        if (this.currentFilters.db_type) {
            params.append('db_type', this.currentFilters.db_type);
        }
        if (this.currentFilters.database_id) {
            params.append('database_id', this.currentFilters.database_id);
        }
        if (this.currentFilters.database_name) {
            params.append('database_name', this.currentFilters.database_name);
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
        return params;
    }

    buildChangePercentChartParams() {
        const params = new URLSearchParams();
        if (this.currentFilters.instance_id) {
            params.append('instance_id', this.currentFilters.instance_id);
        }
        if (this.currentFilters.db_type) {
            params.append('db_type', this.currentFilters.db_type);
        }
        if (this.currentFilters.database_id) {
            params.append('database_id', this.currentFilters.database_id);
        }
        if (this.currentFilters.database_name) {
            params.append('database_name', this.currentFilters.database_name);
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
        return params;
    }

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
            const computedRange = this.calculateDateRange(periodType, this.changeStatisticsPeriod);
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
            const computedRange = this.calculateDateRange(periodType, this.changePercentStatisticsPeriod);
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

    calculateDateRange(periodType, periodsCount = this.currentStatisticsPeriod || 1) {
        const normalizedPeriod = periodType || 'daily';
        const endDate = new Date();
        const startDate = new Date(endDate);
        const periods = Math.max(1, periodsCount || 1);

        switch (normalizedPeriod) {
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
        }

        return {
            startDate: startDate.toISOString().split('T')[0],
            endDate: endDate.toISOString().split('T')[0]
        };
    }
    
    updateTimeRangeFromPeriod() {
        const periodType = this.currentFilters.period_type || 'daily';
        const range = this.calculateDateRange(periodType, this.currentStatisticsPeriod);
        this.currentFilters.start_date = range.startDate;
        this.currentFilters.end_date = range.endDate;
        if (!this.changeFilters.override) {
            this.changeFilters.start_date = this.currentFilters.start_date;
            this.changeFilters.end_date = this.currentFilters.end_date;
            this.changeFilters.period_type = periodType;
        }
        if (!this.changePercentFilters.override) {
            this.changePercentFilters.start_date = this.currentFilters.start_date;
            this.changePercentFilters.end_date = this.currentFilters.end_date;
            this.changePercentFilters.period_type = periodType;
        }
    }

    updateChangeChartOverrideRange() {
        const periodType = this.currentFilters.period_type || 'daily';
        const range = this.calculateDateRange(periodType, this.changeStatisticsPeriod);
        this.changeFilters.start_date = range.startDate;
        this.changeFilters.end_date = range.endDate;
        this.changeFilters.override = true;
        this.changeFilters.period_type = periodType;
    }
    
    updateChangePercentChartOverrideRange() {
        const periodType = this.currentFilters.period_type || 'daily';
        const range = this.calculateDateRange(periodType, this.changePercentStatisticsPeriod);
        this.changePercentFilters.start_date = range.startDate;
        this.changePercentFilters.end_date = range.endDate;
        this.changePercentFilters.override = true;
        this.changePercentFilters.period_type = periodType;
    }
    
    showChartLoading() {
        $('#chartLoading').removeClass('d-none');
    }
    
    hideChartLoading() {
        $('#chartLoading').addClass('d-none');
    }
    
    showChangeChartLoading() {
        $('#changeChartLoading').removeClass('d-none');
    }
    
    hideChangeChartLoading() {
        $('#changeChartLoading').addClass('d-none');
    }

    showChangePercentChartLoading() {
        $('#changePercentChartLoading').removeClass('d-none');
    }

    hideChangePercentChartLoading() {
        $('#changePercentChartLoading').addClass('d-none');
    }
    
    showLoading() {}
    hideLoading() {}
    
    syncUIState() {
        $(`input[name="chartType"][value="${this.currentChartType}"]`).prop('checked', true);
        $(`input[name="topSelector"][value="${this.currentTopCount}"]`).prop('checked', true);
        $(`input[name="statisticsPeriod"][value="${this.currentStatisticsPeriod}"]`).prop('checked', true);
        
        const dbTypeValue = this.currentFilters.db_type || '';
        $('#db_type').val(dbTypeValue);
        
        const instanceValue = this.currentFilters.instance_id ? String(this.currentFilters.instance_id) : '';
        $('#instance').val(instanceValue);
        
        const databaseValue = this.currentFilters.database_id ? String(this.currentFilters.database_id) : '';
        $('#database').val(databaseValue);
        
        $(`input[name="changeChartType"][value="${this.changeChartType}"]`).prop('checked', true);
        $(`input[name="changeTopSelector"][value="${this.changeTopCount}"]`).prop('checked', true);
        $(`input[name="changeStatisticsPeriod"][value="${this.changeStatisticsPeriod}"]`).prop('checked', true);
        
        $(`input[name="changePercentChartType"][value="${this.changePercentChartType}"]`).prop('checked', true);
        $(`input[name="changePercentTopSelector"][value="${this.changePercentTopCount}"]`).prop('checked', true);
        $(`input[name="changePercentStatisticsPeriod"][value="${this.changePercentStatisticsPeriod}"]`).prop('checked', true);
    }
    
    showEmptyChart() {
        const canvas = document.getElementById('databaseChart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
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
                        text: '容量统计趋势图 - 暂无数据'
                    }
                }
            }
        });
    }
    
    showEmptyChangeChart() {
        const canvas = document.getElementById('databaseChangeChart');
        if (!canvas) return;
        
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
                    borderColor: '#dee2e6',
                    borderDash: this.changeChartType === 'line' ? [6, 4] : []
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
                }
            }
        });
    }
    
    showEmptyChangePercentChart() {
        const canvas = document.getElementById('databaseChangePercentChart');
        if (!canvas) return;

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
                    borderColor: '#dee2e6',
                    borderDash: this.changePercentChartType === 'line' ? [6, 4] : []
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
                }
            }
        });
    }
    
    async calculateAggregations() {
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
    
    showSuccess(message) {
        toastr.success(message);
    }
    
    showError(message) {
        toastr.error(message);
    }
    
    formatSizeFromMB(mb) {
        if (mb === 0) return '0 B';
        if (mb < 1024) return `${mb.toFixed(2)} MB`;
        if (mb < 1024 * 1024) return `${(mb / 1024).toFixed(2)} GB`;
        return `${(mb / (1024 * 1024)).toFixed(2)} TB`;
    }
    
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
    
    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }
}
