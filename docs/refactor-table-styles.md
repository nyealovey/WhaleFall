# 表格样式重构文档

## 概述

本文档记录了针对项目中所有基于 Grid.js 的表格组件进行的样式紧凑化重构。目标是统一表格视觉风格，提升信息密度，优化用户体验。

## 重构目标

1. **紧凑化布局**：减少单元格内边距和行高，提升信息密度
2. **统一样式**：建立全局表格样式规范，消除各页面样式差异
3. **响应式优化**：确保在不同屏幕尺寸下的良好展示
4. **性能提升**：减少重复样式定义，优化 CSS 加载

## 影响范围

### 涉及页面

- **实例管理** (`app/static/css/pages/instances/list.css`)
- **账户管理** (`app/static/css/pages/accounts/list.css`)
- **凭据管理** (`app/static/css/pages/credentials/list.css`)
- **用户管理** (`app/static/css/pages/auth/list.css`)
- **历史日志** (`app/static/css/pages/history/logs.css`)
- **同步会话** (`app/static/css/pages/history/sync-sessions.css`)
- **容量统计** (`app/static/css/pages/capacity-stats/*.css`)
- **标签管理** (`app/static/css/pages/tags/index.css`)

### 核心文件

- `app/static/css/components/table.css` (新建)
- `app/static/css/global.css` (更新)
- `app/static/js/common/grid-wrapper.js` (配置更新)

## 重构方案

### 1. 创建全局表格组件样式

新建 `app/static/css/components/table.css`，定义统一的表格样式规范：

```css
/* Grid.js 表格紧凑化样式 */

/* 基础表格容器 */
.gridjs-wrapper {
    border-radius: var(--border-radius-md);
    box-shadow: var(--shadow-sm);
    font-size: 13px;
}

/* 表格主体 */
.gridjs-table {
    width: 100%;
    border-collapse: collapse;
}

/* 表头样式 */
.gridjs-thead {
    background-color: var(--gray-100);
}

.gridjs-th {
    padding: 8px 12px !important;
    font-weight: 600;
    font-size: 13px;
    color: var(--gray-700);
    text-transform: none;
    letter-spacing: 0.3px;
}

/* 单元格样式 - 紧凑化核心 */
.gridjs-td {
    padding: 6px 12px !important;
    line-height: 1.4;
    vertical-align: middle;
}

/* 行样式 */
.gridjs-tr {
    height: auto;
    transition: background-color 0.2s ease;
}

.gridjs-tr:hover {
    background-color: rgba(24, 188, 156, 0.05);
}

/* 徽章/标签紧凑化 */
.gridjs-td .badge {
    padding: 2px 8px;
    font-size: 11px;
    margin: 2px;
    font-weight: 500;
    line-height: 1.3;
}

/* 多标签容器 */
.badge-container {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    align-items: center;
}

.badge-container .badge {
    margin: 0;
    white-space: nowrap;
}

/* 操作按钮紧凑化 */
.gridjs-td .btn {
    padding: 4px 8px;
    font-size: 12px;
    line-height: 1.2;
    min-width: 32px;
    height: 28px;
}

.gridjs-td .btn-group {
    gap: 4px;
}

.gridjs-td .btn-group .btn {
    margin: 0;
}

/* 图标按钮 */
.gridjs-td .btn i {
    font-size: 13px;
}

/* 分页器紧凑化 */
.gridjs-pagination {
    padding: 10px 12px;
}

.gridjs-pagination .gridjs-pages button {
    padding: 4px 10px;
    font-size: 13px;
    min-width: 32px;
    height: 32px;
}

.gridjs-pagination .gridjs-summary {
    font-size: 13px;
}

/* 搜索框紧凑化 */
.gridjs-search {
    padding: 10px 12px;
}

.gridjs-search-input {
    padding: 6px 12px;
    font-size: 13px;
}

/* 加载状态 */
.gridjs-loading {
    font-size: 13px;
}

/* 空状态 */
.gridjs-notfound {
    padding: 20px;
    font-size: 13px;
}

/* 固定列宽优化 */
.gridjs-th[data-column-id="actions"],
.gridjs-td[data-column-id="actions"] {
    width: 80px;
    text-align: center;
}

.gridjs-th[data-column-id="status"],
.gridjs-td[data-column-id="status"] {
    width: 90px;
    text-align: center;
}

.gridjs-th[data-column-id="db_type"],
.gridjs-td[data-column-id="db_type"] {
    width: 100px;
    text-align: center;
}

/* 响应式调整 */
@media (max-width: 768px) {
    .gridjs-wrapper {
        font-size: 12px;
    }
    
    .gridjs-th,
    .gridjs-td {
        padding: 6px 8px !important;
    }
    
    .gridjs-td .badge {
        font-size: 10px;
        padding: 2px 6px;
    }
    
    .gridjs-td .btn {
        padding: 3px 6px;
        font-size: 11px;
        min-width: 28px;
        height: 24px;
    }
}
```

