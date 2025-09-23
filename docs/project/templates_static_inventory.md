# 鲸落 (TaifishV4) - 模板与静态文件清单

## 项目概述
本文档详细列出了鲸落 (TaifishV4) 项目中所有的模板文件和静态资源文件，包括HTML模板、CSS样式表、JavaScript脚本、图片资源等。

## 文件统计概览

### 模板文件 (Templates)
- **总文件数**: 32个HTML模板文件
- **主要目录**: 12个功能模块目录
- **基础文件**: 2个基础模板文件

### 静态文件 (Static)
- **CSS文件**: 21个样式文件
- **JavaScript文件**: 29个脚本文件
- **图片文件**: 6个图片资源
- **第三方库**: Bootstrap、jQuery、Chart.js、Font Awesome

---

## 模板文件清单 (Templates)

### 根目录模板文件
```
templates/
├── about.html                    # 关于页面
└── base.html                     # 基础模板
```

### 功能模块模板文件

#### 1. 账户分类管理 (account_classification/)
```
account_classification/
└── management.html               # 账户分类管理页面
```

#### 2. 账户管理 (accounts/)
```
accounts/
├── list.html                     # 账户列表页面
├── statistics.html               # 账户统计页面
├── sync_details.html             # 同步详情页面
└── sync_records.html             # 同步记录页面
```

#### 3. 管理员功能 (admin/)
```
admin/
└── management.html               # 管理员管理页面
```

#### 4. 用户认证 (auth/)
```
auth/
├── change_password.html          # 修改密码页面
├── login.html                    # 登录页面
└── profile.html                  # 用户资料页面
```

#### 5. 组件模板 (components/)
```
components/
├── permission_modal.html         # 权限模态框组件
└── tag_selector.html             # 标签选择器组件
```

#### 6. 凭据管理 (credentials/)
```
credentials/
├── create.html                   # 创建凭据页面
├── detail.html                   # 凭据详情页面
├── edit.html                     # 编辑凭据页面
└── list.html                     # 凭据列表页面
```

#### 7. 仪表板 (dashboard/)
```
dashboard/
└── overview.html                 # 仪表板概览页面
```

#### 8. 数据库类型 (database_types/)
```
database_types/
└── list.html                     # 数据库类型列表页面
```

#### 9. 错误页面 (errors/)
```
errors/
└── error.html                    # 通用错误页面
```

#### 10. 实例管理 (instances/)
```
instances/
├── create.html                   # 创建实例页面
├── detail.html                   # 实例详情页面
├── edit.html                     # 编辑实例页面
├── list.html                     # 实例列表页面
└── statistics.html               # 实例统计页面
```

#### 11. 日志管理 (logs/)
```
logs/
├── dashboard.html                # 日志仪表板页面
├── detail.html                   # 日志详情页面
└── statistics.html               # 日志统计页面
```

#### 12. 宏定义 (macros/)
```
macros/
└── environment_macro.html        # 环境宏定义
```

#### 13. 主页面 (main/)
```
main/
└── (空目录)
```

#### 14. 任务调度 (scheduler/)
```
scheduler/
└── management.html               # 任务调度管理页面
```

#### 15. 同步会话 (sync_sessions/)
```
sync_sessions/
└── management.html               # 同步会话管理页面
```

#### 16. 标签管理 (tags/)
```
tags/
├── create.html                   # 创建标签页面
├── edit.html                     # 编辑标签页面
└── index.html                    # 标签索引页面
```

#### 17. 用户管理 (user_management/)
```
user_management/
└── management.html               # 用户管理页面
```

---

## 静态文件清单 (Static)

### CSS样式文件

#### 根目录CSS文件
```
static/css/
├── account_classification.css    # 账户分类样式
└── components/
    └── tag_selector.css          # 标签选择器组件样式
```

