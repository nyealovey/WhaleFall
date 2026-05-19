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
  let currentDetail = null;
  let pendingAgDrafts = [];
  const canManage = pageRoot.dataset.canManage === "true";

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
        name: "状态",
        id: "is_enabled",
        formatter: (value) => renderStatus(value),
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
          return gridHtml(
            `<button type="button" class="btn btn-sm btn-outline-primary" data-action="edit-cluster" data-cluster-id="${escapeHtml(String(meta.id || ""))}">` +
              `<i class="fas fa-pen me-1"></i>管理` +
              `</button>`
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
    document.querySelector('[data-action="save-ag-draft"]')?.addEventListener("click", () => {
      saveAgDraft();
    });
    document.getElementById("clusterAgTableBody")?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-action]");
      if (!button) {
        return;
      }
      if (button.dataset.action === "edit-ag") {
        populateAgForm(findAg(button.getAttribute("data-ag-id")));
      }
      if (button.dataset.action === "disable-ag") {
        disableAg(button.getAttribute("data-ag-id"));
      }
    });
  }

  function openCreateModal() {
    currentDetail = null;
    pendingAgDrafts = [];
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
        currentDetail = detail;
        pendingAgDrafts = [];
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
    clearAgForm();
  }

  function fillBasic(cluster) {
    document.getElementById("clusterIdInput").value = cluster.id || "";
    document.getElementById("clusterNameInput").value = cluster.name || "";
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
      .then((cluster) => {
        if (!pendingAgDrafts.length) {
          return cluster;
        }
        return pendingAgDrafts
          .reduce(
            (chain, agPayload) => chain.then(() => store.actions.createAvailabilityGroup(cluster.id, agPayload)),
            Promise.resolve()
          )
          .then(() => cluster);
      })
      .then(() => {
        showToast("success", "cluster 已保存");
        modal?.hide();
        gridWrapper?.refresh?.();
      })
      .catch((error) => showError(error, "保存 cluster 失败"));
  }

  function saveAgDraft() {
    const payload = buildAgPayload();
    if (!payload.name || !payload.listener_host) {
      showToast("warning", "请输入 AG 名称和监听器 host");
      return;
    }
    const clusterId = document.getElementById("clusterIdInput").value;
    const agId = document.getElementById("clusterAgIdInput").value;
    if (!clusterId) {
      const draft = { ...payload, id: `draft-${Date.now()}` };
      pendingAgDrafts.push(payload);
      renderAgTable([...(currentDetail?.availability_groups || []), ...pendingAgDrafts.map((item, index) => ({ ...item, id: `draft-${index}` }))]);
      clearAgForm();
      showToast("success", "AG 已加入待保存列表");
      return draft;
    }

    const action = agId
      ? store.actions.updateAvailabilityGroup(clusterId, agId, payload)
      : store.actions.createAvailabilityGroup(clusterId, payload);
    action
      .then(() => store.actions.load(clusterId))
      .then((detail) => {
        currentDetail = detail;
        renderAgTable(detail.availability_groups || []);
        clearAgForm();
        showToast("success", "AG 已保存");
        gridWrapper?.refresh?.();
      })
      .catch((error) => showError(error, "保存 AG 失败"));
  }

  function buildAgPayload() {
    const credentialId = document.getElementById("clusterAgCredentialInput").value;
    return {
      name: document.getElementById("clusterAgNameInput").value.trim(),
      listener_name: document.getElementById("clusterAgListenerNameInput").value.trim(),
      listener_host: document.getElementById("clusterAgHostInput").value.trim(),
      listener_port: Number(document.getElementById("clusterAgPortInput").value || 1433),
      credential_id: credentialId ? Number(credentialId) : null,
      connection_database: document.getElementById("clusterAgDatabaseInput").value.trim(),
      contained_enabled: document.getElementById("clusterAgContainedInput").checked,
      is_enabled: document.getElementById("clusterAgEnabledInput").checked,
    };
  }

  function populateAgForm(ag) {
    if (!ag) {
      return;
    }
    document.getElementById("clusterAgIdInput").value = ag.id || "";
    document.getElementById("clusterAgNameInput").value = ag.name || "";
    document.getElementById("clusterAgListenerNameInput").value = ag.listener_name || "";
    document.getElementById("clusterAgHostInput").value = ag.listener_host || "";
    document.getElementById("clusterAgPortInput").value = ag.listener_port || 1433;
    document.getElementById("clusterAgCredentialInput").value = ag.credential_id || "";
    document.getElementById("clusterAgDatabaseInput").value = ag.connection_database || "";
    document.getElementById("clusterAgContainedInput").checked = ag.contained_enabled === true;
    document.getElementById("clusterAgEnabledInput").checked = ag.is_enabled !== false;
  }

  function clearAgForm() {
    ["clusterAgIdInput", "clusterAgNameInput", "clusterAgListenerNameInput", "clusterAgHostInput", "clusterAgDatabaseInput"].forEach((id) => {
      document.getElementById(id).value = "";
    });
    document.getElementById("clusterAgPortInput").value = "1433";
    document.getElementById("clusterAgCredentialInput").value = "";
    document.getElementById("clusterAgContainedInput").checked = false;
    document.getElementById("clusterAgEnabledInput").checked = true;
  }

  function disableAg(agId) {
    const clusterId = document.getElementById("clusterIdInput").value;
    if (!clusterId || !agId) {
      return;
    }
    store.actions
      .updateAvailabilityGroup(clusterId, agId, { is_enabled: false })
      .then(() => store.actions.load(clusterId))
      .then((detail) => {
        currentDetail = detail;
        renderAgTable(detail.availability_groups || []);
        gridWrapper?.refresh?.();
      })
      .catch((error) => showError(error, "停用 AG 失败"));
  }

  function findAg(agId) {
    return (currentDetail?.availability_groups || []).find((item) => String(item.id) === String(agId));
  }

  function renderAgTable(items) {
    const body = document.getElementById("clusterAgTableBody");
    if (!body) {
      return;
    }
    if (!items.length) {
      body.innerHTML = '<tr><td colspan="7" class="text-muted">暂无 AG 配置</td></tr>';
      return;
    }
    body.innerHTML = items.map((item) => renderAgRow(item)).join("");
  }

  function renderAgRow(item) {
    const listener = [item.listener_name, item.listener_host].filter(Boolean).join(" / ") || "-";
    const syncLabel = item.last_sync_status || "未同步";
    const actions = String(item.id || "").startsWith("draft-")
      ? '<span class="text-muted small">待保存</span>'
      : `<button type="button" class="btn btn-sm btn-outline-secondary" data-action="edit-ag" data-ag-id="${escapeHtml(String(item.id))}" title="编辑 AG"><i class="fas fa-pen"></i></button>` +
        `<button type="button" class="btn btn-sm btn-outline-danger ms-1" data-action="disable-ag" data-ag-id="${escapeHtml(String(item.id))}" title="停用 AG"><i class="fas fa-ban"></i></button>`;
    return `
      <tr>
        <td>${escapeHtml(item.name || "-")}</td>
        <td>${escapeHtml(listener)}</td>
        <td>${escapeHtml(item.credential_name || "沿用实例凭据")}</td>
        <td>${renderBoolean(item.contained_enabled)}</td>
        <td>${renderStatus(item.is_enabled)}</td>
        <td>${escapeHtml(syncLabel)}</td>
        <td class="text-end cluster-ag-actions">${actions}</td>
      </tr>
    `;
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
}

mountClusterPage(window);
