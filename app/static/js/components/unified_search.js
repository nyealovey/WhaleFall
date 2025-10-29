/**
 * 统一搜索组件JavaScript功能
 */

// 统一搜索功能类
class UnifiedSearch {
    constructor(formId = 'unified-search-form') {
        this.formId = formId;
        this.form = document.getElementById(formId);
        this.validator = null;
        this.timeRangeValidationRegistered = false;
        this.init();
    }

    init() {
        if (!this.form) return;
        
        this.bindEvents();
        this.initTagSelector();
        this.setupValidator();
        this.restoreFormState();
    }

    bindEvents() {
        // 表单提交事件
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.triggerValidation();
        });

        // 筛选按钮事件
        const applyBtn = this.form.querySelector('#applyFilters');
        if (applyBtn) {
            applyBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.triggerValidation();
            });
        }

        // 清除按钮事件
        const clearBtn = this.form.querySelector('.unified-clear-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.clearForm();
            });
        }

        // 输入框回车事件 - 只有搜索关键字才需要手动触发
        const searchInput = this.form.querySelector('.unified-input');
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.triggerValidation();
                }
            });
            
            // 搜索输入框失去焦点时不自动筛选，需要用户点击筛选按钮
            searchInput.addEventListener('blur', () => {
                // 不自动触发筛选，让用户手动点击筛选按钮
            });
        }

        // 下拉框变化事件
        const selects = this.form.querySelectorAll('.unified-select');
        selects.forEach(select => {
            select.addEventListener('change', () => {
                this.handleSelectChange(select);
            });
        });
    }

    initTagSelector() {
        const tagBtn = document.getElementById('open-tag-filter-btn');
        const selectedTagsPreview = document.getElementById('selected-tags-preview');
        const selectedTagsChips = document.getElementById('selected-tags-chips');
        const selectedTagNames = document.getElementById('selected-tag-names');
        const selectedTagsCount = document.getElementById('selected-tags-count');

        if (!tagBtn || !selectedTagsPreview || !selectedTagsChips || !selectedTagNames || !selectedTagsCount) {
            return;
        }

        // 标签选择按钮点击事件
        tagBtn.addEventListener('click', () => {
            this.openTagSelector();
        });

        // 初始化已选择的标签显示
        this.updateSelectedTagsDisplay();
    }

    setupValidator() {
        if (!window.FormValidator) {
            console.warn('FormValidator 未加载，统一搜索将跳过内置验证');
            return;
        }

        this.validator = FormValidator.create(`#${this.formId}`);
        if (!this.validator) {
            return;
        }

        this.validator.onSuccess((event) => {
            event.preventDefault();
            this.handleSubmit();
        }).onFail(() => {
            toast.error('请检查筛选条件后再试');
        });

        const selectableFields = this.form.querySelectorAll('.unified-input[required], .unified-select[required]');
        selectableFields.forEach((field) => {
            if (!field.id) {
                return;
            }
            this.validator.addField(`#${field.id}`, [
                {
                    rule: 'required',
                    errorMessage: '此字段为必填项',
                },
            ]);
        });

        this.registerTimeRangeValidation();
    }

    triggerValidation() {
        if (this.validator && this.validator.instance && typeof this.validator.instance.revalidate === 'function') {
            this.validator.instance.revalidate();
        } else {
            this.handleSubmit();
        }
    }

    registerTimeRangeValidation() {
        if (!this.validator || this.timeRangeValidationRegistered) {
            return;
        }

        const startInput = this.form.querySelector('#start_time');
        const endInput = this.form.querySelector('#end_time');
        if (!startInput || !endInput) {
            return;
        }

        if (window.ValidationRules && window.ValidationRules.unifiedSearch) {
            this.validator.addField('#start_time', window.ValidationRules.unifiedSearch.startTime);
            this.validator.addField('#end_time', window.ValidationRules.unifiedSearch.endTime);
        } else {
            this.validator.addField('#start_time', []);
            this.validator.addField('#end_time', []);
        }

        this.timeRangeValidationRegistered = true;
    }

    restoreFormState() {
        // 从URL参数中恢复表单状态
        const urlParams = new URLSearchParams(window.location.search);
        
        // 恢复输入框的值
        const inputs = this.form.querySelectorAll('.unified-input');
        inputs.forEach(input => {
            const value = urlParams.get(input.name);
            if (value) {
                input.value = value;
            }
        });
        
        // 恢复下拉框的值
        const selects = this.form.querySelectorAll('.unified-select');
        selects.forEach(select => {
            const value = urlParams.get(select.name);
            if (value) {
                select.value = value;
            }
        });
        
        // 恢复标签选择状态
        const selectedTagNames = document.getElementById('selected-tag-names');
        if (selectedTagNames) {
            const tags = urlParams.get('tags');
            if (tags) {
                selectedTagNames.value = tags;
                this.updateSelectedTagsDisplay();
                
                // 如果标签选择器已初始化，也要恢复其状态
                if (window.tagSelector && typeof window.tagSelector.setSelectedTags === 'function') {
                    // 将标签名称转换为标签ID
                    const tagNames = tags.split(',');
                    // 这里需要根据标签名称找到对应的标签ID
                    // 暂时先更新显示，标签选择器的状态会在下次打开时同步
                }
            }
        }
        
    }

    handleSubmit(e) {
        this.showLoading();

        const currentPath = window.location.pathname;

        if (this.isJsDynamicPage(currentPath)) {
            if (typeof window.applyFilters === 'function') {
                window.applyFilters();
            } else {
                this.submitWithUrlRedirect();
            }
        } else {
            this.submitWithUrlRedirect();
        }
    }
    
    /**
     * 判断是否为JavaScript动态页面
     * @param {string} path 页面路径
     * @returns {boolean}
     */
    isJsDynamicPage(path) {
        const jsPages = [
            '/sync_sessions/',  // 会话中心
            '/logs/',           // 日志中心
            '/accounts/sync_records',  // 同步记录
            '/database_stats/database/',  // 数据库统计聚合页面
            '/database_stats/instance/'   // 实例统计聚合页面
            // 注意：/accounts/ 是传统表单页面，不是JavaScript动态页面
        ];
        
        for (const jsPage of jsPages) {
            if (path.includes(jsPage)) {
                return true;
            }
        }
        
        return false;
    }
    
    /**
     * 使用URL跳转方式提交表单
     */
    submitWithUrlRedirect() {
        const formData = new FormData(this.form);
        const params = new URLSearchParams();
        
        // 添加所有表单数据到URL参数
        for (let [key, value] of formData.entries()) {
            if (value && value.trim() !== '') {
                params.append(key, value);
            }
        }
        
        // 构建新的URL，保持搜索条件
        const currentUrl = new URL(window.location);
        const newUrl = `${currentUrl.pathname}?${params.toString()}`;
        
        // 跳转到新的URL，保持搜索条件
        window.location.href = newUrl;
    }

    handleSelectChange(select) {
        // 特定下拉框变化处理
        if (select.id === 'timeRange' && select.value === 'custom') {
            this.showCustomTimeRange();
        } else {
            // 自动筛选：当用户选择筛选条件时自动触发筛选
            this.autoApplyFilters();
        }
    }
    
    autoApplyFilters() {
        // 根据页面路径判断使用哪种方法
        const currentPath = window.location.pathname;
        
        if (this.isJsDynamicPage(currentPath)) {
            // JavaScript动态页面：检查是否有自定义的筛选处理函数
            if (typeof window.applyFilters === 'function') {
                window.applyFilters();
            }
        } else {
            // 传统表格页面：使用URL跳转
            this.submitWithUrlRedirect();
        }
    }

    clearForm() {
        // 清除所有输入框
        const inputs = this.form.querySelectorAll('.unified-input');
        inputs.forEach(input => {
            input.value = '';
        });

        // 重置所有下拉框
        const selects = this.form.querySelectorAll('.unified-select');
        selects.forEach(select => {
            select.selectedIndex = 0;
        });

        // 清除标签选择
        this.clearSelectedTags();

        if (this.validator && this.validator.instance && typeof this.validator.instance.refresh === 'function') {
            this.validator.instance.refresh();
        }

        // 根据页面路径判断使用哪种方法
        const currentPath = window.location.pathname;
        
        if (this.isJsDynamicPage(currentPath)) {
            // JavaScript动态页面：检查是否有自定义的清除处理函数
            if (typeof window.clearFilters === 'function') {
                window.clearFilters();
            } else {
                this.clearWithUrlRedirect();
            }
        } else {
            // 传统表格页面：直接使用URL跳转
            this.clearWithUrlRedirect();
        }
    }
    
    /**
     * 使用URL跳转方式清除筛选
     */
    clearWithUrlRedirect() {
        const currentUrl = new URL(window.location);
        window.location.href = currentUrl.pathname;
    }

    clearSelectedTags() {
        const selectedTagsChips = document.getElementById('selected-tags-chips');
        const selectedTagNames = document.getElementById('selected-tag-names');

        if (selectedTagsChips) selectedTagsChips.innerHTML = '';
        if (selectedTagNames) selectedTagNames.value = '';
    }

    updateSelectedTagsDisplay() {
        const selectedTagNames = document.getElementById('selected-tag-names');
        const selectedTagsChips = document.getElementById('selected-tags-chips');


        if (!selectedTagNames || !selectedTagsChips) {
            return;
        }

        const selectedTags = selectedTagNames.value ? selectedTagNames.value.split(',') : [];
        
        if (selectedTags.length > 0) {
            // 获取标签数据以获取颜色信息
            this.loadTagsForDisplay(selectedTags, selectedTagsChips);
        } else {
            selectedTagsChips.innerHTML = '';
        }
    }

    loadTagsForDisplay(selectedTagNames, container) {
        // 加载标签数据以获取颜色信息
        http.get('/tags/api/tags')
            .then(data => {
                if (data.success && data.tags) {
                    const tags = data.tags;
                    container.innerHTML = selectedTagNames.map(tagName => {
                        const tag = tags.find(t => t.name === tagName.trim());
                        const color = tag ? tag.color : 'secondary';
                        // 优先使用display_name，如果没有则使用name
                        const displayName = tag ? (tag.display_name || tag.name) : tagName;
                        
                        return `
                            <span class="badge bg-${color} me-1 mb-1" style="cursor: pointer; position: relative;">
                                ${displayName}
                                <span class="remove-tag ms-1" onclick="unifiedSearch.removeTagFromSelection('${tagName}')" style="cursor: pointer; font-weight: bold;">&times;</span>
                            </span>
                        `;
                    }).join('');
                } else {
                    // 如果无法获取标签数据，使用默认样式
                    container.innerHTML = selectedTagNames.map(tagName => `
                        <span class="badge bg-secondary me-1 mb-1" style="cursor: pointer; position: relative;">
                            ${tagName}
                            <span class="remove-tag ms-1" onclick="unifiedSearch.removeTagFromSelection('${tagName}')" style="cursor: pointer; font-weight: bold;">&times;</span>
                        </span>
                    `).join('');
                }
            })
            .catch(error => {
                console.error('加载标签数据失败:', error);
                // 使用默认样式
                container.innerHTML = selectedTagNames.map(tagName => `
                    <span class="badge bg-secondary me-1 mb-1" style="cursor: pointer; position: relative;">
                        ${tagName}
                        <span class="remove-tag ms-1" onclick="unifiedSearch.removeTagFromSelection('${tagName}')" style="cursor: pointer; font-weight: bold;">&times;</span>
                    </span>
                `).join('');
            });
    }

    openTagSelector() {
        
        // 打开标签选择模态框
        const modal = document.getElementById('tagSelectorModal');
        
        if (modal) {
            
            // 初始化标签选择器
            this.initTagSelectorModal();
            
            // 同步已选择的标签状态到标签选择器
            this.syncSelectedTagsToSelector();
            
            // 显示模态框
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
            
        } else {
            console.error('openTagSelector: 标签选择器模态框未找到');
            // 如果没有标签选择器，显示提示
            alert('标签选择功能暂不可用');
        }
    }

    initTagSelectorModal() {
        
        // 初始化标签选择器模态框
        const container = document.getElementById('tag-selector-container');
        
        if (!container) {
            console.error('initTagSelectorModal: 标签选择器容器未找到');
            return;
        }

        // 初始化全局标签选择器
        if (typeof initializeTagSelector === 'function') {
            const tagSelector = initializeTagSelector({
                onSelectionChange: (selectedTags) => {
                    this.handleTagSelectionChange(selectedTags);
                }
            });
            
            if (tagSelector) {
                // 设置全局实例
                window.tagSelector = tagSelector;
            } else {
                console.error('initTagSelectorModal: 标签选择器初始化失败');
            }
        } else {
            console.error('initTagSelectorModal: initializeTagSelector函数未定义');
        }
    }

    syncSelectedTagsToSelector() {
        
        // 获取当前已选择的标签
        const selectedTagNames = document.getElementById('selected-tag-names');
        if (!selectedTagNames || !selectedTagNames.value) {
            return;
        }
        
        const selectedTagNamesList = selectedTagNames.value.split(',');
        
        // 如果标签选择器已初始化，同步状态
        if (window.tagSelector && typeof window.tagSelector.setSelectedTags === 'function') {
            
            // 需要根据标签名称找到对应的标签ID
            // 这里我们等待标签加载完成后再同步
            setTimeout(() => {
                if (window.tagSelector && window.tagSelector.allTags && window.tagSelector.allTags.length > 0) {
                    const tagIds = selectedTagNamesList.map(tagName => {
                        const tag = window.tagSelector.allTags.find(t => t.name === tagName.trim());
                        return tag ? tag.id : null;
                    }).filter(id => id !== null);
                    
                    window.tagSelector.setSelectedTags(tagIds);
                } else {
                    // 如果标签还没加载完成，再次尝试
                    setTimeout(() => this.syncSelectedTagsToSelector(), 500);
                }
            }, 100);
        } else {
        }
    }

    handleTagSelectionChange(selectedTags) {
        
        // 更新隐藏的输入框
        const selectedTagNames = document.getElementById('selected-tag-names');
        if (selectedTagNames) {
            const tagNames = selectedTags.map(tag => tag.name).join(',');
            selectedTagNames.value = tagNames;
        }
        
        // 更新显示
        this.updateSelectedTagsDisplay();
        
        // 自动触发筛选
        this.autoApplyFilters();
    }

    loadTags() {
        // 加载标签数据
        http.get('/tags/api/tags')
            .then(data => {
                if (data.success) {
                    this.renderTags(data.tags || []);
                }
            })
            .catch(error => {
                console.error('加载标签失败:', error);
            });
    }

    renderTags(tags) {
        const tagListContainer = document.getElementById('tag-list-container');
        if (!tagListContainer) return;

        tagListContainer.innerHTML = tags.map(tag => `
            <div class="tag-item d-flex justify-content-between align-items-center p-2 border rounded mb-2">
                <div class="d-flex align-items-center">
                    <span class="badge bg-${tag.color || 'secondary'} me-2">${tag.name}</span>
                    <span class="text-muted">${tag.description || ''}</span>
                </div>
                <button class="btn btn-sm btn-outline-primary" onclick="unifiedSearch.addTagToSelection('${tag.name}')">
                    <i class="fas fa-plus"></i>
                </button>
            </div>
        `).join('');
    }

    bindTagSelectorEvents() {
        
        // 绑定确认按钮事件
        const confirmBtn = document.getElementById('confirm-selection-btn');
        if (confirmBtn) {
            // 移除之前的事件监听器
            confirmBtn.onclick = null;
            confirmBtn.onclick = () => {
                this.confirmTagSelection();
            };
        }

        // 绑定取消按钮事件
        const cancelBtn = document.getElementById('cancel-selection-btn');
        if (cancelBtn) {
            // 移除之前的事件监听器
            cancelBtn.onclick = null;
            cancelBtn.onclick = () => {
                this.cancelTagSelection();
            };
        }

        // 绑定搜索框事件
        const searchInput = document.getElementById('tag-search-input');
        if (searchInput) {
            searchInput.oninput = (e) => {
                this.filterTags(e.target.value);
            };
        }
        
    }

    addTagToSelection(tagName) {
        const selectedTagNames = document.getElementById('selected-tag-names');
        if (!selectedTagNames) return;

        const currentTags = selectedTagNames.value ? selectedTagNames.value.split(',') : [];
        if (!currentTags.includes(tagName)) {
            currentTags.push(tagName);
            selectedTagNames.value = currentTags.join(',');
            this.updateSelectedTagsDisplay();
        }
    }

    removeTagFromSelection(tagName) {
        const selectedTagNames = document.getElementById('selected-tag-names');
        if (!selectedTagNames) return;
        
        const currentTags = selectedTagNames.value ? selectedTagNames.value.split(',') : [];
        const filteredTags = currentTags.filter(tag => tag !== tagName);
        selectedTagNames.value = filteredTags.join(',');
        this.updateSelectedTagsDisplay();
    }

    getCurrentSelectedTags() {
        // 尝试从全局标签选择器获取选中的标签
        if (window.tagSelector && typeof window.tagSelector.getSelectedTags === 'function') {
            return window.tagSelector.getSelectedTags();
        }
        
        // 如果没有全局标签选择器，从隐藏输入框获取
        const selectedTagNames = document.getElementById('selected-tag-names');
        if (selectedTagNames && selectedTagNames.value) {
            return selectedTagNames.value.split(',').map(name => ({ name: name.trim() }));
        }
        
        return [];
    }

    confirmTagSelection() {
        
        // 调用标签选择器的确认方法
        if (window.tagSelector && typeof window.tagSelector.confirmSelection === 'function') {
            window.tagSelector.confirmSelection();
        } else {
            
            // 获取当前选中的标签
            const selectedTags = this.getCurrentSelectedTags();
            
            // 更新隐藏的输入框
            const selectedTagNames = document.getElementById('selected-tag-names');
            if (selectedTagNames) {
                const tagNames = selectedTags.map(tag => tag.name).join(',');
                selectedTagNames.value = tagNames;
            }
            
            // 更新显示
            this.updateSelectedTagsDisplay();
            
            // 关闭模态框
            this.closeTagSelectorModal();
            
            // 自动触发筛选
            this.autoApplyFilters();
        }
    }

    cancelTagSelection() {
        
        // 调用标签选择器的取消方法
        if (window.tagSelector && typeof window.tagSelector.cancelSelection === 'function') {
            window.tagSelector.cancelSelection();
        } else {
            
            // 关闭模态框
            this.closeTagSelectorModal();
        }
    }

    closeTagSelectorModal() {
        
        const modal = document.getElementById('tagSelectorModal');
        if (!modal) {
            return;
        }
        
        
        // 方法1: 尝试使用Bootstrap Modal实例
        const bsModal = bootstrap.Modal.getInstance(modal);
        if (bsModal) {
            bsModal.hide();
            
            // 等待Bootstrap完成关闭动画
            setTimeout(() => {
                this.forceCleanupModal();
            }, 300);
        } else {
            this.forceCleanupModal();
        }
    }
    
    forceCleanupModal() {
        
        const modal = document.getElementById('tagSelectorModal');
        
        if (modal) {
            
            // 隐藏模态框
            modal.style.display = 'none';
            modal.classList.remove('show');
            modal.setAttribute('aria-hidden', 'true');
            modal.removeAttribute('aria-modal');
            
        }
        
        // 移除body的modal-open类
        
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
        
        
        // 移除所有backdrop元素
        const backdrops = document.querySelectorAll('.modal-backdrop');
        backdrops.forEach((backdrop, index) => {
            backdrop.remove();
        });
        
        // 移除所有modal相关的类
        const modalElements = document.querySelectorAll('.modal');
        modalElements.forEach((el, index) => {
            el.classList.remove('show');
            el.style.display = 'none';
        });
        
    }

    filterTags(query) {
        // 简单的标签过滤
        const tagItems = document.querySelectorAll('.tag-item');
        tagItems.forEach(item => {
            const tagName = item.querySelector('.badge').textContent;
            const tagDesc = item.querySelector('.text-muted').textContent;
            const shouldShow = tagName.toLowerCase().includes(query.toLowerCase()) || 
                             tagDesc.toLowerCase().includes(query.toLowerCase());
            item.style.display = shouldShow ? 'flex' : 'none';
        });
    }

    showCustomTimeRange() {
        // 显示自定义时间范围选择器
        const timeRangeContainer = document.querySelector('.filter-time-range');
        if (timeRangeContainer) {
            let customTimeRange = timeRangeContainer.querySelector('.custom-time-range');
            if (!customTimeRange) {
                customTimeRange = document.createElement('div');
                customTimeRange.className = 'custom-time-range mt-2';
                customTimeRange.innerHTML = `
                    <div class="row g-2">
                        <div class="col-6">
                            <input type="datetime-local" class="form-control" id="start_time" name="start_time" placeholder="开始时间">
                        </div>
                        <div class="col-6">
                            <input type="datetime-local" class="form-control" id="end_time" name="end_time" placeholder="结束时间">
                        </div>
                    </div>
                `;
                timeRangeContainer.appendChild(customTimeRange);

                const startInput = customTimeRange.querySelector('#start_time');
                const endInput = customTimeRange.querySelector('#end_time');
                if (startInput) {
                    startInput.addEventListener('change', () => {
                        this.validator?.revalidateField?.('#start_time');
                        this.validator?.revalidateField?.('#end_time');
                    });
                }
                if (endInput) {
                    endInput.addEventListener('change', () => {
                        this.validator?.revalidateField?.('#start_time');
                        this.validator?.revalidateField?.('#end_time');
                    });
                }
            }
            customTimeRange.style.display = 'block';
            this.registerTimeRangeValidation();
        }
    }

    showLoading() {
        this.form.classList.add('loading');
        const submitBtn = this.form.querySelector('.unified-search-btn');
        if (submitBtn) {
            submitBtn.disabled = true;
        }
    }

    hideLoading() {
        this.form.classList.remove('loading');
        const submitBtn = this.form.querySelector('.unified-search-btn');
        if (submitBtn) {
            submitBtn.disabled = false;
        }
    }

    // 静态方法：移除标签
    static removeTag(tagName) {
        const selectedTagNames = document.getElementById('selected-tag-names');
        if (selectedTagNames) {
            const selectedTags = selectedTagNames.value ? selectedTagNames.value.split(',') : [];
            const filteredTags = selectedTags.filter(tag => tag !== tagName);
            selectedTagNames.value = filteredTags.join(',');
            
            // 更新显示
            const unifiedSearch = new UnifiedSearch();
            unifiedSearch.updateSelectedTagsDisplay();
        }
    }
}

