# 鲸落标签系统优化设计方案

## 📋 需求概述

### 当前问题
- 标签分类混乱，缺乏统一的管理体系
- 人员信息无法通过标签进行管理
- 手动和自动标签混合管理，缺乏区分

### 优化目标
1. **资源类标签**: 将现有标签重新整理，取消公司类型和部门标签，支持手动管理
2. **身份类标签**: 新增身份类标签，从飞书自动同步人员信息
3. **飞书集成**: 支持飞书API同步，可按部门筛选同步范围
4. **三级部门**: 支持公司-部门-科室的三级部门结构

## 🏗️ 系统架构设计

### 标签分类体系

```
标签系统
├── 资源类标签 (Resource Tags) - 手动管理
│   ├── 地区标签 (location)
│   ├── 环境标签 (environment)
│   ├── 项目标签 (project)
│   ├── 虚拟化类型 (virtualization)
│   ├── 部署方式 (deployment)
│   ├── 架构类型 (architecture)
│   └── 其他标签 (other)
└── 身份类标签 (Identity Tags) - 飞书自动同步
    └── 用户标签 (user) - 个人用户
```

### 飞书同步机制

```
飞书API同步
├── 用户信息同步
│   ├── 基本信息 (姓名、工号、邮箱)
│   ├── 部门信息 (三级部门结构)
│   └── 状态信息 (在职状态)
└── 同步范围控制
    ├── 按部门筛选
    ├── 按状态筛选
    └── 定时同步 (每日)
```

### 标签属性设计

#### 资源类标签属性
- **输入方式**: 手动创建和管理
- **管理权限**: 管理员和DBA可管理
- **使用场景**: 资源分类、筛选、统计
- **数据来源**: 用户手动输入
- **分类范围**: 地区、环境、项目、虚拟化、部署、架构、其他

#### 身份类标签属性
- **输入方式**: 飞书API自动同步
- **管理权限**: 系统自动管理，不可手动修改
- **使用场景**: 权限控制、责任归属、审计追踪
- **数据来源**: 飞书开放平台API
- **分类范围**: 用户
- **同步频率**: 每日定时同步
- **筛选范围**: 可按部门层级筛选同步

## 🗄️ 数据库设计

### 1. 标签表结构优化

```sql
-- 标签表 (优化后)
CREATE TABLE IF NOT EXISTS tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    category_type VARCHAR(20) NOT NULL,  -- 'resource' 或 'identity'
    category VARCHAR(50) NOT NULL,       -- 具体分类
    color VARCHAR(20) DEFAULT 'primary' NOT NULL,
    description TEXT,
    sort_order INTEGER DEFAULT 0 NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_auto_sync BOOLEAN DEFAULT FALSE NOT NULL,  -- 是否自动同步
    sync_source VARCHAR(50),                      -- 同步来源 (feishu)
    sync_id VARCHAR(100),                         -- 飞书用户ID (open_id)
    department_path VARCHAR(500),                 -- 部门路径 (公司-部门-科室)
    user_status VARCHAR(20) DEFAULT 'active',     -- 用户状态 (active/inactive)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    synced_at TIMESTAMP WITH TIME ZONE            -- 最后同步时间
);

-- 新增索引
CREATE INDEX IF NOT EXISTS ix_tags_category_type ON tags(category_type);
CREATE INDEX IF NOT EXISTS ix_tags_is_auto_sync ON tags(is_auto_sync);
CREATE INDEX IF NOT EXISTS ix_tags_sync_source ON tags(sync_source);
CREATE INDEX IF NOT EXISTS ix_tags_department_path ON tags(department_path);
```

### 2. 飞书同步配置表

