# 前端文件命名一致性分析与重构方案

## 执行摘要

本文档结合最近完成的后端命名重构经验（参见 `docs/refactoring/naming_consistency_analysis.md`），全面分析 TaifishingV4 项目前端资源（Templates、JavaScript、CSS）的命名现状，识别不一致问题，并提供一条可以直接落地的统一命名策略与重构路线图。

**统计概览**：
- HTML 模板：33 个文件
- JavaScript 文件：43 个文件
- CSS 样式表：28 个文件
- 总计：104 个前端资源文件

**主要问题**：
1. 命名风格混用：`kebab-case`、`snake_case`、`camelCase` 并存
2. 目录结构与模板/静态资源不完全对应，难以快速定位前端资源（尤其是聚合统计模块）
3. 部分 JS/CSS 文件命名与对应模板不匹配，存在“文件名 → 页面”映射不直观的问题
4. 缺少可复用的命名检测脚本，难以及时发现新增违规文件（后续可复用后端命名检查经验）

**推荐策略**：
- WS-A：先生成前端资源命名基线，明确 8 个 `kebab-case` JS 文件与 `database_sizes` 模板目录的偏差来源。
- WS-B：批量 `git mv` + `rg` 引用校验，一次性收敛全部 JS 命名；过程产出引用清单供 code review 复核。
- WS-C：对齐模板与静态资源目录（`database_sizes` → `capacity_stats`、组件模板扁平化），并清理遗留空目录。
- WS-D：落地 `check_frontend_naming.py`、pre-commit 与 CI 守护，避免后续新增命名违例。


---

## 一、当前命名现状分析

### 1.1 Templates 层（33 个文件）

