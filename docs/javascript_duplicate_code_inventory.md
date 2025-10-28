# JavaScript 重复代码详细清单

**目的**: 提供可直接用于重构的重复代码位置索引

---

## 1. UI 状态管理函数

### 1.1 `showLoadingState` 函数

| 文件 | 行号 | 参数类型 | 文本内容 |
|------|------|---------|---------|
| `credentials/create.js` | 256 | (form) | '创建中...' |
| `credentials/edit.js` | 263 | (form) | '保存中...' |
| `credentials/list.js` | 168 | (element, text) | 动态 |
| `auth/login.js` | 156 | (form) | '登录中...' |
| `auth/change_password.js` | 275 | (form) | '更新中...' |
| `auth/list.js` | 304 | (element, text) | 动态 |
| `tags/index.js` | 258 | (buttonId, text) | 动态 |
| `admin/scheduler.js` | 832 | (element, text) | 动态 |
| `admin/partitions.js` | 246 | () | 固定HTML |
| `history/logs.js` | 181 | () | '搜索中...' |
| `history/sync_sessions.js` | 69 | () | 切换显示 |

**实现差异**:
- **变体A**: 表单按钮 (6处) - 操作 `form.querySelector('button[type="submit"]')`
- **变体B**: 通用元素 (4处) - 支持 ID 字符串或元素对象
- **变体C**: 容器加载 (2处) - 替换整个容器内容

---

### 1.2 `hideLoadingState` 函数

| 文件 | 行号 | 恢复方式 |
|------|------|---------|
| `credentials/create.js` | 265 | 恢复按钮文本 |
| `credentials/edit.js` | 272 | 恢复按钮文本 |
| `credentials/list.js` | 180 | 恢复原始内容 |
| `auth/login.js` | 165 | 恢复按钮文本 |
| `auth/change_password.js` | 284 | 恢复按钮文本 |
| `auth/list.js` | 316 | 恢复原始内容 |
| `tags/index.js` | 267 | 恢复原始内容 |
| `admin/scheduler.js` | 845 | 恢复原始内容 |
| `history/sync_sessions.js` | 77 | 切换显示 |

---

### 1.3 Alert 通知函数

**完全相同的实现** (11个文件):

```javascript
function showSuccessAlert(message) {
    notify.success(message);
}

function showErrorAlert(message) {
    notify.error(message);
}

function showWarningAlert(message) {
    notify.warning(message);
}
```

| 文件 | 行号范围 |
|------|---------|
| `credentials/create.js` | 273-285 |
| `credentials/edit.js` | 280-292 |
| `credentials/list.js` | - |
| `auth/login.js` | 174-207 |
| `auth/change_password.js` | 293-307 |
| `auth/list.js` | 329-341 |
| `tags/index.js` | 278-290 |
| `dashboard/overview.js` | 212-275 |
| `history/logs.js` | 464-504 |
| `admin/partitions.js` | 269-284 |

---

## 2. 表单处理函数

### 2.1 `updateFieldValidation` 函数

**完全相同的实现** (6个文件):

```javascript
function updateFieldValidation(input, isValid, message) {
    const feedbackDiv = input.nextElementSibling;
    input.classList.remove('is-valid', 'is-invalid');
    input.classList.add(isValid ? 'is-valid' : 'is-invalid');
    
    if (feedbackDiv && feedbackDiv.classList.contains('invalid-feedback')) {
        feedbackDiv.textContent = message;
    }
}
```

| 文件 | 行号 |
|------|------|
| `credentials/create.js` | 168 |
| `credentials/edit.js` | 175 |
| `auth/login.js` | 83 |
| `auth/change_password.js` | 188 |
| `instances/create.js` | - |
| `accounts/list.js` | - |

---

### 2.2 `togglePasswordVisibility` 函数

**完全相同的实现** (5个文件):

```javascript
function togglePasswordVisibility(inputElement, toggleButton) {
    const type = inputElement.type === 'password' ? 'text' : 'password';
    inputElement.type = type;
    
    const icon = toggleButton.querySelector('i');
    if (icon) {
        icon.classList.toggle('fa-eye');
        icon.classList.toggle('fa-eye-slash');
    }
}
```

| 文件 | 行号 |
|------|------|
| `credentials/create.js` | 32 |
| `credentials/edit.js` | 36 |
| `auth/login.js` | 31 |
| `auth/change_password.js` | 40 |

---

### 2.3 表单验证函数组

**高度相似的验证逻辑**:

#### `validateName` (2个文件)
| 文件 | 行号 | 字段名 |
|------|------|--------|
| `credentials/create.js` | 117 | 凭据名称 |
| `credentials/edit.js` | 124 | 凭据名称 |