```sql
-- 飞书同步配置表
CREATE TABLE IF NOT EXISTS feishu_sync_config (
    id SERIAL PRIMARY KEY,
    app_id VARCHAR(100) NOT NULL,             -- 飞书应用ID
    app_secret VARCHAR(200) NOT NULL,         -- 飞书应用密钥
    tenant_access_token TEXT,                 -- 租户访问令牌
    token_expires_at TIMESTAMP WITH TIME ZONE, -- 令牌过期时间
    sync_departments JSONB,                   -- 同步部门配置
    sync_users BOOLEAN DEFAULT TRUE NOT NULL, -- 是否同步用户
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 飞书同步配置索引
CREATE INDEX IF NOT EXISTS ix_feishu_sync_config_is_active ON feishu_sync_config(is_active);
```

### 3. 飞书同步日志表

```sql
-- 飞书同步日志表
CREATE TABLE IF NOT EXISTS feishu_sync_logs (
    id SERIAL PRIMARY KEY,
    sync_type VARCHAR(20) NOT NULL,           -- 'user'
    sync_action VARCHAR(20) NOT NULL,         -- 'create', 'update', 'delete'
    feishu_id VARCHAR(100) NOT NULL,          -- 飞书用户ID (open_id)
    local_id INTEGER,                         -- 本地ID
    sync_data JSONB,                          -- 同步数据
    status VARCHAR(20) NOT NULL,              -- 'success', 'failed', 'pending'
    error_message TEXT,                       -- 错误信息
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 同步日志索引
CREATE INDEX IF NOT EXISTS ix_feishu_sync_logs_sync_type ON feishu_sync_logs(sync_type);
CREATE INDEX IF NOT EXISTS ix_feishu_sync_logs_status ON feishu_sync_logs(status);
CREATE INDEX IF NOT EXISTS ix_feishu_sync_logs_created_at ON feishu_sync_logs(created_at);
```


## 🔧 模型设计

### 1. 标签模型优化

```python
class Tag(db.Model):
    """标签模型 - 优化版"""
    
    __tablename__ = "tags"
    
    # 基础字段
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True, index=True)
    display_name = db.Column(db.String(100), nullable=False)
    
    # 分类字段
    category_type = db.Column(db.String(20), nullable=False, index=True)  # 'resource' 或 'identity'
    category = db.Column(db.String(50), nullable=False, index=True)
    
    # 显示字段
    color = db.Column(db.String(20), default="primary", nullable=False)
    description = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # 同步字段
    is_auto_sync = db.Column(db.Boolean, default=False, nullable=False, index=True)
    sync_source = db.Column(db.String(50), nullable=True, index=True)  # 'feishu'
    sync_id = db.Column(db.String(100), nullable=True)  # 飞书ID
    synced_at = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # 身份类标签特有字段
    department_path = db.Column(db.String(500), nullable=True, index=True)  # 部门路径
    user_status = db.Column(db.String(20), default='active', nullable=False)  # 用户状态
    
    # 时间字段
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now)
    
    # 关系
    instances = db.relationship("Instance", secondary="instance_tags", back_populates="tags")
    
    @staticmethod
    def get_category_type_choices():
        """获取分类类型选项"""
        return [
            ("resource", "资源类"),
            ("identity", "身份类")
        ]
    
    @staticmethod
    def get_resource_categories():
        """获取资源类分类"""
        return [
            ("location", "地区标签"),
            ("environment", "环境标签"),
            ("project", "项目标签"),
            ("virtualization", "虚拟化类型"),
            ("deployment", "部署方式"),
            ("architecture", "架构类型"),
            ("other", "其他标签")
        ]
    
    @staticmethod
    def get_identity_categories():
        """获取身份类分类"""
        return [
            ("user", "用户标签")
        ]
```

### 2. 飞书同步配置模型

```python
class FeishuSyncConfig(db.Model):
    """飞书同步配置模型"""
    
    __tablename__ = "feishu_sync_config"
    
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.String(100), nullable=False)
    app_secret = db.Column(db.String(200), nullable=False)
    tenant_access_token = db.Column(db.Text, nullable=True)
    token_expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    sync_departments = db.Column(db.JSON, nullable=True)  # 同步部门配置
    sync_users = db.Column(db.Boolean, default=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now)
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "app_id": self.app_id,
            "sync_departments": self.sync_departments,
            "sync_users": self.sync_users,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
```

