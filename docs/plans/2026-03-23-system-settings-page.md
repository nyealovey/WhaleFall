# 系统设置聚合页 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在管理中心新增“系统设置”菜单，并把邮件设置与 JumpServer 数据源聚合到一个带左侧页内导航的系统设置页中。

**Architecture:** 新增一个聚合型 Web 页面，复用现有邮件设置与 JumpServer 数据源的前端模块与后端接口，只在模板层做组合，并新增轻量的页内导航脚本负责点击跳转与滚动激活。旧功能接口保持不变，旧页面路由继续保留以降低回归风险。

**Tech Stack:** Flask、Jinja2、原生 JavaScript、现有页面 CSS/模块脚本、pytest 单元/契约测试。

### Task 1: 固化新页面契约

**Files:**
- Create: `tests/unit/routes/test_web_system_settings_page_contract.py`
- Create: `tests/unit/test_frontend_system_settings_nav_contract.py`
- Modify: `tests/unit/test_frontend_jumpserver_source_contract.py`

**Step 1: Write the failing tests**
- 为新路由 `/admin/system-settings` 增加页面渲染契约。
- 为基础导航中的“管理中心 -> 系统设置”菜单增加静态契约。
- 为页内导航脚本和锚点结构增加静态契约。
- 调整 JumpServer 导航契约，改为断言新聚合入口而不是旧顶栏直达入口。

**Step 2: Run tests to verify they fail**
Run: `uv run pytest tests/unit/routes/test_web_system_settings_page_contract.py tests/unit/test_frontend_system_settings_nav_contract.py tests/unit/test_frontend_jumpserver_source_contract.py -m unit`
Expected: FAIL，因为新路由、模板、脚本与菜单尚未实现。

### Task 2: 实现系统设置聚合页

**Files:**
- Create: `app/routes/system_settings.py`
- Create: `app/templates/admin/system-settings/index.html`
- Create: `app/templates/admin/system-settings/_email-alert-settings-section.html`
- Create: `app/templates/admin/system-settings/_jumpserver-source-section.html`
- Create: `app/static/css/pages/admin/system-settings.css`
- Create: `app/static/js/modules/views/admin/system-settings/index.js`
- Modify: `app/__init__.py`
- Modify: `app/templates/base.html`
- Modify: `app/templates/admin/alerts/email-settings.html`
- Modify: `app/templates/integrations/jumpserver/source.html`

**Step 1: Add the route and register it**
- 新增 `system_settings` 蓝图并注册到应用。
- 页面返回聚合模板，使用管理中心权限保护。

**Step 2: Extract reusable section partials**
- 抽取邮件设置与 JumpServer 数据源的主体区域为局部模板。
- 旧页面继续通过 include 复用局部模板，减少重复结构。

**Step 3: Build the aggregate page**
- 添加页面标题、左侧目录、右侧内容区。
- 将两个设置模块按 section 形式嵌入，预留后续新增设置项的扩展位。

**Step 4: Add scroll-aware navigation**
- 点击左侧目录滚动到对应 section。
- 使用 `IntersectionObserver` 在滚动时自动切换当前激活项。
- 小屏时降级为顶部横向导航/非 sticky 布局。

**Step 5: Update top navigation**
- 在“管理中心”下新增“系统设置”入口。
- 从“统一设置”中移除邮件告警与 JumpServer 直达入口，避免信息分散。

### Task 3: 验证与收尾

**Files:**
- Verify: `tests/unit/routes/test_web_system_settings_page_contract.py`
- Verify: `tests/unit/test_frontend_system_settings_nav_contract.py`
- Verify: `tests/unit/test_frontend_jumpserver_source_contract.py`
- Verify: `tests/unit/routes/test_web_email_alert_settings_page_contract.py`

**Step 1: Run focused tests**
Run: `uv run pytest tests/unit/routes/test_web_system_settings_page_contract.py tests/unit/test_frontend_system_settings_nav_contract.py tests/unit/test_frontend_jumpserver_source_contract.py tests/unit/routes/test_web_email_alert_settings_page_contract.py -m unit`
Expected: PASS

**Step 2: Run frontend lint if touched JS significantly**
Run: `npm run lint:js -- app/static/js/modules/views/admin/system-settings/index.js`
Expected: PASS

**Step 3: Summarize residual risk**
- 说明旧路由仍保留，仅导航入口迁移。
- 提醒可继续把更多设置模块按相同 section 方式并入系统设置页。
