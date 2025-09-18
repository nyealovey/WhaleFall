# 鲸落 - API接口文档

## 概述
鲸落提供完整的RESTful API接口，支持数据库实例管理、账户分类、任务调度、日志监控等功能。

## 基础信息
- **开发环境URL**: `http://localhost:5001`
- **生产环境URL**: `http://localhost:8000`
- **认证方式**: JWT Token + Flask-Login Session
- **数据格式**: JSON
- **字符编码**: UTF-8
- **当前状态**: 所有核心API已实现并投入使用

## 已实现的API

### 系统状态API ✅

#### 健康检查
```http
GET /api/health
```

**响应:**
```json
{
  "status": "success",
  "data": {
    "status": "healthy",
    "timestamp": 1694123456.789,
    "version": "1.0.0"
  },
  "message": "服务运行正常"
}
```

#### 详细健康检查
```http
GET /health/detailed
```

**响应:**
```json
{
  "status": "success",
  "data": {
    "status": "healthy",
    "database": "connected",
    "redis": "connected",
    "timestamp": "2025-09-18T08:30:00Z",
    "version": "4.0.0"
  }
}
```

### 认证API ✅

#### 登录
```http
POST /auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "Admin123"
}
```

**响应:**
```json
{
  "status": "success",
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
      "id": 1,
      "username": "admin",
      "role": "admin"
    }
  },
  "message": "登录成功"
}
```

#### 刷新Token
```http
POST /api/refresh
Authorization: Bearer <refresh_token>
```

#### 获取当前用户信息
```http
GET /api/me
Authorization: Bearer <access_token>
```

### 仪表板API ✅

#### 系统概览
```http
GET /api/overview
Authorization: Bearer <token>
```

#### 图表数据
```http
GET /api/charts
Authorization: Bearer <token>
```

#### 活动日志
```http
GET /api/activities
Authorization: Bearer <token>
```

#### 系统状态
```http
GET /api/status
Authorization: Bearer <token>
```

### 数据库实例管理API ✅

#### 获取实例列表
```http
GET /api/instances
Authorization: Bearer <token>
```

#### 获取实例详情
```http
GET /api/instances/{id}
Authorization: Bearer <token>
```

#### 测试连接
```http
POST /api/instances/{id}/test
Authorization: Bearer <token>
```

#### 测试连接（通用）
```http
POST /api/test-connection
Authorization: Bearer <token>
Content-Type: application/json

{
  "db_type": "postgresql",
  "host": "localhost",
  "port": 5432,
  "username": "user",
  "password": "password",
  "database": "test"
}
```

#### 获取实例统计
```http
GET /api/statistics
Authorization: Bearer <token>
```

### 账户分类管理API ✅

#### 获取分类批次
```http
GET /api/batches
Authorization: Bearer <token>
```

#### 获取批次详情
```http
GET /api/batches/{batch_id}
Authorization: Bearer <token>
```

#### 获取批次匹配结果
```http
GET /api/batches/{batch_id}/matches
Authorization: Bearer <token>
```

### 任务调度API ✅

#### 获取任务列表
```http
GET /api/jobs
Authorization: Bearer <token>
```

#### 获取任务详情
```http
GET /api/jobs/{job_id}
Authorization: Bearer <token>
```

#### 创建任务
```http
POST /api/jobs
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "账户同步任务",
  "task_type": "sync_accounts",
  "db_type": "postgresql",
  "schedule": "0 */30 * * * *",
  "description": "每30分钟同步一次账户"
}
```

#### 更新任务
```http
PUT /api/jobs/{job_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "更新的任务名称",
  "schedule": "0 0 */6 * * *"
}
```

#### 删除任务
```http
DELETE /api/jobs/{job_id}
Authorization: Bearer <token>
```

#### 启用/禁用任务
```http
POST /api/jobs/{job_id}/enable
POST /api/jobs/{job_id}/disable
Authorization: Bearer <token>
```

#### 暂停/恢复任务
```http
POST /api/jobs/{job_id}/pause
POST /api/jobs/{job_id}/resume
Authorization: Bearer <token>
```

#### 立即执行任务
```http
POST /api/jobs/{job_id}/run
Authorization: Bearer <token>
```

### 同步会话API ✅

#### 获取同步会话列表
```http
GET /api/sessions
Authorization: Bearer <token>
```

#### 获取会话详情
```http
GET /api/sessions/{session_id}
Authorization: Bearer <token>
```

#### 取消同步会话
```http
POST /api/sessions/{session_id}/cancel
Authorization: Bearer <token>
```

#### 获取错误日志
```http
GET /api/sessions/{session_id}/error-logs
Authorization: Bearer <token>
```

#### 获取同步统计
```http
GET /api/statistics
Authorization: Bearer <token>
```

### 日志管理API ✅

#### 搜索日志
```http
GET /api/search?level=ERROR&module=auth&start_date=2025-09-01&end_date=2025-09-18
Authorization: Bearer <token>
```

#### 获取日志统计
```http
GET /api/statistics
Authorization: Bearer <token>
```

#### 获取错误日志
```http
GET /api/errors
Authorization: Bearer <token>
```

#### 获取日志模块
```http
GET /api/modules
Authorization: Bearer <token>
```

#### 导出日志
```http
GET /api/export?format=csv&start_date=2025-09-01&end_date=2025-09-18
Authorization: Bearer <token>
```

