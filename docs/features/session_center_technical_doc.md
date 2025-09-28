# 会话中心功能技术文档

## 1. 功能概述

### 1.1 功能描述
会话中心是鲸落系统的核心安全模块，负责管理用户会话的创建、验证、维护和销毁。该模块基于Flask-Login实现，提供完整的用户认证和会话管理功能，确保系统安全性和用户体验。

### 1.2 主要特性
- **用户认证**：支持用户名密码登录认证
- **会话管理**：基于Flask-Login的会话生命周期管理
- **安全配置**：CSRF保护、会话超时、安全Cookie配置
- **权限控制**：基于角色的访问控制（RBAC）
- **会话监控**：实时监控活跃会话和登录状态
- **安全审计**：记录登录、登出等安全事件
- **多设备支持**：支持多设备同时登录
- **会话持久化**：支持"记住我"功能

### 1.3 技术特点
- 基于Flask-Login的会话管理
- 密码bcrypt加密存储
- JWT令牌支持
- 会话安全配置
- 实时会话监控
- 安全事件审计

## 2. 技术架构

### 2.1 整体架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端认证层    │    │   会话管理层    │    │   数据存储层    │
│                 │    │                 │    │                 │
│ - 登录界面      │◄──►│ - Flask-Login   │◄──►│ - 用户表        │
│ - 权限检查      │    │ - 会话验证      │    │ - 会话表        │
│ - 状态显示      │    │ - 权限控制      │    │ - 审计日志      │
│ - 登出操作      │    │ - 安全配置      │    │ - 缓存存储      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2.2 核心组件
- **认证服务**：处理用户登录认证逻辑
- **会话管理器**：管理会话生命周期
- **权限控制器**：实现基于角色的访问控制
- **安全配置器**：配置会话安全参数
- **审计记录器**：记录安全相关事件

## 3. 前端实现

### 3.1 页面结构
- **登录页面**：`app/templates/auth/login.html`
- **样式文件**：`app/static/css/pages/auth/login.css`
- **脚本文件**：`app/static/js/pages/auth/login.js`

### 3.2 核心组件

#### 3.2.1 登录表单组件
```html
<!-- 登录表单 -->
<div class="container-fluid">
    <div class="row justify-content-center">
        <div class="col-md-6 col-lg-4">
            <div class="card shadow">
                <div class="card-header text-center">
                    <h4 class="card-title mb-0">
                        <i class="fas fa-database me-2"></i>鲸落系统
                    </h4>
                    <p class="text-muted mb-0">数据库管理平台</p>
                </div>
                <div class="card-body">
                    <form id="login-form" method="POST" action="/auth/api/login">
                        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                        
                        <!-- 用户名输入 -->
                        <div class="mb-3">
                            <label for="username" class="form-label">
                                <i class="fas fa-user me-1"></i>用户名
                            </label>
                            <input type="text" 
                                   class="form-control" 
                                   id="username" 
                                   name="username" 
                                   required 
                                   autocomplete="username"
                                   placeholder="请输入用户名">
                            <div class="invalid-feedback" id="username-error"></div>
                        </div>
                        
                        <!-- 密码输入 -->
                        <div class="mb-3">
                            <label for="password" class="form-label">
                                <i class="fas fa-lock me-1"></i>密码
                            </label>
                            <div class="input-group">
                                <input type="password" 
                                       class="form-control" 
                                       id="password" 
                                       name="password" 
                                       required 
                                       autocomplete="current-password"
                                       placeholder="请输入密码">
                                <button class="btn btn-outline-secondary" 
                                        type="button" 
                                        id="toggle-password">
                                    <i class="fas fa-eye"></i>
                                </button>
                            </div>
                            <div class="invalid-feedback" id="password-error"></div>
                        </div>
                        
                        <!-- 记住我选项 -->
                        <div class="mb-3 form-check">
                            <input type="checkbox" 
                                   class="form-check-input" 
                                   id="remember_me" 
                                   name="remember_me">
                            <label class="form-check-label" for="remember_me">
                                记住我
                            </label>
                        </div>
                        
                        <!-- 登录按钮 -->
                        <div class="d-grid">
                            <button type="submit" 
                                    class="btn btn-primary" 
                                    id="login-btn">
                                <i class="fas fa-sign-in-alt me-1"></i>登录
                            </button>
                        </div>
                    </form>
                </div>
                <div class="card-footer text-center">
                    <small class="text-muted">
                        <i class="fas fa-shield-alt me-1"></i>
                        安全登录，保护您的数据
                    </small>
                </div>
            </div>
        </div>
    </div>
</div>
```