#### `validateUsername` (3个文件)
| 文件 | 行号 | 最小长度 |
|------|------|---------|
| `credentials/create.js` | 150 | 2 |
| `credentials/edit.js` | 157 | 2 |
| `auth/login.js` | 65 | 2 |

#### `validatePassword` (5个文件)
| 文件 | 行号 | 规则 |
|------|------|------|
| `credentials/create.js` | 159 | 非空 |
| `credentials/edit.js` | 166 | 非空 |
| `auth/login.js` | 74 | 非空 |
| `auth/change_password.js` | 162 | 复杂规则 |
| `auth/change_password.js` | 171 | 匹配检查 |

---

## 3. 标签选择器集成代码

### 3.1 完整的重复模块

每个文件都包含以下完整的函数集：

**函数清单**:
1. `initializeXxxTagSelector()` - 初始化入口
2. `initializeTagSelectorComponent()` - 组件初始化
3. `setupTagSelectorEvents()` - 事件绑定
4. `openTagSelector()` - 打开选择器
5. `closeTagSelector()` - 关闭选择器
6. `confirmTagSelection()` - 确认选择
7. `updateSelectedTagsPreview()` - 更新预览
8. `removeTagFromPreview()` - 移除标签

| 文件 | 总行数 | 起始行 | 结束行 |
|------|--------|--------|--------|
| `accounts/list.js` | ~200 | 133 | 339 |
| `instances/create.js` | ~180 | 131 | 310 |
| `instances/edit.js` | ~190 | 169 | 363 |
| `instances/list.js` | ~150 | 98 | 248 |

**核心重复逻辑**:

```javascript
// 1. 初始化模式 (完全相同)
function initializeXxxTagSelector() {
    try {
        const modalElement = document.getElementById('tagSelectorModal');
        const containerElement = document.getElementById('tag-selector-container');
        
        if (!modalElement || !containerElement) {
            console.error('标签选择器元素未找到');
            return;
        }
        
        initializeTagSelectorComponent(modalElement, containerElement);
        setupTagSelectorEvents();
        
    } catch (error) {
        console.error('initializeXxxTagSelector 函数执行出错:', error);
    }
}

// 2. 组件初始化 (99% 相同)
function initializeTagSelectorComponent(modalElement, containerElement) {
    if (typeof initializeTagSelector === 'function') {
        xxxPageTagSelector = initializeTagSelector({
            onSelectionChange: (selectedTags) => {
                // 回调处理
            }
        });
        
        if (xxxPageTagSelector) {
            window.xxxPageTagSelector = xxxPageTagSelector;
        } else {
            console.error('初始化标签选择器组件时出错:', error);
        }
    } else {
        console.error('initializeTagSelector函数未定义');
    }
}

// 3. 事件绑定 (95% 相同，仅变量名不同)
function setupTagSelectorEvents() {
    const openBtn = document.getElementById('open-tag-selector-btn');
    if (openBtn) {
        openBtn.addEventListener('click', function(e) {
            e.preventDefault();
            openTagSelector();
        });
    }
    
    if (xxxPageTagSelector && xxxPageTagSelector.container) {
        xxxPageTagSelector.container.addEventListener('tagSelectionConfirmed', function(event) {
            confirmTagSelection();
        });
        
        xxxPageTagSelector.container.addEventListener('tagSelectionCancelled', function(event) {
            // 取消处理
        });
    }
}

// 4. 更新预览 (90% 相同)
function updateSelectedTagsPreview(selectedTags) {
    const preview = document.getElementById('selected-tags-preview');
    if (!preview) return;
    
    if (selectedTags.length === 0) {
        preview.innerHTML = '<span class="text-muted">未选择标签</span>';
        return;
    }
    
    preview.innerHTML = selectedTags.map(tag => `
        <span class="badge me-2 mb-2" style="background-color: ${tag.color}; color: ${isColorDark(tag.color) ? '#fff' : '#000'}">
            ${tag.name}
            <button type="button" class="btn-close btn-close-sm ms-1" 
                    onclick="removeTagFromPreview('${tag.name}')"></button>
        </span>
    `).join('');
}
```

**差异点**:
- 变量名前缀（`accountList`, `createPage`, `editPage`, `listPage`）
- 确认后的处理逻辑（更新隐藏字段、调用不同 API）
- 其他 90% 代码完全相同

---

## 4. 表格操作函数

### 4.1 `sortTable` 函数

**高度相似** (5个文件):

| 文件 | 行号 | 表格选择器 |
|------|------|-----------|
| `credentials/list.js` | 224 | `.credentials-table .table` |
| `auth/list.js` | 226 | `.user-table .table` |
| 其他列表页 | - | 类似模式 |

