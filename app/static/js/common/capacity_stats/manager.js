(function (window, document) {
  "use strict";

  const DataSource = window.CapacityStatsDataSource;
  const Transformers = window.CapacityStatsTransformers;
  const SummaryCards = window.CapacityStatsSummaryCards;
  const Filters = window.CapacityStatsFilters;
  const ChartRenderer = window.CapacityStatsChartRenderer;
  const toast = window.toast || null;

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
  };

  function formatDate(date) {
    if (window.formatDate) {
      return window.formatDate(date);
    }
    return date.toISOString().split("T")[0];
  }

  function calculateDateRange(periodType, periods) {
    const normalizedPeriod = (periodType || "daily").toLowerCase();
    const count = Math.max(1, Number(periods) || 1);
    const endDate = new Date();
    const startDate = new Date(endDate);

    switch (normalizedPeriod) {
      case "weekly":
        startDate.setDate(endDate.getDate() - count * 7);
        break;
      case "monthly":
        startDate.setMonth(endDate.getMonth() - count);
        break;
      case "quarterly":
        startDate.setMonth(endDate.getMonth() - count * 3);
        break;
      default:
        startDate.setDate(endDate.getDate() - count);
    }

    return {
      startDate: formatDate(startDate),
      endDate: formatDate(endDate),
    };
  }

  class CapacityStatsManager {
    constructor(userConfig) {
      this.config = Object.assign({}, DEFAULT_CONFIG, userConfig || {});

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

      this.initialize();
    }

    async initialize() {
      this.bindEvents();
      try {
        await this.prepareInitialOptions();
      } catch (error) {
        this.notifyError(`初始化筛选项失败: ${error.message}`);
      }
      await this.refreshAll();
    }

    async prepareInitialOptions() {
      await this.refreshInstanceOptions({ preserveSelection: true });
      if (this.config.supportsDatabaseFilter) {
        await this.refreshDatabaseOptions(this.state.filters.instanceId, {
          preserveSelection: true,
        });
      }
    }

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

    attach(selector, eventName, handler) {
      const element = document.querySelector(selector);
      if (!element) {
        return;
      }
      element.addEventListener(eventName, handler);
    }

    attachGroup(name, handler) {
      if (!name) {
        return;
      }
      const inputs = document.querySelectorAll(`input[name="${name}"]`);
      inputs.forEach((input) => {
        input.addEventListener("change", (event) => {
          handler(event.target.value);
        });
      });
    }

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
      const element = document.querySelector(selector);
      if (!element) {
        return;
      }
      element.classList.toggle("d-none", !visible);
    }

    async handleCalculateToday() {
      const modalElement = document.getElementById("calculationModal");
      let modalInstance = null;
      if (modalElement) {
        if (window.bootstrap?.Modal) {
          modalInstance = window.bootstrap.Modal.getOrCreateInstance(modalElement);
          modalInstance.show();
        } else if (window.$) {
          window.$(modalElement).modal("show");
          modalInstance = {
            hide() {
              window.$(modalElement).modal("hide");
            },
          };
        }
      }

      try {
        await DataSource.calculateToday(this.config.api.calculateEndpoint);
        this.notifySuccess("聚合计算完成");
        await this.refreshAll();
      } catch (error) {
        this.notifyError(`聚合计算失败: ${error.message}`);
      } finally {
        if (modalInstance && typeof modalInstance.hide === "function") {
          modalInstance.hide();
        }
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
        limit: 1000,
      };
      try {
        const databases = await DataSource.fetchDatabases(
          `${endpoint}/${encodeURIComponent(instanceId)}/databases`,
          params
        );
        Filters.updateSelectOptions("#database", {
          placeholder: "所有数据库",
          allowEmpty: true,
          items: databases.sort((a, b) => {
            const nameA = (a.database_name || "").toLowerCase();
            const nameB = (b.database_name || "").toLowerCase();
            return nameA.localeCompare(nameB);
          }),
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
  }

  window.CapacityStats = window.CapacityStats || {};
  window.CapacityStats.Manager = CapacityStatsManager;
})(window, document);
