function mountClusterPage(global) {
  "use strict";

  const helpers = global.DOMHelpers;
  const gridjs = global.gridjs;
  const GridWrapper = global.GridWrapper;
  const GridPage = global.Views?.GridPage;
  const GridPlugins = global.Views?.GridPlugins;
  const escapeHtml = global.UI?.escapeHtml;
  const resolveErrorMessage = global.UI?.resolveErrorMessage;
  const rowMeta = global.GridRowMeta;

  if (!helpers || !gridjs || !GridWrapper || !GridPage?.mount || !GridPlugins) {
    console.error("群集管理页面依赖未加载");
    return;
  }
  if (typeof escapeHtml !== "function" || typeof resolveErrorMessage !== "function" || !rowMeta?.get) {
    console.error("群集管理页面 UI helpers 未加载");
    return;
  }

  const pageRoot = document.getElementById("cluster-page-root");
  if (!pageRoot) {
    return;
  }

  const SQLServerClustersService = global.SQLServerClustersService;
  const createStore = global.createSQLServerClustersStore;
  const MySQLClustersService = global.MySQLClustersService;
  const createMySQLStore = global.createMySQLClustersStore;
  if (!SQLServerClustersService || typeof createStore !== "function" || !MySQLClustersService || typeof createMySQLStore !== "function") {
    console.error("群集管理 service 或 store 未加载");
    return;
  }

  const gridHtml = gridjs.html;
  const { ready } = helpers;
  let store = null;
  let mysqlStore = null;
  let gridWrapper = null;
  let mysqlGridWrapper = null;
  let modal = null;
  let mysqlModal = null;
  let agStatusModal = null;
  let modalEl = null;
  let mysqlModalEl = null;
  let agStatusModalEl = null;
  let currentAgItems = [];
  let currentDashboardContext = null;
  let activeDbTab = "sqlserver";
  const canManage = pageRoot.dataset.canManage === "true";
  const credentialOptions = parseJsonDataset(pageRoot.dataset.credentials, []);

  ready(() => {
    store = createStore({
      service: new SQLServerClustersService(),
      emitter: global.mitt ? global.mitt() : null,
    });
    mysqlStore = createMySQLStore({
      service: new MySQLClustersService(),
    });
    modalEl = document.getElementById("clusterManagementModal");
    modal = modalEl && global.bootstrap?.Modal ? new global.bootstrap.Modal(modalEl) : null;
    mysqlModalEl = document.getElementById("mysqlClusterManagementModal");
    mysqlModal = mysqlModalEl && global.bootstrap?.Modal ? new global.bootstrap.Modal(mysqlModalEl) : null;
    agStatusModalEl = document.getElementById("agStatusDashboardModal");
    agStatusModal = agStatusModalEl && global.bootstrap?.Modal ? new global.bootstrap.Modal(agStatusModalEl) : null;
    bindModalEvents();
    bindCreateButton();
    bindDbTabs();
    initializeGrid();
    initializeMySQLGrid();
  });

  function initializeGrid() {
    gridWrapper = GridPage.mount({
      root: pageRoot,
      grid: "#sqlserver-clusters-grid",
      filterForm: "#cluster-filter-form",
      gridOptions: {
        sort: false,
        columns: buildColumns(),
        server: {
          url: store.gridUrl,
          headers: { "X-Requested-With": "XMLHttpRequest" },
          then: handleServerResponse,
          total: (response) => {
            const payload = response?.data || response || {};
            return payload.total || 0;
          },
        },
      },
      filters: {
        allowedKeys: ["search", "status"],
        normalize: normalizeFilters,
      },
      plugins: [
        GridPlugins.filterCard({
          autoSubmitOnChange: true,
          autoSubmitDebounce: 400,
        }),
        GridPlugins.actionDelegation({
          actions: {
            "edit-cluster": ({ event, el }) => {
              event.preventDefault();
              openEditor(el.getAttribute("data-cluster-id"));
            },
            "sync-ag-accounts": ({ event, el }) => {
              event.preventDefault();
              syncAgAccounts(el);
            },
            "open-ag-accounts": ({ event, el }) => {
              event.preventDefault();
              openAgAccountsLedger(el);
            },
            "sync-sqlserver-status-row": ({ event, el }) => {
              event.preventDefault();
              syncSQLServerStatus(el);
            },
            "open-ag-dashboard": ({ event, el }) => {
              event.preventDefault();
              openClusterAgDashboard(el);
            },
          },
        }),
      ],
    })?.gridWrapper;
  }

  function initializeMySQLGrid() {
    mysqlGridWrapper = GridPage.mount({
      root: pageRoot,
      grid: "#mysql-clusters-grid",
      filterForm: "#cluster-filter-form",
      gridOptions: {
        sort: false,
        columns: buildMySQLColumns(),
        server: {
          url: mysqlStore.gridUrl,
          headers: { "X-Requested-With": "XMLHttpRequest" },
          then: handleMySQLServerResponse,
          total: (response) => {
            const payload = response?.data || response || {};
            return payload.total || 0;
          },
        },
      },
      filters: {
        allowedKeys: ["search", "status"],
        normalize: normalizeFilters,
      },
      plugins: [
        GridPlugins.filterCard({
          autoSubmitOnChange: true,
          autoSubmitDebounce: 400,
        }),
        GridPlugins.actionDelegation({
          actions: {
            "edit-mysql-cluster": ({ event, el }) => {
              event.preventDefault();
              openMySQLEditor(el.getAttribute("data-cluster-id"));
            },
            "sync-mysql-topology-row": ({ event, el }) => {
              event.preventDefault();
              syncMySQLTopologyFromRow(el);
            },
          },
        }),
      ],
    })?.gridWrapper;
  }

  function buildColumns() {
    const columns = [
      {
        name: "群集",
        id: "name",
        formatter: (cell, row) => {
          const meta = rowMeta.get(row);
          return gridHtml(
            `<div class="fw-semibold">${escapeHtml(cell || "-")}</div>` +
              `<small class="text-muted">${escapeHtml(meta.description || "SQL Server 群集")}</small>`
          );
        },
      },
      {
        name: "域名",
        id: "domain_name",
        formatter: (value) => value || "-",
      },
      {
        name: "状态",
        id: "is_enabled",
        formatter: (value) => gridHtml(renderStatus(value)),
      },
      {
        name: "绑定实例",
        id: "instance_count",
      },
      {
        name: "AG",
        id: "availability_group_count",
        formatter: (value, row) => {
          const meta = rowMeta.get(row);
          return `${Number(value || 0)} / contained ${Number(meta.contained_ag_count || 0)}`;
        },
      },
      {
        name: "最近 AG 同步",
        id: "last_ag_sync_status",
        formatter: (value, row) => {
          const meta = rowMeta.get(row);
          const status = value || "未同步";
          const syncAt = meta.last_ag_sync_at ? `<small class="text-muted ms-2">${escapeHtml(formatDate(meta.last_ag_sync_at))}</small>` : "";
          return gridHtml(`${renderSyncStatus(status)}${syncAt}`);
        },
      },
      {
        name: "数据库同步状态",
        id: "ag_database_sync_abnormal_count",
        formatter: (value, row) => {
          const meta = rowMeta.get(row);
          return gridHtml(renderSQLServerDatabaseStatusSummary(meta));
        },
      },
    ];

    if (canManage) {
      columns.push({
        name: "操作",
        id: "actions",
        sort: false,
        formatter: (value, row) => {
          const meta = rowMeta.get(row);
          const clusterId = escapeHtml(String(meta.id || ""));
          const firstInstanceId = escapeHtml(String(resolveFirstBoundInstanceId(meta) || ""));
          return gridHtml(
            `<div class="btn-group btn-group-sm" role="group">` +
              `<button type="button" class="btn btn-outline-secondary btn-sm btn-icon" data-action="edit-cluster" data-cluster-id="${clusterId}" title="管理" aria-label="管理">` +
              `<i class="fas fa-pen" aria-hidden="true"></i></button>` +
              `<button type="button" class="btn btn-outline-secondary btn-sm btn-icon" data-action="sync-ag-accounts" data-cluster-id="${clusterId}" title="同步AG账户" aria-label="同步AG账户">` +
              `<i class="fas fa-sync" aria-hidden="true"></i></button>` +
              `<button type="button" class="btn btn-outline-secondary btn-sm btn-icon" data-action="open-ag-accounts" data-cluster-id="${clusterId}" data-instance-id="${firstInstanceId}" title="账户列表" aria-label="账户列表">` +
              `<i class="fas fa-users" aria-hidden="true"></i></button>` +
              `<button type="button" class="btn btn-outline-secondary btn-sm btn-icon" data-action="sync-sqlserver-status-row" data-cluster-id="${clusterId}" title="数据库同步状态" aria-label="数据库同步状态">` +
              `<i class="fas fa-heart-pulse" aria-hidden="true"></i></button>` +
              `<button type="button" class="btn btn-outline-secondary btn-sm btn-icon" data-action="open-ag-dashboard" data-cluster-id="${clusterId}" title="查看AG状态" aria-label="查看AG状态">` +
              `<i class="fas fa-chart-line" aria-hidden="true"></i></button>` +
              `</div>`
          );
        },
      });
    }
    return columns;
  }

  function buildMySQLColumns() {
    const columns = [
      {
        name: "群集",
        id: "name",
        formatter: (cell, row) => {
          const meta = rowMeta.get(row);
          return gridHtml(
            `<div class="fw-semibold">${escapeHtml(cell || "-")}</div>` +
              `<small class="text-muted">${escapeHtml(meta.description || "MySQL replication 群集")}</small>`
          );
        },
      },
      {
        name: "拓扑",
        id: "topology_type",
        formatter: (value) => value || "replication",
      },
      {
        name: "状态",
        id: "is_enabled",
        formatter: (value) => gridHtml(renderStatus(value)),
      },
      {
        name: "绑定实例",
        id: "instance_count",
      },
      {
        name: "主从状态",
        id: "abnormal_replica_count",
        formatter: (value, row) => {
          const meta = rowMeta.get(row);
          return gridHtml(renderMySQLTopologySummary(meta));
        },
      },
      {
        name: "最大延迟",
        id: "max_replica_lag_seconds",
        formatter: (value, row) => {
          const meta = rowMeta.get(row);
          return renderMySQLLagSummary(meta);
        },
      },
    ];
    if (canManage) {
      columns.push({
        name: "操作",
        id: "actions",
        sort: false,
        formatter: (value, row) => {
          const meta = rowMeta.get(row);
          const clusterId = escapeHtml(String(meta.id || ""));
          return gridHtml(
            `<div class="btn-group btn-group-sm" role="group">` +
              `<button type="button" class="btn btn-outline-secondary btn-sm btn-icon" data-action="edit-mysql-cluster" data-cluster-id="${clusterId}" title="管理" aria-label="管理">` +
              `<i class="fas fa-pen" aria-hidden="true"></i></button>` +
              `<button type="button" class="btn btn-outline-secondary btn-sm btn-icon" data-action="sync-mysql-topology-row" data-cluster-id="${clusterId}" title="同步主从信息" aria-label="同步主从信息">` +
              `<i class="fas fa-rotate" aria-hidden="true"></i></button>` +
              `</div>`
          );
        },
      });
    }
    return columns;
  }

  function normalizeFilters(filters) {
    const normalized = filters && typeof filters === "object" ? filters : {};
    const cleaned = {};
    const search = typeof normalized.search === "string" ? normalized.search.trim() : "";
    if (search) {
      cleaned.search = search;
    }
    const status = typeof normalized.status === "string" ? normalized.status.trim() : "";
    if (status && status !== "all") {
      cleaned.status = status;
    }
    return cleaned;
  }

  function handleServerResponse(response) {
    const payload = response?.data || response || {};
    const items = Array.isArray(payload.items) ? payload.items : [];
    return items.map((item) => [
      item.name,
      item.domain_name,
      item.is_enabled,
      item.instance_count,
      item.availability_group_count,
      item.last_ag_sync_status,
      item.ag_database_sync_abnormal_count,
      item,
    ]);
  }

  function handleMySQLServerResponse(response) {
    const payload = response?.data || response || {};
    const items = Array.isArray(payload.items) ? payload.items : [];
    return items.map((item) => [
      item.name,
      item.topology_type,
      item.is_enabled,
      item.instance_count,
      item.abnormal_replica_count,
      item.max_replica_lag_seconds,
      item,
    ]);
  }

  function bindCreateButton() {
    pageRoot.querySelector('[data-action="create-cluster"]')?.addEventListener("click", () => {
      if (activeDbTab === "mysql") {
        openMySQLCreateModal();
        return;
      }
      openCreateModal();
    });
  }

  function bindDbTabs() {
    pageRoot.querySelectorAll("[data-cluster-db-type]").forEach((button) => {
      button.addEventListener("click", () => {
        const next = button.getAttribute("data-cluster-db-type") || "sqlserver";
        activeDbTab = next;
        pageRoot.querySelectorAll("[data-cluster-db-type]").forEach((tab) => {
          const active = tab === button;
          tab.classList.toggle("btn-primary", active);
          tab.classList.toggle("btn-outline-primary", !active);
          tab.classList.toggle("border-2", !active);
          tab.classList.toggle("fw-bold", !active);
        });
        pageRoot.querySelectorAll("[data-cluster-db-panel]").forEach((panel) => {
          panel.classList.toggle("d-none", panel.getAttribute("data-cluster-db-panel") !== next);
        });
      });
    });
  }

  function bindModalEvents() {
    document.getElementById("clusterManagementForm")?.addEventListener("submit", (event) => {
      event.preventDefault();
      saveCluster();
    });
    document.querySelector('[data-action="sync-ag"]')?.addEventListener("click", (event) => {
      syncAgInformation(event.currentTarget);
    });
    document.querySelector('[data-action="sync-sqlserver-status"]')?.addEventListener("click", (event) => {
      syncSQLServerStatus(event.currentTarget);
    });
    document.querySelector('[data-action="sync-ag-dashboard"]')?.addEventListener("click", (event) => {
      syncAgDashboard(event.currentTarget);
    });
    document.getElementById("agStatusDashboardTabs")?.addEventListener("click", (event) => {
      const target = event.target?.closest?.('[data-action="switch-ag-dashboard"]');
      if (!target) {
        return;
      }
      event.preventDefault();
      switchAgDashboard(target);
    });
    document.getElementById("mysqlClusterManagementForm")?.addEventListener("submit", (event) => {
      event.preventDefault();
      saveMySQLCluster();
    });
    document.querySelector('[data-action="sync-mysql-topology"]')?.addEventListener("click", (event) => {
      syncMySQLTopology(event.currentTarget);
    });
    document.getElementById("clusterAgTableBody")?.addEventListener("change", (event) => {
      const target = event.target;
      if (target?.matches?.('[data-action="update-ag-account-credential"]')) {
        updateAgAccountCredential(target);
      }
    });
    document.getElementById("clusterAgTableBody")?.addEventListener("click", (event) => {
      const toggleTarget = event.target?.closest?.('[data-action="toggle-ag-collection"]');
      if (toggleTarget) {
        event.preventDefault();
        toggleAgCollection(toggleTarget);
        return;
      }
    });
  }

  function openCreateModal() {
    setModalMode("create");
    fillBasic({});
    setSelectedInstances([]);
    renderAgTable([]);
    modal?.show();
  }

  function openEditor(clusterId) {
    if (!clusterId) {
      return;
    }
    store.actions
      .load(clusterId)
      .then((detail) => {
        setModalMode("edit");
        fillBasic(detail.cluster || {});
        setSelectedInstances((detail.instances || []).map((item) => String(item.id)));
        renderAgTable(detail.availability_groups || []);
        modal?.show();
      })
      .catch((error) => showError(error, "加载群集失败"));
  }

  function setModalMode(mode) {
    const form = document.getElementById("clusterManagementForm");
    if (form) {
      form.dataset.formMode = mode;
    }
    document.getElementById("clusterModalTitle").textContent = mode === "create" ? "添加群集" : "管理群集";
    document.getElementById("clusterModalSubmit").textContent = mode === "create" ? "添加群集" : "保存";
  }

  function fillBasic(cluster) {
    document.getElementById("clusterIdInput").value = cluster.id || "";
    document.getElementById("clusterNameInput").value = cluster.name || "";
    document.getElementById("clusterDomainNameInput").value = cluster.domain_name || "";
    document.getElementById("clusterDescriptionInput").value = cluster.description || "";
    document.getElementById("clusterEnabledInput").checked = cluster.is_enabled !== false;
  }

  function setSelectedInstances(instanceIds) {
    const select = document.getElementById("clusterInstanceSelect");
    if (!select) {
      return;
    }
    Array.from(select.options).forEach((option) => {
      option.selected = instanceIds.includes(option.value);
    });
  }

  function getSelectedInstances() {
    const select = document.getElementById("clusterInstanceSelect");
    if (!select) {
      return [];
    }
    return Array.from(select.selectedOptions).map((option) => Number(option.value)).filter(Boolean);
  }

  function buildClusterPayload() {
    return {
      name: document.getElementById("clusterNameInput").value.trim(),
      domain_name: document.getElementById("clusterDomainNameInput").value.trim(),
      description: document.getElementById("clusterDescriptionInput").value.trim(),
      is_enabled: document.getElementById("clusterEnabledInput").checked,
    };
  }

  function saveCluster() {
    const form = document.getElementById("clusterManagementForm");
    const mode = form?.dataset.formMode || "create";
    const payload = buildClusterPayload();
    if (!payload.name) {
      showToast("warning", "请输入群集名称");
      return;
    }
    if (!payload.domain_name) {
      showToast("warning", "请输入群集域名");
      return;
    }

    const run =
      mode === "create"
        ? store.actions.create(payload).then((response) => response?.data?.cluster)
        : store.actions.update(document.getElementById("clusterIdInput").value, payload).then((response) => response?.data?.cluster);

    run
      .then((cluster) => {
        if (!cluster?.id) {
          throw new Error("保存群集失败");
        }
        const instanceIds = getSelectedInstances();
        return store.actions.replaceInstances(cluster.id, instanceIds).then(() => cluster);
      })
      .then(() => {
        showToast("success", "群集已保存");
        modal?.hide();
        gridWrapper?.refresh?.();
      })
      .catch((error) => showError(error, "保存群集失败"));
  }

  function syncAgInformation(trigger) {
    const clusterId = document.getElementById("clusterIdInput").value;
    if (!clusterId) {
      showToast("warning", "请先保存群集后同步 AG 信息");
      return;
    }
    setButtonLoading(trigger, true);
    store.actions
      .syncAvailabilityGroups(clusterId, {})
      .then(() => store.actions.load(clusterId))
      .then((detail) => {
        renderAgTable(detail.availability_groups || []);
        showToast("success", "AG 信息同步完成");
        gridWrapper?.refresh?.();
      })
      .catch((error) => showError(error, "同步 AG 信息失败"))
      .finally(() => setButtonLoading(trigger, false));
  }

  function syncAgAccounts(trigger) {
    const clusterId = trigger?.getAttribute("data-cluster-id");
    if (!clusterId) {
      showToast("warning", "请选择群集后同步 AG 账户");
      return;
    }
    setButtonLoading(trigger, true);
    store.actions
      .syncAgAccounts(clusterId)
      .then(() => {
        showToast("success", "AG 账户同步完成");
        gridWrapper?.refresh?.();
      })
      .catch((error) => showError(error, "同步 AG 账户失败"))
      .finally(() => setButtonLoading(trigger, false));
  }

  function syncSQLServerStatus(trigger) {
    const clusterId = trigger?.getAttribute("data-cluster-id") || document.getElementById("clusterIdInput").value;
    if (!clusterId) {
      showToast("warning", "请先保存群集后检测同步状态");
      return;
    }
    setButtonLoading(trigger, true);
    store.actions
      .syncStatus(clusterId)
      .then(() => {
        showToast("success", "数据库同步状态检测完成");
        gridWrapper?.refresh?.();
      })
      .catch((error) => showError(error, "检测数据库同步状态失败"))
      .finally(() => setButtonLoading(trigger, false));
  }

  function openClusterAgDashboard(trigger) {
    const clusterId = trigger?.getAttribute("data-cluster-id");
    if (!clusterId) {
      showToast("warning", "请选择群集后查看 AG 状态");
      return;
    }
    setButtonLoading(trigger, true);
    store.actions
      .load(clusterId)
      .then((detail) => {
        const agItems = Array.isArray(detail.availability_groups) ? detail.availability_groups : [];
        if (!agItems.length) {
          showToast("warning", "当前群集暂无 AG 配置");
          return;
        }
        const firstAg = agItems[0];
        if (!firstAg?.id) {
          showToast("warning", "当前 AG 信息不完整");
          return;
        }
        currentDashboardContext = {
          clusterId,
          agId: String(firstAg.id),
          agItems,
        };
        resetAgDashboard();
        renderAgDashboardTabs(agItems, firstAg.id);
        agStatusModal?.show();
        loadAgDashboard(clusterId, firstAg.id);
      })
      .catch((error) => showError(error, "加载 AG 状态失败"))
      .finally(() => setButtonLoading(trigger, false));
  }

  function loadAgDashboard(clusterId, agId) {
    store.actions
      .getAvailabilityGroupDashboard(clusterId, agId)
      .then((data) => renderAgDashboard(data))
      .catch((error) => {
        showError(error, "加载 AG 状态失败");
        renderAgDashboardError(error);
      });
  }

  function syncAgDashboard(trigger) {
    const clusterId = currentDashboardContext?.clusterId || document.getElementById("clusterIdInput").value;
    const agId = currentDashboardContext?.agId;
    if (!clusterId || !agId) {
      showToast("warning", "请选择 AG 后检测状态");
      return;
    }
    setButtonLoading(trigger, true);
    store.actions
      .syncStatus(clusterId)
      .then(() => {
        showToast("success", "数据库同步状态检测完成");
        gridWrapper?.refresh?.();
        return store.actions.load(clusterId);
      })
      .then((detail) => {
        const agItems = Array.isArray(detail.availability_groups) ? detail.availability_groups : [];
        currentDashboardContext = {
          clusterId,
          agId,
          agItems,
        };
        renderAgTable(agItems);
        renderAgDashboardTabs(agItems, agId);
      })
      .then(() => loadAgDashboard(clusterId, agId))
      .catch((error) => showError(error, "检测数据库同步状态失败"))
      .finally(() => setButtonLoading(trigger, false));
  }

  function switchAgDashboard(trigger) {
    const agId = trigger?.getAttribute("data-ag-id");
    const clusterId = currentDashboardContext?.clusterId;
    if (!clusterId || !agId) {
      return;
    }
    currentDashboardContext = {
      ...currentDashboardContext,
      agId,
    };
    resetAgDashboard();
    renderAgDashboardTabs(currentDashboardContext.agItems || [], agId);
    loadAgDashboard(clusterId, agId);
  }

  function openAgAccountsLedger(trigger) {
    const instanceId = trigger?.getAttribute("data-instance-id");
    if (!instanceId) {
      showToast("warning", "请先为群集绑定 SQL Server 实例");
      return;
    }
    const params = new URLSearchParams();
    params.set("instance_id", instanceId);
    params.set("owner_type", "sqlserver_ag");
    params.set("include_roles", "true");
    global.location.href = `/accounts/ledgers/sqlserver?${params.toString()}`;
  }

  function renderAgTable(items) {
    const body = document.getElementById("clusterAgTableBody");
    if (!body) {
      return;
    }
    currentAgItems = Array.isArray(items) ? items : [];
    if (!items.length) {
      body.innerHTML = '<tr><td colspan="8" class="text-muted">暂无 AG 配置</td></tr>';
      return;
    }
    body.innerHTML = items.map((item) => renderAgRow(item)).join("");
  }

  function renderAgRow(item) {
    const listener = [item.listener_name, item.listener_host].filter(Boolean).join(" / ") || "-";
    const syncLabel = item.last_sync_status || "未同步";
    return `
      <tr>
        <td>${escapeHtml(item.name || "-")}</td>
        <td>${escapeHtml(listener)}</td>
        <td>${escapeHtml(item.connection_endpoint || "-")}</td>
        <td>${renderAccountCredentialSelect(item)}</td>
        <td>${renderBoolean(item.contained_enabled)}</td>
        <td>${renderCollectionToggle(item)}</td>
        <td>${escapeHtml(syncLabel)}</td>
        <td>${renderAgRowDatabaseStatus(item)}</td>
      </tr>
    `;
  }

  function renderAgRowDatabaseStatus(item) {
    const abnormal = Number(item.ag_database_sync_abnormal_count || 0);
    if (abnormal > 0) {
      return `<span class="status-pill status-pill--danger">异常 ${abnormal}</span>`;
    }
    return '<span class="status-pill status-pill--muted">查看状态</span>';
  }

  function resetAgDashboard() {
    setText("agStatusDashboardTitle", "加载中...");
    setSummaryValue("listener", "-");
    setSummaryValue("ag_status", "-");
    setSummaryValue("cluster_status", "-");
    setSummaryValue("cluster_type", "-");
    setSummaryValue("primary_replica", "-");
    setSummaryValue("last_checked_at", "加载中");
    ["total_databases", "abnormal_databases", "affected_replicas"].forEach((key) => setKpiValue(key, "0"));
    const replicaBody = document.getElementById("agStatusReplicaTableBody");
    if (replicaBody) {
      replicaBody.innerHTML = '<tr><td colspan="7" class="text-muted">加载中...</td></tr>';
    }
    const groups = document.getElementById("agStatusDatabaseGroups");
    if (groups) {
      groups.innerHTML = '<div class="text-muted small">加载中...</div>';
    }
  }

  function renderAgDashboardTabs(items, activeAgId) {
    const tabs = document.getElementById("agStatusDashboardTabs");
    if (!tabs) {
      return;
    }
    const agItems = Array.isArray(items) ? items : [];
    if (!agItems.length) {
      tabs.innerHTML = '<button type="button" class="ag-status-dashboard__tab is-active" data-action="switch-ag-dashboard">暂无 AG</button>';
      return;
    }
    const active = String(activeAgId || agItems[0]?.id || "");
    tabs.innerHTML = agItems
      .map((item) => {
        const agId = String(item.id || "");
        const activeClass = agId === active ? " is-active" : "";
        return (
          `<button type="button" class="ag-status-dashboard__tab${activeClass}" data-action="switch-ag-dashboard" data-ag-id="${escapeHtml(agId)}">` +
          `${escapeHtml(item.name || "-")}` +
          `</button>`
        );
      })
      .join("");
  }

  function renderAgDashboard(data) {
    const summary = data?.summary || {};
    const kpis = data?.kpis || {};
    setText("agStatusDashboardTitle", summary.ag_name || "-");
    setSummaryValue("listener", renderListenerSummary(summary));
    setSummaryValue("ag_status", renderAgDashboardStatus(summary.status));
    setSummaryValue("cluster_status", summary.cluster_status || renderAgDashboardStatus(summary.status));
    setSummaryValue("cluster_type", summary.cluster_type || "-");
    setSummaryValue("primary_replica", summary.primary_replica || "-");
    setSummaryValue("last_checked_at", summary.last_checked_at ? `最近检测 ${formatDate(summary.last_checked_at)}` : "未检测");
    setKpiValue("total_databases", String(Number(kpis.total_databases || 0)));
    setKpiValue("abnormal_databases", String(Number(kpis.abnormal_databases || 0)));
    setKpiValue("affected_replicas", String(Number(kpis.affected_replicas || 0)));
    renderAgReplicaRows(Array.isArray(data?.replicas) ? data.replicas : []);
    renderAgDatabaseGroups(Array.isArray(data?.database_groups) ? data.database_groups : []);
  }

  function renderAgDashboardError(error) {
    setText("agStatusDashboardTitle", "加载失败");
    const replicaBody = document.getElementById("agStatusReplicaTableBody");
    if (replicaBody) {
      replicaBody.innerHTML = `<tr><td colspan="7" class="text-danger">${escapeHtml(resolveErrorMessage(error, "加载失败"))}</td></tr>`;
    }
  }

  function renderListenerSummary(summary) {
    const endpoint = [summary.listener_host, summary.listener_port].filter(Boolean).join(":");
    return [summary.cluster_name, summary.listener_name, endpoint].filter(Boolean).join(" · ") || "-";
  }

  function renderAgDashboardStatus(status) {
    if (status === "failed") {
      return "检测失败";
    }
    if (status === "abnormal") {
      return "异常";
    }
    if (status === "normal") {
      return "正常";
    }
    return "未检测";
  }

  function renderAgReplicaRows(items) {
    const body = document.getElementById("agStatusReplicaTableBody");
    if (!body) {
      return;
    }
    if (!items.length) {
      body.innerHTML = '<tr><td colspan="7" class="text-muted">暂无可用性副本状态</td></tr>';
      return;
    }
    body.innerHTML = items
      .map((item) => {
        const statusClass = item.status === "abnormal" ? "table-danger" : "";
        return (
          `<tr class="${statusClass}">` +
          `<td class="fw-semibold">${escapeHtml(item.replica_server_name || "-")}</td>` +
          `<td>${escapeHtml(item.role_desc || "-")}</td>` +
          `<td>${escapeHtml(item.availability_mode_desc || "-")}</td>` +
          `<td>${escapeHtml(item.failover_mode_desc || "-")}</td>` +
          `<td>${escapeHtml(item.connected_state_desc || "-")}</td>` +
          `<td>${renderSyncHealth(item.synchronization_health_desc, item.status)}</td>` +
          `<td>${escapeHtml(item.error_summary || "-")}</td>` +
          `</tr>`
        );
      })
      .join("");
  }

  function renderAgDatabaseGroups(groups) {
    const container = document.getElementById("agStatusDatabaseGroups");
    if (!container) {
      return;
    }
    if (!groups.length) {
      container.innerHTML = '<div class="text-muted small">暂无数据库状态</div>';
      return;
    }
    container.innerHTML = groups
      .map((group) => {
        const rows = Array.isArray(group.databases) ? group.databases : [];
        const tableRows = rows.map((item) => renderAgDatabaseRow(item)).join("");
        return (
          `<section class="ag-status-dashboard__database-group">` +
          `<div class="ag-status-dashboard__database-group-title">` +
          `<span>${escapeHtml(group.replica_server_name || "-")}</span>` +
          `${renderStatusPill(group.status)}` +
          `</div>` +
          `<div class="table-responsive">` +
          `<table class="table table-sm align-middle mb-0">` +
          `<thead><tr><th>数据库</th><th>同步状态</th><th>健康</th><th>故障转移就绪</th><th>队列</th><th>问题</th></tr></thead>` +
          `<tbody>${tableRows || '<tr><td colspan="6" class="text-muted">暂无数据库状态</td></tr>'}</tbody>` +
          `</table>` +
          `</div>` +
          `</section>`
        );
      })
      .join("");
  }

  function renderAgDatabaseRow(item) {
    const statusClass = item.status === "abnormal" ? "table-danger" : "";
    const queue = `send ${formatNumber(item.log_send_queue_size)} / redo ${formatNumber(item.redo_queue_size)}`;
    return (
      `<tr class="${statusClass}">` +
      `<td class="fw-semibold">${escapeHtml(item.database_name || "-")}</td>` +
      `<td>${escapeHtml(item.synchronization_state_desc || "-")}</td>` +
      `<td>${renderSyncHealth(item.synchronization_health_desc, item.status)}</td>` +
      `<td>${item.failover_ready ? "是" : "否"}</td>` +
      `<td>${escapeHtml(queue)}</td>` +
      `<td>${escapeHtml(item.error_summary || "-")}</td>` +
      `</tr>`
    );
  }

  function renderSyncHealth(value, status) {
    const tone = status === "abnormal" || value === "NOT_HEALTHY" ? "danger" : value ? "success" : "muted";
    return `<span class="status-pill status-pill--${tone}">${escapeHtml(value || "未采集")}</span>`;
  }

  function renderStatusPill(status) {
    const tone = status === "abnormal" ? "danger" : status === "normal" ? "success" : "muted";
    const label = status === "abnormal" ? "异常" : status === "normal" ? "正常" : "未检测";
    return `<span class="status-pill status-pill--${tone}">${label}</span>`;
  }

  function formatNumber(value) {
    return value === null || value === undefined ? "-" : String(Number(value || 0));
  }

  function setSummaryValue(key, value) {
    const node = document.querySelector(`[data-ag-status-summary="${key}"]`);
    if (node) {
      node.textContent = value;
    }
  }

  function setKpiValue(key, value) {
    const node = document.querySelector(`[data-ag-status-kpi="${key}"]`);
    if (node) {
      node.textContent = value;
    }
  }

  function setText(id, value) {
    const node = document.getElementById(id);
    if (node) {
      node.textContent = value;
    }
  }

  function openMySQLCreateModal() {
    setMySQLModalMode("create");
    fillMySQLBasic({});
    setSelectedMySQLInstances([]);
    renderMySQLTopologyTable([]);
    mysqlModal?.show();
  }

  function openMySQLEditor(clusterId) {
    if (!clusterId) {
      return;
    }
    mysqlStore.actions
      .load(clusterId)
      .then((detail) => {
        setMySQLModalMode("edit");
        fillMySQLBasic(detail.cluster || {});
        setSelectedMySQLInstances((detail.instances || []).map((item) => String(item.instance_id || item.id)));
        renderMySQLTopologyTable(detail.instances || []);
        mysqlModal?.show();
      })
      .catch((error) => showError(error, "加载 MySQL 群集失败"));
  }

  function setMySQLModalMode(mode) {
    const form = document.getElementById("mysqlClusterManagementForm");
    if (form) {
      form.dataset.formMode = mode;
    }
    document.getElementById("mysqlClusterModalTitle").textContent = mode === "create" ? "添加 MySQL 群集" : "管理 MySQL 群集";
    document.getElementById("mysqlClusterModalSubmit").textContent = mode === "create" ? "添加群集" : "保存";
  }

  function fillMySQLBasic(cluster) {
    document.getElementById("mysqlClusterIdInput").value = cluster.id || "";
    document.getElementById("mysqlClusterNameInput").value = cluster.name || "";
    document.getElementById("mysqlClusterTopologyTypeInput").value = cluster.topology_type || "replication";
    document.getElementById("mysqlClusterDescriptionInput").value = cluster.description || "";
    document.getElementById("mysqlClusterEnabledInput").checked = cluster.is_enabled !== false;
  }

  function setSelectedMySQLInstances(instanceIds) {
    const select = document.getElementById("mysqlClusterInstanceSelect");
    if (!select) {
      return;
    }
    Array.from(select.options).forEach((option) => {
      option.selected = instanceIds.includes(option.value);
    });
  }

  function getSelectedMySQLInstances() {
    const select = document.getElementById("mysqlClusterInstanceSelect");
    if (!select) {
      return [];
    }
    return Array.from(select.selectedOptions).map((option) => Number(option.value)).filter(Boolean);
  }

  function buildMySQLClusterPayload() {
    return {
      name: document.getElementById("mysqlClusterNameInput").value.trim(),
      topology_type: document.getElementById("mysqlClusterTopologyTypeInput").value || "replication",
      description: document.getElementById("mysqlClusterDescriptionInput").value.trim(),
      is_enabled: document.getElementById("mysqlClusterEnabledInput").checked,
    };
  }

  function saveMySQLCluster() {
    const form = document.getElementById("mysqlClusterManagementForm");
    const mode = form?.dataset.formMode || "create";
    const payload = buildMySQLClusterPayload();
    if (!payload.name) {
      showToast("warning", "请输入 MySQL 群集名称");
      return;
    }
    const run =
      mode === "create"
        ? mysqlStore.actions.create(payload).then((response) => response?.data?.cluster)
        : mysqlStore.actions.update(document.getElementById("mysqlClusterIdInput").value, payload).then((response) => response?.data?.cluster);

    run
      .then((cluster) => {
        if (!cluster?.id) {
          throw new Error("保存 MySQL 群集失败");
        }
        return mysqlStore.actions.replaceInstances(cluster.id, getSelectedMySQLInstances()).then(() => cluster);
      })
      .then(() => {
        showToast("success", "MySQL 群集已保存");
        mysqlModal?.hide();
        mysqlGridWrapper?.refresh?.();
      })
      .catch((error) => showError(error, "保存 MySQL 群集失败"));
  }

  function syncMySQLTopologyFromRow(trigger) {
    const clusterId = trigger?.getAttribute("data-cluster-id");
    syncMySQLTopology(trigger, clusterId);
  }

  function syncMySQLTopology(trigger, explicitClusterId) {
    const clusterId = explicitClusterId || document.getElementById("mysqlClusterIdInput").value;
    if (!clusterId) {
      showToast("warning", "请先保存 MySQL 群集后同步主从信息");
      return;
    }
    setButtonLoading(trigger, true);
    mysqlStore.actions
      .syncTopology(clusterId)
      .then(() => mysqlStore.actions.load(clusterId))
      .then((detail) => {
        renderMySQLTopologyTable(detail.instances || []);
        showToast("success", "MySQL 主从信息同步完成");
        mysqlGridWrapper?.refresh?.();
      })
      .catch((error) => showError(error, "同步 MySQL 主从信息失败"))
      .finally(() => setButtonLoading(trigger, false));
  }

  function renderMySQLTopologyTable(items) {
    const body = document.getElementById("mysqlClusterTopologyTableBody");
    if (!body) {
      return;
    }
    if (!items.length) {
      body.innerHTML = '<tr><td colspan="7" class="text-muted">暂无主从状态</td></tr>';
      return;
    }
    body.innerHTML = items
      .map((item) => {
        const source = item.source_host ? `${item.source_host}:${item.source_port || 3306}` : "-";
        const lag = item.seconds_behind_source === null || item.seconds_behind_source === undefined ? "-" : `${item.seconds_behind_source}s`;
        const reason = item.last_error || "-";
        return (
          `<tr>` +
          `<td>${escapeHtml(item.name || "-")}</td>` +
          `<td>${escapeHtml(item.replication_role || "unknown")}</td>` +
          `<td>${renderSyncStatus(item.replication_status || "unknown")}</td>` +
          `<td>${escapeHtml(source)}</td>` +
          `<td>${escapeHtml(lag)}</td>` +
          `<td class="mysql-cluster-topology-reason">${escapeHtml(reason)}</td>` +
          `<td>${escapeHtml(item.last_checked_at ? formatDate(item.last_checked_at) : "-")}</td>` +
          `</tr>`
        );
      })
      .join("");
  }

  function renderAccountCredentialSelect(item) {
    const selectedId = item.account_credential_id ? String(item.account_credential_id) : "";
    const options = [
      '<option value="">请选择凭据</option>',
      ...credentialOptions.map((credential) => {
        const value = String(credential.id || "");
        const selected = value && value === selectedId ? " selected" : "";
        return `<option value="${escapeHtml(value)}"${selected}>${escapeHtml(credential.name || "-")}</option>`;
      }),
    ];
    const disabled = !canManage ? " disabled" : "";
    return (
      `<select class="form-select form-select-sm" data-action="update-ag-account-credential" ` +
      `data-ag-id="${escapeHtml(String(item.id || ""))}"${disabled}>${options.join("")}</select>`
    );
  }

  function renderCollectionToggle(item) {
    const enabled = item.is_enabled === true;
    const canEnable = Boolean(item.contained_enabled && item.account_credential_id);
    const disabled = !canManage || (!enabled && !canEnable);
    const disabledAttr = disabled ? " disabled" : "";
    const title = !item.contained_enabled
      ? "非 contained AG 不允许启用采集"
      : !item.account_credential_id
        ? "请选择账户采集凭据后启用"
        : "";
    const tone = enabled ? "success" : "muted";
    const label = enabled ? "启用" : "停用";
    return (
      `<button type="button" class="status-pill status-pill--${tone} border-0" ` +
      `data-action="toggle-ag-collection" data-ag-id="${escapeHtml(String(item.id || ""))}"` +
      `${disabledAttr} title="${escapeHtml(title)}">${label}</button>`
    );
  }

  function findCurrentAg(agId) {
    return currentAgItems.find((item) => String(item.id) === String(agId)) || null;
  }

  function resolveFirstBoundInstanceId(cluster) {
    const ids = Array.isArray(cluster?.bound_instance_ids) ? cluster.bound_instance_ids : [];
    return ids.length ? ids[0] : "";
  }

  function updateAgAccountCredential(select) {
    const clusterId = document.getElementById("clusterIdInput").value;
    const agId = select.getAttribute("data-ag-id");
    if (!clusterId || !agId) {
      return;
    }
    const credentialId = Number(select.value || 0);
    const payload = {
      account_credential_id: credentialId || null,
    };
    if (!credentialId) {
      payload.is_enabled = false;
    }
    select.disabled = true;
    store.actions
      .updateAvailabilityGroup(clusterId, agId, payload)
      .then(() => store.actions.load(clusterId))
      .then((detail) => {
        renderAgTable(detail.availability_groups || []);
        showToast("success", "AG 账户采集凭据已更新");
      })
      .catch((error) => showError(error, "更新 AG 账户采集凭据失败"))
      .finally(() => {
        select.disabled = false;
      });
  }

  function toggleAgCollection(button) {
    const clusterId = document.getElementById("clusterIdInput").value;
    const agId = button.getAttribute("data-ag-id");
    const item = findCurrentAg(agId);
    if (!clusterId || !agId || !item) {
      return;
    }
    if (!item.contained_enabled) {
      showToast("warning", "非 contained AG 不允许启用采集");
      return;
    }
    if (!item.account_credential_id && !item.is_enabled) {
      showToast("warning", "请选择账户采集凭据后启用");
      return;
    }
    setButtonLoading(button, true);
    store.actions
      .updateAvailabilityGroup(clusterId, agId, { is_enabled: !item.is_enabled })
      .then(() => store.actions.load(clusterId))
      .then((detail) => {
        renderAgTable(detail.availability_groups || []);
        showToast("success", "AG 采集状态已更新");
      })
      .catch((error) => showError(error, "更新 AG 采集状态失败"))
      .finally(() => setButtonLoading(button, false));
  }

  function renderBoolean(value) {
    return value
      ? '<span class="status-pill status-pill--success">是</span>'
      : '<span class="status-pill status-pill--muted">否</span>';
  }

  function renderStatus(value) {
    return value
      ? '<span class="status-pill status-pill--success">启用</span>'
      : '<span class="status-pill status-pill--muted">停用</span>';
  }

  function renderSyncStatus(value) {
    const tone = value === "failed" ? "danger" : value === "completed" ? "success" : "muted";
    return `<span class="status-pill status-pill--${tone}">${escapeHtml(value || "未同步")}</span>`;
  }

  function renderSQLServerDatabaseStatusSummary(cluster) {
    const checkedAt = cluster.last_status_sync_at ? `<small class="text-muted ms-2">${escapeHtml(formatDate(cluster.last_status_sync_at))}</small>` : "";
    const status = cluster.last_status_sync_status || "";
    if (!cluster.last_status_sync_at && !status) {
      return '<span class="status-pill status-pill--muted">未检测</span>';
    }
    if (status === "failed") {
      const errorTitle = cluster.last_status_sync_error ? ` title="${escapeHtml(cluster.last_status_sync_error)}"` : "";
      return `<span class="status-pill status-pill--danger"${errorTitle}>检测失败</span>${checkedAt}`;
    }
    const abnormal = Number(cluster.ag_database_sync_abnormal_count || 0);
    if (abnormal > 0) {
      return `<span class="status-pill status-pill--danger">异常 ${abnormal}</span>${checkedAt}`;
    }
    return `<span class="status-pill status-pill--success">正常</span>${checkedAt}`;
  }

  function renderMySQLTopologySummary(cluster) {
    const status = cluster.last_topology_sync_status || "";
    const checkedAt = cluster.last_topology_sync_at ? `<small class="text-muted ms-2">${escapeHtml(formatDate(cluster.last_topology_sync_at))}</small>` : "";
    if (!cluster.last_topology_sync_at && !status) {
      return `<span class="status-pill status-pill--muted">未检测</span>`;
    }
    if (status === "failed") {
      return `<span class="status-pill status-pill--danger">检测失败</span>${checkedAt}`;
    }
    const abnormal = Number(cluster.abnormal_replica_count || 0);
    if (abnormal > 0) {
      return `<span class="status-pill status-pill--danger">异常 ${abnormal}</span>${checkedAt}`;
    }
    return `<span class="status-pill status-pill--success">正常</span>${checkedAt}`;
  }

  function renderMySQLLagSummary(cluster) {
    if (!cluster.last_topology_sync_at) {
      return "-";
    }
    const replicaCount = Number(cluster.replica_count || 0);
    if (replicaCount <= 0) {
      return "-";
    }
    if (cluster.max_replica_lag_seconds === null || cluster.max_replica_lag_seconds === undefined) {
      return Number(cluster.unknown_replica_lag_count || 0) > 0 ? "未知" : "-";
    }
    return `${Number(cluster.max_replica_lag_seconds)}s`;
  }

  function formatDate(value) {
    if (global.timeUtils?.formatDateTime) {
      return global.timeUtils.formatDateTime(value);
    }
    return value;
  }

  function showToast(type, message) {
    const toast = global.toast;
    if (!toast) {
      return;
    }
    if (type === "success" && typeof toast.success === "function") {
      toast.success(message);
    } else if (type === "warning" && typeof toast.warning === "function") {
      toast.warning(message);
    } else if (typeof toast.error === "function") {
      toast.error(message);
    }
  }

  function showError(error, fallback) {
    const message = resolveErrorMessage(error, fallback);
    showToast("error", message);
  }

  function setButtonLoading(button, loading) {
    if (!button) {
      return;
    }
    button.disabled = loading;
    if (loading) {
      button.dataset.originalText = button.innerHTML;
      button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>同步中';
      return;
    }
    if (button.dataset.originalText) {
      button.innerHTML = button.dataset.originalText;
      delete button.dataset.originalText;
    }
  }

  function parseJsonDataset(raw, fallback) {
    if (!raw) {
      return fallback;
    }
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : fallback;
    } catch (error) {
      console.warn("解析群集管理页面数据失败:", error);
      return fallback;
    }
  }
}

mountClusterPage(window);
