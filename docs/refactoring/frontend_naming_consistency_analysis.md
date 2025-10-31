# 前端文件命名一致性分析与重构方案

## 执行摘要

本文档分析 TaifishingV4 项目前端资源（Templates、JavaScript、CSS）的命名规范现状，识别不一致问题，并提供统一的命名策略与重构路线图。

**统计概览**：
- HTML 模板：33 个文件
- JavaScript 文件：43 个文件
- CSS 样式表：28 个文件
- 总计：104 个前端资源文件

**主要问题**：
1. 命名风格混用：`kebab-case`、`snake_case`、`camelCase` 并存
2. 目录结构与模板路径不完全对应
3. 部分 JS/CSS 文件命名与对应模板不匹配
4. 缺少统一的命名约定文档


---

## 一、当前命名现状分析

### 1.1 Templates 层（33 个文件）

#### 目录结构
```
templates/
├── accounts/           # 账号管理（3 个文件）
├── admin/              # 系统管理（2 个文件）
├── auth/               # 认证授权（4 个文件）
├── components/         # 可复用组件（2 个文件 + filters 子目录）
├── credentials/        # 凭证管理（4 个文件）
├── dashboard/          # 仪表盘（1 个文件）
├── database_sizes/     # 容量统计（2 个文件）
├── errors/             # 错误页面（1 个文件）
├── history/            # 历史记录（2 个文件）
├── instances/          # 实例管理（5 个文件）
├── main/               # 主页面（空目录）
├── tags/               # 标签管理（4 个文件）
├── about.html          # 关于页面
└── base.html           # 基础模板
```

#### 命名规范现状
- **一致性较好**：大部分使用 `snake_case`（如 `account_classification.html`）
- **标准操作命名**：`list.html`、`create.html`、`edit.html`、`detail.html`
- **问题点**：
  - `database_sizes/` 目录名与内容不匹配（实际是聚合统计页面）
  - `main/` 空目录未使用
  - `components/` 下文件较少，可考虑扁平化


### 1.2 JavaScript 层（43 个文件）

#### 目录结构
```
js/
├── common/                          # 通用模块（8 个文件）
│   ├── capacity_stats/              # 容量统计共享逻辑（6 个文件）
│   ├── config.js
│   ├── csrf-utils.js                # ❌ kebab-case
│   ├── permission_policy_center.js  # ✅ snake_case
│   ├── permission-modal.js          # ❌ kebab-case
│   ├── permission-viewer.js         # ❌ kebab-case
│   ├── time-utils.js                # ❌ kebab-case
│   └── toast.js
├── components/                      # 组件（4 个文件）
│   ├── connection-manager.js        # ❌ kebab-case
│   ├── filters/filter_utils.js      # ✅ snake_case
│   ├── permission-button.js         # ❌ kebab-case
│   └── tag_selector.js              # ✅ snake_case
├── pages/                           # 页面脚本（29 个文件）
│   ├── accounts/
│   ├── admin/
│   ├── auth/
│   ├── capacity_stats/              # ✅ 与模板对应
│   ├── credentials/
│   ├── dashboard/
│   ├── history/
│   ├── instances/
│   └── tags/
└── utils/                           # 工具函数（2 个文件）
    ├── form-validator.js            # ❌ kebab-case
    └── validation-rules.js          # ❌ kebab-case
```

#### 命名问题汇总
| 文件路径 | 当前命名风格 | 建议风格 | 优先级 |
|---------|------------|---------|--------|
| `common/csrf-utils.js` | kebab-case | snake_case | 高 |
| `common/permission-modal.js` | kebab-case | snake_case | 高 |
| `common/permission-viewer.js` | kebab-case | snake_case | 高 |
| `common/time-utils.js` | kebab-case | snake_case | 高 |
| `components/connection-manager.js` | kebab-case | snake_case | 高 |
| `components/permission-button.js` | kebab-case | snake_case | 高 |
| `utils/form-validator.js` | kebab-case | snake_case | 中 |
| `utils/validation-rules.js` | kebab-case | snake_case | 中 |