### 3. 飞书同步日志模型

```python
class FeishuSyncLog(db.Model):
    """飞书同步日志模型"""
    
    __tablename__ = "feishu_sync_logs"
    
    id = db.Column(db.Integer, primary_key=True)
    sync_type = db.Column(db.String(20), nullable=False, index=True)  # 'user'
    sync_action = db.Column(db.String(20), nullable=False)  # 'create', 'update', 'delete'
    feishu_id = db.Column(db.String(100), nullable=False)  # 飞书用户ID (open_id)
    local_id = db.Column(db.Integer, nullable=True)
    sync_data = db.Column(db.JSON, nullable=True)
    status = db.Column(db.String(20), nullable=False, index=True)  # 'success', 'failed', 'pending'
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=now, index=True)
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "sync_type": self.sync_type,
            "sync_action": self.sync_action,
            "feishu_id": self.feishu_id,
            "local_id": self.local_id,
            "sync_data": self.sync_data,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
```

## 🔄 飞书同步机制设计

### 1. 飞书API客户端

```python
class FeishuAPIClient:
    """飞书API客户端"""
    
    def __init__(self, app_id: str, app_secret: str):
        self.app_id = app_id
        self.app_secret = app_secret
        self.base_url = "https://open.feishu.cn/open-apis"
        self.tenant_access_token = None
        self.token_expires_at = None
    
    def get_tenant_access_token(self) -> str:
        """获取租户访问令牌"""
        if self.tenant_access_token and self.token_expires_at and now() < self.token_expires_at:
            return self.tenant_access_token
        
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        response = requests.post(url, json=data)
        result = response.json()
        
        if result.get("code") == 0:
            self.tenant_access_token = result["tenant_access_token"]
            # 设置过期时间（提前5分钟刷新）
            expires_in = result.get("expire", 7200) - 300
            self.token_expires_at = now() + timedelta(seconds=expires_in)
            return self.tenant_access_token
        else:
            raise Exception(f"获取飞书访问令牌失败: {result.get('msg')}")
    
    def get_users(self, department_ids: list = None) -> list:
        """获取用户列表"""
        token = self.get_tenant_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/contact/v3/users"
        params = {
            "page_size": 100,
            "department_id_type": "open_department_id"
        }
        
        if department_ids:
            params["department_ids"] = department_ids
        
        all_users = []
        page_token = None
        
        while True:
            if page_token:
                params["page_token"] = page_token
            
            response = requests.get(url, headers=headers, params=params)
            result = response.json()
            
            if result.get("code") == 0:
                users = result.get("data", {}).get("items", [])
                # 确保每个用户都有user_id字段
                for user in users:
                    if "user_id" not in user:
                        # 如果飞书API返回的字段名不同，需要映射
                        user["user_id"] = user.get("open_id") or user.get("union_id") or user.get("id")
                all_users.extend(users)
                
                page_token = result.get("data", {}).get("page_token")
                if not page_token:
                    break
            else:
                raise Exception(f"获取用户列表失败: {result.get('msg')}")
        
        return all_users
    
    def get_departments(self) -> list:
        """获取部门列表"""
        token = self.get_tenant_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/contact/v3/departments"
        params = {
            "page_size": 100,
            "department_id_type": "open_department_id"
        }
        
        all_departments = []
        page_token = None
        
        while True:
            if page_token:
                params["page_token"] = page_token
            
            response = requests.get(url, headers=headers, params=params)
            result = response.json()
            
            if result.get("code") == 0:
                departments = result.get("data", {}).get("items", [])
                all_departments.extend(departments)
                
                page_token = result.get("data", {}).get("page_token")
                if not page_token:
                    break
            else:
                raise Exception(f"获取部门列表失败: {result.get('msg')}")
        
        return all_departments
```

