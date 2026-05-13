(function mountVeeamSourcePage(global) {
  "use strict";

  const pageRoot = document.getElementById("veeam-source-page");
  if (!pageRoot) {
    return;
  }

  const toast = global.toast;
  const csrfToken = document.getElementById("veeam-source-csrf-token")?.value || "";
  const apiUrl = pageRoot.dataset.apiUrl;
  const sourcesApiUrl = pageRoot.dataset.sourcesApiUrl;
  const syncApiUrl = pageRoot.dataset.syncApiUrl;
  const service = new global.VeeamSourceService(apiUrl, syncApiUrl, sourcesApiUrl);
  const setButtonLoading = global.UI?.setButtonLoading;
  const clearButtonLoading = global.UI?.clearButtonLoading;

  const elements = {
    sourceName: document.getElementById("veeamSourceName"),
    formTitle: document.getElementById("veeamSourceFormTitle"),
    credentialId: document.getElementById("veeamCredentialId"),
    serverHost: document.getElementById("veeamServerHost"),
    serverPort: document.getElementById("veeamServerPort"),
    apiVersion: document.getElementById("veeamApiVersion"),
    verifySsl: document.getElementById("veeamVerifySsl"),
    matchDomains: document.getElementById("veeamMatchDomains"),
    providerStatus: document.getElementById("veeamProviderStatus"),
    bindingSummary: document.getElementById("veeamBindingSummary"),
    syncStatusSummary: document.getElementById("veeamSyncStatusSummary"),
    sourcesList: document.getElementById("veeamSourcesList"),
    saveButton: document.getElementById("saveVeeamSourceBtn"),
    unbindButton: document.getElementById("unbindVeeamSourceBtn"),
    cancelEditButton: document.getElementById("cancelEditVeeamSourceBtn"),
    syncButton: document.getElementById("syncVeeamBackupsBtn"),
  };
  const state = {
    editingSourceId: null,
    sources: [],
    lastPayload: null,
  };

  function setButtonBusy(button, loadingText) {
    const hasHelpers = typeof setButtonLoading === "function" && typeof clearButtonLoading === "function";
    if (hasHelpers) {
      setButtonLoading(button, { loadingText });
      return function stop() {
        clearButtonLoading(button);
      };
    }

    const originalHtml = button.innerHTML;
    button.disabled = true;
    button.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>${loadingText}`;
    return function stop() {
      button.disabled = false;
      button.innerHTML = originalHtml;
    };
  }

  function linesToDomains(value) {
    return String(value || "")
      .split("\n")
      .map((item) => item.trim().replace(/^\.+|\.+$/g, "").toLowerCase())
      .filter(Boolean)
      .filter((item, index, list) => list.indexOf(item) === index);
  }

  function domainsToLines(domains) {
    return Array.isArray(domains) ? domains.join("\n") : "";
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function renderCredentialOptions(options, selectedId) {
    if (!(elements.credentialId instanceof HTMLSelectElement)) {
      return;
    }
    const items = Array.isArray(options) ? options : [];
    const optionHtml = ['<option value="">请选择 Veeam 凭据</option>']
      .concat(
        items.map((item) => {
          const selected = Number(item?.id) === Number(selectedId) ? "selected" : "";
          const label = item?.description
            ? `${item?.name || "未命名凭据"} · ${item.description}`
            : `${item?.name || "未命名凭据"}`;
          return `<option value="${String(item?.id || "")}" ${selected}>${label}</option>`;
        }),
      )
      .join("");
    elements.credentialId.innerHTML = optionHtml;
  }

  function fillPage(payload) {
    state.lastPayload = payload || {};
    state.sources = Array.isArray(payload?.sources) ? payload.sources : [];
    const binding =
      state.editingSourceId !== null
        ? state.sources.find((item) => Number(item?.id) === Number(state.editingSourceId)) || null
        : payload?.binding || state.sources[0] || null;
    const selectedId = binding?.credential_id || binding?.credential?.id || "";
    renderCredentialOptions(payload?.veeam_credentials, selectedId);
    if (elements.sourceName) {
      elements.sourceName.value = binding?.name || "";
    }
    if (elements.formTitle) {
      elements.formTitle.textContent = binding && state.editingSourceId !== null ? "编辑数据源" : "新增数据源";
    }
    if (elements.serverHost) {
      elements.serverHost.value = binding?.server_host || "";
    }
    if (elements.serverPort) {
      elements.serverPort.value = binding?.server_port || payload?.default_port || 9419;
    }
    if (elements.apiVersion) {
      elements.apiVersion.value = binding?.api_version || payload?.default_api_version || "v1.2-rev0";
    }
    if (elements.verifySsl instanceof HTMLInputElement) {
      if (typeof binding?.verify_ssl === "boolean") {
        elements.verifySsl.checked = binding.verify_ssl;
      } else {
        elements.verifySsl.checked = Boolean(payload?.default_verify_ssl ?? true);
      }
    }
    if (elements.matchDomains) {
      elements.matchDomains.value = domainsToLines(binding?.match_domains || payload?.default_match_domains || []);
    }
    if (elements.providerStatus) {
      elements.providerStatus.textContent = payload?.provider_ready ? "Provider 已接入" : "Provider 待接入";
    }
    if (elements.bindingSummary) {
      if (!state.sources.length) {
        elements.bindingSummary.textContent = "当前未配置 Veeam 数据源";
      } else {
        const enabledCount = state.sources.filter((item) => item?.is_enabled).length;
        elements.bindingSummary.textContent = `${state.sources.length} 个数据源 · ${enabledCount} 个启用`;
      }
    }
    if (elements.syncStatusSummary) {
      if (!state.sources.length) {
        elements.syncStatusSummary.textContent = "未执行同步";
      } else {
        const latest = state.sources
          .filter((item) => item?.last_sync_at)
          .sort((a, b) => String(b.last_sync_at).localeCompare(String(a.last_sync_at)))[0];
        const failedCount = state.sources.filter((item) => item?.last_sync_status === "failed").length;
        const status = failedCount > 0 ? `${failedCount} 个失败` : latest?.last_sync_status || "未执行同步";
        elements.syncStatusSummary.textContent = `${status} · ${latest?.last_sync_at || "-"}`;
      }
    }
    if (elements.unbindButton) {
      elements.unbindButton.disabled = state.editingSourceId === null;
    }
    if (elements.syncButton) {
      elements.syncButton.disabled = !state.sources.some((item) => item?.is_enabled) || !payload?.provider_ready;
      elements.syncButton.title = payload?.provider_ready ? "同步 Veeam 备份" : "Veeam Provider 待接入";
    }
    renderSourcesList();
  }

  function renderSourcesList() {
    const container = elements.sourcesList;
    if (!container) {
      return;
    }
    const tbody = container.querySelector("tbody");
    if (!tbody) {
      return;
    }
    if (!state.sources.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-muted">当前未配置 Veeam 数据源</td></tr>';
      return;
    }
    tbody.innerHTML = state.sources
      .map((source) => {
        const sourceId = Number(source?.id || 0);
        const statusText = source?.is_enabled ? "启用" : "停用";
        const statusClass = source?.is_enabled ? "text-success" : "text-muted";
        const syncText = source?.last_sync_status
          ? `${escapeHtml(source.last_sync_status)} · ${escapeHtml(source.last_sync_at || "-")}`
          : "未执行";
        const credentialName = source?.credential?.name || "-";
        return `
          <tr data-source-id="${sourceId}">
            <td><strong>${escapeHtml(source?.name || "未命名 Veeam")}</strong></td>
            <td>${escapeHtml(source?.server_host || "-")}:${escapeHtml(source?.server_port || "-")}</td>
            <td>${escapeHtml(credentialName)}</td>
            <td><span class="${statusClass}">${statusText}</span></td>
            <td>${syncText}</td>
            <td class="text-end">
              <button class="btn btn-sm btn-outline-secondary" type="button" data-veeam-source-action="edit" data-source-id="${sourceId}">编辑</button>
              <button class="btn btn-sm btn-outline-secondary" type="button" data-veeam-source-action="${source?.is_enabled ? "disable" : "enable"}" data-source-id="${sourceId}">
                ${source?.is_enabled ? "停用" : "启用"}
              </button>
            </td>
          </tr>
        `;
      })
      .join("");
  }

  function resetForm(payload) {
    state.editingSourceId = null;
    renderCredentialOptions(payload?.veeam_credentials || state.lastPayload?.veeam_credentials, "");
    if (elements.sourceName) {
      elements.sourceName.value = "";
    }
    if (elements.serverHost) {
      elements.serverHost.value = "";
    }
    if (elements.serverPort) {
      elements.serverPort.value = payload?.default_port || state.lastPayload?.default_port || 9419;
    }
    if (elements.apiVersion) {
      elements.apiVersion.value =
        payload?.default_api_version || state.lastPayload?.default_api_version || "v1.2-rev0";
    }
    if (elements.verifySsl instanceof HTMLInputElement) {
      elements.verifySsl.checked = Boolean(
        payload?.default_verify_ssl ?? state.lastPayload?.default_verify_ssl ?? true,
      );
    }
    if (elements.matchDomains) {
      elements.matchDomains.value = domainsToLines(
        payload?.default_match_domains || state.lastPayload?.default_match_domains || [],
      );
    }
    if (elements.formTitle) {
      elements.formTitle.textContent = "新增数据源";
    }
    if (elements.unbindButton) {
      elements.unbindButton.disabled = true;
    }
  }

  async function loadSource() {
    const response = await service.load();
    if (!response?.success) {
      throw new Error(response?.message || "加载 Veeam 数据源失败");
    }
    fillPage(response.data || {});
  }

  async function handleSaveBinding(event) {
    event.preventDefault();
    const credentialId = Number(elements.credentialId?.value || 0);
    const name = String(elements.sourceName?.value || "").trim();
    const serverHost = String(elements.serverHost?.value || "").trim();
    const serverPort = Number(elements.serverPort?.value || 0);
    const apiVersion = String(elements.apiVersion?.value || "").trim();
    const verifySsl = elements.verifySsl instanceof HTMLInputElement ? elements.verifySsl.checked : true;
    const matchDomains = linesToDomains(elements.matchDomains?.value || "");

    if (!credentialId) {
      toast?.error?.("请选择 Veeam 凭据");
      return;
    }
    if (!serverHost) {
      toast?.error?.("请输入 Veeam IP");
      return;
    }
    if (!serverPort) {
      toast?.error?.("请输入端口");
      return;
    }
    if (!apiVersion) {
      toast?.error?.("请输入 API 版本");
      return;
    }

    const stop = setButtonBusy(elements.saveButton, "保存中...");
    try {
      const payload = {
        name,
        credential_id: credentialId,
        server_host: serverHost,
        server_port: serverPort,
        api_version: apiVersion,
        verify_ssl: verifySsl,
        match_domains: matchDomains,
      };
      const response = state.editingSourceId
        ? await service.updateSource(state.editingSourceId, payload, csrfToken)
        : await service.createSource(payload, csrfToken);
      if (!response?.success) {
        throw new Error(response?.message || "保存 Veeam 数据源失败");
      }
      fillPage(response.data || {});
      toast?.success?.("Veeam 数据源保存成功");
    } catch (error) {
      toast?.error?.(error?.message || "保存 Veeam 数据源失败");
    } finally {
      stop();
    }
  }

  async function handleUnbindSource() {
    if (state.editingSourceId === null) {
      toast?.error?.("请先选择要删除的数据源");
      return;
    }
    const stop = setButtonBusy(elements.unbindButton, "解绑中...");
    try {
      const response = await service.deleteSource(state.editingSourceId, csrfToken);
      if (!response?.success) {
        throw new Error(response?.message || "解绑数据源失败");
      }
      state.editingSourceId = null;
      fillPage(response.data || {});
      toast?.success?.("解绑 Veeam 数据源成功");
    } catch (error) {
      toast?.error?.(error?.message || "解绑 Veeam 数据源失败");
    } finally {
      stop();
    }
  }

  async function handleSourcesListClick(event) {
    const target = event.target instanceof Element ? event.target.closest("[data-veeam-source-action]") : null;
    if (!target) {
      return;
    }
    const sourceId = Number(target.getAttribute("data-source-id") || 0);
    const action = target.getAttribute("data-veeam-source-action");
    const source = state.sources.find((item) => Number(item?.id) === sourceId);
    if (!source) {
      return;
    }
    if (action === "edit") {
      state.editingSourceId = sourceId;
      fillPage(state.lastPayload || {});
      return;
    }
    if (action !== "enable" && action !== "disable") {
      return;
    }
    const stop = setButtonBusy(target, action === "enable" ? "启用中..." : "停用中...");
    try {
      const response = await service.setSourceEnabled(sourceId, action === "enable", csrfToken);
      if (!response?.success) {
        throw new Error(response?.message || "更新数据源状态失败");
      }
      fillPage(response.data || {});
      toast?.success?.(action === "enable" ? "Veeam 数据源已启用" : "Veeam 数据源已停用");
    } catch (error) {
      toast?.error?.(error?.message || "更新数据源状态失败");
    } finally {
      stop();
    }
  }

  async function handleSyncBackups() {
    const stop = setButtonBusy(elements.syncButton, "同步中...");
    try {
      const result = await service.syncBackups(csrfToken);
      const resolver = global.UI?.resolveAsyncActionOutcome;
      const outcome =
        typeof resolver === "function"
          ? resolver(result, {
              action: "veeam:syncBackups",
              startedMessage: "Veeam 备份同步任务已启动",
              failedMessage: "同步 Veeam 备份失败",
              unknownMessage: "Veeam 备份同步未完成，请稍后在运行中心确认",
              resultUrl: "/history/sessions",
              resultText: "前往运行中心查看同步进度",
            })
          : null;

      const fallbackStatus =
        result?.success === true
          ? "started"
          : result?.success === false || result?.error === true
            ? "failed"
            : "unknown";
      const fallbackOutcome = {
        status: fallbackStatus,
        tone:
          fallbackStatus === "started"
            ? "success"
            : fallbackStatus === "failed"
              ? "error"
              : "warning",
        message:
          fallbackStatus === "started"
            ? result?.message || "Veeam 备份同步任务已启动"
            : fallbackStatus === "failed"
              ? result?.message || "同步 Veeam 备份失败"
              : result?.message || "Veeam 备份同步未完成，请稍后在运行中心确认",
      };

      const resolved = outcome || fallbackOutcome;
      const warnOrInfo = toast?.warning || toast?.info;
      const notifier =
        resolved.tone === "success"
          ? toast?.success
          : resolved.tone === "error"
            ? toast?.error
            : warnOrInfo;
      notifier?.call(toast, resolved.message);
      await loadSource();
    } catch (error) {
      toast?.error?.(error?.message || "同步 Veeam 备份失败");
    } finally {
      stop();
    }
  }

  elements.saveButton?.addEventListener("click", handleSaveBinding);
  elements.unbindButton?.addEventListener("click", handleUnbindSource);
  elements.cancelEditButton?.addEventListener("click", () => resetForm(state.lastPayload || {}));
  elements.syncButton?.addEventListener("click", handleSyncBackups);
  elements.sourcesList?.addEventListener("click", handleSourcesListClick);

  loadSource().catch((error) => {
    toast?.error?.(error?.message || "加载 Veeam 数据源失败");
  });
})(window);
