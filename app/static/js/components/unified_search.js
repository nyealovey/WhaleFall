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

        // 触发变化事件
        this.form.dispatchEvent(new Event('change'));
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
                <span class="selected-tag-chip">
                    ${tag}
                    <span class="remove-tag" onclick="removeTag('${tag}')">&times;</span>
                </span>
            `).join('');
        } else {
            selectedTagsPreview.style.display = 'none';
            selectedTagsCount.textContent = '未选择标签';
        }
    }

    openTagSelector() {
        // 打开标签选择模态框
        if (typeof openTagFilterModal === 'function') {
            openTagFilterModal();
        } else {
            // 如果没有标签选择器，显示提示
            alert('标签选择功能暂不可用');
        }
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

// 全局函数
function clearUnifiedSearch() {
    const unifiedSearch = new UnifiedSearch();
    unifiedSearch.clearForm();
}

function removeTag(tagName) {
    UnifiedSearch.removeTag(tagName);
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 自动初始化所有统一搜索表单
    const searchForms = document.querySelectorAll('.unified-search-form');
    searchForms.forEach(form => {
        new UnifiedSearch(form.id);
    });
});

// 导出类供其他脚本使用
window.UnifiedSearch = UnifiedSearch;
