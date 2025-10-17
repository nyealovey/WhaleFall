/**
 * 用户管理页面JavaScript
 * 处理用户增删改查、状态切换等功能
 */

// 全局变量

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function () {
    initializeUserManagementPage();
});

// 初始化用户管理页面
function initializeUserManagementPage() {
    initializeAddUserForm();
    initializeEditUserForm();
    initializeDeleteUserHandlers();
    // initializeUserStatusToggles(); // 已移除状态切换功能
    initializeUserTable();
}

// 初始化添加用户表单
function initializeAddUserForm() {
    const addUserForm = document.getElementById('addUserForm');

    if (addUserForm) {
        addUserForm.addEventListener('submit', function (e) {
            handleAddUser(e, this);
        });
    }
}

// 处理添加用户
function handleAddUser(event, form) {
    event.preventDefault();

    const formData = new FormData(form);
    const data = {
        username: formData.get('username'),
        password: formData.get('password'),
        role: formData.get('role'),
        is_active: formData.get('is_active') === 'on'
    };

    // 添加调试日志

    // 验证表单
    if (!validateUserForm(data)) {
        return;
    }

    // 添加调试日志

    showLoadingState(form.querySelector('button[type="submit"]'), '添加中...');

    fetch('/users/api/users', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify(data)
    })
        .then(response => {
            return response.json();
        })
        .then(data => {
            if (data.success) {
                showAlert('success', data.message);
                const modal = bootstrap.Modal.getInstance(document.getElementById('addUserModal'));
                if (modal) modal.hide();
                location.reload();
            } else {
                showAlert('error', data.message || '添加用户失败');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('error', '添加用户失败');
        })
        .finally(() => {
            hideLoadingState(form.querySelector('button[type="submit"]'), '添加用户');
        });
}

// 初始化编辑用户表单
function initializeEditUserForm() {
    const editUserForm = document.getElementById('editUserForm');

    if (editUserForm) {
        editUserForm.addEventListener('submit', function (e) {
            handleEditUser(e, this);
        });
    }
}

// 处理编辑用户
function handleEditUser(event, form) {
    event.preventDefault();

    const formData = new FormData(form);
    const data = {
        user_id: parseInt(formData.get('user_id')),
        username: formData.get('username'),
        role: formData.get('role'),
        is_active: formData.get('is_active') === 'on'
    };

    // 处理密码字段 - 只有非空时才包含
    const password = formData.get('password');
    if (password && password.trim() !== '') {
        data.password = password;
    }

    // 验证表单
    if (!validateUserForm(data, true)) {
        return;
    }

    // 添加调试日志

    showLoadingState(form.querySelector('button[type="submit"]'), '保存中...');

    fetch(`/users/api/users/${data.user_id}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify(data)
    })
        .then(response => {
            return response.json();
        })
        .then(data => {
            if (data.success) {
                showAlert('success', data.message);
                const modal = bootstrap.Modal.getInstance(document.getElementById('editUserModal'));
                if (modal) modal.hide();
                location.reload();
            } else {
                showAlert('error', data.message || '更新用户失败');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('error', '更新用户失败');
        })
        .finally(() => {
            hideLoadingState(form.querySelector('button[type="submit"]'), '保存更改');
        });
}

// 初始化删除用户处理器
function initializeDeleteUserHandlers() {
    const deleteButtons = document.querySelectorAll('[onclick*="deleteUser"]');

    deleteButtons.forEach(button => {
        button.addEventListener('click', function (e) {
            e.preventDefault();
            const userId = this.getAttribute('data-user-id');
            const username = this.getAttribute('data-username');

            if (userId && username) {
                confirmDeleteUser(userId, username);
            }
        });
    });
}

// 确认删除用户（已废弃，使用deleteUser函数）
function confirmDeleteUser(userId, username) {
    deleteUser(userId, username);
}

// 删除用户
function deleteUser(userId, username) {
    if (confirm(`确定要删除用户 "${username}" 吗？此操作不可撤销。`)) {
        performDeleteUser(userId);
    }
}

// 执行删除用户
function performDeleteUser(userId) {
    showLoadingState(document.querySelector(`[data-user-id="${userId}"]`), '删除中...');

    fetch(`/users/api/users/${userId}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('success', data.message);
                location.reload();
            } else {
                showAlert('error', data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('error', '删除用户失败');
        })
        .finally(() => {
            hideLoadingState(document.querySelector(`[data-user-id="${userId}"]`), '删除');
        });
}

