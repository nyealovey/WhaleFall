# 凭据管理功能技术文档

## 功能概述

凭据管理功能是鲸落系统的安全基础功能，负责管理数据库连接凭据的创建、编辑、删除、状态管理等操作。支持多种凭据类型（数据库、API、SSH等）和多种数据库类型（MySQL、PostgreSQL、SQL Server、Oracle），提供安全的密码加密存储和访问控制。

## 技术架构

### 1. 前端架构

#### 1.1 HTML模板文件
- **主模板**: `app/templates/credentials/list.html`
  - 凭据列表页面主模板
  - 包含搜索筛选、状态切换、删除确认等功能
  - 继承自 `base.html` 基础模板

- **创建模板**: `app/templates/credentials/create.html`
  - 凭据创建表单页面
  - 包含凭据类型选择、密码输入、数据库类型配置等

- **编辑模板**: `app/templates/credentials/edit.html`
  - 凭据编辑表单页面
  - 预填充现有凭据数据，支持密码修改

- **详情模板**: `app/templates/credentials/detail.html`
  - 凭据详情展示页面
  - 包含凭据信息、关联实例、使用统计等

#### 1.2 JavaScript文件
- **主页面脚本**: `app/static/js/pages/credentials/list.js`
  - 凭据列表页面交互逻辑
  - 状态切换、删除确认、搜索筛选等功能
  - 实时搜索和表格排序

- **创建页面脚本**: `app/static/js/pages/credentials/create.js`
  - 凭据创建表单验证和提交
  - 凭据类型切换逻辑
  - 密码强度验证

- **编辑页面脚本**: `app/static/js/pages/credentials/edit.js`
  - 凭据编辑表单处理
  - 数据预填充和验证
  - 密码修改确认

#### 1.3 CSS样式文件
- **主样式**: `app/static/css/pages/credentials/list.css`
  - 凭据列表页面样式
  - 卡片布局、状态指示器、操作按钮等
  - 响应式设计和动画效果

- **创建编辑样式**: `app/static/css/pages/credentials/create.css`
  - 凭据创建和编辑页面样式
  - 表单样式、密码输入框、验证提示等

### 2. 后端架构

#### 2.1 数据模型
- **主模型**: `app/models/credential.py`
  - `Credential` 类：凭据模型
  - 包含凭据基本信息、加密密码、关联实例等
  - 支持软删除、密码加密、类型分类

#### 2.2 路由控制器
- **主路由**: `app/routes/credentials.py`
  - 凭据管理相关API接口
  - 包含CRUD操作、状态切换、批量操作等

#### 2.3 服务层
- **密码管理服务**: `app/utils/password_manager.py`
  - 密码加密和解密逻辑
  - 支持多种加密算法
  - 密码强度验证

- **安全工具**: `app/utils/security.py`
  - 数据清理和验证
  - 凭据类型验证
  - 安全防护措施

#### 2.4 工具类
- **数据验证器**: `app/utils/data_validator.py`
  - 表单数据验证
  - 凭据参数校验
  - 密码格式验证

## 核心功能实现

### 1. 凭据CRUD操作

#### 1.1 创建凭据
**前端流程**:
```javascript
// 表单提交处理
function submitCredentialForm() {
    const formData = new FormData(document.getElementById('credentialForm'));
    
    // 密码强度验证
    const password = formData.get('password');
    if (!validatePasswordStrength(password)) {
        showAlert('warning', '密码强度不足，请包含大小写字母、数字和特殊字符');
        return;
    }
    
    fetch('/credentials/create', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken()
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            showAlert('success', data.message);
            window.location.href = '/credentials/';
        } else if (data.error) {
            showAlert('danger', data.error);
        }
    });
}

// 密码强度验证
function validatePasswordStrength(password) {
    const minLength = 8;
    const hasUpperCase = /[A-Z]/.test(password);
    const hasLowerCase = /[a-z]/.test(password);
    const hasNumbers = /\d/.test(password);
    const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);
    
    return password.length >= minLength && 
           hasUpperCase && 
           hasLowerCase && 
           hasNumbers && 
           hasSpecialChar;
}
```