#### 页面专用CSS文件 (pages/)
```
static/css/pages/
├── about.css                     # 关于页面样式
├── accounts/
│   ├── list.css                  # 账户列表样式
│   └── sync_records.css          # 同步记录样式
├── admin/
│   └── management.css            # 管理员管理样式
├── auth/
│   ├── change_password.css       # 修改密码样式
│   └── login.css                 # 登录页面样式
├── credentials/
│   ├── create.css                # 创建凭据样式
│   ├── edit.css                  # 编辑凭据样式
│   └── list.css                  # 凭据列表样式
├── dashboard/
│   └── overview.css              # 仪表板概览样式
├── instances/
│   ├── create.css                # 创建实例样式
│   ├── detail.css                # 实例详情样式
│   ├── list.css                  # 实例列表样式
│   └── statistics.css            # 实例统计样式
├── logs/
│   └── dashboard.css             # 日志仪表板样式
├── scheduler/
│   └── management.css            # 任务调度管理样式
├── sync_sessions/
│   └── management.css            # 同步会话管理样式
├── tags/
│   └── index.css                 # 标签索引样式
└── user_management/
    └── management.css            # 用户管理样式
```

### JavaScript脚本文件

#### 根目录JavaScript文件
```
static/js/
├── account_classification.js     # 账户分类功能脚本
├── common/                       # 通用工具脚本
│   ├── alert-utils.js            # 警告工具
│   ├── console-utils.js          # 控制台工具
│   ├── csrf-utils.js             # CSRF工具
│   ├── permission-modal.js       # 权限模态框
│   ├── permission-viewer.js      # 权限查看器
│   └── time-utils.js             # 时间工具
├── components/                   # 组件脚本
│   ├── permission-button.js      # 权限按钮组件
│   └── tag_selector.js           # 标签选择器组件
└── debug/                        # 调试脚本
    └── permission-debug.js       # 权限调试工具
```

#### 页面专用JavaScript文件 (pages/)
```
static/js/pages/
├── accounts/
│   ├── list.js                   # 账户列表功能
│   └── sync_records.js           # 同步记录功能
├── admin/
│   └── management.js             # 管理员管理功能
├── auth/
│   ├── change_password.js        # 修改密码功能
│   └── login.js                  # 登录功能
├── credentials/
│   ├── create.js                 # 创建凭据功能
│   ├── edit.js                   # 编辑凭据功能
│   └── list.js                   # 凭据列表功能
├── dashboard/
│   └── overview.js               # 仪表板概览功能
├── instances/
│   ├── create.js                 # 创建实例功能
│   ├── detail.js                 # 实例详情功能
│   ├── edit.js                   # 编辑实例功能
│   ├── list.js                   # 实例列表功能
│   └── statistics.js             # 实例统计功能
├── logs/
│   └── dashboard.js              # 日志仪表板功能
├── scheduler/
│   └── management.js             # 任务调度管理功能
├── sync_sessions/
│   └── management.js             # 同步会话管理功能
├── tags/
│   └── index.js                  # 标签索引功能
└── user_management/
    └── management.js             # 用户管理功能
```

### 图片资源文件
```
static/img/
├── apple-touch-icon-precomposed.png  # Apple触摸图标
├── apple-touch-icon.png              # Apple触摸图标
├── favicon.png                       # 网站图标
├── logo_backup.png                   # 备用Logo
├── logo.png                          # 主Logo
└── logo.webp                         # WebP格式Logo
```

### 第三方库文件 (vendor/)

#### Bootstrap框架
```
static/vendor/bootstrap/
├── bootstrap.bundle.min.js        # Bootstrap JavaScript包
├── bootstrap.bundle.min.js.map    # Bootstrap JavaScript映射文件
├── bootstrap.min.css              # Bootstrap CSS样式
└── bootstrap.min.css.map          # Bootstrap CSS映射文件
```

#### Chart.js图表库
```
static/vendor/chartjs/
└── chart.min.js                   # Chart.js图表库
```

#### jQuery库
```
static/vendor/jquery/
└── jquery.min.js                  # jQuery库
```

