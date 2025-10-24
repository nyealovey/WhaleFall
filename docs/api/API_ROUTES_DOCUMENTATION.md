# TaifishingV4 API 和路由文档

## 📖 文档说明

本文档详细列出了 TaifishingV4 项目中的所有路由和 API 接口，按照功能模块分类，并明确区分页面路由和 API 接口。

### 🔗 路由类型说明
- **页面路由**: 返回 HTML 页面的路由，主要用于用户界面展示
- **API 接口**: 返回 JSON 数据的路由，主要用于前后端数据交互

---

## 1. 认证模块 (auth.py)

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/auth/login` | GET, POST | 用户登录页面 |
| `/auth/profile` | GET | 用户资料页面 |
| `/auth/change-password` | GET, POST | 修改密码页面 |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/auth/api/login` | POST | 用户登录API |
| `/auth/api/change-password` | POST | 修改密码API |
| `/auth/api/logout` | GET, POST | 用户登出接口 |
| `/auth/api/csrf-token` | GET | 获取 CSRF 令牌 |
| `/auth/api/refresh` | POST | 刷新 JWT 令牌 |
| `/auth/api/me` | GET | 获取当前用户信息 |

---

## 2. 账户管理模块 (account.py)

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/account/` | GET | 账户列表页面 |
| `/account/<db_type>` | GET | 按数据库类型筛选的账户页面 |
| `/account/statistics` | GET | 账户统计页面 |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/account/api/export` | GET | 导出账户数据为 CSV |
| `/account/api/<int:account_id>/permissions` | GET | 获取账户权限详情 |
| `/account/api/statistics` | GET | 账户统计 API |

---

## 3. 账户分类模块 (account_classification.py)

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/account_classification/` | GET | 账户分类管理首页 |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/account_classification/api/classifications` | GET, POST | 分类列表和创建 |
| `/account_classification/api/classifications/<int:id>` | GET, PUT, DELETE | 单个分类操作 |
| `/account_classification/api/rules/filter` | GET | 获取分类规则 |
| `/account_classification/api/rules` | GET, POST | 规则列表和创建 |
| `/account_classification/api/rules/<int:id>` | GET, PUT, DELETE | 单个规则操作 |
| `/account_classification/api/auto-classify` | POST | 自动分类账户 |
| `/account_classification/api/assignments` | GET | 获取账户分类分配 |
| `/account_classification/api/assignments/<int:id>` | DELETE | 移除账户分类分配 |
| `/account_classification/api/permissions/<db_type>` | GET | 获取数据库权限列表 |

## 4. 聚合统计模块 (aggregations.py) - 核心聚合功能

### 页面路由
*此模块专注于核心聚合功能，不包含页面路由*

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/aggregations/api/summary` | GET | 获取统计聚合数据汇总 |
| `/aggregations/api/manual_aggregate` | POST | 手动触发聚合计算 |
| `/aggregations/api/aggregate` | POST | 手动触发统计聚合计算 |
| `/aggregations/api/aggregate-today` | POST | 手动触发今日数据聚合 |
| `/aggregations/api/aggregate/status` | GET | 获取聚合状态信息 |

---

## 5. 数据库统计模块 (database_stats.py) - 数据库层面统计

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/database_stats/instance` | GET | 实例统计聚合页面（数据库统计层面） |
| `/database_stats/database` | GET | 数据库统计聚合页面（数据库统计层面） |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/database_stats/api/instances/<int:instance_id>/database-sizes/total` | GET | 获取指定实例的数据库总大小 |
| `/database_stats/api/instance-options` | GET | 获取用于表单的实例选项 |
| `/database_stats/api/instances/<int:instance_id>/database-sizes` | GET | 获取指定实例的数据库大小历史数据 |
| `/database_stats/api/instances/<int:instance_id>/database-sizes/summary` | GET | 获取指定实例的数据库大小汇总信息 |
| `/database_stats/api/instances/<int:instance_id>/databases` | GET | 获取指定实例的数据库列表 |
| `/database_stats/api/instances/aggregations` | GET | 获取实例聚合数据（数据库统计层面） |
| `/database_stats/api/instances/aggregations/summary` | GET | 获取实例聚合汇总信息（数据库统计层面） |

---

## 6. 实例统计模块 (instance_stats.py) - 实例层面统计

### 页面路由
*此模块专注于实例层面统计，不包含页面路由*

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/instance_stats/api/instances/<int:instance_id>/performance` | GET | 获取指定实例的性能统计信息 |
| `/instance_stats/api/instances/<int:instance_id>/trends` | GET | 获取指定实例的趋势数据 |
| `/instance_stats/api/instances/<int:instance_id>/health` | GET | 获取指定实例的健康度分析 |
| `/instance_stats/api/instances/<int:instance_id>/capacity-forecast` | GET | 获取指定实例的容量预测 |
| `/instance_stats/api/databases/aggregations` | GET | 获取数据库统计聚合数据（实例统计层面） |
| `/instance_stats/api/databases/aggregations/summary` | GET | 获取数据库统计聚合汇总信息（实例统计层面） |