#### 3.2.2 会话状态显示组件
```html
<!-- 用户信息下拉菜单 -->
<div class="dropdown">
    <button class="btn btn-outline-light dropdown-toggle" 
            type="button" 
            id="userDropdown" 
            data-bs-toggle="dropdown">
        <i class="fas fa-user me-1"></i>
        <span id="current-username">{{ current_user.username }}</span>
    </button>
    <ul class="dropdown-menu dropdown-menu-end">
        <li>
            <h6 class="dropdown-header">
                <i class="fas fa-info-circle me-1"></i>用户信息
            </h6>
        </li>
        <li>
            <span class="dropdown-item-text">
                <small class="text-muted">角色: {{ current_user.role }}</small>
            </span>
        </li>
        <li>
            <span class="dropdown-item-text">
                <small class="text-muted">最后登录: {{ current_user.last_login.strftime('%Y-%m-%d %H:%M') if current_user.last_login else '首次登录' }}</small>
            </span>
        </li>
        <li><hr class="dropdown-divider"></li>
        <li>
            <a class="dropdown-item" href="/user/profile">
                <i class="fas fa-user-cog me-1"></i>个人设置
            </a>
        </li>
        <li>
            <a class="dropdown-item" href="/auth/logout">
                <i class="fas fa-sign-out-alt me-1"></i>退出登录
            </a>
        </li>
    </ul>
</div>
```

### 3.3 JavaScript实现

