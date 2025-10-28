# UI 状态管理现成库推荐

**针对问题**: 替代重复的 `showLoadingState`、`hideLoadingState` 等函数

---

## 一、加载状态管理库

### 1.1 Ladda（按钮加载状态）⭐⭐⭐⭐⭐ 强烈推荐

**官网**: https://ladda.dev/  
**GitHub**: https://github.com/hakimel/Ladda  
**大小**: 5KB  

**特点**:
- ✅ 专门为按钮设计的加载状态
- ✅ 内置多种动画效果
- ✅ 自动禁用按钮
- ✅ 进度条支持
- ✅ Bootstrap 兼容

**CDN**:
```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/ladda@2/dist/ladda.min.css">
<script src="https://cdn.jsdelivr.net/npm/ladda@2/dist/ladda.min.js"></script>
```

**使用示例**（直接替代你的代码）:

```html
<!-- HTML: 添加 data 属性 -->
<button class="ladda-button btn btn-primary" data-style="expand-right">
    <span class="ladda-label">创建凭据</span>
</button>
```

```javascript
// JavaScript: 简单到令人发指
const button = document.querySelector('.ladda-button');
const l = Ladda.create(button);

// 之前：自己写
function showLoadingState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>创建中...';
    submitBtn.disabled = true;
}

function hideLoadingState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.innerHTML = '创建凭据';
    submitBtn.disabled = false;
}

// 之后：使用 Ladda
l.start();  // 开始加载
// ... 执行操作
l.stop();   // 停止加载

// 或者带进度
l.setProgress(0.5);  // 50%
```

**高级用法**:
```javascript
// 自动绑定所有按钮
Ladda.bind('.ladda-button');

// 与 Axios 集成
const l = Ladda.create(button);
l.start();

try {
    const result = await http.post('/api/xxx', data);
    notify.success(result.message);
} finally {
    l.stop();  // 确保停止
}

// 不同的动画效果
<button data-style="expand-right">向右展开</button>
<button data-style="expand-up">向上展开</button>
<button data-style="slide-left">左滑</button>
<button data-style="zoom-in">缩放</button>
```

**效果演示**: https://ladda.dev/ （非常酷炫）

**替代效果**:
- ❌ 可以删除所有 `showLoadingState(form)` 代码
- ❌ 可以删除所有 `hideLoadingState(form)` 代码
- ✅ 11 个文件 × 10 行 = **110 行代码可以删除**

---

### 1.2 SpinKit（纯 CSS 加载动画）⭐⭐⭐⭐

**官网**: https://tobiasahlin.com/spinkit/  
**GitHub**: https://github.com/tobiasahlin/SpinKit  
**大小**: 3KB (CSS only)

**特点**:
- ✅ 纯 CSS，零 JavaScript
- ✅ 11 种精美动画
- ✅ 可自定义颜色和大小

**CDN**:
```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/spinkit@2/spinkit.min.css">
```

**使用示例**:
```html
<!-- 放在容器中 -->
<div class="spinner-border" role="status">
    <span class="visually-hidden">加载中...</span>
</div>

<!-- SpinKit 的动画更好看 -->
<div class="sk-circle">
    <div class="sk-circle1 sk-child"></div>
    <div class="sk-circle2 sk-child"></div>
    <!-- ... -->
</div>
```

**替代容器加载**:
```javascript
// 之前：手动写 HTML
function showLoadingState() {
    const container = document.getElementById('logsContainer');
    container.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i>搜索中...</div>';
}

// 之后：使用 SpinKit
function showLoadingState() {
    const container = document.getElementById('logsContainer');
    container.innerHTML = '<div class="sk-circle">...</div>';
}
```

---

### 1.3 Spin.js（可编程的加载动画）⭐⭐⭐

**官网**: https://spin.js.org/  
**大小**: 4KB

**特点**:
- ✅ 完全用 JavaScript 生成
- ✅ 高度可定制
- ✅ 无图片依赖

**CDN**:
```html
<script src="https://cdn.jsdelivr.net/npm/spin.js@4/spin.umd.js"></script>
```

**使用示例**:
```javascript
const spinner = new Spinner({
    lines: 12,
    length: 7,
    width: 5,
    radius: 10,
    color: '#000'
});

// 在元素中显示
const target = document.getElementById('container');
spinner.spin(target);

// 停止
spinner.stop();
```

---

## 二、通知/Toast 库（已有 Toastr，但可以了解替代品）