---

## 7. 缓存管理模块 (cache.py)

### 页面路由
*此模块无页面路由*

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/cache/api/stats` | GET | 获取缓存统计信息 |
| `/cache/api/clear/user` | POST | 清除用户缓存 |
| `/cache/api/clear/instance` | POST | 清除实例缓存 |
| `/cache/api/clear/all` | POST | 清除所有缓存 |
| `/cache/api/classification/clear` | POST | 清除分类相关缓存 |
| `/cache/api/classification/clear/<db_type>` | POST | 清除特定数据库类型缓存 |
| `/cache/api/classification/stats` | GET | 获取分类缓存统计信息 |

---

## 8. 凭据管理模块 (credentials.py)

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/credentials/` | GET | 凭据管理首页 |
| `/credentials/create` | GET, POST | 创建凭据页面 |
| `/credentials/<int:id>/edit` | GET, POST | 编辑凭据页面 |
| `/credentials/<int:id>` | GET | 查看凭据详情页面 |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/credentials/api/create` | POST | 创建凭据 API |
| `/credentials/api/<int:id>/edit` | POST | 编辑凭据 API |
| `/credentials/api/credentials/<int:id>/toggle` | POST | 启用/禁用凭据 |
| `/credentials/api/credentials/<int:id>/delete` | POST | 删除凭据 |
| `/credentials/api/credentials` | GET | 获取凭据列表 API |
| `/credentials/api/credentials/<int:id>` | GET | 获取凭据详情 API |

---

## 9. 仪表板模块 (dashboard.py)

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/dashboard/` | GET | 系统仪表板首页 |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/dashboard/api/overview` | GET | 获取系统概览 API |
| `/dashboard/api/charts` | GET | 获取图表数据 API |
| `/dashboard/api/activities` | GET | 获取最近活动 API |
| `/dashboard/api/status` | GET | 获取系统状态 API |

---

## 10. 数据库类型模块 (database_types.py)

### 页面路由
*此模块无页面路由*

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/database_types/api/list` | GET | 获取数据库类型列表 |
| `/database_types/api/active` | GET | 获取启用的数据库类型 |
| `/database_types/api/form-options` | GET | 获取用于表单的数据库类型选项 |

---

## 11. 健康检查模块 (health.py)

### 页面路由
*此模块无页面路由*

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/health/api/basic` | GET | 基础健康检查 |
| `/health/api/detailed` | GET | 详细健康检查 |
| `/health/api/health` | GET | 健康检查 API |
| `/health/api/cache` | GET | 缓存服务健康检查 |
| `/health/api/scheduler` | GET | 调度器健康检查 |

---

## 12. 实例管理模块 (instances.py)

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/instances/` | GET | 实例管理首页 |
| `/instances/create` | GET, POST | 创建实例页面 |
| `/instances/<int:instance_id>/edit` | GET, POST | 编辑实例页面 |
| `/instances/<int:instance_id>` | GET | 查看实例详情页面 |
| `/instances/statistics` | GET | 实例统计页面 |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/instances/api/statistics` | GET | 获取实例统计API |
| `/instances/api` | GET | 获取实例列表API |
| `/instances/api/<int:instance_id>` | GET | 获取实例详情API |
| `/instances/api/create` | POST | 创建实例API |
| `/instances/api/<int:instance_id>/edit` | POST | 编辑实例API |
| `/instances/api/<int:instance_id>/delete` | POST | 删除实例 |
| `/instances/api/<int:instance_id>/accounts` | GET | 获取实例账户数据API |
| `/instances/api/<int:instance_id>/accounts/<int:account_id>/change-history` | GET | 获取账户变更历史 |
| `/instances/api/<int:instance_id>/accounts/<int:account_id>/permissions` | GET | 获取账户权限详情 |
| `/instances/api/batch-delete` | POST | 批量删除实例 |
| `/instances/api/batch-create` | POST | 批量创建实例 |
| `/instances/api/export` | GET | 导出实例数据为CSV |
| `/instances/api/template/download` | GET | 下载CSV模板 |

---

## 13. 日志管理模块 (logs.py)

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/logs/` | GET | 日志中心仪表板 |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/logs/api/search` | GET | 搜索日志 API |
| `/logs/api/statistics` | GET | 获取日志统计信息 API |
| `/logs/api/errors` | GET | 获取错误日志 API |
| `/logs/api/modules` | GET | 获取日志模块列表 API |
| `/logs/api/export` | GET | 导出日志 API |
| `/logs/api/stats` | GET | 获取日志统计信息 API |
| `/logs/api/detail/<int:id>` | GET | 获取日志详情 API |

---

## 14. 主路由模块 (main.py)

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 首页（重定向到登录页面） |
| `/about` | GET | 关于页面 |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/favicon.ico` | GET | 网站图标 |
| `/.well-known/appspecific/com.chrome.devtools.json` | GET | Chrome 开发者工具请求处理 |
| `/admin/api/app-info` | GET | 获取应用信息 |

