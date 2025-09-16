# 模板文件重命名映射表

## ✅ 重命名完成状态

所有模板文件已成功重命名，应用测试通过！

## 重命名映射表

### 1. Auth 模块
- `auth/login.html` → `auth/login.html` (保持不变)
- `auth/profile.html` → `auth/profile.html` (保持不变)
- `auth/change_password.html` → `auth/change_password.html` (保持不变)

### 2. Dashboard 模块
- `dashboard/index.html` → `dashboard/overview.html`

### 3. Accounts 模块
- `accounts/index.html` → `accounts/statistics.html` (账户统计页面)
- `accounts/list.html` → `accounts/list.html` (保持不变)
- `accounts/sync_records.html` → `accounts/sync_records.html` (保持不变)
- `accounts/sync_details.html` → `accounts/sync_details.html` (保持不变)

### 4. Account Classification 模块
- `account_classification/index.html` → `account_classification/management.html`
- `account_classification/batches.html` → `account_classification/batches.html` (保持不变)

### 5. Instances 模块
- `instances/index.html` → `instances/list.html`
- `instances/detail.html` → `instances/detail.html` (保持不变)
- `instances/create.html` → `instances/create.html` (保持不变)
- `instances/edit.html` → `instances/edit.html` (保持不变)
- `instances/statistics.html` → `instances/statistics.html` (保持不变)

### 6. Credentials 模块
- `credentials/index.html` → `credentials/list.html`
- `credentials/detail.html` → `credentials/detail.html` (保持不变)
- `credentials/create.html` → `credentials/create.html` (保持不变)
- `credentials/edit.html` → `credentials/edit.html` (保持不变)

### 7. Database Types 模块
- `database_types/index.html` → `database_types/list.html`
- `database_types/create.html` → `database_types/create.html` (保持不变)
- `database_types/edit.html` → `database_types/edit.html` (保持不变)

### 8. Scheduler 模块
- `scheduler/index.html` → `scheduler/management.html`

### 9. Sync Sessions 模块
- `sync_sessions/index.html` → `sync_sessions/management.html`

### 10. Logs 模块
- `logs/dashboard.html` → `logs/dashboard.html` (保持不变)
- `logs/detail.html` → `logs/detail.html` (保持不变)
- `logs/statistics.html` → `logs/statistics.html` (保持不变)

### 11. Admin 模块
- `admin/index.html` → `admin/management.html`

### 12. User Management 模块
- `user_management/index.html` → `user_management/management.html`

### 13. 其他文件
- `base.html` → `base.html` (保持不变)
- `components/permission_modal.html` → `components/permission_modal.html` (保持不变)
- `macros/environment_macro.html` → `macros/environment_macro.html` (保持不变)
- `errors/error.html` → `errors/error.html` (保持不变)

## ✅ 路由文件更新完成

所有路由文件已成功更新，引用新的模板文件名：

### 1. dashboard.py ✅
- `dashboard/index.html` → `dashboard/overview.html`

### 2. instances.py ✅
- `instances/index.html` → `instances/list.html`

### 3. credentials.py ✅
- `credentials/index.html` → `credentials/list.html`

### 4. database_types.py ✅
- `database_types/index.html` → `database_types/list.html`

### 5. account_classification.py ✅
- `account_classification/index.html` → `account_classification/management.html`

### 6. scheduler.py ✅
- `scheduler/index.html` → `scheduler/management.html`

### 7. sync_sessions.py ✅
- `sync_sessions/index.html` → `sync_sessions/management.html`

### 8. main.py (admin) ✅
- `admin/index.html` → `admin/management.html`

### 9. user_management.py ✅
- `user_management/index.html` → `user_management/management.html`

### 10. account_static.py ✅
- `accounts/index.html` → `accounts/statistics.html`

## ✅ 验证结果

- ✅ 所有模板文件重命名完成
- ✅ 所有路由文件更新完成
- ✅ 应用启动测试通过
- ✅ 无遗留的index.html文件
- ✅ 无模板引用错误