你的项目已经使用 **Toastr**，这已经很好了。但如果想要更现代的替代品：

### 2.1 Notyf（现代化通知）⭐⭐⭐⭐⭐

**官网**: https://carlosroso.com/notyf/  
**大小**: 3KB  
**特点**:
- ✅ 动画流畅
- ✅ 移动端友好
- ✅ 支持自定义样式
- ✅ TypeScript 支持

**CDN**:
```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/notyf@3/notyf.min.css">
<script src="https://cdn.jsdelivr.net/npm/notyf@3/notyf.min.js"></script>
```

**使用示例**:
```javascript
const notyf = new Notyf({
    duration: 3000,
    position: {
        x: 'right',
        y: 'top',
    },
});

// 替代你的 notify.success
notyf.success('操作成功');
notyf.error('操作失败');

// 自定义
notyf.open({
    type: 'info',
    message: '这是一条消息',
    duration: 5000,
    dismissible: true
});
```

---

### 2.2 iziToast（功能最全）⭐⭐⭐⭐

**官网**: http://izitoast.marcelodolza.com/  
**大小**: 17KB  
**特点**:
- ✅ 功能非常全
- ✅ 主题丰富
- ✅ 可拖动
- ✅ 进度条

**CDN**:
```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/izitoast@1/dist/css/iziToast.min.css">
<script src="https://cdn.jsdelivr.net/npm/izitoast@1/dist/js/iziToast.min.js"></script>
```

**使用示例**:
```javascript
iziToast.success({
    title: '成功',
    message: '凭据创建成功',
    position: 'topRight'
});

iziToast.error({
    title: '错误',
    message: '操作失败',
    position: 'topRight'
});

// 带进度条
iziToast.show({
    timeout: 5000,
    progressBar: true,
    message: '5秒后自动关闭'
});
```

---

## 三、模态框/对话框库

### 3.1 SweetAlert2（现代化确认框）⭐⭐⭐⭐⭐ 强烈推荐

**官网**: https://sweetalert2.github.io/  
**大小**: 40KB（功能强大）  
**特点**:
- ✅ 美观的确认/警告框
- ✅ Promise 支持
- ✅ 可定制性极强
- ✅ 支持输入框、加载状态

**CDN**:
```html
<script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
```

**使用示例**（替代 confirm）:
```javascript
// 之前：原生 confirm 很丑
if (confirm('确定要删除吗？')) {
    deleteCredential(id);
}

// 之后：SweetAlert2
Swal.fire({
    title: '确定要删除吗？',
    text: "删除后无法恢复！",
    icon: 'warning',
    showCancelButton: true,
    confirmButtonColor: '#d33',
    cancelButtonColor: '#3085d6',
    confirmButtonText: '确定删除',
    cancelButtonText: '取消'
}).then((result) => {
    if (result.isConfirmed) {
        deleteCredential(id);
    }
});

// 带加载状态的确认框
Swal.fire({
    title: '正在删除...',
    didOpen: () => {
        Swal.showLoading();
    }
});

// 删除完成后
Swal.fire('已删除!', '凭据已成功删除', 'success');

// 输入框
const { value: text } = await Swal.fire({
    title: '请输入凭据名称',
    input: 'text',
    inputPlaceholder: '输入名称',
    showCancelButton: true
});
```

**效果**: 非常漂亮，比原生 confirm/alert 好太多

---

### 3.2 Micromodal（轻量级模态框）⭐⭐⭐⭐

**官网**: https://micromodal.vercel.app/  
**大小**: 3KB  
**特点**:
- ✅ ARIA 友好
- ✅ 动画流畅
- ✅ 零依赖
- ✅ 可嵌套

**CDN**:
```html
<script src="https://cdn.jsdelivr.net/npm/micromodal@0.4/dist/micromodal.min.js"></script>
```

**使用示例**:
```javascript
// 初始化
MicroModal.init();

// 打开模态框
MicroModal.show('modal-1');

// 关闭
MicroModal.close('modal-1');

// 带回调
MicroModal.show('modal-1', {
    onShow: modal => console.info(`${modal.id} 已显示`),
    onClose: modal => console.info(`${modal.id} 已关闭`),
});
```

---

## 四、工具提示 (Tooltip/Popover)

### 4.1 Tippy.js（最好的 Tooltip 库）⭐⭐⭐⭐⭐

