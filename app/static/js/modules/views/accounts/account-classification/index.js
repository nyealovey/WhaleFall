/* 账户分类管理页面脚本（模块化重构版） */
function mountAccountClassificationPage(window, document) {
    'use strict';

    const debugEnabled = window.DEBUG_ACCOUNT_CLASSIFICATION ?? true;
    window.DEBUG_ACCOUNT_CLASSIFICATION = debugEnabled;

    function debugLog(message, payload) {
        if (!debugEnabled) {
            return;
        }
        const prefix = '[AccountClassificationPage]';
        if (payload !== undefined) {
            console.debug(`${prefix} ${message}`, payload);
        } else {
            console.debug(`${prefix} ${message}`);
        }
    }

    const AccountClassificationService = window.AccountClassificationService;
    if (!AccountClassificationService) {
        console.error('AccountClassificationService 未加载，账户分类页面无法初始化');
        return;
    }
    const service = new AccountClassificationService(window.httpU);
    const api = {
        classifications: {
            list: () => service.listClassifications(),
            detail: id => service.getClassification(id),
            create: payload => service.createClassification(payload),
            update: (id, payload) => service.updateClassification(id, payload),
            remove: id => service.deleteClassification(id),
        },
        rules: {
            list: () => service.listRules(),
            stats: ids => service.ruleStats(ids),
            create: payload => service.createRule(payload),
            detail: id => service.getRule(id),
            update: (id, payload) => service.updateRule(id, payload),
            remove: id => service.deleteRule(id),
        },
        automation: {
            trigger: payload => service.triggerAutomation(payload),
        },
    };

    const toast = window.toast || {
        success: message => console.log(message),
        error: message => console.error(message),
        warning: message => console.warn(message),
        info: message => console.info(message),
    };

    const logError =
        window.logErrorWithContext ||
        function fallbackLogger(error, context, extras) {
            console.error(`[AccountClassificationPage] ${context}`, error, extras || {});
        };

    const state = {
        classifications: [],
        rulesByDbType: {},
    };

    const permissionView = window.AccountClassificationPermissionView
        ? window.AccountClassificationPermissionView.createView({
              PermissionPolicyCenter: window.PermissionPolicyCenter,
              handleRequestError,
          })
        : null;

    const ruleModals = window.AccountClassificationRuleModals
        ? window.AccountClassificationRuleModals.createController({
              document,
              UI: window.UI,
              toast,
              FormValidator: window.FormValidator,
              ValidationRules: window.ValidationRules,
              api: api.rules,
              permissionView,
              debugLog,
              handleRequestError,
              onMutated: loadRules,
              getClassificationOptions: () => state.classifications,
          })
        : null;

    const classificationModals = window.AccountClassificationModals
        ? window.AccountClassificationModals.createController({
              document,
              UI: window.UI,
              toast,
              FormValidator: window.FormValidator,
              ValidationRules: window.ValidationRules,
              api: api.classifications,
              debugLog,
              handleRequestError,
              onMutated: async () => {
                  await loadClassifications();
                  ruleModals?.updateClassificationOptions(state.classifications);
                  await loadRules();
              },
          })
        : null;

    function startPageInitialization() {
        debugLog('开始初始化账户分类页面');
        setupGlobalSearchListener();
        ruleModals?.init();
        classificationModals?.init();
        loadClassifications()
            .then(list => {
                ruleModals?.updateClassificationOptions?.(list);
            })
            .catch(error => debugLog('分类加载失败', error));
        loadRules();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startPageInitialization, { once: true });
    } else {
        startPageInitialization();
    }

    /* ========== 数据加载 ========== */
    async function loadClassifications() {
        try {
            debugLog('开始加载分类');
            const response = await api.classifications.list();
            const list = extractClassifications(response);
            state.classifications = list;
            debugLog('分类加载成功', { count: list.length });
            renderClassifications(list);
            return list;
        } catch (error) {
            handleRequestError(error, '加载分类失败', 'load_classifications');
            renderClassifications([]);
            throw error;
        }
    }

    async function loadRules() {
        try {
            debugLog('开始加载规则');
            const response = await api.rules.list();
            const rulesByDbType = extractRules(response);
            const enriched = await attachRuleStats(rulesByDbType);
            state.rulesByDbType = enriched;
            debugLog('规则加载成功', { dbTypes: Object.keys(enriched).length });
            renderRules(enriched);
        } catch (error) {
            handleRequestError(error, '加载规则失败', 'load_rules');
            renderRules({});
        }
    }

    function extractClassifications(response) {
        const collection = response?.data?.classifications ?? response?.classifications ?? [];
        return Array.isArray(collection) ? collection : [];
    }

    function extractRules(response) {
        const raw = response?.data?.rules_by_db_type ?? response?.rules_by_db_type ?? {};
        return typeof raw === 'object' && raw !== null ? raw : {};
    }

    async function attachRuleStats(rulesByDbType) {
        const ids = collectRuleIds(rulesByDbType);
        if (ids.length === 0) {
            return rulesByDbType;
        }

        try {
            const response = await api.rules.stats(ids);
            const statsList = response?.data?.rule_stats ?? response?.rule_stats ?? [];
            const statsMap = {};
            if (Array.isArray(statsList)) {
                statsList.forEach(item => {
                    if (item && typeof item.rule_id === 'number') {
                        statsMap[item.rule_id] = item.matched_accounts_count ?? 0;
                    }
                });
            }
            Object.values(rulesByDbType).forEach(ruleGroup => {
                if (Array.isArray(ruleGroup)) {
                    ruleGroup.forEach(rule => {
                        if (rule && typeof rule.id === 'number') {
                            rule.matched_accounts_count = statsMap[rule.id] ?? 0;
                        }
                    });
                }
            });
        } catch (error) {
            console.error('加载规则统计失败', error);
        }

        return rulesByDbType;
    }

    function collectRuleIds(rulesByDbType) {
        const ids = [];
        Object.values(rulesByDbType || {}).forEach(ruleGroup => {
            if (Array.isArray(ruleGroup)) {
                ruleGroup.forEach(rule => {
                    if (rule && typeof rule.id === 'number') {
                        ids.push(rule.id);
                    }
                });
            }
        });
        return ids;
    }

    function renderClassifications(classifications) {
        const container = document.getElementById('classificationsList');
        if (!container) {
            return;
        }

        if (!classifications.length) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-box-open"></i>
                    <h5 class="mb-2">暂无分类</h5>
                    <p class="mb-0">点击"新建分类"按钮创建第一个分类</p>
                </div>
            `;
            return;
        }

        container.innerHTML = classifications
            .map(classification => {
                const riskLevelClass =
                    {
                        low: 'success',
                        medium: 'warning',
                        high: 'danger',
                        critical: 'dark',
                    }[classification.risk_level] || 'secondary';

                const iconHtml = getClassificationIcon(classification.icon_name, classification.color);
                const badge = `
                    <span class="position-relative d-inline-block me-2">
                        <span class="badge bg-${riskLevelClass}" style="background-color: ${
                            classification.color || '#6c757d'
                        } !important;">
                            ${classification.name}
                        </span>
                        ${
                            classification.rules_count > 0
                                ? `
                                <span class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger shadow-sm">
                                    ${classification.rules_count}
                                    <span class="visually-hidden">匹配规则数量</span>
                                </span>
                            `
                                : ''
                        }
                    </span>
                `;

                const actionButtons =
                    window.currentUserRole === 'admin'
                        ? `
                            <button class="btn btn-outline-primary" onclick="editClassification(${classification.id})" title="编辑">
                                <i class="fas fa-edit"></i>
                            </button>
                            ${
                                classification.is_system
                                    ? ''
                                    : `
                                <button class="btn btn-outline-danger" onclick="deleteClassification(${classification.id})" title="删除">
                                    <i class="fas ${classification.rules_count ? 'fa-trash' : 'fa-trash-alt'}"></i>
                                </button>
                            `
                            }
                        `
                        : `
                            <span class="btn btn-outline-secondary disabled" title="只读模式">
                                <i class="fas fa-lock"></i>
                            </span>
                        `;

                return `
                    <div class="card mb-2 classification-item" data-id="${classification.id}">
                        <div class="card-body py-2">
                            <div class="d-flex justify-content-between align-items-center">
                                <div class="d-flex align-items-center">
                                    <div class="me-2">${iconHtml}</div>
                                    ${badge}
                                    ${
                                        classification.rules_count > 0
                                            ? ''
                                            : '<small class="text-muted">无匹配</small>'
                                    }
                                </div>
                                <div class="btn-group btn-group-sm">${actionButtons}</div>
                            </div>
                            ${
                                classification.description
                                    ? `<small class="text-muted d-block mt-1">${classification.description}</small>`
                                    : ''
                            }
                        </div>
                    </div>
                `;
            })
            .join('');
    }

    function getClassificationIcon(iconName, color) {
        const iconMap = {
            'fa-crown': 'fas fa-crown',
            'fa-shield-alt': 'fas fa-shield-alt',
            'fa-exclamation-triangle': 'fas fa-exclamation-triangle',
            'fa-user': 'fas fa-user',
            'fa-eye': 'fas fa-eye',
            'fa-tag': 'fas fa-tag',
        };

        const iconClass = iconMap[iconName] || 'fas fa-tag';
        return `<i class="${iconClass}" style="color: ${color || '#6c757d'};"></i>`;
    }

    async function handleDeleteClassification(id) {
        if (!confirm('确定要删除这个分类吗？')) {
            return;
        }

        try {
            const response = await api.classifications.remove(id);
            toast.success(response?.message || '分类删除成功');
            await loadClassifications();
            ruleModals?.updateClassificationOptions(state.classifications);
            await loadRules();
        } catch (error) {
            handleRequestError(error, '删除分类失败', 'delete_classification');
        }
    }

    function renderRules(rulesByDbType) {
        const container = document.getElementById('rulesList');
        if (!container) {
            return;
        }

        const entries = Object.entries(rulesByDbType || {});
        if (entries.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-info-circle"></i>
                    <h5 class="mb-2">暂无规则</h5>
                    <p class="mb-0">点击"新建规则"按钮创建第一个分类规则</p>
                </div>
            `;
            return;
        }

        container.innerHTML = entries
            .map(([dbType, rulesRaw]) => {
                const rules = Array.isArray(rulesRaw) ? rulesRaw : [];
                const dbIcons = {
                    mysql: 'fas fa-database',
                    postgresql: 'fas fa-elephant',
                    sqlserver: 'fas fa-server',
                    oracle: 'fas fa-database',
                };
                const dbIcon = dbIcons[dbType] || 'fas fa-database';

                return `
                    <div class="rule-group-card">
                        <div class="card">
                            <div class="card-header">
                                <h5>
                                    <i class="${dbIcon} me-2 text-primary"></i>${dbType.toUpperCase()} 规则
                                </h5>
                            </div>
                            <div class="card-body">
                                ${
                                    rules.length
                                        ? rules.map(rule => renderRuleRow(rule)).join('')
                                        : '<p class="text-muted mb-0">暂无规则</p>'
                                }
                            </div>
                        </div>
                    </div>
                `;
            })
            .join('');
    }

    function renderRuleRow(rule) {
        const matched = rule.matched_accounts_count ?? 0;
        return `
            <div class="rule-row">
                <div>
                    <h6 class="mb-1">${rule.rule_name || '未命名规则'}</h6>
                    <div class="text-muted small">
                        <span class="me-2">分类：${rule.classification_name || '未分类'}</span>
                        <span class="me-2">数据库：${(rule.db_type || '').toUpperCase()}</span>
                        <span>匹配账户：${matched}</span>
                    </div>
                </div>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="viewRule(${rule.id})">
                        <i class="fas fa-eye"></i>
                    </button>
                    ${
                        window.currentUserRole === 'admin'
                            ? `
                                <button class="btn btn-outline-secondary" onclick="editRule(${rule.id})">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button class="btn btn-outline-danger" onclick="deleteRule(${rule.id})">
                                    <i class="fas fa-trash"></i>
                                </button>
                            `
                            : ''
                    }
                </div>
            </div>
        `;
    }

    /* ========== 自动分类 ========== */
    async function handleAutoClassifyAll(eventArg) {
        const evt = eventArg || window.event;
        const btn = evt?.currentTarget || evt?.target;
        const originalText = btn ? btn.innerHTML : '';

        if (btn) {
            btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>分类中...';
            btn.disabled = true;
        }

        debugLog('触发自动分类所有账户操作');

        try {
            if (!api.automation || typeof api.automation.trigger !== 'function') {
                throw new Error('AccountClassificationService.automation.trigger 未定义');
            }
            const response = await api.automation.trigger({});
            toast.success(response?.message || '自动分类任务已启动');
            setTimeout(() => window.location.reload(), 2000);
        } catch (error) {
            toast.error(error?.response?.error || error.message || '自动分类失败');
            debugLog('自动分类失败', error);
        } finally {
            if (btn) {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        }
    }

    /* ========== 其他辅助 ========== */
    function setupGlobalSearchListener() {
        document.addEventListener('keypress', function (event) {
            if (event.target?.id === 'accountSearchInput' && event.key === 'Enter') {
                const modal = event.target.closest('.modal');
                const ruleId = modal?.dataset?.ruleId;
                if (ruleId && typeof window.searchMatchedAccounts === 'function') {
                    window.searchMatchedAccounts(parseInt(ruleId, 10));
                }
            }
        });
    }

    function handleRequestError(error, fallbackMessage, context) {
        logError(error, context || 'account_classification', {
            fallbackMessage,
        });
        const message = error?.response?.error || error?.message || fallbackMessage || '操作失败';
        if (fallbackMessage) {
            toast.error(message);
        }
    }

    /* ========== 对外暴露（保持旧接口兼容） ========== */
    window.openCreateClassificationModal = event => classificationModals?.openCreate?.(event);
    window.openCreateRuleModal = event => ruleModals?.openCreate?.(event);
    window.createClassification = () => classificationModals?.triggerCreate?.();
    window.editClassification = id => classificationModals?.openEditById?.(id);
    window.updateClassification = () => classificationModals?.triggerUpdate?.();
    window.deleteClassification = handleDeleteClassification;

    window.createRule = () => ruleModals?.triggerCreate?.();
    window.editRule = id => ruleModals?.openEditById?.(id);
    window.updateRule = () => ruleModals?.submitUpdate?.();
    window.deleteRule = id => ruleModals?.deleteRule?.(id);
    window.viewRule = id => ruleModals?.openViewById?.(id);

    window.autoClassifyAll = handleAutoClassifyAll;
    window.loadPermissions = prefix => ruleModals?.loadPermissions?.(prefix) ?? Promise.resolve();
    window.loadClassificationsForRules = () => ruleModals?.updateClassificationOptions?.(state.classifications);

    window.AccountClassificationPage = {
        reload: function reloadPageData() {
            loadClassifications();
            loadRules();
        },
        state,
    };
}

window.AccountClassificationPage = {
    mount: () => mountAccountClassificationPage(window, document),
};