### 1.3 CSS 层（28 个文件）

#### 目录结构
```
css/
├── components/                      # 组件样式（2 个文件）
│   ├── filters/filter_common.css    # ✅ snake_case
│   └── tag_selector.css             # ✅ snake_case
├── pages/                           # 页面样式（24 个文件）
│   ├── about.css
│   ├── accounts/
│   ├── admin/
│   ├── auth/
│   ├── capacity_stats/              # ✅ 与模板对应
│   ├── credentials/
│   ├── dashboard/
│   ├── history/
│   ├── instances/
│   └── tags/
├── global.css                       # 全局样式
└── variables.css                    # CSS 变量
```

#### 命名规范现状
- **一致性优秀**：全部使用 `snake_case`
- **目录结构清晰**：`pages/` 与 `templates/` 目录结构基本对应
- **问题点**：
  - `pages/capacity_stats/` 与模板目录 `database_sizes/` 不一致


---

## 二、命名不一致问题详解

### 2.1 跨层命名不匹配

| 模板路径 | CSS 路径 | JS 路径 | 问题描述 |
|---------|---------|---------|---------|
| `templates/database_sizes/` | `css/pages/capacity_stats/` | `js/pages/capacity_stats/` | 模板目录名与资源目录名不一致 |
| `templates/components/permission_modal.html` | ✅ | `js/common/permission-modal.js` | JS 使用 kebab-case |
| `templates/components/tag_selector.html` | `css/components/tag_selector.css` | `js/components/tag_selector.js` | ✅ 命名一致 |

### 2.2 JavaScript 命名风格混乱

**问题根源**：早期开发使用 `kebab-case`，后期统一为 `snake_case`，但未完全迁移。

**影响范围**：
- `common/` 目录：8 个文件中 4 个使用 kebab-case
- `components/` 目录：4 个文件中 2 个使用 kebab-case
- `utils/` 目录：2 个文件全部使用 kebab-case

### 2.3 目录结构冗余

- `templates/main/` 空目录未使用
- `components/filters/` 仅包含 1 个模板文件，可考虑扁平化


---

## 三、统一命名规范

### 3.1 核心原则

1. **统一使用 `snake_case`**：所有文件名、目录名使用下划线分隔
2. **目录结构对应**：JS/CSS 的 `pages/` 子目录与 `templates/` 保持一致
3. **语义化命名**：文件名清晰表达功能，避免缩写
4. **分层清晰**：`common/`（跨页面）、`components/`（可复用）、`pages/`（页面特定）、`utils/`（纯函数）

### 3.2 命名模式速查表

| 层级 | 命名格式 | 示例 | 说明 |
|-----|---------|------|------|
| **Templates** | `<功能>.html` | `list.html`、`account_classification.html` | 使用 snake_case |
| **CSS - Pages** | `pages/<模块>/<功能>.css` | `pages/accounts/list.css` | 与模板路径对应 |
| **CSS - Components** | `components/<组件名>.css` | `components/tag_selector.css` | 可复用组件样式 |
| **JS - Pages** | `pages/<模块>/<功能>.js` | `pages/accounts/list.js` | 与模板路径对应 |
| **JS - Common** | `common/<功能>.js` | `common/csrf_utils.js` | 跨页面共享逻辑 |
| **JS - Components** | `components/<组件名>.js` | `components/tag_selector.js` | 可复用组件脚本 |
| **JS - Utils** | `utils/<功能>_utils.js` | `utils/form_validator.js` | 纯函数工具集 |

### 3.3 特殊场景命名

- **多词组合**：使用下划线连接，如 `account_classification.js`
- **通用工具**：添加 `_utils` 后缀，如 `time_utils.js`
- **管理器类**：添加 `_manager` 后缀，如 `connection_manager.js`
- **配置文件**：使用单一名词，如 `config.js`、`variables.css`


---

