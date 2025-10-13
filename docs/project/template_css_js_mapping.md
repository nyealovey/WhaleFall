# 鲸落 (TaifishV4) - 模板与静态文件对应关系表

## 概述
本文档详细列出了每个HTML模板文件对应的CSS样式文件和JavaScript脚本文件，便于开发人员快速定位相关资源文件。

---

## 模板文件与静态资源对应关系表

| 序号 | 模板文件 | 对应CSS文件 | 对应JS文件 | 功能模块 | 备注 |
|------|----------|-------------|------------|----------|------|
| 1 | `base.html` | 无专用CSS | 无专用JS | 基础模板 | 包含全局样式和通用脚本 |
| 2 | `about.html` | `css/pages/about.css` | 无专用JS | 关于页面 | 静态信息展示 |
| 3 | `account_classification/management.html` | 无专用CSS | 无专用JS | 账户分类管理 | 使用全局样式 |
| 4 | `accounts/list.html` | `css/pages/accounts/list.css` | `js/pages/accounts/list.js` | 账户管理 | 包含权限查看组件 |
| 5 | `accounts/statistics.html` | 无专用CSS | 无专用JS | 账户统计 | 使用全局样式 |
| 6 | `accounts/sync_details.html` | 无专用CSS | 无专用JS | 同步详情 | 使用全局样式 |
| 7 | `accounts/sync_records.html` | `css/pages/accounts/sync_records.css` | `js/pages/accounts/sync_records.js` | 同步记录 | 包含Chart.js图表 |
| 8 | `admin/management.html` | `css/pages/admin/management.css` | `js/pages/admin/management.js` | 管理员功能 | 系统管理功能 |
| 9 | `auth/change_password.html` | `css/pages/auth/change_password.css` | `js/pages/auth/change_password.js` | 修改密码 | 包含CSRF工具 |
| 10 | `auth/login.html` | `css/pages/auth/login.css` | `js/pages/auth/login.js` | 用户登录 | 认证页面 |
| 11 | `auth/profile.html` | 无专用CSS | 无专用JS | 用户资料 | 使用全局样式 |
| 12 | `components/permission_modal.html` | 无专用CSS | 无专用JS | 权限模态框 | 组件模板 |
| 13 | `components/tag_selector.html` | `css/components/tag_selector.css` | `js/components/tag_selector.js` | 标签选择器 | 可复用组件 |
| 14 | `credentials/create.html` | `css/pages/credentials/create.css` | `js/pages/credentials/create.js` | 创建凭据 | 表单页面 |
| 15 | `credentials/detail.html` | 无专用CSS | 无专用JS | 凭据详情 | 使用全局样式 |
| 16 | `credentials/edit.html` | `css/pages/credentials/edit.css` | `js/pages/credentials/edit.js` | 编辑凭据 | 表单页面 |
| 17 | `credentials/list.html` | `css/pages/credentials/list.css` | `js/pages/credentials/list.js` | 凭据列表 | 列表页面 |
| 18 | `dashboard/overview.html` | `css/pages/dashboard/overview.css` | `js/pages/dashboard/overview.js` | 仪表板 | 包含Chart.js图表 |
| 19 | `database_types/list.html` | 无专用CSS | 无专用JS | 数据库类型 | 使用全局样式 |
| 20 | `errors/error.html` | 无专用CSS | 无专用JS | 错误页面 | 使用全局样式 |
| 21 | `instances/create.html` | `css/pages/instances/create.css` | `js/pages/instances/create.js` | 创建实例 | 包含标签选择器 |
| 22 | `instances/detail.html` | `css/pages/instances/detail.css` | `js/pages/instances/detail.js` | 实例详情 | 包含权限查看组件 |
| 23 | `instances/edit.html` | `css/pages/instances/create.css` | `js/pages/instances/edit.js` | 编辑实例 | 复用创建页面样式 |
| 24 | `instances/list.html` | `css/pages/instances/list.css` | `js/pages/instances/list.js` | 实例列表 | 包含标签选择器 |
| 25 | `instances/statistics.html` | `css/pages/instances/statistics.css` | `js/pages/instances/statistics.js` | 实例统计 | 包含Chart.js图表 |
| 26 | `history/logs.html` | `css/pages/history/logs.css` | `js/pages/history/logs.js` | 日志仪表板 | 日志管理 |
| 27 | `logs/detail.html` | 无专用CSS | 无专用JS | 日志详情 | 使用全局样式 |
| 28 | `logs/statistics.html` | 无专用CSS | 无专用JS | 日志统计 | 使用全局样式 |
| 29 | `macros/environment_macro.html` | 无专用CSS | 无专用JS | 环境宏 | Jinja2宏定义 |
| 30 | `scheduler/management.html` | `css/pages/scheduler/management.css` | `js/pages/scheduler/management.js` | 任务调度 | 定时任务管理 |
| 31 | `history/sync_sessions.html` | `css/pages/history/sync_sessions.css` | `js/pages/history/sync_sessions.js` | 同步会话 | 数据同步管理 |
| 32 | `tags/create.html` | 无专用CSS | 无专用JS | 创建标签 | 使用全局样式 |
| 33 | `tags/edit.html` | 无专用CSS | 无专用JS | 编辑标签 | 使用全局样式 |
| 34 | `tags/index.html` | `css/pages/tags/index.css` | `js/pages/tags/index.js` | 标签管理 | 标签列表页面 |
| 35 | `user_management/management.html` | `css/pages/user_management/management.css` | `js/pages/user_management/management.js` | 用户管理 | 用户账户管理 |

