# 用户管理功能技术文档

## 1. 功能概述

### 1.1 功能描述
用户管理功能是鲸落系统的核心管理模块，负责系统用户的创建、编辑、删除、权限分配等操作。该模块提供完整的用户生命周期管理，支持基于角色的访问控制（RBAC），确保系统安全性和用户权限的精确控制。

### 1.2 主要特性
- **用户CRUD操作**：创建、查看、编辑、删除用户
- **角色管理**：支持管理员和普通用户角色
- **权限控制**：基于角色的细粒度权限控制
- **密码管理**：安全的密码设置和验证
- **用户状态管理**：启用/禁用用户账户
- **登录记录**：记录用户登录历史和活动
- **批量操作**：支持批量用户管理操作
- **搜索过滤**：多条件用户搜索和过滤

### 1.3 技术特点
- 基于Flask-Login的用户认证
- bcrypt密码加密存储
- 基于装饰器的权限控制
- 响应式用户界面
- 实时用户状态更新
- 安全审计日志

## 2. 技术架构

### 2.1 整体架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端界面层    │    │   业务逻辑层    │    │   数据存储层    │
│                 │    │                 │    │                 │
│ - 用户列表      │◄──►│ - 用户服务      │◄──►│ - 用户表        │
│ - 用户编辑      │    │ - 权限服务      │    │ - 角色表        │
│ - 权限管理      │    │ - 验证服务      │    │ - 权限表        │
│ - 状态监控      │    │ - 审计服务      │    │ - 审计日志      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2.2 核心组件
- **用户管理服务**：核心用户操作逻辑
- **权限控制服务**：权限验证和分配
- **密码管理服务**：密码加密和验证
- **审计服务**：用户操作审计记录

## 3. 前端实现

### 3.1 页面结构
- **主页面**：`app/templates/users/management.html`
- **样式文件**：`app/static/css/pages/users/management.css`
- **脚本文件**：`app/static/js/pages/users/management.js`

### 3.2 核心组件

#### 3.2.1 用户列表组件
```html
<!-- 用户管理主界面 -->
<div class="container-fluid">
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="card-title mb-0">
                        <i class="fas fa-users me-2"></i>用户管理
                    </h5>
                    <div class="btn-group" role="group">
                        <button type="button" class="btn btn-primary" id="add-user-btn">
                            <i class="fas fa-plus me-1"></i>添加用户
                        </button>
                        <button type="button" class="btn btn-outline-secondary" id="refresh-btn">
                            <i class="fas fa-sync-alt me-1"></i>刷新
                        </button>
                    </div>
                </div>
                <div class="card-body">
                    <!-- 搜索和过滤区域 -->
                    <div class="row mb-3">
                        <div class="col-md-4">
                            <input type="text" class="form-control" id="search-input" placeholder="搜索用户名...">
                        </div>
                        <div class="col-md-2">
                            <select class="form-select" id="role-filter">
                                <option value="">全部角色</option>
                                <option value="admin">管理员</option>
                                <option value="user">普通用户</option>
                            </select>
                        </div>
                        <div class="col-md-2">
                            <select class="form-select" id="status-filter">
                                <option value="">全部状态</option>
                                <option value="active">活跃</option>
                                <option value="inactive">禁用</option>
                            </select>
                        </div>
                        <div class="col-md-2">
                            <button type="button" class="btn btn-outline-primary" id="search-btn">
                                <i class="fas fa-search me-1"></i>搜索
                            </button>
                        </div>
                        <div class="col-md-2">
                            <button type="button" class="btn btn-outline-secondary" id="reset-btn">
                                <i class="fas fa-undo me-1"></i>重置
                            </button>
                        </div>
                    </div>
                    
                    <!-- 用户列表表格 -->
                    <div class="table-responsive">
                        <table class="table table-hover" id="users-table">
                            <thead class="table-light">
                                <tr>
                                    <th>
                                        <input type="checkbox" id="select-all" class="form-check-input">
                                    </th>
                                    <th>用户名</th>
                                    <th>角色</th>
                                    <th>状态</th>
                                    <th>创建时间</th>
                                    <th>最后登录</th>
                                    <th>操作</th>
                                </tr>
                            </thead>
                            <tbody id="users-tbody">
                                <!-- 用户数据通过JavaScript动态加载 -->
                            </tbody>
                        </table>
                    </div>
                    
                    <!-- 分页组件 -->
                    <nav aria-label="用户分页">
                        <ul class="pagination justify-content-center" id="pagination">
                            <!-- 分页组件通过JavaScript动态生成 -->
                        </ul>
                    </nav>
                </div>
            </div>
        </div>
    </div>
</div>
```