// 初始化用户状态切换
function initializeUserStatusToggles() {
    const statusToggles = document.querySelectorAll('.user-status-toggle input');

    statusToggles.forEach(toggle => {
        toggle.addEventListener('change', function () {
            const userId = this.getAttribute('data-user-id');
            const isActive = this.checked;

            if (userId) {
                toggleUserStatus(userId, isActive);
            }
        });
    });
}

// 切换用户状态
function toggleUserStatus(userId, isActive) {
    fetch(`/users/api/users/${userId}/toggle-status`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({
            user_id: userId,
            is_active: isActive
        })
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert('success', data.message);
            } else {
                showAlert('error', data.message);
                // 恢复切换状态
                const toggle = document.querySelector(`input[data-user-id="${userId}"]`);
                if (toggle) {
                    toggle.checked = !isActive;
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('error', '状态切换失败');
            // 恢复切换状态
            const toggle = document.querySelector(`input[data-user-id="${userId}"]`);
            if (toggle) {
                toggle.checked = !isActive;
            }
        });
}





// 初始化用户表格
function initializeUserTable() {
    // 表格排序
    const sortableHeaders = document.querySelectorAll('th[data-sort]');

    sortableHeaders.forEach(header => {
        header.addEventListener('click', function () {
            const column = this.getAttribute('data-sort');
            const direction = this.getAttribute('data-direction') || 'asc';
            sortTable(column, direction);
        });
    });
}

// 表格排序
function sortTable(column, direction) {
    const table = document.querySelector('.user-table .table');
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

// 编辑用户
function editUser(userId) {
    fetch(`/users/api/users/${userId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.data.user) {
                const user = data.data.user;
                document.getElementById('editUserId').value = user.id;
                document.getElementById('editUsername').value = user.username;
                document.getElementById('editPassword').value = ''; // 清空密码字段
                document.getElementById('editRole').value = user.role;
                document.getElementById('editIsActive').checked = user.is_active;

                const modal = new bootstrap.Modal(document.getElementById('editUserModal'));
                modal.show();
            } else {
                showAlert('error', '获取用户信息失败');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('error', '获取用户信息失败');
        });
}

// 验证用户表单
function validateUserForm(data, isEdit = false) {

    if (!data.username || data.username.trim().length < 2) {
        showAlert('error', '用户名至少需要2个字符');
        return false;
    }

    // 密码验证逻辑
    if (!isEdit) {
        // 新建用户时，密码是必需的
        if (!data.password || data.password.length < 6) {
            showAlert('error', '密码至少需要6个字符');
            return false;
        }
    } else {
        // 编辑用户时，如果提供了密码，则验证密码长度
        if (data.password && data.password.length < 6) {
            showAlert('error', '密码至少需要6个字符');
            return false;
        }
    }

    if (!data.role) {
        showAlert('error', '请选择用户角色');
        return false;
    }

    return true;
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

// CSRF Token处理已统一到csrf-utils.js中的全局getCSRFToken函数

// 显示提示信息
function showAlert(type, message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
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
    showAlert('error', message);
}


// 导出用户数据
function exportUsers(format = 'csv') {
    const url = `${window.location.pathname}?export=${format}`;
    window.open(url, '_blank');
}

// 导出函数供全局使用
window.editUser = editUser;
window.deleteUser = deleteUser;
window.confirmDeleteUser = confirmDeleteUser;
window.toggleUserStatus = toggleUserStatus;
window.exportUsers = exportUsers;
window.showAlert = showAlert;
window.showSuccessAlert = showSuccessAlert;
window.showWarningAlert = showWarningAlert;
window.showErrorAlert = showErrorAlert;
