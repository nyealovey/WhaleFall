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

    handleSubmit() {
        if (this.validateForm()) {
            this.showLoading();
            this.form.submit();
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

        // 提交表单以刷新数据
        this.form.submit();
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
        // 打开标签选择模态框
        const modal = document.getElementById('tagSelectorModal');
        if (modal) {
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
            
            // 初始化标签选择器
            this.initTagSelectorModal();
        } else {
            // 如果没有标签选择器，显示提示
            alert('标签选择功能暂不可用');
        }
    }

    initTagSelectorModal() {
        // 初始化标签选择器模态框
        const container = document.getElementById('tag-selector-container');
        if (!container) return;

        // 加载标签数据
        this.loadTags();
        
        // 绑定事件
        this.bindTagSelectorEvents();
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
        // 绑定确认按钮事件
        const confirmBtn = document.getElementById('confirm-selection-btn');
        if (confirmBtn) {
            confirmBtn.onclick = () => {
                this.confirmTagSelection();
            };
        }

        // 绑定取消按钮事件
        const cancelBtn = document.getElementById('cancel-selection-btn');
        if (cancelBtn) {
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

    confirmTagSelection() {
        // 关闭模态框
        const modal = document.getElementById('tagSelectorModal');
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        }
    }

    cancelTagSelection() {
        // 关闭模态框
        const modal = document.getElementById('tagSelectorModal');
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        }
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

            // 提交表单以刷新数据
            form.submit();
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
    searchForms.forEach(form => {
        unifiedSearch = new UnifiedSearch(form.id);
    });
});

// 导出类供其他脚本使用
window.UnifiedSearch = UnifiedSearch;
