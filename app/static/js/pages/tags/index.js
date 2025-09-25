/**
 * 标签管理页面JavaScript
 * 处理标签删除、搜索、筛选、状态切换等功能
 */

// 全局变量
window.currentTags = window.currentTags || [];
window.currentFilters = window.currentFilters || {};

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
    initializeSearchForm();
    initializeTagActions();
    window.tagsPageInitialized = true;
    console.log('标签管理页面已加载');
}

// 初始化事件处理器
function initializeEventHandlers() {
    // 搜索表单提交
    const searchForm = document.querySelector('form[method="GET"]');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            handleSearchSubmit(e, this);
        });
    }

    // 清除搜索
    const clearSearchBtn = document.getElementById('clearSearch');
    if (clearSearchBtn) {
        clearSearchBtn.addEventListener('click', function() {
            clearSearch();
        });
    }

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
            document.getElementById('deleteForm').action = `/tags/delete/${tagId}`;
        });
    }
}

// 初始化搜索表单
function initializeSearchForm() {
    // 搜索表单的初始化逻辑
    const searchInput = document.querySelector('input[name="search"]');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            // 实时搜索逻辑（如果需要）
        });
    }
}

// 初始化标签操作
function initializeTagActions() {
    // 标签操作相关的初始化逻辑
}

// 处理搜索提交
function handleSearchSubmit(event, form) {
    // 搜索表单提交处理
    const formData = new FormData(form);
    const searchParams = new URLSearchParams(formData);
    
    // 构建新的URL
    const newUrl = `${window.location.pathname}?${searchParams.toString()}`;
    window.location.href = newUrl;
}

// 清除搜索
function clearSearch() {
    const searchInput = document.querySelector('input[name="search"]');
    const categorySelect = document.querySelector('select[name="category"]');
    const statusSelect = document.querySelector('select[name="status"]');
    
    if (searchInput) searchInput.value = '';
    if (categorySelect) categorySelect.value = '';
    if (statusSelect) statusSelect.value = 'all';
    
    // 提交表单
    const form = document.querySelector('form[method="GET"]');
    if (form) {
        form.submit();
    }
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
        showWarningAlert('请选择要删除的标签');
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
        
        const response = await fetch('/tags/api/batch_delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({
                tag_ids: tagIds
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccessAlert(data.message);
            // 刷新页面
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showErrorAlert(`批量删除失败: ${data.error}`);
        }
    } catch (error) {
        console.error('Error during batch delete:', error);
        showErrorAlert('批量删除失败，请检查网络或服务器日志。');
    } finally {
        hideLoadingState('batchDelete', '批量删除');
    }
}

// 处理批量导出
function handleBatchExport() {
    const selectedCheckboxes = document.querySelectorAll('input[name="tag_ids"]:checked');
    if (selectedCheckboxes.length === 0) {
        showWarningAlert('请选择要导出的标签');
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

// 获取CSRF令牌
function getCSRFToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.getAttribute('content') : '';
}

// 显示警告提示
function showWarningAlert(message) {
    showAlert(message, 'warning');
}

// 显示成功提示
function showSuccessAlert(message) {
    showAlert(message, 'success');
}

// 显示错误提示
function showErrorAlert(message) {
    showAlert(message, 'danger');
}

// 显示提示
function showAlert(message, type) {
    // 创建提示元素
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // 插入到页面顶部
    const container = document.querySelector('.container-fluid');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // 自动隐藏
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// 导出函数到全局作用域
window.clearSearch = clearSearch;
window.exportTags = exportTags;
window.showAlert = showAlert;
window.showSuccessAlert = showSuccessAlert;
window.showWarningAlert = showWarningAlert;
window.showErrorAlert = showErrorAlert;