#### 3.2.2 用户编辑模态框
```html
<!-- 用户编辑模态框 -->
<div class="modal fade" id="userModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="userModalTitle">
                    <i class="fas fa-user me-2"></i>用户信息
                </h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <form id="user-form">
                    <input type="hidden" id="user-id" name="id">
                    
                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="username" class="form-label">用户名 *</label>
                                <input type="text" class="form-control" id="username" name="username" required>
                                <div class="invalid-feedback" id="username-error"></div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="role" class="form-label">角色 *</label>
                                <select class="form-select" id="role" name="role" required>
                                    <option value="">请选择角色</option>
                                    <option value="admin">管理员</option>
                                    <option value="user">普通用户</option>
                                </select>
                                <div class="invalid-feedback" id="role-error"></div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="password" class="form-label">密码</label>
                                <input type="password" class="form-control" id="password" name="password">
                                <div class="form-text">留空表示不修改密码</div>
                                <div class="invalid-feedback" id="password-error"></div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="mb-3">
                                <label for="confirm-password" class="form-label">确认密码</label>
                                <input type="password" class="form-control" id="confirm-password" name="confirm_password">
                                <div class="invalid-feedback" id="confirm-password-error"></div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="is_active" name="is_active">
                                    <label class="form-check-label" for="is_active">
                                        启用账户
                                    </label>
                                </div>
                            </div>
                        </div>
                    </div>
                </form>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
                <button type="button" class="btn btn-primary" id="save-user-btn">
                    <i class="fas fa-save me-1"></i>保存
                </button>
            </div>
        </div>
    </div>
</div>
```

### 3.3 JavaScript实现

