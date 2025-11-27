/**
 * 挂载账户分类管理页面。
 *
 * 初始化账户分类管理页面的所有组件，包括分类列表、规则管理、
 * 创建/编辑/删除模态框等功能。支持账户分类和规则的 CRUD 操作。
 *
 * @param {Window} window - 全局 window 对象
 * @param {Document} document - document 对象
 * @return {void}
 *
 * @example
 * // 在页面加载时调用
 * mountAccountClassificationPage(window, document);
 */
function mountAccountClassificationPage(window, document) {
    'use strict';

    const debugEnabled = window.DEBUG_ACCOUNT_CLASSIFICATION ?? true;
    window.DEBUG_ACCOUNT_CLASSIFICATION = debugEnabled;

    /**
     * 统一的调试日志输出。
     *
     * @param {string} message 文本描述。
     * @param {*} [payload] 可选上下文对象。
     * @returns {void}
     */
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
    /**
     * 将服务的各 API 封装为前端调用入口。
     */
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
        /**
         * 默认错误记录器，控制台兜底输出。
         *
         * @param {Error|Object|string} error 捕获的错误。
         * @param {string} context 错误发生场景。
         * @param {Object} [extras] 附加信息。
         * @returns {void}
         */
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

    /**
     * 页面入口：初始化模态、加载分类与规则。
     *
     * @param {Event} [event] 触发事件（可选）。
     * @returns {void}
     */
    function startPageInitialization(event) {
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
    /**
     * 拉取分类列表并渲染，同时缓存 state。
     */
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

    /**
     * 拉取规则列表，附加统计信息后渲染。
     */
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

    /**
     * 从接口响应提取分类数组，兼容多种结构。
     *
     * @param {Object} response API 响应对象。
     * @returns {Array<Object>} 分类数组。
     */
    function extractClassifications(response) {
        const collection = response?.data?.classifications ?? response?.classifications ?? [];
        return Array.isArray(collection) ? collection : [];
    }

    /**
     * 从接口响应提取按 db_type 分类的规则对象。
     *
     * @param {Object} response API 响应对象。
     * @returns {Object} 以 db_type 为键的规则映射。
     */
    function extractRules(response) {
        const raw = response?.data?.rules_by_db_type ?? response?.rules_by_db_type ?? {};
        return typeof raw === 'object' && raw !== null ? raw : {};
    }

    /**
     * 为规则字典附加匹配账户数统计。
     *
     * @param {Object} rulesByDbType 原始规则字典。
     * @returns {Promise<Object>} 附加统计后的规则字典。
     */
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

    /**
     * 将 rulesByDbType 拆平，收集规则 ID 列表。
     *
     * @param {Object} rulesByDbType 规则分组。
     * @returns {Array<number>} 规则 ID 数组。
     */
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

    /**
     * 分类列表渲染。
     *
     * @param {Array<Object>} classifications 分类数组。
     * @returns {void}
     */
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
                const badgeColor = classification.color || 'var(--gray-600)';
                const badge = `
                    <span class="position-relative d-inline-block me-2">
                        <span class="badge bg-${riskLevelClass}" style="background-color: ${
                            badgeColor
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

    /**
     * 根据配置生成分类图标 HTML。
     *
     * @param {string} iconName FontAwesome 图标名。
     * @param {string} [color] Hex 或 CSS 颜色值。
     * @returns {string} HTML 片段。
     */
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
        return `<i class="${iconClass}" style="color: ${color || 'var(--gray-600)'};"></i>`;
    }

    /**
     * 渲染按 DB 类型分组的规则卡片。
     *
     * @param {Object} rulesByDbType 规则映射。
     * @returns {void}
     */
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
                                    <span class="badge bg-primary ms-2 rounded-pill">${rules.length}</span>
                                </h5>
                            </div>
                            <div class="card-body">
                                ${
                                    rules.length > 0
                                        ? `
                                        <div class="rule-list">
                                            ${rules.map(rule => renderRuleRow(rule)).join('')}
                                        </div>
                                    `
                                        : `
                                        <div class="text-center text-muted py-5">
                                            <i class="fas fa-info-circle fa-3x mb-3 text-muted"></i>
                                            <p class="mb-0">暂无${dbType.toUpperCase()}规则</p>
                                            <small class="text-muted">点击"新建规则"按钮创建第一个规则</small>
                                        </div>
                                    `
                                }
                            </div>
                        </div>
                    </div>
                `;
            })
            .join('');
    }

    /**
     * 单条规则的渲染行。
     *
     * @param {Object} rule 规则对象。
     * @returns {string} 规则卡片 HTML。
     */
    function renderRuleRow(rule) {
        const classificationBadge = `
            <span class="rule-classification-badge ${getClassificationClass(rule.classification_name)}">
                ${rule.classification_name || '未分类'}
            </span>
        `;
        const count = typeof rule.matched_accounts_count === 'number' ? rule.matched_accounts_count : 0;

        const actions =
            window.currentUserRole === 'admin'
                ? `
                    <button class="btn btn-outline-info" onclick="viewRule(${rule.id})" title="查看详情">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-outline-primary" onclick="editRule(${rule.id})" title="编辑规则">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteRule(${rule.id})" title="删除规则">
                        <i class="fas fa-trash"></i>
                    </button>
                `
                : `
                    <span class="btn btn-outline-secondary disabled" title="只读模式">
                        <i class="fas fa-lock"></i>
                    </span>
                `;

        return `
            <div class="rule-item">
                <div class="rule-card">
                    <div class="card-body">
                        <div class="row align-items-center">
                            <div class="col-3">
                                <h6 class="card-title mb-0">${rule.rule_name}</h6>
                            </div>
                            <div class="col-4">
                                <div class="d-flex align-items-center justify-content-center gap-1">
                                    ${classificationBadge}
                                    <span class="db-type-badge">${(rule.db_type || '').toUpperCase()}</span>
                                </div>
                            </div>
                            <div class="col-3 text-center">
                                <span class="badge accounts-count-badge" data-count="${count}">
                                    <i class="fas fa-users me-1"></i>${count} 个账户
                                </span>
                            </div>
                            <div class="col-2">
                                <div class="rule-actions">${actions}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * 简单根据名称判断分类样式。
     *
     * @param {string} name 分类名称。
     * @returns {string} CSS 类名。
     */
    function getClassificationClass(name) {
        if (!name) return 'normal';
        if (name.includes('特权')) return 'privileged';
        if (name.includes('敏感')) return 'sensitive';
        if (name.includes('风险')) return 'risk';
        if (name.includes('只读')) return 'readonly';
        return 'normal';
    }

    /**
     * 删除分类后刷新列表并同步规则模态选择项。
     *
     * @param {number} id 分类 ID。
     * @returns {Promise<void>} 完成后 resolve。
     */
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
    /**
     * 监听规则详情弹窗中的 Enter 键快捷搜索事件。
     *
     * @param {Document} [doc=document] 可选文档对象。
     * @returns {void}
     */
    function setupGlobalSearchListener(doc) {
        const targetDoc = doc || document;
        targetDoc.addEventListener('keypress', function (event) {
            if (event.target?.id === 'accountSearchInput' && event.key === 'Enter') {
                const modal = event.target.closest('.modal');
                const ruleId = modal?.dataset?.ruleId;
                if (ruleId && typeof window.searchMatchedAccounts === 'function') {
                    window.searchMatchedAccounts(parseInt(ruleId, 10));
                }
            }
        });
    }

    /**
     * 统一处理请求失败并展示提示。
     *
     * @param {Error|Object} error 后端或前端错误。
     * @param {string} [fallbackMessage] 默认提示文本。
     * @param {string} [context] 日志上下文。
     * @returns {string} 最终展示的错误消息文本。
     */
    function handleRequestError(error, fallbackMessage, context) {
        logError(error, context || 'account_classification', {
            fallbackMessage,
        });
        const message = error?.response?.error || error?.message || fallbackMessage || '操作失败';
        if (fallbackMessage) {
            toast.error(message);
        }
        return message;
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