// 全局变量存储当前实例
let unifiedSearch = null;

// 全局函数
function clearUnifiedSearch() {
    if (unifiedSearch) {
        unifiedSearch.clearForm();
    } else {
        // 如果没有统一搜索实例，直接清除表单并提交
        const form = document.querySelector('.unified-search-form');
        if (form) {
            // 清除所有输入框
            const inputs = form.querySelectorAll('.unified-input');
            inputs.forEach(input => {
                input.value = '';
            });

            // 重置所有下拉框
            const selects = form.querySelectorAll('.unified-select');
            selects.forEach(select => {
                select.selectedIndex = 0;
            });

            // 清除标签选择
            const selectedTagsPreview = document.getElementById('selected-tags-preview');
            const selectedTagsChips = document.getElementById('selected-tags-chips');
            const selectedTagNames = document.getElementById('selected-tag-names');
            const selectedTagsCount = document.getElementById('selected-tags-count');

            if (selectedTagsPreview) selectedTagsPreview.style.display = 'none';
            if (selectedTagsChips) selectedTagsChips.innerHTML = '';
            if (selectedTagNames) selectedTagNames.value = '';
            if (selectedTagsCount) selectedTagsCount.textContent = '未选择标签';

            // 直接跳转到没有搜索参数的URL，显示所有数据
            const currentUrl = new URL(window.location);
            window.location.href = currentUrl.pathname;
        }
    }
}

