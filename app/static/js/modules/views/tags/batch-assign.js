/**
 * 标签批量分配页面入口。
 *
 * 约束:
 * - 页面不直连 TagManagementService：所有业务动作通过 TagBatchStore actions。
 * - 页面不维护业务 state：渲染以 store.getState() 快照为准。
 */
(function (global) {
  "use strict";

  const UNSAFE_KEYS = new Set(["__proto__", "prototype", "constructor"]);

  function isSafeKey(key) {
    return typeof key === "string" && key && !UNSAFE_KEYS.has(key);
  }

  function toDomIdFragment(value) {
    const raw = typeof value === "string" ? value : "unknown";
    const normalized = raw.trim() || "unknown";
    const cleaned = normalized.replace(/[^a-zA-Z0-9_-]/g, "_");
    return cleaned && isSafeKey(cleaned) ? cleaned : "unknown";
  }

  function normalizeId(value) {
    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === "string" && value.trim()) {
      const parsed = Number.parseInt(value, 10);
      return Number.isFinite(parsed) ? parsed : null;
    }
    return null;
  }

  function mountTagsBatchAssignPage(globalRef = global, documentRef = document) {
    const escapeHtml = globalRef.UI?.escapeHtml;
    if (typeof escapeHtml !== "function") {
      console.error("UI.escapeHtml 未初始化，批量分配页面无法安全渲染");
      return;
    }

    const toast = globalRef.toast || {
      success: (message) => console.info(message),
      error: (message) => console.error(message),
      warning: (message) => console.warn(message),
      info: (message) => console.info(message),
    };

    const TagManagementService = globalRef.TagManagementService;
    if (!TagManagementService) {
      console.error("TagManagementService 未初始化，批量分配页面无法加载");
      return;
    }

    const createTagBatchStore = globalRef.createTagBatchStore;
    if (typeof createTagBatchStore !== "function") {
      console.error("createTagBatchStore 未加载，批量分配页面无法加载");
      return;
    }

    const service = new TagManagementService();
    const store = createTagBatchStore({ service });

    const dom = {
      instancesLoading: documentRef.getElementById("instancesLoading"),
      instancesContainer: documentRef.getElementById("instancesContainer"),
      tagsLoading: documentRef.getElementById("tagsLoading"),
      tagsContainer: documentRef.getElementById("tagsContainer"),
      form: documentRef.getElementById("batchAssignForm"),
      batchModeField: documentRef.getElementById("batchModeField"),
      selectedInstancesInput: documentRef.getElementById("selectedInstancesInput"),
      selectedTagsInput: documentRef.getElementById("selectedTagsInput"),
      clearAllSelections: documentRef.getElementById("clearAllSelections"),
      executeBatchOperation: documentRef.getElementById("executeBatchOperation"),
      removeModeInfo: documentRef.getElementById("removeModeInfo"),
      tagSelectionPanel: documentRef.getElementById("tagSelectionPanel"),
      batchLayoutGrid: documentRef.getElementById("batchLayoutGrid"),
      selectedTagsSection: documentRef.getElementById("selectedTagsSection"),
      selectedInstancesCount: documentRef.getElementById("selectedInstancesCount"),
      selectedTagsCount: documentRef.getElementById("selectedTagsCount"),
      totalSelectedInstances: documentRef.getElementById("totalSelectedInstances"),
      totalSelectedTags: documentRef.getElementById("totalSelectedTags"),
      summaryTagCount: documentRef.getElementById("summaryTagCount"),
      selectedInstancesList: documentRef.getElementById("selectedInstancesList"),
      selectedTagsList: documentRef.getElementById("selectedTagsList"),
      progressContainer: documentRef.getElementById("progressContainer"),
      progressText: documentRef.getElementById("progressText"),
    };

    if (!dom.instancesContainer || !dom.tagsContainer || !dom.form) {
      console.error("批量分配页面 DOM 结构缺失，无法初始化");
      return;
    }

    let validator = null;
    if (globalRef.FormValidator && globalRef.ValidationRules) {
      validator = globalRef.FormValidator.create("#batchAssignForm");
      validator
        ?.useRules("#selectedInstancesInput", globalRef.ValidationRules.batchAssign.instances)
        ?.useRules("#selectedTagsInput", globalRef.ValidationRules.batchAssign.tags)
        ?.onSuccess((event) => {
          event.preventDefault();
          executeOperation();
        })
        ?.onFail(() => {
          toast.error("请检查实例和标签选择后再执行操作");
        });
    }

    let instanceById = new Map();
    let tagById = new Map();
    let progressTimer = null;

    function rebuildLookups(state) {
      instanceById = new Map();
      tagById = new Map();

      Object.values(state.instancesByDbType || {}).forEach((items) => {
        if (!Array.isArray(items)) return;
        items.forEach((item) => {
          const id = normalizeId(item?.id);
          if (id !== null) {
            instanceById.set(id, item);
          }
        });
      });

      Object.values(state.tagsByCategory || {}).forEach((items) => {
        if (!Array.isArray(items)) return;
        items.forEach((item) => {
          const id = normalizeId(item?.id);
          if (id !== null) {
            tagById.set(id, item);
          }
        });
      });
    }

    function getDbTypeDisplayName(dbType) {
      const normalized = typeof dbType === "string" ? dbType.toLowerCase() : "";
      switch (normalized) {
        case "mysql":
          return "MySQL";
        case "postgresql":
          return "PostgreSQL";
        case "sqlserver":
          return "SQL Server";
        case "oracle":
          return "Oracle";
        case "redis":
          return "Redis";
        default:
          return dbType || "Unknown";
      }
    }

    function buildEmptyState(text, iconClass) {
      return `
        <div class="empty-state">
          <i class="${iconClass || "fas fa-box-open"}"></i>
          <p>${escapeHtml(text || "")}</p>
        </div>
      `;
    }

    function buildLedgerChipHtml(content, muted) {
      const classes = ["ledger-chip"];
      if (muted) {
        classes.push("ledger-chip--muted");
      }
      return `<span class="${classes.join(" ")}">${content}</span>`;
    }

    function renderInstances(state) {
      const groups = state.instancesByDbType || {};
      const keys = Object.keys(groups).filter(isSafeKey).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));

      if (!keys.length) {
        dom.instancesContainer.innerHTML = buildEmptyState("暂无实例数据", "fas fa-database");
        return;
      }

      const selected = new Set(state.selectedInstanceIds || []);
      const html = keys
        .map((dbType) => {
          const domKey = toDomIdFragment(dbType);
          // eslint-disable-next-line security/detect-object-injection
          const instances = Array.isArray(groups[dbType]) ? groups[dbType] : [];

          const dbTypeDisplay = getDbTypeDisplayName(dbType);
          const rowsHtml = instances
            .map((instance) => {
              const id = normalizeId(instance?.id);
              const checked = id !== null && selected.has(id);
              const name = escapeHtml(instance?.name || (id !== null ? `实例 ${id}` : "未知实例"));
              const host = escapeHtml(instance?.host || "-");
              const port = escapeHtml(instance?.port ?? "-");
              const rowId = id !== null ? id : "";
              return `
                <label class="ledger-row${checked ? " ledger-row--selected" : ""}" data-instance-row="${rowId}" for="instance_${rowId}">
                  <input class="form-check-input" type="checkbox"
                         id="instance_${rowId}"
                         ${checked ? "checked" : ""}
                         data-action="toggle-instance-selection"
                         data-instance-id="${rowId}">
                  <div class="ledger-row__body">
                    <div class="ledger-row__title">${name}</div>
                    <div class="ledger-row__meta">${host}:${port}</div>
                  </div>
                  <div class="ledger-row__badge">
                    <span class="chip-outline chip-outline--muted">${escapeHtml(getDbTypeDisplayName(instance?.db_type))}</span>
                  </div>
                </label>
              `;
            })
            .join("");

          return `
            <div class="instance-group">
              <div class="instance-group-header" data-action="toggle-instance-group" data-db-type="${escapeHtml(dbType)}">
                <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
                  <div class="d-flex align-items-center gap-2">
                    <i class="fas fa-chevron-right instance-group-icon"></i>
                    <span class="chip-outline chip-outline--muted">${escapeHtml(dbTypeDisplay)}</span>
                    <span class="text-muted small">${instances.length} 个</span>
                  </div>
                  <div class="form-check form-check-inline">
                    <input class="form-check-input" type="checkbox"
                           id="instanceGroup_${domKey}"
                           data-action="toggle-instance-group-selection"
                           data-db-type="${escapeHtml(dbType)}">
                    <label class="form-check-label" for="instanceGroup_${domKey}">全选</label>
                  </div>
                </div>
              </div>
              <div class="instance-group-content" id="instanceGroupContent_${domKey}">
                ${rowsHtml}
              </div>
            </div>
          `;
        })
        .join("");

      dom.instancesContainer.innerHTML = html;
    }

    function renderTags(state) {
      const groups = state.tagsByCategory || {};
      const keys = Object.keys(groups).filter(isSafeKey).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));

      if (!keys.length) {
        dom.tagsContainer.innerHTML = buildEmptyState("暂无标签数据", "fas fa-tags");
        return;
      }

      const selected = new Set(state.selectedTagIds || []);
      const html = keys
        .map((category) => {
          const domKey = toDomIdFragment(category);
          // eslint-disable-next-line security/detect-object-injection
          const tags = Array.isArray(groups[category]) ? groups[category] : [];

          const rowsHtml = tags
            .map((tag) => {
              const id = normalizeId(tag?.id);
              const checked = id !== null && selected.has(id);
              const label = escapeHtml(tag?.display_name || tag?.name || (id !== null ? `标签 ${id}` : "未知标签"));
              const isActive = Boolean(tag?.is_active);
              const rowId = id !== null ? id : "";
              return `
                <label class="ledger-row${checked ? " ledger-row--selected" : ""}" data-tag-row="${rowId}" for="tag_${rowId}">
                  <input class="form-check-input" type="checkbox"
                         id="tag_${rowId}"
                         ${checked ? "checked" : ""}
                         data-action="toggle-tag-selection"
                         data-tag-id="${rowId}">
                  <div class="ledger-row__body">
                    <div class="ledger-row__title">${label}</div>
                    <div class="ledger-row__meta">
                      <span class="status-pill status-pill--${isActive ? "success" : "muted"}">
                        <i class="fas fa-${isActive ? "check-circle" : "ban"}"></i>${isActive ? "启用" : "停用"}
                      </span>
                    </div>
                  </div>
                  <div class="ledger-row__badge">
                    <span class="chip-outline chip-outline--muted">${escapeHtml(category)}</span>
                  </div>
                </label>
              `;
            })
            .join("");

          return `
            <div class="tag-group">
              <div class="tag-group-header" data-action="toggle-tag-group" data-category="${escapeHtml(category)}">
                <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
                  <div class="d-flex align-items-center gap-2">
                    <i class="fas fa-chevron-right tag-group-icon"></i>
                    <span class="chip-outline chip-outline--muted">${escapeHtml(category)}</span>
                    <span class="text-muted small">${tags.length} 个</span>
                  </div>
                  <div class="form-check form-check-inline">
                    <input class="form-check-input" type="checkbox"
                           id="tagGroup_${domKey}"
                           data-action="toggle-tag-group-selection"
                           data-category="${escapeHtml(category)}">
                    <label class="form-check-label" for="tagGroup_${domKey}">全选</label>
                  </div>
                </div>
              </div>
              <div class="tag-group-content" id="tagGroupContent_${domKey}">
                ${rowsHtml}
              </div>
            </div>
          `;
        })
        .join("");

      dom.tagsContainer.innerHTML = html;
    }

    function setLoadingState(panel, loading) {
      if (panel === "instances") {
        if (dom.instancesLoading) {
          dom.instancesLoading.style.display = loading ? "block" : "none";
        }
        dom.instancesContainer.style.display = loading ? "none" : "block";
      }
      if (panel === "tags") {
        if (dom.tagsLoading) {
          dom.tagsLoading.style.display = loading ? "block" : "none";
        }
        dom.tagsContainer.style.display = loading ? "none" : "block";
      }
    }

    function syncModeUI(mode) {
      const isRemoveMode = mode === "remove";

      if (dom.batchLayoutGrid) {
        dom.batchLayoutGrid.dataset.mode = mode || "assign";
        dom.batchLayoutGrid.classList.toggle("is-remove-mode", isRemoveMode);
      }
      if (dom.removeModeInfo) {
        dom.removeModeInfo.style.display = isRemoveMode ? "block" : "none";
      }
      if (dom.tagSelectionPanel) {
        dom.tagSelectionPanel.style.display = isRemoveMode ? "none" : "block";
      }
      if (dom.selectedTagsSection) {
        dom.selectedTagsSection.style.display = isRemoveMode ? "none" : "block";
      }
      if (dom.summaryTagCount) {
        dom.summaryTagCount.hidden = isRemoveMode;
      }
      if (dom.batchModeField) {
        dom.batchModeField.value = mode || "assign";
      }

      documentRef.querySelectorAll(".chip-toggle").forEach((label) => label.classList.remove("chip-toggle--active"));
      documentRef.querySelectorAll(".chip-toggle-input").forEach((input) => {
        if (input.checked) {
          const label = documentRef.querySelector(`label[for="${input.id}"]`);
          label?.classList.add("chip-toggle--active");
        }
      });

      if (dom.executeBatchOperation) {
        dom.executeBatchOperation.innerHTML = isRemoveMode
          ? '<i class="fas fa-minus me-1"></i>移除标签'
          : '<i class="fas fa-plus me-1"></i>分配标签';
      }
    }

    function updateHiddenFields(state) {
      if (dom.selectedInstancesInput) {
        dom.selectedInstancesInput.value = (state.selectedInstanceIds || []).join(",");
        validator?.revalidateField?.("#selectedInstancesInput");
      }
      if (dom.selectedTagsInput) {
        dom.selectedTagsInput.value = (state.selectedTagIds || []).join(",");
        validator?.revalidateField?.("#selectedTagsInput");
      }
    }

    function updateCounts(state) {
      const instancesCount = Array.isArray(state.selectedInstanceIds) ? state.selectedInstanceIds.length : 0;
      const tagsCount = Array.isArray(state.selectedTagIds) ? state.selectedTagIds.length : 0;

      if (dom.selectedInstancesCount) dom.selectedInstancesCount.textContent = String(instancesCount);
      if (dom.selectedTagsCount) dom.selectedTagsCount.textContent = String(tagsCount);
      if (dom.totalSelectedInstances) dom.totalSelectedInstances.textContent = String(instancesCount);
      if (dom.totalSelectedTags) dom.totalSelectedTags.textContent = String(tagsCount);
    }

    function updateActionButton(state) {
      if (!dom.executeBatchOperation) {
        return;
      }
      const instancesCount = Array.isArray(state.selectedInstanceIds) ? state.selectedInstanceIds.length : 0;
      const tagsCount = Array.isArray(state.selectedTagIds) ? state.selectedTagIds.length : 0;
      const canExecute = instancesCount > 0 && (state.mode === "remove" || tagsCount > 0);
      dom.executeBatchOperation.disabled = !canExecute;
    }

    function updateSelectionSummary(state) {
      if (!dom.selectedInstancesList || !dom.selectedTagsList) {
        return;
      }

      const instanceIds = Array.isArray(state.selectedInstanceIds) ? state.selectedInstanceIds : [];
      const tagIds = Array.isArray(state.selectedTagIds) ? state.selectedTagIds : [];
      const isRemoveMode = state.mode === "remove";

      if (instanceIds.length) {
        dom.selectedInstancesList.innerHTML = instanceIds
          .map((id) => {
            const instance = instanceById.get(id);
            const label = escapeHtml(instance?.name || `实例 ${id}`);
            return buildLedgerChipHtml(`<i class="fas fa-database"></i>${label}`, false);
          })
          .join("");
      } else {
        dom.selectedInstancesList.innerHTML = buildEmptyState("尚未选择实例", "fas fa-database");
      }

      if (isRemoveMode) {
        dom.selectedTagsList.innerHTML = buildEmptyState("移除模式无需选择标签", "fas fa-tags");
        return;
      }

      if (tagIds.length) {
        dom.selectedTagsList.innerHTML = tagIds
          .map((id) => {
            const tag = tagById.get(id);
            const label = escapeHtml(tag?.display_name || tag?.name || `标签 ${id}`);
            const muted = tag ? !tag.is_active : true;
            return buildLedgerChipHtml(`<i class="fas fa-tag"></i>${label}`, muted);
          })
          .join("");
      } else {
        dom.selectedTagsList.innerHTML = buildEmptyState("尚未选择标签", "fas fa-tags");
      }
    }

    function syncGroupCheckboxes(state) {
      const selectedInstances = new Set(state.selectedInstanceIds || []);
      const selectedTags = new Set(state.selectedTagIds || []);

      Object.entries(state.instancesByDbType || {}).forEach(([dbType, items]) => {
        if (!isSafeKey(dbType) || !Array.isArray(items)) {
          return;
        }
        const domKey = toDomIdFragment(dbType);
        const checkbox = documentRef.getElementById(`instanceGroup_${domKey}`);
        if (!checkbox) {
          return;
        }
        const ids = items.map((item) => normalizeId(item?.id)).filter((id) => id !== null);
        const selectedCount = ids.filter((id) => selectedInstances.has(id)).length;
        checkbox.indeterminate = selectedCount > 0 && selectedCount < ids.length;
        checkbox.checked = ids.length > 0 && selectedCount === ids.length;
      });

      Object.entries(state.tagsByCategory || {}).forEach(([category, items]) => {
        if (!isSafeKey(category) || !Array.isArray(items)) {
          return;
        }
        const domKey = toDomIdFragment(category);
        const checkbox = documentRef.getElementById(`tagGroup_${domKey}`);
        if (!checkbox) {
          return;
        }
        const ids = items.map((item) => normalizeId(item?.id)).filter((id) => id !== null);
        const selectedCount = ids.filter((id) => selectedTags.has(id)).length;
        checkbox.indeterminate = selectedCount > 0 && selectedCount < ids.length;
        checkbox.checked = ids.length > 0 && selectedCount === ids.length;
      });
    }

    function syncRowSelectedStates() {
      dom.instancesContainer.querySelectorAll("input[data-action='toggle-instance-selection']").forEach((checkbox) => {
        const id = normalizeId(checkbox.getAttribute("data-instance-id"));
        const row = checkbox.closest(".ledger-row");
        if (id !== null && row) {
          row.classList.toggle("ledger-row--selected", checkbox.checked);
        }
      });
      dom.tagsContainer.querySelectorAll("input[data-action='toggle-tag-selection']").forEach((checkbox) => {
        const id = normalizeId(checkbox.getAttribute("data-tag-id"));
        const row = checkbox.closest(".ledger-row");
        if (id !== null && row) {
          row.classList.toggle("ledger-row--selected", checkbox.checked);
        }
      });
    }

    function showProgress() {
      if (!dom.progressContainer || !dom.progressText) {
        return;
      }
      const bar = dom.progressContainer.querySelector(".progress-bar");
      dom.progressContainer.style.display = "block";
      if (bar) {
        bar.style.width = "0%";
      }
      dom.progressText.textContent = "准备中...";

      let progress = 0;
      progressTimer = setInterval(() => {
        progress += Math.random() * 18;
        if (progress > 90) {
          progress = 90;
        }
        if (bar) {
          bar.style.width = `${Math.round(progress)}%`;
        }
        dom.progressText.textContent = `处理中... ${Math.round(progress)}%`;
      }, 200);
    }

    function hideProgress(success) {
      if (progressTimer) {
        clearInterval(progressTimer);
        progressTimer = null;
      }
      if (!dom.progressContainer || !dom.progressText) {
        return;
      }
      const bar = dom.progressContainer.querySelector(".progress-bar");
      if (bar) {
        bar.style.width = "100%";
      }
      dom.progressText.textContent = success ? "完成" : "失败";
      setTimeout(() => {
        dom.progressContainer.style.display = "none";
      }, 800);
    }

    async function executeOperation() {
      try {
        showProgress();
        await store.actions.executeOperation();
        hideProgress(true);
        toast.success("操作完成");
        store.actions.clearSelections();
      } catch (error) {
        hideProgress(false);
        toast.error(error?.message || "操作失败");
      }
    }

    function refreshSelectionUI() {
      const state = store.getState();
      updateHiddenFields(state);
      updateCounts(state);
      updateSelectionSummary(state);
      updateActionButton(state);
      syncGroupCheckboxes(state);
      syncRowSelectedStates();
    }

    function refreshAllUI() {
      const state = store.getState();
      rebuildLookups(state);
      renderInstances(state);
      renderTags(state);
      syncModeUI(state.mode);
      refreshSelectionUI();
    }

    // Store subscriptions
    store.subscribe("tagBatchAssign:loading", (payload) => {
      const target = payload?.target;
      const loading = payload?.loading || {};
      if (target === "data") {
        setLoadingState("instances", Boolean(loading.data));
        setLoadingState("tags", Boolean(loading.data));
      }
    });

    store.subscribe("tagBatchAssign:updated", () => {
      setLoadingState("instances", false);
      setLoadingState("tags", false);
      refreshAllUI();
    });

    store.subscribe("tagBatchAssign:modeChanged", () => {
      const state = store.getState();
      syncModeUI(state.mode);
      refreshSelectionUI();
    });

    store.subscribe("tagBatchAssign:selectionChanged", () => {
      refreshSelectionUI();
    });

    store.subscribe("tagBatchAssign:error", (payload) => {
      const error = payload?.error || payload;
      toast.error(error?.message || "操作失败");
    });

    // Event bindings
    documentRef.querySelectorAll('input[name="batchMode"]').forEach((radio) => {
      radio.addEventListener("change", (event) => {
        const mode = event?.target?.value || "assign";
        store.actions.setMode(mode).catch((error) => {
          toast.error(error?.message || "切换模式失败");
        });
      });
    });

    dom.clearAllSelections?.addEventListener("click", (event) => {
      event.preventDefault();
      store.actions.clearSelections();
    });

    dom.form.addEventListener("submit", (event) => {
      event.preventDefault();
      if (validator?.instance?.revalidate) {
        validator.instance.revalidate();
        return;
      }
      executeOperation();
    });

    dom.instancesContainer.addEventListener("change", (event) => {
      const el = event.target;
      if (!(el instanceof HTMLElement)) {
        return;
      }
      if (el.matches("input[data-action='toggle-instance-selection']")) {
        const id = el.getAttribute("data-instance-id");
        store.actions.setInstanceSelected(id, el.checked);
      }
      if (el.matches("input[data-action='toggle-instance-group-selection']")) {
        const dbType = el.getAttribute("data-db-type") || "";
        store.actions.setInstancesByDbTypeSelected(dbType, el.checked);
      }
    });

    dom.instancesContainer.addEventListener("click", (event) => {
      const header = event.target.closest("[data-action='toggle-instance-group']");
      if (!header) {
        return;
      }
      if (event.target.closest("input[type='checkbox']")) {
        return;
      }
      const dbType = header.getAttribute("data-db-type") || "";
      const domKey = toDomIdFragment(dbType);
      const content = documentRef.getElementById(`instanceGroupContent_${domKey}`);
      if (content) {
        content.classList.toggle("show");
      }
    });

    dom.tagsContainer.addEventListener("change", (event) => {
      const el = event.target;
      if (!(el instanceof HTMLElement)) {
        return;
      }
      if (el.matches("input[data-action='toggle-tag-selection']")) {
        const id = el.getAttribute("data-tag-id");
        store.actions.setTagSelected(id, el.checked);
      }
      if (el.matches("input[data-action='toggle-tag-group-selection']")) {
        const category = el.getAttribute("data-category") || "";
        store.actions.setTagsByCategorySelected(category, el.checked);
      }
    });

    dom.tagsContainer.addEventListener("click", (event) => {
      const header = event.target.closest("[data-action='toggle-tag-group']");
      if (!header) {
        return;
      }
      if (event.target.closest("input[type='checkbox']")) {
        return;
      }
      const category = header.getAttribute("data-category") || "";
      const domKey = toDomIdFragment(category);
      const content = documentRef.getElementById(`tagGroupContent_${domKey}`);
      if (content) {
        content.classList.toggle("show");
      }
    });

    // Initial mode sync
    const initialMode = documentRef.querySelector('input[name="batchMode"]:checked')?.value || "assign";
    store.actions.setMode(initialMode).catch(() => {});
    syncModeUI(initialMode);
    refreshSelectionUI();
    setLoadingState("instances", true);
    setLoadingState("tags", true);
    store.actions.loadData().catch(() => {});
  }

  global.TagsBatchAssignPage = {
    mount: mountTagsBatchAssignPage,
  };
})(window);