**后端处理**:
```python
@credentials_bp.route("/create", methods=["GET", "POST"])
@login_required
@create_required
def create() -> str | Response:
    """创建凭据"""
    if request.method == "POST":
        # 数据验证
        validation_result = validate_credential_data(request.form)
        
        if not validation_result["valid"]:
            flash(validation_result["error"], "error")
            return render_template("credentials/create.html", form_data=request.form)
        
        # 创建凭据
        credential = Credential(
            name=request.form["name"],
            credential_type=request.form["credential_type"],
            username=request.form["username"],
            password=request.form["password"],
            db_type=request.form.get("db_type"),
            description=request.form.get("description"),
        )
        
        db.session.add(credential)
        db.session.commit()
        
        log_info("凭据创建成功", credential_id=credential.id, name=credential.name)
        flash("凭据创建成功", "success")
        return redirect(url_for("credentials.detail", credential_id=credential.id))
    
    return render_template("credentials/create.html")
```

#### 1.2 凭据列表查询
**前端搜索筛选**:
```javascript
// 搜索和筛选功能
function performSearch(searchTerm, credentialType, dbType, status) {
    const params = new URLSearchParams();
    
    if (searchTerm && searchTerm.trim()) {
        params.append('search', searchTerm.trim());
    }
    
    if (credentialType) {
        params.append('credential_type', credentialType);
    }
    
    if (dbType) {
        params.append('db_type', dbType);
    }
    
    if (status) {
        params.append('status', status);
    }
    
    const queryString = params.toString();
    const url = queryString ? `${window.location.pathname}?${queryString}` : window.location.pathname;
    
    window.location.href = url;
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
```

**后端查询逻辑**:
```python
@credentials_bp.route("/")
@login_required
@view_required
def index() -> str:
    """凭据管理首页"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    search = request.args.get("search", "", type=str)
    credential_type = request.args.get("credential_type", "", type=str)
    db_type = request.args.get("db_type", "", type=str)
    status = request.args.get("status", "", type=str)
    tags_str = request.args.get("tags", "", type=str)
    tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]

    # 构建查询，包含实例数量统计
    query = db.session.query(Credential, db.func.count(Instance.id).label("instance_count")).outerjoin(
        Instance, Credential.id == Instance.credential_id
    )

    if search:
        query = query.filter(
            db.or_(
                Credential.name.contains(search),
                Credential.username.contains(search),
                Credential.description.contains(search),
            )
        )

    if credential_type:
        query = query.filter(Credential.credential_type == credential_type)
    
    if db_type:
        query = query.filter(Credential.db_type == db_type)
    
    if status:
        if status == 'active':
            query = query.filter(Credential.is_active == True)
        elif status == 'inactive':
            query = query.filter(Credential.is_active == False)

    # 分页查询
    credentials = query.group_by(Credential.id).order_by(Credential.id).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template("credentials/list.html", credentials=credentials)
```

### 2. 状态管理功能

#### 2.1 前端状态切换
```javascript
// 切换凭据状态
function toggleCredentialStatus(credentialId, isActive, button) {
    const originalHtml = button.innerHTML;
    
    showLoadingState(button, '处理中...');
    button.disabled = true;
    
    const csrfToken = getCSRFToken();
    
    fetch(`/credentials/${credentialId}/toggle`, {
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
```

#### 2.2 后端状态切换
```python
@credentials_bp.route("/<int:credential_id>/toggle", methods=["POST"])
@login_required
@update_required
def toggle_credential_status(credential_id: int) -> Response:
    """切换凭据状态"""
    credential = Credential.query.get_or_404(credential_id)
    
    try:
        data = request.get_json()
        is_active = data.get('is_active', not credential.is_active)
        
        credential.is_active = is_active
        db.session.commit()
        
        status_text = "激活" if is_active else "停用"
        log_info(f"凭据{status_text}成功", credential_id=credential_id, name=credential.name)
        
        return jsonify({
            "success": True,
            "message": f"凭据已{status_text}",
            "is_active": is_active
        })
        
    except Exception as e:
        db.session.rollback()
        log_error(f"切换凭据状态失败: {str(e)}", credential_id=credential_id)
        return jsonify({
            "success": False,
            "error": f"操作失败: {str(e)}"
        }), 500
```

