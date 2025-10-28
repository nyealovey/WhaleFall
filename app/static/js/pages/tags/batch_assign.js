/**
 * 批量分配标签页面逻辑
 */

class BatchAssignManager {
    constructor() {
        this.selectedInstances = new Set();
        this.selectedTags = new Set();
        this.currentMode = 'assign'; // assign | remove
        this.instances = [];
        this.tags = [];
        this.instancesByDbType = {};
        this.tagsByCategory = {};

        this.init();
    }

    /**
     * 初始化页面
     */
    init() {
        this.bindEvents();
        this.loadData();
        this.updateModeDisplay();
    }

    /**
     * 绑定事件监听器
     */
    bindEvents() {
        // 模式切换
        document.querySelectorAll('input[name="batchMode"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.currentMode = e.target.value;
                this.updateModeDisplay();
                this.updateUI();
            });
        });

        // 清空选择
        document.getElementById('clearAllSelections').addEventListener('click', () => {
            this.clearAllSelections();
        });

        // 执行操作
        document.getElementById('executeBatchOperation').addEventListener('click', () => {
            this.executeBatchOperation();
        });
    }

    /**
     * 加载数据
     */
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

    /**
     * 加载实例数据
     */
    async loadInstances() {
        try {
            const { data: payload } = await http.get('/tags/api/instances');
            this.instances = Array.isArray(payload?.instances) ? payload.instances : [];
            this.instancesByDbType = this.groupInstancesByDbType(this.instances);
        } catch (error) {
            console.error('加载实例失败:', error);
            throw error;
        }
    }

    /**
     * 加载标签数据
     */
    async loadTags() {
        try {
            const { data: payload } = await http.get('/tags/api/all_tags');
            this.tags = Array.isArray(payload?.tags) ? payload.tags : [];
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
        const grouped = {};
        instances.forEach(instance => {
            const dbType = instance.db_type || 'unknown';
            if (!grouped[dbType]) {
                grouped[dbType] = [];
            }
            grouped[dbType].push(instance);
        });

        // 对每个分组内的实例按名称排序
        Object.keys(grouped).forEach(dbType => {
            grouped[dbType].sort((a, b) => {
                const nameA = a.name || '';
                const nameB = b.name || '';
                return nameA.localeCompare(nameB, 'zh-CN', { numeric: true });
            });
        });

        return grouped;
    }

    /**
     * 按分类分组标签
     */
    groupTagsByCategory(tags) {
        const grouped = {};
        tags.forEach(tag => {
            const category = tag.category || '未分类';
            if (!grouped[category]) {
                grouped[category] = [];
            }
            grouped[category].push(tag);
        });

        // 对每个分组内的标签按显示名称排序
        Object.keys(grouped).forEach(category => {
            grouped[category].sort((a, b) => {
                const nameA = a.display_name || a.name || '';
                const nameB = b.display_name || b.name || '';
                return nameA.localeCompare(nameB, 'zh-CN', { numeric: true });
            });
        });

        return grouped;
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
        Object.keys(this.instancesByDbType).sort().forEach(dbType => {
            const instances = this.instancesByDbType[dbType];
            const dbTypeDisplay = this.getDbTypeDisplayName(dbType);

            html += `
                <div class="instance-group">
                    <div class="instance-group-header" onclick="batchAssignManager.toggleInstanceGroup('${dbType}')">
                        <div class="d-flex justify-content-between align-items-center">
                            <h6 class="mb-0">
                                <i class="fas fa-chevron-right instance-group-icon me-2"></i>
                                ${dbTypeDisplay} (${instances.length})
                            </h6>
                            <div class="form-check">
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
                        <div class="list-group list-group-flush">
                            ${instances.map(instance => `
                                <div class="list-group-item">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" 
                                               id="instance_${instance.id}" 
                                               value="${instance.id}"
                                               onchange="batchAssignManager.toggleInstanceSelection(${instance.id})">
                                        <label class="form-check-label" for="instance_${instance.id}">
                                            <div class="instance-info">
                                                <span class="instance-name">${instance.name}</span>
                                                <span class="instance-address">${instance.host}:${instance.port}</span>
                                            </div>
                                        </label>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
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
        Object.keys(this.tagsByCategory).sort().forEach(category => {
            const tags = this.tagsByCategory[category];

            html += `
                <div class="tag-group">
                    <div class="tag-group-header" onclick="batchAssignManager.toggleTagGroup('${category}')">
                        <div class="d-flex justify-content-between align-items-center">
                            <h6 class="mb-0">
                                <i class="fas fa-chevron-right tag-group-icon me-2"></i>
                                ${category} (${tags.length})
                            </h6>
                            <div class="form-check">
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
                        <div class="list-group list-group-flush">
                            ${tags.map(tag => `
                                <div class="list-group-item">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" 
                                               id="tag_${tag.id}" 
                                               value="${tag.id}"
                                               onchange="batchAssignManager.toggleTagSelection(${tag.id})">
                                        <label class="form-check-label" for="tag_${tag.id}">
                                            <span class="badge bg-${tag.color || 'primary'} me-2">${tag.display_name || tag.name}</span>
                                            ${tag.description ? `<small class="text-muted">${tag.description}</small>` : ''}
                                        </label>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
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
        Object.keys(this.instancesByDbType).forEach(dbType => {
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
        Object.keys(this.tagsByCategory).forEach(category => {
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

        this.updateGroupCheckboxState('tag');
        this.updateUI();
    }

    /**
     * 更新分组复选框状态
     */
    updateGroupCheckboxState(type) {
        if (type === 'instance') {
            Object.keys(this.instancesByDbType).forEach(dbType => {
                const groupCheckbox = document.getElementById(`instanceGroup_${dbType}`);
                const instanceCheckboxes = document.querySelectorAll(`#instanceGroupContent_${dbType} input[type="checkbox"]`);
                const checkedCount = Array.from(instanceCheckboxes).filter(cb => cb.checked).length;

                groupCheckbox.checked = checkedCount === instanceCheckboxes.length;
                groupCheckbox.indeterminate = checkedCount > 0 && checkedCount < instanceCheckboxes.length;
            });
        } else if (type === 'tag') {
            Object.keys(this.tagsByCategory).forEach(category => {
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

        if (this.currentMode === 'remove') {
            removeModeInfo.style.display = 'block';
            tagSelectionPanel.style.display = 'none';
            selectedTagsSection.style.display = 'none';
        } else {
            removeModeInfo.style.display = 'none';
            tagSelectionPanel.style.display = 'block';
            selectedTagsSection.style.display = 'block';
        }
    }

    /**
     * 更新UI显示
     */
    updateUI() {
        this.updateCounts();
        this.updateSelectionSummary();
        this.updateActionButton();
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
        const summary = document.getElementById('selectionSummary');
        const selectedInstancesList = document.getElementById('selectedInstancesList');
        const selectedTagsList = document.getElementById('selectedTagsList');

        if (this.selectedInstances.size === 0 && this.selectedTags.size === 0) {
            summary.style.display = 'none';
            return;
        }

        summary.style.display = 'block';

        // 更新实例列表
        const instanceNames = Array.from(this.selectedInstances).map(id => {
            const instance = this.instances.find(i => i.id === id);
            return instance ? instance.name : `实例 ${id}`;
        });

        selectedInstancesList.innerHTML = instanceNames.map(name =>
            `<span class="selected-item">${name}</span>`
        ).join('');

        // 更新标签列表（仅在分配模式下显示）
        if (this.currentMode === 'assign') {
            const tagItems = Array.from(this.selectedTags).map(id => {
                const tag = this.tags.find(t => t.id === id);
                return tag ? {
                    name: tag.display_name || tag.name,
                    color: tag.color || 'primary'
                } : {
                    name: `标签 ${id}`,
                    color: 'secondary'
                };
            });

            selectedTagsList.innerHTML = tagItems.map(tag =>
                `<span class="selected-item">
                    <span class="badge bg-${tag.color} me-1">${tag.name}</span>
                </span>`
            ).join('');
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
            button.className = 'btn btn-primary';
        } else {
            button.innerHTML = '<i class="fas fa-minus me-1"></i>移除标签';
            button.className = 'btn btn-danger';
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

        // 更新UI
        this.updateUI();
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
        const result = await http.post('/tags/api/batch_assign_tags', {
            instance_ids: Array.from(this.selectedInstances),
            tag_ids: Array.from(this.selectedTags)
        });
        return result;
    }

    /**
     * 执行批量移除
     */
    async performBatchRemove() {
        const result = await http.post('/tags/api/batch_remove_all_tags', {
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
        notify.alert(type, text);
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
        const selectionAreas = document.querySelectorAll('.instance-selection, .tag-selection');
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

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function () {
    window.batchAssignManager = new BatchAssignManager();
});
