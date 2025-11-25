(function (window) {
  "use strict";

  const DataSource = window.CapacityStatsDataSource;
  const Transformers = window.CapacityStatsTransformers;
  const SummaryCards = window.CapacityStatsSummaryCards;
  const Filters = window.CapacityStatsFilters;
  const ChartRenderer = window.CapacityStatsChartRenderer;
  const LodashUtils = window.LodashUtils;
  const helpers = window.DOMHelpers;
  if (!helpers) {
    throw new Error("DOMHelpers 未初始化");
  }
  const { selectOne, select } = helpers;
  if (!LodashUtils) {
    throw new Error("LodashUtils 未初始化");
  }
  const toast = window.toast || null;
  const EventBus = window.EventBus || null;

  const DEFAULT_CONFIG = {
    selectors: {
      charts: {
        trend: "#instanceChart",
        change: "#instanceChangeChart",
        percent: "#instanceChangePercentChart",
      },
      loaders: {
        trend: "#chartLoading",
        change: "#changeChartLoading",
        percent: "#changePercentChartLoading",
      },
    },
    chartTitles: {
      trend: "容量统计趋势图",
      change: "容量变化趋势图",
      percent: "容量变化趋势图 (百分比)",
    },
    axisLabels: {
      trend: "大小 (GB)",
      change: "变化量 (GB)",
      percent: "变化率 (%)",
    },
    fields: {
      change: "total_size_change_mb",
      percent: "total_size_change_percent",
    },
    includeDatabaseName: false,
    supportsDatabaseFilter: false,
    scope: "instance",
    filterFormId: null,
    autoApplyOnFilterChange: true,
  };

  const PERIOD_TEXT = {
    daily: {
      title: "统计当前日",
      message: "正在统计当前日容量，请稍候...",
    },
    weekly: {
      title: "统计当前周",
      message: "正在统计当前周容量，请稍候...",
    },
    monthly: {
      title: "统计当前月",
      message: "正在统计当前月容量，请稍候...",
    },
    quarterly: {
      title: "统计当前季度",
      message: "正在统计当前季度容量，请稍候...",
    },
    default: {
      title: "统计当前周期",
      message: "正在统计当前周期，请稍候...",
    },
  };

  /**
   * 统一日期格式化工具，封装 window.formatDate。
   */
  function formatDate(date) {
    return window.formatDate(date);
  }

  /**
   * 根据基准日和周期类型计算当前周期的起止时间。
   */
  function getCurrentPeriodRange(baseDate, periodType) {
    const normalized = (periodType || "daily").toLowerCase();
    const current = new Date(baseDate);
    current.setHours(12, 0, 0, 0);

    const start = new Date(current);
    const end = new Date(current);

    switch (normalized) {
      case "weekly": {
        const day = current.getDay(); // Sunday = 0
        const offsetToMonday = (day + 6) % 7;
        start.setDate(start.getDate() - offsetToMonday);
        end.setDate(start.getDate() + 6);
        break;
      }
      case "monthly": {
        start.setDate(1);
        end.setMonth(start.getMonth() + 1, 0);
        break;
      }
      case "quarterly": {
        const quarter = Math.floor(start.getMonth() / 3);
        const quarterStartMonth = quarter * 3;
        start.setMonth(quarterStartMonth, 1);
        end.setMonth(quarterStartMonth + 3, 0);
        break;
      }
      default:
        break;
    }

    start.setHours(12, 0, 0, 0);
    end.setHours(12, 0, 0, 0);

    return { start, end };
  }

  /**
   * 计算跨多个周期的起止时间范围，用于批量查询。
   */
  function calculateDateRange(periodType, periods) {
    const normalizedPeriod = (periodType || "daily").toLowerCase();
    const count = Math.max(1, Number(periods) || 1);
    const today = new Date();
    const { start: currentStart, end: currentEnd } = getCurrentPeriodRange(
      today,
      normalizedPeriod
    );

    const startDate = new Date(currentStart);
    startDate.setHours(12, 0, 0, 0);

    switch (normalizedPeriod) {
      case "weekly": {
        const deltaWeeks = (count - 1) * 7;
        if (deltaWeeks > 0) {
          startDate.setDate(startDate.getDate() - deltaWeeks);
        }
        break;
      }
      case "monthly": {
        if (count > 1) {
          startDate.setMonth(startDate.getMonth() - (count - 1));
        }
        startDate.setDate(1);
        break;
      }
      case "quarterly": {
        if (count > 1) {
          startDate.setMonth(startDate.getMonth() - (count - 1) * 3);
        }
        startDate.setDate(1);
        break;
      }
      default: {
        const deltaDays = count - 1;
        if (deltaDays > 0) {
          startDate.setDate(startDate.getDate() - deltaDays);
        }
      }
    }

    currentEnd.setHours(12, 0, 0, 0);

    return {
      startDate: formatDate(startDate),
      endDate: formatDate(currentEnd),
    };
  }

  /**
   * 容量统计总控：负责筛选、数据加载与图表渲染。
   *
   * 统一管理容量统计的筛选器、数据加载和图表渲染，支持趋势图、变化图和百分比图。
   *
   * @class
   */
  class CapacityStatsManager {
    /**
     * 构造函数。
     *
     * @constructor
     * @param {Object} userConfig - 用户配置对象
     * @param {Function} userConfig.labelExtractor - 标签提取函数（必需）
     * @param {string} [userConfig.filterFormId] - 筛选表单 ID
     * @param {boolean} [userConfig.autoApplyOnFilterChange=true] - 是否自动应用筛选
     * @throws {Error} 当缺少 labelExtractor 配置时抛出
     */
    constructor(userConfig) {
      const userOverrides = userConfig ? LodashUtils.cloneDeep(userConfig) : {};
      this.config = LodashUtils.merge({}, DEFAULT_CONFIG, userOverrides);
      this.config.autoApplyOnFilterChange =
        userOverrides?.autoApplyOnFilterChange !== undefined
          ? Boolean(userOverrides.autoApplyOnFilterChange)
          : DEFAULT_CONFIG.autoApplyOnFilterChange;
      this.filterFormId = (this.config.filterFormId || "").replace(/^#/, "") || null;
      this.handleFilterEvent = this.handleFilterEvent.bind(this);
      this.eventBusUnsubscribers = [];
      if (EventBus && this.filterFormId) {
        ["change", "submit", "clear"].forEach((action) => {
          const channel = `filters:${action}`;
          EventBus.on(channel, this.handleFilterEvent);
          this.eventBusUnsubscribers.push(() => EventBus.off(channel, this.handleFilterEvent));
        });
      }

      if (!this.config.labelExtractor || typeof this.config.labelExtractor !== "function") {
        throw new Error("CapacityStatsManager: 缺少 labelExtractor 配置");
      }

      this.state = {
        filters: Filters.readInitialFilters(this.config),
        charts: Filters.readChartState(),
        overrides: {
          change: false,
          percent: false,
        },
      };

      this.dataStore = {
        trend: [],
        change: [],
        percent: [],
      };

      this.charts = {
        trend: null,
        change: null,
        percent: null,
      };
      this.calculationModal = null;

      this.initialize();

      window.addEventListener("beforeunload", () => this.destroy(), { once: true });
    }

    /**
     * 初始化计算提示模态。
     */
    initializeModals() {
      const factory = window.UI?.createModal;
      if (!factory) {
        throw new Error("UI.createModal 未加载，容量统计模态无法初始化");
      }
      const modalElement = selectOne("#calculationModal");
      if (!modalElement.length) {
        return;
      }
      this.calculationModal = factory({
        modalSelector: modalElement.first(),
        confirmSelector: null,
        cancelSelector: null,
      });
    }

    /**
     * 初始流程：事件绑定、模态初始化、默认加载数据。
     */
    async initialize() {
      this.bindEvents();
      this.initializeModals();
      try {
        await this.prepareInitialOptions();
      } catch (error) {
        this.notifyError(`初始化筛选项失败: ${error.message}`);
      }
      await this.refreshAll();
    }

    /**
     * 首次加载时，填充实例/数据库等下拉选项。
     */
    async prepareInitialOptions() {
      await this.refreshInstanceOptions({ preserveSelection: true });
      if (this.config.supportsDatabaseFilter) {
        await this.refreshDatabaseOptions(this.state.filters.instanceId, {
          preserveSelection: true,
        });
      }
    }

    /**
     * 响应 filter-card 事件，支持 clear/change/submit。
     */
    handleFilterEvent(detail) {
      if (!detail || !this.filterFormId) {
        return;
      }
      const incoming = (detail.formId || "").replace(/^#/, "");
      if (!incoming || incoming !== this.filterFormId) {
        return;
      }
      switch (detail.action) {
        case "clear":
          this.resetFilters();
          break;
        case "change":
          if (this.config.autoApplyOnFilterChange) {
            this.applyFilters();
          }
          break;
        case "submit":
          this.applyFilters();
          break;
        default:
          break;
      }
    }

    /**
     * 绑定页面交互事件，更新 state 并触发重绘。
     */
    bindEvents() {
      this.attach("#refreshData", "click", (event) => {
        event.preventDefault();
        this.refreshAll();
      });

      this.attach("#calculateAggregations", "click", (event) => {
        event.preventDefault();
        this.handleCalculateToday();
      });

      this.attach("#db_type", "change", (event) => this.handleDbTypeChange(event));
      this.attach("#instance", "change", (event) => this.handleInstanceChange(event));
      if (this.config.supportsDatabaseFilter) {
        this.attach("#database", "change", (event) => this.handleDatabaseChange(event));
      }
      this.attach("#period_type", "change", (event) => this.handlePeriodTypeChange(event));

      this.attachGroup("chartType", (value) => {
        this.state.charts.trend.type = value;
        this.renderTrendChart();
      });
      this.attachGroup("topSelector", (value) => {
        this.state.charts.trend.top = Number(value) || 5;
        this.renderTrendChart();
      });
      this.attachGroup("statisticsPeriod", (value) => {
        this.state.charts.trend.periods = Number(value) || 7;
        if (!this.state.overrides.change) {
          this.state.charts.change.periods = this.state.charts.trend.periods;
        }
        if (!this.state.overrides.percent) {
          this.state.charts.percent.periods = this.state.charts.trend.periods;
        }
        this.reloadAfterPeriodChange();
      });

      this.attachGroup("changeChartType", (value) => {
        this.state.charts.change.type = value;
        this.renderChangeChart();
      });
      this.attachGroup("changeTopSelector", (value) => {
        this.state.charts.change.top = Number(value) || 5;
        this.renderChangeChart();
      });
      this.attachGroup("changeStatisticsPeriod", (value) => {
        this.state.charts.change.periods = Number(value) || 7;
        this.state.overrides.change = true;
        this.loadChangeData();
      });

      this.attachGroup("changePercentChartType", (value) => {
        this.state.charts.percent.type = value;
        this.renderChangePercentChart();
      });
      this.attachGroup("changePercentTopSelector", (value) => {
        this.state.charts.percent.top = Number(value) || 5;
        this.renderChangePercentChart();
      });
      this.attachGroup("changePercentStatisticsPeriod", (value) => {
        this.state.charts.percent.periods = Number(value) || 7;
        this.state.overrides.percent = true;
        this.loadPercentChangeData();
      });
    }

    /**
     * 工具：按选择器为单个元素绑定事件。
     */
    attach(selector, eventName, handler) {
      const element = selectOne(selector);
      if (!element.length) {
        return;
      }
      element.on(eventName, handler);
    }

    /**
     * 工具：为同名 radio/checkbox 组绑定事件。
     */
    attachGroup(name, handler) {
      if (!name) {
        return;
      }
      const inputs = select(`input[name="${name}"]`);
      if (!inputs.length) {
        return;
      }
      inputs.on("change", (event) => {
        const value = event?.target?.value ?? event?.currentTarget?.value ?? "";
        handler(value);
      });
    }

    /**
     * 同步刷新所有图表和摘要。
     */
    async refreshAll() {
      try {
        await Promise.all([
          this.loadSummaryData(),
          this.loadTrendData(),
          this.loadChangeData(),
          this.loadPercentChangeData(),
        ]);
        this.notifySuccess("数据刷新成功");
      } catch (error) {
        this.notifyError(error.message || "数据刷新失败");
      }
    }

    /**
     * 拉取顶部汇总卡片的数据。
     */
    async loadSummaryData() {
      try {
        const params = this.buildCommonParams();
        const range = calculateDateRange(
          this.state.filters.periodType,
          this.state.charts.trend.periods
        );
        params.start_date = range.startDate;
        params.end_date = range.endDate;
        const summary = await DataSource.fetchSummary(this.config.api, params);
        SummaryCards.updateCards(summary, this.config.summaryCards || []);
      } catch (error) {
        this.notifyError(`加载汇总数据失败: ${error.message}`);
      }
    }

    /**
     * 拉取趋势图数据并渲染。
     */
    async loadTrendData() {
      this.toggleLoader("trend", true);
      try {
        const params = this.buildTrendParams();
        const items = await DataSource.fetchTrend(this.config.api, params);
        this.dataStore.trend = Array.isArray(items) ? items : [];
        this.renderTrendChart();
      } catch (error) {
        this.notifyError(`加载容量趋势数据失败: ${error.message}`);
        this.dataStore.trend = [];
        this.renderTrendChart();
      } finally {
        this.toggleLoader("trend", false);
      }
    }

    /**
     * 使用最新数据重绘容量趋势图。
     */
    renderTrendChart() {
      this.charts.trend = ChartRenderer.renderTrendChart({
        canvas: this.config.selectors.charts.trend,
        instance: this.charts.trend,
        type: this.state.charts.trend.type,
        data: Transformers.prepareTrendChartData({
          items: this.dataStore.trend || [],
          labelExtractor: this.config.labelExtractor,
          topN: this.state.charts.trend.top,
          chartType: this.state.charts.trend.type,
        }),
        title: this.config.chartTitles.trend,
        yLabel: this.config.axisLabels.trend,
      });
    }

    /**
     * 拉取容量变化数据并渲染。
     */
    async loadChangeData() {
      this.toggleLoader("change", true);
      try {
        const params = this.buildChangeParams();
        const items = await DataSource.fetchChange(this.config.api, params);
        this.dataStore.change = Array.isArray(items) ? items : [];
        this.renderChangeChart();
      } catch (error) {
        this.notifyError(`加载容量变化趋势数据失败: ${error.message}`);
        this.dataStore.change = [];
        this.renderChangeChart();
      } finally {
        this.toggleLoader("change", false);
      }
    }

    /**
     * 重绘容量变化图（绝对值）。
     */
    renderChangeChart() {
      this.charts.change = ChartRenderer.renderChangeChart({
        canvas: this.config.selectors.charts.change,
        instance: this.charts.change,
        type: this.state.charts.change.type,
        data: Transformers.prepareChangeChartData({
          items: this.dataStore.change || [],
          labelExtractor: this.config.labelExtractor,
          topN: this.state.charts.change.top,
          chartType: this.state.charts.change.type,
          valueField: this.config.fields.change,
        }),
        title: this.config.chartTitles.change,
        yLabel: this.config.axisLabels.change,
      });
    }

    /**
     * 拉取容量变化百分比数据并渲染。
     */
    async loadPercentChangeData() {
      this.toggleLoader("percent", true);
      try {
        const params = this.buildPercentParams();
        const items = await DataSource.fetchPercentChange(this.config.api, params);
        this.dataStore.percent = Array.isArray(items) ? items : [];
        this.renderChangePercentChart();
      } catch (error) {
        this.notifyError(`加载容量变化百分比数据失败: ${error.message}`);
        this.dataStore.percent = [];
        this.renderChangePercentChart();
      } finally {
        this.toggleLoader("percent", false);
      }
    }

    /**
     * 重绘容量变化百分比图。
     */
    renderChangePercentChart() {
      this.charts.percent = ChartRenderer.renderChangePercentChart({
        canvas: this.config.selectors.charts.percent,
        instance: this.charts.percent,
        type: this.state.charts.percent.type,
        data: Transformers.prepareChangePercentChartData({
          items: this.dataStore.percent || [],
          labelExtractor: this.config.labelExtractor,
          topN: this.state.charts.percent.top,
          chartType: this.state.charts.percent.type,
          valueField: this.config.fields.percent,
        }),
        title: this.config.chartTitles.percent,
        yLabel: this.config.axisLabels.percent,
      });
    }

    /**
     * 构造所有接口共享的查询参数。
     */
    buildCommonParams() {
      const params = {};
      const filters = this.state.filters;

      if (filters.instanceId) {
        params.instance_id = filters.instanceId;
      }
      if (filters.dbType) {
        params.db_type = filters.dbType;
      }
      if (this.config.supportsDatabaseFilter && filters.databaseId) {
        params.database_id = filters.databaseId;
      }
      if (this.config.includeDatabaseName && filters.databaseName && filters.databaseId) {
        params.database_name = filters.databaseName;
      }
      params.period_type = filters.periodType || "daily";
      return params;
    }

    /**
     * 构造趋势图接口参数。
     */
    buildTrendParams() {
      const params = this.buildCommonParams();
      const range = calculateDateRange(
        this.state.filters.periodType,
        this.state.charts.trend.periods
      );
      params.start_date = range.startDate;
      params.end_date = range.endDate;
      return params;
    }

    /**
     * 构造变化图接口参数。
     */
    buildChangeParams() {
      const params = this.buildCommonParams();
      const range = calculateDateRange(
        this.state.filters.periodType,
        this.state.charts.change.periods
      );
      params.start_date = range.startDate;
      params.end_date = range.endDate;
      params.get_all = "true";
      return params;
    }

    /**
     * 构造变化百分比接口参数。
     */
    buildPercentParams() {
      const params = this.buildCommonParams();
      const range = calculateDateRange(
        this.state.filters.periodType,
        this.state.charts.percent.periods
      );
      params.start_date = range.startDate;
      params.end_date = range.endDate;
      params.get_all = "true";
      return params;
    }

    toggleLoader(kind, visible) {
      const selector = this.config.selectors.loaders?.[kind];
      if (!selector) {
        return;
      }
      const element = selectOne(selector).first();
      if (!element) {
        return;
      }
      element.classList.toggle("d-none", !visible);
    }

    async handleCalculateToday() {
      const modalElement = selectOne("#calculationModal").first();
      const modalInstance = this.calculationModal;
      const periodType = (this.state.filters.periodType || "daily").toLowerCase();
      const textConfig = PERIOD_TEXT[periodType] || PERIOD_TEXT.default;

      if (modalElement) {
        const titleNode = modalElement.querySelector(".calculation-modal-title-text");
        if (titleNode) {
          titleNode.textContent = textConfig.title;
        }
        const messageNode = modalElement.querySelector(".calculation-modal-message");
        if (messageNode) {
          messageNode.textContent = textConfig.message;
        }

        modalInstance?.open();
      }

      try {
        await DataSource.calculateCurrent(this.config.api.calculateEndpoint, {
          period_type: periodType,
          scope: this.config.scope || "instance",
        });
        this.notifySuccess("聚合计算完成");
        await this.refreshAll();
      } catch (error) {
        this.notifyError(`聚合计算失败: ${error.message}`);
      } finally {
        modalInstance?.close();
      }
    }

    async handleDbTypeChange(event) {
      const value = event?.target?.value || "";
      this.state.filters.dbType = value;
      this.state.filters.instanceId = "";
      Filters.syncSelectValue("#instance", "");
      Filters.setDisabled("#instance", true);

      if (this.config.supportsDatabaseFilter) {
        this.state.filters.databaseId = "";
        this.state.filters.databaseName = null;
        Filters.syncSelectValue("#database", "");
        Filters.setDisabled("#database", true);
      }

      await this.refreshInstanceOptions({ preserveSelection: false });
      if (this.config.supportsDatabaseFilter) {
        await this.refreshDatabaseOptions("", { preserveSelection: false });
      }
      await this.refreshAll();
    }

    async handleInstanceChange(event) {
      const value = event?.target?.value || "";
      this.state.filters.instanceId = value;
      if (this.config.supportsDatabaseFilter) {
        this.state.filters.databaseId = "";
        this.state.filters.databaseName = null;
        Filters.syncSelectValue("#database", "");
        Filters.setDisabled("#database", true);
        await this.refreshDatabaseOptions(value, { preserveSelection: false });
      }
      await this.refreshAll();
    }

    async handleDatabaseChange(event) {
      const select = event?.target;
      if (!select) {
        return;
      }
      const value = select.value || "";
      this.state.filters.databaseId = value;
      const option = select.options[select.selectedIndex];
      this.state.filters.databaseName = option ? option.textContent.trim() : null;
      await this.refreshAll();
    }

    async handlePeriodTypeChange(event) {
      const value = event?.target?.value || "daily";
      this.state.filters.periodType = value;
      await this.refreshAll();
    }

    /**
     * 拉取实例下拉数据，options 可指定是否保留原选择。
     */
    async refreshInstanceOptions(options) {
      const endpoint = this.config.api.instanceOptionsEndpoint;
      if (!endpoint) {
        return;
      }
      const params = {};
      if (this.state.filters.dbType) {
        params.db_type = this.state.filters.dbType;
      }
      try {
        const instances = await DataSource.fetchInstances(endpoint, params);
        Filters.updateSelectOptions("#instance", {
          placeholder: "所有实例",
          items: instances,
          allowEmpty: true,
          selected: options?.preserveSelection ? this.state.filters.instanceId : "",
          getOptionValue: (item) => item?.id,
          getOptionLabel: (item) => {
            if (!item) {
              return "";
            }
            const name = item.name || item.instance_name || "未知实例";
            const dbType = item.db_type || "";
            return dbType ? `${name} (${dbType})` : name;
          },
        });
        Filters.setDisabled("#instance", !this.state.filters.dbType);
      } catch (error) {
        this.notifyError(`加载实例列表失败: ${error.message}`);
        Filters.setDisabled("#instance", true);
      }
    }

    /**
     * 根据选中的实例加载数据库下拉。
     */
    async refreshDatabaseOptions(instanceId, options) {
      const endpoint = this.config.api.databaseOptionsEndpoint;
      if (!endpoint) {
        return;
      }
      if (!instanceId) {
        Filters.updateSelectOptions("#database", {
          placeholder: "所有数据库",
          allowEmpty: true,
          items: [],
        });
        Filters.setDisabled("#database", true);
        return;
      }
      const params = {
        instance_id: instanceId,
        limit: 1000,
      };
      try {
        const databases = await DataSource.fetchDatabases(
          endpoint,
          params
        );
        const sortedDatabases = LodashUtils.orderBy(
          databases || [],
          [
            (item) => (item?.database_name || "").toLowerCase(),
          ],
          ["asc"],
        );
        Filters.updateSelectOptions("#database", {
          placeholder: "所有数据库",
          allowEmpty: true,
          items: sortedDatabases,
          selected: options?.preserveSelection ? this.state.filters.databaseId : "",
          getOptionValue: (item) => item?.id,
          getOptionLabel: (item) => item?.database_name || "未知数据库",
        });
        Filters.setDisabled("#database", !instanceId);
      } catch (error) {
        this.notifyError(`加载数据库列表失败: ${error.message}`);
        Filters.setDisabled("#database", true);
      }
    }

    reloadAfterPeriodChange() {
      this.state.overrides.change = false;
      this.state.overrides.percent = false;
      this.refreshAll();
    }

    /**
     * 重置筛选表单，并刷新实例/数据库的选项。
     */
    async resetFilters() {
      this.state.filters = {
        dbType: "",
        instanceId: "",
        databaseId: "",
        databaseName: null,
        periodType: "daily",
      };
      Filters.syncSelectValue("#db_type", "");
      Filters.syncSelectValue("#instance", "");
      Filters.setDisabled("#instance", true);
      if (this.config.supportsDatabaseFilter) {
        Filters.syncSelectValue("#database", "");
        Filters.setDisabled("#database", true);
      }
      Filters.syncSelectValue("#period_type", "daily");
      this.state.overrides.change = false;
      this.state.overrides.percent = false;
      await this.prepareInitialOptions();
      await this.refreshAll();
    }

    /**
     * 正式应用当前筛选，并刷新实例/数据库选项。
     */
    async applyFilters() {
      const latest = Filters.readInitialFilters(this.config);
      this.state.filters.dbType = latest.dbType || "";
      this.state.filters.instanceId = latest.instanceId || "";
      this.state.filters.databaseId = latest.databaseId || "";
      this.state.filters.databaseName = latest.databaseName || null;
      this.state.filters.periodType = latest.periodType || "daily";
      Filters.setDisabled("#instance", !this.state.filters.dbType);
      if (this.config.supportsDatabaseFilter) {
        Filters.setDisabled("#database", !this.state.filters.instanceId);
      }
      await this.refreshAll();
    }

    /**
     * Toast 成功提示。
     */
    notifySuccess(message) {
      if (!message) {
        return;
      }
      if (toast?.success) {
        toast.success(message);
      } else {
        console.info(message);
      }
    }

    /**
     * Toast 错误提示。
     */
    notifyError(message) {
      if (!message) {
        return;
      }
      if (toast?.error) {
        toast.error(message);
      } else {
        console.error(message);
      }
    }

    /**
     * 清理事件与模态，释放资源。
     */
    destroy() {
      if (this.eventBusUnsubscribers && this.eventBusUnsubscribers.length) {
        this.eventBusUnsubscribers.forEach((unsubscribe) => {
          try {
            unsubscribe();
          } catch (error) {
            console.warn("解除事件总线订阅失败:", error);
          }
        });
        this.eventBusUnsubscribers = [];
      }
    }
  }

  window.CapacityStats = window.CapacityStats || {};
  window.CapacityStats.Manager = CapacityStatsManager;
})(window, document);
