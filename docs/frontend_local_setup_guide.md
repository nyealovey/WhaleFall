# 前端库本地化安装指南

**目的**: 将所有推荐的前端库下载到本地，避免依赖 CDN

---

## 一、快速开始

### 方法 1：使用自动化脚本（推荐）⭐⭐⭐⭐⭐

**只需一行命令**：

```bash
cd /Users/apple/Taifish/TaifishingV4
bash scripts/download_vendor_libs.sh
```

脚本会自动：
1. 下载 6 个库到 `app/static/vendor/`
2. 创建版本信息文件
3. 验证所有文件完整性

**预计时间**: 1-2 分钟（取决于网络速度）

---

### 方法 2：手动下载（备用）

如果脚本失败，可以手动下载：

#### 1. Axios
```bash
cd app/static/vendor
mkdir -p axios
curl -L -o axios/axios.min.js https://cdn.jsdelivr.net/npm/axios@1.6.2/dist/axios.min.js
```

#### 2. Just-Validate
```bash
mkdir -p just-validate
curl -L -o just-validate/just-validate.production.min.js https://unpkg.com/just-validate@4.3.0/dist/just-validate.production.min.js
```

#### 3. NProgress
```bash
mkdir -p nprogress
curl -L -o nprogress/nprogress.js https://unpkg.com/nprogress@0.2.0/nprogress.js
curl -L -o nprogress/nprogress.css https://unpkg.com/nprogress@0.2.0/nprogress.css
```

#### 4. Ladda
```bash
mkdir -p ladda
curl -L -o ladda/ladda.min.js https://cdn.jsdelivr.net/npm/ladda@2.0.0/dist/ladda.min.js
curl -L -o ladda/ladda.min.css https://cdn.jsdelivr.net/npm/ladda@2.0.0/dist/ladda.min.css
curl -L -o ladda/spin.min.js https://cdn.jsdelivr.net/npm/spin.js@4.1.1/spin.umd.js
```

#### 5. SweetAlert2
```bash
mkdir -p sweetalert2
curl -L -o sweetalert2/sweetalert2.all.min.js https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.all.min.js
```

#### 6. Tom Select（可选）
```bash
mkdir -p tom-select
curl -L -o tom-select/tom-select.complete.min.js https://cdn.jsdelivr.net/npm/tom-select@2.3.1/dist/js/tom-select.complete.min.js
curl -L -o tom-select/tom-select.bootstrap5.min.css https://cdn.jsdelivr.net/npm/tom-select@2.3.1/dist/css/tom-select.bootstrap5.min.css
```

---

## 二、验证安装

### 检查目录结构

```bash
cd app/static/vendor
tree -L 2
```

**期望的结构**：
```
vendor/
├── axios/
│   ├── axios.min.js
│   └── axios.min.js.map
├── just-validate/
│   └── just-validate.production.min.js
├── nprogress/
│   ├── nprogress.js
│   └── nprogress.css
├── ladda/
│   ├── ladda.min.js
│   ├── ladda.min.css
│   └── spin.min.js
├── sweetalert2/
│   └── sweetalert2.all.min.js
├── tom-select/
│   ├── tom-select.complete.min.js
│   └── tom-select.bootstrap5.min.css
├── bootstrap/      (已有)
├── jquery/         (已有)
├── toastr/         (已有)
├── chartjs/        (已有)
├── fontawesome/    (已有)
└── VERSIONS.txt    (新生成)
```

### 检查文件大小

```bash
cd app/static/vendor
du -sh *
```

**期望输出**：
```
 32K    axios
 16K    just-validate
  8K    nprogress
 20K    ladda
 80K    sweetalert2
 40K    tom-select
```

---

## 三、更新 base.html

### 修改模板引用

编辑 `app/templates/base.html`，将 CDN 链接改为本地路径：

