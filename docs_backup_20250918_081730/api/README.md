# 泰摸鱼吧 - API接口文档

## 概述
泰摸鱼吧提供RESTful API接口，支持数据库实例管理、账户同步、任务调度等功能。

## 基础信息
- **开发环境URL**: `http://localhost:5001/api`
- **生产环境URL**: `http://localhost:8000/api`
- **认证方式**: JWT Token
- **数据格式**: JSON
- **字符编码**: UTF-8
- **当前状态**: 基础API已实现，功能API开发中

## 当前已实现的API

### 系统状态API ✅

#### 获取API状态
```http
GET /api/status
```

**响应:**
```json
{
  "status": "success",
  "message": "泰摸鱼吧API运行正常",
  "version": "1.0.0",
  "user": null
}
```

#### 健康检查
```http
GET /api/health
```

**响应:**
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "timestamp": "2025-09-07T22:06:25Z"
}
```

### 基础Web界面 ✅

#### 首页
```http
GET /
```

**响应:** HTML页面，包含系统状态监控界面

## 计划实现的API

### 认证

### 登录
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "Admin123"
}
```

**响应:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### 刷新Token
```http
POST /api/auth/refresh
Authorization: Bearer <token>
```

## 实例管理

### 获取实例列表
```http
GET /api/instances
Authorization: Bearer <token>
```

### 创建实例
```http
POST /api/instances
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "生产数据库",
  "db_type": "postgresql",
  "host": "192.168.1.100",
  "port": 5432,
  "credential_id": 1,
  "description": "生产环境PostgreSQL数据库"
}
```

### 测试连接
```http
POST /api/instances/{id}/test
Authorization: Bearer <token>
```

## 凭据管理

### 获取凭据列表
```http
GET /api/credentials
Authorization: Bearer <token>
```

### 创建凭据
```http
POST /api/credentials
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "生产数据库凭据",
  "credential_type": "database",
  "db_type": "postgresql",
  "username": "admin",
  "password": "password123"
}
```

## 账户同步

### 获取账户列表
```http
GET /api/accounts
Authorization: Bearer <token>
```

### 同步账户
```http
POST /api/accounts/sync
Authorization: Bearer <token>
Content-Type: application/json

{
  "instance_id": 1,
  "account_ids": [1, 2, 3]
}
```

## 任务管理

### 获取任务列表
```http
GET /api/tasks
Authorization: Bearer <token>
```

### 创建任务
```http
POST /api/tasks
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "每日同步任务",
  "instance_id": 1,
  "schedule": "0 2 * * *",
  "enabled": true
}
```

## 错误处理

### 错误响应格式
```json
{
  "error": "错误类型",
  "message": "错误描述",
  "code": 400,
  "details": {}
}
```

### 常见错误码
- `400` - 请求参数错误
- `401` - 未授权
- `403` - 禁止访问
- `404` - 资源不存在
- `500` - 服务器内部错误

## 分页

### 分页参数
- `page` - 页码 (默认: 1)
- `per_page` - 每页数量 (默认: 20, 最大: 100)

### 分页响应
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "pages": 5
  }
}
```

## 状态码

### HTTP状态码
- `200` - 成功
- `201` - 创建成功
- `204` - 删除成功
- `400` - 请求错误
- `401` - 未授权
- `403` - 禁止访问
- `404` - 未找到
- `500` - 服务器错误

## 示例

### 完整的API调用示例
```bash
# 1. 登录获取Token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "Admin123"}'

# 2. 使用Token获取实例列表
curl -X GET http://localhost:8000/api/instances \
  -H "Authorization: Bearer <token>"

# 3. 创建新实例
curl -X POST http://localhost:8000/api/instances \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试数据库",
    "db_type": "mysql",
    "host": "localhost",
    "port": 3306,
    "credential_id": 1
  }'
```
