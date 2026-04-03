(function mountVeeamSourcePage(global) {
  "use strict";

  const pageRoot = document.getElementById("veeam-source-page");
  if (!pageRoot) {
    return;
  }

  const toast = global.toast;
  const csrfToken = document.getElementById("veeam-source-csrf-token")?.value || "";
  const apiUrl = pageRoot.dataset.apiUrl;
  const syncApiUrl = pageRoot.dataset.syncApiUrl;
  const service = new global.VeeamSourceService(apiUrl, syncApiUrl);
  const setButtonLoading = global.UI?.setButtonLoading;
  const clearButtonLoading = global.UI?.clearButtonLoading;

  const elements = {
    credentialId: document.getElementById("veeamCredentialId"),
    serverHost: document.getElementById("veeamServerHost"),
    serverPort: document.getElementById("veeamServerPort"),
    apiVersion: document.getElementById("veeamApiVersion"),
    verifySsl: document.getElementById("veeamVerifySsl"),
    matchDomains: document.getElementById("veeamMatchDomains"),
    providerStatus: document.getElementById("veeamProviderStatus"),
    bindingSummary: document.getElementById("veeamBindingSummary"),
    syncStatusSummary: document.getElementById("veeamSyncStatusSummary"),
    saveButton: document.getElementById("saveVeeamSourceBtn"),
    unbindButton: document.getElementById("unbindVeeamSourceBtn"),
    syncButton: document.getElementById("syncVeeamBackupsBtn"),
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
    const binding = payload?.binding || null;
    const selectedId = binding?.credential_id || binding?.credential?.id || "";
    renderCredentialOptions(payload?.veeam_credentials, selectedId);
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
      if (!binding || !binding.credential) {
        elements.bindingSummary.textContent = "当前未绑定 Veeam 凭据";
      } else {
        const domainSummary = Array.isArray(binding.match_domains) && binding.match_domains.length
          ? binding.match_domains.join(", ")
          : "无";
        elements.bindingSummary.textContent =
          `${binding.credential.name} · ${binding.server_host}:${binding.server_port} · ${binding.api_version} · 域名=${domainSummary}`;
      }
    }
    if (elements.syncStatusSummary) {
      if (!binding) {
        elements.syncStatusSummary.textContent = "未执行同步";
      } else {
        const status = binding.last_sync_status || "未执行同步";
        const lastSyncAt = binding.last_sync_at || "-";
        elements.syncStatusSummary.textContent = `${status} · ${lastSyncAt}`;
      }
    }
    if (elements.unbindButton) {
      elements.unbindButton.disabled = !binding;
    }
    if (elements.syncButton) {
      elements.syncButton.disabled = !binding || !payload?.provider_ready;
      elements.syncButton.title = payload?.provider_ready ? "同步 Veeam 备份" : "Veeam Provider 待接入";
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
      const response = await service.updateBinding(
        {
          credential_id: credentialId,
          server_host: serverHost,
          server_port: serverPort,
          api_version: apiVersion,
          verify_ssl: verifySsl,
          match_domains: matchDomains,
        },
        csrfToken,
      );
      if (!response?.success) {
        throw new Error(response?.message || "绑定 Veeam 数据源失败");
      }
      fillPage(response.data || {});
      toast?.success?.("Veeam 数据源绑定成功");
    } catch (error) {
      toast?.error?.(error?.message || "绑定 Veeam 数据源失败");
    } finally {
      stop();
    }
  }

  async function handleUnbindSource() {
    const stop = setButtonBusy(elements.unbindButton, "解绑中...");
    try {
      const response = await service.deleteBinding(csrfToken);
      if (!response?.success) {
        throw new Error(response?.message || "解绑数据源失败");
      }
      fillPage(response.data || {});
      toast?.success?.("解绑 Veeam 数据源成功");
    } catch (error) {
      toast?.error?.(error?.message || "解绑 Veeam 数据源失败");
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
  elements.syncButton?.addEventListener("click", handleSyncBackups);

  loadSource().catch((error) => {
    toast?.error?.(error?.message || "加载 Veeam 数据源失败");
  });
})(window);
