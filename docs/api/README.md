# 鲸落 (TaifishV4) API 文档

## 📋 API 概览

鲸落提供完整的RESTful API接口，支持数据库实例管理、账户分类、数据同步、任务调度等核心功能。所有API接口都支持JSON格式的请求和响应。

### 基础信息
- **API版本**: v1.2.2
- **基础URL**: `http://your-domain.com/api`
- **认证方式**: JWT Token / Session Cookie
- **数据格式**: JSON
- **字符编码**: UTF-8

## 🔐 认证与授权

### 认证方式

#### 1. Session Cookie 认证
```http
POST /auth/login
Content-Type: application/json

{
    "username": "admin",
    "password": "password123"
}
```

#### 2. JWT Token 认证
```http
Authorization: Bearer <jwt_token>
```

### 用户角色权限

| 角色 | 权限描述 |
|------|----------|
| admin | 系统管理员，拥有所有权限 |
| dba | 数据库管理员，拥有数据库相关权限 |
| operator | 操作员，拥有基本操作权限 |
| viewer | 只读用户，只能查看数据 |

## 🗄️ 数据库实例管理 API

### 实例列表
```http
GET /api/instances
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "instances": [
            {
                "id": 1,
                "name": "MySQL-Prod",
                "host": "192.168.1.100",
                "port": 3306,
                "db_type": "mysql",
                "status": "active",
                "created_at": "2025-09-25T10:00:00Z"
            }
        ],
        "total": 1
    }
}
```

### 创建实例
```http
POST /api/instances
Content-Type: application/json

{
    "name": "MySQL-Prod",
    "host": "192.168.1.100",
    "port": 3306,
    "db_type": "mysql",
    "credentials": {
        "username": "root",
        "password": "password123"
    }
}
```

### 更新实例
```http
PUT /api/instances/{id}
Content-Type: application/json

{
    "name": "MySQL-Prod-Updated",
    "host": "192.168.1.101"
}
```

### 删除实例
```http
DELETE /api/instances/{id}
```

### 测试连接
```http
POST /api/instances/{id}/test-connection
```

## 🏷️ 标签管理 API

### 标签列表
```http
GET /api/tags
```

**查询参数**:
- `page`: 页码 (默认: 1)
- `per_page`: 每页数量 (默认: 20)
- `search`: 搜索关键词
- `category`: 分类筛选
- `status`: 状态筛选

**响应示例**:
```json
{
    "success": true,
    "data": {
        "tags": [
            {
                "id": 1,
                "name": "core_system",
                "display_name": "核心系统",
                "category": "project",
                "color": "primary",
                "description": "核心业务系统",
                "is_active": true,
                "instances_count": 5
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

### 创建标签
```http
POST /api/tags
Content-Type: application/json

{
    "name": "test_system",
    "display_name": "测试系统",
    "category": "project",
    "color": "success",
    "description": "测试环境系统"
}
```

### 更新标签
```http
PUT /api/tags/{id}
Content-Type: application/json

{
    "display_name": "测试系统-更新",
    "description": "更新后的描述"
}
```

### 删除标签
```http
DELETE /api/tags/{id}
```

### 批量分配标签
```http
POST /api/tags/batch-assign
Content-Type: application/json

{
    "instance_ids": [1, 2, 3],
    "tag_ids": [1, 2],
    "operation": "assign"
}
```

## 👥 账户分类管理 API

### 分类列表
```http
GET /api/account-classifications
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "classifications": [
            {
                "id": 1,
                "name": "核心系统账户",
                "description": "核心业务系统相关账户",
                "db_type": "mysql",
                "is_active": true,
                "accounts_count": 10
            }
        ]
    }
}
```

### 创建分类
```http
POST /api/account-classifications
Content-Type: application/json

