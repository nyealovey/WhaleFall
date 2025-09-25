/**
 * 统一搜索组件JavaScript功能
 */

// 统一搜索功能类
class UnifiedSearch {
    constructor(formId = 'unified-search-form') {
        this.formId = formId;
        this.form = document.getElementById(formId);
        this.init();
    }

    init() {
        if (!this.form) return;
        
        this.bindEvents();
        this.initTagSelector();
        this.initFormValidation();
        this.restoreFormState();
    }

    bindEvents() {
        // 表单提交事件
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSubmit();
        });

        // 清除按钮事件
        const clearBtn = this.form.querySelector('.unified-clear-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.clearForm();
            });
        }

        // 输入框回车事件
        const searchInput = this.form.querySelector('.unified-input');
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.handleSubmit();
                }
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

    initFormValidation() {
        // 实时验证
        const inputs = this.form.querySelectorAll('.unified-input, .unified-select');
        inputs.forEach(input => {
            input.addEventListener('blur', () => {
                this.validateField(input);
            });
        });
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
            }
        }
    }

    handleSubmit() {
        if (this.validateForm()) {
            this.showLoading();
            
            // 构建查询参数，确保搜索条件被保持
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
    }

    handleSelectChange(select) {
        // 特定下拉框变化处理
        if (select.id === 'timeRange' && select.value === 'custom') {
            this.showCustomTimeRange();
        } else if (select.id === 'levelFilter' || select.id === 'moduleFilter') {
            // 日志页面特殊处理
            if (typeof searchLogs === 'function') {
                searchLogs(1);
            }
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

        // 移除验证样式
        this.clearValidationStyles();

        // 直接跳转到没有搜索参数的URL，显示所有数据
        const currentUrl = new URL(window.location);
        window.location.href = currentUrl.pathname;
    }

    clearSelectedTags() {
        const selectedTagsPreview = document.getElementById('selected-tags-preview');
        const selectedTagsChips = document.getElementById('selected-tags-chips');
        const selectedTagNames = document.getElementById('selected-tag-names');
        const selectedTagsCount = document.getElementById('selected-tags-count');

        if (selectedTagsPreview) selectedTagsPreview.style.display = 'none';
        if (selectedTagsChips) selectedTagsChips.innerHTML = '';
        if (selectedTagNames) selectedTagNames.value = '';
        if (selectedTagsCount) selectedTagsCount.textContent = '未选择标签';
    }

    updateSelectedTagsDisplay() {
        const selectedTagNames = document.getElementById('selected-tag-names');
        const selectedTagsChips = document.getElementById('selected-tags-chips');
        const selectedTagsPreview = document.getElementById('selected-tags-preview');
        const selectedTagsCount = document.getElementById('selected-tags-count');

        if (!selectedTagNames || !selectedTagsChips || !selectedTagsPreview || !selectedTagsCount) {
            return;
        }

        const selectedTags = selectedTagNames.value ? selectedTagNames.value.split(',') : [];
        
        if (selectedTags.length > 0) {
            selectedTagsPreview.style.display = 'block';
            selectedTagsCount.textContent = `已选择 ${selectedTags.length} 个标签`;
            
            selectedTagsChips.innerHTML = selectedTags.map(tag => `
                <span class="selected-tag-chip badge bg-primary me-1 mb-1" style="cursor: pointer;">
                    ${tag}
                    <span class="remove-tag ms-1" onclick="unifiedSearch.removeTagFromSelection('${tag}')" style="cursor: pointer;">&times;</span>
                </span>
            `).join('');
        } else {
            selectedTagsPreview.style.display = 'none';
            selectedTagsCount.textContent = '未选择标签';
        }
    }

    openTagSelector() {
        console.log('openTagSelector: 开始打开标签选择器');
        
        // 打开标签选择模态框
        const modal = document.getElementById('tagSelectorModal');
        console.log('openTagSelector: 查找模态框结果:', modal ? '找到' : '未找到');
        
        if (modal) {
            console.log('openTagSelector: 模态框找到，准备显示');
            
            // 初始化标签选择器
            this.initTagSelectorModal();
            
            // 显示模态框
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
            
            console.log('openTagSelector: 模态框显示命令已执行');
        } else {
            console.error('openTagSelector: 标签选择器模态框未找到');
            console.error('openTagSelector: 当前页面DOM状态:');
            console.error('- 所有模态框:', document.querySelectorAll('.modal'));
            console.error('- 所有ID包含tag的元素:', document.querySelectorAll('[id*="tag"]'));
            
            // 如果没有标签选择器，显示提示
            alert('标签选择功能暂不可用');
        }
    }

    initTagSelectorModal() {
        console.log('initTagSelectorModal: 开始初始化标签选择器模态框');
        
        // 初始化标签选择器模态框
        const container = document.getElementById('tag-selector-container');
        console.log('initTagSelectorModal: 查找容器结果:', container ? '找到' : '未找到');
        
        if (!container) {
            console.error('initTagSelectorModal: 标签选择器容器未找到');
            return;
        }

        // 初始化全局标签选择器
        if (typeof initializeTagSelector === 'function') {
            console.log('initTagSelectorModal: 调用全局标签选择器初始化');
            const tagSelector = initializeTagSelector({
                onSelectionChange: (selectedTags) => {
                    console.log('initTagSelectorModal: 标签选择变化:', selectedTags);
                    this.handleTagSelectionChange(selectedTags);
                }
            });
            
            if (tagSelector) {
                console.log('initTagSelectorModal: 标签选择器初始化成功');
                // 设置全局实例
                window.tagSelector = tagSelector;
            } else {
                console.error('initTagSelectorModal: 标签选择器初始化失败');
            }
        } else {
            console.error('initTagSelectorModal: initializeTagSelector函数未定义');
        }
    }

    handleTagSelectionChange(selectedTags) {
        console.log('handleTagSelectionChange: 处理标签选择变化:', selectedTags);
        
        // 更新隐藏的输入框
        const selectedTagNames = document.getElementById('selected-tag-names');
        if (selectedTagNames) {
            const tagNames = selectedTags.map(tag => tag.name).join(',');
            selectedTagNames.value = tagNames;
            console.log('handleTagSelectionChange: 更新隐藏输入框值:', tagNames);
        }
        
        // 更新显示
        this.updateSelectedTagsDisplay();
    }

    loadTags() {
        // 加载标签数据
        fetch('/tags/api/list')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.renderTags(data.data.tags || []);
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
        console.log('bindTagSelectorEvents: 开始绑定标签选择器事件');
        
        // 绑定确认按钮事件
        const confirmBtn = document.getElementById('confirm-selection-btn');
        console.log('bindTagSelectorEvents: 查找确认按钮结果:', confirmBtn ? '找到' : '未找到');
        if (confirmBtn) {
            // 移除之前的事件监听器
            confirmBtn.onclick = null;
            confirmBtn.onclick = () => {
                console.log('bindTagSelectorEvents: 确认按钮被点击，调用confirmTagSelection');
                this.confirmTagSelection();
            };
            console.log('bindTagSelectorEvents: 确认按钮事件绑定成功');
        }

        // 绑定取消按钮事件
        const cancelBtn = document.getElementById('cancel-selection-btn');
        console.log('bindTagSelectorEvents: 查找取消按钮结果:', cancelBtn ? '找到' : '未找到');
        if (cancelBtn) {
            // 移除之前的事件监听器
            cancelBtn.onclick = null;
            cancelBtn.onclick = () => {
                console.log('bindTagSelectorEvents: 取消按钮被点击，调用cancelTagSelection');
                this.cancelTagSelection();
            };
            console.log('bindTagSelectorEvents: 取消按钮事件绑定成功');
        }

        // 绑定搜索框事件
        const searchInput = document.getElementById('tag-search-input');
        if (searchInput) {
            searchInput.oninput = (e) => {
                this.filterTags(e.target.value);
            };
        }
        
        console.log('bindTagSelectorEvents: 事件绑定完成');
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
        console.log('confirmTagSelection: 开始确认标签选择');
        console.log('confirmTagSelection: window.tagSelector存在:', !!window.tagSelector);
        console.log('confirmTagSelection: window.tagSelector.confirmSelection存在:', !!(window.tagSelector && typeof window.tagSelector.confirmSelection === 'function'));
        
        // 调用标签选择器的确认方法
        if (window.tagSelector && typeof window.tagSelector.confirmSelection === 'function') {
            console.log('confirmTagSelection: 调用标签选择器的确认方法');
            window.tagSelector.confirmSelection();
        } else {
            console.log('confirmTagSelection: 标签选择器不可用，使用备用方法');
            
            // 获取当前选中的标签
            const selectedTags = this.getCurrentSelectedTags();
            console.log('confirmTagSelection: 当前选中标签:', selectedTags);
            
            // 更新隐藏的输入框
            const selectedTagNames = document.getElementById('selected-tag-names');
            if (selectedTagNames) {
                const tagNames = selectedTags.map(tag => tag.name).join(',');
                selectedTagNames.value = tagNames;
                console.log('confirmTagSelection: 更新隐藏输入框值:', tagNames);
            }
            
            // 更新显示
            this.updateSelectedTagsDisplay();
            
            // 关闭模态框
            console.log('confirmTagSelection: 准备关闭模态框');
            this.closeTagSelectorModal();
        }
    }

    cancelTagSelection() {
        console.log('cancelTagSelection: 开始取消标签选择');
        
        // 调用标签选择器的取消方法
        if (window.tagSelector && typeof window.tagSelector.cancelSelection === 'function') {
            console.log('cancelTagSelection: 调用标签选择器的取消方法');
            window.tagSelector.cancelSelection();
        } else {
            console.log('cancelTagSelection: 标签选择器不可用，使用备用方法');
            
            // 关闭模态框
            this.closeTagSelectorModal();
        }
    }

    closeTagSelectorModal() {
        console.log('closeTagSelectorModal: 开始关闭标签选择器模态框');
        
        const modal = document.getElementById('tagSelectorModal');
        console.log('closeTagSelectorModal: 模态框元素:', modal);
        if (!modal) {
            console.log('closeTagSelectorModal: 模态框未找到');
            return;
        }
        
        console.log('closeTagSelectorModal: 模态框当前状态:');
        console.log('- display:', modal.style.display);
        console.log('- classList:', modal.classList.toString());
        console.log('- aria-hidden:', modal.getAttribute('aria-hidden'));
        
        // 方法1: 尝试使用Bootstrap Modal实例
        const bsModal = bootstrap.Modal.getInstance(modal);
        console.log('closeTagSelectorModal: Bootstrap Modal实例:', bsModal);
        if (bsModal) {
            console.log('closeTagSelectorModal: 使用Bootstrap Modal实例关闭');
            bsModal.hide();
            
            // 等待Bootstrap完成关闭动画
            setTimeout(() => {
                console.log('closeTagSelectorModal: 延迟执行强制清理');
                this.forceCleanupModal();
            }, 300);
        } else {
            console.log('closeTagSelectorModal: Bootstrap实例不可用，直接清理');
            this.forceCleanupModal();
        }
    }
    
    forceCleanupModal() {
        console.log('forceCleanupModal: 强制清理模态框');
        
        const modal = document.getElementById('tagSelectorModal');
        console.log('forceCleanupModal: 模态框元素:', modal);
        
        if (modal) {
            console.log('forceCleanupModal: 清理前模态框状态:');
            console.log('- display:', modal.style.display);
            console.log('- classList:', modal.classList.toString());
            console.log('- aria-hidden:', modal.getAttribute('aria-hidden'));
            
            // 隐藏模态框
            modal.style.display = 'none';
            modal.classList.remove('show');
            modal.setAttribute('aria-hidden', 'true');
            modal.removeAttribute('aria-modal');
            
            console.log('forceCleanupModal: 清理后模态框状态:');
            console.log('- display:', modal.style.display);
            console.log('- classList:', modal.classList.toString());
            console.log('- aria-hidden:', modal.getAttribute('aria-hidden'));
        }
        
        // 移除body的modal-open类
        console.log('forceCleanupModal: body清理前状态:');
        console.log('- classList:', document.body.classList.toString());
        console.log('- overflow:', document.body.style.overflow);
        console.log('- paddingRight:', document.body.style.paddingRight);
        
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
        
        console.log('forceCleanupModal: body清理后状态:');
        console.log('- classList:', document.body.classList.toString());
        console.log('- overflow:', document.body.style.overflow);
        console.log('- paddingRight:', document.body.style.paddingRight);
        
        // 移除所有backdrop元素
        const backdrops = document.querySelectorAll('.modal-backdrop');
        console.log('forceCleanupModal: 找到backdrop元素数量:', backdrops.length);
        backdrops.forEach((backdrop, index) => {
            console.log(`forceCleanupModal: 移除backdrop ${index + 1}:`, backdrop);
            backdrop.remove();
        });
        
        // 移除所有modal相关的类
        const modalElements = document.querySelectorAll('.modal');
        console.log('forceCleanupModal: 找到modal元素数量:', modalElements.length);
        modalElements.forEach((el, index) => {
            console.log(`forceCleanupModal: 清理modal ${index + 1}:`, el);
            el.classList.remove('show');
            el.style.display = 'none';
        });
        
        console.log('forceCleanupModal: 模态框清理完成');
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
            }
            customTimeRange.style.display = 'block';
        }
    }

    validateForm() {
        let isValid = true;
        const inputs = this.form.querySelectorAll('.unified-input, .unified-select');
        
        inputs.forEach(input => {
            if (!this.validateField(input)) {
                isValid = false;
            }
        });

        return isValid;
    }

    validateField(field) {
        const value = field.value.trim();
        let isValid = true;
        let errorMessage = '';

        // 必填字段验证
        if (field.hasAttribute('required') && !value) {
            isValid = false;
            errorMessage = '此字段为必填项';
        }

        // 长度验证
        const minLength = field.getAttribute('minlength');
        const maxLength = field.getAttribute('maxlength');
        
        if (minLength && value.length < parseInt(minLength)) {
            isValid = false;
            errorMessage = `至少需要 ${minLength} 个字符`;
        }
        
        if (maxLength && value.length > parseInt(maxLength)) {
            isValid = false;
            errorMessage = `最多允许 ${maxLength} 个字符`;
        }

        // 邮箱验证
        if (field.type === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                isValid = false;
                errorMessage = '请输入有效的邮箱地址';
            }
        }

        // 更新字段样式
        this.updateFieldValidation(field, isValid, errorMessage);

        return isValid;
    }

    updateFieldValidation(field, isValid, errorMessage) {
        // 移除之前的验证样式
        field.classList.remove('is-valid', 'is-invalid');
        
        // 移除之前的错误消息
        const existingFeedback = field.parentNode.querySelector('.invalid-feedback');
        if (existingFeedback) {
            existingFeedback.remove();
        }

        if (isValid) {
            field.classList.add('is-valid');
        } else {
            field.classList.add('is-invalid');
            
            // 添加错误消息
            if (errorMessage) {
                const feedback = document.createElement('div');
                feedback.className = 'invalid-feedback';
                feedback.textContent = errorMessage;
                field.parentNode.appendChild(feedback);
            }
        }
    }

    clearValidationStyles() {
        const fields = this.form.querySelectorAll('.unified-input, .unified-select');
        fields.forEach(field => {
            field.classList.remove('is-valid', 'is-invalid');
            const feedback = field.parentNode.querySelector('.invalid-feedback');
            if (feedback) {
                feedback.remove();
            }
        });
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
    console.log('统一搜索组件: DOM加载完成，开始初始化');
    
    // 自动初始化所有统一搜索表单
    const searchForms = document.querySelectorAll('.unified-search-form');
    console.log('统一搜索组件: 找到搜索表单数量:', searchForms.length);
    
    searchForms.forEach((form, index) => {
        console.log(`统一搜索组件: 初始化第${index + 1}个表单, ID:`, form.id);
        unifiedSearch = new UnifiedSearch(form);
        unifiedSearch.init();
        
        // 设置全局实例
        window.unifiedSearch = unifiedSearch;
        console.log('统一搜索组件: 设置全局实例', window.unifiedSearch);
    });
    
    // 检查标签选择器相关元素
    const tagModal = document.getElementById('tagSelectorModal');
    const tagContainer = document.getElementById('tag-selector-container');
    console.log('统一搜索组件: 标签选择器模态框:', tagModal ? '找到' : '未找到');
    console.log('统一搜索组件: 标签选择器容器:', tagContainer ? '找到' : '未找到');
    console.log('统一搜索组件: initializeTagSelector函数:', typeof initializeTagSelector);
});

// 全局清理模态框函数
function forceCleanupAllModals() {
    console.log('forceCleanupAllModals: 强制清理所有模态框');
    
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
    
    console.log('forceCleanupAllModals: 所有模态框清理完成');
}

// 导出类供其他脚本使用
window.UnifiedSearch = UnifiedSearch;
window.forceCleanupAllModals = forceCleanupAllModals;