#### 清理日志
```http
POST /api/cleanup
Authorization: Bearer <token>
Content-Type: application/json

{
  "days": 30
}
```

#### 实时日志
```http
GET /api/real-time
Authorization: Bearer <token>
```

#### 日志健康检查
```http
GET /api/health
Authorization: Bearer <token>
```

#### 日志统计信息
```http
GET /api/stats
Authorization: Bearer <token>
```

#### 获取日志详情
```http
GET /api/detail/{log_id}
Authorization: Bearer <token>
```

### 用户管理API ✅

#### 获取用户列表
```http
GET /api/users
Authorization: Bearer <token>
```

#### 创建用户
```http
POST /api/users
Authorization: Bearer <token>
Content-Type: application/json

{
  "username": "newuser",
  "password": "password123",
  "role": "user",
  "email": "user@example.com"
}
```

#### 更新用户
```http
PUT /api/users/{user_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "username": "updateduser",
  "role": "admin"
}
```

#### 删除用户
```http
DELETE /api/users/{user_id}
Authorization: Bearer <token>
```

#### 切换用户状态
```http
POST /api/users/{user_id}/toggle-status
Authorization: Bearer <token>
```

#### 获取用户统计
```http
GET /api/users/stats
Authorization: Bearer <token>
```

### 凭据管理API ✅

#### 获取凭据列表
```http
GET /api/credentials
Authorization: Bearer <token>
```

#### 获取凭据详情
```http
GET /api/credentials/{credential_id}
Authorization: Bearer <token>
```

### 数据库类型API ✅

#### 获取数据库类型列表
```http
GET /api/list
Authorization: Bearer <token>
```

#### 获取活跃数据库类型
```http
GET /api/active
Authorization: Bearer <token>
```

#### 获取表单选项
```http
GET /api/form-options
Authorization: Bearer <token>
```

## 权限控制

### 权限级别
- **view_required**: 查看权限
- **create_required**: 创建权限  
- **update_required**: 更新权限
- **delete_required**: 删除权限
- **scheduler_view_required**: 任务查看权限
- **scheduler_manage_required**: 任务管理权限

### 管理员权限
- **admin_required**: 管理员权限，用于系统配置和用户管理

## 响应格式

### 成功响应
```json
{
  "status": "success",
  "data": {
    // 具体数据
  },
  "message": "操作成功"
}
```

### 错误响应
```json
{
  "status": "error",
  "error": "错误类型",
  "message": "错误描述",
  "code": 400,
  "details": {}
}
```

### 分页响应
```json
{
  "status": "success",
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "pages": 5
  }
}
```

## 错误处理

### 常见错误码
- `400` - 请求参数错误
- `401` - 未授权
- `403` - 禁止访问
- `404` - 资源不存在
- `500` - 服务器内部错误

### 错误类型
- **ValidationError**: 数据验证错误
- **AuthenticationError**: 认证失败
- **AuthorizationError**: 权限不足
- **ResourceNotFoundError**: 资源不存在
- **DatabaseError**: 数据库操作错误
- **ExternalServiceError**: 外部服务错误

## 分页

### 分页参数
- `page` - 页码 (默认: 1)
- `per_page` - 每页数量 (默认: 20, 最大: 100)
- `sort` - 排序字段
- `order` - 排序方向 (asc/desc)

### 查询参数
- `search` - 搜索关键词
- `filter` - 过滤条件
- `start_date` - 开始日期
- `end_date` - 结束日期

## HTTP状态码

### 成功状态码
- `200` - 成功
- `201` - 创建成功
- `204` - 删除成功

### 客户端错误
- `400` - 请求错误
- `401` - 未授权
- `403` - 禁止访问
- `404` - 未找到
- `422` - 数据验证错误

### 服务器错误
- `500` - 服务器内部错误
- `502` - 网关错误
- `503` - 服务不可用

## 使用示例

### 完整的API调用流程
```bash
# 1. 登录获取Token
curl -X POST http://localhost:5001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "Admin123"}'

# 2. 使用Token获取实例列表
curl -X GET http://localhost:5001/api/instances \
  -H "Authorization: Bearer <access_token>"

# 3. 创建定时任务
curl -X POST http://localhost:5001/api/jobs \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "账户同步任务",
    "task_type": "sync_accounts",
    "db_type": "postgresql",
    "schedule": "0 */30 * * * *",
    "description": "每30分钟同步一次账户"
  }'

# 4. 获取日志统计
curl -X GET "http://localhost:5001/api/statistics?start_date=2025-09-01&end_date=2025-09-18" \
  -H "Authorization: Bearer <access_token>"
```

### JavaScript调用示例
```javascript
// 登录获取Token
const loginResponse = await fetch('/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    username: 'admin',
    password: 'Admin123'
  })
});

const loginData = await loginResponse.json();
const token = loginData.data.access_token;

// 使用Token调用API
const instancesResponse = await fetch('/api/instances', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const instances = await instancesResponse.json();
console.log(instances);
```

## 注意事项

1. **认证**: 大部分API需要JWT Token认证
2. **权限**: 不同操作需要相应权限级别
3. **频率限制**: API调用有频率限制，避免过于频繁的请求
4. **数据格式**: 所有请求和响应都使用JSON格式
5. **时区**: 所有时间字段使用UTC时区
6. **错误处理**: 请妥善处理API返回的错误信息
7. **版本控制**: 当前API版本为v4.0.0