#### Font Awesome图标库
```
static/vendor/fontawesome/
├── css/                           # CSS样式文件
│   ├── all.css                    # 完整样式
│   ├── all.min.css                # 完整样式(压缩)
│   ├── brands.css                 # 品牌图标样式
│   ├── brands.min.css             # 品牌图标样式(压缩)
│   ├── fontawesome.css            # 核心样式
│   ├── fontawesome.min.css        # 核心样式(压缩)
│   ├── regular.css                # 常规图标样式
│   ├── regular.min.css            # 常规图标样式(压缩)
│   ├── solid.css                  # 实心图标样式
│   ├── solid.min.css              # 实心图标样式(压缩)
│   ├── svg-with-js.css            # SVG样式
│   ├── svg-with-js.min.css        # SVG样式(压缩)
│   ├── v4-font-face.css           # v4字体样式
│   ├── v4-shims.css               # v4兼容样式
│   ├── v5-font-face.css           # v5字体样式
│   └── fontawesome.min.css        # 主样式文件
├── js/                            # JavaScript文件
│   ├── all.js                     # 完整脚本
│   ├── all.min.js                 # 完整脚本(压缩)
│   ├── brands.js                  # 品牌图标脚本
│   ├── brands.min.js              # 品牌图标脚本(压缩)
│   ├── conflict-detection.js      # 冲突检测脚本
│   ├── conflict-detection.min.js  # 冲突检测脚本(压缩)
│   ├── fontawesome.js             # 核心脚本
│   ├── fontawesome.min.js         # 核心脚本(压缩)
│   ├── regular.js                 # 常规图标脚本
│   ├── regular.min.js             # 常规图标脚本(压缩)
│   ├── solid.js                   # 实心图标脚本
│   ├── solid.min.js               # 实心图标脚本(压缩)
│   ├── v4-shims.js                # v4兼容脚本
│   └── v4-shims.min.js            # v4兼容脚本(压缩)
├── less/                          # LESS源文件
│   ├── _animated.less             # 动画样式
│   ├── _bordered-pulled.less      # 边框样式
│   ├── _core.less                 # 核心样式
│   ├── _fixed-width.less          # 固定宽度样式
│   ├── _icons.less                # 图标样式
│   ├── _list.less                 # 列表样式
│   ├── _mixins.less               # 混合样式
│   ├── _rotated-flipped.less      # 旋转翻转样式
│   ├── _screen-reader.less        # 屏幕阅读器样式
│   ├── _shims.less                # 兼容样式
│   ├── _sizing.less               # 尺寸样式
│   ├── _stacked.less              # 堆叠样式
│   ├── _variables.less            # 变量定义
│   ├── brands.less                # 品牌图标
│   ├── fontawesome.less           # 主样式文件
│   ├── regular.less               # 常规图标
│   ├── solid.less                 # 实心图标
│   └── v4-shims.less              # v4兼容
├── scss/                          # SCSS源文件
│   ├── _animated.scss             # 动画样式
│   ├── _bordered-pulled.scss      # 边框样式
│   ├── _core.scss                 # 核心样式
│   ├── _fixed-width.scss          # 固定宽度样式
│   ├── _functions.scss            # 函数定义
│   ├── _icons.scss                # 图标样式
│   ├── _list.scss                 # 列表样式
│   ├── _mixins.scss               # 混合样式
│   ├── _rotated-flipped.scss      # 旋转翻转样式
│   ├── _screen-reader.scss        # 屏幕阅读器样式
│   ├── _shims.scss                # 兼容样式
│   ├── _sizing.scss               # 尺寸样式
│   ├── _stacked.scss              # 堆叠样式
│   ├── _variables.scss            # 变量定义
│   ├── brands.scss                # 品牌图标
│   ├── fontawesome.scss           # 主样式文件
│   ├── regular.scss               # 常规图标
│   ├── solid.scss                 # 实心图标
│   └── v4-shims.scss              # v4兼容
├── sprites/                       # 精灵图文件
│   ├── brands.svg                 # 品牌图标精灵图
│   ├── regular.svg                # 常规图标精灵图
│   └── solid.svg                  # 实心图标精灵图
├── svgs/                          # SVG图标文件
│   ├── brands/                    # 品牌图标 (467个文件)
│   ├── regular/                   # 常规图标 (163个文件)
│   └── solid/                     # 实心图标 (1390个文件)
├── webfonts/                      # 网页字体文件
│   ├── fa-brands-400.ttf          # 品牌字体
│   ├── fa-brands-400.woff2        # 品牌字体(woff2)
│   ├── fa-regular-400.ttf         # 常规字体
│   ├── fa-regular-400.woff2       # 常规字体(woff2)
│   ├── fa-solid-900.ttf           # 实心字体
│   ├── fa-solid-900.woff2         # 实心字体(woff2)
│   ├── fa-v4compatibility.ttf     # v4兼容字体
│   └── fa-v4compatibility.woff2   # v4兼容字体(woff2)
├── metadata/                      # 元数据文件
│   ├── categories.yml             # 分类定义
│   ├── icon-families.json         # 图标族JSON
│   ├── icon-families.yml          # 图标族YAML
│   ├── icons.json                 # 图标JSON
│   ├── icons.yml                  # 图标YAML
│   ├── shims.json                 # 兼容JSON
│   ├── shims.yml                  # 兼容YAML
│   └── sponsors.yml               # 赞助商信息
└── LICENSE.txt                    # 许可证文件
```

