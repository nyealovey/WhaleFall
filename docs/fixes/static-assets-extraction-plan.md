# 前端静态资源抽离与优化修复计划

更新时间：2025-09-22

## 一、背景与目标
- 背景：项目部分页面存在内联 CSS/JS，增加了维护成本与首屏阻塞风险，不利于缓存与 CSP 收紧。
- 目标：
  - 将页面内联 CSS/JS 抽离为外部静态资源，统一目录与命名规范。
  - 复用全局工具模块（时间格式、消息提示等），减少重复逻辑。
  - 为后续性能优化（缓存、压缩、版本参数）与安全策略（CSP、SRI）打基础。

## 二、目录与命名规范
- 目录
  - CSS：app/static/css/pages/
  - JS：app/static/js/pages/
- 命名：采用“目录-文件名”形式（去掉后缀），例如：
  - logs/dashboard.html → css/pages/logs-dashboard.css、js/pages/logs-dashboard.js
  - sync_sessions/management.html → css/pages/sync_sessions-management.css、js/pages/sync_sessions-management.js

## 三、基础模板与全局依赖
- base.html 已提供：
  - 页面级资源注入点：{% block extra_css %} 与 {% block extra_js %}
  - 全局依赖：Bootstrap、alert-utils.js、time-utils.js、CSRF meta 等
- 页面改造仅在上述 blocks 内插入外链，不改动全局依赖。

## 四、改造范围与优先级
- 高优先级：
  - logs/dashboard.html（已完成）
  - sync_sessions/management.html（已完成）
  - accounts/list.html（进行中）
  - accounts/sync_records.html
  - instances/detail.html、instances/statistics.html
  - credentials/list.html
  - scheduler/management.html
  - user_management/management.html
- 中/低优先级：
  - dashboard/overview.html（CSS）
  - admin/management.html（CSS）
  - instances/create.html、instances/edit.html、credentials/create.html、credentials/edit.html（JS）
  - logs/detail.html、logs/statistics.html、accounts/statistics.html、accounts/sync_details.html、database_types/list.html、auth/* 等

## 五、已完成与产出
- 已完成页面：
  - sync_sessions/management.html：
    - 新增：app/static/css/pages/sync_sessions-management.css
    - 新增：app/static/js/pages/sync_sessions-management.js
    - 模板：将 {% block extra_css %}/{% block extra_js %} 内联替换为外链
  - logs/dashboard.html：
    - 新增：app/static/css/pages/logs-dashboard.css
    - 新增：app/static/js/pages/logs-dashboard.js
    - 模板：将 {% block extra_css %}/{% block extra_js %} 内联替换为外链
- 验证：页面在本地开发环境可正常加载并交互；依赖 alert-utils.js、time-utils.js 在 base.html 已全局注入。

## 六、标准实施步骤（单页）
1) 盘点页面内联 CSS/JS，识别对全局工具与第三方库的依赖。
2) 抽离：
   - 将内联 CSS → app/static/css/pages/<目录-文件名>.css
   - 将内联 JS → app/static/js/pages/<目录-文件名>.js（封装 IIFE，避免全局泄露）
3) 模板替换：
   - {% block extra_css %} 中使用 <link rel="stylesheet" href="{{ url_for('static', filename='css/pages/<name>.css') }}">
   - {% block extra_js %} 中使用 <script src="{{ url_for('static', filename='js/pages/<name>.js') }}"></script>
4) 对齐全局工具：
   - 时间格式：使用 window.formatTime（来自 app/static/js/common/time-utils.js）
   - 提示通知：使用 showSuccessAlert/showErrorAlert 等（来自 app/static/js/common/alert-utils.js）
5) 自测：功能回归、控制台无错误、加载顺序正确、参数/选择器匹配。

## 七、性能与可维护性
- 近期改造：
  - 资源抽离、去内联，启用浏览器缓存；
  - 统一工具方法复用，减少重复逻辑；
- 后续优化（规划中）：
  - 版本参数：为静态资源增加版本号（如 url_for(..., v=APP_VERSION)），提升缓存失效控制。
  - 压缩与指纹：构建阶段生成压缩与指纹文件，配合 Nginx 长缓存策略。
  - 指标验证：对比 LCP/FCP、网络请求数、缓存命中率。

## 八、安全与合规
- 逐步收紧 CSP：
  - 移除 unsafe-inline；过渡期可使用 nonce 方案。
  - 对第三方资源引入 SRI 校验。
- CSRF：base.html 已提供 <meta name="csrf-token" ...>，页面 Ajax 按统一方式携带。

## 九、回滚方案
- 单页原子化回滚：若外链资源导致问题，可将模板中对应 blocks 暂时回退为原内联实现，同时保留外链文件以便后续修复。
- 最小影响面：修改仅限 {% block extra_css %}/{% block extra_js %}，不影响全局依赖与主布局。

## 十、风险与注意事项
- 依赖加载顺序：页面 JS 依赖的全局库（如 Bootstrap、utils）应在 base.html 中先于页面脚本加载。
- 选择器/ID 变更：抽离时避免变更 DOM 结构或 ID，减少回归风险。
- JSON/时间格式：统一使用 formatTime/formatDateTime/formatRelativeTime，避免自定义格式分叉。

## 十一、验收标准
- 功能无回归：页面交互与数据请求均正常。
- 控制台无报错：网络与 JS 控制台无错误。
- 性能正向：首次渲染时间不劣于改造前；静态资源可缓存。
- 安全改进：为后续 CSP 收紧与 SRI 引入创造条件。

## 十二、后续任务清单（节选）
- [ ] 在 base.html 层面为静态资源增加统一版本参数策略
- [ ] 抽离 accounts/list.html 的内联 JS 与 CSS（进行中）
- [ ] 抽离 accounts/sync_records.html 的内联 JS
- [ ] 抽离 instances/detail.html 的内联 JS 与 CSS
- [ ] 抽离 instances/statistics.html 的内联 JS
- [ ] 抽离 credentials/list.html 的内联 JS
- [ ] 抽离 scheduler/management.html 的内联 JS 与 CSS
- [ ] 抽离 user_management/management.html 的内联 JS 与 CSS
- [ ] 建立 shared 公共模块（JS: utils/组件；CSS: 变量/工具类）消除重复逻辑/样式
- [ ] 引入资源最小化与缓存策略；LCP/FCP 对比与报告

## 附录：本次新增/修改文件清单
- 新增
  - app/static/css/pages/sync_sessions-management.css
  - app/static/js/pages/sync_sessions-management.js
  - app/static/css/pages/logs-dashboard.css
  - app/static/js/pages/logs-dashboard.js
- 修改
  - app/templates/sync_sessions/management.html（使用外链 CSS/JS）
  - app/templates/logs/dashboard.html（使用外链 CSS/JS）