#### 3.3.1 用户管理控制器
```javascript
// 用户管理控制器
class UserManagementController {
    constructor() {
        this.currentPage = 1;
        this.pageSize = 10;
        this.filters = {};
        this.selectedUsers = new Set();
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadUsers();
    }
    
    bindEvents() {
        // 添加用户按钮
        document.getElementById('add-user-btn').addEventListener('click', () => {
            this.showUserModal();
        });
        
        // 刷新按钮
        document.getElementById('refresh-btn').addEventListener('click', () => {
            this.loadUsers();
        });
        
        // 搜索按钮
        document.getElementById('search-btn').addEventListener('click', () => {
            this.applyFilters();
        });
        
        // 重置按钮
        document.getElementById('reset-btn').addEventListener('click', () => {
            this.resetFilters();
        });
        
        // 全选复选框
        document.getElementById('select-all').addEventListener('change', (e) => {
            this.toggleSelectAll(e.target.checked);
        });
        
        // 保存用户按钮
        document.getElementById('save-user-btn').addEventListener('click', () => {
            this.saveUser();
        });
        
        // 搜索输入框回车
        document.getElementById('search-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.applyFilters();
            }
        });
    }
    
    async loadUsers() {
        try {
            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: this.pageSize,
                ...this.filters
            });
            
            const response = await fetch(`/users/api/users?${params}`);
            const data = await response.json();
            
            if (data.success) {
                this.renderUsers(data.data.users);
                this.renderPagination(data.data.pagination);
            } else {
                this.showError(data.message || '加载用户列表失败');
            }
        } catch (error) {
            console.error('加载用户列表失败:', error);
            this.showError('网络错误，请稍后重试');
        }
    }
    
    renderUsers(users) {
        const tbody = document.getElementById('users-tbody');
        tbody.innerHTML = '';
        
        if (users.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center text-muted py-4">
                        <i class="fas fa-users fa-2x mb-2"></i>
                        <p class="mb-0">暂无用户数据</p>
                    </td>
                </tr>
            `;
            return;
        }
        
        users.forEach(user => {
            const row = this.createUserRow(user);
            tbody.appendChild(row);
        });
    }
    
    createUserRow(user) {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <input type="checkbox" class="form-check-input user-checkbox" 
                       value="${user.id}" ${this.selectedUsers.has(user.id) ? 'checked' : ''}>
            </td>
            <td>
                <div class="d-flex align-items-center">
                    <div class="avatar-sm bg-primary text-white rounded-circle d-flex align-items-center justify-content-center me-2">
                        ${user.username.charAt(0).toUpperCase()}
                    </div>
                    <div>
                        <h6 class="mb-0">${this.escapeHtml(user.username)}</h6>
                        <small class="text-muted">ID: ${user.id}</small>
                    </div>
                </div>
            </td>
            <td>
                <span class="badge ${this.getRoleBadgeClass(user.role)}">
                    ${this.getRoleDisplayName(user.role)}
                </span>
            </td>
            <td>
                <span class="badge ${user.is_active ? 'bg-success' : 'bg-secondary'}">
                    ${user.is_active ? '活跃' : '禁用'}
                </span>
            </td>
            <td>
                <small class="text-muted">${this.formatDate(user.created_at)}</small>
            </td>
            <td>
                <small class="text-muted">
                    ${user.last_login ? this.formatDate(user.last_login) : '从未登录'}
                </small>
            </td>
            <td>
                <div class="btn-group btn-group-sm" role="group">
                    <button type="button" class="btn btn-outline-primary" 
                            onclick="userManager.editUser(${user.id})" title="编辑">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button type="button" class="btn btn-outline-danger" 
                            onclick="userManager.deleteUser(${user.id})" title="删除">
                        <i class="fas fa-trash"></i>
                    </button>
                    <button type="button" class="btn btn-outline-secondary" 
                            onclick="userManager.toggleUserStatus(${user.id})" 
                            title="${user.is_active ? '禁用' : '启用'}">
                        <i class="fas fa-${user.is_active ? 'ban' : 'check'}"></i>
                    </button>
                </div>
            </td>
        `;
        
        // 绑定复选框事件
        const checkbox = row.querySelector('.user-checkbox');
        checkbox.addEventListener('change', (e) => {
            this.toggleUserSelection(user.id, e.target.checked);
        });
        
        return row;
    }
    
    getRoleBadgeClass(role) {
        const roleClasses = {
            'admin': 'bg-danger',
            'user': 'bg-primary'
        };
        return roleClasses[role] || 'bg-secondary';
    }
    
    getRoleDisplayName(role) {
        const roleNames = {
            'admin': '管理员',
            'user': '普通用户'
        };
        return roleNames[role] || role;
    }
    
    formatDate(dateString) {
        if (!dateString) return '-';
        return new Date(dateString).toLocaleString('zh-CN');
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    applyFilters() {
        const searchInput = document.getElementById('search-input');
        const roleFilter = document.getElementById('role-filter');
        const statusFilter = document.getElementById('status-filter');
        
        this.filters = {};
        
        if (searchInput.value.trim()) {
            this.filters.search = searchInput.value.trim();
        }
        
        if (roleFilter.value) {
            this.filters.role = roleFilter.value;
        }
        
        if (statusFilter.value) {
            this.filters.status = statusFilter.value;
        }
        
        this.currentPage = 1;
        this.loadUsers();
    }
    
    resetFilters() {
        document.getElementById('search-input').value = '';
        document.getElementById('role-filter').value = '';
        document.getElementById('status-filter').value = '';
        
        this.filters = {};
        this.currentPage = 1;
        this.loadUsers();
    }
    
    toggleSelectAll(checked) {
        const checkboxes = document.querySelectorAll('.user-checkbox');
        checkboxes.forEach(checkbox => {
            checkbox.checked = checked;
            const userId = parseInt(checkbox.value);
            if (checked) {
                this.selectedUsers.add(userId);
            } else {
                this.selectedUsers.delete(userId);
            }
        });
    }
    
    toggleUserSelection(userId, checked) {
        if (checked) {
            this.selectedUsers.add(userId);
        } else {
            this.selectedUsers.delete(userId);
        }
    }
    
    showUserModal(user = null) {
        const modal = new bootstrap.Modal(document.getElementById('userModal'));
        const modalTitle = document.getElementById('userModalTitle');
        const form = document.getElementById('user-form');
        
        // 重置表单
        form.reset();
        
        if (user) {
            // 编辑模式
            modalTitle.innerHTML = '<i class="fas fa-edit me-2"></i>编辑用户';
            document.getElementById('user-id').value = user.id;
            document.getElementById('username').value = user.username;
            document.getElementById('role').value = user.role;
            document.getElementById('is_active').checked = user.is_active;
        } else {
            // 添加模式
            modalTitle.innerHTML = '<i class="fas fa-plus me-2"></i>添加用户';
            document.getElementById('password').required = true;
            document.getElementById('confirm-password').required = true;
        }
        
        modal.show();
    }
    
    async editUser(userId) {
        try {
            const response = await fetch(`/users/api/users/${userId}`);
            const data = await response.json();
            
            if (data.success) {
                this.showUserModal(data.data);
            } else {
                this.showError(data.message || '获取用户信息失败');
            }
        } catch (error) {
            console.error('获取用户信息失败:', error);
            this.showError('网络错误，请稍后重试');
        }
    }
    
    async saveUser() {
        if (!this.validateUserForm()) {
            return;
        }
        
        const form = document.getElementById('user-form');
        const formData = new FormData(form);
        const userId = formData.get('id');
        
        try {
            const url = userId ? `/users/api/users/${userId}` : '/users/api/users';
            const method = userId ? 'PUT' : 'POST';
            
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(Object.fromEntries(formData))
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showSuccess(data.message || '保存成功');
                bootstrap.Modal.getInstance(document.getElementById('userModal')).hide();
                this.loadUsers();
            } else {
                this.showError(data.message || '保存失败');
            }
        } catch (error) {
            console.error('保存用户失败:', error);
            this.showError('网络错误，请稍后重试');
        }
    }
    
    validateUserForm() {
        let isValid = true;
        
        // 验证用户名
        const username = document.getElementById('username').value.trim();
        if (!username) {
            this.showFieldError('username', '请输入用户名');
            isValid = false;
        } else if (!/^[a-zA-Z0-9_]{3,20}$/.test(username)) {
            this.showFieldError('username', '用户名只能包含字母、数字和下划线，长度3-20位');
            isValid = false;
        } else {
            this.clearFieldError('username');
        }
        
        // 验证角色
        const role = document.getElementById('role').value;
        if (!role) {
            this.showFieldError('role', '请选择角色');
            isValid = false;
        } else {
            this.clearFieldError('role');
        }
        
        // 验证密码
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirm-password').value;
        
        if (password || confirmPassword) {
            if (password.length < 8) {
                this.showFieldError('password', '密码至少8位');
                isValid = false;
            } else if (password !== confirmPassword) {
                this.showFieldError('confirm-password', '两次输入的密码不一致');
                isValid = false;
            } else {
                this.clearFieldError('password');
                this.clearFieldError('confirm-password');
            }
        }
        
        return isValid;
    }
    
    showFieldError(fieldName, message) {
        const field = document.getElementById(fieldName);
        const errorDiv = document.getElementById(`${fieldName}-error`);
        
        field.classList.add('is-invalid');
        errorDiv.textContent = message;
    }
    
    clearFieldError(fieldName) {
        const field = document.getElementById(fieldName);
        const errorDiv = document.getElementById(`${fieldName}-error`);
        
        field.classList.remove('is-invalid');
        errorDiv.textContent = '';
    }
    
    async deleteUser(userId) {
        if (!confirm('确定要删除这个用户吗？此操作不可恢复！')) {
            return;
        }
        
        try {
            const response = await fetch(`/users/api/users/${userId}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showSuccess(data.message || '删除成功');
                this.loadUsers();
            } else {
                this.showError(data.message || '删除失败');
            }
        } catch (error) {
            console.error('删除用户失败:', error);
            this.showError('网络错误，请稍后重试');
        }
    }
    
    async toggleUserStatus(userId) {
        try {
            const response = await fetch(`/users/api/users/${userId}/toggle-status`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showSuccess(data.message || '状态更新成功');
                this.loadUsers();
            } else {
                this.showError(data.message || '状态更新失败');
            }
        } catch (error) {
            console.error('更新用户状态失败:', error);
            this.showError('网络错误，请稍后重试');
        }
    }
    
    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    }
    
    showSuccess(message) {
        this.showAlert(message, 'success');
    }
    
    showError(message) {
        this.showAlert(message, 'danger');
    }
    
    showAlert(message, type) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
}