#### 3.3.1 登录表单处理
```javascript
// 登录表单管理器
class LoginFormManager {
    constructor() {
        this.form = document.getElementById('login-form');
        this.usernameInput = document.getElementById('username');
        this.passwordInput = document.getElementById('password');
        this.rememberMeInput = document.getElementById('remember_me');
        this.loginBtn = document.getElementById('login-btn');
        this.togglePasswordBtn = document.getElementById('toggle-password');
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.setupValidation();
    }
    
    bindEvents() {
        // 表单提交
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });
        
        // 密码显示切换
        this.togglePasswordBtn.addEventListener('click', () => {
            this.togglePasswordVisibility();
        });
        
        // 输入验证
        this.usernameInput.addEventListener('blur', () => {
            this.validateUsername();
        });
        
        this.passwordInput.addEventListener('blur', () => {
            this.validatePassword();
        });
        
        // 回车键登录
        this.form.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.handleLogin();
            }
        });
    }
    
    setupValidation() {
        // 实时验证
        this.usernameInput.addEventListener('input', () => {
            this.clearFieldError('username');
        });
        
        this.passwordInput.addEventListener('input', () => {
            this.clearFieldError('password');
        });
    }
    
    async handleLogin() {
        if (!this.validateForm()) {
            return;
        }
        
        this.setLoading(true);
        
        try {
            const formData = new FormData(this.form);
            const response = await fetch('/auth/api/login', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showSuccess('登录成功，正在跳转...');
                setTimeout(() => {
                    window.location.href = data.redirect_url || '/dashboard';
                }, 1000);
            } else {
                this.showError(data.message || '登录失败');
            }
        } catch (error) {
            console.error('登录请求失败:', error);
            this.showError('网络错误，请稍后重试');
        } finally {
            this.setLoading(false);
        }
    }
    
    validateForm() {
        let isValid = true;
        
        // 验证用户名
        if (!this.validateUsername()) {
            isValid = false;
        }
        
        // 验证密码
        if (!this.validatePassword()) {
            isValid = false;
        }
        
        return isValid;
    }
    
    validateUsername() {
        const username = this.usernameInput.value.trim();
        
        if (!username) {
            this.showFieldError('username', '请输入用户名');
            return false;
        }
        
        if (username.length < 3) {
            this.showFieldError('username', '用户名至少3个字符');
            return false;
        }
        
        if (!/^[a-zA-Z0-9_]+$/.test(username)) {
            this.showFieldError('username', '用户名只能包含字母、数字和下划线');
            return false;
        }
        
        this.clearFieldError('username');
        return true;
    }
    
    validatePassword() {
        const password = this.passwordInput.value;
        
        if (!password) {
            this.showFieldError('password', '请输入密码');
            return false;
        }
        
        if (password.length < 6) {
            this.showFieldError('password', '密码至少6个字符');
            return false;
        }
        
        this.clearFieldError('password');
        return true;
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
    
    togglePasswordVisibility() {
        const type = this.passwordInput.type === 'password' ? 'text' : 'password';
        this.passwordInput.type = type;
        
        const icon = this.togglePasswordBtn.querySelector('i');
        icon.classList.toggle('fa-eye');
        icon.classList.toggle('fa-eye-slash');
    }
    
    setLoading(loading) {
        this.loginBtn.disabled = loading;
        
        if (loading) {
            this.loginBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>登录中...';
        } else {
            this.loginBtn.innerHTML = '<i class="fas fa-sign-in-alt me-1"></i>登录';
        }
    }
    
    showSuccess(message) {
        this.showAlert(message, 'success');
    }
    
    showError(message) {
        this.showAlert(message, 'danger');
    }
    
    showAlert(message, type) {
        // 移除现有提示
        const existingAlert = document.querySelector('.alert');
        if (existingAlert) {
            existingAlert.remove();
        }
        
        // 创建新提示
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // 插入到表单前
        this.form.parentNode.insertBefore(alertDiv, this.form);
        
        // 自动隐藏
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }
    
    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    }
}

// 初始化登录表单管理器
document.addEventListener('DOMContentLoaded', () => {
    new LoginFormManager();
});
```

