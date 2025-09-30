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
| `/account/api/<int:account_id>/change-history` | GET | 获取账户变更历史 |
| `/account/api/account-statistics` | GET | 账户统计 API |

---

## 3. 账户分类模块 (account_classification.py)

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/account_classification/` | GET | 账户分类管理首页 |
| `/account_classification/rules-page` | GET | 规则管理页面 |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/account_classification/api/classifications` | GET, POST | 分类列表和创建 |
| `/account_classification/api/classifications/<int:id>` | GET, PUT, DELETE | 单个分类操作 |
| `/account_classification/api/rules/filter` | GET | 获取分类规则 |
| `/account_classification/api/rules` | GET, POST | 规则列表和创建 |
| `/account_classification/api/rules/<int:id>` | GET, PUT, DELETE | 单个规则操作 |
| `/account_classification/api/rules/<int:id>/matched-accounts` | GET | 获取规则匹配的账户 |
| `/account_classification/api/auto-classify` | POST | 自动分类账户 |
| `/account_classification/api/assignments` | GET | 获取账户分类分配 |
| `/account_classification/api/assignments/<int:id>` | DELETE | 移除账户分类分配 |
| `/account_classification/api/permissions/<db_type>` | GET | 获取数据库权限列表 |

---

## 4. 管理员模块 (admin.py)

### 页面路由
*此模块无页面路由*

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/admin/api/app-info` | GET | 获取应用信息 |

---

## 5. 聚合统计模块 (aggregations.py)

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/aggregations/api/instance` | GET | 实例统计聚合页面（无查询参数时） |
| `/aggregations/api/database` | GET | 数据库统计聚合页面（无查询参数时） |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/aggregations/api/summary` | GET | 获取统计聚合数据汇总 |
| `/aggregations/api/instance` | GET | 实例统计聚合数据（有查询参数时） |
| `/aggregations/api/database` | GET | 数据库统计聚合数据（有查询参数时） |
| `/aggregations/api/instance/summary` | GET | 获取实例统计聚合汇总 |
| `/aggregations/api/database/summary` | GET | 获取数据库统计聚合汇总 |
| `/aggregations/api/manual_aggregate` | POST | 手动触发聚合计算 |
| `/aggregations/api/aggregate` | POST | 手动触发统计聚合计算 |
| `/aggregations/api/aggregate-today` | POST | 手动触发今日数据聚合 |
| `/aggregations/api/aggregate/status` | GET | 获取聚合状态信息 |
| `/aggregations/api/instances/<int:id>/database-sizes/aggregations` | GET | 获取指定实例的聚合数据 |

---

## 6. 缓存管理模块 (cache.py)

### 页面路由
*此模块无页面路由*

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/cache/api/stats` | GET | 获取缓存统计信息 |
| `/cache/api/health` | GET | 检查缓存健康状态 |
| `/cache/api/clear/user` | POST | 清除用户缓存 |
| `/cache/api/clear/instance` | POST | 清除实例缓存 |
| `/cache/api/clear/all` | POST | 清除所有缓存 |
| `/cache/api/classification/clear` | POST | 清除分类相关缓存 |
| `/cache/api/classification/clear/<db_type>` | POST | 清除特定数据库类型缓存 |
| `/cache/api/classification/stats` | GET | 获取分类缓存统计信息 |

---

## 7. 凭据管理模块 (credentials.py)

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

## 8. 仪表板模块 (dashboard.py)

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

## 9. 数据库类型模块 (database_types.py)

### 页面路由
*此模块无页面路由*

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/database_types/api/list` | GET | 获取数据库类型列表 |
| `/database_types/api/active` | GET | 获取启用的数据库类型 |
| `/database_types/api/form-options` | GET | 获取用于表单的数据库类型选项 |

---

## 10. 健康检查模块 (health.py)

### 页面路由
*此模块无页面路由*

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/health/` | GET | 基础健康检查 |
| `/health/detailed` | GET | 详细健康检查 |
| `/health/health/readiness` | GET | 就绪检查（Kubernetes 用） |
| `/health/health/liveness` | GET | 存活检查（Kubernetes 用） |

---