### 3. 删除确认功能

#### 3.1 前端删除确认
```javascript
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

// 处理删除确认
function handleDeleteConfirmation() {
    if (deleteCredentialId) {
        const csrfToken = getCSRFToken();
        
        showLoadingState('confirmDelete', '删除中...');
        
        fetch(`/credentials/${deleteCredentialId}/delete`, {
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
```

#### 3.2 后端删除处理
```python
@credentials_bp.route("/<int:credential_id>/delete", methods=["POST"])
@login_required
@delete_required
def delete_credential(credential_id: int) -> Response:
    """删除凭据"""
    credential = Credential.query.get_or_404(credential_id)
    
    try:
        # 检查是否有关联的实例
        associated_instances = Instance.query.filter_by(credential_id=credential_id).count()
        if associated_instances > 0:
            return jsonify({
                "success": False,
                "error": f"无法删除凭据，还有 {associated_instances} 个实例正在使用此凭据"
            }), 400
        
        # 软删除凭据
        credential.soft_delete()
        
        log_info("凭据删除成功", credential_id=credential_id, name=credential.name)
        return jsonify({
            "success": True,
            "message": "凭据删除成功"
        })
        
    except Exception as e:
        db.session.rollback()
        log_error(f"删除凭据失败: {str(e)}", credential_id=credential_id)
        return jsonify({
            "success": False,
            "error": f"删除失败: {str(e)}"
        }), 500
```

### 4. 密码加密管理

#### 4.1 密码加密存储
```python
# app/models/credential.py
def set_password(self, password: str) -> None:
    """
    设置密码（加密）
    
    Args:
        password: 原始密码
    """
    # 使用新的加密方式存储密码
    self.password = get_password_manager().encrypt_password(password)

def get_plain_password(self) -> str:
    """
    获取原始密码（用于数据库连接）
    
    Returns:
        str: 原始密码
    """
    # 如果密码是bcrypt哈希，说明是旧格式，需要特殊处理
    if self.password.startswith("$2b$"):
        # 对于旧格式，从环境变量获取密码，避免硬编码
        import os
        default_password = os.getenv(f"DEFAULT_{self.db_type.upper()}_PASSWORD")
        if default_password:
            return default_password
        return ""

    # 如果是我们的加密格式，尝试解密
    if get_password_manager().is_encrypted(self.password):
        return get_password_manager().decrypt_password(self.password)

    # 如果都不是，可能是明文密码（不安全）
    return self.password
```

#### 4.2 密码管理器
```python
# app/utils/password_manager.py
class PasswordManager:
    """密码管理器"""
    
    def __init__(self):
        self.encryption_key = os.getenv('PASSWORD_ENCRYPTION_KEY')
        if not self.encryption_key:
            raise ValueError("PASSWORD_ENCRYPTION_KEY 环境变量未设置")
    
    def encrypt_password(self, password: str) -> str:
        """加密密码"""
        try:
            # 使用Fernet对称加密
            f = Fernet(self.encryption_key.encode())
            encrypted_password = f.encrypt(password.encode())
            return encrypted_password.decode()
        except Exception as e:
            raise ValueError(f"密码加密失败: {str(e)}")
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """解密密码"""
        try:
            f = Fernet(self.encryption_key.encode())
            decrypted_password = f.decrypt(encrypted_password.encode())
            return decrypted_password.decode()
        except Exception as e:
            raise ValueError(f"密码解密失败: {str(e)}")
    
    def is_encrypted(self, password: str) -> bool:
        """检查密码是否已加密"""
        try:
            f = Fernet(self.encryption_key.encode())
            f.decrypt(password.encode())
            return True
        except:
            return False
```

### 5. 批量操作功能