### 2. 飞书同步服务

```python
class FeishuSyncService:
    """飞书同步服务"""
    
    def __init__(self):
        self.config = FeishuSyncConfig.query.filter_by(is_active=True).first()
        if not self.config:
            raise Exception("飞书同步配置未找到")
        
        self.client = FeishuAPIClient(self.config.app_id, self.config.app_secret)
    
    def sync_all(self) -> dict:
        """同步所有数据"""
        result = {
            "users": {"created": 0, "updated": 0, "failed": 0}
        }
        
        try:
            # 同步用户
            if self.config.sync_users:
                user_result = self.sync_users()
                result["users"] = user_result
            
            return result
            
        except Exception as e:
            log_error(f"飞书同步失败: {str(e)}", module="feishu_sync")
            raise
    
    def sync_users(self) -> dict:
        """同步用户信息"""
        try:
            # 获取同步部门配置
            sync_departments = self.config.sync_departments or []
            department_ids = [dept["id"] for dept in sync_departments] if sync_departments else None
            
            # 获取飞书用户数据
            feishu_users = self.client.get_users(department_ids)
            
            created = 0
            updated = 0
            failed = 0
            
        for user_data in feishu_users:
            try:
                feishu_user_id = user_data["user_id"]  # 获取飞书用户ID
                # 创建或更新用户标签
                tag_result = self._sync_user_tag(user_data)
                if tag_result == "created":
                    created += 1
                elif tag_result == "updated":
                    updated += 1
                    
                    # 记录同步日志
                    self._log_sync("user", "create" if tag_result == "created" else "update", 
                                 feishu_user_id, tag_result, user_data)
                    
                except Exception as e:
                    failed += 1
                    self._log_sync("user", "create", feishu_user_id, "failed", 
                                 user_data, str(e))
            
            return {"created": created, "updated": updated, "failed": failed}
            
        except Exception as e:
            log_error(f"同步用户失败: {str(e)}", module="feishu_sync")
            raise
    
    
    def _sync_user_tag(self, user_data: dict) -> str:
        """同步用户标签"""
        feishu_user_id = user_data["user_id"]  # 飞书用户ID
        display_name = user_data.get("name", "")
        email = user_data.get("email", "")
        user_status = user_data.get("status", "active")  # 飞书用户状态
        
        # 构建部门路径
        department_path = self._build_department_path(user_data.get("department_ids", []))
        
        # 根据用户状态确定颜色
        color = "info" if user_status == "active" else "secondary"
        
        # 查找现有标签（以飞书用户ID为准）
        tag = Tag.query.filter_by(
            category_type="identity",
            category="user",
            sync_source="feishu",
            sync_id=feishu_user_id  # 使用飞书用户ID作为同步ID
        ).first()
        
        if tag:
            # 更新现有标签
            tag.display_name = display_name
            tag.department_path = department_path
            tag.user_status = user_status
            tag.color = color
            tag.synced_at = now()
            db.session.commit()
            return "updated"
        else:
            # 创建新标签
            tag = Tag(
                name=f"feishu_user_{feishu_user_id}",  # 标签名称包含飞书用户ID
                display_name=display_name,
                category_type="identity",
                category="user",
                color=color,  # 根据状态设置颜色
                description=f"用户: {display_name} ({email})",
                is_auto_sync=True,
                sync_source="feishu",
                sync_id=feishu_user_id,  # 存储飞书用户ID
                department_path=department_path,
                user_status=user_status,  # 存储用户状态
                synced_at=now()
            )
            db.session.add(tag)
            db.session.commit()
            return "created"
    
    
    def _build_department_path(self, department_ids: list) -> str:
        """构建部门路径"""
        # 这里需要根据部门ID获取完整的部门层级路径
        # 简化实现，实际需要递归获取父部门信息
        return "公司-部门-科室"  # 占位符
    
    def _log_sync(self, sync_type: str, sync_action: str, feishu_id: str, 
                  status: str, sync_data: dict, error_message: str = None):
        """记录同步日志"""
        log = FeishuSyncLog(
            sync_type=sync_type,
            sync_action=sync_action,
            feishu_id=feishu_id,
            sync_data=sync_data,
            status=status,
            error_message=error_message
        )
        db.session.add(log)
        db.session.commit()
```