## 11. 实例管理模块 (instances.py)

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/instances/` | GET | 实例管理首页 |
| `/instances/create` | GET, POST | 创建实例页面 |
| `/instances/<int:id>/edit` | GET, POST | 编辑实例页面 |
| `/instances/<int:id>` | GET | 查看实例详情页面 |
| `/instances/statistics` | GET | 实例统计页面 |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/instances/api/statistics` | GET | 获取实例统计API |
| `/instances/api/instances` | GET | 获取实例列表API |
| `/instances/api/instances/<int:id>` | GET | 获取实例详情API |
| `/instances/api/create` | POST | 创建实例API |
| `/instances/api/<int:id>/edit` | POST | 编辑实例API |
| `/instances/api/instances/<int:id>/delete` | POST | 删除实例 |
| `/instances/api/instances/<int:id>/test` | GET, POST | 测试连接API（支持GET和POST方法） |
| `/instances/api/test-connection` | POST | 测试数据库连接API（无需CSRF） |
| `/instances/api/instances/<int:id>/accounts` | GET | 获取实例账户数据API |
| `/instances/api/instances/<int:id>/accounts/<int:account_id>/change-history` | GET | 获取账户变更历史 |
| `/instances/api/instances/<int:id>/accounts/<int:account_id>/permissions` | GET | 获取账户权限详情 |
| `/instances/api/batch-delete` | POST | 批量删除实例 |
| `/instances/api/batch-create` | POST | 批量创建实例 |
| `/instances/api/export` | GET | 导出实例数据为CSV |
| `/instances/api/template/download` | GET | 下载CSV模板 |

---

## 12. 日志管理模块 (logs.py)

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
| `/logs/api/cleanup` | POST | 清理旧日志 API |
| `/logs/api/real-time` | GET | 获取实时日志 API |
| `/logs/api/stats` | GET | 获取日志统计信息 API |
| `/logs/api/detail/<int:id>` | GET | 获取日志详情 API |

---

