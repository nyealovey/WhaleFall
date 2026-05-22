(function mountAdDomainConfigsPage(global) {
  "use strict";

  const pageRoot = document.getElementById("ad-domain-configs-page");
  if (!pageRoot) {
    return;
  }

  const toast = global.toast;
  const csrfToken = document.getElementById("ad-domain-configs-csrf-token")?.value || "";
  const service = new global.AdDomainConfigsService(pageRoot.dataset.apiUrl, pageRoot.dataset.credentialsApiUrl);
  const setButtonLoading = global.UI?.setButtonLoading;
  const clearButtonLoading = global.UI?.clearButtonLoading;
  const escapeHtml = global.UI?.escapeHtml || function fallbackEscapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  };

  const elements = {
    formTitle: document.getElementById("adDomainConfigFormTitle"),
    name: document.getElementById("adDomainConfigName"),
    netbiosName: document.getElementById("adDomainNetbiosName"),
    controllers: document.getElementById("adDomainControllers"),
    ldapPort: document.getElementById("adDomainLdapPort"),
    useSsl: document.getElementById("adDomainUseSsl"),
    verifySsl: document.getElementById("adDomainVerifySsl"),
    baseDn: document.getElementById("adDomainBaseDn"),
    credentialId: document.getElementById("adDomainCredentialId"),
    isEnabled: document.getElementById("adDomainIsEnabled"),
    description: document.getElementById("adDomainDescription"),
    configsList: document.getElementById("adDomainConfigsList"),
    configSummary: document.getElementById("adDomainConfigSummary"),
    syncStatusSummary: document.getElementById("adDomainSyncStatusSummary"),
    saveButton: document.getElementById("saveAdDomainConfigBtn"),
    deleteButton: document.getElementById("deleteAdDomainConfigBtn"),
    cancelEditButton: document.getElementById("cancelEditAdDomainConfigBtn"),
    syncButton: document.getElementById("syncAdDomainAccountsBtn"),
  };

  const state = {
    editingConfigId: null,
    configs: [],
    credentials: [],
  };

  function setButtonBusy(button, loadingText) {
    if (!button) {
      return function stop() {};
    }
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

  function controllersToList(value) {
    return String(value || "")
      .split(/[\n,]+/)
      .map((item) => item.trim())
      .filter(Boolean)
      .filter((item, index, list) => list.indexOf(item) === index);
  }

  function controllersToText(value) {
    return Array.isArray(value) ? value.join("\n") : "";
  }

  function verifySslToPayload(value) {
    if (value === "true") {
      return true;
    }
    if (value === "false") {
      return false;
    }
    return null;
  }

  function verifySslToControlValue(value) {
    if (value === true) {
      return "true";
    }
    if (value === false) {
      return "false";
    }
    return "";
  }

  function renderCredentialOptions(selectedId) {
    if (!(elements.credentialId instanceof HTMLSelectElement)) {
      return;
    }
    const optionHtml = ['<option value="">请选择 LDAP 凭据</option>']
      .concat(
        state.credentials.map((item) => {
          const selected = Number(item?.id) === Number(selectedId) ? "selected" : "";
          const description = item?.description ? ` · ${item.description}` : "";
          return `<option value="${String(item?.id || "")}" ${selected}>${escapeHtml(item?.name || "未命名凭据")}${escapeHtml(description)}</option>`;
        }),
      )
      .join("");
    elements.credentialId.innerHTML = optionHtml;
  }

  function updateSummaries() {
    if (elements.configSummary) {
      if (!state.configs.length) {
        elements.configSummary.textContent = "当前未配置 AD 域";
      } else {
        const enabledCount = state.configs.filter((item) => item?.is_enabled).length;
        elements.configSummary.textContent = `${state.configs.length} 个域 · ${enabledCount} 个启用`;
      }
    }
    if (elements.syncStatusSummary) {
      const latest = state.configs
        .filter((item) => item?.last_sync_at)
        .sort((a, b) => String(b.last_sync_at).localeCompare(String(a.last_sync_at)))[0];
      const failedCount = state.configs.filter((item) => item?.last_sync_status === "failed").length;
      if (!state.configs.length) {
        elements.syncStatusSummary.textContent = "未执行同步";
      } else if (failedCount > 0) {
        elements.syncStatusSummary.textContent = `${failedCount} 个失败 · ${latest?.last_sync_at || "-"}`;
      } else {
        elements.syncStatusSummary.textContent = `${latest?.last_sync_status || "未执行同步"} · ${latest?.last_sync_at || "-"}`;
      }
    }
    if (elements.deleteButton) {
      elements.deleteButton.disabled = state.editingConfigId === null;
    }
    if (elements.syncButton) {
      const hasEnabledConfig = state.configs.some((item) => item?.is_enabled);
      elements.syncButton.disabled = !hasEnabledConfig;
      elements.syncButton.title = hasEnabledConfig ? "AD 域账户同步" : "请先启用至少一个 AD 域配置";
    }
  }

  function renderConfigsList() {
    const tbody = elements.configsList?.querySelector("tbody");
    if (!tbody) {
      return;
    }
    if (!state.configs.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-muted">当前未配置 AD 域</td></tr>';
      return;
    }
    tbody.innerHTML = state.configs
      .map((config) => {
        const configId = Number(config?.id || 0);
        const controllers = Array.isArray(config?.domain_controllers) ? config.domain_controllers : [];
        const statusText = config?.is_enabled ? "启用" : "停用";
        const statusClass = config?.is_enabled ? "text-success" : "text-muted";
        const credentialName = config?.credential?.name || "-";
        const syncText = config?.last_sync_status
          ? `${escapeHtml(config.last_sync_status)} · ${escapeHtml(config.last_sync_at || "-")}`
          : "未执行";
        return `
          <tr data-config-id="${configId}">
            <td><strong>${escapeHtml(config?.name || "-")}</strong><div class="text-muted small">${escapeHtml(config?.netbios_name || "-")}</div></td>
            <td>${escapeHtml(controllers.join(", ") || "-")}</td>
            <td>${escapeHtml(credentialName)}</td>
            <td><span class="${statusClass}">${statusText}</span></td>
            <td>${syncText}</td>
            <td class="text-end">
              <button class="btn btn-sm btn-outline-secondary" type="button" data-ad-domain-action="edit" data-config-id="${configId}">编辑</button>
              <button class="btn btn-sm btn-outline-secondary" type="button" data-ad-domain-action="test" data-config-id="${configId}">测试</button>
              <button class="btn btn-sm btn-outline-secondary" type="button" data-ad-domain-action="${config?.is_enabled ? "disable" : "enable"}" data-config-id="${configId}">
                ${config?.is_enabled ? "停用" : "启用"}
              </button>
            </td>
          </tr>
        `;
      })
      .join("");
  }

  function fillForm(config) {
    const item = config || {};
    if (elements.formTitle) {
      elements.formTitle.textContent = config ? "编辑 AD 域" : "新增 AD 域";
    }
    if (elements.name) elements.name.value = item.name || "";
    if (elements.netbiosName) elements.netbiosName.value = item.netbios_name || "";
    if (elements.controllers) elements.controllers.value = controllersToText(item.domain_controllers);
    if (elements.ldapPort) elements.ldapPort.value = item.ldap_port || 636;
    if (elements.useSsl instanceof HTMLInputElement) elements.useSsl.checked = Boolean(item.use_ssl ?? true);
    if (elements.verifySsl instanceof HTMLSelectElement) elements.verifySsl.value = verifySslToControlValue(item.verify_ssl);
    if (elements.baseDn) elements.baseDn.value = item.base_dn || "";
    if (elements.isEnabled instanceof HTMLInputElement) elements.isEnabled.checked = Boolean(item.is_enabled ?? true);
    if (elements.description) elements.description.value = item.description || "";
    renderCredentialOptions(item.credential_id || item.credential?.id || "");
    updateSummaries();
  }

  function fillPage(configs, credentials) {
    state.configs = Array.isArray(configs) ? configs : [];
    state.credentials = Array.isArray(credentials) ? credentials : [];
    const current = state.editingConfigId
      ? state.configs.find((item) => Number(item?.id) === Number(state.editingConfigId))
      : null;
    if (state.editingConfigId && !current) {
      state.editingConfigId = null;
    }
    fillForm(current || null);
    renderConfigsList();
    updateSummaries();
  }

  async function loadPage() {
    const [configsResponse, credentialsResponse] = await Promise.all([
      service.loadConfigs(),
      service.loadLdapCredentials(),
    ]);
    if (!configsResponse?.success) {
      throw new Error(configsResponse?.message || "加载 AD 域配置失败");
    }
    if (!credentialsResponse?.success) {
      throw new Error(credentialsResponse?.message || "加载 LDAP 凭据失败");
    }
    fillPage(configsResponse.data?.configs || [], credentialsResponse.data?.items || []);
  }

  function buildPayload() {
    const name = String(elements.name?.value || "").trim();
    const netbiosName = String(elements.netbiosName?.value || "").trim();
    const domainControllers = controllersToList(elements.controllers?.value || "");
    const ldapPort = Number(elements.ldapPort?.value || 0);
    const baseDn = String(elements.baseDn?.value || "").trim();
    const credentialId = Number(elements.credentialId?.value || 0);

    if (!name) throw new Error("请输入域名");
    if (!netbiosName) throw new Error("请输入 NetBIOS 名称");
    if (!domainControllers.length) throw new Error("请输入域控地址");
    if (!ldapPort) throw new Error("请输入 LDAP 端口");
    if (!baseDn) throw new Error("请输入 Base DN");
    if (!credentialId) throw new Error("请选择 LDAP 凭据");

    return {
      name,
      netbios_name: netbiosName,
      domain_controllers: domainControllers,
      ldap_port: ldapPort,
      use_ssl: elements.useSsl instanceof HTMLInputElement ? elements.useSsl.checked : true,
      verify_ssl: verifySslToPayload(elements.verifySsl?.value || ""),
      base_dn: baseDn,
      credential_id: credentialId,
      is_enabled: elements.isEnabled instanceof HTMLInputElement ? elements.isEnabled.checked : true,
      description: String(elements.description?.value || "").trim() || null,
    };
  }

  async function handleSaveConfig(event) {
    event.preventDefault();
    let payload;
    try {
      payload = buildPayload();
    } catch (error) {
      toast?.error?.(error?.message || "请检查 AD 域配置");
      return;
    }

    const stop = setButtonBusy(elements.saveButton, "保存中...");
    try {
      const response = state.editingConfigId
        ? await service.updateConfig(state.editingConfigId, payload, csrfToken)
        : await service.createConfig(payload, csrfToken);
      if (!response?.success) {
        throw new Error(response?.message || "保存 AD 域配置失败");
      }
      toast?.success?.("AD 域配置保存成功");
      fillPage(response.data?.configs || [], state.credentials);
    } catch (error) {
      toast?.error?.(error?.message || "保存 AD 域配置失败");
    } finally {
      stop();
    }
  }

  async function handleDeleteConfig() {
    if (state.editingConfigId === null) {
      toast?.error?.("请先选择要删除的 AD 域配置");
      return;
    }
    const stop = setButtonBusy(elements.deleteButton, "删除中...");
    try {
      const response = await service.deleteConfig(state.editingConfigId, csrfToken);
      if (!response?.success) {
        throw new Error(response?.message || "删除 AD 域配置失败");
      }
      state.editingConfigId = null;
      toast?.success?.("AD 域配置已删除");
      fillPage(response.data?.configs || [], state.credentials);
    } catch (error) {
      toast?.error?.(error?.message || "删除 AD 域配置失败");
    } finally {
      stop();
    }
  }

  async function handleConfigsListClick(event) {
    const target = event.target instanceof Element ? event.target.closest("[data-ad-domain-action]") : null;
    if (!target) {
      return;
    }
    const configId = Number(target.getAttribute("data-config-id") || 0);
    const action = target.getAttribute("data-ad-domain-action");
    const config = state.configs.find((item) => Number(item?.id) === configId);
    if (!config) {
      return;
    }
    if (action === "edit") {
      state.editingConfigId = configId;
      fillForm(config);
      return;
    }
    if (action === "test") {
      const stop = setButtonBusy(target, "测试中...");
      try {
        const response = await service.testConnection(configId, csrfToken);
        if (!response?.success) {
          throw new Error(response?.message || "AD 域连接测试失败");
        }
        toast?.success?.(`AD 域连接测试成功：${response.data?.principal_count ?? 0} 个对象`);
      } catch (error) {
        toast?.error?.(error?.message || "AD 域连接测试失败");
      } finally {
        stop();
      }
      return;
    }
    if (action !== "enable" && action !== "disable") {
      return;
    }
    const stop = setButtonBusy(target, action === "enable" ? "启用中..." : "停用中...");
    try {
      const response = await service.setEnabled(configId, action === "enable", csrfToken);
      if (!response?.success) {
        throw new Error(response?.message || "更新 AD 域配置状态失败");
      }
      toast?.success?.(action === "enable" ? "AD 域配置已启用" : "AD 域配置已停用");
      fillPage(response.data?.configs || [], state.credentials);
    } catch (error) {
      toast?.error?.(error?.message || "更新 AD 域配置状态失败");
    } finally {
      stop();
    }
  }

  async function handleSyncAccounts() {
    const stop = setButtonBusy(elements.syncButton, "同步中...");
    try {
      const response = await service.syncAccounts(csrfToken);
      if (!response?.success) {
        throw new Error(response?.message || "AD 域账户同步失败");
      }
      toast?.success?.(response?.message || "AD 域账户同步已触发");
      await loadPage();
    } catch (error) {
      toast?.error?.(error?.message || "AD 域账户同步失败");
    } finally {
      stop();
    }
  }

  elements.saveButton?.addEventListener("click", handleSaveConfig);
  elements.deleteButton?.addEventListener("click", handleDeleteConfig);
  elements.cancelEditButton?.addEventListener("click", () => {
    state.editingConfigId = null;
    fillForm(null);
  });
  elements.syncButton?.addEventListener("click", handleSyncAccounts);
  elements.configsList?.addEventListener("click", handleConfigsListClick);

  loadPage().catch((error) => {
    toast?.error?.(error?.message || "加载 AD 域配置失败");
  });
})(window);