### 3. 定时任务配置

```python
# 在 app/tasks.py 中添加飞书同步任务
from app.services.feishu_sync_service import FeishuSyncService

def feishu_sync_task():
    """飞书同步定时任务"""
    try:
        log_info("开始执行飞书同步任务", module="feishu_sync_task")
        
        sync_service = FeishuSyncService()
        result = sync_service.sync_all()
        
        log_info(
            "飞书同步任务完成",
            module="feishu_sync_task",
            result=result
        )
        
        return result
        
    except Exception as e:
        log_error(f"飞书同步任务失败: {str(e)}", module="feishu_sync_task")
        raise

# 在 app/scheduler.py 中注册任务
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

def register_feishu_sync_job():
    """注册飞书同步任务"""
    scheduler = get_scheduler()
    
    # 每天凌晨2点执行飞书同步
    scheduler.add_job(
        func=feishu_sync_task,
        trigger=CronTrigger(hour=2, minute=0),
        id='feishu_sync_daily',
        name='飞书每日同步',
        replace_existing=True
    )
    
    log_info("飞书同步任务已注册", module="scheduler")
```

### 4. 飞书同步配置管理

```python
class FeishuSyncConfigService:
    """飞书同步配置服务"""
    
    @staticmethod
    def create_config(app_id: str, app_secret: str, sync_departments: list = None) -> FeishuSyncConfig:
        """创建飞书同步配置"""
        config = FeishuSyncConfig(
            app_id=app_id,
            app_secret=app_secret,
            sync_departments=sync_departments or []
        )
        db.session.add(config)
        db.session.commit()
        return config
    
    @staticmethod
    def update_sync_departments(config_id: int, sync_departments: list):
        """更新同步部门配置"""
        config = FeishuSyncConfig.query.get(config_id)
        if config:
            config.sync_departments = sync_departments
            db.session.commit()
    
    @staticmethod
    def test_connection(app_id: str, app_secret: str) -> bool:
        """测试飞书连接"""
        try:
            client = FeishuAPIClient(app_id, app_secret)
            client.get_tenant_access_token()
            return True
        except Exception as e:
            log_error(f"飞书连接测试失败: {str(e)}", module="feishu_config")
            return False
```

## 🎨 前端界面设计

### 1. 标签管理页面优化

#### 分类筛选
```html
<!-- 标签分类筛选 -->
<div class="tag-category-filter mb-3">
    <div class="btn-group" role="group">
        <input type="radio" class="btn-check" name="categoryType" id="all" value="all" checked>
        <label class="btn btn-outline-primary" for="all">全部</label>
        
        <input type="radio" class="btn-check" name="categoryType" id="resource" value="resource">
        <label class="btn btn-outline-success" for="resource">资源类</label>
        
        <input type="radio" class="btn-check" name="categoryType" id="identity" value="identity">
        <label class="btn btn-outline-info" for="identity">身份类</label>
    </div>
</div>
```

#### 身份类标签显示
```html
<!-- 身份类标签特殊显示 -->
<div class="identity-tag-item" v-if="tag.category_type === 'identity'" 
     :class="{'inactive-user': tag.user_status === 'inactive'}">
    <div class="tag-icon">
        <i class="fas fa-user" :class="{'text-muted': tag.user_status === 'inactive'}"></i>
    </div>
    <div class="tag-info">
        <div class="tag-name" :class="{'text-muted': tag.user_status === 'inactive'}">
            {{ tag.display_name }}
            <span v-if="tag.user_status === 'inactive'" class="badge bg-secondary ms-1">离职</span>
        </div>
        <div class="tag-department" v-if="tag.department_path" 
             :class="{'text-muted': tag.user_status === 'inactive'}">
            {{ tag.department_path }}
        </div>
        <div class="tag-sync-info">
            <small class="text-muted">最后同步: {{ formatDate(tag.synced_at) }}</small>
        </div>
    </div>
    <div class="tag-actions">
        <span class="badge" :class="tag.user_status === 'active' ? 'bg-info' : 'bg-secondary'">
            {{ tag.user_status === 'active' ? '在职' : '离职' }}
        </span>
    </div>
</div>
```