**官网**: https://atomiks.github.io/tippyjs/  
**大小**: 20KB  
**特点**:
- ✅ 动画流畅
- ✅ 智能定位
- ✅ 主题丰富
- ✅ 支持 HTML 内容

**CDN**:
```html
<script src="https://unpkg.com/@popperjs/core@2"></script>
<script src="https://unpkg.com/tippy.js@6"></script>
```

**使用示例**:
```javascript
// 简单使用
tippy('#myButton', {
    content: "这是提示文本",
});

// 复杂内容
tippy('#myButton', {
    content: document.getElementById('template').innerHTML,
    allowHTML: true,
    interactive: true,
    theme: 'light-border',
    placement: 'top',
});

// 批量绑定
tippy('[data-tippy-content]');
```

```html
<button data-tippy-content="点击删除">删除</button>
```

---

## 五、骨架屏/占位符

### 5.1 placeholder-loading（CSS 骨架屏）⭐⭐⭐⭐

**GitHub**: https://github.com/zalog/placeholder-loading  
**大小**: 2KB (CSS only)  
**特点**:
- ✅ 纯 CSS
- ✅ 类似 Facebook/LinkedIn 的加载效果
- ✅ 响应式

**CDN**:
```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/placeholder-loading@0.6/dist/css/placeholder-loading.min.css">
```

**使用示例**:
```html
<!-- 加载时显示骨架屏 -->
<div class="ph-item">
    <div class="ph-col-12">
        <div class="ph-row">
            <div class="ph-col-4"></div>
            <div class="ph-col-8 empty"></div>
            <div class="ph-col-6"></div>
            <div class="ph-col-6 empty"></div>
        </div>
    </div>
</div>

<!-- 数据加载完成后替换 -->
```

---

## 六、整合方案：一站式 UI 库

如果你想要**一个库解决所有问题**，推荐：

### 6.1 UIkit（完整 UI 框架）⭐⭐⭐⭐

**官网**: https://getuikit.com/  
**大小**: 80KB (完整版)  
**特点**:
- ✅ 包含所有组件（模态框、通知、加载、表单等）
- ✅ 现代设计
- ✅ 响应式
- ❌ 可能和 Bootstrap 冲突

**CDN**:
```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/uikit@3/dist/css/uikit.min.css" />
<script src="https://cdn.jsdelivr.net/npm/uikit@3/dist/js/uikit.min.js"></script>
```

**使用示例**:
```javascript
// 通知
UIkit.notification('消息内容', {status: 'primary'});
UIkit.notification('成功消息', {status: 'success'});
UIkit.notification('错误消息', {status: 'danger'});

// 模态框
UIkit.modal('#my-modal').show();

// 确认框
UIkit.modal.confirm('确定删除吗？').then(() => {
    // 用户点击确定
}, () => {
    // 用户点击取消
});
```

---

### 6.2 Bulma + Bulma Extensions（推荐）⭐⭐⭐⭐

**官网**: https://bulma.io/  
**大小**: 20KB (CSS only, 需要配合 JS 扩展)  
**特点**:
- ✅ 纯 CSS 框架（不冲突）
- ✅ 现代、美观
- ✅ Flexbox 布局
- ✅ 有配套的 JS 扩展

**可以只使用部分组件**，不必全部引入。

---

## 七、推荐的最佳组合方案

### 方案 A：最小集合（推荐）⭐⭐⭐⭐⭐

```html
<!-- 按钮加载 -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/ladda@2/dist/ladda.min.css">
<script src="https://cdn.jsdelivr.net/npm/ladda@2/dist/ladda.min.js"></script>

<!-- 顶部进度条（已推荐） -->
<link rel="stylesheet" href="https://unpkg.com/nprogress@0.2.0/nprogress.css"/>
<script src="https://unpkg.com/nprogress@0.2.0/nprogress.js"></script>

<!-- 美化确认框 -->
<script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>

<!-- 通知（保留现有 Toastr 或换成 Notyf） -->
<!-- 已有 Toastr，继续使用 -->
```

**总大小**: ~50KB (gzip 后 ~15KB)

**效果**:
- ✅ 删除所有 `showLoadingState` 函数
- ✅ 删除所有 `hideLoadingState` 函数  
- ✅ 删除所有原生 `confirm` 
- ✅ 减少 **150+ 行代码**

---

### 方案 B：完整替换（如果想全面升级）