```html
<head>
    <!-- ... 现有的引用 ... -->
    
    <!-- 现有的库（保持不变） -->
    <script src="{{ url_for('static', filename='vendor/jquery/jquery.min.js') }}"></script>
    <script src="{{ url_for('static', filename='vendor/bootstrap/bootstrap.bundle.min.js') }}"></script>
    <link rel="stylesheet" href="{{ url_for('static', filename='vendor/bootstrap/bootstrap.min.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='vendor/toastr/toastr.min.css') }}">
    <script src="{{ url_for('static', filename='vendor/toastr/toastr.min.js') }}"></script>
    <link href="{{ url_for('static', filename='vendor/fontawesome/css/all.min.css') }}" rel="stylesheet">
    
    <!-- 新增：Axios - HTTP 客户端 -->
    <script src="{{ url_for('static', filename='vendor/axios/axios.min.js') }}"></script>
    
    <!-- 新增：Just-Validate - 表单验证 -->
    <script src="{{ url_for('static', filename='vendor/just-validate/just-validate.production.min.js') }}"></script>
    
    <!-- 新增：NProgress - 加载进度条 -->
    <link rel="stylesheet" href="{{ url_for('static', filename='vendor/nprogress/nprogress.css') }}">
    <script src="{{ url_for('static', filename='vendor/nprogress/nprogress.js') }}"></script>
    
    <!-- 新增：Ladda - 按钮加载状态 -->
    <link rel="stylesheet" href="{{ url_for('static', filename='vendor/ladda/ladda.min.css') }}">
    <script src="{{ url_for('static', filename='vendor/ladda/spin.min.js') }}"></script>
    <script src="{{ url_for('static', filename='vendor/ladda/ladda.min.js') }}"></script>
    
    <!-- 新增：SweetAlert2 - 美化对话框 -->
    <script src="{{ url_for('static', filename='vendor/sweetalert2/sweetalert2.all.min.js') }}"></script>
    
    <!-- 可选：Tom Select - 标签选择器 -->
    <!-- <link rel="stylesheet" href="{{ url_for('static', filename='vendor/tom-select/tom-select.bootstrap5.min.css') }}"> -->
    <!-- <script src="{{ url_for('static', filename='vendor/tom-select/tom-select.complete.min.js') }}"></script> -->
</head>
```

---

## 四、创建配置文件

### 创建 common/config.js

```bash
cd app/static/js/common
touch config.js
```

**内容**：

```javascript
/**
 * 前端库全局配置
 * 配置 Axios、NProgress 等库的默认行为
 */
(function() {
    'use strict';
    
    // =========================================================================
    // Axios 配置
    // =========================================================================
    if (typeof axios !== 'undefined') {
        // 创建 Axios 实例
        window.http = axios.create({
            baseURL: window.location.origin,
            timeout: 30000,
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        // 请求拦截器：自动添加 CSRF token
        window.http.interceptors.request.use(
            config => {
                const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
                if (csrfToken) {
                    config.headers['X-CSRF-Token'] = csrfToken;
                }
                
                // 启动 NProgress
                if (typeof NProgress !== 'undefined') {
                    NProgress.start();
                }
                
                return config;
            },
            error => {
                if (typeof NProgress !== 'undefined') {
                    NProgress.done();
                }
                return Promise.reject(error);
            }
        );
        
        // 响应拦截器：统一错误处理
        window.http.interceptors.response.use(
            response => {
                // 完成 NProgress
                if (typeof NProgress !== 'undefined') {
                    NProgress.done();
                }
                
                // 返回数据
                return response.data;
            },
            error => {
                // 完成 NProgress
                if (typeof NProgress !== 'undefined') {
                    NProgress.done();
                }
                
                // 统一错误提示
                const message = error.response?.data?.error 
                    || error.response?.data?.message 
                    || error.message 
                    || '请求失败';
                
                if (typeof notify !== 'undefined') {
                    notify.error(message);
                } else if (typeof toastr !== 'undefined') {
                    toastr.error(message);
                }
                
                return Promise.reject(error);
            }
        );
        
        console.info('✓ Axios 配置完成');
    }
    
    // =========================================================================
    // NProgress 配置
    // =========================================================================
    if (typeof NProgress !== 'undefined') {
        NProgress.configure({
            showSpinner: false,  // 不显示右上角的旋转图标
            minimum: 0.1,
            speed: 400,
            trickle: true,
            trickleSpeed: 200
        });
        
        console.info('✓ NProgress 配置完成');
    }
    
    // =========================================================================
    // SweetAlert2 默认配置
    // =========================================================================
    if (typeof Swal !== 'undefined') {
        // 设置中文按钮文本
        Swal.mixin({
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            customClass: {
                confirmButton: 'btn btn-primary mx-2',
                cancelButton: 'btn btn-secondary mx-2'
            },
            buttonsStyling: false
        });
        
        // 创建全局简化函数
        window.confirmDelete = function(title = '确定要删除吗？', text = '删除后无法恢复！') {
            return Swal.fire({
                title: title,
                text: text,
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#dc3545',
                confirmButtonText: '确定删除',
                cancelButtonText: '取消'
            });
        };
        
        window.showSuccess = function(message, title = '成功') {
            return Swal.fire({
                title: title,
                text: message,
                icon: 'success',
                confirmButtonText: '确定'
            });
        };
        
        window.showError = function(message, title = '错误') {
            return Swal.fire({
                title: title,
                text: message,
                icon: 'error',
                confirmButtonText: '确定'
            });
        };
        
        console.info('✓ SweetAlert2 配置完成');
    }
    
    // =========================================================================
    // Ladda 配置
    // =========================================================================
    if (typeof Ladda !== 'undefined') {
        // 自动绑定所有带 ladda-button 类的按钮
        Ladda.bind('.ladda-button', { timeout: 30000 });
        
        console.info('✓ Ladda 配置完成');
    }
    
    console.info('=================================');
    console.info('前端库配置加载完成');
    console.info('可用对象: window.http, window.confirmDelete, window.showSuccess, window.showError');
    console.info('=================================');
    
})();
```