## 四、重构方案

### 4.1 Phase 1：JavaScript 文件重命名（高优先级）

#### 重命名清单

```bash
# common/ 目录
mv app/static/js/common/csrf-utils.js app/static/js/common/csrf_utils.js
mv app/static/js/common/permission-modal.js app/static/js/common/permission_modal.js
mv app/static/js/common/permission-viewer.js app/static/js/common/permission_viewer.js
mv app/static/js/common/time-utils.js app/static/js/common/time_utils.js

# components/ 目录
mv app/static/js/components/connection-manager.js app/static/js/components/connection_manager.js
mv app/static/js/components/permission-button.js app/static/js/components/permission_button.js

# utils/ 目录
mv app/static/js/utils/form-validator.js app/static/js/utils/form_validator.js
mv app/static/js/utils/validation-rules.js app/static/js/utils/validation_rules.js
```

#### 影响范围分析

需要更新引用的文件类型：
1. **HTML 模板**：`<script src="...">` 标签
2. **JavaScript 文件**：`import` 或动态加载语句
3. **配置文件**：可能的资源清单

#### 更新策略

```bash
# 1. 批量查找引用
grep -r "csrf-utils" app/templates/ app/static/js/
grep -r "permission-modal" app/templates/ app/static/js/
grep -r "permission-viewer" app/templates/ app/static/js/
grep -r "time-utils" app/templates/ app/static/js/
grep -r "connection-manager" app/templates/ app/static/js/
grep -r "permission-button" app/templates/ app/static/js/
grep -r "form-validator" app/templates/ app/static/js/
grep -r "validation-rules" app/templates/ app/static/js/

# 2. 使用 sed 批量替换（示例）
find app/templates -name "*.html" -exec sed -i '' 's/csrf-utils/csrf_utils/g' {} +
find app/static/js -name "*.js" -exec sed -i '' 's/csrf-utils/csrf_utils/g' {} +
```


### 4.2 Phase 2：目录结构调整（中优先级）

#### 调整清单

1. **统一容量统计目录名**
```bash
# 方案 A：模板目录改名（推荐）
mv app/templates/database_sizes app/templates/capacity_stats

# 方案 B：资源目录改名
mv app/static/css/pages/capacity_stats app/static/css/pages/database_sizes
mv app/static/js/pages/capacity_stats app/static/js/pages/database_sizes
```

**推荐方案 A**，理由：
- `capacity_stats` 更准确描述功能（容量统计聚合）
- JS/CSS 已使用此命名，改动成本更低
- 与后端路由 `/aggregations` 语义更接近

2. **清理空目录**
```bash
rmdir app/templates/main/  # 如确认未使用
```

3. **评估 components 扁平化**
```bash
# 如果 components/filters/ 仅 1 个文件，考虑上移
mv app/templates/components/filters/* app/templates/components/
rmdir app/templates/components/filters/
```


### 4.3 Phase 3：建立命名检查机制（低优先级）

#### 创建检查脚本

```python
# scripts/code/check_frontend_naming.py
import re
from pathlib import Path

def check_naming_conventions():
    errors = []
    
    # 检查 JS 文件命名
    js_files = Path("app/static/js").rglob("*.js")
    for path in js_files:
        if "-" in path.stem:
            errors.append(f"JS 文件使用 kebab-case: {path}")
    
    # 检查 CSS 文件命名
    css_files = Path("app/static/css").rglob("*.css")
    for path in css_files:
        if "-" in path.stem and path.stem not in ["global", "variables"]:
            errors.append(f"CSS 文件使用 kebab-case: {path}")
    
    # 检查目录对应关系
    template_dirs = {d.name for d in Path("app/templates").iterdir() if d.is_dir()}
    css_page_dirs = {d.name for d in Path("app/static/css/pages").iterdir() if d.is_dir()}
    js_page_dirs = {d.name for d in Path("app/static/js/pages").iterdir() if d.is_dir()}
    
    mismatches = (css_page_dirs | js_page_dirs) - template_dirs
    if mismatches:
        errors.append(f"目录不匹配: {mismatches}")
    
    return errors

if __name__ == "__main__":
    errors = check_naming_conventions()
    if errors:
        print("❌ 发现命名问题：")
        for error in errors:
            print(f"  - {error}")
        exit(1)
    else:
        print("✅ 前端命名规范检查通过")
```