#### 标签操作权限
```javascript
// 根据标签类型控制操作权限
function updateTagActions(tag) {
    const isIdentity = tag.category_type === 'identity';
    const isAutoSync = tag.is_auto_sync;
    
    // 身份类标签不可手动编辑
    if (isIdentity || isAutoSync) {
        $('#edit-tag-btn').prop('disabled', true);
        $('#delete-tag-btn').prop('disabled', true);
        $('#edit-tag-btn').attr('title', '身份类标签不可手动编辑');
        $('#delete-tag-btn').attr('title', '身份类标签不可手动删除');
    } else {
        $('#edit-tag-btn').prop('disabled', false);
        $('#delete-tag-btn').prop('disabled', false);
        $('#edit-tag-btn').removeAttr('title');
        $('#delete-tag-btn').removeAttr('title');
    }
}
```

### 2. 飞书同步配置页面

#### 同步配置表单
```html
<!-- 飞书同步配置 -->
<div class="feishu-sync-config">
    <div class="card">
        <div class="card-header">
            <h5><i class="fab fa-microsoft"></i> 飞书同步配置</h5>
        </div>
        <div class="card-body">
            <form id="feishu-config-form">
                <div class="row">
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label for="app_id" class="form-label">应用ID</label>
                            <input type="text" class="form-control" id="app_id" name="app_id" required>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="mb-3">
                            <label for="app_secret" class="form-label">应用密钥</label>
                            <input type="password" class="form-control" id="app_secret" name="app_secret" required>
                        </div>
                    </div>
                </div>
                
                <div class="mb-3">
                    <label class="form-label">同步范围</label>
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="sync_users" name="sync_users" checked>
                        <label class="form-check-label" for="sync_users">同步用户</label>
                    </div>
                </div>
                
                <div class="mb-3">
                    <label class="form-label">部门筛选</label>
                    <div id="department-tree">
                        <!-- 部门树形选择器 -->
                    </div>
                </div>
                
                <div class="mb-3">
                    <button type="button" class="btn btn-outline-primary" onclick="testFeishuConnection()">
                        <i class="fas fa-plug"></i> 测试连接
                    </button>
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-save"></i> 保存配置
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>
```

#### 同步状态监控
```html
<!-- 同步状态监控 -->
<div class="sync-status-monitor">
    <div class="card">
        <div class="card-header">
            <h5><i class="fas fa-sync"></i> 同步状态</h5>
        </div>
        <div class="card-body">
            <div class="row">
                <div class="col-md-4">
                    <div class="sync-stat-item">
                        <div class="stat-icon">
                            <i class="fas fa-users text-primary"></i>
                        </div>
                        <div class="stat-info">
                            <div class="stat-label">用户同步</div>
                            <div class="stat-value">{{ syncStats.users.total }}</div>
                            <div class="stat-detail">
                                <span class="text-success">+{{ syncStats.users.created }}</span>
                                <span class="text-warning">~{{ syncStats.users.updated }}</span>
                                <span class="text-danger">-{{ syncStats.users.failed }}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="sync-actions mt-3">
                <button class="btn btn-primary" onclick="startSync()">
                    <i class="fas fa-play"></i> 立即同步
                </button>
                <button class="btn btn-outline-secondary" onclick="viewSyncLogs()">
                    <i class="fas fa-list"></i> 查看日志
                </button>
            </div>
        </div>
    </div>
</div>
```

