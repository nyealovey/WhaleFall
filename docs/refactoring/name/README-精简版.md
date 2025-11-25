# 命名规范重构文档（2025-11-18 再次扫描版）

> 基于实际代码扫描，识别出 **约 60 项命名问题**

## 📊 问题统计

| 类别 | 数量 | 状态 |
|-----|------|------|
| 后端文件命名 | 16 个 | 🔴 待重构 |
| 前端目录/文件 | 0 个 | ✅ 已完成（已采用 kebab-case） |
| 函数命名 | 35+ 个 | 🔴 待重构（含新增函数） |
| **总计** | **约 60 项** | - |

**预计工作量**: 3-5 天  
**风险等级**: 低-中

## ✅ 已完成的重构

- 前端目录已使用 kebab-case（`capacity-stats/`, `classification-rules/`）
- 前端文件已使用 kebab-case（`database-aggregations.js`, `tag-selector.css` 等）

---

## 🚀 快速开始

### 自动化执行（推荐）

```bash
# 1. 预览操作
./scripts/refactor_naming.sh --dry-run

# 2. 执行重构（自动运行测试并生成报告）
./scripts/refactor_naming.sh

# 3. 查看报告
ls docs/refactoring/重构执行报告_*.md | tail -n 1
```

### 手动执行

参考下方命令模板，按"目录 → 文件 → 引用"顺序执行。

---

## 📋 重构清单

### 后端文件（16 个）

```bash
# 路由文件（2 个）
app/routes/database_aggr.py → database_aggregations.py
app/routes/instance_aggr.py → instance_aggregations.py

# 视图文件（7 个）
app/views/account_classification_form_view.py → classification_forms.py
app/views/change_password_form_view.py → password_forms.py
app/views/credential_form_view.py → credential_forms.py
app/views/instance_form_view.py → instance_forms.py
app/views/scheduler_job_form_view.py → scheduler_forms.py
app/views/tag_form_view.py → tag_forms.py
app/views/user_form_view.py → user_forms.py

# 服务文件（9 个）
app/services/form_service/change_password_form_service.py → password_service.py
app/services/form_service/classification_form_service.py → classification_service.py
app/services/form_service/classification_rule_form_service.py → classification_rule_service.py
app/services/form_service/credentials_form_service.py → credential_service.py
app/services/form_service/instances_form_service.py → instance_service.py
app/services/form_service/resource_form_service.py → resource_service.py
app/services/form_service/scheduler_job_form_service.py → scheduler_job_service.py
app/services/form_service/tags_form_service.py → tag_service.py
app/services/form_service/users_form_service.py → user_service.py
```

### 函数重命名（再扫描结果）

> 以下列表取自 `./scripts/refactor_naming.sh --dry-run` 的最新输出，请按模块依次修复并随手运行脚本确认。

#### 1. `api_` 前缀（共 26 个）

- `routes/users.py`：`api_get_users / api_get_user / api_create_user / api_update_user / api_delete_user / api_get_stats`
- `routes/instance.py`：`api_detail / api_get_accounts`
- `routes/credentials.py`：`api_list / api_detail`
- `routes/tags.py`：`api_tags / api_categories / api_tag_detail / api_tag_detail_by_id`
- `routes/tags_batch.py`：`api_instance_tags / api_instances / api_all_tags`
- `routes/sync_sessions.py`：`api_get_session_detail / api_cancel_session / api_get_error_logs`
- `routes/dashboard.py`：`api_overview / api_charts / api_activities / api_status`
- `routes/health.py`：`api_health / api_cache_health`
- `routes/instance_statistics.py`：`api_statistics`

统一规则：改为 REST 风格动词，如 `list_tags()`、`get_session_detail()`。

#### 2. `_api` 后缀（共 16 个）

- `routes/account.py`：`list_accounts_api`
- `routes/logs.py`：`get_log_modules_api`
- `routes/instance_detail.py`：`edit_api`
- `routes/credentials.py`：`create_api / edit_api`
- `routes/account_stat.py`：`statistics_api / statistics_summary_api / statistics_db_type_api / statistics_classification_api`
- `routes/instance.py`：`create_api / list_instances_api`
- `routes/auth.py`：`login_api / change_password_api`
- `routes/tags.py`：`create_api / edit_api / list_tags_api`

统一规则：保持动词 + 资源名，例如 `create_credential()`, `get_log_modules()`。

#### 3. `_optimized` 后缀（2 个）

- `services/account_classification/orchestrator.py`: `auto_classify_accounts_optimized`
- `services/account_sync/adapters/sqlserver_adapter.py`: `_get_all_users_database_permissions_batch_optimized`

统一改为无实现细节的名称（例如 `auto_classify_accounts` / `_get_all_users_database_permissions_batch`）。