// 初始化用户管理器
const userManager = new UserManagementController();
```

## 4. 后端实现

### 4.1 数据模型
```python
# app/models/user.py
from flask_login import UserMixin
from app import bcrypt, db
from app.utils.timezone import now


class User(UserMixin, db.Model):
    """用户模型"""
    
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="user")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    last_login = db.Column(db.DateTime(timezone=True), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    def set_password(self, password: str) -> None:
        """设置密码（加密）"""
        # 密码强度验证
        if len(password) < 8:
            raise ValueError("密码长度至少8位")
        if not any(c.isupper() for c in password):
            raise ValueError("密码必须包含大写字母")
        if not any(c.islower() for c in password):
            raise ValueError("密码必须包含小写字母")
        if not any(c.isdigit() for c in password):
            raise ValueError("密码必须包含数字")
        
        self.password = bcrypt.generate_password_hash(password, rounds=12).decode("utf-8")
    
    def check_password(self, password: str) -> bool:
        """验证密码"""
        return bcrypt.check_password_hash(self.password, password)
    
    def is_admin(self) -> bool:
        """检查是否为管理员"""
        return self.role == "admin"
    
    def has_permission(self, permission: str) -> bool:
        """检查用户是否有指定权限"""
        if self.is_admin():
            return True
        if self.role == "user":
            return permission == "view"
        return False
    
    def update_last_login(self) -> None:
        """更新最后登录时间"""
        self.last_login = now()
        db.session.commit()
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_active": self.is_active,
        }