#### 集成到 CI/CD

```yaml
# .github/workflows/frontend-lint.yml
name: Frontend Naming Check
on: [push, pull_request]
jobs:
  check-naming:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Check frontend naming conventions
        run: python scripts/code/check_frontend_naming.py
```


---

## 五、实施计划

### 5.1 时间线

| 阶段 | 任务 | 预计工时 | 负责人 | 状态 |
|-----|------|---------|--------|------|
| Phase 1 | JS 文件重命名 + 引用更新 | 4 小时 | TBD | 待开始 |
| Phase 1 | 回归测试（手动点击所有页面） | 2 小时 | TBD | 待开始 |
| Phase 2 | 目录结构调整 | 2 小时 | TBD | 待开始 |
| Phase 2 | 路由配置更新（如需要） | 1 小时 | TBD | 待开始 |
| Phase 3 | 编写命名检查脚本 | 2 小时 | TBD | 待开始 |
| Phase 3 | 集成到 pre-commit | 1 小时 | TBD | 待开始 |
| **总计** | | **12 小时** | | |

### 5.2 风险评估

| 风险 | 影响 | 概率 | 缓解措施 |
|-----|------|------|---------|
| 遗漏引用导致页面报错 | 高 | 中 | 使用全局搜索 + 手动测试所有页面 |
| 浏览器缓存导致 404 | 中 | 高 | 清理缓存 + 版本号参数 |
| 第三方库引用路径错误 | 低 | 低 | vendor/ 目录不在重构范围 |
| 模板目录改名影响路由 | 高 | 低 | 先检查 Flask 路由配置 |

### 5.3 回滚方案

```bash
# 使用 Git 回滚
git checkout HEAD -- app/static/js/
git checkout HEAD -- app/templates/

# 或使用分支保护
git checkout -b refactor/frontend-naming-backup
# 在新分支进行重构，测试通过后合并
```


---

## 六、验证清单

### 6.1 自动化检查

- [ ] 运行 `python scripts/code/check_frontend_naming.py`
- [ ] 检查所有 JS 文件无 kebab-case
- [ ] 检查 CSS/JS 目录与模板目录对应
- [ ] 运行 `make test` 确保后端测试通过

### 6.2 手动测试清单

#### 核心页面功能测试
- [ ] 登录页面（`/auth/login`）
- [ ] 仪表盘（`/dashboard`）
- [ ] 实例列表（`/instances`）
- [ ] 实例详情（`/instances/<id>`）
- [ ] 账号列表（`/accounts`）
- [ ] 账号分类（`/accounts/classification`）
- [ ] 凭证管理（`/credentials`）
- [ ] 容量统计 - 数据库聚合（`/aggregations/databases`）
- [ ] 容量统计 - 实例聚合（`/aggregations/instances`）
- [ ] 标签管理（`/tags`）
- [ ] 标签批量分配（`/tags/batch`）
- [ ] 同步会话历史（`/history/sync-sessions`）
- [ ] 日志查看（`/history/logs`）
- [ ] 调度器管理（`/admin/scheduler`）
- [ ] 分区管理（`/admin/partitions`）

#### 组件功能测试
- [ ] 标签选择器（Tag Selector）
- [ ] 权限按钮（Permission Button）
- [ ] 权限模态框（Permission Modal）
- [ ] 连接测试（Connection Manager）
- [ ] 筛选器（Filters）
- [ ] 表单验证（Form Validator）
- [ ] Toast 提示
- [ ] 图表渲染（Chart.js）