### 2. 更新 GridWrapper 默认配置

修改 `app/static/js/common/grid-wrapper.js` 的 `mergeOptions` 方法：

```javascript
GridWrapper.prototype.mergeOptions = function mergeOptions(userOptions = {}) {
  const defaults = {
    search: false,
    sort: {
      multiColumn: false,
      server: { /* ... */ },
    },
    pagination: {
      enabled: true,
      limit: 20,  // 紧凑化后可适当增加每页条数
      summary: true,
      server: { /* ... */ },
    },
    className: {
      table: "table table-hover align-middle mb-0 compact-table",
      thead: "table-light",
      td: "compact-cell",
      th: "compact-header"
    },
    style: {
      table: {
        'font-size': '13px'
      },
      td: {
        'padding': '6px 12px',
        'line-height': '1.4'
      },
      th: {
        'padding': '8px 12px',
        'font-size': '13px'
      }
    },
    // ... 其他配置
  };
  return this.deepMerge(defaults, userOptions);
};
```

### 3. 更新全局样式

在 `app/static/css/global.css` 中添加表格相关的全局样式：

```css
/* 统一表格样式 - 追加到文件末尾 */

/* 表格容器 */
.table-responsive {
    border-radius: var(--border-radius-md);
    box-shadow: var(--shadow-sm);
}

/* Bootstrap 表格紧凑化 */
.table-sm th,
.table-sm td {
    padding: 6px 12px;
    font-size: 13px;
}

/* 表格徽章统一样式 */
.table .badge {
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 500;
}

/* 表格操作按钮统一样式 */
.table .btn-sm {
    padding: 4px 8px;
    font-size: 12px;
    line-height: 1.2;
}

/* 表格图标统一大小 */
.table i {
    font-size: 13px;
}
```

### 4. 页面级样式清理

#### 4.1 实例列表 (`app/static/css/pages/instances/list.css`)

**移除重复样式**：
- `.gridjs-wrapper` 的基础样式（已在全局定义）
- `.gridjs-table` 的宽度设置（已在全局定义）
- `.gridjs-tr:hover` 的背景色（已在全局定义）

**保留页面特定样式**：
```css
/* 实例列表页面特定样式 */

/* 数据库类型按钮组 */
.btn-group [data-db-type-btn] {
    transition: all 0.2s ease;
    min-width: 110px;
    border-radius: var(--border-radius-sm);
    margin-bottom: 0.5rem;
}

/* 实例名称列加粗 */
#instances-grid td[data-column-id="name"] {
    font-weight: 600;
}

/* 标签列特殊处理 */
#instances-grid td[data-column-id="tags"] {
    white-space: normal;
    line-height: 1.8;
}

/* 统计徽章 */
.stat-badge {
    min-width: 64px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.8rem;
}
```

#### 4.2 账户列表 (`app/static/css/pages/accounts/list.css`)

**清理方案**：类似实例列表，移除重复的 Grid.js 基础样式，保留：
- 用户名列加粗样式
- 标签/分类列的特殊布局
- 响应式断点调整

#### 4.3 凭据列表 (`app/static/css/pages/credentials/list.css`)

**保留特色样式**：
- 凭据类型徽章的自定义颜色
- 空状态动画
- 实例计数徽章

#### 4.4 历史日志 (`app/static/css/pages/history/logs.css`)

**特殊处理**：
- 日志级别颜色保持不变
- 日志条目的网格布局保持不变
- 代码块样式保持不变

### 5. 模板文件更新

确保所有使用 Grid.js 的模板引入新的组件样式：