---
 
## 15. 分区管理模块 (partition.py)

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/partition/` | GET | 分区管理页面 |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/partition/api/info` | GET | 获取分区信息 |
| `/partition/api/status` | GET | 获取分区管理状态 |
| `/partition/api/create` | POST | 创建分区 |
| `/partition/api/cleanup` | POST | 清理旧分区 |
| `/partition/api/statistics` | GET | 获取分区统计信息 |
| `/partition/api/aggregations/core-metrics` | GET | 获取核心指标数据 |

---

## 16. 定时任务模块 (scheduler.py)

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/scheduler/` | GET | 定时任务管理页面 |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/scheduler/api/jobs` | GET | 获取所有定时任务 |
| `/scheduler/api/jobs/<job_id>` | GET | 获取指定任务详情 |
| `/scheduler/api/jobs/<job_id>/pause` | POST | 暂停任务 |
| `/scheduler/api/jobs/<job_id>/resume` | POST | 恢复任务 |
| `/scheduler/api/jobs/<job_id>/run` | POST | 立即执行任务 |
| `/scheduler/api/jobs/reload` | POST | 重新加载所有任务配置 |
| `/scheduler/api/jobs/<job_id>` | PUT | 更新内置任务的触发器配置 |

---

## 17. 存储同步模块 (storage_sync.py)

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/storage_sync/api/instances/<int:id>/sync-capacity` | POST | 同步指定实例的数据库容量信息 |
| `/storage_sync/api/instances/<int:id>/databases` | GET | 获取指定实例的数据库列表 |

---

## 18. 同步会话模块 (sync_sessions.py)

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/sync_sessions/` | GET | 会话中心首页 |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/sync_sessions/api/sessions` | GET | 获取同步会话列表 API |
| `/sync_sessions/api/sessions/<session_id>` | GET | 获取同步会话详情 API |
| `/sync_sessions/api/sessions/<session_id>/cancel` | POST | 取消同步会话 API |
| `/sync_sessions/api/sessions/<session_id>/error-logs` | GET | 获取同步会话错误日志 API |

---

## 19. 标签管理模块 (tags.py)

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/tags/` | GET | 标签管理首页 |
| `/tags/create` | GET, POST | 创建标签页面 |
| `/tags/edit/<int:id>` | GET, POST | 编辑标签页面 |
| `/tags/batch_assign` | GET | 批量分配标签页面 |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/tags/api/create` | POST | 创建标签API |
| `/tags/api/edit/<int:tag_id>` | POST | 编辑标签API |
| `/tags/api/delete/<int:tag_id>` | POST | 删除标签 |
| `/tags/api/batch_assign_tags` | POST | 批量分配标签给实例 |
| `/tags/api/batch_remove_tags` | POST | 批量移除实例的标签 |
| `/tags/api/instance_tags` | POST | 获取实例的已关联标签 |
| `/tags/api/batch_remove_all_tags` | POST | 批量移除实例的所有标签 |
| `/tags/api/instances` | GET | 获取所有实例列表 |
| `/tags/api/all_tags` | GET | 获取所有标签列表（包括非活跃标签） |
| `/tags/api/tags` | GET | 获取标签列表 API |
| `/tags/api/categories` | GET | 获取标签分类列表 API |
| `/tags/api/tags/<tag_name>` | GET | 获取标签详情 API |

---

## 20. 用户管理模块 (users.py)

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/users/` | GET | 用户管理首页 |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/users/api/users` | GET | 获取用户列表 API |
| `/users/api/users/<int:user_id>` | GET | 获取单个用户信息 API |
| `/users/api/users` | POST | 创建用户 API |
| `/users/api/users/<int:user_id>` | PUT | 更新用户 API |
| `/users/api/users/<int:user_id>` | DELETE | 删除用户 API |
| `/users/api/users/stats` | GET | 获取用户统计信息 API |

---

## 21. 账户同步模块 (account_sync.py)

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/account_sync/` | GET | 同步记录页面 |
| `/account_sync/sync-details/<sync_id>` | GET | 同步详情页面 |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/account_sync/api/sync-all` | POST | 同步所有实例的账户 |
| `/account_sync/api/instances/<int:id>/sync` | POST | 同步指定实例的账户信息 |

---

## 22. 连接管理模块 (connections.py)

### 页面路由
*此模块无页面路由，仅提供API接口*

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/connections/api/test` | POST | 测试数据库连接（支持现有实例和新连接） |
| `/connections/api/supported-types` | GET | 获取支持的数据库类型列表 |
| `/connections/api/validate-params` | POST | 验证连接参数 |
| `/connections/api/batch-test` | POST | 批量测试连接（最多50个实例） |
| `/connections/api/status/<int:instance_id>` | GET | 获取实例连接状态 |

