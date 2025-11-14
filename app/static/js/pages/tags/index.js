/**
 * 标签管理页面JavaScript
 * 处理标签删除、搜索、筛选、状态切换等功能
 */

// 全局变量
window.currentTags = window.currentTags || [];
window.currentFilters = window.currentFilters || {};
const TAG_FILTER_FORM_ID = 'tag-filter-form';
const AUTO_APPLY_FILTER_CHANGE = true;
let tagFilterEventHandler = null;

// 防止重复初始化
if (window.tagsPageInitialized) {
    console.warn('标签管理页面已经初始化，跳过重复初始化');
} else {
    // 页面加载完成后初始化
    document.addEventListener('DOMContentLoaded', function() {
        initializeTagsPage();
    });
}

// 初始化标签管理页面
function initializeTagsPage() {
    if (window.tagsPageInitialized) {
        console.warn('标签管理页面已经初始化，跳过重复初始化');
        return;
    }
    
    initializeEventHandlers();
    initializeTagActions();
    registerTagFilterForm();
    subscribeFilterEvents();
    window.tagsPageInitialized = true;
}

// 初始化事件处理器
function initializeEventHandlers() {
    // 批量操作
    const selectAllCheckbox = document.getElementById('selectAll');
    const tagCheckboxes = document.querySelectorAll('input[name="tag_ids"]');
    const batchActions = document.querySelector('.batch-actions');

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            toggleAllTags(this.checked);
        });
    }

    if (tagCheckboxes.length > 0) {
        tagCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                updateBatchActions();
            });
        });
    }

    // 批量删除
    const batchDeleteBtn = document.getElementById('batchDelete');
    if (batchDeleteBtn) {
        batchDeleteBtn.addEventListener('click', function() {
            handleBatchDelete();
        });
    }

    // 批量导出
    const batchExportBtn = document.getElementById('batchExport');
    if (batchExportBtn) {
        batchExportBtn.addEventListener('click', function() {
            handleBatchExport();
        });
    }

    // 删除确认
    const deleteModal = document.getElementById('deleteModal');
    if (deleteModal) {
        deleteModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const tagId = button.getAttribute('data-tag-id');
            const tagName = button.getAttribute('data-tag-name');
            
            document.getElementById('deleteTagName').textContent = tagName;
            document.getElementById('deleteForm').action = `/tags/api/delete/${tagId}`;
        });
    }
}

// 初始化标签操作
function initializeTagActions() {
    // 标签操作相关的初始化逻辑
}

// 切换所有标签选择
function toggleAllTags(checked) {
    const tagCheckboxes = document.querySelectorAll('input[name="tag_ids"]');
    tagCheckboxes.forEach(checkbox => {
        checkbox.checked = checked;
    });
    updateBatchActions();
}

// 更新批量操作按钮状态
function updateBatchActions() {
    const selectedCheckboxes = document.querySelectorAll('input[name="tag_ids"]:checked');
    const batchActions = document.querySelector('.batch-actions');
    
    if (batchActions) {
        if (selectedCheckboxes.length > 0) {
            batchActions.style.display = 'block';
        } else {
            batchActions.style.display = 'none';
        }
    }
}

// 处理批量删除
function handleBatchDelete() {
    const selectedCheckboxes = document.querySelectorAll('input[name="tag_ids"]:checked');
    if (selectedCheckboxes.length === 0) {
        toast.warning('请选择要删除的标签');
        return;
    }
    
    const tagIds = Array.from(selectedCheckboxes).map(cb => cb.value);
    const confirmText = `确定要删除选中的 ${tagIds.length} 个标签吗？此操作不可撤销！`;
    
    if (confirm(confirmText)) {
        // 执行批量删除
        performBatchDelete(tagIds);
    }
}

// 执行批量删除
async function performBatchDelete(tagIds) {
    try {
        showLoadingState('batchDelete', '删除中...');
        
        const data = await http.post('/tags/api/batch_delete', { tag_ids: tagIds });
        
        if (data.success) {
            toast.success(data.message);
            // 刷新页面
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            toast.error(`批量删除失败: ${data.error}`);
        }
    } catch (error) {
        console.error('Error during batch delete:', error);
        toast.error('批量删除失败，请检查网络或服务器日志。');
    } finally {
        hideLoadingState('batchDelete', '批量删除');
    }
}

function registerTagFilterForm() {
    if (!window.FilterUtils) {
        console.warn('FilterUtils 未加载，跳过标签筛选初始化');
        return;
    }
    const selector = `#${TAG_FILTER_FORM_ID}`;
    const form = document.querySelector(selector);
    if (!form) {
        return;
    }
    window.FilterUtils.registerFilterForm(selector, {
        onSubmit: ({ form, event }) => {
            event?.preventDefault?.();
            applyTagFilters(form);
        },
        onClear: ({ form, event }) => {
            event?.preventDefault?.();
            resetTagFilters(form);
        },
        autoSubmitOnChange: false,
    });
}

