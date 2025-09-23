/**
 * 标签选择器组件JavaScript
 * 提供标签搜索、筛选、选择、管理等功能
 */

// 标签选择器类
class TagSelector {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.options = {
            allowMultiple: true,
            showSearch: true,
            showCategories: true,
            showStats: true,
            maxSelections: null,
            onSelectionChange: null,
            onTagAdd: null,
            onTagRemove: null,
            ...options
        };
        
        this.selectedTags = new Set();
        this.allTags = [];
        this.filteredTags = [];
        this.currentCategory = 'all';
        this.searchQuery = '';
        
        this.init();
    }
    
    // 初始化标签选择器
    init() {
        if (!this.container) {
            console.error('TagSelector: Container not found');
            return;
        }
        
        this.setupEventListeners();
        this.loadTags();
        this.loadCategories();
    }
    
    // 设置事件监听器
    setupEventListeners() {
        // 搜索输入
        const searchInput = this.container.querySelector('#tag-search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.handleSearch(e.target.value);
            });
        }
        
        // 清除搜索
        const clearSearchBtn = this.container.querySelector('#clear-search-btn');
        if (clearSearchBtn) {
            clearSearchBtn.addEventListener('click', () => {
                this.clearSearch();
            });
        }
        
        // 确认按钮
        const confirmBtn = this.container.querySelector('#confirm-selection-btn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => {
                this.confirmSelection();
            });
        }
        
        // 取消按钮
        const cancelBtn = this.container.querySelector('#cancel-selection-btn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                this.cancelSelection();
            });
        }
    }

    // 加载分类数据
    async loadCategories() {
        try {
            const response = await fetch('/tags/api/categories', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (!response.ok) {
                throw new Error('Failed to load categories');
            }

            const data = await response.json();
            if (data.success) {
                this.renderCategories(data.categories);
            } else {
                throw new Error(data.message || 'Failed to load categories');
            }
        } catch (error) {
            console.error('Error loading categories:', error);
        }
    }

    // 渲染分类筛选器
    renderCategories(categories) {
        const container = this.container.querySelector('#tag-category-filter-container');
        if (!container) return;

        let html = `
            <input type="radio" class="btn-check" name="category-filter" id="category-all" value="all" checked>
            <label class="btn btn-outline-secondary" for="category-all">全部</label>
        `;

        categories.forEach(([value, displayName]) => {
            html += `
                <input type="radio" class="btn-check" name="category-filter" id="category-${value}" value="${value}">
                <label class="btn btn-outline-secondary" for="category-${value}">${displayName}</label>
            `;
        });

        container.innerHTML = html;

        const categoryFilters = container.querySelectorAll('input[name="category-filter"]');
        categoryFilters.forEach(filter => {
            filter.addEventListener('change', (e) => {
                this.handleCategoryFilter(e.target.value);
            });
        });
    }
    
    // 加载标签数据
    async loadTags() {
        try {
            this.showLoading();
            
            const response = await fetch('/tags/api/tags', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to load tags');
            }
            
            const data = await response.json();
            if (data.success) {
                this.allTags = data.tags || [];
                this.filteredTags = [...this.allTags];
                this.renderTags();
                this.updateStats();
            } else {
                throw new Error(data.message || 'Failed to load tags');
            }
        } catch (error) {
            console.error('Error loading tags:', error);
            this.showError('加载标签失败: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }
    
    // 处理搜索
    handleSearch(query) {
        this.searchQuery = query.toLowerCase();
        this.filterTags();
    }
    
    // 清除搜索
    clearSearch() {
        const searchInput = this.container.querySelector('#tag-search-input');
        if (searchInput) {
            searchInput.value = '';
        }
        this.searchQuery = '';
        this.filterTags();
    }
    
    // 处理分类筛选
    handleCategoryFilter(category) {
        this.currentCategory = category;
        this.filterTags();
    }
    
    // 筛选标签
    filterTags() {
        this.filteredTags = this.allTags.filter(tag => {
            // 搜索筛选
            const matchesSearch = !this.searchQuery || 
                tag.name.toLowerCase().includes(this.searchQuery) ||
                tag.display_name.toLowerCase().includes(this.searchQuery) ||
                tag.description.toLowerCase().includes(this.searchQuery) ||
                tag.category.toLowerCase().includes(this.searchQuery);
            
            // 分类筛选
            const matchesCategory = this.currentCategory === 'all' || 
                tag.category === this.currentCategory;
            
            return matchesSearch && matchesCategory;
        });
        
        this.renderTags();
        this.updateStats();
    }
    
    // 渲染标签列表
    renderTags() {
        const tagListContainer = this.container.querySelector('#tag-list-container');
        if (!tagListContainer) return;
        
        if (this.filteredTags.length === 0) {
            tagListContainer.innerHTML = this.getEmptyStateHTML();
            return;
        }
        
        const tagsHTML = this.filteredTags.map(tag => this.getTagItemHTML(tag)).join('');
        tagListContainer.innerHTML = tagsHTML;
        
        // 添加点击事件
        this.attachTagItemEvents();
    }
    
    // 获取标签项HTML
    getTagItemHTML(tag) {
        const isSelected = this.selectedTags.has(tag.id);
        const isDisabled = !tag.is_active;
        
        return `
            <div class="tag-item ${isSelected ? 'selected' : ''} ${isDisabled ? 'disabled' : ''}" 
                 data-tag-id="${tag.id}">
                <div class="tag-info">
                    <div class="tag-details">
                        <span class="badge bg-${tag.color || 'primary'} tag-display-badge">
                            ${this.highlightSearch(tag.display_name)}
                        </span>
                        <span class="tag-description">${tag.description || ''}</span>
                        <span class="badge bg-secondary tag-category-badge">${this.getCategoryDisplayName(tag.category)}</span>
                    </div>
                </div>
                <div class="tag-actions">
                    ${this.getTagActionButton(tag, isSelected, isDisabled)}
                </div>
            </div>
        `;
    }
    
    // 获取标签操作按钮
    getTagActionButton(tag, isSelected, isDisabled) {
        if (isDisabled) {
            return '<span class="text-muted">已停用</span>';
        }
        
        if (isSelected) {
            return `
                <button class="tag-action-btn remove" data-tag-id="${tag.id}" title="移除标签">
                    <i class="fas fa-minus"></i>
                </button>
            `;
        } else {
            return `
                <button class="tag-action-btn add" data-tag-id="${tag.id}" title="添加标签">
                    <i class="fas fa-plus"></i>
                </button>
            `;
        }
    }
    
    // 附加标签项事件
    attachTagItemEvents() {
        const tagItems = this.container.querySelectorAll('.tag-item');
        tagItems.forEach(item => {
            const tagId = parseInt(item.dataset.tagId);
            const isDisabled = item.classList.contains('disabled');
            
            if (!isDisabled) {
                item.addEventListener('click', (e) => {
                    if (!e.target.closest('.tag-action-btn')) {
                        this.toggleTagSelection(tagId);
                    }
                });
            }
        });
        
        const actionButtons = this.container.querySelectorAll('.tag-action-btn');
        actionButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                const tagId = parseInt(button.dataset.tagId);
                this.toggleTagSelection(tagId);
            });
        });
    }
    
    // 切换标签选择状态
    toggleTagSelection(tagId) {
        if (this.selectedTags.has(tagId)) {
            this.removeTag(tagId);
        } else {
            this.addTag(tagId);
        }
    }
    
    // 添加标签
    addTag(tagId) {
        if (this.options.maxSelections && this.selectedTags.size >= this.options.maxSelections) {
            this.showAlert('warning', `最多只能选择 ${this.options.maxSelections} 个标签`);
            return;
        }
        
        const tag = this.allTags.find(t => t.id === tagId);
        if (!tag) return;
        
        this.selectedTags.add(tagId);
        this.updateSelectedTagsDisplay();
        this.updateTagItemState(tagId, true);
        this.updateStats();
        
        if (this.options.onTagAdd) {
            this.options.onTagAdd(tag);
        }
        
        if (this.options.onSelectionChange) {
            this.options.onSelectionChange(this.getSelectedTags());
        }
    }
    
    // 移除标签
    removeTag(tagId) {
        const tag = this.allTags.find(t => t.id === tagId);
        if (!tag) return;
        
        this.selectedTags.delete(tagId);
        this.updateSelectedTagsDisplay();
        this.updateTagItemState(tagId, false);
        this.updateStats();
        
        if (this.options.onTagRemove) {
            this.options.onTagRemove(tag);
        }
        
        if (this.options.onSelectionChange) {
            this.options.onSelectionChange(this.getSelectedTags());
        }
    }
    
    // 更新已选择标签显示
    updateSelectedTagsDisplay() {
        const selectedTagsList = this.container.querySelector('#selected-tags-list');
        const noTagsPlaceholder = this.container.querySelector('#no-tags-placeholder');
        
        if (!selectedTagsList || !noTagsPlaceholder) return;
        
        if (this.selectedTags.size === 0) {
            selectedTagsList.innerHTML = '';
            noTagsPlaceholder.style.display = 'block';
        } else {
            noTagsPlaceholder.style.display = 'none';
            const selectedTagsHTML = Array.from(this.selectedTags).map(tagId => {
                const tag = this.allTags.find(t => t.id === tagId);
                return tag ? this.getSelectedTagHTML(tag) : '';
            }).join('');
            selectedTagsList.innerHTML = selectedTagsHTML;
            
            // 添加移除事件
            this.attachSelectedTagEvents();
        }
    }
    
    // 获取已选择标签HTML
    getSelectedTagHTML(tag) {
        return `
            <div class="selected-tag" data-tag-id="${tag.id}">
                <span class="badge bg-${tag.color || 'primary'} selected-tag-badge">
                    ${tag.display_name}
                </span>
                <button class="remove-tag" data-tag-id="${tag.id}" title="移除标签">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
    }
    
    // 附加已选择标签事件
    attachSelectedTagEvents() {
        const removeButtons = this.container.querySelectorAll('.remove-tag');
        removeButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.stopPropagation();
                const tagId = parseInt(button.dataset.tagId);
                this.removeTag(tagId);
            });
        });
    }
    
    // 更新标签项状态
    updateTagItemState(tagId, isSelected) {
        const tagItem = this.container.querySelector(`[data-tag-id="${tagId}"]`);
        if (!tagItem) return;
        
        if (isSelected) {
            tagItem.classList.add('selected');
            const actionButton = tagItem.querySelector('.tag-action-btn');
            if (actionButton) {
                actionButton.className = 'tag-action-btn remove';
                actionButton.innerHTML = '<i class="fas fa-minus"></i>';
                actionButton.title = '移除标签';
            }
        } else {
            tagItem.classList.remove('selected');
            const actionButton = tagItem.querySelector('.tag-action-btn');
            if (actionButton) {
                actionButton.className = 'tag-action-btn add';
                actionButton.innerHTML = '<i class="fas fa-plus"></i>';
                actionButton.title = '添加标签';
            }
        }
    }
    
    // 更新统计信息
    updateStats() {
        if (!this.options.showStats) return;
        
        const totalTags = this.allTags.length;
        const selectedTags = this.selectedTags.size;
        const activeTags = this.allTags.filter(tag => tag.is_active).length;
        const filteredTags = this.filteredTags.length;
        
        this.updateStatItem('total-tags', totalTags);
        this.updateStatItem('selected-tags', selectedTags);
        this.updateStatItem('active-tags', activeTags);
        this.updateStatItem('filtered-tags', filteredTags);
    }
    
    // 更新统计项
    updateStatItem(statId, value) {
        const statElement = this.container.querySelector(`#${statId}`);
        if (statElement) {
            statElement.textContent = value;
        }
    }
    
    // 确认选择
    confirmSelection() {
        const selectedTags = this.getSelectedTags();
        
        // 触发确认事件
        const confirmEvent = new CustomEvent('tagSelectionConfirmed', {
            detail: { selectedTags }
        });
        this.container.dispatchEvent(confirmEvent);
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(this.container.closest('.modal'));
        if (modal) {
            modal.hide();
        }
    }
    
    // 取消选择
    cancelSelection() {
        // 触发取消事件
        const cancelEvent = new CustomEvent('tagSelectionCancelled', {
            detail: { selectedTags: this.getSelectedTags() }
        });
        this.container.dispatchEvent(cancelEvent);
        
        // 关闭模态框
        const modal = bootstrap.Modal.getInstance(this.container.closest('.modal'));
        if (modal) {
            modal.hide();
        }
    }
    
    // 获取已选择的标签
    getSelectedTags() {
        return Array.from(this.selectedTags).map(tagId => 
            this.allTags.find(tag => tag.id === tagId)
        ).filter(tag => tag);
    }
    
    // 设置已选择的标签
    setSelectedTags(tagIds) {
        this.selectedTags.clear();
        tagIds.forEach(tagId => {
            if (this.allTags.find(tag => tag.id === tagId)) {
                this.selectedTags.add(tagId);
            }
        });
        this.updateSelectedTagsDisplay();
        this.updateStats();
    }
    
    // 清空选择
    clearSelection() {
        this.selectedTags.clear();
        this.updateSelectedTagsDisplay();
        this.updateStats();
    }
    
    // 搜索高亮
    highlightSearch(text) {
        if (!this.searchQuery) return text;
        
        const regex = new RegExp(`(${this.searchQuery})`, 'gi');
        return text.replace(regex, '<span class="search-highlight">$1</span>');
    }
    
    // 获取分类名称
    getCategoryName(category) {
        const categoryNames = {
            'department': '部门',
            'company_type': '公司类型',
            'environment': '环境',
            'custom': '自定义'
        };
        return categoryNames[category] || category;
    }
    
    // 获取分类显示名称
    getCategoryDisplayName(category) {
        const categoryNames = {
            'architecture': '架构',
            'company_type': '公司',
            'department': '部门',
            'deployment': '部署',
            'environment': '环境',
            'region': '地区',
            'project': '项目',
            'virtualization': '虚拟化',
            'other': '其他'
        };
        return categoryNames[category] || category;
    }
    
    // 显示加载状态
    showLoading() {
        const tagListContainer = this.container.querySelector('#tag-list-container');
        if (tagListContainer) {
            tagListContainer.innerHTML = this.getLoadingHTML();
        }
    }
    
    // 隐藏加载状态
    hideLoading() {
        // 加载状态会在renderTags中被替换
    }
    
    // 显示错误
    showError(message) {
        const tagListContainer = this.container.querySelector('#tag-list-container');
        if (tagListContainer) {
            tagListContainer.innerHTML = this.getErrorHTML(message);
        }
    }
    
    // 显示提示
    showAlert(type, message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            <i class="fas fa-${this.getAlertIcon(type)} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        this.container.insertBefore(alertDiv, this.container.firstChild);
        
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }
    
    // 获取提示图标
    getAlertIcon(type) {
        switch (type) {
            case 'success': return 'check-circle';
            case 'danger': return 'exclamation-triangle';
            case 'warning': return 'exclamation-triangle';
            case 'info': return 'info-circle';
            default: return 'info-circle';
        }
    }
    
    // 获取空状态HTML
    getEmptyStateHTML() {
        return `
            <div class="empty-state">
                <i class="fas fa-search"></i>
                <h5>未找到标签</h5>
                <p>没有找到符合条件的标签，请尝试调整搜索条件</p>
            </div>
        `;
    }
    
    // 获取加载状态HTML
    getLoadingHTML() {
        return `
            <div class="loading-state">
                <div class="loading-spinner"></div>
                <p>加载标签中...</p>
            </div>
        `;
    }
    
    // 获取错误状态HTML
    getErrorHTML(message) {
        return `
            <div class="empty-state">
                <i class="fas fa-exclamation-triangle"></i>
                <h5>加载失败</h5>
                <p>${message}</p>
                <button class="btn btn-primary btn-sm" onclick="location.reload()">
                    <i class="fas fa-refresh me-1"></i>重新加载
                </button>
            </div>
        `;
    }
    
    // 获取CSRF令牌
    getCSRFToken() {
        const csrfInput = document.querySelector('input[name="csrf_token"]');
        return csrfInput ? csrfInput.value : '';
    }
}

// 全局标签选择器实例
let globalTagSelector = null;

// 初始化标签选择器
function initializeTagSelector(options = {}) {
    const container = document.getElementById('tag-selector-container');
    if (!container) {
        console.error('TagSelector container not found');
        return null;
    }
    
    globalTagSelector = new TagSelector('tag-selector-container', options);
    return globalTagSelector;
}

// 获取全局标签选择器实例
function getTagSelector() {
    return globalTagSelector;
}

// 导出函数供全局使用
window.TagSelector = TagSelector;
window.initializeTagSelector = initializeTagSelector;
window.getTagSelector = getTagSelector;