```

### 4.2 路由层
```python
# app/routes/users.py
from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user, login_required
from sqlalchemy import or_, and_
from app import db
from app.models.user import User
from app.utils.api_response import APIResponse
from app.utils.decorators import admin_required, view_required, create_required, update_required, delete_required
from app.utils.structlog_config import log_info, log_error


users_bp = Blueprint("users", __name__)


@users_bp.route("/")
@login_required
@view_required
def index() -> str:
    """用户管理首页"""
    try:
        return render_template("users/management.html")
    except Exception as e:
        log_error(f"加载用户管理页面失败: {str(e)}", module="users")
        return render_template("users/management.html", error="页面加载失败")


@users_bp.route("/api/users")
@login_required
@view_required
def api_get_users() -> tuple[dict, int]:
    """获取用户列表API"""
    try:
        # 获取查询参数
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        search = request.args.get("search", "").strip()
        role = request.args.get("role", "").strip()
        status = request.args.get("status", "").strip()
        
        # 构建查询
        query = User.query
        
        # 应用过滤条件
        filters = []
        
        if search:
            filters.append(User.username.ilike(f"%{search}%"))
        
        if role:
            filters.append(User.role == role)
        
        if status:
            if status == "active":
                filters.append(User.is_active == True)
            elif status == "inactive":
                filters.append(User.is_active == False)
        
        if filters:
            query = query.filter(and_(*filters))
        
        # 排序和分页
        query = query.order_by(User.created_at.desc())
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # 转换为字典格式
        users = [user.to_dict() for user in pagination.items]
        
        # 记录查询日志
        log_info(
            "用户列表查询",
            module="users",
            user_id=current_user.id,
            query_params={
                "search": search,
                "role": role,
                "status": status,
                "page": page,
                "per_page": per_page
            },
            result_count=len(users)
        )
        
        return APIResponse.success({
            "users": users,
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_prev": pagination.has_prev,
                "has_next": pagination.has_next,
                "prev_num": pagination.prev_num,
                "next_num": pagination.next_num,
            }
        })
        
    except Exception as e:
        log_error(f"获取用户列表失败: {str(e)}", module="users")
        return APIResponse.error(f"获取用户列表失败: {str(e)}"), 500


