/**
 * 凭据列表页面JavaScript
 * 处理凭据状态切换、删除确认、搜索筛选、分页等功能
 */

// 全局变量
let deleteCredentialId = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeCredentialsListPage();
});

// 初始化凭据列表页面
function initializeCredentialsListPage() {
    initializeDeleteConfirmation();
    initializeSearchForm();
    initializeStatusToggles();
    console.log('凭据列表页面已加载');
}

// 初始化删除确认功能
function initializeDeleteConfirmation() {
    const confirmDeleteBtn = document.getElementById('confirmDelete');
    
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', function() {
            handleDeleteConfirmation();
        });
    }
}

// 处理删除确认
function handleDeleteConfirmation() {
    if (deleteCredentialId) {
        const csrfToken = getCSRFToken();
        
        showLoadingState('confirmDelete', '删除中...');
        
        fetch(`/credentials/api/credentials/${deleteCredentialId}/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                showAlert('success', data.message);
                setTimeout(() => location.reload(), 1000);
            } else if (data.error) {
                showAlert('danger', data.error);
            }
        })
        .catch(error => {
            console.error('删除凭据失败:', error);
            showAlert('danger', '删除失败，请稍后重试');
        })
        .finally(() => {
            hideLoadingState('confirmDelete', '确认删除');
        });
    }
}

// 初始化搜索表单
function initializeSearchForm() {
    const searchForm = document.querySelector('form[method="GET"]');
    
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            handleSearchSubmit(e, this);
        });
    }
}

// 处理搜索提交
function handleSearchSubmit(event, form) {
    const searchInput = form.querySelector('input[name="search"]');
    const credentialTypeSelect = form.querySelector('select[name="credential_type"]');
    
    // 基本验证
    if (searchInput && searchInput.value.trim().length > 0 && searchInput.value.trim().length < 2) {
        event.preventDefault();
        showAlert('warning', '搜索关键词至少需要2个字符');
        return false;
    }
    
    // 显示加载状态
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        showLoadingState(submitBtn, '搜索中...');
    }
    
    return true;
}

// 初始化状态切换功能
function initializeStatusToggles() {
    const toggleButtons = document.querySelectorAll('[onclick*="toggleCredential"]');
    
    toggleButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const credentialId = this.getAttribute('data-credential-id');
            const isActive = this.getAttribute('data-is-active') === 'true';
            
            if (credentialId) {
                toggleCredentialStatus(credentialId, isActive, this);
            }
        });
    });
}

// 切换凭据状态
function toggleCredentialStatus(credentialId, isActive, button) {
    const originalHtml = button.innerHTML;
    
    showLoadingState(button, '处理中...');
    button.disabled = true;
    
    const csrfToken = getCSRFToken();
    
    fetch(`/credentials/api/credentials/${credentialId}/toggle`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ is_active: !isActive })
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            showAlert('success', data.message);
            setTimeout(() => location.reload(), 1000);
        } else if (data.error) {
            showAlert('danger', data.error);
        }
    })
    .catch(error => {
        console.error('切换凭据状态失败:', error);
        showAlert('danger', '操作失败，请稍后重试');
    })
    .finally(() => {
        hideLoadingState(button, originalHtml);
        button.disabled = false;
    });
}

// 删除凭据
function deleteCredential(credentialId, credentialName) {
    deleteCredentialId = credentialId;
    
    const deleteModal = document.getElementById('deleteModal');
    const credentialNameElement = document.getElementById('deleteCredentialName');
    
    if (credentialNameElement) {
        credentialNameElement.textContent = credentialName;
    }
    
    if (deleteModal) {
        const modal = new bootstrap.Modal(deleteModal);
        modal.show();
    }
}

// 显示加载状态
function showLoadingState(element, text) {
    if (typeof element === 'string') {
        element = document.getElementById(element);
    }
    
    if (element) {
        element.innerHTML = `<i class="fas fa-spinner fa-spin me-2"></i>${text}`;
        element.disabled = true;
    }
}

// 隐藏加载状态
function hideLoadingState(element, originalText) {
    if (typeof element === 'string') {
        element = document.getElementById(element);
    }
    
    if (element) {
        element.innerHTML = originalText;
        element.disabled = false;
    }
}

// 获取CSRF令牌
function getCSRFToken() {
    const csrfInput = document.querySelector('input[name="csrf_token"]');
    return csrfInput ? csrfInput.value : '';
}

// 显示提示信息
function showAlert(type, message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-triangle'} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
    }
    
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// 显示成功提示
function showSuccessAlert(message) {
    showAlert('success', message);
}

// 显示警告提示
function showWarningAlert(message) {
    showAlert('warning', message);
}

// 显示错误提示
function showErrorAlert(message) {
    showAlert('danger', message);
}

// 搜索功能
function performSearch(searchTerm, credentialType) {
    const params = new URLSearchParams();
    
    if (searchTerm && searchTerm.trim()) {
        params.append('search', searchTerm.trim());
    }
    
    if (credentialType) {
        params.append('credential_type', credentialType);
    }
    
    const queryString = params.toString();
    const url = queryString ? `${window.location.pathname}?${queryString}` : window.location.pathname;
    
    window.location.href = url;
}

// 清除搜索
function clearSearch() {
    window.location.href = window.location.pathname;
}

// 导出凭据
function exportCredentials(format = 'csv') {
    const searchParams = new URLSearchParams(window.location.search);
    searchParams.append('export', format);
    
    const url = `${window.location.pathname}?${searchParams.toString()}`;
    window.open(url, '_blank');
}

// 键盘快捷键
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl+F 聚焦搜索框
        if (e.ctrlKey && e.key === 'f') {
            e.preventDefault();
            const searchInput = document.querySelector('input[name="search"]');
            if (searchInput) {
                searchInput.focus();
            }
        }
        
        // Escape 清除搜索
        if (e.key === 'Escape') {
            const searchInput = document.querySelector('input[name="search"]');
            if (searchInput && searchInput.value) {
                searchInput.value = '';
                clearSearch();
            }
        }
    });
}

// 初始化键盘快捷键
initializeKeyboardShortcuts();

// 表格排序
function sortTable(column, direction = 'asc') {
    const table = document.querySelector('.credentials-table .table');
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.sort((a, b) => {
        const aValue = a.querySelector(`td:nth-child(${column})`).textContent.trim();
        const bValue = b.querySelector(`td:nth-child(${column})`).textContent.trim();
        
        if (direction === 'asc') {
            return aValue.localeCompare(bValue);
        } else {
            return bValue.localeCompare(aValue);
        }
    });
    
    rows.forEach(row => tbody.appendChild(row));
}

// 表格筛选
function filterTable(filterValue) {
    const table = document.querySelector('.credentials-table .table');
    if (!table) return;
    
    const rows = table.querySelectorAll('tbody tr');
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        const shouldShow = text.includes(filterValue.toLowerCase());
        
        row.style.display = shouldShow ? '' : 'none';
    });
}

// 实时搜索
function initializeRealTimeSearch() {
    const searchInput = document.querySelector('input[name="search"]');
    
    if (searchInput) {
        let searchTimeout;
        
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            
            searchTimeout = setTimeout(() => {
                const filterValue = this.value.trim();
                filterTable(filterValue);
            }, 300);
        });
    }
}

// 初始化实时搜索
initializeRealTimeSearch();

// 导出函数供全局使用
window.deleteCredential = deleteCredential;
window.toggleCredentialStatus = toggleCredentialStatus;
window.performSearch = performSearch;
window.clearSearch = clearSearch;
window.exportCredentials = exportCredentials;
window.sortTable = sortTable;
window.filterTable = filterTable;
window.showAlert = showAlert;
window.showSuccessAlert = showSuccessAlert;
window.showWarningAlert = showWarningAlert;
window.showErrorAlert = showErrorAlert;