{
    "name": "测试系统账户",
    "description": "测试环境相关账户",
    "db_type": "mysql",
    "rules": [
        {
            "field": "username",
            "operator": "contains",
            "value": "test"
        }
    ]
}
```

### 执行分类
```http
POST /api/account-classifications/{id}/execute
```

### 获取分类结果
```http
GET /api/account-classifications/{id}/results
```

## 🔄 数据同步管理 API

### 同步会话列表
```http
GET /api/sync-sessions
```

**查询参数**:
- `status`: 状态筛选 (running, completed, failed, cancelled)
- `page`: 页码
- `per_page`: 每页数量

**响应示例**:
```json
{
    "success": true,
    "data": {
        "sessions": [
            {
                "id": 1,
                "name": "账户同步-2025-09-25",
                "status": "completed",
                "start_time": "2025-09-25T10:00:00Z",
                "end_time": "2025-09-25T10:05:00Z",
                "records_count": 100,
                "success_count": 95,
                "failed_count": 5
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

### 创建同步会话
```http
POST /api/sync-sessions
Content-Type: application/json

{
    "name": "账户同步-2025-09-25",
    "instance_ids": [1, 2, 3],
    "sync_type": "account_sync"
}
```

### 启动同步
```http
POST /api/sync-sessions/{id}/start
```

### 停止同步
```http
POST /api/sync-sessions/{id}/stop
```

### 获取同步详情
```http
GET /api/sync-sessions/{id}/details
```

## ⏰ 任务调度管理 API

### 任务列表
```http
GET /api/scheduler/tasks
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "tasks": [
            {
                "id": "account_sync_task",
                "name": "账户同步任务",
                "type": "account_sync",
                "status": "running",
                "next_run_time": "2025-09-25T11:00:00Z",
                "last_run_time": "2025-09-25T10:00:00Z",
                "is_enabled": true
            }
        ]
    }
}
```

### 启用任务
```http
POST /api/scheduler/tasks/{id}/enable
```

### 禁用任务
```http
POST /api/scheduler/tasks/{id}/disable
```

### 立即执行任务
```http
POST /api/scheduler/tasks/{id}/execute
```

### 获取任务日志
```http
GET /api/scheduler/tasks/{id}/logs
```

## 📊 日志监控 API

### 日志列表
```http
GET /api/logs
```

**查询参数**:
- `level`: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `module`: 模块名称
- `time_range`: 时间范围 (1h, 1d, 1w, 1m)
- `page`: 页码
- `per_page`: 每页数量

**响应示例**:
```json
{
    "success": true,
    "data": {
        "logs": [
            {
                "id": 1,
                "level": "INFO",
                "module": "account_sync",
                "message": "账户同步完成",
                "timestamp": "2025-09-25T10:05:00Z",
                "details": {
                    "instance_id": 1,
                    "accounts_count": 100
                }
            }
        ],
        "pagination": {
            "page": 1,
            "per_page": 50,
            "total": 100,
            "pages": 2
        }
    }
}
```

### 获取日志统计
```http
GET /api/logs/statistics
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "total_logs": 1000,
        "by_level": {
            "DEBUG": 100,
            "INFO": 700,
            "WARNING": 150,
            "ERROR": 40,
            "CRITICAL": 10
        },
        "by_module": {
            "account_sync": 300,
            "permission_scan": 200,
            "data_cleanup": 100
        }
    }
}
```

## 👤 用户管理 API

### 用户列表
```http
GET /api/users
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "users": [
            {
                "id": 1,
                "username": "admin",
                "email": "admin@example.com",
                "role": "admin",
                "is_active": true,
                "created_at": "2025-09-25T10:00:00Z",
                "last_login": "2025-09-25T10:00:00Z"
            }
        ]
    }
}
```

### 创建用户
```http
POST /api/users
Content-Type: application/json

{
    "username": "newuser",
    "email": "newuser@example.com",
    "password": "password123",
    "role": "operator"
}
```

### 更新用户
```http
PUT /api/users/{id}
Content-Type: application/json

{
    "email": "updated@example.com",
    "role": "dba"
}
```

### 删除用户
```http
DELETE /api/users/{id}
```

## 🔧 系统管理 API

### 系统信息
```http
GET /api/system/info
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "app_name": "鲸落",
        "app_version": "1.2.2",
        "python_version": "3.11.0",
        "flask_version": "3.1.2",
        "uptime": "2 days, 5 hours",
        "memory_usage": "256MB",
        "cpu_usage": "15%"
    }
}
```

### 健康检查
```http
GET /health/api/health
```

**响应示例**:
```json
{
    "success": true,
    "data": {
        "status": "healthy",
        "timestamp": "2025-09-25T10:00:00Z",
        "version": "1.2.2",
        "components": {
            "database": "healthy",
            "cache": "healthy",
            "system": "healthy"
        }
    }
}
```

### 缓存管理
```http
GET /api/cache/status
```

```http
POST /api/cache/clear
```

## 📈 统计报告 API

### 实例统计
```http
GET /api/statistics/instances
```

### 账户统计
```http
GET /api/statistics/accounts
```

### 同步统计
```http
GET /api/statistics/sync
```

### 系统统计
```http
GET /api/statistics/system
```

## ❌ 错误处理

### 错误响应格式
```json
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "请求参数验证失败",
        "details": {
            "field": "username",
            "reason": "用户名不能为空"
        }
    }
}
```

### 常见错误码

| 错误码 | HTTP状态码 | 描述 |
|--------|------------|------|
| VALIDATION_ERROR | 400 | 请求参数验证失败 |
| AUTHENTICATION_FAILED | 401 | 认证失败 |
| PERMISSION_DENIED | 403 | 权限不足 |
| RESOURCE_NOT_FOUND | 404 | 资源不存在 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |

## 🔍 搜索和筛选

### 统一搜索
```http
GET /api/search?q=关键词&type=instances&filters={"status":"active"}
```

### 高级筛选
```http
GET /api/instances?filters={"db_type":"mysql","status":"active","created_after":"2025-01-01"}
```

## 📝 请求示例

### cURL 示例
```bash
# 获取实例列表
curl -X GET "http://localhost:5000/api/instances" \
  -H "Authorization: Bearer your_jwt_token"

# 创建标签
curl -X POST "http://localhost:5000/api/tags" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_jwt_token" \
  -d '{
    "name": "test_tag",
    "display_name": "测试标签",
    "category": "project",
    "color": "primary"
  }'
```

### Python 示例
```python
import requests

# 设置基础URL和认证
base_url = "http://localhost:5000/api"
headers = {
    "Authorization": "Bearer your_jwt_token",
    "Content-Type": "application/json"
}

# 获取实例列表
response = requests.get(f"{base_url}/instances", headers=headers)
instances = response.json()

# 创建标签
tag_data = {
    "name": "test_tag",
    "display_name": "测试标签",
    "category": "project",
    "color": "primary"
}
response = requests.post(f"{base_url}/tags", headers=headers, json=tag_data)
```

## 📚 更多信息

- [认证授权](./AUTHENTICATION.md) - 详细的认证和授权说明
- [错误处理](./ERROR_HANDLING.md) - 错误码和异常处理指南
- [开发指南](../development/DEVELOPMENT_SETUP.md) - 开发环境搭建指南

---

**最后更新**: 2025-11-05  
**API版本**: v1.2.2  
**维护团队**: TaifishingV4 Team
