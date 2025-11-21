# 鲸落项目前端样式指南

> 最后更新：2025-11-21  
> 本文档定义了项目的前端样式规范，确保视觉一致性和代码可维护性。

## 1. 颜色规范

### 1.1 CSS 变量系统

项目使用 CSS 变量统一管理颜色，定义在 `app/static/css/variables.css` 中。所有新组件必须使用这些变量，禁止硬编码颜色值。

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

## 2. CSS 编写规范

### 2.1 文件组织

```
app/static/css/
├── variables.css       # CSS 变量定义
├── global.css          # 全局样式
├── components/         # 组件样式
│   ├── filters/       # 筛选组件
│   └── ui/            # UI 组件
└── pages/             # 页面特定样式
    ├── admin/         # 管理页面
    ├── capacity-stats/# 容量统计
    └── history/       # 历史记录
```

### 2.2 命名规范

- **文件名**: 使用 `kebab-case`
  - 正确: `database-aggregations.css`
  - 错误: `database_aggregations.css`, `databaseAggregations.css`

- **类名**: 使用 `kebab-case`，语义化命名
  - 正确: `.stat-card`, `.filter-container`, `.btn-action-sm`
  - 错误: `.statCard`, `.stat_card`

- **避免过深嵌套**: 最多 3 层
  ```css
  /* 正确 */
  .card-header .title { }
  
  /* 避免 */
  .container .card .card-header .title .text { }
  ```

### 2.3 使用 CSS 变量

```css
/* 正确：使用 CSS 变量 */
.btn-primary {
    background-color: var(--primary-color);
    color: var(--text-color);
}

/* 错误：硬编码颜色 */
.btn-primary {
    background-color: #667eea;
    color: #333333;
}
```

### 2.4 响应式设计

使用 Bootstrap 的断点系统：

```css
/* 移动优先 */
.stat-card {
    padding: 1rem;
}

/* 平板及以上 */
@media (min-width: 768px) {
    .stat-card {
        padding: 1.5rem;
    }
}

/* 桌面及以上 */
@media (min-width: 992px) {
    .stat-card {
        padding: 2rem;
    }
}
```

## 3. HTML 模板规范

### 3.1 禁止内联样式

**强制要求**: 所有样式必须通过 CSS 类定义，禁止使用内联 `style` 属性。

```html
<!-- 错误：内联样式 -->
<th style="font-size: 0.8rem; color: #666;">名称</th>

<!-- 正确：使用 CSS 类 -->
<th class="table-header-small text-muted">名称</th>
```

### 3.2 使用 Bootstrap 工具类

优先使用 Bootstrap 提供的工具类：

```html
<!-- 间距 -->
<div class="mb-3 mt-4 p-2">...</div>

<!-- 文本 -->
<p class="text-muted text-center fw-bold">...</p>

<!-- 显示 -->
<div class="d-flex justify-content-between align-items-center">...</div>
```

### 3.3 组件复用

使用 Jinja2 宏实现组件复用：

```jinja2
{# 定义宏 #}
{% macro stats_card(title, value_id, icon_class, card_class) %}
<div class="col-12 col-md-3 mb-3">
    <div class="card {{ card_class }}">
        <div class="card-body">
            <div class="d-flex justify-content-between">
                <div>
                    <p class="text-white-50 small">{{ title }}</p>
                    <h3 id="{{ value_id }}">-</h3>
                </div>
                <i class="{{ icon_class }} fa-2x text-white-50"></i>
            </div>
        </div>
    </div>
</div>
{% endmacro %}

{# 使用宏 #}
{{ stats_card('总用户数', 'totalUsers', 'fas fa-users', 'bg-primary text-white') }}
```

## 4. JavaScript 样式规范

### 4.1 获取 CSS 变量

```javascript
// 获取 CSS 变量
const rootStyles = getComputedStyle(document.documentElement);
const primaryColor = rootStyles.getPropertyValue('--primary-color').trim();

// 在图表中使用
const chartConfig = {
    borderColor: primaryColor,
    backgroundColor: `${primaryColor}33` // 添加透明度
};
```

### 4.2 动态样式操作

```javascript
// 使用 classList 而不是直接操作 style
element.classList.add('active');
element.classList.remove('disabled');
element.classList.toggle('hidden');

// 避免直接操作 style
// 错误
element.style.color = '#667eea';

// 正确：添加类
element.classList.add('text-primary');
```

### 4.3 Chart.js 颜色配置