### 在 base.html 中引入配置

```html
<head>
    <!-- ... 所有库的引用 ... -->
    
    <!-- 配置文件（必须在所有库之后） -->
    <script src="{{ url_for('static', filename='js/common/config.js') }}"></script>
</head>
```

---

## 五、测试验证

### 创建测试页面

```bash
touch app/templates/test_libs.html
```

**内容**：

```html
{% extends "base.html" %}

{% block title %}前端库测试{% endblock %}

{% block content %}
<div class="container mt-5">
    <h1>前端库功能测试</h1>
    
    <div class="row mt-4">
        <!-- 1. Axios 测试 -->
        <div class="col-md-6 mb-3">
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">1. Axios 测试</h5>
                    <button class="btn btn-primary" onclick="testAxios()">测试 HTTP 请求</button>
                    <p id="axios-result" class="mt-2"></p>
                </div>
            </div>
        </div>
        
        <!-- 2. Just-Validate 测试 -->
        <div class="col-md-6 mb-3">
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">2. Just-Validate 测试</h5>
                    <form id="test-form">
                        <input type="text" id="test-input" class="form-control" placeholder="必填项">
                        <div class="invalid-feedback"></div>
                        <button type="submit" class="btn btn-primary mt-2">提交</button>
                    </form>
                </div>
            </div>
        </div>
        
        <!-- 3. Ladda 测试 -->
        <div class="col-md-6 mb-3">
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">3. Ladda 测试</h5>
                    <button class="ladda-button btn btn-success" data-style="expand-right" onclick="testLadda(this)">
                        <span class="ladda-label">点击测试加载</span>
                    </button>
                </div>
            </div>
        </div>
        
        <!-- 4. SweetAlert2 测试 -->
        <div class="col-md-6 mb-3">
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">4. SweetAlert2 测试</h5>
                    <button class="btn btn-warning" onclick="testSwal()">测试对话框</button>
                </div>
            </div>
        </div>
        
        <!-- 5. NProgress 测试 -->
        <div class="col-md-6 mb-3">
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">5. NProgress 测试</h5>
                    <button class="btn btn-info" onclick="testNProgress()">测试进度条</button>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
// 1. 测试 Axios
function testAxios() {
    const result = document.getElementById('axios-result');
    result.textContent = '请求中...';
    
    // 测试获取当前页面
    http.get('/health')
        .then(data => {
            result.textContent = '✓ Axios 工作正常！';
            result.className = 'mt-2 text-success';
        })
        .catch(error => {
            result.textContent = '✗ Axios 测试失败';
            result.className = 'mt-2 text-danger';
        });
}

// 2. 测试 Just-Validate
document.addEventListener('DOMContentLoaded', function() {
    const validation = new JustValidate('#test-form');
    validation
        .addField('#test-input', [
            {
                rule: 'required',
                errorMessage: '此字段为必填项'
            }
        ])
        .onSuccess((event) => {
            event.preventDefault();
            notify.success('✓ Just-Validate 工作正常！');
        });
});

// 3. 测试 Ladda
function testLadda(button) {
    const l = Ladda.create(button);
    l.start();
    
    setTimeout(() => {
        l.stop();
        notify.success('✓ Ladda 工作正常！');
    }, 2000);
}

// 4. 测试 SweetAlert2
function testSwal() {
    Swal.fire({
        title: '测试对话框',
        text: '✓ SweetAlert2 工作正常！',
        icon: 'success',
        confirmButtonText: '确定'
    });
}

// 5. 测试 NProgress
function testNProgress() {
    NProgress.start();
    setTimeout(() => {
        NProgress.set(0.4);
    }, 500);
    setTimeout(() => {
        NProgress.set(0.8);
    }, 1000);
    setTimeout(() => {
        NProgress.done();
        notify.success('✓ NProgress 工作正常！');
    }, 1500);
}
</script>
{% endblock %}
```

