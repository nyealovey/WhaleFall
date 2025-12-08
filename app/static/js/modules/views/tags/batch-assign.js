/**
 * 批量分配标签页面逻辑
 */

const LodashUtils = window.LodashUtils;
if (!LodashUtils) {
    throw new Error('LodashUtils 未初始化');
}

const TagManagementService = window.TagManagementService;
if (!TagManagementService) {
    throw new Error('TagManagementService 未初始化');
}

const tagService = new TagManagementService(window.httpU);

/**
 * 批量分配/移除标签的控制器。
 */
class BatchAssignManager {
    constructor() {
        this.selectedInstances = new Set();
        this.selectedTags = new Set();
        this.currentMode = 'assign'; // assign | remove
        this.instances = [];
        this.tags = [];
        this.instanceLookup = {};
        this.tagLookup = {};
        this.instancesByDbType = {};
        this.tagsByCategory = {};
        this.form = document.getElementById('batchAssignForm');
        this.validator = null;

        this.init();
    }

    init() {
        this.bindEvents();
        this.initializeValidator();
        this.loadData();
        this.updateModeDisplay();
        this.syncModeToggleState();
        this.updateHiddenFields();
    }

   bindEvents() {
        // 模式切换
        document.querySelectorAll('input[name="batchMode"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.currentMode = e.target.value;
                this.updateModeDisplay();
                this.syncModeToggleState();
                this.updateUI();
            });
        });

        // 清空选择
        document.getElementById('clearAllSelections').addEventListener('click', () => {
            this.clearAllSelections();
        });

        if (this.form) {
            this.form.addEventListener('submit', (event) => {
                event.preventDefault();
                if (this.validator && this.validator.instance && typeof this.validator.instance.revalidate === 'function') {
                    this.validator.instance.revalidate();
                } else {
                    this.executeBatchOperation();
                }
            });
        }
    }

    initializeValidator() {
        if (typeof FormValidator === 'undefined' || typeof ValidationRules === 'undefined') {
            console.warn('FormValidator 或 ValidationRules 未加载，批量分配表单跳过校验初始化');
            return;
        }

        if (!this.form) {
            return;
        }

        this.validator = FormValidator.create('#batchAssignForm');
        if (!this.validator) {
            return;
        }

        this.validator
            .useRules('#selectedInstancesInput', ValidationRules.batchAssign.instances)
            .useRules('#selectedTagsInput', ValidationRules.batchAssign.tags)
            .onSuccess((event) => {
                event.preventDefault();
                this.executeBatchOperation();
            })
            .onFail(() => {
                toast.error('请检查实例和标签选择后再执行操作');
            });
    }

   async loadData() {
        try {
            await Promise.all([
                this.loadInstances(),
                this.loadTags()
            ]);
            this.renderInstances();
            this.renderTags();
        } catch (error) {
            this.showError('加载数据失败', error.message);
        }
    }

   async loadInstances() {
        try {
            const response = await tagService.listInstances();
            const payload = response?.data ?? response;
            this.instances = Array.isArray(payload?.instances) ? payload.instances : [];
            this.instanceLookup = LodashUtils.keyBy(this.instances, 'id');
            this.instancesByDbType = this.groupInstancesByDbType(this.instances);
        } catch (error) {
            console.error('加载实例失败:', error);
            throw error;
        }
    }

   async loadTags() {
        try {
            const response = await tagService.listAllTags();
            const payload = response?.data ?? response;
            this.tags = Array.isArray(payload?.tags) ? payload.tags : [];
            this.tagLookup = LodashUtils.keyBy(this.tags, 'id');
            this.tagsByCategory = this.groupTagsByCategory(this.tags);

        } catch (error) {
            console.error('加载标签失败:', error);
            throw error;
        }
    }

    /**
     * 按数据库类型分组实例
     */
    groupInstancesByDbType(instances) {
        const grouped = LodashUtils.groupBy(instances || [], (instance) => instance?.db_type || 'unknown');
        return LodashUtils.mapValues(grouped, (items) =>
            LodashUtils.orderBy(
                items,
                [
                    (instance) => this.normalizeText(instance?.name),
                ],
                ['asc']
            )
        );
    }

    /**
     * 按分类分组标签
     */
    groupTagsByCategory(tags) {
        const grouped = LodashUtils.groupBy(tags || [], (tag) => tag?.category || '未分类');
        return LodashUtils.mapValues(grouped, (items) =>
            LodashUtils.orderBy(
                items,
                [
                    (tag) => this.normalizeText(tag?.display_name || tag?.name),
                ],
                ['asc']
            )
        );
    }

    /**
     * 渲染实例列表
     */
    renderInstances() {
        const container = document.getElementById('instancesContainer');
        const loading = document.getElementById('instancesLoading');

        if (this.instances.length === 0) {
            container.innerHTML = this.getEmptyState('实例', 'fas fa-database');
            loading.style.display = 'none';
            container.style.display = 'block';
            return;
        }

        let html = '';
        this.getSortedKeys(this.instancesByDbType).forEach(dbType => {
            const instances = this.instancesByDbType[dbType];
            const dbTypeDisplay = this.getDbTypeDisplayName(dbType);

            html += `
                <div class="instance-group">
                    <div class="instance-group-header" onclick="batchAssignManager.toggleInstanceGroup('${dbType}')">
                        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
                            <div class="d-flex align-items-center gap-2">
                                <i class="fas fa-chevron-right instance-group-icon"></i>
                                <span class="chip-outline chip-outline--muted">${dbTypeDisplay}</span>
                                <span class="text-muted small">${instances.length} 个</span>
                            </div>
                            <div class="form-check form-check-inline">
                                <input class="form-check-input" type="checkbox" 
                                       id="instanceGroup_${dbType}" 
                                       onchange="batchAssignManager.toggleInstanceGroupSelection('${dbType}')">
                                <label class="form-check-label" for="instanceGroup_${dbType}">
                                    全选
                                </label>
                            </div>
                        </div>
                    </div>
                    <div class="instance-group-content" id="instanceGroupContent_${dbType}">
                        ${instances.map(instance => `
                            <label class="ledger-row" data-instance-row="${instance.id}" for="instance_${instance.id}">
                                <input class="form-check-input" type="checkbox" 
                                       id="instance_${instance.id}" 
                                       value="${instance.id}"
                                       onchange="batchAssignManager.toggleInstanceSelection(${instance.id})">
                                <div class="ledger-row__body">
                                    <div class="ledger-row__title">${instance.name}</div>
                                    <div class="ledger-row__meta">${instance.host}:${instance.port}</div>
                                </div>
                                <div class="ledger-row__badge">
                                    <span class="chip-outline chip-outline--muted">${this.getDbTypeDisplayName(instance.db_type)}</span>
                                </div>
                            </label>
                        `).join('')}
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
        loading.style.display = 'none';
        container.style.display = 'block';

        this.initializeScrollAreas();
    }

    /**
     * 渲染标签列表
     */
    renderTags() {
        const container = document.getElementById('tagsContainer');
        const loading = document.getElementById('tagsLoading');

        if (this.tags.length === 0) {
            container.innerHTML = this.getEmptyState('标签', 'fas fa-tags');
            loading.style.display = 'none';
            container.style.display = 'block';
            return;
        }

        let html = '';
        this.getSortedKeys(this.tagsByCategory).forEach(category => {
            const tags = this.tagsByCategory[category];

            html += `
                <div class="tag-group">
                    <div class="tag-group-header" onclick="batchAssignManager.toggleTagGroup('${category}')">
                        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
                            <div class="d-flex align-items-center gap-2">
                                <i class="fas fa-chevron-right tag-group-icon"></i>
                                <span class="chip-outline chip-outline--muted">${category}</span>
                                <span class="text-muted small">${tags.length} 个</span>
                            </div>
                            <div class="form-check form-check-inline">
                                <input class="form-check-input" type="checkbox" 
                                       id="tagGroup_${category}" 
                                       onchange="batchAssignManager.toggleTagGroupSelection('${category}')">
                                <label class="form-check-label" for="tagGroup_${category}">
                                    全选
                                </label>
                            </div>
                        </div>
                    </div>
                    <div class="tag-group-content" id="tagGroupContent_${category}">
                        ${tags.map(tag => `
                            <label class="ledger-row" data-tag-row="${tag.id}" for="tag_${tag.id}">
                                <input class="form-check-input" type="checkbox" 
                                       id="tag_${tag.id}" 
                                       value="${tag.id}"
                                       onchange="batchAssignManager.toggleTagSelection(${tag.id})">
                                <div class="ledger-row__body">
                                    <div class="ledger-row__title">${tag.display_name || tag.name}</div>
                                    ${tag.category ? `<div class="ledger-row__meta">分类：${tag.category}</div>` : ''}
                                </div>
                                <div class="ledger-row__badge">
                                    <span class="status-pill ${tag.is_active ? 'status-pill--info' : 'status-pill--muted'}">
                                        ${tag.is_active ? '启用' : '停用'}
                                    </span>
                                </div>
                            </label>
                        `).join('')}
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
        loading.style.display = 'none';
        container.style.display = 'block';

        // 初始化滚动功能
        this.initializeScrollAreas();
    }

    /**
     * 切换实例分组展开/收起
     */
    toggleInstanceGroup(dbType) {
        const content = document.getElementById(`instanceGroupContent_${dbType}`);
        const header = content.previousElementSibling;
        const icon = header.querySelector('.instance-group-icon');

        if (content.classList.contains('show')) {
            // 如果当前分组是展开的，则收起
            content.classList.remove('show');
            if (icon) icon.style.transform = 'rotate(0deg)';
        } else {
            // 先收起所有其他分组（手风琴效果）
            this.collapseAllInstanceGroups();

            // 展开当前分组
            content.classList.add('show');
            if (icon) icon.style.transform = 'rotate(90deg)';

            // 确保内容区域可以滚动
            setTimeout(() => {
                if (content.scrollHeight > content.clientHeight) {
                    content.style.overflowY = 'auto';
                }
            }, 300);
        }
    }

    /**
     * 收起所有实例分组
     */
    collapseAllInstanceGroups() {
        this.getSortedKeys(this.instancesByDbType).forEach(dbType => {
            const content = document.getElementById(`instanceGroupContent_${dbType}`);
            if (content && content.classList.contains('show')) {
                content.classList.remove('show');
                const header = content.previousElementSibling;
                const icon = header?.querySelector('.instance-group-icon');
                if (icon) {
                    icon.style.transform = 'rotate(0deg)';
                }
            }
        });
    }

    /**
     * 收起所有标签分组
     */
    collapseAllTagGroups() {
        this.getSortedKeys(this.tagsByCategory).forEach(category => {
            const content = document.getElementById(`tagGroupContent_${category}`);
            if (content && content.classList.contains('show')) {
                content.classList.remove('show');
                const header = content.previousElementSibling;
                const icon = header?.querySelector('.tag-group-icon');
                if (icon) {
                    icon.style.transform = 'rotate(0deg)';
                }
            }
        });
    }

    /**
     * 切换标签分组展开/收起
     */
    toggleTagGroup(category) {
        const content = document.getElementById(`tagGroupContent_${category}`);
        const header = content.previousElementSibling;
        const icon = header.querySelector('.tag-group-icon');

        if (content.classList.contains('show')) {
            // 如果当前分组是展开的，则收起
            content.classList.remove('show');
            if (icon) icon.style.transform = 'rotate(0deg)';
        } else {
            // 先收起所有其他分组（手风琴效果）
            this.collapseAllTagGroups();

            // 展开当前分组
            content.classList.add('show');
            if (icon) icon.style.transform = 'rotate(90deg)';

            // 确保内容区域可以滚动
            setTimeout(() => {
                if (content.scrollHeight > content.clientHeight) {
                    content.style.overflowY = 'auto';
                }
            }, 300);
        }
    }

    /**
     * 切换实例分组全选
     */
    toggleInstanceGroupSelection(dbType) {
        const groupCheckbox = document.getElementById(`instanceGroup_${dbType}`);
        const instanceCheckboxes = document.querySelectorAll(`#instanceGroupContent_${dbType} input[type="checkbox"]`);

        instanceCheckboxes.forEach(checkbox => {
            checkbox.checked = groupCheckbox.checked;
            const instanceId = parseInt(checkbox.value);
            if (groupCheckbox.checked) {
                this.selectedInstances.add(instanceId);
            } else {
                this.selectedInstances.delete(instanceId);
            }
            this.updateRowSelectedState('instance', instanceId, checkbox.checked);
        });

        this.updateUI();
    }

    /**
     * 切换标签分组全选
     */
    toggleTagGroupSelection(category) {
        const groupCheckbox = document.getElementById(`tagGroup_${category}`);
        const tagCheckboxes = document.querySelectorAll(`#tagGroupContent_${category} input[type="checkbox"]`);

        tagCheckboxes.forEach(checkbox => {
            checkbox.checked = groupCheckbox.checked;
            const tagId = parseInt(checkbox.value);
            if (groupCheckbox.checked) {
                this.selectedTags.add(tagId);
            } else {
                this.selectedTags.delete(tagId);
            }
            this.updateRowSelectedState('tag', tagId, checkbox.checked);
        });

        this.updateUI();
    }

    /**
     * 切换单个实例选择
     */
    toggleInstanceSelection(instanceId) {
        const checkbox = document.getElementById(`instance_${instanceId}`);

        if (checkbox.checked) {
            this.selectedInstances.add(instanceId);
        } else {
            this.selectedInstances.delete(instanceId);
        }
        this.updateRowSelectedState('instance', instanceId, checkbox.checked);

        this.updateGroupCheckboxState('instance');
        this.updateUI();
    }

    /**
     * 切换单个标签选择
     */
    toggleTagSelection(tagId) {
        const checkbox = document.getElementById(`tag_${tagId}`);

        if (checkbox.checked) {
            this.selectedTags.add(tagId);
        } else {
            this.selectedTags.delete(tagId);
        }
        this.updateRowSelectedState('tag', tagId, checkbox.checked);

        this.updateGroupCheckboxState('tag');
        this.updateUI();
    }

    /**
     * 更新分组复选框状态
     */
    updateGroupCheckboxState(type) {
        if (type === 'instance') {
            this.getSortedKeys(this.instancesByDbType).forEach(dbType => {
                const groupCheckbox = document.getElementById(`instanceGroup_${dbType}`);
                const instanceCheckboxes = document.querySelectorAll(`#instanceGroupContent_${dbType} input[type="checkbox"]`);
                const checkedCount = Array.from(instanceCheckboxes).filter(cb => cb.checked).length;

                groupCheckbox.checked = checkedCount === instanceCheckboxes.length;
                groupCheckbox.indeterminate = checkedCount > 0 && checkedCount < instanceCheckboxes.length;
            });
        } else if (type === 'tag') {
            this.getSortedKeys(this.tagsByCategory).forEach(category => {
                const groupCheckbox = document.getElementById(`tagGroup_${category}`);
                const tagCheckboxes = document.querySelectorAll(`#tagGroupContent_${category} input[type="checkbox"]`);
                const checkedCount = Array.from(tagCheckboxes).filter(cb => cb.checked).length;

                groupCheckbox.checked = checkedCount === tagCheckboxes.length;
                groupCheckbox.indeterminate = checkedCount > 0 && checkedCount < tagCheckboxes.length;
            });
        }
    }

    /**
     * 更新模式显示
     */
    updateModeDisplay() {
        const removeModeInfo = document.getElementById('removeModeInfo');
        const tagSelectionPanel = document.getElementById('tagSelectionPanel');
        const selectedTagsSection = document.getElementById('selectedTagsSection');
        const layoutGrid = document.getElementById('batchLayoutGrid');
        const summaryTagCount = document.getElementById('summaryTagCount');
        const modeField = document.getElementById('batchModeField');
        const isRemoveMode = this.currentMode === 'remove';

        if (removeModeInfo) {
            removeModeInfo.style.display = isRemoveMode ? 'flex' : 'none';
        }
        if (tagSelectionPanel) {
            tagSelectionPanel.hidden = isRemoveMode;
        }
        if (selectedTagsSection) {
            selectedTagsSection.hidden = isRemoveMode;
        }
        if (summaryTagCount) {
            summaryTagCount.hidden = isRemoveMode;
        }
        if (layoutGrid) {
            layoutGrid.classList.toggle('is-remove-mode', isRemoveMode);
            layoutGrid.dataset.mode = this.currentMode;
        }
        if (modeField) {
            modeField.value = this.currentMode;
        }
        if (this.validator?.revalidateField) {
            this.validator.revalidateField('#selectedTagsInput');
        }
    }

    /**
     * 更新UI显示
     */
    updateUI() {
        this.updateCounts();
        this.updateSelectionSummary();
        this.updateHiddenFields();
        this.updateActionButton();
    }

    updateHiddenFields() {
        const instancesInput = document.getElementById('selectedInstancesInput');
        const tagsInput = document.getElementById('selectedTagsInput');

        if (instancesInput) {
            instancesInput.value = Array.from(this.selectedInstances).join(',');
        }

        if (tagsInput) {
            tagsInput.value = Array.from(this.selectedTags).join(',');
        }

        if (this.validator) {
            this.validator.revalidateField('#selectedInstancesInput');
            this.validator.revalidateField('#selectedTagsInput');
        }
    }

    /**
     * 更新计数显示
     */
    updateCounts() {
        document.getElementById('selectedInstancesCount').textContent = this.selectedInstances.size;
        document.getElementById('selectedTagsCount').textContent = this.selectedTags.size;
        document.getElementById('totalSelectedInstances').textContent = this.selectedInstances.size;
        document.getElementById('totalSelectedTags').textContent = this.selectedTags.size;
    }

    /**
     * 更新选择摘要
     */
    updateSelectionSummary() {
        const selectedInstancesList = document.getElementById('selectedInstancesList');
        const selectedTagsList = document.getElementById('selectedTagsList');
        const summaryTagCount = document.getElementById('summaryTagCount');
        const isRemoveMode = this.currentMode === 'remove';

        if (!selectedInstancesList || !selectedTagsList) {
            return;
        }

        if (this.selectedInstances.size > 0) {
            const chips = Array.from(this.selectedInstances).map((id) => {
                const instance = this.instanceLookup[id];
                const name = this.escapeHtml(instance?.name || `实例 ${id}`);
                return this.buildLedgerChipHtml(`<i class="fas fa-database"></i>${name}`);
            });
            selectedInstancesList.innerHTML = chips.join('');
        } else {
            selectedInstancesList.innerHTML = this.buildSummaryEmptyState('尚未选择实例', 'fas fa-database');
        }

        if (!isRemoveMode) {
            if (this.selectedTags.size > 0) {
                const tagChips = Array.from(this.selectedTags).map((id) => {
                    const tag = this.tagLookup[id];
                    const label = this.escapeHtml(tag?.display_name || tag?.name || `标签 ${id}`);
                    const isInactive = tag ? !tag.is_active : true;
                    return this.buildLedgerChipHtml(`<i class="fas fa-tag"></i>${label}`, isInactive);
                });
                selectedTagsList.innerHTML = tagChips.join('');
            } else {
                selectedTagsList.innerHTML = this.buildSummaryEmptyState('尚未选择标签', 'fas fa-tags');
            }
        } else {
            selectedTagsList.innerHTML = this.buildSummaryEmptyState('移除模式无需选择标签', 'fas fa-tags');
        }

        if (summaryTagCount) {
            summaryTagCount.hidden = isRemoveMode;
        }
    }

    /**
     * 更新操作按钮状态
     */
    updateActionButton() {
        const button = document.getElementById('executeBatchOperation');
        const canExecute = this.selectedInstances.size > 0 &&
            (this.currentMode === 'remove' || this.selectedTags.size > 0);

        button.disabled = !canExecute;

        if (this.currentMode === 'assign') {
            button.innerHTML = '<i class="fas fa-plus me-1"></i>分配标签';
        } else {
            button.innerHTML = '<i class="fas fa-minus me-1"></i>移除标签';
        }
    }

    /**
     * 清空所有选择
     */
    clearAllSelections() {
        // 清空选择集合
        this.selectedInstances.clear();
        this.selectedTags.clear();

        // 取消所有复选框
        document.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.checked = false;
            checkbox.indeterminate = false;
        });

        document.querySelectorAll('.ledger-row--selected').forEach((row) => row.classList.remove('ledger-row--selected'));

        this.updateGroupCheckboxState('instance');
        this.updateGroupCheckboxState('tag');

        // 更新UI
        this.updateUI();

        if (this.validator && this.validator.instance) {
            this.validator.instance.refresh();
        }
    }

    /**
     * 执行批量操作
     */
    async executeBatchOperation() {
        if (this.selectedInstances.size === 0) {
            this.showError('请选择至少一个实例');
            return;
        }

        if (this.currentMode === 'assign' && this.selectedTags.size === 0) {
            this.showError('请选择至少一个标签');
            return;
        }

        try {
            this.showProgress();

            if (this.currentMode === 'assign') {
                await this.performBatchAssign();
            } else {
                await this.performBatchRemove();
            }

            this.hideProgress();
            this.showSuccess('操作完成');
            this.clearAllSelections();

        } catch (error) {
            this.hideProgress();
            this.showError('操作失败', error.message);
        }
    }

    /**
     * 执行批量分配
     */
    async performBatchAssign() {
        const result = await tagService.batchAssign({
            instance_ids: Array.from(this.selectedInstances),
            tag_ids: Array.from(this.selectedTags)
        });
        return result;
    }

    /**
     * 执行批量移除
     */
    async performBatchRemove() {
        const result = await tagService.batchRemoveAll({
            instance_ids: Array.from(this.selectedInstances)
        });
        if (!result.success) {
            throw new Error(result.message || '移除失败');
        }
        return result;
    }

    /**
     * 显示进度
     */
    showProgress() {
        const container = document.getElementById('progressContainer');
        const progressBar = container.querySelector('.progress-bar');
        const progressText = document.getElementById('progressText');

        container.style.display = 'block';
        progressBar.style.width = '0%';
        progressText.textContent = '准备中...';

        // 模拟进度
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 20;
            if (progress > 90) progress = 90;

            progressBar.style.width = progress + '%';
            progressText.textContent = `处理中... ${Math.round(progress)}%`;
        }, 200);

        this.progressInterval = interval;
    }

    /**
     * 隐藏进度
     */
    hideProgress() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }

        const container = document.getElementById('progressContainer');
        const progressBar = container.querySelector('.progress-bar');
        const progressText = document.getElementById('progressText');

        progressBar.style.width = '100%';
        progressText.textContent = '完成';

        setTimeout(() => {
            container.style.display = 'none';
        }, 1000);
    }

    /**
     * 显示成功消息
     */
    showSuccess(message) {
        this.showAlert(message, 'success');
    }

    /**
     * 显示错误消息
     */
    showError(message, details = null) {
        this.showAlert(message, 'danger', details);
    }

    /**
     * 显示警告消息
     */
    showAlert(message, type, details = null) {
        const text = details ? `${message}\n${details}` : message;
        const normalizedType = type === 'danger' ? 'error' : type;
        toast.show(normalizedType, text);
    }

    syncModeToggleState() {
        document.querySelectorAll('.chip-toggle').forEach((label) => label.classList.remove('chip-toggle--active'));
        document.querySelectorAll('.chip-toggle-input').forEach((input) => {
            if (input.checked) {
                const label = document.querySelector(`label[for="${input.id}"]`);
                label?.classList.add('chip-toggle--active');
            }
        });
    }

    updateRowSelectedState(type, id, checked) {
        const selector = type === 'instance' ? `[data-instance-row="${id}"]` : `[data-tag-row="${id}"]`;
        const row = document.querySelector(selector);
        if (row) {
            row.classList.toggle('ledger-row--selected', checked);
        }
    }

    buildLedgerChipHtml(content, muted = false) {
        const classes = ['ledger-chip'];
        if (muted) {
            classes.push('ledger-chip--muted');
        }
        return `<span class="${classes.join(' ')}">${content}</span>`;
    }

    buildSummaryEmptyState(text, iconClass) {
        const iconHtml = iconClass ? `<i class="${iconClass}" aria-hidden="true"></i>` : '';
        return `<div class="summary-card__empty">${iconHtml}${this.escapeHtml(text)}</div>`;
    }

    escapeHtml(value) {
        if (value === undefined || value === null) {
            return '';
        }
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    /**
     * 获取空状态HTML
     */
    getEmptyState(type, icon) {
        return `
            <div class="empty-state">
                <i class="${icon}"></i>
                <p>暂无${type}数据</p>
            </div>
        `;
    }

    getSortedKeys(collection) {
        const keys = Object.keys(collection || {});
        if (!keys.length) {
            return [];
        }
        return LodashUtils.orderBy(
            keys,
            [
                (key) => this.normalizeText(key),
            ],
            ['asc']
        );
    }

    normalizeText(value) {
        const text = (value || '').toString();
        if (typeof LodashUtils.toLower === 'function') {
            return LodashUtils.toLower(text);
        }
        return text.toLowerCase();
    }

    /**
     * 获取数据库类型显示名称
     */
    getDbTypeDisplayName(dbType) {
        const displayNames = {
            'mysql': 'MySQL',
            'postgresql': 'PostgreSQL',
            'sqlserver': 'SQL Server',
            'oracle': 'Oracle',
            'unknown': '未知类型'
        };
        return displayNames[dbType] || dbType;
    }

    /**
     * 初始化滚动区域
     */
    initializeScrollAreas() {
        // 确保所有分组内容区域都能正确滚动
        const groupContents = document.querySelectorAll('.instance-group-content, .tag-group-content');
        groupContents.forEach(content => {
            if (content.scrollHeight > content.clientHeight) {
                content.style.overflowY = 'auto';
            }
        });

        // 确保主选择区域也能正确滚动
        const selectionAreas = document.querySelectorAll('.selection-panel__content');
        selectionAreas.forEach(area => {
            if (area.scrollHeight > area.clientHeight) {
                area.style.overflowY = 'auto';
            }
        });
    }

    /**
     * 获取CSRF令牌 - 使用全局函数
     */
    getCSRFToken() {
        return window.getCSRFToken();
    }
}

/**
 * 挂载标签批量分配页面。
 *
 * 创建 BatchAssignManager 实例并挂载到全局 window 对象，
 * 用于管理标签的批量分配操作。
 *
 * @return {void}
 *
 * @example
 * // 在页面加载时调用
 * mountBatchAssignPage();
 */
function mountBatchAssignPage() {
    window.batchAssignManager = new BatchAssignManager();
}

window.TagsBatchAssignPage = {
    mount: mountBatchAssignPage,
};