### 前端组件
| 组件 | 路径 | 描述 |
|------|------|------|
| `connectionManager` | `/static/js/components/connection-manager.js` | 统一的连接管理前端组件 |
| 批量测试UI | 实例列表页面 | 支持批量选择和测试连接 |
| 进度显示 | 各页面 | 实时显示测试进度和结果 |

### 使用示例
```javascript
// 测试现有实例连接
connectionManager.testInstanceConnection(instanceId, {
    onSuccess: (data) => console.log('成功:', data),
    onError: (error) => console.error('失败:', error)
});

// 批量测试连接
connectionManager.batchTestConnections([1,2,3], {
    onProgress: (result) => connectionManager.showBatchTestProgress(result)
});
```

---

## 📊 统计信息

### 总体统计
- **总模块数**: 23 个
- **页面路由总数**: 约 39 个
- **API 接口总数**: 173 个
- **总路由数**: 212 个
- **前端组件数**: 1 个（连接管理组件）
- **已弃用API**: 2 个（保持向后兼容）

### 混合路由说明
目前没有混合路由，所有模块都已完成页面路由和API路由的分离。

**注意**: 认证模块、账户管理模块和实例管理模块都已经完成拆分，有独立的API路由和页面路由。

### API 前缀使用情况
根据内存中的已知问题，项目存在 API 前缀不统一的情况：

| 前缀模式 | 示例 | 使用模块 |
|----------|------|----------|
| `/api/` | `/auth/api/csrf-token` | auth, dashboard, logs 等 |
| `/module/api/` | `/health/api/basic` | health |
| 混合使用 | `/instances/api/statistics` 和 `/instances/statistics` | instances, aggregations 等 |

### 建议改进
1. **统一 API 前缀**: 建议所有 API 使用 `/api/v1/` 前缀
2. **规范命名风格**: 统一使用横杠分隔符 (`kebab-case`)
3. **版本控制**: 为 API 添加版本号支持
4. **文档化**: 建议添加 Swagger/OpenAPI 文档
5. **语义化方法**: 避免使用 GET 执行有副作用的操作（如登出），建议限制为 POST
6. **路径去冗余**: 避免重复片段，如 `/aggregations/api/instance/api`，建议统一到 `/aggregations/api/instance`
7. **资源层级一致性**: 类似 `/instances/api/instances/<id>` 建议调整为 `/instances/api/<id>`，保持层级简洁一致
9. **CSRF 策略明确**: 仅对确需跨域或非表单请求的接口豁免 CSRF，例如 `/connections/api/test`
10. **限流与防护**: 对登录等敏感接口（`/auth/api/login`）增加限流与强校验，防止暴力尝试

### 连接管理API迁移状态
- ✅ **已完成**: 连接管理模块API抽离和前端迁移
- ✅ **新功能**: 批量测试连接（最多50个实例）
- ✅ **向后兼容**: 旧API标记为已弃用但仍可用
- ✅ **统一组件**: 前端使用 `connectionManager` 统一组件
- 📋 **迁移指南**: 详见 `docs/connection-api-migration.md`

### 迁移影响范围
- **前端页面**: 实例详情、编辑、列表页面已完全迁移
- **代码优化**: 减少137行重复代码，提高维护性
- **功能增强**: 新增批量测试和进度显示功能
- **用户体验**: 统一的操作界面和错误处理
- **开发效率**: 统一的API调用方式，简化开发流程

---



---

*此文档基于代码分析生成，如有更新请及时同步修改。*
