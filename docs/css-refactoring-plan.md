# CSS 重构计划

## 🎯 目标
- 减少自定义CSS代码量（目前11,693行）
- 提高样式一致性和可维护性
- 利用Bootstrap组件和工具类
- 建立统一的设计系统

## 📊 当前状况分析
- **CSS文件数量**: 26个
- **总代码行数**: 11,693行
- **主要问题**:
  - 大量重复的样式定义
  - 每个页面都有独立的CSS文件
  - 缺乏统一的设计规范
  - 过度自定义，没有充分利用Bootstrap

## 🔧 重构策略

### 阶段1: 建立设计系统
1. **创建统一的CSS变量文件** (`app/static/css/variables.css`)
   - 颜色系统
   - 字体系统
   - 间距系统
   - 阴影系统

2. **创建通用组件样式** (`app/static/css/components.css`)
   - 卡片组件
   - 按钮变体
   - 表单组件
   - 导航组件

### 阶段2: 页面样式整合
1. **合并相似页面的样式**
   - 列表页面通用样式
   - 表单页面通用样式
   - 详情页面通用样式

2. **利用Bootstrap工具类替换自定义样式**
   - 间距: `m-*`, `p-*`
   - 颜色: `text-*`, `bg-*`
   - 布局: `d-*`, `flex-*`

### 阶段3: 组件化
1. **提取可复用的UI组件**
   - 统计卡片
   - 数据表格
   - 搜索表单
   - 状态徽章

2. **使用CSS类命名规范** (BEM方法论)
   - `.component__element--modifier`

## 📋 实施计划

### 第一步: 创建基础文件
- [ ] `css/variables.css` - CSS变量定义
- [ ] `css/base.css` - 基础样式重置
- [ ] `css/components.css` - 通用组件
- [ ] `css/utilities.css` - 工具类扩展

### 第二步: 页面样式分析和重构
- [ ] 分析每个页面的样式使用情况
- [ ] 识别可以用Bootstrap类替换的样式
- [ ] 提取共同的样式模式

### 第三步: 逐步迁移
- [ ] 从最简单的页面开始
- [ ] 逐个页面进行样式重构
- [ ] 删除不再需要的CSS文件

## 🎨 设计系统规范

### 颜色系统
```css
:root {
  /* 主色调 */
  --primary: #667eea;
  --secondary: #764ba2;
  
  /* 功能色 */
  --success: #28a745;
  --danger: #dc3545;
  --warning: #ffc107;
  --info: #17a2b8;
  
  /* 中性色 */
  --gray-50: #f8f9fa;
  --gray-100: #e9ecef;
  --gray-200: #dee2e6;
  --gray-300: #ced4da;
  --gray-400: #adb5bd;
  --gray-500: #6c757d;
  --gray-600: #495057;
  --gray-700: #343a40;
  --gray-800: #212529;
  --gray-900: #000000;
}
```

### 组件规范
```css
/* 卡片组件 */
.card-custom {
  border: none;
  border-radius: 0.75rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

/* 按钮变体 */
.btn-gradient-primary {
  background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
  border: none;
}
```

## 📈 预期效果
- **代码减少**: 预计减少60-70%的CSS代码
- **维护性**: 统一的样式系统，易于维护
- **一致性**: 统一的视觉风格
- **性能**: 减少CSS文件数量，提高加载速度

## 🚀 开始实施
建议从创建基础的设计系统文件开始，然后逐步重构现有页面。