@users_bp.route("/api/users/<int:user_id>")
@login_required
@view_required
def api_get_user(user_id: int) -> tuple[dict, int]:
    """获取用户详情API"""
    try:
        user = User.query.get_or_404(user_id)
        
        return APIResponse.success(user.to_dict())
        
    except Exception as e:
        log_error(f"获取用户详情失败: {str(e)}", module="users")
        return APIResponse.error(f"获取用户详情失败: {str(e)}"), 500


@users_bp.route("/api/users", methods=["POST"])
@login_required
@create_required
def api_create_user() -> tuple[dict, int]:
    """创建用户API"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        required_fields = ["username", "password", "role"]
        for field in required_fields:
            if not data.get(field):
                return APIResponse.error(f"缺少必填字段: {field}"), 400
        
        username = data["username"].strip()
        password = data["password"]
        role = data["role"]
        is_active = data.get("is_active", True)
        
        # 验证用户名格式
        if not re.match(r"^[a-zA-Z0-9_]{3,20}$", username):
            return APIResponse.error("用户名只能包含字母、数字和下划线，长度3-20位"), 400
        
        # 检查用户名是否已存在
        if User.query.filter_by(username=username).first():
            return APIResponse.error("用户名已存在"), 400
        
        # 验证角色
        if role not in ["admin", "user"]:
            return APIResponse.error("角色只能是admin或user"), 400
        
        # 创建用户
        user = User(username=username, password=password, role=role)
        user.is_active = is_active
        db.session.add(user)
        db.session.commit()
        
        # 记录操作日志
        log_info(
            "创建用户",
            module="users",
            user_id=current_user.id,
            created_user_id=user.id,
            created_username=user.username,
            created_role=user.role,
            is_active=user.is_active,
        )
        
        return APIResponse.success({
            "message": "用户创建成功",
            "user": user.to_dict()
        })
        
    except ValueError as e:
        return APIResponse.error(str(e)), 400
    except Exception as e:
        db.session.rollback()
        log_error(f"创建用户失败: {str(e)}", module="users")
        return APIResponse.error(f"创建用户失败: {str(e)}"), 500


@users_bp.route("/api/users/<int:user_id>", methods=["PUT"])
@login_required
@update_required
def api_update_user(user_id: int) -> tuple[dict, int]:
    """更新用户API"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        # 更新用户名
        if "username" in data:
            username = data["username"].strip()
            if not re.match(r"^[a-zA-Z0-9_]{3,20}$", username):
                return APIResponse.error("用户名只能包含字母、数字和下划线，长度3-20位"), 400
            
            # 检查用户名是否已被其他用户使用
            existing_user = User.query.filter(User.username == username, User.id != user_id).first()
            if existing_user:
                return APIResponse.error("用户名已被其他用户使用"), 400
            
            user.username = username
        
        # 更新角色
        if "role" in data:
            role = data["role"]
            if role not in ["admin", "user"]:
                return APIResponse.error("角色只能是admin或user"), 400
            user.role = role
        
        # 更新密码
        if "password" in data and data["password"]:
            user.set_password(data["password"])
        
        # 更新状态
        if "is_active" in data:
            user.is_active = data["is_active"]
        
        db.session.commit()
        
        # 记录操作日志
        log_info(
            "更新用户",
            module="users",
            user_id=current_user.id,
            updated_user_id=user.id,
            updated_username=user.username,
            changes=data
        )
        
        return APIResponse.success({
            "message": "用户更新成功",
            "user": user.to_dict()
        })
        
    except ValueError as e:
        return APIResponse.error(str(e)), 400
    except Exception as e:
        db.session.rollback()
        log_error(f"更新用户失败: {str(e)}", module="users")
        return APIResponse.error(f"更新用户失败: {str(e)}"), 500


