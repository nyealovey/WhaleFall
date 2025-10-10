# 样式指南和重构建议

本文档概述了统一应用程序颜色和样式以创建更专业、更一致的外观的建议。

## 1. 统一调色板

我们将在整个应用程序中标准化以下调色板。此调色板基于 `base.html` 中定义的现有 CSS 变量，但经过了整理和扩展，以确保一致性。

所有新组件和样式都应使用这些颜色。

### 主要颜色
| 角色 | 变量 | 十六进制值 | 建议用法 |
| --- | --- | --- | --- |
| 主要 | `--primary-color` | `#667eea` | 主要按钮、链接、图标、高亮 |
| 次要 | `--secondary-color` | `#764ba2` | 渐变、次要元素 |
| 主体背景 | `--body-bg` | `linear-gradient(135deg, var(--primary-color), var(--secondary-color))` | 页面背景 |
| 卡片/组件背景 | `--component-bg` | `rgba(255, 255, 255, 0.95)` | 卡片、模态框、下拉菜单 |

### 语义颜色
| 角色 | 变量 | 十六进制值 | 建议用法 |
| --- | --- | --- | --- |
| 成功 | `--success-color` | `#28a745` | 成功消息、验证、可用状态 |
| 危险 | `--danger-color` | `#dc3545` | 错误消息、删除按钮、警告 |
| 警告 | `--warning-color` | `#ffc107` | 警告、需要注意的区域 |
| 信息 | `--info-color` | `#17a2b8` | 信息性消息、中性操作 |

### 中性色
| 角色 | 变量 | 十六进制值 | 建议用法 |
| --- | --- | --- | --- |
| 文本颜色 | `--text-color` | `#333333` | 主要文本 |
| 次要文本 | `--text-muted` | `#6c757d` | 辅助文本、占位符 |
| 边框颜色 | `--border-color` | `#dee2e6` | 边框、分隔线 |
| 浅灰色背景 | `--light-gray-bg` | `#f8f9fa` | 禁用的元素、背景 |

## 2. CSS 重构建议

为了实施新的调色板并解决不一致问题，建议对以下 CSS 文件进行更改。

### `app/static/css/pages/list.css`

此文件是造成不一致的主要原因，因为它依赖于 Bootstrap 的默认蓝色。

**建议：**

*   覆盖 Bootstrap 的 `.btn-primary` 和 `.btn-outline-primary` 类，以使用 `--primary-color`。
*   为数据库类型切换按钮创建特定的类，而不是依赖通用的 Bootstrap 类。

```css
/* app/static/css/pages/list.css */

/* 覆盖 Bootstrap 主按钮 */
.btn-primary {
    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
    border: none;
}

.btn-primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
}

/* 覆盖 Bootstrap 轮廓按钮 */
.btn-outline-primary {
    color: var(--primary-color);
    border-color: var(--primary-color);
}

.btn-outline-primary:hover {
    background-color: var(--primary-color);
    color: white;
}

/* 数据库类型切换按钮 */
.db-type-toggle .btn {
    border-width: 2px;
    font-weight: bold;
}
```

### `app/static/css/pages/dashboard/overview.css`

此文件包含一些不一致的渐变和颜色。

**建议：**

*   移除卡片标题上不一致的渐变。
*   确保所有统计卡片都使用语义颜色变量。

```css
/* app/static/css/pages/dashboard/overview.css */

/* 移除不一致的渐变 */
.card-header-cyan-purple,
.card-header-green-teal {
    background: none;
    background-color: var(--component-bg);
}

/* 确保统计卡片使用标准颜色 */
.stat-card.bg-success { background-color: var(--success-color) !important; }
.stat-card.bg-danger { background-color: var(--danger-color) !important; }
.stat-card.bg-warning { background-color: var(--warning-color) !important; }
.stat-card.bg-info { background-color: var(--info-color) !important; }
```

## 3. HTML 和 JavaScript 重构

### 移除内联样式

所有内联 `style` 属性都应替换为 CSS 类。

**示例：`app/templates/accounts/list.html`**

**之前：**
```html
<th style="font-size: 0.8rem;">名称</th>
<a href="..." style="font-size: 0.75rem; padding: ...">...</a>
```

**之后 (使用新的 CSS 类)：**
```html
<!-- HTML -->
<th class="table-header-small">名称</th>
<a href="..." class="btn-action-sm">...</a>

<!-- CSS -->
.table-header-small {
    font-size: 0.8rem;
}

.btn-action-sm {
    font-size: 0.75rem;
    padding: 0.25rem 0.5rem;
    border-radius: 0.375rem;
    font-weight: 500;
    transition: all 0.2s ease;
}
```

### 从 JavaScript 中移除硬编码颜色

JavaScript 中的硬编码颜色应替换为 CSS 变量或类。

**示例：`app/static/js/pages/dashboard/overview.js`**

**之前：**
```javascript
borderColor: 'rgb(220, 53, 69)',
backgroundColor: 'rgba(220, 53, 69, 0.2)',
```

**之后 (使用 CSS 变量)：**
```javascript
// 在 JS 中获取 CSS 变量
const rootStyles = getComputedStyle(document.documentElement);
const dangerColor = rootStyles.getPropertyValue('--danger-color').trim();

// ... 在图表配置中 ...
borderColor: dangerColor,
backgroundColor: `${dangerColor}33`, // 添加透明度
```

## 4. 管理动态颜色

对于来自数据库的动态颜色 (标签、分类)，应实施以下策略：

1.  **限制调色板：** 在 UI 中为管理员提供一组预定义的、与主调色板协调的颜色供选择，而不是允许任意的十六进制代码。
2.  **提供后备颜色：** 如果必须允许自定义颜色，请确保后备颜色 (`#6c757d`) 始终是中性色，并且与 `--text-muted` 或 `--border-color` 等变量保持一致。
3.  **确保可读性：** 在显示带有动态背景颜色的文本时，动态计算文本颜色 (黑色或白色) 以确保可读性。

通过实施这些更改，我们可以显著提高应用程序的视觉一致性和专业性。