---

## 文件组织架构

### 模板文件架构
```
templates/
├── base.html                      # 基础模板，包含通用布局
├── about.html                     # 静态页面
├── components/                    # 可复用组件模板
├── [功能模块]/                    # 各功能模块的模板
│   ├── [功能页面].html            # 具体功能页面
│   └── ...                       # 其他相关页面
└── macros/                        # Jinja2宏定义
```

### 静态文件架构
```
static/
├── css/                          # 样式文件
│   ├── [功能模块].css            # 全局样式
│   ├── components/               # 组件样式
│   └── pages/                    # 页面专用样式
├── js/                           # JavaScript文件
│   ├── [功能模块].js             # 全局脚本
│   ├── common/                   # 通用工具脚本
│   ├── components/               # 组件脚本
│   ├── debug/                    # 调试脚本
│   └── pages/                    # 页面专用脚本
├── img/                          # 图片资源
└── vendor/                       # 第三方库
    ├── bootstrap/                # Bootstrap框架
    ├── chartjs/                  # Chart.js图表库
    ├── jquery/                   # jQuery库
    └── fontawesome/              # Font Awesome图标库
```

---

## 技术栈说明

### 前端框架
- **Bootstrap 5.3.2**: 响应式UI框架
- **jQuery 3.7.1**: JavaScript库
- **Chart.js 4.4.0**: 图表可视化库
- **Font Awesome 6.4.0**: 图标库

### 模板引擎
- **Jinja2**: Flask默认模板引擎
- **宏定义**: 可复用的模板组件
- **模板继承**: 基于base.html的模板继承

### 文件组织原则
1. **模块化**: 按功能模块组织文件
2. **可维护性**: 清晰的目录结构便于维护
3. **可复用性**: 组件化设计提高代码复用
4. **性能优化**: 静态资源压缩和缓存策略

---

## 维护说明

### 添加新功能模块
1. 在`templates/`下创建对应的目录
2. 在`static/css/pages/`下创建对应的样式文件
3. 在`static/js/pages/`下创建对应的脚本文件
4. 更新本清单文档

### 文件命名规范
- **模板文件**: 使用下划线分隔，如`user_management.html`
- **CSS文件**: 与模板文件对应，如`user_management.css`
- **JavaScript文件**: 与模板文件对应，如`user_management.js`
- **图片文件**: 使用连字符分隔，如`apple-touch-icon.png`

### 版本控制
- 所有静态资源文件都应纳入版本控制
- 第三方库文件建议使用CDN或子模块管理
- 定期更新第三方库版本

---

**文档生成时间**: 2024年12月19日  
**项目版本**: TaifishV4  
**维护者**: 开发团队