#### 5.1 前端批量操作
```javascript
// 批量操作
function performBatchAction(action, credentialIds) {
    if (!credentialIds || credentialIds.length === 0) {
        showAlert('warning', '请选择要操作的凭据');
        return;
    }
    
    const csrfToken = getCSRFToken();
    
    fetch('/credentials/batch-action', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            action: action,
            credential_ids: credentialIds
        })
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
        console.error('批量操作失败:', error);
        showAlert('danger', '批量操作失败，请稍后重试');
    });
}
```

#### 5.2 后端批量操作
```python
@credentials_bp.route("/batch-action", methods=["POST"])
@login_required
@update_required
def batch_action() -> Response:
    """批量操作凭据"""
    try:
        data = request.get_json()
        action = data.get('action')
        credential_ids = data.get('credential_ids', [])
        
        if not credential_ids:
            return jsonify({
                "success": False,
                "error": "请选择要操作的凭据"
            }), 400
        
        credentials = Credential.query.filter(Credential.id.in_(credential_ids)).all()
        
        if action == 'activate':
            for credential in credentials:
                credential.is_active = True
            message = f"已激活 {len(credentials)} 个凭据"
            
        elif action == 'deactivate':
            for credential in credentials:
                credential.is_active = False
            message = f"已停用 {len(credentials)} 个凭据"
            
        elif action == 'delete':
            # 检查是否有关联实例
            for credential in credentials:
                associated_instances = Instance.query.filter_by(credential_id=credential.id).count()
                if associated_instances > 0:
                    return jsonify({
                        "success": False,
                        "error": f"凭据 {credential.name} 还有关联实例，无法删除"
                    }), 400
                credential.soft_delete()
            message = f"已删除 {len(credentials)} 个凭据"
            
        else:
            return jsonify({
                "success": False,
                "error": "不支持的操作类型"
            }), 400
        
        db.session.commit()
        
        log_info(f"批量操作成功: {action}", credential_count=len(credentials))
        return jsonify({
            "success": True,
            "message": message
        })
        
    except Exception as e:
        db.session.rollback()
        log_error(f"批量操作失败: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"批量操作失败: {str(e)}"
        }), 500
```

## 数据库设计

### 1. 凭据表结构
```sql
CREATE TABLE credentials (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    credential_type VARCHAR(50) NOT NULL,
    db_type VARCHAR(50),
    username VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    description TEXT,
    instance_ids JSON,
    category_id INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);
```

### 2. 索引设计
```sql
-- 凭据名称索引
CREATE INDEX idx_credentials_name ON credentials(name);

-- 凭据类型索引
CREATE INDEX idx_credentials_type ON credentials(credential_type);

-- 数据库类型索引
CREATE INDEX idx_credentials_db_type ON credentials(db_type);

-- 活跃状态索引
CREATE INDEX idx_credentials_active ON credentials(is_active);

-- 软删除索引
CREATE INDEX idx_credentials_deleted ON credentials(deleted_at);
```

## API接口文档

### 1. 凭据管理接口

#### 1.1 获取凭据列表
- **URL**: `GET /credentials/`
- **参数**:
  - `page`: 页码 (默认: 1)
  - `per_page`: 每页数量 (默认: 10)
  - `search`: 搜索关键词
  - `credential_type`: 凭据类型筛选
  - `db_type`: 数据库类型筛选
  - `status`: 状态筛选 (active/inactive)

#### 1.2 创建凭据
- **URL**: `POST /credentials/create`
- **参数**:
  - `name`: 凭据名称 (必填)
  - `credential_type`: 凭据类型 (必填)
  - `username`: 用户名 (必填)
  - `password`: 密码 (必填)
  - `db_type`: 数据库类型
  - `description`: 描述

#### 1.3 切换状态
- **URL**: `POST /credentials/{id}/toggle`
- **参数**:
  - `is_active`: 是否激活 (boolean)

#### 1.4 删除凭据
- **URL**: `POST /credentials/{id}/delete`
- **返回**:
  ```json
  {
    "success": true,
    "message": "凭据删除成功"
  }
  ```