function removeTag(tagName) {
    if (unifiedSearch) {
        unifiedSearch.removeTagFromSelection(tagName);
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    
    // 自动初始化所有统一搜索表单
    const searchForms = document.querySelectorAll('.unified-search-form');
    
    searchForms.forEach((form, index) => {
        unifiedSearch = new UnifiedSearch(form.id);
        unifiedSearch.init();
        
        // 设置全局实例
        window.unifiedSearch = unifiedSearch;
        window.unifiedSearchInstance = unifiedSearch; // 添加这个别名
    });
    
    // 检查标签选择器相关元素
    const tagModal = document.getElementById('tagSelectorModal');
    const tagContainer = document.getElementById('tag-selector-container');
});

// 全局清理模态框函数
function forceCleanupAllModals() {
    
    // 移除body的modal-open类
    document.body.classList.remove('modal-open');
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
    
    // 移除所有backdrop元素
    const backdrops = document.querySelectorAll('.modal-backdrop');
    backdrops.forEach(backdrop => {
        backdrop.remove();
    });
    
    // 隐藏所有模态框
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.style.display = 'none';
        modal.classList.remove('show');
        modal.setAttribute('aria-hidden', 'true');
        modal.removeAttribute('aria-modal');
    });
    
}

// 导出类供其他脚本使用
window.UnifiedSearch = UnifiedSearch;
window.forceCleanupAllModals = forceCleanupAllModals;