---

## 全局资源文件

### 基础模板 (base.html) 包含的全局资源

#### CSS文件
- `vendor/bootstrap/bootstrap.min.css` - Bootstrap框架样式
- `vendor/fontawesome/css/all.min.css` - Font Awesome图标库
- 内联样式 - 全局CSS变量和基础样式

#### JavaScript文件
- `vendor/jquery/jquery.min.js` - jQuery库
- `vendor/bootstrap/bootstrap.bundle.min.js` - Bootstrap JavaScript
- `js/common/console-utils.js` - 控制台工具
- `js/common/alert-utils.js` - 警告工具
- `js/common/time-utils.js` - 时间工具
- `js/common/permission-viewer.js` - 权限查看器
- `js/common/permission-modal.js` - 权限模态框
- `js/components/permission-button.js` - 权限按钮组件

---

## 特殊资源文件

### 图表相关页面
以下页面包含Chart.js图表库：
- `dashboard/overview.html` - 仪表板图表
- `accounts/sync_records.html` - 同步记录图表
- `instances/statistics.html` - 实例统计图表

### 组件相关页面
以下页面包含可复用组件：
- `components/tag_selector.html` - 标签选择器组件
- `instances/create.html` - 包含标签选择器
- `instances/edit.html` - 包含标签选择器
- `instances/list.html` - 包含标签选择器

### 权限相关页面
以下页面包含权限管理功能：
- `accounts/list.html` - 账户权限查看
- `instances/detail.html` - 实例权限查看
- `components/permission_modal.html` - 权限模态框

---

## 文件命名规范

### CSS文件命名
- 页面专用：`css/pages/[模块名]/[页面名].css`
- 组件专用：`css/components/[组件名].css`
- 全局样式：`css/[功能名].css`

### JavaScript文件命名
- 页面专用：`js/pages/[模块名]/[页面名].js`
- 组件专用：`js/components/[组件名].js`
- 通用工具：`js/common/[工具名].js`
- 调试工具：`js/debug/[工具名].js`

---

## 开发建议

### 添加新页面时
1. 创建对应的CSS文件：`css/pages/[模块名]/[页面名].css`
2. 创建对应的JS文件：`js/pages/[模块名]/[页面名].js`
3. 在模板中使用`{% block extra_css %}`和`{% block extra_js %}`引入
4. 更新本对应关系表

### 修改现有页面时
1. 检查对应的CSS和JS文件是否存在
2. 确保文件路径正确
3. 测试页面功能是否正常
4. 更新相关文档

### 组件开发时
1. 创建独立的CSS和JS文件
2. 确保组件可复用性
3. 在需要使用的页面中引入
4. 更新组件文档

---

## 统计信息

- **总模板文件数**: 35个
- **有专用CSS的模板**: 20个
- **有专用JS的模板**: 20个
- **使用全局样式的模板**: 15个
- **包含图表的页面**: 3个
- **包含组件的页面**: 4个
- **权限相关页面**: 3个

---

**文档生成时间**: 2024年12月19日  
**项目版本**: TaifishV4  
**维护者**: 开发团队