## 🔌 API接口设计

### 1. 标签管理API

#### 获取标签列表（支持分类筛选）
```http
GET /api/tags?category_type=resource&category=project&page=1&per_page=20
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "tags": [
            {
                "id": 1,
                "name": "mysql_prod",
                "display_name": "MySQL生产环境",
                "category_type": "resource",
                "category": "environment",
                "color": "danger",
                "description": "MySQL生产环境标签",
                "is_auto_sync": false,
                "created_at": "2025-09-25T10:00:00Z"
            },
            {
                "id": 2,
                "name": "user_12345",
                "display_name": "张三",
                "category_type": "identity",
                "category": "user",
                "color": "info",
                "department_path": "公司-技术部-开发组",
                "is_auto_sync": true,
                "sync_source": "feishu",
                "synced_at": "2025-09-25T09:30:00Z"
            }
        ],
        "pagination": {
            "page": 1,
            "per_page": 20,
            "total": 2,
            "pages": 1
        }
    }
}
```

#### 创建资源类标签
```http
POST /api/tags
Content-Type: application/json

{
    "name": "new_project",
    "display_name": "新项目",
    "category_type": "resource",
    "category": "project",
    "color": "primary",
    "description": "新项目标签"
}
```

#### 更新标签
```http
PUT /api/tags/{id}
Content-Type: application/json

{
    "display_name": "更新后的项目名称",
    "description": "更新后的描述"
}
```

#### 删除标签
```http
DELETE /api/tags/{id}
```

### 2. 飞书同步API

#### 获取飞书同步配置
```http
GET /api/feishu/config
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "id": 1,
        "app_id": "cli_xxx",
        "sync_departments": [
            {"id": "dept_123", "name": "技术部", "level": 2},
            {"id": "dept_456", "name": "产品部", "level": 2}
        ],
        "sync_users": true,
        "is_active": true
    }
}
```

#### 创建/更新飞书同步配置
```http
POST /api/feishu/config
Content-Type: application/json

{
    "app_id": "cli_xxx",
    "app_secret": "xxx",
    "sync_departments": [
        {"id": "dept_123", "name": "技术部", "level": 2}
    ],
    "sync_users": true
}
```

#### 测试飞书连接
```http
POST /api/feishu/test-connection
Content-Type: application/json

{
    "app_id": "cli_xxx",
    "app_secret": "xxx"
}
```

#### 立即同步
```http
POST /api/feishu/sync
Content-Type: application/json

{
    "sync_type": "all"  // "all", "users"
}
```

#### 获取同步状态
```http
GET /api/feishu/sync-status
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "last_sync": "2025-09-25T02:00:00Z",
        "next_sync": "2025-09-26T02:00:00Z",
        "status": "success",
        "stats": {
            "users": {"total": 100, "created": 5, "updated": 10, "failed": 0}
        }
    }
}
```

#### 获取同步日志
```http
GET /api/feishu/sync-logs?status=failed&page=1&per_page=20
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "logs": [
            {
                "id": 1,
                "sync_type": "user",
                "sync_action": "create",
                "feishu_id": "user_12345",
                "local_id": 2,
                "status": "success",
                "created_at": "2025-09-25T02:00:00Z"
            }
        ],
        "pagination": {
            "page": 1,
            "per_page": 20,
            "total": 1,
            "pages": 1
        }
    }
}
```


## 📊 使用场景

### 1. 资源类标签使用场景
- **实例分类**: 按地区、环境、项目对数据库实例进行分类
- **权限管理**: 基于项目、环境进行访问控制
- **统计报告**: 按分类生成资源使用统计
- **批量操作**: 对同类型资源进行批量管理

### 2. 身份类标签使用场景
- **责任归属**: 明确每个资源的具体负责人
- **权限控制**: 基于人员身份进行细粒度权限控制
- **审计追踪**: 记录资源变更的责任人
- **通知告警**: 向相关责任人发送告警信息
- **部门信息**: 显示用户所属的部门层级信息
- **状态管理**: 通过颜色和样式区分在职/离职用户

