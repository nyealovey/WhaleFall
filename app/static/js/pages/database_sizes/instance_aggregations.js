/**
 * 实例统计页面脚本
 * 基于 jQuery 3.7.1 和 Chart.js 4.4.0
 */

class InstanceAggregationsManager {
    constructor() {
        this.chart = null;
        this.currentData = [];
        this.currentChartType = 'line';
        this.currentTopCount = 5; // 默认显示TOP5
        this.currentStatisticsPeriod = 7; // 默认7个周期
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
        this.bindEvents();
        this.initializeDatabaseFilter();
        this.updateTimeRangeFromPeriod(); // 初始化时间范围
        this.loadSummaryData();
        this.loadChartData();
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
        
        // 统计周期选择器切换
        $('input[name="statisticsPeriod"]').on('change', (e) => {
            this.currentStatisticsPeriod = parseInt(e.target.value);
            this.updateTimeRangeFromPeriod();
            this.loadChartData();
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
        
        // 实例变化时自动刷新
        $('#instance').on('change', () => {
            this.updateFilters();
            this.loadChartData();
        });
    }
    
    /**
     * 初始化数据库筛选器
     */
    initializeDatabaseFilter() {
        const instanceSelect = $('#instance');
        
        // 初始化实例筛选器
        instanceSelect.empty();
        instanceSelect.append('<option value="">请先选择数据库类型</option>');
        instanceSelect.prop('disabled', true);
    }
    
    /**
     * 根据选择的数据库类型更新实例选项
     */
    async updateInstanceOptions(dbType) {
        const instanceSelect = $('#instance');
        
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
    }
    
    /**
     * 重置筛选条件
     */
    resetFilters() {
        console.log('重置筛选条件');
        
        // 清空所有筛选器
        $('#instanceFilter').val('');
        $('#dbTypeFilter').val('');
        $('#periodTypeFilter').val('daily');
        $('#startDateFilter').val('');
        $('#endDateFilter').val('');
        
        // 重置筛选条件
        this.currentFilters = {
            instance_id: null,
            db_type: null,
            period_type: 'daily',
            start_date: null,
            end_date: null
        };
        
        // 重新加载数据
        this.loadSummaryData();
        this.loadChartData();
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
            const response = await fetch(`/aggregations/instance/summary?api=true&${params}`);
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
        // 从API响应中提取正确的数据
        const summaryData = data.data || data;
        $('#totalInstances').text(summaryData.total_instances || 0);
        $('#totalDatabases').text(summaryData.total_databases || 0);
        $('#averageSize').text(this.formatSizeFromMB(summaryData.avg_size_mb || 0));
        $('#maxSize').text(this.formatSizeFromMB(summaryData.max_size_mb || 0));
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
            const response = await fetch(`/aggregations/instance?api=true&${params}`);
            const data = await response.json();
            
            console.log('图表数据响应:', data);
            
            if (response.ok) {
                // 限制处理的数据量，防止前端崩溃
                const limitedData = data.data ? data.data.slice(0, 100) : [];
                this.currentData = limitedData;
                console.log('当前图表数据（限制100条）:', this.currentData.length);
                this.renderChart(limitedData);
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
            
            // 按实例分组，使用实例的总容量
            const instanceName = item.instance?.name || '未知实例';
            if (!grouped[date][instanceName]) {
                grouped[date][instanceName] = 0;
            }
            // 使用total_size_mb，表示实例的总容量（直接赋值，因为每个实例每天只有一条记录）
            grouped[date][instanceName] = item.total_size_mb || 0;
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
            // 将MB转换为GB用于图表显示
            const data = labels.map(date => {
                const mbValue = groupedData[date][instanceName] || 0;
                return mbValue / 1024; // 转换为GB
            });
            
            datasets.push({
                label: instanceName,
                data: data,
                borderColor: colors[colorIndex % colors.length],
                backgroundColor: colors[colorIndex % colors.length] + '20',
                fill: false,
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
     * 聚合计算
     */
    async calculateAggregations() {
        console.log('开始聚合计算');
        
        // 显示进度模态框
        $('#calculationModal').modal('show');
        
        try {
            const response = await fetch('/aggregations/aggregate-today', {
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
        const endDate = new Date();
        const startDate = new Date();
        
        // 根据当前统计周期类型计算开始日期
        const periodType = this.currentFilters.period_type || 'daily';
        
        switch (periodType) {
            case 'daily':
                startDate.setDate(endDate.getDate() - this.currentStatisticsPeriod);
                break;
            case 'weekly':
                startDate.setDate(endDate.getDate() - (this.currentStatisticsPeriod * 7));
                break;
            case 'monthly':
                startDate.setMonth(endDate.getMonth() - this.currentStatisticsPeriod);
                break;
            case 'quarterly':
                startDate.setMonth(endDate.getMonth() - (this.currentStatisticsPeriod * 3));
                break;
            default:
                startDate.setDate(endDate.getDate() - this.currentStatisticsPeriod);
        }
        
        // 更新筛选条件中的时间范围
        this.currentFilters.start_date = startDate.toISOString().split('T')[0];
        this.currentFilters.end_date = endDate.toISOString().split('T')[0];
        
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
     * 获取CSRF令牌
     */
    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }
}