```html
<!-- 在 base.html 或各页面模板的 <head> 中添加 -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/components/table.css') }}">
```

## 实施步骤

### 阶段一：基础设施（第 1-2 天）

1. 创建 `app/static/css/components/table.css`
2. 更新 `app/static/css/global.css`
3. 修改 `app/static/js/common/grid-wrapper.js`
4. 更新 `app/templates/base.html` 引入新样式

### 阶段二：页面迁移（第 3-5 天）

按优先级逐页迁移：

1. **高优先级**（用户最常访问）
   - 实例列表
   - 账户列表
   - 凭据列表

2. **中优先级**
   - 用户管理
   - 历史日志
   - 同步会话

3. **低优先级**
   - 容量统计
   - 标签管理
   - 其他管理页面

### 阶段三：测试与优化（第 6-7 天）

1. **功能测试**
   - 表格排序功能
   - 分页功能
   - 筛选功能
   - 操作按钮点击

2. **视觉测试**
   - 不同浏览器兼容性（Chrome、Firefox、Safari、Edge）
   - 响应式布局（桌面、平板、手机）
   - 主题一致性

3. **性能测试**
   - 大数据量渲染（1000+ 行）
   - CSS 加载时间
   - 页面重绘性能

## 迁移检查清单

每个页面迁移时需确认：

- [ ] 引入 `components/table.css`
- [ ] 移除页面级重复的 Grid.js 基础样式
- [ ] 保留页面特定的业务样式
- [ ] 测试表格功能正常
- [ ] 测试响应式布局
- [ ] 检查徽章/按钮显示正常
- [ ] 验证操作按钮可点击
- [ ] 确认排序/分页/筛选功能正常

## 样式对比

### 重构前

```css
/* 各页面重复定义 */
#instances-grid .gridjs-table {
    width: 100%;
}

#accounts-grid .gridjs-table {
    width: 100%;
}

#credentials-grid .gridjs-table {
    width: 100%;
}

/* 单元格内边距不统一 */
.gridjs-td {
    padding: 12px 16px;  /* 实例页面 */
}

.gridjs-td {
    padding: 10px 14px;  /* 账户页面 */
}
```

### 重构后

```css
/* 全局统一定义 */
.gridjs-table {
    width: 100%;
}

.gridjs-td {
    padding: 6px 12px !important;
}

/* 页面只保留特定样式 */
#instances-grid td[data-column-id="name"] {
    font-weight: 600;
}
```

## 预期效果

### 视觉效果

- **行高减少约 30%**：从平均 48px 降至 36px
- **信息密度提升**：相同屏幕空间显示更多数据行
- **视觉统一**：所有表格风格一致

### 性能提升

- **CSS 体积减少**：消除约 40% 的重复样式定义
- **加载速度提升**：减少 HTTP 请求和 CSS 解析时间
- **维护成本降低**：单一样式源，修改一处生效全局

### 用户体验

- **浏览效率提升**：减少滚动次数
- **操作便捷性**：按钮和徽章更紧凑但仍易点击
- **视觉舒适度**：保持足够的留白和对比度

## 回滚方案

如遇重大问题需回滚：

1. 从 Git 恢复修改前的文件
2. 移除 `components/table.css` 的引入
3. 恢复 `grid-wrapper.js` 的原始配置

建议：
- 在开发分支完成全部迁移和测试
- 使用功能开关（feature flag）控制新样式启用
- 保留旧样式文件备份至少一个版本周期

## 后续优化建议

1. **虚拟滚动**：对于超大数据集（10000+ 行），考虑引入虚拟滚动
2. **列宽自适应**：根据内容动态调整列宽
3. **固定表头**：长表格滚动时固定表头
4. **导出功能**：添加 CSV/Excel 导出功能
5. **列显示控制**：允许用户自定义显示/隐藏列

## 相关文档

- [Grid.js 官方文档](https://gridjs.io/)
- [Bootstrap 表格组件](https://getbootstrap.com/docs/5.3/content/tables/)
- [Flatly 主题规范](https://bootswatch.com/flatly/)
- [项目 CSS 变量系统](../app/static/css/variables.css)

## 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2025-11-24 | 1.0 | 初始文档创建 | - |

---

**文档维护**：本文档应随重构进度实时更新，记录实际遇到的问题和解决方案。