@users_bp.route("/api/users/<int:user_id>", methods=["DELETE"])
@login_required
@delete_required
def api_delete_user(user_id: int) -> tuple[dict, int]:
    """删除用户API"""
    try:
        user = User.query.get_or_404(user_id)
        
        # 不能删除自己
        if user.id == current_user.id:
            return APIResponse.error("不能删除自己的账户"), 400
        
        username = user.username
        db.session.delete(user)
        db.session.commit()
        
        # 记录操作日志
        log_info(
            "删除用户",
            module="users",
            user_id=current_user.id,
            deleted_user_id=user_id,
            deleted_username=username
        )
        
        return APIResponse.success({"message": "用户删除成功"})
        
    except Exception as e:
        db.session.rollback()
        log_error(f"删除用户失败: {str(e)}", module="users")
        return APIResponse.error(f"删除用户失败: {str(e)}"), 500


@users_bp.route("/api/users/<int:user_id>/toggle-status", methods=["POST"])
@login_required
@update_required
def api_toggle_user_status(user_id: int) -> tuple[dict, int]:
    """切换用户状态API"""
    try:
        user = User.query.get_or_404(user_id)
        
        # 不能禁用自己
        if user.id == current_user.id:
            return APIResponse.error("不能禁用自己的账户"), 400
        
        user.is_active = not user.is_active
        db.session.commit()
        
        status_text = "启用" if user.is_active else "禁用"
        
        # 记录操作日志
        log_info(
            f"{status_text}用户",
            module="users",
            user_id=current_user.id,
            target_user_id=user_id,
            target_username=user.username,
            new_status=user.is_active
        )
        
        return APIResponse.success({
            "message": f"用户{status_text}成功",
            "user": user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        log_error(f"切换用户状态失败: {str(e)}", module="users")
        return APIResponse.error(f"切换用户状态失败: {str(e)}"), 500
```

## 5. 权限控制

### 5.1 权限装饰器
```python
# app/utils/decorators.py
from functools import wraps
from flask import abort
from flask_login import current_user


def admin_required(f):
    """需要管理员权限"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def view_required(f):
    """需要查看权限"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_permission("view"):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def create_required(f):
    """需要创建权限"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_permission("create"):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def update_required(f):
    """需要更新权限"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_permission("update"):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def delete_required(f):
    """需要删除权限"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_permission("delete"):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
```

## 6. 安全考虑

### 6.1 密码安全
- 使用bcrypt加密存储密码
- 强制密码复杂度要求
- 密码强度验证

### 6.2 权限安全
- 基于角色的访问控制
- 权限装饰器验证
- 防止权限提升攻击

### 6.3 操作安全
- 防止删除自己的账户
- 防止禁用自己的账户
- 操作审计日志

## 7. 性能优化

### 7.1 查询优化
- 使用索引优化查询
- 分页查询减少内存使用
- 缓存用户信息

### 7.2 前端优化
- 异步加载用户数据
- 虚拟滚动处理大量数据
- 防抖搜索优化

---

**注意**: 本文档描述了用户管理功能的完整技术实现，包括用户CRUD操作、权限控制、安全考虑等各个方面。该功能为鲸落系统提供了完整的用户管理能力，确保系统安全性和用户权限的精确控制。