## 🚀 实施计划

### 阶段1: 数据库结构优化 (1-2天)
1. 创建数据库迁移脚本
2. 更新标签模型，添加身份类支持
3. 创建飞书同步配置和日志表
4. 数据迁移和验证

### 阶段2: 飞书集成开发 (2-3天)
1. 实现飞书API客户端
2. 实现用户同步服务
3. 创建定时任务调度
4. 添加同步配置管理

### 阶段3: 后端API开发 (1-2天)
1. 更新标签管理API
2. 创建飞书同步API
3. 完善权限控制

### 阶段4: 前端界面优化 (2-3天)
1. 更新标签管理页面，支持分类筛选
2. 创建飞书同步配置页面
3. 优化用户标签显示（图标、部门路径）
4. 添加同步状态监控

### 阶段5: 测试和部署 (1-2天)
1. 单元测试和集成测试
2. 飞书API集成测试
3. 用户验收测试
4. 生产环境部署

## 📈 预期效果

### 功能提升
- **分类清晰**: 资源类和身份类标签分离管理
- **自动化**: 飞书人员信息自动同步，减少手动维护
- **权限精确**: 基于人员身份的细粒度权限控制
- **审计完整**: 完整的资源归属和变更记录
- **用户体验**: 用户图标和部门层级信息提升界面友好性
- **状态可视化**: 通过颜色和样式直观显示用户在职/离职状态

### 管理效率
- **减少维护**: 飞书自动同步减少手动维护工作
- **提高准确性**: 自动同步确保数据一致性
- **增强安全性**: 基于人员身份的权限控制更安全
- **便于审计**: 清晰的归属关系便于审计追踪
- **灵活配置**: 支持按部门筛选同步范围

### 技术优势
- **飞书集成**: 与现有企业系统无缝集成，以飞书用户ID为准
- **三级部门**: 支持公司-部门-科室的完整层级
- **用户图标**: 使用Font Awesome用户图标提升界面体验
- **状态区分**: 在职用户显示蓝色，离职用户显示灰色，视觉区分明显
- **定时同步**: 每日自动同步确保数据最新
- **错误处理**: 完善的同步日志和错误处理机制

## 🔧 技术要点

### 飞书API集成
- **认证机制**: 使用应用凭证获取租户访问令牌
- **用户接口**: 调用飞书用户管理API获取用户信息，以open_id作为唯一标识
- **分页处理**: 支持大量数据的分页获取
- **错误重试**: 实现指数退避重试机制
- **令牌刷新**: 自动处理访问令牌过期

### 数据同步策略
- **增量同步**: 只同步变更的数据
- **用户ID映射**: 以飞书open_id作为唯一标识，确保用户数据一致性
- **状态同步**: 同步飞书用户状态，支持在职/离职状态管理
- **冲突处理**: 处理数据冲突和重复
- **回滚机制**: 同步失败时的数据回滚
- **日志记录**: 详细的同步操作日志

### 性能优化
- **批量操作**: 批量处理数据库操作
- **缓存机制**: 缓存部门树和用户信息
- **异步处理**: 大量数据异步同步
- **资源限制**: 控制API调用频率

## 📋 配置要求

### 飞书应用配置
- **应用类型**: 企业自建应用
- **权限范围**: 通讯录读取权限
- **回调地址**: 配置Webhook回调（可选）
- **IP白名单**: 配置服务器IP白名单

### 系统配置
- **Python依赖**: 添加requests库
- **环境变量**: 配置飞书应用凭证
- **定时任务**: 配置APScheduler任务
- **数据库**: 支持JSON字段存储

---

**文档版本**: v1.1  
**创建时间**: 2025-09-25  
**最后更新**: 2025-09-25  
**维护团队**: TaifishingV4 Team