### 添加路由

```python
# app/routes/main.py
@main_bp.route('/test-libs')
def test_libs():
    """测试前端库页面"""
    return render_template('test_libs.html')
```

### 访问测试页面

```
http://localhost:5001/test-libs
```

逐个点击测试按钮，确保所有库都正常工作。

---

## 六、常见问题

### Q1: 下载速度很慢怎么办？

**A**: 可以使用国内镜像：

```bash
# 使用 npmcdn.com（国内镜像）
curl -L -o axios.min.js https://npmcdn.com/axios@1.6.2/dist/axios.min.js

# 或使用 unpkg.com
curl -L -o axios.min.js https://unpkg.com/axios@1.6.2/dist/axios.min.js
```

---

### Q2: 文件下载失败怎么办？

**A**: 手动从浏览器下载：

1. 在浏览器中打开 CDN 链接（例如 https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js）
2. 右键 → 另存为
3. 保存到对应的 vendor 目录

---

### Q3: 如何更新库的版本？

**A**: 修改下载脚本中的版本号，重新运行：

```bash
# 编辑 scripts/download_vendor_libs.sh
# 将版本号改为最新版本，例如：
# axios@1.6.2 → axios@1.7.0

# 重新运行脚本
bash scripts/download_vendor_libs.sh
```

---

### Q4: 可以选择性安装某些库吗？

**A**: 可以，注释掉不需要的部分：

```bash
# 编辑 scripts/download_vendor_libs.sh
# 注释掉不需要的库，例如：
# echo -e "${GREEN}[6/6] 下载 Tom Select (可选)...${NC}"
# mkdir -p tom-select
# ...
```

---

### Q5: 如何验证库是否加载成功？

**A**: 打开浏览器控制台（F12），输入：

```javascript
// 检查各个库是否存在
console.log('Axios:', typeof axios);      // 应该输出 'function'
console.log('JustValidate:', typeof JustValidate);  // 'function'
console.log('NProgress:', typeof NProgress);  // 'object'
console.log('Ladda:', typeof Ladda);      // 'object'
console.log('Swal:', typeof Swal);        // 'object'
console.log('http:', typeof http);        // 'object'
```

所有输出都不应该是 `'undefined'`。

---

## 七、目录结构总览

最终的目录结构：

```
app/static/
├── vendor/
│   ├── axios/
│   │   ├── axios.min.js
│   │   └── axios.min.js.map
│   ├── just-validate/
│   │   └── just-validate.production.min.js
│   ├── nprogress/
│   │   ├── nprogress.js
│   │   └── nprogress.css
│   ├── ladda/
│   │   ├── ladda.min.js
│   │   ├── ladda.min.css
│   │   └── spin.min.js
│   ├── sweetalert2/
│   │   └── sweetalert2.all.min.js
│   ├── tom-select/
│   │   ├── tom-select.complete.min.js
│   │   └── tom-select.bootstrap5.min.css
│   ├── bootstrap/ (已有)
│   ├── jquery/ (已有)
│   ├── toastr/ (已有)
│   ├── chartjs/ (已有)
│   ├── fontawesome/ (已有)
│   └── VERSIONS.txt
├── js/
│   ├── common/
│   │   ├── config.js (新建)
│   │   ├── notify.js (已有)
│   │   ├── csrf-utils.js (已有)
│   │   └── time-utils.js (已有)
│   ├── pages/ (已有)
│   └── components/ (已有)
└── css/ (已有)
```

---

## 八、下一步

安装完成后，可以开始重构：

1. ✅ **第1周**：在一个简单页面（如 auth/login.js）试点新方案
2. ✅ **第2-3周**：迁移 credentials 和 instances 相关页面
3. ✅ **第4周**：评估效果，决定是否全面推广

详细的重构指南见：
- `docs/javascript_refactoring_analysis.md` - 重构策略
- `docs/javascript_refactoring_libraries.md` - 库使用指南

---

## 九、总结

### 安装清单

- [x] 运行下载脚本
- [ ] 验证文件完整性
- [ ] 更新 base.html
- [ ] 创建 config.js
- [ ] 访问测试页面
- [ ] 开始重构第一个页面

### 预期效果

- ✅ 所有库本地化，不依赖 CDN
- ✅ 加载速度更快（本地访问）
- ✅ 离线开发友好
- ✅ 版本可控，不会突然失效

---

**现在可以开始了！** 🚀