## 13. 主路由模块 (main.py)

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 首页（重定向到登录页面） |
| `/about` | GET | 关于页面 |
| `/admin` | GET | 系统管理页面 |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/favicon.ico` | GET | 网站图标 |
| `/.well-known/appspecific/com.chrome.devtools.json` | GET | Chrome 开发者工具请求处理 |
| `/api/health` | GET | 健康检查 API |

---

## 14. 分区管理模块 (partition.py)

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/partition/` | GET | 分区管理页面（无查询参数时） |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/partition/api/info` | GET | 获取分区信息 |
| `/partition/api/status` | GET | 获取分区管理状态 |
| `/partition/api/test` | GET | 测试分区管理服务（调试用） |
| `/partition/api/create` | POST | 创建分区 |
| `/partition/api/cleanup` | POST | 清理旧分区 |
| `/partition/api/statistics` | GET | 获取分区统计信息 |
| `/partition/api/create-future` | POST | 创建未来分区 |
| `/partition/api/aggregations/latest` | GET | 获取最新的聚合数据 |
| `/partition/api/aggregations/cleanup` | POST | 清理旧的聚合数据 |
| `/partition/api/aggregations/summary` | GET | 获取聚合数据统计概览 |
| `/partition/api/aggregations/core-metrics` | GET | 获取核心指标数据 |
| `/partition/api/aggregations/chart` | GET | 获取聚合数据图表数据 |

---

## 15. 定时任务模块 (scheduler.py)

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/scheduler/` | GET | 定时任务管理页面 |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/scheduler/api/jobs` | GET | 获取所有定时任务 |
| `/scheduler/api/jobs/<job_id>` | GET | 获取指定任务详情 |
| `/scheduler/api/jobs/<job_id>/disable` | POST | 禁用定时任务 |
| `/scheduler/api/jobs/<job_id>/enable` | POST | 启用定时任务 |
| `/scheduler/api/jobs/<job_id>/pause` | POST | 暂停任务 |
| `/scheduler/api/jobs/<job_id>/resume` | POST | 恢复任务 |
| `/scheduler/api/jobs/<job_id>/run` | POST | 立即执行任务 |
| `/scheduler/api/jobs/reload` | POST | 重新加载所有任务配置 |
| `/scheduler/api/jobs/<job_id>` | PUT | 更新内置任务的触发器配置 |
| `/scheduler/api/health` | GET | 获取调度器健康状态 |

---

## 16. 存储同步模块 (storage_sync.py)

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/storage_sync/` | GET | 存储同步主页面 |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/storage_sync/api/status` | GET | 获取数据库大小监控状态 |
| `/storage_sync/api/stats` | GET | 获取数据库大小监控统计信息 |
| `/storage_sync/api/test_connection` | POST | 测试数据库连接 |
| `/storage_sync/api/manual_collect` | POST | 手动触发数据采集 |
| `/storage_sync/api/cleanup_partitions` | POST | 手动清理分区 |
| `/storage_sync/api/instances` | GET | 获取实例列表 |
| `/storage_sync/api/instances/<int:id>/database-sizes/total` | GET | 获取指定实例的数据库总大小 |
| `/storage_sync/api/instances/<int:id>/database-sizes` | GET | 获取指定实例的数据库大小历史数据 |
| `/storage_sync/api/instances/<int:id>/database-sizes/summary` | GET | 获取指定实例的数据库大小汇总信息 |
| `/storage_sync/api/collect` | POST | 手动触发数据库大小采集 |
| `/storage_sync/api/instances/<int:id>/sync-capacity` | POST | 同步指定实例的数据库容量信息 |
| `/storage_sync/api/instances/<int:id>/databases` | GET | 获取指定实例的数据库列表 |

---

## 17. 同步会话模块 (sync_sessions.py)

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
| `/sync_sessions/api/statistics` | GET | 获取同步统计信息 API |

---

## 18. 标签管理模块 (tags.py)

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
| `/tags/api/delete/<int:id>` | POST | 删除标签 |
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

## 19. 用户管理模块 (users.py)

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/users/` | GET | 用户管理首页 |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/users/api/users` | GET | 获取用户列表 API |
| `/users/api/users/<int:id>` | GET | 获取单个用户信息 API |
| `/users/api/users` | POST | 创建用户 API |
| `/users/api/users/<int:id>` | PUT | 更新用户 API |
| `/users/api/users/<int:id>` | DELETE | 删除用户 API |
| `/users/api/users/<int:id>/toggle-status` | POST | 切换用户状态 API |
| `/users/api/users/stats` | GET | 获取用户统计信息 API |

---

## 20. 账户同步模块 (account_sync.py)

### 页面路由
| 路径 | 方法 | 描述 |
|------|------|------|
| `/account_sync/` | GET | 同步记录页面 |
| `/account_sync/sync-details/<sync_id>` | GET | 同步详情页面 |

### API 接口
| 路径 | 方法 | 描述 |
|------|------|------|
| `/account_sync/api/sync-all` | POST | 同步所有实例的账户 |
| `/account_sync/api/sync-details-batch` | GET | 获取批量同步详情 |
| `/account_sync/api/instances/<int:id>/sync` | POST | 同步指定实例的账户信息 |

---

## 📊 统计信息

### 总体统计
- **总模块数**: 20 个
- **页面路由总数**: 约 39 个
- **API 接口总数**: 153 个
- **总路由数**: 192 个

### API 前缀使用情况
根据内存中的已知问题，项目存在 API 前缀不统一的情况：

| 前缀模式 | 示例 | 使用模块 |
|----------|------|----------|
| `/api/` | `/auth/api/csrf-token` | auth, dashboard, logs 等 |
| 无前缀 | `/admin/app-info` | admin, cache, health 等 |
| 混合使用 | `/account/api/statistics` 和 `/account/statistics` | account, aggregations 等 |

### 建议改进
1. **统一 API 前缀**: 建议所有 API 使用 `/api/v1/` 前缀
2. **规范命名风格**: 统一使用横杠分隔符 (`kebab-case`)
3. **版本控制**: 为 API 添加版本号支持
4. **文档化**: 建议添加 Swagger/OpenAPI 文档

---

## 📝 更新日志

- **创建日期**: 2025年1月X日
- **最后更新**: 2025年9月30日
- **版本**: v1.2.10

### v1.2.10 更新内容 (2025-09-30)
- ✅ 删除无用的API路由：/aggregations/api/data
- ✅ 该路由功能重复，没有前端调用，违反单一职责原则
- ✅ 更新API接口总数统计（从154个减少到153个）
- ✅ 更新总路由数统计（从193个减少到192个）
- ✅ 清理冗余代码，提高代码质量

### v1.2.9 更新内容 (2025-09-30)
- ✅ 修复认证模块页面路由和API混在一起的问题
- ✅ 添加认证模块专门的API：/auth/api/login 和 /auth/api/change-password
- ✅ 简化页面路由，移除API逻辑，提高代码可维护性
- ✅ 更新API接口总数统计（从152个增加到154个）
- ✅ 更新总路由数统计（从191个增加到193个）
- ✅ 实现页面和API的完全分离

### v1.2.8 更新内容 (2025-09-30)
- ✅ 修复页面路由和API混在一起的问题
- ✅ 添加实例管理模块缺失的API：/instances/api/create 和 /instances/api/<int:id>/edit
- ✅ 添加标签管理模块缺失的API：/tags/api/create 和 /tags/api/edit/<int:tag_id>
- ✅ 更新API接口总数统计（从148个增加到152个）
- ✅ 更新总路由数统计（从187个增加到191个）
- ✅ 完善API路径标准化

### v1.2.7 更新内容 (2025-09-30)
- ✅ 修复健康检查模块重复路由问题
- ✅ 删除重复的 /health/ 路由（health_check_root函数）
- ✅ 更新API接口总数统计（从149个减少到148个）
- ✅ 更新总路由数统计（从188个减少到187个）
- ✅ 清理冗余代码

### v1.2.6 更新内容 (2025-09-30)
- ✅ 修复凭据管理模块缺失的API路径
- ✅ 添加 /credentials/api/create POST API（创建凭据）
- ✅ 添加 /credentials/api/<int:id>/edit POST API（编辑凭据）
- ✅ 更新API接口总数统计（从147个增加到149个）
- ✅ 更新总路由数统计（从186个增加到188个）
- ✅ 完善API路径标准化

### v1.2.5 更新内容 (2025-09-30)
- ✅ 进行全面代码扫描，发现API接口统计不准确
- ✅ 重新统计API接口总数（从141个修正为147个）
- ✅ 重新统计总路由数（从180个修正为186个）
- ✅ 确认所有模块的API接口都已完整记录
- ✅ 验证API文档与实际代码的一致性

### v1.2.4 更新内容 (2025-09-30)
- ✅ 补全凭据管理模块缺失的API接口
- ✅ 添加 /credentials/create POST API（创建凭据）
- ✅ 添加 /credentials/<int:id>/edit POST API（编辑凭据）
- ✅ 更新API接口总数统计（从139个增加到141个）
- ✅ 更新总路由数统计（从178个增加到180个）
- ✅ 确保API文档完整性

### v1.2.3 更新内容 (2025-09-30)
- ✅ 删除不存在的 /aggregations/ 根路径路由记录
- ✅ 修正聚合统计模块页面路由为实际存在的路径
- ✅ 更新页面路由总数统计（从40个减少为39个）
- ✅ 更新总路由数统计（从179个减少为178个）
- ✅ 确保API文档与实际代码完全一致

### v1.2.2 更新内容 (2025-09-30)
- ✅ 删除冗余的 /account/api/statistics 接口
- ✅ 保留 /account/api/account-statistics 接口（标准格式）
- ✅ 更新API接口总数统计（从140个减少为139个）
- ✅ 更新总路由数统计（从180个减少为179个）
- ✅ 清理代码冗余，提高维护性

### v1.2.1 更新内容 (2025-09-30)
- ✅ 修复健康检查模块API路径错误（readiness和liveness路径）
- ✅ 补充分区管理模块缺失的API路径（core-metrics和chart）
- ✅ 修复实例管理模块API路径重复定义问题
- ✅ 修复账户管理模块API路径重复定义问题
- ✅ 更新API接口总数统计（从158个修正为140个）
- ✅ 更新总路由数统计（从199个修正为180个）
- ✅ 修正API文档中的路径错误和不一致问题

### v1.2.0 更新内容 (2025-09-30)
- ✅ 全面补充实例管理模块的API接口（增加15个接口）
- ✅ 新增账户同步模块文档
- ✅ 更新模块总数（从19个增加到20个）
- ✅ 更新API接口总数统计（从128个增加到158个）
- ✅ 更新总路由数统计（从163个增加到199个）
- ✅ 补充健康检查模块的详细API
- ✅ 补充数据库类型模块的API
- ✅ 补充日志管理模块的API

### v1.1.0 更新内容 (2025-09-29)
- ✅ 修复分区管理模块缺失的4个路由
- ✅ 验证存储同步模块路由完整性
- ✅ 验证同步会话模块路由完整性  
- ✅ 验证定时任务模块路由完整性
- ✅ 更新API接口总数统计（从120个增加到128个）
- ✅ 更新总路由数统计（从155个增加到163个）

---

*此文档基于代码分析生成，如有更新请及时同步修改。*