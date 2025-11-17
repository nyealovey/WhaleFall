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
    const api = new AccountClassificationService(window.httpU);

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

    const modals = {
        createClassification: null,
        editClassification: null,
        createRule: null,
        editRule: null,
        viewRule: null,
    };

    const validators = {
        createClassification: null,
        editClassification: null,
        createRule: null,
    };

    document.addEventListener('DOMContentLoaded', function onReady() {
        debugLog('DOM Ready，开始初始化页面');
        initializeModals();
        setupColorPreviewListeners();
        setupGlobalSearchListener();
        initFormValidators();

        loadClassifications()
            .then(() => {
                debugLog('分类加载完成，填充规则下拉');
                return loadClassificationsForRules();
            })
            .catch(error => {
                debugLog('分类加载失败，依旧尝试填充规则下拉', error);
                return loadClassificationsForRules();
            });
        loadRules();
        loadPermissions().catch(error => {
            debugLog('权限配置加载失败', error);
        });
    });

    function initializeModals() {
        const factory = window.UI?.createModal;
        if (!factory) {
            throw new Error('UI.createModal 未加载，账户分类模态无法初始化');
        }
        debugLog('初始化模态...');
        modals.createClassification = factory({
            modalSelector: '#createClassificationModal',
            onConfirm: () => triggerCreateClassification(),
            onClose: resetCreateClassificationForm,
        });
        modals.editClassification = factory({
            modalSelector: '#editClassificationModal',
            onConfirm: () => triggerUpdateClassification(),
            onClose: resetEditClassificationForm,
        });
        modals.createRule = factory({
            modalSelector: '#createRuleModal',
            onConfirm: () => triggerCreateRule(),
            onClose: resetCreateRuleForm,
            size: 'lg',
        });
        modals.editRule = factory({
            modalSelector: '#editRuleModal',
            onConfirm: () => submitUpdateRule(),
            onClose: resetEditRuleForm,
            size: 'lg',
        });
        modals.viewRule = factory({
            modalSelector: '#viewRuleModal',
            onClose: resetViewRuleModal,
            size: 'lg',
        });
    }

    function ensureModalInstance(key) {
        const instance = modals[key];
        if (!instance) {
            console.error(`模态未初始化: ${key}`);
            return {
                open: () => {},
                close: () => {},
            };
        }
        return instance;
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
            populateRuleClassificationSelect('ruleClassification', list);
            populateRuleClassificationSelect('editRuleClassification', list);
            return list;
        } catch (error) {
            handleRequestError(error, '加载分类失败', 'load_classifications');
            renderClassifications([]);
            debugLog('分类加载失败', error);
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
            debugLog('规则加载失败', error);
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

    /* ========== 分类渲染 & 处理 ========== */
    function renderClassifications(classifications) {
        const container = document.getElementById('classificationsList');
        if (!container) {
            return;
        }

        const list = Array.isArray(classifications) ? classifications : [];
        if (list.length === 0) {
            container.innerHTML =
                '<div class="text-center text-muted py-3"><i class="fas fa-info-circle me-2"></i>暂无分类</div>';
            return;
        }

        container.innerHTML = list
            .map(classification => {
                const riskLevelClass = {
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
                                    <i class="fas fa-trash"></i>
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

    function openCreateClassificationModal(eventArg) {
        eventArg?.preventDefault?.();
        resetCreateClassificationForm();
        ensureModalInstance('createClassification').open();
    }

    function openCreateRuleModal(eventArg) {
        eventArg?.preventDefault?.();
        resetCreateRuleForm();
        ensureModalInstance('createRule').open();
    }

    function openEditClassificationModal(eventArg) {
        eventArg?.preventDefault?.();
        resetEditClassificationForm();
        ensureModalInstance('editClassification').open();
    }

    async function handleEditClassification(id) {
        try {
            const response = await api.classifications.detail(id);
            const classification = response?.data?.classification ?? response?.classification;
            if (!classification) {
                toast.error('未获取到分类信息');
                return;
            }

            fillEditClassificationForm(classification);

            openEditClassificationModal();
        } catch (error) {
            handleRequestError(error, '获取分类信息失败', 'edit_classification');
        }
    }

    function fillEditClassificationForm(classification) {
        document.getElementById('editClassificationId').value = classification.id;
        document.getElementById('editClassificationName').value = classification.name || '';
        document.getElementById('editClassificationDescription').value = classification.description || '';
        document.getElementById('editClassificationRiskLevel').value = classification.risk_level || 'medium';
        document.getElementById('editClassificationColor').value = classification.color_key || classification.color || '';
        document.getElementById('editClassificationPriority').value = classification.priority ?? 0;

        const iconName = classification.icon_name || 'fa-tag';
        const radio = document.querySelector(`input[name="editClassificationIcon"][value="${iconName}"]`);
        if (radio) {
            radio.checked = true;
        } else {
            const fallback = document.querySelector('input[name="editClassificationIcon"][value="fa-tag"]');
            if (fallback) {
                fallback.checked = true;
            }
        }

        updateColorPreview('editColorPreview', document.getElementById('editClassificationColor'));
    }

    async function handleDeleteClassification(id) {
        if (!confirm('确定要删除这个分类吗？')) {
            return;
        }

        try {
            const response = await api.classifications.remove(id);
            toast.success(response?.message || '分类删除成功');
            await loadClassifications();
            await loadRules();
        } catch (error) {
            handleRequestError(error, '删除分类失败', 'delete_classification');
        }
    }

function triggerCreateClassification() {
        if (validators.createClassification) {
            validators.createClassification.revalidate();
            return;
        }
        const form = document.getElementById('createClassificationForm');
        if (form) {
            submitCreateClassification(form);
        }
    }

    function triggerUpdateClassification() {
        if (validators.editClassification) {
            if (typeof validators.editClassification.revalidate === 'function') {
                validators.editClassification.revalidate();
                return;
            }
            if (validators.editClassification.instance) {
                validators.editClassification.instance.revalidate();
                return;
            }
        }

        const form = document.getElementById('editClassificationForm');
        if (form) {
            submitUpdateClassification(form);
        }
    }

    async function submitCreateClassification(form) {
        const payload = collectClassificationPayload(form, {
            name: '#classificationName',
            description: '#classificationDescription',
            riskLevel: '#riskLevel',
            color: '#classificationColor',
            priority: '#priority',
            iconSelector: 'input[name="classificationIcon"]:checked',
        });

        if (!payload) {
            return;
        }

        try {
            const response = await api.classifications.create(payload);
            toast.success(response?.message || '分类创建成功');
            ensureModalInstance('createClassification').close();
            form.reset();
            resetColorPreview('colorPreview');
            refreshValidator(validators.createClassification);
            await loadClassifications();
        } catch (error) {
            handleRequestError(error, '创建分类失败', 'create_classification');
        }
    }

    async function submitUpdateClassification(form) {
        const payload = collectClassificationPayload(form, {
            name: '#editClassificationName',
            description: '#editClassificationDescription',
            riskLevel: '#editClassificationRiskLevel',
            color: '#editClassificationColor',
            priority: '#editClassificationPriority',
            iconSelector: 'input[name="editClassificationIcon"]:checked',
        });

        const id = form.querySelector('#editClassificationId')?.value;
        if (!payload || !id) {
            toast.error('请填写完整的分类信息');
            return;
        }

        try {
            const response = await api.classifications.update(id, payload);
            toast.success(response?.message || '分类更新成功');
            ensureModalInstance('editClassification').close();
            resetColorPreview('editColorPreview');
            refreshValidator(validators.editClassification);
            await loadClassifications();
        } catch (error) {
            handleRequestError(error, '更新分类失败', 'update_classification');
        }
    }

    function collectClassificationPayload(form, selectors) {
        const nameInput = form.querySelector(selectors.name);
        const colorSelect = form.querySelector(selectors.color);
        const priorityInput = form.querySelector(selectors.priority);
        const descriptionInput = form.querySelector(selectors.description);
        const riskLevelSelect = form.querySelector(selectors.riskLevel);
        const iconRadio = form.querySelector(selectors.iconSelector);

        const payload = {
            name: nameInput ? nameInput.value.trim() : '',
            description: descriptionInput ? descriptionInput.value.trim() : '',
            risk_level: riskLevelSelect ? riskLevelSelect.value : 'medium',
            color: colorSelect ? colorSelect.value : '',
            priority: parsePriority(priorityInput ? priorityInput.value : ''),
            icon_name: iconRadio ? iconRadio.value : 'fa-tag',
        };

        if (!payload.name || !payload.color) {
            toast.error('请填写完整的分类信息');
            return null;
        }

        return payload;
    }

    function parsePriority(value) {
        if (value === '' || value === null || value === undefined) {
            return 0;
        }
        const parsed = parseInt(value, 10);
        return Number.isFinite(parsed) ? parsed : 0;
    }

    /* ========== 规则渲染 & 处理 ========== */
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
                            <div class="col-2">
                                <span class="badge accounts-count-badge" data-count="${count}">
                                    <i class="fas fa-users me-1"></i>${count} 个账户
                                </span>
                            </div>
                            <div class="col-3">
                                <div class="rule-actions">${actions}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    function getClassificationClass(name) {
        if (!name) return 'normal';
        if (name.includes('特权')) return 'privileged';
        if (name.includes('敏感')) return 'sensitive';
        if (name.includes('风险')) return 'risk';
        if (name.includes('只读')) return 'readonly';
        return 'normal';
    }

function triggerCreateRule() {
        if (validators.createRule) {
            validators.createRule.revalidate();
            return;
        }
        const form = document.getElementById('createRuleForm');
        if (form) {
            submitCreateRule(form);
        }
    }

    async function submitCreateRule(form) {
        const payload = collectRulePayload(form, {
            idField: '#ruleId',
            classification: '#ruleClassification',
            name: '#ruleName',
            dbType: '#ruleDbType',
            operator: '#ruleOperator',
            permissionsContainer: 'permissionsConfig',
            prefix: '',
        });

        if (!payload) {
            return;
        }

        try {
            const response = await api.rules.create(payload);
            toast.success(response?.message || '规则创建成功');
            ensureModalInstance('createRule').close();
            form.reset();
            refreshValidator(validators.createRule);
            await loadRules();
        } catch (error) {
            handleRequestError(error, '创建规则失败', 'create_rule');
        }
    }

    async function handleEditRule(id) {
        try {
            const response = await api.rules.detail(id);
            const rule = response?.data?.rule ?? response?.rule;
            if (!rule) {
                toast.error('未获取到规则信息');
                return;
            }
            resetViewRuleModal();

            await loadClassificationsForRules('edit');
            resetEditRuleForm();

            document.getElementById('editRuleId').value = rule.id;
            document.getElementById('editRuleName').value = rule.rule_name || '';
            document.getElementById('editRuleClassification').value = rule.classification_id || '';
            document.getElementById('editRuleDbType').value = rule.db_type || '';
            document.getElementById('editRuleDbTypeHidden').value = rule.db_type || '';
            document.getElementById('editRuleOperator').value =
                (rule.rule_expression && rule.rule_expression.operator) || 'OR';

            ensureModalInstance('editRule').open();
            loadPermissions('edit')
                .then(() => {
                    if (
                        window.PermissionPolicyCenter &&
                        typeof window.PermissionPolicyCenter.setSelected === 'function'
                    ) {
                        window.PermissionPolicyCenter.setSelected(
                            rule.db_type,
                            rule.rule_expression,
                            'editPermissionsConfig',
                            'edit'
                        );
                    }
                })
                .catch(err => handleRequestError(err, '加载权限配置失败', 'edit_rule_permissions'));
        } catch (error) {
            handleRequestError(error, '获取规则信息失败', 'edit_rule');
        }
    }

    async function submitUpdateRule() {
        const form = document.getElementById('editRuleForm');
        if (!form) {
            return;
        }

        const payload = collectRulePayload(form, {
            idField: '#editRuleId',
            classification: '#editRuleClassification',
            name: '#editRuleName',
            dbType: '#editRuleDbTypeHidden',
            operator: '#editRuleOperator',
            permissionsContainer: 'editPermissionsConfig',
            prefix: 'edit',
        });

        if (!payload) {
            return;
        }

        const ruleId = form.querySelector('#editRuleId')?.value;

        try {
            const response = await api.rules.update(ruleId, payload);
            toast.success(response?.message || '规则更新成功');
            ensureModalInstance('editRule').close();
            await loadRules();
        } catch (error) {
            handleRequestError(error, '更新规则失败', 'update_rule');
        }
    }

    function collectRulePayload(form, options) {
        if (!ensurePermissionCenter()) {
            return null;
        }

        const classificationId = form.querySelector(options.classification)?.value;
        const ruleName = form.querySelector(options.name)?.value;
        const dbType = form.querySelector(options.dbType)?.value;
        const operator = form.querySelector(options.operator)?.value || 'OR';

        const selected = window.PermissionPolicyCenter.collectSelected(
            dbType,
            options.permissionsContainer,
            options.prefix || ''
        );
        if (!window.PermissionPolicyCenter.hasSelection(selected)) {
            toast.warning('请至少选择一个权限');
            return null;
        }

        const ruleExpression = window.PermissionPolicyCenter.buildExpression(dbType, selected, operator);

        return {
            classification_id: parseInt(classificationId, 10),
            rule_name: ruleName,
            db_type: dbType,
            rule_expression: ruleExpression,
        };
    }

    async function handleViewRule(id) {
        try {
            const response = await api.rules.detail(id);
            const rule = response?.data?.rule ?? response?.rule;
            if (!rule) {
                toast.error('未获取到规则信息');
                return;
            }

            const modalEl = document.getElementById('viewRuleModal');
            if (modalEl) {
                modalEl.dataset.ruleId = rule.id;
            }

            document.getElementById('viewRuleName').textContent = rule.rule_name || '-';
            document.getElementById('viewRuleClassification').textContent = rule.classification_name || '未分类';
            document.getElementById('viewRuleDbType').textContent = (rule.db_type || '').toUpperCase();

            const operator = rule.rule_expression?.operator === 'AND' ? 'AND (所有条件都必须满足)' : 'OR (任一条件满足即可)';
            document.getElementById('viewRuleOperator').textContent = operator;

            document.getElementById('viewRuleStatus').innerHTML = rule.is_active
                ? '<span class="badge bg-success">启用</span>'
                : '<span class="badge bg-secondary">禁用</span>';

            if (window.timeUtils && typeof window.timeUtils.formatDateTime === 'function') {
                document.getElementById('viewRuleCreatedAt').textContent = rule.created_at
                    ? window.timeUtils.formatDateTime(rule.created_at)
                    : '-';
                document.getElementById('viewRuleUpdatedAt').textContent = rule.updated_at
                    ? window.timeUtils.formatDateTime(rule.updated_at)
                    : '-';
            }

            const permissionsContainer = document.getElementById('viewPermissionsConfig');
            if (permissionsContainer && ensurePermissionCenter()) {
                permissionsContainer.innerHTML = window.PermissionPolicyCenter.renderDisplay(
                    rule.db_type,
                    rule.rule_expression
                );
            }

            ensureModalInstance('viewRule').open();
        } catch (error) {
            handleRequestError(error, '获取规则信息失败', 'view_rule');
        }
    }

    async function handleDeleteRule(id) {
        if (!confirm('确定要删除这个规则吗？')) {
            return;
        }

        try {
            const response = await api.rules.remove(id);
            toast.success(response?.message || '规则删除成功');
            await loadRules();
        } catch (error) {
            handleRequestError(error, '删除规则失败', 'delete_rule');
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

        console.info('开始自动分类所有账户', { operation: 'auto_classify_all' });
        debugLog('触发自动分类所有账户操作', { filters: state.classifications.length });

        try {
            if (!api.automation || typeof api.automation.trigger !== 'function') {
                throw new Error('AccountClassificationService.automation.trigger 未定义');
            }
            const response = await api.automation.trigger({});
            console.info('自动分类所有账户成功', { operation: 'auto_classify_all', result: 'success' });
            toast.success(response?.message || '自动分类任务已启动');
            setTimeout(() => window.location.reload(), 2000);
        } catch (error) {
            console.error('自动分类所有账户失败', error);
            toast.error(error?.response?.error || error.message || '自动分类失败');
            debugLog('自动分类失败', error);
        } finally {
            if (btn) {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        }
    }

    /* ========== 下拉/权限加载 ========== */
    async function loadClassificationsForRules(prefix = '') {
        const selectId = prefix ? `${prefix}RuleClassification` : 'ruleClassification';
        const select = document.getElementById(selectId);
        if (!select) {
            return;
        }

        const data =
            state.classifications.length > 0
                ? state.classifications
                : await loadClassifications().catch(() => []);

        populateRuleClassificationSelect(selectId, data);
    }

    function populateRuleClassificationSelect(elementId, classifications) {
        const select = document.getElementById(elementId);
        if (!select) {
            return;
        }

        select.innerHTML = '<option value="">请选择分类</option>';
        classifications.forEach(classification => {
            const option = document.createElement('option');
            option.value = classification.id;
            option.textContent = classification.name;
            select.appendChild(option);
        });
    }

    function loadPermissions(prefix = '') {
        if (!ensurePermissionCenter()) {
            return Promise.resolve();
        }

        const elementId = prefix ? `${prefix}RuleDbType` : 'ruleDbType';
        const dbTypeElement = document.getElementById(elementId);
        if (!dbTypeElement) {
            console.error('找不到数据库类型选择元素:', elementId);
            return Promise.resolve();
        }

        const dbType = dbTypeElement.value;
        const containerId = prefix ? `${prefix}PermissionsConfig` : 'permissionsConfig';

        return window.PermissionPolicyCenter.load(dbType, containerId, prefix).catch(error => {
            handleRequestError(error, '加载权限配置失败', 'load_permissions');
        });
    }

    /* ========== 颜色预览 & 表单校验 ========== */
    function setupColorPreviewListeners() {
        const createColorSelect = document.getElementById('classificationColor');
        if (createColorSelect) {
            createColorSelect.addEventListener('change', function () {
                updateColorPreview('colorPreview', this);
            });
        }

        const editColorSelect = document.getElementById('editClassificationColor');
        if (editColorSelect) {
            editColorSelect.addEventListener('change', function () {
                updateColorPreview('editColorPreview', this);
            });
        }
    }

    function updateColorPreview(previewId, selectElement) {
        const preview = document.getElementById(previewId);
        if (!preview || !selectElement) {
            return;
        }

        const selectedOption = selectElement.options[selectElement.selectedIndex];
        const colorValue = selectedOption?.dataset?.color;
        const colorText = selectedOption?.text;

        if (colorValue && selectElement.value) {
            const dot = preview.querySelector('.color-preview-dot');
            const text = preview.querySelector('.color-preview-text');
            if (dot && text) {
                dot.style.backgroundColor = colorValue;
                text.textContent = colorText;
                preview.style.display = 'flex';
            }
        } else {
            preview.style.display = 'none';
        }
    }

    function resetColorPreview(previewId) {
        const preview = document.getElementById(previewId);
        if (preview) {
            preview.style.display = 'none';
        }
    }

    function initFormValidators() {
        if (!window.FormValidator || !window.ValidationRules) {
            console.error('表单校验模块未正确加载');
            return;
        }

        const createForm = document.getElementById('createClassificationForm');
        if (createForm) {
            validators.createClassification = window.FormValidator.create('#createClassificationForm');
            if (validators.createClassification) {
                validators.createClassification
                    .useRules('#classificationName', window.ValidationRules.classification.name)
                    .useRules('#classificationColor', window.ValidationRules.classification.color)
                    .useRules('#priority', window.ValidationRules.classification.priority)
                    .onSuccess(event => submitCreateClassification(event.target))
                    .onFail(() => toast.error('请检查分类信息填写'));

                bindRevalidate(createForm, '#classificationName', validators.createClassification);
                bindRevalidate(createForm, '#classificationColor', validators.createClassification, 'change');
                bindRevalidate(createForm, '#priority', validators.createClassification, 'input');
            }
        }

        const editForm = document.getElementById('editClassificationForm');
        if (editForm) {
            validators.editClassification = window.FormValidator.create('#editClassificationForm');
            if (validators.editClassification) {
                validators.editClassification
                    .useRules('#editClassificationName', window.ValidationRules.classification.name)
                    .useRules('#editClassificationColor', window.ValidationRules.classification.color)
                    .useRules('#editClassificationPriority', window.ValidationRules.classification.priority)
                    .onSuccess(event => submitUpdateClassification(event.target))
                    .onFail(() => toast.error('请检查分类信息填写'));

                bindRevalidate(editForm, '#editClassificationName', validators.editClassification);
                bindRevalidate(editForm, '#editClassificationColor', validators.editClassification, 'change');
                bindRevalidate(editForm, '#editClassificationPriority', validators.editClassification, 'input');
            }
        }

        const ruleForm = document.getElementById('createRuleForm');
        if (ruleForm) {
            validators.createRule = window.FormValidator.create('#createRuleForm');
            if (validators.createRule) {
                validators.createRule
                    .useRules('#ruleClassification', window.ValidationRules.classificationRule.classification)
                    .useRules('#ruleName', window.ValidationRules.classificationRule.name)
                    .useRules('#ruleDbType', window.ValidationRules.classificationRule.dbType)
                    .useRules('#ruleOperator', window.ValidationRules.classificationRule.operator)
                    .onSuccess(event => submitCreateRule(event.target))
                    .onFail(() => toast.error('请检查规则信息填写'));

                bindRevalidate(ruleForm, '#ruleClassification', validators.createRule, 'change');
                bindRevalidate(ruleForm, '#ruleName', validators.createRule);
                bindRevalidate(ruleForm, '#ruleDbType', validators.createRule, 'change');
                bindRevalidate(ruleForm, '#ruleOperator', validators.createRule, 'change');
            }
        }
    }

    function bindRevalidate(form, selector, validator, eventName) {
        const field = form.querySelector(selector);
        if (!field || !validator) {
            return;
        }
        const evt = eventName || 'blur';
        field.addEventListener(evt, function () {
            validator.revalidateField(selector);
        });
    }

    function resetCreateClassificationForm() {
        const form = document.getElementById('createClassificationForm');
        if (form) {
            form.reset();
        }
        resetColorPreview('colorPreview');
        refreshValidator(validators.createClassification);
    }

    function resetEditClassificationForm() {
        const form = document.getElementById('editClassificationForm');
        if (form) {
            form.reset();
        }
        resetColorPreview('editColorPreview');
        refreshValidator(validators.editClassification);
    }

    function resetCreateRuleForm() {
        const form = document.getElementById('createRuleForm');
        if (form) {
            form.reset();
        }
        if (ensurePermissionCenter()) {
            window.PermissionPolicyCenter.reset?.('permissionsConfig');
        }
        refreshValidator(validators.createRule);
    }

    function resetEditRuleForm() {
        const form = document.getElementById('editRuleForm');
        if (form) {
            form.reset();
            const hiddenDbType = form.querySelector('#editRuleDbTypeHidden');
            if (hiddenDbType) {
                hiddenDbType.value = '';
            }
        }
        if (ensurePermissionCenter()) {
            window.PermissionPolicyCenter.reset?.('editPermissionsConfig', 'edit');
        }
    }

    function resetViewRuleModal() {
        const modal = document.getElementById('viewRuleModal');
        if (modal?.dataset) {
            delete modal.dataset.ruleId;
        }
        const fields = [
            'viewRuleName',
            'viewRuleClassification',
            'viewRuleDbType',
            'viewRuleOperator',
            'viewRuleCreatedAt',
            'viewRuleUpdatedAt',
        ];
        fields.forEach(id => {
            const node = document.getElementById(id);
            if (node) {
                node.textContent = '-';
            }
        });
        const status = document.getElementById('viewRuleStatus');
        if (status) {
            status.innerHTML = '-';
        }
        const permissionsContainer = document.getElementById('viewPermissionsConfig');
        if (permissionsContainer) {
            permissionsContainer.innerHTML = '<div class="text-center text-muted">未加载权限配置</div>';
        }
    }

    function refreshValidator(validator) {
        if (validator?.instance?.refresh) {
            validator.instance.refresh();
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

    function ensurePermissionCenter() {
        if (!window.PermissionPolicyCenter) {
            toast.error('权限配置模块未加载');
            return false;
        }
        return true;
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
    window.openCreateClassificationModal = openCreateClassificationModal;
    window.openCreateRuleModal = openCreateRuleModal;
    window.openEditClassificationModal = openEditClassificationModal;
    window.createClassification = triggerCreateClassification;
    window.editClassification = handleEditClassification;
    window.updateClassification = triggerUpdateClassification;
    window.deleteClassification = handleDeleteClassification;
    window.createRule = triggerCreateRule;
    window.editRule = handleEditRule;
    window.updateRule = submitUpdateRule;
    window.deleteRule = handleDeleteRule;
    window.viewRule = handleViewRule;

    window.autoClassifyAll = handleAutoClassifyAll;
    window.loadPermissions = loadPermissions;
    window.loadClassificationsForRules = loadClassificationsForRules;

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
