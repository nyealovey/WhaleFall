(function mountJumpServerSourcePage(global) {
  "use strict";

  const pageRoot = document.getElementById("jumpserver-source-page");
  if (!pageRoot) {
    return;
  }

  const toast = global.toast;
  const csrfToken = document.getElementById("jumpserver-source-csrf-token")?.value || "";
  const apiUrl = pageRoot.dataset.apiUrl;
  const syncApiUrl = pageRoot.dataset.syncApiUrl;
  const service = new global.JumpServerSourceService(apiUrl, syncApiUrl);
  const escapeHtml = global.UI?.escapeHtml || function fallbackEscapeHtml(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  };
  const setButtonLoading = global.UI?.setButtonLoading;
  const clearButtonLoading = global.UI?.clearButtonLoading;

  const elements = {
    credentialId: document.getElementById("jumpserverCredentialId"),
    baseUrl: document.getElementById("jumpserverBaseUrl"),
    orgId: document.getElementById("jumpserverOrgId"),
    verifySsl: document.getElementById("jumpserverVerifySsl"),
    providerStatus: document.getElementById("jumpserverProviderStatus"),
    bindingSummary: document.getElementById("jumpserverBindingSummary"),
    syncStatusSummary: document.getElementById("jumpserverSyncStatusSummary"),
    saveButton: document.getElementById("saveJumpserverSourceBtn"),
    unbindButton: document.getElementById("unbindJumpserverSourceBtn"),
    syncButton: document.getElementById("syncJumpserverAssetsBtn"),
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

  function renderCredentialOptions(options, selectedId) {
    if (!(elements.credentialId instanceof HTMLSelectElement)) {
      return;
    }
    const items = Array.isArray(options) ? options : [];
    const optionHtml = ['<option value="">请选择 API 凭据</option>']
      .concat(
        items.map((item) => {
          const selected = Number(item?.id) === Number(selectedId) ? "selected" : "";
          const label = item?.description
            ? `${item?.name || "未命名凭据"} · ${item.description}`
            : `${item?.name || "未命名凭据"}`;
          return `<option value="${String(item?.id || "")}" ${selected}>${escapeHtml(label)}</option>`;
        }),
      )
      .join("");
    elements.credentialId.innerHTML = optionHtml;
  }

  function updateProviderStatus(providerReady) {
    if (!elements.providerStatus) {
      return;
    }
    elements.providerStatus.textContent = providerReady ? "Provider 已接入" : "Provider 待接入";
  }

  function updateBindingSummary(binding) {
    if (!elements.bindingSummary) {
      return;
    }
    if (!binding || !binding.credential) {
      elements.bindingSummary.textContent = "当前未绑定 JumpServer API 凭据";
      return;
    }
    const sslVerifyStatus = binding.verify_ssl === false ? "SSL 证书验证关闭" : "SSL 证书验证开启";
    elements.bindingSummary.textContent =
      `${binding.credential.name} · ${binding.base_url || "-"} · org=${binding.org_id || "-"} · ${sslVerifyStatus}`;
  }

  function updateSyncSummary(binding) {
    if (!elements.syncStatusSummary) {
      return;
    }
    if (!binding) {
      elements.syncStatusSummary.textContent = "未执行同步";
      return;
    }
    const status = binding.last_sync_status || "未执行同步";
    const lastSyncAt = binding.last_sync_at || "-";
    elements.syncStatusSummary.textContent = `${status} · ${lastSyncAt}`;
  }

  function syncButtons(payload) {
    const binding = payload?.binding || null;
    const providerReady = Boolean(payload?.provider_ready);
    if (elements.unbindButton) {
      elements.unbindButton.disabled = !binding;
    }
    if (elements.syncButton) {
      elements.syncButton.disabled = !binding || !providerReady;
      elements.syncButton.title = providerReady ? "同步 JumpServer 资源" : "JumpServer Provider 待接入";
    }
  }

  function fillPage(payload) {
    const binding = payload?.binding || null;
    const selectedId = binding?.credential_id || binding?.credential?.id || "";
    renderCredentialOptions(payload?.api_credentials, selectedId);
    if (elements.baseUrl) {
      elements.baseUrl.value = binding?.base_url || "";
    }
    if (elements.orgId) {
      elements.orgId.value = binding?.org_id || payload?.default_org_id || "";
    }
    if (elements.verifySsl instanceof HTMLInputElement) {
      if (typeof binding?.verify_ssl === "boolean") {
        elements.verifySsl.checked = binding.verify_ssl;
      } else {
        elements.verifySsl.checked = Boolean(payload?.default_verify_ssl ?? true);
      }
    }
    updateProviderStatus(payload?.provider_ready);
    updateBindingSummary(binding);
    updateSyncSummary(binding);
    syncButtons(payload);
  }

  async function loadSource() {
    const response = await service.load();
    if (!response?.success) {
      throw new Error(response?.message || "加载 JumpServer 数据源失败");
    }
    fillPage(response.data || {});
  }

  async function handleSaveBinding(event) {
    event.preventDefault();
    const credentialId = Number(elements.credentialId?.value || 0);
    const baseUrl = String(elements.baseUrl?.value || "").trim();
    const orgId = String(elements.orgId?.value || "").trim();
    const verifySsl = elements.verifySsl instanceof HTMLInputElement ? elements.verifySsl.checked : true;
    if (!credentialId) {
      toast?.error?.("请选择 API 凭据");
      return;
    }
    if (!baseUrl) {
      toast?.error?.("请输入 JumpServer URL");
      return;
    }
    if (!orgId) {
      toast?.error?.("请输入 JumpServer 组织 ID");
      return;
    }
    const stop = setButtonBusy(elements.saveButton, "保存中...");
    try {
      const response = await service.updateBinding(
        { credential_id: credentialId, base_url: baseUrl, org_id: orgId, verify_ssl: verifySsl },
        csrfToken,
      );
      if (!response?.success) {
        throw new Error(response?.message || "绑定 JumpServer 数据源失败");
      }
      fillPage(response.data || {});
      toast?.success?.("JumpServer 数据源绑定成功");
    } catch (error) {
      toast?.error?.(error?.message || "绑定 JumpServer 数据源失败");
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
      toast?.success?.("解绑数据源成功");
    } catch (error) {
      toast?.error?.(error?.message || "解绑数据源失败");
    } finally {
      stop();
    }
  }

  async function handleSyncAssets() {
    const stop = setButtonBusy(elements.syncButton, "同步中...");
    try {
      const response = await service.syncAssets(csrfToken);
      if (!response?.success) {
        throw new Error(response?.message || "同步 JumpServer 资源失败");
      }
      const runId = response?.data?.run_id || "-";
      toast?.success?.(`同步 JumpServer 资源任务已启动：${runId}`);
      await loadSource();
    } catch (error) {
      toast?.error?.(error?.message || "同步 JumpServer 资源失败");
    } finally {
      stop();
    }
  }

  elements.saveButton?.addEventListener("click", handleSaveBinding);
  elements.unbindButton?.addEventListener("click", handleUnbindSource);
  elements.syncButton?.addEventListener("click", handleSyncAssets);

  loadSource().catch((error) => {
    toast?.error?.(error?.message || "加载 JumpServer 数据源失败");
  });
})(window);