function subscribeFilterEvents() {
    if (!window.EventBus) {
        return;
    }
    const form = document.getElementById(TAG_FILTER_FORM_ID);
    if (!form) {
        return;
    }
    const handler = (detail) => {
        if (!detail) {
            return;
        }
        const incoming = (detail.formId || '').replace(/^#/, '');
        if (incoming !== TAG_FILTER_FORM_ID) {
            return;
        }
        switch (detail.action) {
            case 'clear':
                resetTagFilters(form);
                break;
            case 'change':
                if (AUTO_APPLY_FILTER_CHANGE) {
                    applyTagFilters(form, detail.values);
                }
                break;
            case 'submit':
                applyTagFilters(form, detail.values);
                break;
            default:
                break;
        }
    };
    ['change', 'submit', 'clear'].forEach((action) => {
        EventBus.on(`filters:${action}`, handler);
    });
    tagFilterEventHandler = handler;
    window.addEventListener('beforeunload', () => {
        cleanupFilterEvents();
    }, { once: true });
}

function cleanupFilterEvents() {
    if (!window.EventBus || !tagFilterEventHandler) {
        return;
    }
    ['change', 'submit', 'clear'].forEach((action) => {
        EventBus.off(`filters:${action}`, tagFilterEventHandler);
    });
    tagFilterEventHandler = null;
}

function applyTagFilters(form, values) {
    const targetForm = form || document.getElementById(TAG_FILTER_FORM_ID);
    if (!targetForm) {
        return;
    }
    const data = values && Object.keys(values).length ? values : collectFormValues(targetForm);
    const params = new URLSearchParams();
    Object.entries(data || {}).forEach(([key, value]) => {
        if (key === 'csrf_token') {
            return;
        }
        if (value === undefined || value === null) {
            return;
        }
        if (Array.isArray(value)) {
            value.filter((item) => item !== '' && item !== null).forEach((item) => {
                params.append(key, item);
            });
        } else if (String(value).trim() !== '') {
            params.append(key, value);
        }
    });
    const action = targetForm.getAttribute('action') || window.location.pathname;
    const query = params.toString();
    window.location.href = query ? `${action}?${query}` : action;
}

function resetTagFilters(form) {
    const targetForm = form || document.getElementById(TAG_FILTER_FORM_ID);
    if (targetForm) {
        targetForm.reset();
    }
    applyTagFilters(targetForm, {});
}

function collectFormValues(form) {
    if (!form) {
        return {};
    }
    if (window.FilterUtils && typeof window.FilterUtils.serializeForm === 'function') {
        return window.FilterUtils.serializeForm(form);
    }
    const formData = new FormData(form);
    const result = {};
    formData.forEach((value, key) => {
        const normalized = value instanceof File ? value.name : value;
        if (result[key] === undefined) {
            result[key] = normalized;
        } else if (Array.isArray(result[key])) {
            result[key].push(normalized);
        } else {
            result[key] = [result[key], normalized];
        }
    });
    return result;
}

// 处理批量导出
function handleBatchExport() {
    const selectedCheckboxes = document.querySelectorAll('input[name="tag_ids"]:checked');
    if (selectedCheckboxes.length === 0) {
        toast.warning('请选择要导出的标签');
        return;
    }
    
    const tagIds = Array.from(selectedCheckboxes).map(cb => cb.value);
    exportTags(tagIds);
}

// 导出标签
function exportTags(tagIds = null) {
    const params = new URLSearchParams();
    if (tagIds && tagIds.length > 0) {
        params.append('tag_ids', tagIds.join(','));
    }
    
    // 添加当前筛选条件
    const searchInput = document.querySelector('input[name="search"]');
    const categorySelect = document.querySelector('select[name="category"]');
    const statusSelect = document.querySelector('select[name="status"]');
    
    if (searchInput && searchInput.value) {
        params.append('search', searchInput.value);
    }
    if (categorySelect && categorySelect.value) {
        params.append('category', categorySelect.value);
    }
    if (statusSelect && statusSelect.value && statusSelect.value !== 'all') {
        params.append('status', statusSelect.value);
    }
    
    const exportUrl = `/tags/export?${params.toString()}`;
    window.open(exportUrl, '_blank');
}

// 显示加载状态
function showLoadingState(buttonId, text) {
    const button = document.getElementById(buttonId);
    if (button) {
        button.disabled = true;
        button.innerHTML = `<i class="fas fa-spinner fa-spin me-1"></i>${text}`;
    }
}

// 隐藏加载状态
function hideLoadingState(buttonId, originalText) {
    const button = document.getElementById(buttonId);
    if (button) {
        button.disabled = false;
        button.innerHTML = originalText;
    }
}

// CSRF Token处理已统一到csrf-utils.js中的全局getCSRFToken函数

// 导出函数到全局作用域
window.exportTags = exportTags;
