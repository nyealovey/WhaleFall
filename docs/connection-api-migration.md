# 数据库连接API抽离方案

## 📋 概述

将分散在各个模块中的数据库连接测试功能统一抽离到独立的连接管理模块，提供统一的API接口和前端组件。

## 🎯 设计目标

1. **统一管理**：所有数据库连接测试功能集中管理
2. **功能完整**：支持现有实例测试、新连接测试、批量测试等
3. **向后兼容**：保留现有API，提供迁移路径
4. **易于使用**：提供前端组件和详细文档

## 🏗️ 架构设计

### 新增模块

#### 1. 连接管理API模块 (`app/routes/connections.py`)

**核心功能**：
- 统一的连接测试API
- 支持现有实例和新连接测试
- 批量测试功能
- 连接状态查询
- 参数验证

**API端点**：
```
POST /connections/api/test              # 测试连接（通用）
GET  /connections/api/supported-types  # 获取支持的数据库类型
POST /connections/api/validate-params  # 验证连接参数
POST /connections/api/batch-test       # 批量测试连接
GET  /connections/api/status/<id>      # 获取连接状态
```

#### 2. 前端连接管理组件 (`app/static/js/components/connection-manager.js`)

**功能特性**：
- 统一的连接测试接口
- 支持回调函数和Promise
- 内置UI组件
- 批量测试进度显示

## 🔄 迁移方案

### 阶段1：新增连接管理模块（已完成）

✅ 创建 `app/routes/connections.py`
✅ 注册蓝图到应用
✅ 创建前端组件
✅ 更新API文档

### 阶段2：标记旧API为已弃用

✅ 更新 `instances.py` 中的连接测试API
✅ 更新 `storage_sync.py` 中的连接测试API
✅ 添加弃用警告和重定向

### 阶段3：前端迁移（待完成）

**需要更新的前端文件**：
- `app/static/js/pages/instances/detail.js`
- `app/static/js/pages/instances/list.js`
- `app/static/js/pages/instances/edit.js`
- `app/static/js/pages/database_sizes/*.js`

**迁移步骤**：
1. 引入连接管理组件
2. 替换现有的连接测试调用
3. 更新UI显示逻辑

### 阶段4：清理旧代码（未来）

- 移除已弃用的API
- 清理重复的连接测试逻辑
- 优化代码结构

## 📖 使用指南

### 后端API使用

#### 测试现有实例连接

```python
# 请求
POST /connections/api/test
{
    "instance_id": 123
}

# 响应
{
    "success": true,
    "message": "连接成功，数据库版本: 8.0.32",
    "version": "8.0.32"
}
```

#### 测试新连接参数

```python
# 请求
POST /connections/api/test
{
    "db_type": "mysql",
    "host": "localhost",
    "port": 3306,
    "credential_id": 1,
    "name": "测试连接"
}

# 响应
{
    "success": true,
    "message": "连接成功，数据库版本: 8.0.32",
    "version": "8.0.32"
}
```

#### 批量测试连接

```python
# 请求
POST /connections/api/batch-test
{
    "instance_ids": [1, 2, 3, 4, 5]
}

# 响应
{
    "success": true,
    "data": [
        {
            "instance_id": 1,
            "instance_name": "MySQL-01",
            "success": true,
            "message": "连接成功"
        },
        // ... 更多结果
    ],
    "summary": {
        "total": 5,
        "success": 4,
        "failed": 1
    }
}
```

### 前端组件使用

#### 基本使用

```javascript
// 测试现有实例连接
const result = await connectionManager.testInstanceConnection(123, {
    onSuccess: (result) => {
        console.log('连接成功:', result);
        connectionManager.showTestResult(result, 'test-result');
    },
    onError: (error) => {
        console.error('连接失败:', error);
        connectionManager.showTestResult(error, 'test-result');
    }
});

// 测试新连接参数
const result = await connectionManager.testNewConnection({
    db_type: 'mysql',
    host: 'localhost',
    port: 3306,
    credential_id: 1
});

// 批量测试
const result = await connectionManager.batchTestConnections([1, 2, 3], {
    onProgress: (result) => {
        connectionManager.showBatchTestProgress(result, 'batch-progress');
    }
});
```

#### 在HTML中使用

```html
<!-- 引入连接管理组件 -->
<script src="/static/js/components/connection-manager.js"></script>

<!-- 连接测试结果容器 -->
<div id="connection-test-result"></div>

<!-- 批量测试进度容器 -->
<div id="batch-test-progress"></div>

<script>
// 测试连接
document.getElementById('test-btn').addEventListener('click', async () => {
    const instanceId = document.getElementById('instance-id').value;
    await connectionManager.testInstanceConnection(instanceId, {
        onSuccess: (result) => {
            connectionManager.showTestResult(result, 'connection-test-result');
        },
        onError: (error) => {
            connectionManager.showTestResult(error, 'connection-test-result');
        }
    });
});
</script>
```

## 🔧 配置说明

### 环境变量

无需额外配置，使用现有的数据库连接配置。

### 权限控制

所有API都需要登录认证和相应的权限：
- `@login_required` - 需要登录
- `@view_required` - 需要查看权限

### 错误处理

统一的错误响应格式：
```json
{
    "success": false,
    "error": "错误描述"
}
```

## 📊 性能优化

### 批量测试限制

- 单次批量测试最多50个实例
- 建议分批处理大量实例

### 连接超时

- 单个连接测试超时时间：30秒
- 批量测试总超时时间：300秒

### 缓存策略

- 连接状态缓存：1小时
- 支持的数据库类型：永久缓存

## 🚀 未来扩展

### 计划功能

1. **连接池管理**：监控和管理数据库连接池
2. **健康检查**：定期自动检查连接状态
3. **性能监控**：连接响应时间和性能指标
4. **告警机制**：连接失败时发送通知

### 扩展点

1. **自定义连接器**：支持新的数据库类型
2. **插件系统**：支持第三方连接测试插件
3. **API版本控制**：支持API版本管理
4. **WebSocket支持**：实时连接状态更新

## 📝 注意事项

1. **向后兼容**：现有API继续工作，但建议迁移到新API
2. **错误处理**：新API提供更详细的错误信息
3. **性能提升**：统一的连接管理提供更好的性能
4. **维护性**：集中管理便于维护和扩展

## 🔍 故障排除

### 常见问题

1. **连接超时**：检查网络连接和数据库配置
2. **权限错误**：确认用户有相应的数据库访问权限
3. **参数错误**：使用验证API检查参数格式
4. **批量测试失败**：检查实例ID列表和网络状态

### 调试方法

1. 查看应用日志
2. 使用连接状态API检查实例状态
3. 使用参数验证API检查连接参数
4. 检查数据库服务状态

---

**更新时间**: 2025-09-30  
**版本**: v1.0.0  
**维护者**: 鲸落开发团队