```html
<!-- 加载状态 -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/ladda@2/dist/ladda.min.css">
<script src="https://cdn.jsdelivr.net/npm/ladda@2/dist/ladda.min.js"></script>
<link rel="stylesheet" href="https://unpkg.com/nprogress@0.2.0/nprogress.css"/>
<script src="https://unpkg.com/nprogress@0.2.0/nprogress.js"></script>

<!-- 通知 -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/notyf@3/notyf.min.css">
<script src="https://cdn.jsdelivr.net/npm/notyf@3/notyf.min.js"></script>

<!-- 对话框 -->
<script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>

<!-- 提示框 -->
<script src="https://unpkg.com/@popperjs/core@2"></script>
<script src="https://unpkg.com/tippy.js@6"></script>
```

**总大小**: ~100KB (gzip 后 ~30KB)

---

## 八、快速实施指南

### Step 1: 添加 CDN（5分钟）

在 `templates/base.html` 的 `<head>` 中添加：

```html
<!-- Ladda - 按钮加载状态 -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/ladda@2/dist/ladda.min.css">
<script src="https://cdn.jsdelivr.net/npm/ladda@2/dist/ladda.min.js"></script>

<!-- NProgress - 页面加载进度 -->
<link rel="stylesheet" href="https://unpkg.com/nprogress@0.2.0/nprogress.css"/>
<script src="https://unpkg.com/nprogress@0.2.0/nprogress.js"></script>

<!-- SweetAlert2 - 美化确认框 -->
<script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
```

---

### Step 2: 修改按钮 HTML（2分钟）

```html
<!-- 之前 -->
<button type="submit" class="btn btn-primary">创建凭据</button>

<!-- 之后：添加 Ladda 属性 -->
<button type="submit" class="ladda-button btn btn-primary" data-style="expand-right">
    <span class="ladda-label">创建凭据</span>
</button>
```

---

### Step 3: 修改 JavaScript（5分钟）

```javascript
// credentials/create.js

// 之前：150+ 行的验证和加载状态代码
function showLoadingState(form) { /* ... */ }
function hideLoadingState(form) { /* ... */ }
function validateForm() { /* ... */ }

// 之后：使用库，只需 20 行
document.addEventListener('DOMContentLoaded', function() {
    const button = document.querySelector('.ladda-button');
    const l = Ladda.create(button);
    
    // 表单验证（使用 Just-Validate）
    const validation = new JustValidate('#credentialForm');
    validation
        .addField('#name', [{ rule: 'required' }])
        .addField('#username', [{ rule: 'required' }])
        .onSuccess(async (event) => {
            event.preventDefault();
            l.start(); // 开始加载
            
            try {
                const data = new FormData(event.target);
                const result = await http.post('/api/credentials', Object.fromEntries(data));
                
                // 成功
                Swal.fire('成功!', result.message, 'success').then(() => {
                    window.location.href = '/credentials';
                });
            } catch (error) {
                l.stop(); // 停止加载
            }
        });
});
```

---

### Step 4: 替换 confirm（1分钟）

```javascript
// 之前：到处都是这种代码
if (confirm('确定要删除吗？')) {
    deleteCredential(id);
}

// 之后：全局替换为 SweetAlert2
Swal.fire({
    title: '确定要删除吗？',
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: '确定',
    cancelButtonText: '取消'
}).then((result) => {
    if (result.isConfirmed) {
        deleteCredential(id);
    }
});
```

---

## 九、总结对比

| 功能 | 之前（自己写） | 之后（用库） | 节省 |
|------|--------------|-------------|------|
| 按钮加载 | 10行 × 11文件 = 110行 | Ladda 1行 | 110行 |
| 确认框 | confirm() 丑陋 | SweetAlert2 美观 | ∞ |
| 进度条 | 无 | NProgress 自动 | 新增功能 |
| 表单验证 | 200行 | Just-Validate 20行 | 180行 |
| **总计** | **~500行** | **~30行** | **470行** |

---

## 十、最终推荐

### ⭐⭐⭐⭐⭐ 立即使用这三个库：

1. **Ladda** - 替代所有按钮加载状态（5KB）
2. **SweetAlert2** - 替代所有 confirm/alert（40KB）
3. **NProgress** - 页面加载进度条（2KB）

**加上之前推荐的**:
4. **Axios** - HTTP 客户端
5. **Just-Validate** - 表单验证

**总大小**: ~70KB (gzip 后 ~20KB)  
**节省代码**: ~1,500 行  
**时间投入**: 半天  

**ROI**: 非常高！

---

**现在可以立即开始了！** 🚀
