/**
 * 权限查看核心逻辑
 * 提供统一的权限查看功能，支持所有数据库类型
 */

/**
 * 查看账户权限
 * @param {number} accountId - 账户ID
 * @param {Object} options - 选项
 * @param {string} options.apiUrl - API URL，默认为 `/account/api/${accountId}/permissions`
 * @param {Function} options.onSuccess - 成功回调
 * @param {Function} options.onError - 错误回调
 * @param {Function} options.onFinally - 完成回调
 */
function viewAccountPermissions(accountId, options = {}) {
    const {
        apiUrl = `/account/api/${accountId}/permissions`,
        onSuccess,
        onError,
        onFinally
    } = options;
    
    // 如果apiUrl包含模板字符串，则替换为实际的accountId
    const finalApiUrl = apiUrl.replace('${accountId}', accountId);
    
    // 获取CSRF token
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || 
                     document.querySelector('input[name="csrf_token"]')?.value;
    
    // 显示加载状态
    const button = event?.target;
    let originalText = '';
    if (button) {
        originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>加载中...';
        button.disabled = true;
    }
    
    fetch(finalApiUrl, {
        method: 'GET',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin'  // 包含认证cookie
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 调用权限模态框显示
            if (window.showPermissionsModal) {
                window.showPermissionsModal(data.permissions, data.account);
            } else {
                console.error('showPermissionsModal 函数未定义');
            }
            
            // 调用成功回调
            if (onSuccess) {
                onSuccess(data);
            }
        } else {
            const errorMsg = data.error || '获取权限信息失败';
            if (window.showAlert) {
                window.showAlert('danger', errorMsg);
            } else {
                console.error(errorMsg);
            }
            
            // 调用错误回调
            if (onError) {
                onError(data);
            }
        }
    })
    .catch(error => {
        const errorMsg = '获取权限信息失败';
        if (window.showAlert) {
            window.showAlert('danger', errorMsg);
        } else {
            console.error(errorMsg, error);
        }
        
        // 调用错误回调
        if (onError) {
            onError(error);
        }
    })
    .finally(() => {
        // 恢复按钮状态
        if (button) {
            button.innerHTML = originalText;
            button.disabled = false;
        }
        
        // 调用完成回调
        if (onFinally) {
            onFinally();
        }
    });
}

/**
 * 获取账户权限数据
 * @param {number} accountId - 账户ID
 * @param {string} apiUrl - API URL
 * @returns {Promise} 权限数据Promise
 */
function fetchAccountPermissions(accountId, apiUrl = `/account/api/${accountId}/permissions`) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || 
                     document.querySelector('input[name="csrf_token"]')?.value;
    
    // 如果apiUrl包含模板字符串，则替换为实际的accountId
    const finalApiUrl = apiUrl.replace('${accountId}', accountId);
    
    return fetch(finalApiUrl, {
        method: 'GET',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin'  // 包含认证cookie
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            return data;
        } else {
            throw new Error(data.error || '获取权限信息失败');
        }
    });
}

// 导出到全局作用域
window.viewAccountPermissions = viewAccountPermissions;
window.fetchAccountPermissions = fetchAccountPermissions;