**核心逻辑**:
```javascript
function sortTable(column, direction = 'asc') {
    const table = document.querySelector('.xxx-table .table');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.sort((a, b) => {
        const aValue = a.querySelector(`td[data-${column}]`)?.textContent || '';
        const bValue = b.querySelector(`td[data-${column}]`)?.textContent || '';
        return direction === 'asc' ? 
            aValue.localeCompare(bValue) : 
            bValue.localeCompare(aValue);
    });
    
    rows.forEach(row => tbody.appendChild(row));
}
```

---

### 4.2 `filterTable` / `searchTable` 函数

**相似模式** (多个文件):

```javascript
function filterTable(filterValue) {
    const rows = document.querySelectorAll('.table tbody tr');
    rows.forEach(row => {
        const matchesFilter = /* 不同的过滤逻辑 */;
        row.style.display = matchesFilter ? '' : 'none';
    });
}
```

---

## 5. API 调用模式

### 5.1 CSRF Token 获取

**出现位置**: 几乎所有 fetch 调用

```javascript
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
const headers = {
    'Content-Type': 'application/json',
    'X-CSRF-Token': csrfToken
};
```

**统计**: 约 **50+ 处**重复

---

### 5.2 统一的 fetch 错误处理模式

```javascript
fetch(url, options)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            notify.success(data.message);
            // 成功处理
        } else {
            notify.error(data.error || '操作失败');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        notify.error('请求失败');
    });
```

---

## 6. 工具函数

### 6.1 颜色判断函数 `isColorDark`

**完全相同** (4个文件):

| 文件 | 行号 |
|------|------|
| `accounts/list.js` | 310 |
| `instances/create.js` | - |
| `instances/edit.js` | - |
| `instances/list.js` | - |

```javascript
function isColorDark(colorStr) {
    // 完全相同的实现
    const hex = colorStr.replace('#', '');
    const r = parseInt(hex.substr(0, 2), 16);
    const g = parseInt(hex.substr(2, 2), 16);
    const b = parseInt(hex.substr(4, 2), 16);
    const brightness = (r * 299 + g * 587 + b * 114) / 1000;
    return brightness < 128;
}
```

---

### 6.2 `formatSize` / `formatBytes` 函数

**高度相似** (多个文件):

```javascript
function formatSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
```

---

## 7. 初始化模式

### 7.1 `DOMContentLoaded` 事件监听

**模式**: 几乎每个文件都有

```javascript
document.addEventListener('DOMContentLoaded', function() {
    initializeXxxPage();
    // ... 其他初始化
});
```

**问题**: 缺乏统一的页面生命周期管理

---

## 8. 统计总结

### 8.1 重复函数汇总

| 函数名 | 重复次数 | 总行数 | 类型 |
|--------|---------|--------|------|
| `showLoadingState` | 11 | ~165 | 完全重复 |
| `hideLoadingState` | 9 | ~90 | 完全重复 |
| `showSuccessAlert` | 11 | ~44 | 完全重复 |
| `showErrorAlert` | 11 | ~44 | 完全重复 |
| `showWarningAlert` | 11 | ~44 | 完全重复 |
| `updateFieldValidation` | 6 | ~90 | 完全重复 |
| `togglePasswordVisibility` | 5 | ~75 | 完全重复 |
| 标签选择器集成 | 4 | ~800 | 高度相似 |
| `sortTable` | 5 | ~125 | 高度相似 |
| `isColorDark` | 4 | ~40 | 完全重复 |
| `formatSize` | 3 | ~30 | 高度相似 |

**总计**: 约 **1,547 行**可提取的重复代码

---

### 8.2 重构优先级排序

| 序号 | 目标 | 节省行数 | 影响文件 | 难度 |
|------|------|---------|---------|------|
| 1 | 标签选择器 Mixin | 800 | 4 | 🟡 中 |
| 2 | UI 状态管理 | 300 | 11 | 🟢 低 |
| 3 | 表单验证器 | 200 | 6 | 🟡 中 |
| 4 | HTTP 客户端 | 150 | 20+ | 🟢 低 |
| 5 | 工具函数库 | 100 | 10+ | 🟢 低 |

---

## 9. 快速行动清单

### 立即可提取（本周）

**文件**: `common/ui-helpers.js`

```javascript
// 合并这些函数到一个文件
export function showLoading(element, options) { }
export function hideLoading(element) { }
export function showSuccess(message) { }
export function showError(message) { }
export function showWarning(message) { }
export function togglePasswordVisibility(input, button) { }
export function updateFieldValidation(input, isValid, message) { }
export function isColorDark(color) { }
export function formatBytes(bytes) { }
```

**影响**: 可立即减少 ~600 行重复代码

---

**报告完成时间**: 2025-10-28  
**下一步**: 创建 PoC (概念验证) 实现