#### 4. 复数错误函数名（4 个）

- `routes/database_aggr.py`：`get_databases_aggregations`, `get_databases_aggregations_summary`
- `routes/instance_aggr.py`：`get_instances_aggregations`, `get_instances_aggregations_summary`

改为 `database`/`instance` 单数 + `aggregations`。

---

## 🔧 命令模板

### 1. 重命名后端文件

```bash
# 路由文件
git mv app/routes/database_aggr.py app/routes/database_aggregations.py
git mv app/routes/instance_aggr.py app/routes/instance_aggregations.py

# 视图文件
git mv app/views/account_classification_form_view.py app/views/classification_forms.py
# ... 其他文件
```

### 2. 更新引用

```bash
# 更新后端导入（macOS）
find app -name "*.py" -type f -exec sed -i '' \
  -e 's/from app\.routes\.database_aggr/from app.routes.database_aggregations/g' \
  -e 's/from app\.routes\.instance_aggr/from app.routes.instance_aggregations/g' \
  -e 's/import database_aggr/import database_aggregations/g' \
  -e 's/import instance_aggr/import instance_aggregations/g' \
  -e 's/database_aggr\./database_aggregations./g' \
  -e 's/instance_aggr\./instance_aggregations./g' \
  -e 's/from app\.views\.account_classification_form_view/from app.views.classification_forms/g' \
  -e 's/from app\.views\.change_password_form_view/from app.views.password_forms/g' \
  -e 's/from app\.views\.credential_form_view/from app.views.credential_forms/g' \
  -e 's/from app\.views\.instance_form_view/from app.views.instance_forms/g' \
  -e 's/from app\.views\.scheduler_job_form_view/from app.views.scheduler_forms/g' \
  -e 's/from app\.views\.tag_form_view/from app.views.tag_forms/g' \
  -e 's/from app\.views\.user_form_view/from app.views.user_forms/g' \
  -e 's/from app\.services\.form_service\.change_password_form_service/from app.services.form_service.password_service/g' \
  -e 's/from app\.services\.form_service\.classification_form_service/from app.services.form_service.classification_service/g' \
  -e 's/from app\.services\.form_service\.classification_rule_form_service/from app.services.form_service.classification_rule_service/g' \
  -e 's/from app\.services\.form_service\.credentials_form_service/from app.services.form_service.credential_service/g' \
  -e 's/from app\.services\.form_service\.instances_form_service/from app.services.form_service.instance_service/g' \
  -e 's/from app\.services\.form_service\.resource_form_service/from app.services.form_service.resource_service/g' \
  -e 's/from app\.services\.form_service\.scheduler_job_form_service/from app.services.form_service.scheduler_job_service/g' \
  -e 's/from app\.services\.form_service\.tags_form_service/from app.services.form_service.tag_service/g' \
  -e 's/from app\.services\.form_service\.users_form_service/from app.services.form_service.user_service/g' \
  {} +
```

---

## ✅ 验证清单

### 执行后验证

- [ ] 运行 `make test` 通过
- [ ] 运行 `make quality` 通过
- [ ] 前端页面正常加载
- [ ] 浏览器控制台无 404 错误
- [ ] 没有旧路径残留

### 搜索残留

```bash
# 搜索旧的导入路径
rg "from app\.routes\.database_aggr" app/
rg "from app\.routes\.instance_aggr" app/
rg "from app\.views\.\w+_form_view" app/
rg "from app\.services\.form_service\.\w+_form_service" app/

# 搜索 api_ 前缀函数
rg "def api_" app/routes/
```

---

## 📚 命名规范速查

### Python

| 类型 | 规范 | 示例 |
|-----|------|------|
| 模块 | snake_case | `user_service.py` |
| 类 | CapWords | `UserService` |
| 函数 | snake_case | `get_user()` |
| 常量 | UPPER_SNAKE_CASE | `MAX_SIZE` |

### JavaScript

| 类型 | 规范 | 示例 |
|-----|------|------|
| 文件 | kebab-case | `user-service.js` |
| 类 | PascalCase | `UserService` |
| 函数 | camelCase | `getUser()` |
| 常量 | UPPER_SNAKE_CASE | `MAX_SIZE` |

---

## 🔄 回滚方案

```bash
# 创建备份
git tag backup-before-naming-$(date +%Y%m%d%H%M%S)

# 回滚
git reset --hard backup-before-naming-XXXXXX
```

---

## 📖 参考资源

- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [PEP 8 Style Guide](https://www.python.org/dev/peps/pep-0008/)
- [Google JavaScript Style Guide](https://google.github.io/styleguide/jsguide.html)

---

*最后更新: 2025-11-13*