```javascript
// 定义标准颜色
const CHART_COLORS = {
    primary: 'rgba(54, 162, 235, 0.7)',
    success: 'rgba(75, 192, 192, 0.7)',
    danger: 'rgba(255, 99, 132, 0.7)',
    warning: 'rgba(255, 159, 64, 0.7)'
};

// 在图表配置中使用
datasets: [{
    label: '数据集',
    borderColor: CHART_COLORS.primary,
    backgroundColor: CHART_COLORS.primary,
    borderWidth: 2
}]
```

## 5. 动态颜色管理

### 5.1 标签和分类颜色

对于数据库中的动态颜色（如标签、分类），遵循以下原则：

1. **预定义调色板**: 提供有限的颜色选项，确保与主题协调
2. **后备颜色**: 使用中性色作为默认值
3. **可读性检查**: 动态计算文本颜色确保对比度

```javascript
// 预定义的标签颜色
const TAG_COLORS = [
    '#667eea', // 主色
    '#28a745', // 成功
    '#dc3545', // 危险
    '#ffc107', // 警告
    '#17a2b8', // 信息
    '#6c757d'  // 中性
];

// 计算文本颜色
function getContrastColor(hexColor) {
    const r = parseInt(hexColor.substr(1, 2), 16);
    const g = parseInt(hexColor.substr(3, 2), 16);
    const b = parseInt(hexColor.substr(5, 2), 16);
    const brightness = (r * 299 + g * 587 + b * 114) / 1000;
    return brightness > 128 ? '#000000' : '#ffffff';
}
```

## 6. 图标使用规范

### 6.1 Font Awesome

项目使用 Font Awesome 图标库，统一图标风格：

```html
<!-- 实心图标 (fas) -->
<i class="fas fa-user"></i>
<i class="fas fa-database"></i>

<!-- 常规图标 (far) -->
<i class="far fa-circle"></i>

<!-- 品牌图标 (fab) -->
<i class="fab fa-github"></i>
```

### 6.2 图标大小

```html
<!-- 标准大小 -->
<i class="fas fa-user"></i>

<!-- 大小变体 -->
<i class="fas fa-user fa-xs"></i>
<i class="fas fa-user fa-sm"></i>
<i class="fas fa-user fa-lg"></i>
<i class="fas fa-user fa-2x"></i>
<i class="fas fa-user fa-3x"></i>
```

## 7. 组件样式规范

### 7.1 统计卡片

```html
<div class="col-12 col-md-3 mb-3">
    <div class="card shadow-sm border-0 bg-primary text-white">
        <div class="card-body">
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <p class="text-white-50 small mb-1">标题</p>
                    <h3 class="fw-bold mb-0">数值</h3>
                </div>
                <i class="fas fa-icon fa-2x text-white-50"></i>
            </div>
        </div>
    </div>
</div>
```

### 7.2 表格样式

```html
<div class="table-responsive">
    <table class="table table-hover">
        <thead>
            <tr>
                <th>列1</th>
                <th>列2</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>数据1</td>
                <td>数据2</td>
            </tr>
        </tbody>
    </table>
</div>
```

### 7.3 按钮样式

```html
<!-- 主要操作 -->
<button class="btn btn-primary">
    <i class="fas fa-plus me-1"></i>创建
</button>

<!-- 次要操作 -->
<button class="btn btn-outline-primary">
    <i class="fas fa-edit me-1"></i>编辑
</button>

<!-- 危险操作 -->
<button class="btn btn-danger">
    <i class="fas fa-trash me-1"></i>删除
</button>

<!-- 按钮组 -->
<div class="btn-group">
    <button class="btn btn-light">选项1</button>
    <button class="btn btn-light">选项2</button>
</div>
```

## 8. 代码审查清单

提交前端代码前，确保：

- [ ] 没有内联样式
- [ ] 使用 CSS 变量而非硬编码颜色
- [ ] 文件和类名使用 `kebab-case`
- [ ] 使用 Bootstrap 工具类
- [ ] 图标使用 Font Awesome
- [ ] 响应式设计适配移动端
- [ ] 代码格式化（Prettier）
- [ ] 浏览器兼容性测试

## 9. 参考资源

- [Bootstrap 5 文档](https://getbootstrap.com/docs/5.0/)
- [Font Awesome 图标](https://fontawesome.com/icons)
- [Chart.js 文档](https://www.chartjs.org/docs/)
- [CSS 变量指南](https://developer.mozilla.org/zh-CN/docs/Web/CSS/Using_CSS_custom_properties)

---

**相关文档**:
- [CODING_STANDARDS.md](./CODING_STANDARDS.md) - 编码规范
- [PROJECT_STRUCTURE.md](../architecture/PROJECT_STRUCTURE.md) - 项目结构