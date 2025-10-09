# 健康检查功能技术文档

## 1. 功能概述

### 1.1 模块职责
- 提供系统健康状态监控和检查功能，包括数据库、缓存、系统资源等组件的健康检查。
- 实现基础健康检查、详细健康检查、存活检查和就绪检查等多种检查模式。
- 支持容器化部署的Kubernetes健康检查协议。
- 提供系统状态API接口，供前端和管理界面调用。

### 1.2 代码定位
- 路由：`app/routes/health.py`（健康检查专用路由）
- 主路由：`app/routes/main.py`（系统管理相关健康检查API）
- 前端：`app/templates/admin/management.html`、`app/static/js/pages/admin/management.js`
- 工具：`app/utils/api_response.py`、`app/utils/structlog_config.py`

## 2. 架构设计

### 2.1 模块关系
```
┌─────────────────────────────┐
│ 前端管理界面                 │
│  - 系统状态监控            │
│  - 健康状态指示器          │
│  - 实时状态更新            │
└───────▲───────────┬──────┘
        │AJAX        │
┌───────┴───────────▼──────┐
│ Flask 路由 (health.py)    │
│  - /health               │
│  - /health/detailed      │
│  - /health/readiness     │
│  - /health/liveness      │
└───────▲───────────┬──────┘
        │检查函数    │
┌───────┴───────────▼──────┐
│ 健康检查服务              │
│  - check_database_health │
│  - check_cache_health    │
│  - check_system_health   │
└────────────────────────────┘
```

### 2.2 权限控制
- 健康检查接口无需认证，供监控系统调用。
- 系统管理页面需要 `@login_required` 和 `@admin_required`。

## 3. 路由实现（`health.py`）

### 3.1 基础健康检查
- `GET /health`（19-30）：
  - 提供基础健康检查接口。
  - 返回服务状态、时间戳和版本信息。
  - 使用 `APIResponse.success()` 统一响应格式。

- `GET /health/`（33-44）：
  - 健康检查根路由，兼容Nginx配置。
  - 与基础健康检查功能相同。

### 3.2 详细健康检查
- `GET /health/detailed`（47-90）：
  - 执行全面的系统健康检查。
  - 检查数据库、缓存、系统资源三个组件。
  - 综合评估整体健康状态。
  - 返回详细的组件状态信息。

### 3.3 容器健康检查
- `GET /health/readiness`（167-181）：
  - Kubernetes就绪检查。
  - 检查关键服务（数据库、缓存）是否就绪。
  - 返回503状态码表示服务未就绪。

- `GET /health/liveness`（184-193）：
  - Kubernetes存活检查。
  - 简单的应用存活状态检查。
  - 用于容器重启判断。

## 4. 健康检查服务

### 4.1 数据库健康检查
- `check_database_health()`（93-109）：
  - 执行 `SELECT 1` 查询测试数据库连接。
  - 测量响应时间（毫秒）。
  - 返回连接状态和响应时间。

### 4.2 缓存健康检查
- `check_cache_health()`（112-128）：
  - 使用 `cache.set()` 和 `cache.get()` 测试缓存连接。
  - 测量缓存操作响应时间。
  - 验证缓存功能是否正常。

### 4.3 系统资源健康检查
- `check_system_health()`（131-164）：
  - 使用 `psutil` 获取CPU、内存、磁盘使用率。
  - 设置健康阈值：CPU < 90%、内存 < 90%、磁盘 < 90%。
  - 返回详细的资源使用情况。

## 5. 系统管理集成（`main.py`）

### 5.1 健康检查API
- `GET /api/health`（51-102）：
  - 系统管理页面的健康检查接口。
  - 检查数据库和Redis连接状态。
  - 返回系统运行时间和整体状态。
  - 记录API调用日志。

### 5.2 系统运行时间
- `get_system_uptime()`（105-122）：
  - 计算系统运行时间。
  - 支持多种时间格式输出。
  - 处理异常情况。

## 6. 前端实现

### 6.1 系统管理页面（`management.html`）
- 系统概览卡片：显示用户总数、数据库实例、定时任务、操作日志。
- 系统状态监控：显示数据库、Redis、应用状态。
- 实时状态指示器：使用颜色和图标表示健康状态。

### 6.2 前端JavaScript（`management.js`）
- `loadSystemOverview()`（19-29）：加载系统概览数据。
- `updateSystemOverview()`（32-47）：更新概览数据显示。
- `checkSystemStatus()`（50-60）：检查系统状态。
- `updateSystemStatus()`（63-87）：更新状态显示。
- `updateStatusIndicator()`（100-120）：更新状态指示器。

## 7. 响应格式

### 7.1 基础健康检查响应
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": 1703123456.789,
    "version": "1.0.7"
  },
  "message": "服务运行正常"
}
```

### 7.2 详细健康检查响应
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": 1703123456.789,
    "version": "1.1.1",
    "components": {
      "database": {
        "healthy": true,
        "response_time_ms": 15.23,
        "status": "connected"
      },
      "cache": {
        "healthy": true,
        "response_time_ms": 2.45,
        "status": "connected"
      },
      "system": {
        "healthy": true,
        "cpu_percent": 25.6,
        "memory_percent": 45.2,
        "disk_percent": 67.8,
        "status": "healthy"
      }
    }
  },
  "message": "详细健康检查完成"
}
```

## 8. 错误处理

### 8.1 后端错误处理
- 所有健康检查函数都有异常处理。
- 使用 `get_system_logger()` 记录错误日志。
- 返回统一的错误响应格式。

### 8.2 前端错误处理
- AJAX请求失败时显示错误提示。
- 状态检查失败时显示错误状态。
- 使用 `showError()` 显示用户友好的错误信息。

## 9. 性能优化

### 9.1 检查优化
- 使用 `psutil.cpu_percent(interval=1)` 获取准确的CPU使用率。
- 缓存操作使用短超时时间（10秒）。
- 数据库查询使用简单的 `SELECT 1`。

### 9.2 响应优化
- 健康检查接口无需认证，提高响应速度。
- 使用 `APIResponse` 统一响应格式。
- 记录API调用性能指标。

## 10. 监控集成

### 10.1 容器健康检查
- 支持Kubernetes的存活检查和就绪检查。
- 提供标准的HTTP状态码。
- 支持容器编排系统的健康检查协议。

### 10.2 系统监控
- 集成到系统管理页面。
- 提供实时状态监控。
- 支持手动刷新和自动更新。

## 11. 配置管理

### 11.1 健康阈值配置
- CPU使用率阈值：90%
- 内存使用率阈值：90%
- 磁盘使用率阈值：90%
- 缓存超时时间：10秒

### 11.2 日志配置
- 使用结构化日志记录健康检查事件。
- 记录错误详情和堆栈跟踪。
- 支持不同日志级别。

## 12. 测试建议

### 12.1 功能测试
- 各组件健康检查的准确性。
- 不同健康状态的响应格式。
- 容器健康检查的兼容性。

### 12.2 性能测试
- 健康检查接口的响应时间。
- 并发健康检查的稳定性。
- 系统资源检查的准确性。

## 13. 后续优化方向

### 13.1 功能增强
- 添加更多系统组件的健康检查。
- 实现健康状态历史记录。
- 添加健康状态告警机制。

### 13.2 监控增强
- 集成Prometheus指标。
- 添加健康状态趋势分析。
- 实现健康状态仪表板。

### 13.3 容器化增强
- 优化Kubernetes健康检查。
- 添加健康状态探针。
- 实现健康状态自动恢复。