#### 浏览器兼容性测试
- [ ] Chrome（最新版）
- [ ] Firefox（最新版）
- [ ] Safari（最新版）
- [ ] Edge（最新版）


---

## 七、最佳实践建议

### 7.1 新增文件命名规范

创建新文件时遵循以下流程：

1. **确定文件类型**
   - 页面特定 → `pages/<模块>/<功能>.{js,css}`
   - 可复用组件 → `components/<组件名>.{js,css}`
   - 跨页面共享 → `common/<功能>.js`
   - 纯函数工具 → `utils/<功能>_utils.js`

2. **命名检查清单**
   - [ ] 使用 `snake_case`（全小写 + 下划线）
   - [ ] 避免缩写（除非是通用缩写如 `csrf`、`api`）
   - [ ] 与对应模板文件名一致
   - [ ] 目录结构与 `templates/` 对应

3. **代码审查要点**
   - PR 中新增文件需检查命名规范
   - 使用 `check_frontend_naming.py` 自动检查
   - 确保 JS/CSS 引用路径正确

### 7.2 重构后维护建议

1. **文档同步**
   - 更新 `README.md` 中的前端目录说明
   - 在 `docs/` 中维护前端架构文档
   - 记录命名规范到团队 Wiki

2. **工具链集成**
   - 配置 ESLint 检查文件命名
   - 添加 pre-commit hook 自动检查
   - CI/CD 流程中加入命名验证

3. **团队培训**
   - 向团队成员宣讲新规范
   - 提供命名速查表（Quick Reference）
   - Code Review 时强化规范执行


---

## 八、附录

### 8.1 完整文件清单

#### JavaScript 文件（43 个）
```
common/ (8)
├── capacity_stats/ (6)
│   ├── chart_renderer.js
│   ├── data_source.js
│   ├── filters.js
│   ├── manager.js
│   ├── summary_cards.js
│   └── transformers.js
├── config.js
├── csrf_utils.js          # 待重命名
├── permission_policy_center.js
├── permission_modal.js    # 待重命名
├── permission_viewer.js   # 待重命名
├── time_utils.js          # 待重命名
└── toast.js

components/ (4)
├── connection_manager.js  # 待重命名
├── filters/filter_utils.js
├── permission_button.js   # 待重命名
└── tag_selector.js

pages/ (29)
├── accounts/ (2)
├── admin/ (3)
├── auth/ (3)
├── capacity_stats/ (2)
├── credentials/ (3)
├── dashboard/ (1)
├── history/ (2)
├── instances/ (5)
└── tags/ (3)

utils/ (2)
├── form_validator.js      # 待重命名
└── validation_rules.js    # 待重命名
```

#### CSS 文件（28 个）
```
components/ (2)
├── filters/filter_common.css
└── tag_selector.css

pages/ (24)
├── about.css
├── accounts/ (2)
├── admin/ (2)
├── auth/ (3)
├── capacity_stats/ (2)
├── credentials/ (4)
├── dashboard/ (1)
├── history/ (2)
├── instances/ (5)
└── tags/ (2)

global.css
variables.css
```

#### HTML 模板（33 个）
```
accounts/ (3)
admin/ (2)
auth/ (4)
components/ (2 + filters/)
credentials/ (4)
dashboard/ (1)
database_sizes/ (2)        # 待重命名为 capacity_stats
errors/ (1)
history/ (2)
instances/ (5)
main/ (0)                  # 待删除
tags/ (4)
about.html
base.html
```

### 8.2 参考资源

- [Flask 模板最佳实践](https://flask.palletsprojects.com/en/2.3.x/patterns/)
- [Google HTML/CSS Style Guide](https://google.github.io/styleguide/htmlcssguide.html)
- [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)
- [Python PEP 8 命名约定](https://peps.python.org/pep-0008/#naming-conventions)（参考 snake_case）


---

**文档版本**：1.0  
**创建日期**：2025-10-31  
**最后更新**：2025-10-31  
**维护者**：开发团队  
**审核状态**：待审核