#### 目录结构
```
templates/
├── accounts/           # 账号管理（3 个文件）
├── admin/              # 系统管理（2 个文件）
├── auth/               # 认证授权（4 个文件）
├── components/         # 可复用组件（3 个文件，含 filters/macros.html）
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
  - `components/filters/macros.html` 与其他组件放在不同子目录，增加检索成本


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

### 2.3 目录结构冗余/错位

- `templates/main/` 空目录未使用，建议移除并确认无引用
- `templates/database_sizes/` 与静态资源 `capacity_stats/` 不匹配，需要整体迁移
- `templates/components/filters/` 仅包含单一模板，建议合并进 `templates/components/`
- `app/static/js/components/` 与 `app/static/css/components/` 结构一致但文件分散，可在命名统一后保持扁平结构


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
| **JS - Utils** | `utils/<功能>_utils.js` | `utils/form_validator.js` | 纯函数工具集（命名与后端 `*_utils.py` 对齐） |

### 3.3 特殊场景命名

- **多词组合**：使用下划线连接，如 `account_classification.js`
- **通用工具**：添加 `_utils` 后缀，如 `time_utils.js`
- **管理器类**：添加 `_manager` 后缀，如 `connection_manager.js`
- **配置文件**：使用单一名词，如 `config.js`、`variables.css`
- **服务端对齐**：若前后端共同描述同一业务（如 `account_data_service`），保持术语一致，降低沟通成本


---

## 四、改进后的重构策略

### 4.1 工作流拆分与交付物

- **WS-A — 基线扫描与数据校验**  
  - 目标：锁定全部静态资源与模板的真实命名现状，生成 rename 风险矩阵。  
  - 交付物：`docs/refactoring/frontend_inventory-YYYYMMDD.csv`、命名风险列表、更新后的本文档。  
  - 依赖：无，为后续工作流提供数据输入。

- **WS-B — JavaScript 文件命名收敛**  
  - 目标：将 8 个 `kebab-case` 文件统一为 `snake_case`，并同步更新所有引用。  
  - 交付物：完成 `git mv`、引用更新、lint/单测通过的 PR。  
  - 依赖：WS-A 的基线结果、引用清单。

- **WS-C — 模板与静态资源目录对齐**  
  - 目标：使模板、JS、CSS 的目录命名一一对应，移除历史遗留的空目录。  
  - 交付物：`templates/capacity_stats` 重命名、组件模板扁平化、确认无残留引用。  
  - 依赖：WS-B 完成后才能启动（避免同时大规模移动造成审查困难）。

- **WS-D — 工具化与守护**  
  - 目标：让命名规范成为日常工作流的一部分，防止回退。  
  - 交付物：`scripts/code/check_frontend_naming.py`、pre-commit 钩子、CI 结果、README 更新。  
  - 依赖：WS-B/WS-C 提供最终的目录结构。

### 4.2 操作步骤详解

#### 步骤 1：建立命名基线（WS-A）
1. 运行一次快速扫描，生成当前命名分布（可临时保存为 `tmp/frontend_naming_baseline.txt`）：
   ```bash
   python3 - <<'PY'
   import pathlib, json
   root_js = pathlib.Path('app/static/js')
   kebab = sorted(str(p.relative_to(root_js)) for p in root_js.rglob('*.js') if '-' in p.name)
   root_css = pathlib.Path('app/static/css')
   mismatched_templates = []
   for tpl in pathlib.Path('app/templates').rglob('*.html'):
       if 'database_sizes' in tpl.parts:
           mismatched_templates.append(str(tpl))
   baseline = {
       'js_total': len(list(root_js.rglob('*.js'))),
       'js_kebab': kebab,
       'css_total': len(list(root_css.rglob('*.css'))),
       'template_mismatch': mismatched_templates,
   }
   pathlib.Path('tmp').mkdir(exist_ok=True)
   pathlib.Path('tmp/frontend_naming_baseline.json').write_text(json.dumps(baseline, indent=2))
   print(json.dumps(baseline, indent=2))
   PY
   ```
2. 将输出附在 PR 描述中，作为后续验收的基准，并补充到本文档的附录。

#### 步骤 2：统一 JavaScript 文件命名（WS-B）
1. 创建映射文件 `scripts/refactoring/frontend_js_rename_map.csv`（临时文件亦可），内容如下：
   ```
   common/csrf-utils.js,common/csrf_utils.js
   common/permission-modal.js,common/permission_modal.js
   common/permission-viewer.js,common/permission_viewer.js
   common/time-utils.js,common/time_utils.js
   components/connection-manager.js,components/connection_manager.js
   components/permission-button.js,components/permission_button.js
   utils/form-validator.js,utils/form_validator.js
   utils/validation-rules.js,utils/validation_rules.js
   ```
2. 执行批量重命名并保留历史记录：
   ```bash
   while IFS=, read -r src dst; do
     git mv "app/static/js/${src}" "app/static/js/${dst}"
   done < scripts/refactoring/frontend_js_rename_map.csv
   ```
3. 使用 `rg` 构建引用清单，并逐项替换（建议使用 `sd`/`perl -pi` 等原子命令）：
   ```bash
   rg "csrf-utils" -n app/templates app/static/js
   rg "permission-modal" -n app
   # 逐项替换后再次运行扫描脚本，确认引用全部更新
   ```
4. 运行 `make format`、`make quality`、`make test`，确保重命名未破坏静态资源加载。

#### 步骤 3：对齐模板与静态资源目录（WS-C）
1. 将 `templates/database_sizes` 重命名为 `templates/capacity_stats`：
   ```bash
   git mv app/templates/database_sizes app/templates/capacity_stats
   rg "database_sizes" -n app | sort -u
   ```
   - 更新 Blueprint、`url_for`、`render_template` 等引用，直到上述搜索无结果。
2. 扁平化组件模板目录：
   ```bash
   git mv app/templates/components/filters/macros.html app/templates/components/filter_macros.html
   rmdir app/templates/components/filters
   ```
   - 同步更新所有 `{% include %}`、`{% import %}` 引用。
3. 移除历史遗留的 `templates/main/` 目录（确认无引用后执行）。
4. 再次运行基线脚本，验证模板/JS/CSS 目录名称对齐。

#### 步骤 4：工具化守护（WS-D）
1. 新增 `scripts/code/check_frontend_naming.py`，核心逻辑：
   - 遍历 `app/templates`、`app/static/js`、`app/static/css`
   - 校验命名格式、目录映射以及孤立目录
   - 支持 `--diff`（仅输出问题）、`--fix`（可选自动建议）、`--export <path>`（输出基线 JSON）参数
2. 在 `pyproject.toml` 中注册命令行入口（若使用 `poetry`/`uv`）。
3. 更新 `.pre-commit-config.yaml`，在 `python` 钩子中调用该脚本：
   ```yaml
   -   repo: local
       hooks:
       -   id: frontend-naming
           name: frontend naming guard
           entry: python3 scripts/code/check_frontend_naming.py
           language: system
           pass_filenames: false
   ```
4. 在 CI（`make quality`）中新增命名检查步骤，并将结果上传为构件，方便回溯。

### 4.3 工作流验收标准
- **WS-A**：`tmp/frontend_naming_baseline.json` 与本文档同步更新，覆盖率 100%。
- **WS-B**：八个目标文件全部完成 `snake_case`，引用搜索无遗留命中，`npm`/`Webpack`（若有） 能正常构建。
- **WS-C**：`templates/capacity_stats` 内文件与 `css/pages/capacity_stats`、`js/pages/capacity_stats` 一一对应，`components/` 目录无孤立子目录。
- **WS-D**：本地 pre-commit 与 CI 均能阻止新增的命名违规文件，README/团队 Wiki 更新完成。

### 4.4 推进指引
- 每个工作流保持独立 Pull Request，降低评审压力。
- 对于引用替换，优先提交自动化脚本结果，再进行人工调整，确保改动可重复。
- 在开始 WS-B 前冻结新的前端文件提交，避免冲突；完成后再解冻并同步规范。


---

## 五、里程碑与资源评估

### 5.1 推进节奏

| 里程碑 | 建议时间 | 工作内容 | 验收标准 |
|--------|----------|----------|----------|
| M0 | Day 0 | 完成 WS-A 基线扫描并更新本文档、发起同步会议 | `tmp/frontend_naming_baseline.json` 入库 |
| M1 | Day 1-2 | 交付 WS-B（含引用更新与测试） | JS 全部 `snake_case`、测试通过 |
| M2 | Day 3 | 交付 WS-C，更新文档并回归关键页面 | 模板与静态资源目录对齐，无 404 |
| M3 | Day 4 | 交付 WS-D，集成 pre-commit/CI，更新 README/Wiki | 自动化守护上线，团队培训完成 |

> 建议在 M0-M1 期间限制并行的前端改动，待命名收敛后再合并其他特性分支。

### 5.2 风险评估

| 风险 | 影响 | 概率 | 缓解措施 |
|-----|------|------|---------|
| 引用替换遗漏导致页面报错 | 高 | 中 | `rg` 全量搜索 + 浏览器端逐页验证 |
| 并行分支继续产生不规范文件 | 中 | 中 | 重构期间冻结新分支，完成后统一 rebase |
| 模板目录改名触发 Flask 路由解析异常 | 高 | 低 | 在重命名前运行 `pytest -k 'app.routes'` 并复测 |
| 新增命名脚本误报 | 中 | 低 | 在 PR 中附 baseline 输出，评审期接受例外白名单 |
| 浏览器缓存保留旧静态资源路径 | 中 | 中 | 部署后清除 CDN/浏览器缓存，并附带静态资源版本号参数 |

### 5.3 回滚与隔离建议
- 在开始 WS-B 前创建 `refactor/frontend-naming` 分支，并保留 `git worktree` 用于对照测试。
- 每个工作流完成后 Tag（如 `tag/ws-b-complete`），方便按阶段回滚。
- 发生问题时优先回滚单个工作流的 commit，再回收基线数据以确认状态。
- 若脚本误删文件，使用 `git restore --source=HEAD@{1}` 或直接切换到 Tag 恢复。


---

## 六、验证清单

### 6.1 自动化检查

- [ ] 运行 `python3 scripts/code/check_frontend_naming.py --diff`，确认无新问题
- [ ] 使用 `python3 scripts/code/check_frontend_naming.py --export tmp/frontend_naming_postfix.json` 产生日志，更新文档附录
- [ ] 运行 `make quality`（含 lint + naming guard）确保通过
- [ ] 运行 `make test` 验证后端回归

### 6.2 手动测试清单

#### 核心页面功能测试
- [ ] 登录页面（`/auth/login`）
- [ ] 仪表盘（`/dashboard`）
- [ ] 实例列表（`/instances`）
- [ ] 实例详情（`/instances/<id>`）
- [ ] 账号列表（`/accounts`）
- [ ] 账号分类（`/accounts/classification`）
- [ ] 凭证管理（`/credentials`）
- [ ] 容量统计 - 数据库聚合（`/databases/`）
- [ ] 容量统计 - 实例聚合（`/instance_stats/instance`）
- [ ] 标签管理（`/tags`）
- [ ] 标签批量分配（`/tags/batch_assign`）
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
   - 添加 pre-commit hook 自动执行 `python3 scripts/code/check_frontend_naming.py`
   - CI/CD 流程中加入命名验证并产出 JSON 报告

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
├── csrf-utils.js          # 待重命名
├── permission_policy_center.js
├── permission-modal.js    # 待重命名
├── permission-viewer.js   # 待重命名
├── time-utils.js          # 待重命名
└── toast.js

components/ (4)
├── connection-manager.js  # 待重命名
├── filters/filter_utils.js
├── permission-button.js   # 待重命名
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
├── form-validator.js      # 待重命名
└── validation-rules.js    # 待重命名
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
components/ (2 + filters/macros.html)
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
