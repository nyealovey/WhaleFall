# 命名规范重构文档

> 基于代码扫描，识别出 **79 项命名问题**，提供完整重构方案

## 📊 问题统计

| 类别 | 数量 |
|-----|------|
| 后端文件命名 | 18 个 |
| 前端目录命名 | 5 个 |
| 前端 JS 文件 | 13 个 |
| 前端 CSS 文件 | 8 个 |
| 函数命名 | 38 个 |
| **总计** | **79 项** |

**预计工作量**: 5-7 天  
**风险等级**: 低-中

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

### 后端文件（18 个）

```bash
# 路由文件（2 个）
database_aggr.py → database_aggregations.py
instance_aggr.py → instance_aggregations.py

# 视图文件（7 个）
account_classification_form_view.py → classification_forms.py
change_password_form_view.py → password_forms.py
credential_form_view.py → credential_forms.py
instance_form_view.py → instance_forms.py
scheduler_job_form_view.py → scheduler_forms.py
tag_form_view.py → tag_forms.py
user_form_view.py → user_forms.py

# 服务文件（9 个）
app/services/form_service/ 下所有 *_form_service.py → *_service.py
```

### 前端目录（5 个）

```bash
capacity_stats/ → capacity-stats/
classification_rules/ → classification-rules/
```

### 前端文件（21 个）

```bash
# JavaScript（13 个）
permission_policy_center.js → permission-policy-center.js
chart_renderer.js → chart-renderer.js
# ... 其他下划线改为连字符

# CSS（8 个）
tag_selector.css → tag-selector.css
filter_common.css → filter-common.css
# ... 其他下划线改为连字符
```

### 函数重命名（38 个）

```python
# 移除 api_ 前缀（28 个）
api_get_users() → get_users()
api_list() → list_instances()
api_detail() → get_instance()

# 修复语法错误（4 个）
get_databases_aggregations() → get_database_aggregations()
get_instances_aggregations() → get_instance_aggregations()

# 移除 _optimized 后缀（2 个）
auto_classify_accounts_optimized() → auto_classify_accounts()

# 统一 _api 后缀（4 个）
statistics_api() → get_statistics()
```

---

## ⚠️ 执行顺序（重要）

**正确顺序**：
1. ✅ 先重命名目录 → 文件自动跟随
2. ✅ 再重命名文件 → 在新目录下操作
3. ✅ 最后更新引用 → 只需更新一次

**错误顺序**（不推荐）：
- ❌ 先重命名文件，再重命名目录 → 需要修改两次引用

---

## 🔧 命令模板

### 1. 重命名目录

```bash
# 前端目录（优先执行）
git mv app/static/css/pages/capacity_stats app/static/css/pages/capacity-stats
git mv app/static/js/common/capacity_stats app/static/js/common/capacity-stats
git mv app/static/js/pages/capacity_stats app/static/js/pages/capacity-stats
git mv app/static/js/pages/accounts/classification_rules app/static/js/pages/accounts/classification-rules
git mv app/templates/accounts/classification_rules app/templates/accounts/classification-rules
```

### 2. 重命名后端文件

```bash
# 路由文件
git mv app/routes/database_aggr.py app/routes/database_aggregations.py
git mv app/routes/instance_aggr.py app/routes/instance_aggregations.py

# 视图文件
git mv app/views/account_classification_form_view.py app/views/classification_forms.py
# ... 其他文件
```

### 3. 重命名前端文件

```bash
# JavaScript 文件（在新目录下）
git mv app/static/js/common/capacity-stats/chart_renderer.js \
     app/static/js/common/capacity-stats/chart-renderer.js
# ... 其他文件
```

### 4. 更新引用

```bash
# 更新后端导入
find app -name "*.py" -type f -exec sed -i '' \
  -e 's/from app\.routes\.database_aggr/from app.routes.database_aggregations/g' \
  -e 's/from app\.views\.account_classification_form_view/from app.views.classification_forms/g' \
  {} +

# 更新前端引用
find app/templates -name "*.html" -type f -exec sed -i '' \
  -e 's/capacity_stats\//capacity-stats\//g' \
  -e 's/chart_renderer\.js/chart-renderer.js/g' \
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
# 搜索旧名称
rg "database_aggr" app/
rg "capacity_stats/" app/templates/ app/static/
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