#### 1.5 批量操作
- **URL**: `POST /credentials/batch-action`
- **参数**:
  - `action`: 操作类型 (activate/deactivate/delete)
  - `credential_ids`: 凭据ID列表

## 安全考虑

### 1. 密码安全
- 使用Fernet对称加密算法
- 密码强度验证（大小写字母、数字、特殊字符）
- 密码掩码显示
- 加密密钥环境变量管理

### 2. 访问控制
- 基于角色的权限控制
- 操作权限验证装饰器
- 敏感操作审计日志

### 3. 数据安全
- 软删除保护数据
- 关联检查防止误删
- 输入数据验证和清理

## 错误处理

### 1. 前端错误处理
```javascript
// 统一错误处理函数
function handleError(error, context) {
    console.error(`${context} 错误:`, error);
    
    // 显示用户友好的错误信息
    showAlert('danger', `${context}失败，请稍后重试`);
    
    // 记录错误日志
    logErrorWithContext(error, context, {
        operation: context,
        result: 'exception'
    });
}

// 网络请求错误处理
function handleFetchError(response, context) {
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    return response.json();
}
```

### 2. 后端错误处理
```python
# 统一异常处理装饰器
def handle_credential_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except CredentialNotFoundError as e:
            return jsonify({"success": False, "error": "凭据不存在"}), 404
        except PasswordEncryptionError as e:
            return jsonify({"success": False, "error": "密码加密失败"}), 500
        except ValidationError as e:
            return jsonify({"success": False, "error": f"数据验证失败: {str(e)}"}), 400
        except Exception as e:
            logger.error(f"凭据操作异常: {str(e)}")
            return jsonify({"success": False, "error": "服务器内部错误"}), 500
    return decorated_function
```

## 性能优化

### 1. 数据库查询优化
- 使用索引优化查询性能
- 分页查询避免大量数据加载
- 预加载关联数据减少N+1查询

### 2. 前端性能优化
- 实时搜索防抖处理
- 表格排序客户端实现
- 懒加载密码显示

### 3. 密码处理优化
- 密码加密缓存
- 批量操作事务处理
- 异步密码验证

## 测试策略

### 1. 单元测试
- 模型方法测试
- 密码加密解密测试
- 服务类功能测试

### 2. 集成测试
- API接口测试
- 数据库操作测试
- 前后端交互测试

### 3. 安全测试
- 密码强度验证测试
- 权限控制测试
- 加密算法测试

## 部署配置

### 1. 环境变量
```bash
# 密码加密密钥
PASSWORD_ENCRYPTION_KEY=your-encryption-key-here

# 默认密码（用于旧格式凭据）
DEFAULT_MYSQL_PASSWORD=default-mysql-password
DEFAULT_POSTGRESQL_PASSWORD=default-postgresql-password
DEFAULT_SQLSERVER_PASSWORD=default-sqlserver-password
DEFAULT_ORACLE_PASSWORD=default-oracle-password

# 安全配置
SECRET_KEY=your-secret-key
CSRF_SECRET_KEY=your-csrf-secret-key
```

### 2. 依赖包
```txt
Flask==3.0.3
SQLAlchemy==1.4.54
cryptography==41.0.7
bcrypt==4.0.1
```

## 监控和日志

### 1. 操作日志
- 凭据创建、编辑、删除操作
- 状态切换操作记录
- 密码修改操作记录

### 2. 安全监控
- 密码强度统计
- 加密失败监控
- 异常访问记录

### 3. 性能监控
- 密码加密解密性能
- 数据库查询性能
- 页面加载时间

## 维护指南

### 1. 日常维护
- 定期清理软删除的凭据
- 检查密码加密状态
- 监控凭据使用情况

### 2. 故障排查
- 查看错误日志定位问题
- 检查密码加密配置
- 验证权限设置

### 3. 安全维护
- 定期轮换加密密钥
- 更新密码强度要求
- 审计凭据访问记录

---

**文档版本**: 1.0  
**最后更新**: 2025-01-28  
**维护人员**: 开发团队
