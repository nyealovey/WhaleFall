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

    const escapeHtml = window.UI?.escapeHtml;
    if (typeof escapeHtml !== 'function') {
        console.error('UI.escapeHtml 未初始化，账户分类页面无法安全渲染');
        return;
    }

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
    const createAccountClassificationStore = window.createAccountClassificationStore;
    if (typeof createAccountClassificationStore !== 'function') {
        console.error('createAccountClassificationStore 未加载，账户分类页面无法初始化');
        return;
    }
    const service = new AccountClassificationService();
    const store = createAccountClassificationStore({ service });

    // 注入依赖: PermissionPolicyCenter 不应自行直连 service.
    if (typeof window.PermissionPolicyCenter?.configure === 'function') {
        window.PermissionPolicyCenter.configure({
            fetchPermissions: store.actions.fetchPermissions,
        });
    }

    /**
     * 将 store actions 封装为页面调用入口(兼容现有 modal controller 的 api 形态)。
     */
    const api = {
        classifications: {
            detail: id => store.actions.fetchClassificationDetail(id),
            create: payload => store.actions.createClassification(payload),
            update: (id, payload) => store.actions.updateClassification(id, payload),
            remove: id => store.actions.deleteClassification(id),
        },
        rules: {
            detail: id => store.actions.fetchRuleDetail(id),
            create: payload => store.actions.createRule(payload),
            update: (id, payload) => store.actions.updateRule(id, payload),
            remove: id => store.actions.deleteRule(id),
        },
        automation: {
            trigger: payload => store.actions.triggerAutomation(payload),
        },
        load: {
            classifications: () => store.actions.loadClassifications(),
            rules: () => store.actions.loadRules(),
        },
    };

    const toast = window.toast;
    if (!toast?.success || !toast?.error) {
        console.error('toast 未初始化，账户分类页面无法提示');
        return;
    }

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
              onMutated: null,
              getClassificationOptions: () => store.getState().classifications,
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
              onMutated: null,
          })
        : null;

    function resolveActionErrorMessage(action) {
        switch (action) {
            case 'loadClassifications':
                return '加载分类失败';
            case 'loadRules':
                return '加载规则失败';
            case 'loadRuleStats':
                return '加载规则统计失败';
            case 'createClassification':
                return '创建分类失败';
            case 'updateClassification':
                return '更新分类失败';
            case 'deleteClassification':
                return '删除分类失败';
            case 'createRule':
                return '创建规则失败';
            case 'updateRule':
                return '更新规则失败';
            case 'deleteRule':
                return '删除规则失败';
            case 'triggerAutomation':
                return '自动分类失败';
            case 'fetchPermissions':
                return '加载权限配置失败';
            default:
                return '操作失败';
        }
    }

    function handleStoreError(payload) {
        const error = payload?.error || payload;
        const action = payload?.meta?.action;
        const fallback = resolveActionErrorMessage(action);
        handleRequestError(error, fallback, action || 'account_classification_store');
        if (action === 'loadClassifications') {
            renderClassifications([]);
        }
        if (action === 'loadRules') {
            renderRules({});
        }
    }

    store.subscribe('accountClassification:classificationsUpdated', (payload) => {
        const list = payload?.classifications || store.getState().classifications;
        renderClassifications(list);
        ruleModals?.updateClassificationOptions?.(list);
    });

    store.subscribe('accountClassification:rulesUpdated', (payload) => {
        const rulesByDbType = payload?.rulesByDbType || store.getState().rulesByDbType;
        renderRules(rulesByDbType);
    });

    store.subscribe('accountClassification:error', handleStoreError);

    /**
     * 页面入口：初始化模态、加载分类与规则。
     *
     * @param {Event} [event] 触发事件（可选）。
     * @returns {void}
     */
    function startPageInitialization() {
        debugLog('开始初始化账户分类页面');
        bindTemplateActions();
        setupGlobalSearchListener();
        ruleModals?.init();
        classificationModals?.init();
        store.actions.loadClassifications().catch(error => debugLog('分类加载失败', error));
        store.actions.loadRules().catch(error => debugLog('规则加载失败', error));
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startPageInitialization, { once: true });
    } else {
        startPageInitialization();
    }

    /**
     * 打开规则详情。
     *
     * @param {string|number} ruleId 规则 ID。
     * @returns {void}
     */
    function viewRule(ruleId) {
        if (!ruleId) {
            toast.error('未找到规则 ID');
            return;
        }
        ruleModals?.openViewById?.(ruleId);
    }

    /**
     * 打开规则编辑。
     *
     * @param {string|number} ruleId 规则 ID。
     * @returns {void}
     */
    function editRule(ruleId) {
        if (!ruleId) {
            toast.error('未找到规则 ID');
            return;
        }
        ruleModals?.openEditById?.(ruleId);
    }

    /**
     * 删除规则并刷新列表。
     *
     * @param {string|number} ruleId 规则 ID。
     * @returns {Promise<void>}
     */
    async function deleteRule(ruleId) {
        if (!ruleId) {
            toast.error('未找到规则 ID');
            return;
        }

        const confirmDanger = window.UI?.confirmDanger;
        if (typeof confirmDanger !== 'function') {
            toast.error('确认组件未初始化');
            return;
        }

        const confirmed = await confirmDanger({
            title: '确认删除规则',
            message: '该操作不可撤销，请确认后继续。',
            details: [
                { label: '规则 ID', value: String(ruleId), tone: 'danger' },
                { label: '不可撤销', value: '删除后将无法恢复', tone: 'danger' },
            ],
            confirmText: '确认删除',
            confirmButtonClass: 'btn-danger',
        });
        if (!confirmed) {
            return;
        }
        try {
            await api.rules.remove(ruleId);
            toast.success('规则已删除');
        } catch (error) {
            handleRequestError(error, '删除规则失败', 'delete_rule');
        }
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

        const list = Array.isArray(classifications) ? classifications : [];
        if (!list.length) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-box-open"></i>
                    <p class="mt-2 mb-0">暂无分类，点击“新建分类”开始配置</p>
                </div>
            `;
            return;
        }

        container.innerHTML = list.map(renderClassificationCard).join('');
    }

    function renderClassificationCard(classification) {
        const iconHtml = getClassificationIcon(classification.icon_name);
        const priority = typeof classification.priority === 'number' ? classification.priority : '—';
        const rulesCount = typeof classification.rules_count === 'number' ? classification.rules_count : 0;
        const chips = [
            renderLedgerChip(`优先级 ${priority}`, 'muted'),
            renderLedgerChip(`规则 ${rulesCount}`, 'muted'),
        ];

        return `
            <div class="classification-card" data-id="${escapeHtml(classification?.id ?? '')}">
                <div class="classification-card__header">
                    <div class="classification-card__title">
                        ${iconHtml}
                        <div>
                            <div class="classification-card__name-row">
                                <div class="classification-card__name">${escapeHtml(classification?.name || '未命名分类')}</div>
                                <div class="classification-card__badges">
                                    ${renderSystemClassificationPill(classification.is_system)}
                                    ${renderRiskLevelPill(classification.risk_level)}
                                </div>
                            </div>
                            <div class="small text-muted"><code>${escapeHtml(classification?.code || '-')}</code></div>
                        </div>
                    </div>
                    <div class="classification-card__actions">
                        ${renderClassificationActions(classification)}
                    </div>
                </div>
                ${
                    classification.description
                        ? `<p class="classification-card__desc">${escapeHtml(classification.description)}</p>`
                        : ''
                }
                <div class="ledger-chip-stack">${chips.join('')}</div>
            </div>
        `;
    }

    function renderClassificationActions(classification) {
        if (window.currentUserRole !== 'admin') {
            return `
                <span class="btn btn-outline-secondary btn-sm btn-icon disabled" title="只读模式">
                    <i class="fas fa-lock"></i>
                </span>
            `;
        }

        const editButton = `
            <button type="button" class="btn btn-outline-secondary btn-sm btn-icon" data-action="edit-classification" data-classification-id="${escapeHtml(classification?.id ?? '')}" title="编辑分类">
                <i class="fas fa-edit"></i>
            </button>
        `;
        const deleteButton = classification.is_system
            ? ''
            : `
                <button type="button" class="btn btn-outline-danger btn-sm btn-icon" data-action="delete-classification" data-classification-id="${escapeHtml(classification?.id ?? '')}" title="删除分类">
                    <i class="fas fa-trash"></i>
                </button>
            `;
        return `${editButton}${deleteButton}`;
    }

    const UNSAFE_KEYS = ['__proto__', 'prototype', 'constructor'];
    const isSafeKey = (key) => typeof key === 'string' && !UNSAFE_KEYS.includes(key);

    function getClassificationIcon(iconName) {
        let iconClass = 'fas fa-tag';
        if (isSafeKey(iconName)) {
            switch (iconName) {
                case 'fa-crown':
                    iconClass = 'fas fa-crown';
                    break;
                case 'fa-shield-alt':
                    iconClass = 'fas fa-shield-alt';
                    break;
                case 'fa-exclamation-triangle':
                    iconClass = 'fas fa-exclamation-triangle';
                    break;
                case 'fa-user':
                    iconClass = 'fas fa-user';
                    break;
                case 'fa-eye':
                    iconClass = 'fas fa-eye';
                    break;
                case 'fa-tag':
                    iconClass = 'fas fa-tag';
                    break;
                default:
                    break;
            }
        }
        return `<span class="classification-card__icon"><i class="${iconClass}"></i></span>`;
    }

    function renderRiskLevelPill(riskLevel) {
        const level = Number(riskLevel);
        let preset = { text: '4级(默认)', tone: 'info', icon: 'fa-info-circle' };
        switch (level) {
            case 1:
                preset = { text: '1级(最高)', tone: 'danger', icon: 'fa-skull-crossbones' };
                break;
            case 2:
                preset = { text: '2级', tone: 'danger', icon: 'fa-exclamation-triangle' };
                break;
            case 3:
                preset = { text: '3级', tone: 'warning', icon: 'fa-exclamation-circle' };
                break;
            case 4:
                preset = { text: '4级(默认)', tone: 'info', icon: 'fa-info-circle' };
                break;
            case 5:
                preset = { text: '5级', tone: 'muted', icon: 'fa-shield-alt' };
                break;
            case 6:
                preset = { text: '6级(最低)', tone: 'muted', icon: 'fa-eye' };
                break;
            default:
                preset = { text: '未标记风险', tone: 'muted', icon: 'fa-question-circle' };
                break;
        }
        return renderStatusPill(preset.text, preset.tone, preset.icon);
    }

    function renderSystemClassificationPill(isSystem) {
        return isSystem ? renderStatusPill('系统', 'muted', 'fa-lock') : '';
    }

    function renderLedgerChip(label, modifier) {
        if (!label) {
            return '';
        }
        const modifierClass = modifier ? ` ledger-chip--${modifier}` : '';
        return `<span class="ledger-chip${modifierClass}">${escapeHtml(label)}</span>`;
    }

    function renderStatusPill(label, tone = 'muted', icon, title) {
        const toneClass = tone ? ` status-pill--${tone}` : '';
        const iconHtml = icon ? `<i class="fas ${icon}"></i>` : '';
        const safeLabel = escapeHtml(label ?? '');
        const safeTitle = title === undefined || title === null ? '' : escapeHtml(title);
        const titleAttr = safeTitle ? ` title="${safeTitle}"` : '';
        return `<span class="status-pill${toneClass}"${titleAttr}>${iconHtml}${safeLabel}</span>`;
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

        const entries = Object.entries(rulesByDbType || {}).map(([dbType, rulesRaw]) => [dbType, Array.isArray(rulesRaw) ? rulesRaw : []]);
        const meaningfulEntries = entries.filter(([, rules]) => rules.length > 0);

        if (!meaningfulEntries.length) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-info-circle"></i>
                    <p class="mt-2 mb-0">暂无规则，点击“新建规则”开始配置</p>
                </div>
            `;
            return;
        }

        container.innerHTML = meaningfulEntries.map(([dbType, rules]) => renderRuleGroup(dbType, rules)).join('');
    }

    function renderRuleGroup(dbType, rules) {
        const dbIcon = resolveDbIcon(dbType);
        const label = `${(dbType || 'unknown').toUpperCase()} 规则`;
        return `
            <div class="rule-group-card">
                <div class="rule-group-card__header">
                    <div class="rule-group-card__title">
                        <i class="${dbIcon} text-primary"></i>
                        <span>${escapeHtml(label)}</span>
                    </div>
                    ${renderStatusPill(`${rules.length}`, 'muted', 'fa-layer-group', `规则数 ${rules.length}`)}
                </div>
                <div class="rule-list">
                    ${rules.map(rule => renderRuleRow(rule)).join('')}
                </div>
            </div>
        `;
    }

    /**
     * 单条规则的渲染行。
     *
     * @param {Object} rule 规则对象。
     * @returns {string} 规则卡片 HTML。
     */
    function renderRuleRow(rule) {
        const count = Number(rule?.matched_accounts_count) || 0;
        return `
            <div class="rule-card">
                <div class="rule-card__body">
                    <div class="rule-card__info">
                        <div class="rule-card__title">${escapeHtml(rule?.rule_name || '')}</div>
                        <div class="rule-card__classification">
                            ${renderLedgerChip(rule.classification_name || '未分类', 'brand')}
                        </div>
                        <div class="rule-card__states">
                            ${renderMatchedAccountsPill(count)}
                        </div>
                    </div>
                    <div class="rule-actions">${renderRuleActions(rule)}</div>
                </div>
            </div>
        `;
    }

    function renderMatchedAccountsPill(count) {
        const total = Number(count) || 0;
        const tone = total > 0 ? 'info' : 'muted';
        const label = `${total}`;
        return renderStatusPill(label, tone, 'fa-users');
    }

    function renderRuleActions(rule) {
        if (window.currentUserRole !== 'admin') {
            return `
                <span class="btn btn-outline-secondary btn-sm btn-icon disabled" title="只读模式">
                    <i class="fas fa-lock"></i>
                </span>
            `;
        }
        return `
            <button type="button" class="btn btn-outline-secondary btn-sm btn-icon" data-action="view-rule" data-rule-id="${escapeHtml(rule?.id ?? '')}" title="查看详情">
                <i class="fas fa-eye"></i>
            </button>
            <button type="button" class="btn btn-outline-secondary btn-sm btn-icon" data-action="edit-rule" data-rule-id="${escapeHtml(rule?.id ?? '')}" title="编辑规则">
                <i class="fas fa-edit"></i>
            </button>
            <button type="button" class="btn btn-outline-danger btn-sm btn-icon" data-action="delete-rule" data-rule-id="${escapeHtml(rule?.id ?? '')}" title="删除规则">
                <i class="fas fa-trash"></i>
            </button>
        `;
    }

    function resolveDbIcon(dbType) {
        const normalized = (dbType || '').toLowerCase();
        if (!isSafeKey(normalized)) {
            return 'fas fa-database';
        }
        switch (normalized) {
            case 'mysql':
                return 'fas fa-database';
            case 'postgresql':
                return 'fas fa-elephant';
            case 'sqlserver':
                return 'fas fa-server';
            case 'oracle':
                return 'fas fa-database';
            case 'redis':
                return 'fas fa-database';
            default:
                return 'fas fa-database';
        }
    }

    /**
     * 打开分类编辑模态。
     *
     * @param {string|number|null} id 分类 ID。
     * @returns {void}
     */
    function editClassification(id) {
        if (!id) {
            toast.error('未找到分类 ID');
            return;
        }
        classificationModals?.openEditById?.(id);
    }

    /**
     * 删除分类（带二次确认）并刷新列表。
     *
     * @param {string|number|null} id 分类 ID。
     * @returns {Promise<void>} 完成后 resolve。
     */
    async function deleteClassification(id) {
        const parsedId = typeof id === 'string' ? parseInt(id, 10) : Number(id);
        if (!parsedId) {
            toast.error('未找到分类 ID');
            return;
        }
        await handleDeleteClassification(parsedId);
    }

    /**
     * 删除分类后刷新列表并同步规则模态选择项。
     *
     * @param {number} id 分类 ID。
     * @returns {Promise<void>} 完成后 resolve。
     */
    async function handleDeleteClassification(id) {
        const confirmDanger = window.UI?.confirmDanger;
        if (typeof confirmDanger !== 'function') {
            toast.error('确认组件未初始化');
            return;
        }

        const confirmed = await confirmDanger({
            title: '确认删除分类',
            message: '该操作不可撤销，请确认后继续。',
            details: [
                { label: '分类 ID', value: String(id), tone: 'danger' },
                { label: '不可撤销', value: '删除后将无法恢复', tone: 'danger' },
            ],
            confirmText: '确认删除',
            confirmButtonClass: 'btn-danger',
        });
        if (!confirmed) {
            return;
        }

        try {
            const response = await api.classifications.remove(id);
            toast.success(response?.message || '分类删除成功');
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

    /**
     * 绑定模板内 data-action 触发器，替代内联 onclick。
     *
     * @returns {void}
     */
    function bindTemplateActions() {
        const root = document;
        root.addEventListener('click', (event) => {
            const actionEl = event.target.closest('[data-action]');
            if (!actionEl) {
                return;
            }
            const action = actionEl.getAttribute('data-action');
            const actionEvent = { ...event, currentTarget: actionEl, target: actionEl };
            switch (action) {
                case 'auto-classify-all':
                    event.preventDefault();
                    handleAutoClassifyAll(actionEvent);
                    break;
                case 'open-create-classification':
                    event.preventDefault();
                    classificationModals?.openCreate?.(actionEvent);
                    break;
                case 'open-create-rule':
                    event.preventDefault();
                    ruleModals?.openCreate?.(actionEvent);
                    break;
                case 'edit-classification':
                    event.preventDefault();
                    editClassification(actionEl.getAttribute('data-classification-id'));
                    break;
                case 'delete-classification':
                    event.preventDefault();
                    deleteClassification(actionEl.getAttribute('data-classification-id'));
                    break;
                case 'view-rule':
                    event.preventDefault();
                    viewRule(actionEl.getAttribute('data-rule-id'));
                    break;
                case 'edit-rule':
                    event.preventDefault();
                    editRule(actionEl.getAttribute('data-rule-id'));
                    break;
                case 'delete-rule':
                    event.preventDefault();
                    deleteRule(actionEl.getAttribute('data-rule-id'));
                    break;
                default:
                    break;
            }
        });
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
        console.error(`[AccountClassificationPage] ${context || 'account_classification'}`, error, {
            fallbackMessage,
        });
        const message = error?.response?.error || error?.message || fallbackMessage || '操作失败';
        if (fallbackMessage) {
            toast.error(message);
        }
        return message;
    }

}

// 提前注册页面入口，供 page-loader 查找。
window.AccountClassificationPage = {
    mount: () => mountAccountClassificationPage(window, document),
};