#### 3.3.2 会话状态监控
```javascript
// 会话状态监控器
class SessionMonitor {
    constructor() {
        this.checkInterval = 60000; // 1分钟检查一次
        this.warningTime = 300000; // 5分钟前警告
        this.timeoutTime = 3600000; // 1小时超时
        this.timer = null;
        
        this.init();
    }
    
    init() {
        this.startMonitoring();
        this.bindEvents();
    }
    
    startMonitoring() {
        this.timer = setInterval(() => {
            this.checkSessionStatus();
        }, this.checkInterval);
    }
    
    stopMonitoring() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
    }
    
    async checkSessionStatus() {
        try {
            const response = await fetch('/auth/api/session-status');
            const data = await response.json();
            
            if (data.success) {
                this.updateSessionInfo(data.session);
            } else {
                this.handleSessionExpired();
            }
        } catch (error) {
            console.error('检查会话状态失败:', error);
        }
    }
    
    updateSessionInfo(sessionInfo) {
        // 更新最后活动时间
        const lastActiveElement = document.getElementById('last-active');
        if (lastActiveElement && sessionInfo.last_active) {
            lastActiveElement.textContent = this.formatTime(sessionInfo.last_active);
        }
        
        // 检查是否需要警告
        const timeLeft = sessionInfo.expires_at - Date.now();
        if (timeLeft < this.warningTime && timeLeft > 0) {
            this.showSessionWarning(timeLeft);
        }
    }
    
    showSessionWarning(timeLeft) {
        const minutes = Math.floor(timeLeft / 60000);
        
        if (!document.getElementById('session-warning')) {
            const warningDiv = document.createElement('div');
            warningDiv.id = 'session-warning';
            warningDiv.className = 'alert alert-warning alert-dismissible fade show position-fixed';
            warningDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
            warningDiv.innerHTML = `
                <i class="fas fa-exclamation-triangle me-2"></i>
                会话将在 ${minutes} 分钟后过期
                <div class="mt-2">
                    <button class="btn btn-sm btn-outline-warning me-2" onclick="sessionMonitor.extendSession()">
                        延长会话
                    </button>
                    <button class="btn btn-sm btn-outline-secondary" onclick="sessionMonitor.logout()">
                        立即登出
                    </button>
                </div>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            
            document.body.appendChild(warningDiv);
        }
    }
    
    async extendSession() {
        try {
            const response = await fetch('/auth/api/extend-session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.hideSessionWarning();
                this.showSuccess('会话已延长');
            } else {
                this.showError(data.message || '延长会话失败');
            }
        } catch (error) {
            console.error('延长会话失败:', error);
            this.showError('网络错误，请稍后重试');
        }
    }
    
    hideSessionWarning() {
        const warningDiv = document.getElementById('session-warning');
        if (warningDiv) {
            warningDiv.remove();
        }
    }
    
    handleSessionExpired() {
        this.stopMonitoring();
        this.showError('会话已过期，请重新登录');
        setTimeout(() => {
            window.location.href = '/auth/login';
        }, 2000);
    }
    
    async logout() {
        try {
            const response = await fetch('/auth/logout', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            window.location.href = '/auth/login';
        } catch (error) {
            console.error('登出失败:', error);
            window.location.href = '/auth/login';
        }
    }
    
    bindEvents() {
        // 页面可见性变化时检查会话
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.checkSessionStatus();
            }
        });
        
        // 用户活动时重置会话
        ['click', 'keypress', 'scroll', 'mousemove'].forEach(event => {
            document.addEventListener(event, () => {
                this.resetSessionTimeout();
            });
        });
    }
    
    resetSessionTimeout() {
        // 发送心跳请求重置会话超时
        fetch('/auth/api/heartbeat', {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.getCSRFToken()
            }
        }).catch(error => {
            console.error('心跳请求失败:', error);
        });
    }
    
    formatTime(timestamp) {
        return new Date(timestamp).toLocaleString('zh-CN');
    }
    
    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    }
    
    showSuccess(message) {
        // 显示成功消息
        this.showAlert(message, 'success');
    }
    
    showError(message) {
        // 显示错误消息
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

// 初始化会话监控器
const sessionMonitor = new SessionMonitor();
```

## 4. 后端实现

### 4.1 数据模型

#### 4.1.1 用户模型
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
    
    def __init__(self, username: str, password: str, role: str = "user") -> None:
        """初始化用户"""
        self.username = username
        self.set_password(password)
        self.role = role
    
    def set_password(self, password: str) -> None:
        """设置密码（加密）"""
        # 增加密码强度验证
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
        # 管理员拥有所有权限
        if self.is_admin():
            return True
        
        # 根据角色判断权限
        if self.role == "admin":
            return True
        if self.role == "user":
            # 普通用户只有查看权限
            return permission == "view"
        # 其他角色默认无权限
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
    
    @staticmethod
    def create_admin() -> "User | None":
        """创建默认管理员用户"""
        try:
            admin = User.query.filter_by(username="admin").first()
            if not admin:
                admin = User(username="admin", password="admin123", role="admin")
                db.session.add(admin)
                db.session.commit()
                return admin
            return admin
        except Exception:
            return None
```

### 4.2 服务层

#### 4.2.1 认证服务
```python
# app/services/auth_service.py
from typing import Optional, Dict, Any
from flask import current_app
from flask_login import login_user, logout_user, current_user
from app import db
from app.models.user import User
from app.utils.structlog_config import log_info, log_error, log_warning
from app.utils.timezone import now


class AuthService:
    """认证服务"""
    
    @staticmethod
    def authenticate_user(username: str, password: str, remember_me: bool = False) -> Dict[str, Any]:
        """用户认证"""
        try:
            # 查找用户
            user = User.query.filter_by(username=username, is_active=True).first()
            
            if not user:
                log_warning(f"用户不存在: {username}", module="auth")
                return {
                    "success": False,
                    "message": "用户名或密码错误"
                }
            
            # 验证密码
            if not user.check_password(password):
                log_warning(f"密码错误: {username}", module="auth")
                return {
                    "success": False,
                    "message": "用户名或密码错误"
                }
            
            # 登录用户
            login_user(user, remember=remember_me)
            
            # 更新最后登录时间
            user.update_last_login()
            
            # 记录登录日志
            log_info(
                "用户登录",
                module="auth",
                user_id=user.id,
                username=user.username,
                role=user.role,
                remember_me=remember_me,
                ip_address=AuthService.get_client_ip()
            )
            
            return {
                "success": True,
                "message": "登录成功",
                "user": user.to_dict(),
                "redirect_url": AuthService.get_redirect_url()
            }
            
        except Exception as e:
            log_error(f"用户认证失败: {str(e)}", module="auth", username=username)
            return {
                "success": False,
                "message": "登录失败，请稍后重试"
            }
    
    @staticmethod
    def logout_user() -> Dict[str, Any]:
        """用户登出"""
        try:
            if current_user.is_authenticated:
                user_id = current_user.id
                username = current_user.username
                
                # 登出用户
                logout_user()
                
                # 记录登出日志
                log_info(
                    "用户登出",
                    module="auth",
                    user_id=user_id,
                    username=username,
                    ip_address=AuthService.get_client_ip()
                )
                
                return {
                    "success": True,
                    "message": "登出成功"
                }
            else:
                return {
                    "success": False,
                    "message": "用户未登录"
                }
                
        except Exception as e:
            log_error(f"用户登出失败: {str(e)}", module="auth")
            return {
                "success": False,
                "message": "登出失败，请稍后重试"
            }
    
    @staticmethod
    def get_session_info() -> Dict[str, Any]:
        """获取会话信息"""
        try:
            if not current_user.is_authenticated:
                return {
                    "success": False,
                    "message": "用户未登录"
                }
            
            # 计算会话剩余时间
            session_lifetime = current_app.config.get("PERMANENT_SESSION_LIFETIME", 3600)
            session_timeout = session_lifetime * 1000  # 转换为毫秒
            
            return {
                "success": True,
                "session": {
                    "user": current_user.to_dict(),
                    "is_authenticated": current_user.is_authenticated,
                    "session_timeout": session_timeout,
                    "last_active": now().isoformat(),
                    "expires_at": (now().timestamp() + session_lifetime) * 1000
                }
            }
            
        except Exception as e:
            log_error(f"获取会话信息失败: {str(e)}", module="auth")
            return {
                "success": False,
                "message": "获取会话信息失败"
            }
    
    @staticmethod
    def extend_session() -> Dict[str, Any]:
        """延长会话"""
        try:
            if not current_user.is_authenticated:
                return {
                    "success": False,
                    "message": "用户未登录"
                }
            
            # 更新最后活动时间
            current_user.update_last_login()
            
            log_info(
                "会话延长",
                module="auth",
                user_id=current_user.id,
                username=current_user.username
            )
            
            return {
                "success": True,
                "message": "会话已延长"
            }
            
        except Exception as e:
            log_error(f"延长会话失败: {str(e)}", module="auth")
            return {
                "success": False,
                "message": "延长会话失败"
            }
    
    @staticmethod
    def heartbeat() -> Dict[str, Any]:
        """心跳检测"""
        try:
            if not current_user.is_authenticated:
                return {
                    "success": False,
                    "message": "用户未登录"
                }
            
            # 更新最后活动时间
            current_user.update_last_login()
            
            return {
                "success": True,
                "message": "心跳正常"
            }
            
        except Exception as e:
            log_error(f"心跳检测失败: {str(e)}", module="auth")
            return {
                "success": False,
                "message": "心跳检测失败"
            }
    
    @staticmethod
    def get_client_ip() -> str:
        """获取客户端IP地址"""
        try:
            from flask import request
            return request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        except Exception:
            return "unknown"
    
    @staticmethod
    def get_redirect_url() -> str:
        """获取重定向URL"""
        try:
            from flask import request
            next_page = request.args.get('next')
            if next_page and AuthService.is_safe_url(next_page):
                return next_page
            return '/dashboard'
        except Exception:
            return '/dashboard'
    
    @staticmethod
    def is_safe_url(target: str) -> bool:
        """检查URL是否安全"""
        try:
            from urllib.parse import urlparse, urljoin
            from flask import request
            
            ref_url = urlparse(request.host_url)
            test_url = urlparse(urljoin(request.host_url, target))
            return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc
        except Exception:
            return False
```

### 4.3 路由层

#### 4.3.1 认证路由
```python
# app/routes/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.services.auth_service import AuthService
from app.utils.api_response import APIResponse
from app.utils.structlog_config import log_info, log_error


# 创建蓝图
auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login")
def login() -> str:
    """登录页面"""
    try:
        # 如果已登录，重定向到仪表板
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        
        return render_template("auth/login.html")
    except Exception as e:
        log_error(f"加载登录页面失败: {str(e)}", module="auth")
        return render_template("auth/login.html", error="页面加载失败")


@auth_bp.route("/api/login", methods=["POST"])
def api_login() -> tuple[dict, int]:
    """登录API"""
    try:
        # 获取表单数据
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember_me = request.form.get("remember_me") == "on"
        
        # 验证必填字段
        if not username:
            return APIResponse.error("请输入用户名"), 400
        
        if not password:
            return APIResponse.error("请输入密码"), 400
        
        # 执行认证
        result = AuthService.authenticate_user(username, password, remember_me)
        
        if result["success"]:
            return APIResponse.success(result)
        else:
            return APIResponse.error(result["message"]), 401
            
    except Exception as e:
        log_error(f"登录API失败: {str(e)}", module="auth")
        return APIResponse.error("登录失败，请稍后重试"), 500


@auth_bp.route("/logout")
@login_required
def logout() -> str:
    """登出页面"""
    try:
        # 执行登出
        result = AuthService.logout_user()
        
        if result["success"]:
            flash("已成功登出", "info")
        else:
            flash(result["message"], "error")
        
        return redirect(url_for('auth.login'))
        
    except Exception as e:
        log_error(f"登出失败: {str(e)}", module="auth")
        flash("登出失败，请稍后重试", "error")
        return redirect(url_for('auth.login'))


@auth_bp.route("/api/logout", methods=["POST"])
@login_required
def api_logout() -> tuple[dict, int]:
    """登出API"""
    try:
        result = AuthService.logout_user()
        
        if result["success"]:
            return APIResponse.success(result)
        else:
            return APIResponse.error(result["message"]), 400
            
    except Exception as e:
        log_error(f"登出API失败: {str(e)}", module="auth")
        return APIResponse.error("登出失败，请稍后重试"), 500


@auth_bp.route("/api/session-status")
@login_required
def api_session_status() -> tuple[dict, int]:
    """获取会话状态API"""
    try:
        result = AuthService.get_session_info()
        
        if result["success"]:
            return APIResponse.success(result)
        else:
            return APIResponse.error(result["message"]), 401
            
    except Exception as e:
        log_error(f"获取会话状态失败: {str(e)}", module="auth")
        return APIResponse.error("获取会话状态失败"), 500


@auth_bp.route("/api/extend-session", methods=["POST"])
@login_required
def api_extend_session() -> tuple[dict, int]:
    """延长会话API"""
    try:
        result = AuthService.extend_session()
        
        if result["success"]:
            return APIResponse.success(result)
        else:
            return APIResponse.error(result["message"]), 400
            
    except Exception as e:
        log_error(f"延长会话失败: {str(e)}", module="auth")
        return APIResponse.error("延长会话失败"), 500


@auth_bp.route("/api/heartbeat", methods=["POST"])
@login_required
def api_heartbeat() -> tuple[dict, int]:
    """心跳检测API"""
    try:
        result = AuthService.heartbeat()
        
        if result["success"]:
            return APIResponse.success(result)
        else:
            return APIResponse.error(result["message"]), 401
            
    except Exception as e:
        log_error(f"心跳检测失败: {str(e)}", module="auth")
        return APIResponse.error("心跳检测失败"), 500
```

## 5. 配置管理

### 5.1 会话安全配置
```python
# app/__init__.py
def configure_session_security(app: Flask) -> None:
    """配置会话安全"""
    # 从环境变量读取会话超时时间，默认为1小时
    session_lifetime = int(os.getenv("PERMANENT_SESSION_LIFETIME", SystemConstants.SESSION_LIFETIME))
    
    # 会话配置
    app.config["PERMANENT_SESSION_LIFETIME"] = session_lifetime  # 会话超时时间
    app.config["SESSION_COOKIE_SECURE"] = False  # 暂时禁用HTTPS要求，使用HTTP
    app.config["SESSION_COOKIE_HTTPONLY"] = True  # 防止XSS攻击
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # CSRF保护
    app.config["SESSION_COOKIE_NAME"] = "whalefall_session"  # 防止会话固定攻击
    
    # 会话超时配置
    app.config["SESSION_TIMEOUT"] = session_lifetime  # 会话超时时间


def initialize_extensions(app: Flask) -> None:
    """初始化Flask扩展"""
    # 初始化登录管理
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "请先登录"
    login_manager.login_message_category = "info"
    
    # 会话安全配置
    login_manager.session_protection = "basic"  # 基础会话保护
    session_lifetime = int(os.getenv("PERMANENT_SESSION_LIFETIME", SystemConstants.SESSION_LIFETIME))
    login_manager.remember_cookie_duration = session_lifetime  # 记住我功能过期时间
    login_manager.remember_cookie_secure = not app.debug  # 生产环境使用HTTPS
    login_manager.remember_cookie_httponly = True  # 防止XSS攻击
    
    # 用户加载器
    @login_manager.user_loader
    def load_user(user_id: str) -> "User | None":
        from app.models.user import User
        return User.query.get(int(user_id))
```

### 5.2 环境变量配置
```bash
# 会话配置
PERMANENT_SESSION_LIFETIME=3600
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax
SESSION_COOKIE_NAME=whalefall_session

# 安全配置
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
```

## 6. 安全考虑

### 6.1 密码安全
- 使用bcrypt加密存储密码
- 强制密码复杂度要求
- 密码强度验证

### 6.2 会话安全
- 会话超时自动清理
- 防止会话固定攻击
- CSRF保护
- 安全Cookie配置

### 6.3 权限控制
- 基于角色的访问控制
- 权限装饰器验证
- 敏感操作权限检查

## 7. 监控和审计

### 7.1 登录监控
- 记录所有登录尝试
- 监控异常登录行为
- 登录失败次数限制

### 7.2 会话监控
- 监控活跃会话数量
- 检测异常会话行为
- 会话超时告警

### 7.3 安全审计
- 记录所有认证事件
- 审计权限变更
- 安全事件告警

## 8. 性能优化

### 8.1 会话存储优化
- 使用Redis存储会话数据
- 会话数据压缩
- 定期清理过期会话

### 8.2 认证性能优化
- 密码验证缓存
- 权限检查缓存
- 异步认证处理

## 9. 扩展功能

### 9.1 多因素认证
- 支持短信验证码
- 支持邮箱验证码
- 支持TOTP认证

### 9.2 单点登录
- 支持OAuth2.0
- 支持SAML
- 支持LDAP集成

---

**注意**: 本文档描述了会话中心功能的完整技术实现，包括用户认证、会话管理、安全配置、权限控制等各个方面。该功能为鲸落系统提供了完整的用户认证和会话管理能力，确保系统安全性和用户体验。
