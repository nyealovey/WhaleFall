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
    console.error("cluster 页面依赖未加载");
    return;
  }
  if (typeof escapeHtml !== "function" || typeof resolveErrorMessage !== "function" || !rowMeta?.get) {
    console.error("cluster 页面 UI helpers 未加载");
    return;
  }

  const pageRoot = document.getElementById("cluster-page-root");
  if (!pageRoot) {
    return;
  }

  const SQLServerClustersService = global.SQLServerClustersService;
  const createStore = global.createSQLServerClustersStore;
  if (!SQLServerClustersService || typeof createStore !== "function") {
    console.error("SQLServerClustersService 或 store 未加载");
    return;
  }

  const gridHtml = gridjs.html;
  const { ready } = helpers;
  let store = null;
  let gridWrapper = null;
  let modal = null;
  let modalEl = null;
  let currentAgItems = [];
  const canManage = pageRoot.dataset.canManage === "true";
  const credentialOptions = parseJsonDataset(pageRoot.dataset.credentials, []);

  ready(() => {
    store = createStore({
      service: new SQLServerClustersService(),
      emitter: global.mitt ? global.mitt() : null,
    });
    modalEl = document.getElementById("clusterManagementModal");
    modal = modalEl && global.bootstrap?.Modal ? new global.bootstrap.Modal(modalEl) : null;
    bindModalEvents();
    bindCreateButton();
    initializeGrid();
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
              `<small class="text-muted">${escapeHtml(meta.description || "SQL Server cluster")}</small>`
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
      item,
    ]);
  }

  function bindCreateButton() {
    pageRoot.querySelector('[data-action="create-cluster"]')?.addEventListener("click", () => {
      openCreateModal();
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
    document.getElementById("clusterAgTableBody")?.addEventListener("change", (event) => {
      const target = event.target;
      if (target?.matches?.('[data-action="update-ag-account-credential"]')) {
        updateAgAccountCredential(target);
      }
    });
    document.getElementById("clusterAgTableBody")?.addEventListener("click", (event) => {
      const target = event.target?.closest?.('[data-action="toggle-ag-collection"]');
      if (target) {
        event.preventDefault();
        toggleAgCollection(target);
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
        showToast("success", "cluster 已保存");
        modal?.hide();
        gridWrapper?.refresh?.();
      })
      .catch((error) => showError(error, "保存 cluster 失败"));
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
      body.innerHTML = '<tr><td colspan="7" class="text-muted">暂无 AG 配置</td></tr>';
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
      </tr>
    `;
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
      console.warn("解析 cluster 页面数据失败:", error);
      return fallback;
    }
  }
}

mountClusterPage(window);
