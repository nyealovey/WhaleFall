/**
 * 聚合数据图表管理器
 * 基于 Chart.js 4.4.0 和 jQuery 3.7.1
 */

const ColorTokens = window.ColorTokens;
if (!ColorTokens) {
    throw new Error('ColorTokens 未初始化');
}

const LodashUtils = window.LodashUtils;
if (!LodashUtils) {
    throw new Error('LodashUtils 未初始化');
}

const DOMHelpers = window.DOMHelpers;
if (!DOMHelpers) {
    throw new Error('DOMHelpers 未初始化');
}

const { selectOne, ready, from } = DOMHelpers;

/**
 * 分区聚合图表入口，负责初始化服务及管理器。
 *
 * @param {Window} [context=window] 自定义全局上下文，便于测试。
 * @returns {void}
 */
function mountAggregationsChart(context) {
const PartitionService = window.PartitionService;
if (!PartitionService) {
    throw new Error('PartitionService 未初始化');
}
const partitionService = new PartitionService(window.httpU);
const createPartitionStore = window.createPartitionStore;

/**
 * 将过滤条件序列化为查询参数。
 *
 * @param {Object} values 过滤条件对象。
 * @returns {URLSearchParams} 序列化结果。
 */
function buildChartQueryParams(values) {
    const params = new URLSearchParams();
    Object.entries(values || {}).forEach(([key, value]) => {
        if (value === undefined || value === null) {
            return;
        }
        if (Array.isArray(value)) {
            value.forEach((item) => {
                if (item !== undefined && item !== null) {
                    params.append(key, item);
                }
            });
        } else if (typeof value === 'string') {
            const trimmed = value.trim();
            if (trimmed !== '') {
                params.append(key, trimmed);
            }
        } else {
            params.append(key, value);
        }
    });
    return params;
}

/**
 * 负责监听 store、拉取数据并渲染 Chart.js。
 */
class AggregationsChartManager {
    constructor() {
        this.chart = null;
        this.currentData = [];
        this.currentChartType = 'line'; // 固定为折线图
        this.currentPeriodType = 'daily';
        this.partitionStore = window.PartitionStoreInstance || null;
        this.partitionStoreSubscriptions = [];
        this.ownsStore = false;
        this.handleMetricsUpdated = this.handleMetricsUpdated.bind(this);
        this.handleStoreLoading = this.handleStoreLoading.bind(this);
        this.handleStoreError = this.handleStoreError.bind(this);
        const typeColorIndex = {
            '数据库聚合': 0,
            '实例聚合': 1,
            '数据库统计': 2,
            '实例统计': 3,
        };

        // 为不同类型的聚合数据定义颜色和样式
        this.dataTypeStyles = Object.fromEntries(
            Object.entries({
                '数据库聚合': { borderDash: [], pointStyle: 'circle' },
                '实例聚合': { borderDash: [5, 5], pointStyle: 'rect' },
                '数据库统计': { borderDash: [10, 5], pointStyle: 'triangle' },
                '实例统计': { borderDash: [2, 2], pointStyle: 'star' },
            }).map(([name, style]) => {
                const color = ColorTokens.getChartColor(typeColorIndex[name] ?? 0);
                return [name, { ...style, color }];
            })
        );
        
        this.init();
    }
    
    init() {
        this.ensurePartitionStore();
        this.bindEvents();
        this.loadChartData();
        this.createLegend();
    }

    getLegendGradient(startIndex, endIndex, alpha = 0.7) {
        return `linear-gradient(90deg, ${ColorTokens.getChartColor(startIndex, alpha)} 0%, ${ColorTokens.getChartColor(endIndex, alpha)} 100%)`;
    }

    getLegendSolid(index, alpha = 1) {
        return ColorTokens.getChartColor(index, alpha);
    }
    
    /**
     * 创建图例说明
     */
    createLegend() {
        const legendContainer = selectOne('#chartLegend');
        if (!legendContainer.length) return;
        
        // 预先计算颜色渐变与纯色块，保持 token 一致
        const gradientInstance = this.getLegendGradient(1, 0);
        const gradientDatabase = this.getLegendGradient(2, 3);
        const solidA = this.getLegendSolid(1, 0.9);
        const solidB = this.getLegendSolid(2, 0.9);
        const solidC = this.getLegendSolid(0, 0.7);
        const solidD = this.getLegendSolid(4, 0.7);
        
        // 根据当前统计周期生成图例说明
        const periodType = this.currentPeriodType;
        let legendHtml = '';
        
        if (periodType === 'daily') {
            legendHtml = `
                <div class="chart-legend">
                    <h6>核心指标说明：</h6>
                    <div class="legend-items">
                        <div class="legend-item">
                            <span class="legend-color" style="background: ${gradientInstance}; width: 30px; height: 4px; display: inline-block; margin-right: 8px; border-radius: 2px;"></span>
                            <span class="legend-text">📊 实例数总量（蓝色实线，70%透明度）+ 实例日统计数量（红色实线，70%透明度）→ 紫色偏粉红混合效果</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background: ${gradientDatabase}; width: 30px; height: 4px; display: inline-block; margin-right: 8px; border-radius: 2px;"></span>
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
                            <span class="legend-color" style="background: ${this.getLegendGradient(1, 0)}; width: 30px; height: 4px; display: inline-block; margin-right: 8px; border-radius: 2px;"></span>
                            <span class="legend-text">📊 实例数平均值（周）（蓝色实线）+ 实例周统计数量（红色虚线）→ 紫色偏粉红混合效果</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background: ${this.getLegendGradient(3, 4)}; width: 30px; height: 4px; display: inline-block; margin-right: 8px; border-radius: 2px;"></span>
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
                            <span class="legend-color" style="background-color: ${solidA};"></span>
                            <span class="legend-text">📊 实例数平均值（月） - 每月采集的实例数量平均值</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background-color: ${solidB};"></span>
                            <span class="legend-text">🗄️ 数据库数平均值（月） - 每月采集的数据库数量平均值</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background-color: ${solidC}; border-style: dashed;"></span>
                            <span class="legend-text">📈 实例月统计数量 - 聚合统计下的实例月统计数量</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background-color: ${solidD}; border-style: dashed;"></span>
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
                            <span class="legend-color" style="background-color: ${solidA};"></span>
                            <span class="legend-text">📊 实例数平均值（季） - 每季采集的实例数量平均值</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background-color: ${solidB};"></span>
                            <span class="legend-text">🗄️ 数据库数平均值（季） - 每季采集的数据库数量平均值</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background-color: ${solidC}; border-style: dashed;"></span>
                            <span class="legend-text">📈 实例季统计数量 - 聚合统计下的实例季统计数量</span>
                        </div>
                        <div class="legend-item">
                            <span class="legend-color" style="background-color: ${solidD}; border-style: dashed;"></span>
                            <span class="legend-text">📈 数据库季统计数量 - 聚合统计下的数据库季统计数量</span>
                        </div>
                    </div>
                </div>
            `;
        }
        
        legendContainer.html(legendHtml);
    }
    
    bindEvents() {
        // 周期类型切换
        const periodInputs = document.querySelectorAll('input[name="periodType"]');
        periodInputs.forEach((input) => {
            input.addEventListener('change', (event) => {
                this.currentPeriodType = event.target.value;
                this.updateChartInfo();
                this.createLegend();
                this.loadChartData();
            });
        });

        const refreshButton = document.getElementById('refreshAggregations');
        if (refreshButton) {
            refreshButton.addEventListener('click', () => this.refreshAllData());
        }
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
        
        selectOne('#chartTitle').text(periodNames[this.currentPeriodType] || '');
        selectOne('#chartSubtitle').text(periodSubtitles[this.currentPeriodType] || '');
    }
    
    /**
     * 加载图表数据
     */
    async loadChartData() {
        this.showChartLoading(true);

        if (this.partitionStore) {
            try {
                await this.partitionStore.actions.loadCoreMetrics({
                    periodType: this.currentPeriodType,
                    days: 7,
                });
            } catch (error) {
                console.error('加载图表数据异常:', error);
                this.showError('加载图表数据异常');
                this.showChartLoading(false);
            }
            return;
        }

        try {
            const params = buildChartQueryParams({
                period_type: this.currentPeriodType,
                days: 7,
            });

            const raw = await partitionService.fetchCoreMetrics(params);
            if (raw.success !== false) {
                const payload = raw?.data ?? raw ?? {};
                this.currentData = payload;
                this.renderChart(payload);
                this.updateChartStats(payload);
            } else {
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
        const canvas = selectOne('#aggregationsChart').first();
        if (!canvas) {
            this.showError('找不到图表容器');
            return;
        }
        const ctx = canvas.getContext('2d');
        
        // 销毁现有图表
        if (this.chart) {
            this.chart.destroy();
        }
        
        const chartData = this.prepareChartData(data);
        
        // 如果有数据，隐藏消息
        if (chartData.labels.length > 0 && chartData.datasets.length > 0) {
            this.hideChartMessage();
        }
        
        const contrastColor = ColorTokens.resolveCssVar('--surface-contrast') || 'var(--surface-contrast)';
        const surfaceText = ColorTokens.resolveCssVar('--surface-elevated') || 'var(--surface-elevated)';
        const tooltipBackground = ColorTokens.withAlpha(contrastColor, 0.85);
        const tooltipText = surfaceText;
        const tooltipBorder = ColorTokens.getAccentColor();
        const gridColor = ColorTokens.withAlpha(contrastColor, 0.15);

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
                        backgroundColor: tooltipBackground,
                        titleColor: tooltipText,
                        bodyColor: tooltipText,
                        borderColor: tooltipBorder,
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
                            color: gridColor
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
                            color: gridColor
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
        const labels = LodashUtils.sortBy(Object.keys(groupedData || {}));

        // 收集所有数据库名称并保持唯一
        const allDatabases = LodashUtils.uniq(
            LodashUtils.flatMap(Object.values(groupedData || {}), (dateData) =>
                Object.keys(dateData || {})
            )
        );

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
            
            const borderColor = style?.color || ColorTokens.getChartColor(colorIndex);
            datasets.push({
                label: dbName,
                data: dataPoints,
                borderColor,
                backgroundColor: ColorTokens.withAlpha(borderColor, 0.2),
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
            selectOne('#dataPointCount').text(data.dataPointCount);
            selectOne('#timeRange').text(data.timeRange);
            return;
        }
        
        // 旧格式数据处理
        if (!data || !data.length) {
            selectOne('#dataPointCount').text('0');
            selectOne('#timeRange').text('-');
            return;
        }
        
        // 统一使用period_end作为日期显示
        const dates = LodashUtils.sortBy(
            LodashUtils.compact(data.map(item => item.period_end))
        );
        const dataPointCount = data.length;
        
        let timeRange = '-';
        if (dates.length > 0) {
            // 使用统一的时间格式化
            const startDate = timeUtils.formatDate(dates[0]);
            const endDate = timeUtils.formatDate(dates[dates.length - 1]);
            timeRange = `${startDate} - ${endDate}`;
        }
        
        selectOne('#dataPointCount').text(dataPointCount);
        selectOne('#timeRange').text(timeRange);
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
        const loading = selectOne('#chartLoading');
        if (!loading.length) {
            return;
        }
        loading.toggleClass('d-none', !show);
    }
    
    /**
     * 显示图表消息
     */
    showChartMessage(message) {
        const messageDiv = selectOne('#chartMessage');
        const messageText = selectOne('#chartMessageText');
        if (!messageDiv.length || !messageText.length) {
            return;
        }
        messageText.text(message);
        messageDiv.removeClass('d-none');
    }
    
    /**
     * 隐藏图表消息
     */
    hideChartMessage() {
        const messageDiv = selectOne('#chartMessage');
        if (!messageDiv.length) {
            return;
        }
        messageDiv.addClass('d-none');
    }
    
    /**
     * 显示错误信息
     */
    showError(message) {
        console.error('图表错误:', message);
    }

    ensurePartitionStore() {
        if (this.partitionStore) {
            this.bindStoreEvents();
            return true;
        }
        if (window.PartitionStoreInstance) {
            this.partitionStore = window.PartitionStoreInstance;
            this.bindStoreEvents();
            return true;
        }
        if (!createPartitionStore) {
            console.warn('createPartitionStore 未初始化，使用直接请求模式');
            return false;
        }
        try {
            this.partitionStore = createPartitionStore({
                service: partitionService,
                emitter: window.mitt ? window.mitt() : null,
            });
            window.PartitionStoreInstance = this.partitionStore;
            this.ownsStore = true;
            this.partitionStore.init({ autoLoad: false });
            this.bindStoreEvents();
            return true;
        } catch (error) {
            console.error('初始化 PartitionStore 失败:', error);
            this.partitionStore = null;
            return false;
        }
    }

    bindStoreEvents() {
        if (!this.partitionStore) {
            return;
        }
        this.subscribeToStore('partitions:metricsUpdated', this.handleMetricsUpdated);
        this.subscribeToStore('partitions:loading', this.handleStoreLoading);
        this.subscribeToStore('partitions:error', this.handleStoreError);
    }

    subscribeToStore(eventName, handler) {
        this.partitionStore.subscribe(eventName, handler);
        this.partitionStoreSubscriptions.push({ eventName, handler });
    }

    handleMetricsUpdated(payload) {
        const metrics = payload?.metrics || payload?.state?.metrics;
        if (!metrics) {
            return;
        }
        if (metrics.periodType !== this.currentPeriodType) {
            return;
        }
        this.currentData = metrics.payload;
        this.renderChart(metrics.payload);
        this.updateChartStats(metrics.payload);
        this.showChartLoading(false);
    }

    handleStoreLoading(payload) {
        if (payload?.target !== 'metrics') {
            return;
        }
        const loading = payload?.loading?.metrics ?? false;
        this.showChartLoading(loading);
    }

    handleStoreError(payload) {
        if (payload?.meta?.target !== 'metrics') {
            return;
        }
        this.showChartLoading(false);
        this.showError(payload?.error?.message || '加载图表数据失败');
        this.showChartMessage('加载聚合数据失败');
    }

    teardownStore() {
        if (!this.partitionStore) {
            return;
        }
        this.partitionStoreSubscriptions.forEach(({ eventName, handler }) => {
            this.partitionStore.unsubscribe(eventName, handler);
        });
        this.partitionStoreSubscriptions.length = 0;
        if (this.ownsStore) {
            this.partitionStore.destroy?.();
            window.PartitionStoreInstance = null;
        }
        this.partitionStore = null;
    }
    
    /**
     * 格式化大小（从MB）
     */
    static formatSizeFromMB(mb) {
        return window.NumberFormat.formatBytesFromMB(mb, {
            precision: 2,
            fallback: '0 B'
        });
    }
    
    /**
     * 格式化日期时间
     */
    formatDateTime(dateString) {
        // 使用统一的时间格式化
        return timeUtils.formatDateTime(dateString);
    }
}

// 页面加载完成后初始化
ready(() => {
    /**
     * 确保 Chart.js 加载后再初始化图表管理器。
     *
     * @param {void} 无参数。函数仅依赖全局 Chart 与 AggregationsChartManager。
     * @returns {void}
     */
    function initManager() {
        if (typeof Chart !== 'undefined' && typeof AggregationsChartManager !== 'undefined') {
            window.aggregationsChartManager = new AggregationsChartManager();
            from(window).on('beforeunload', () => {
                window.aggregationsChartManager?.teardownStore();
            });
        } else {
            window.setTimeout(initManager, 100);
        }
    }

    initManager();
});
}

window.AggregationsChartPage = {
    mount: mountAggregationsChart,
};
