# 前端代码重构需求文档 (V1.0)

#### 1. 项目背景与目标

**1.1 背景:**
当前项目在 `/Users/apple/Taifish/TaifishingV4/app/templates` 目录下的部分 HTML 模板文件（如 `sync_sessions/management.html`）包含了大量的内联 CSS (`<style>`) 和 JavaScript (`<script>`) 代码。这种方式导致单个文件过大，难以维护和阅读，同时也影响了浏览器缓存效率。

**1.2 目标:**
为了优化前端代码结构，提升开发和维护效率，本项目旨在将 HTML 模板中的内联 CSS 和 JavaScript 代码抽离到独立的静态文件中。

#### 2. 重构范围

本次重构将覆盖 `/Users/apple/Taifish/TaifishingV4/app/templates` 目录及其所有子目录下的 `.html` 文件。我们将优先处理代码行数较多、逻辑较复杂的模板文件。

#### 3. 重构策略

**3.1 文件组织结构**

为了保持代码的整洁和一一对应，我们将采用以下文件组织结构：

1.  **CSS 文件:**
    *   在 `/Users/apple/Taifish/TaifishingV4/app/static/css/` 目录下创建一个 `pages` 子目录。
    *   对于每个模板文件，例如 `app/templates/sync_sessions/management.html`，其抽离的 CSS 将存放在 `app/static/css/pages/sync_sessions/management.css`。目录结构将镜像 `templates` 目录。

2.  **JavaScript 文件:**
    *   在 `/Users/apple/Taifish/TaifishingV4/app/static/js/` 目录下创建一个 `pages` 子目录。
    *   同理，`app/templates/sync_sessions/management.html` 的 JavaScript 将存放在 `app/static/js/pages/sync_sessions/management.js`。

**3.2 代码抽离步骤**

对于每一个需要重构的 HTML 文件，执行以下操作：

1.  **创建静态文件:** 根据 **3.1** 的规则，创建对应的 `.css` 和 `.js` 空文件。
2.  **抽离 CSS:**
    *   剪切 HTML 文件中 `<style>` 标签内的所有 CSS 代码。
    *   将代码粘贴到新创建的 `.css` 文件中。
    *   在 HTML 文件的 `{% block styles %}` 或类似的区块中，删除旧的 `<style>` 标签，并添加链接：
        ```html
        <link rel="stylesheet" href="{{ url_for('static', filename='css/pages/path/to/your/file.css') }}">
        ```
3.  **抽离 JavaScript:**
    *   剪切 HTML 文件中 `<script>` 标签内的所有 JavaScript 代码（不包含 `src` 属性的标签）。
    *   将代码粘贴到新创建的 `.js` 文件中。
    *   在 HTML 文件的 `{% block scripts %}` 或类似的区块中，删除旧的 `<script>` 标签，并添加引用：
        ```html
        <script src="{{ url_for('static', filename='js/pages/path/to/your/file.js') }}"></script>
        ```

**3.3 动态数据处理（关键挑战）**

内联 JavaScript 常常会使用 Jinja2 模板引擎传递动态数据（例如 `{{ session.id }}` 或 `url_for(...)`）。当代码被移动到静态 `.js` 文件后，这些模板标签将失效。

**解决方案:** 使用 `data-*` 属性或在页面中注入一个全局配置对象。

*   **使用 `data-*` 属性（推荐）:**
    *   **场景:** 需要将特定 URL 或 ID 传递给 JS。
    *   **HTML 修改:**
        ```html
        <!-- 原来的 JS: var url = "{{ url_for('api.get_data') }}"; -->
        <!-- 修改后的 HTML -->
        <div id="my-component" data-api-url="{{ url_for('api.get_data') }}"></div>
        ```
    *   **JavaScript 修改:**
        ```javascript
        // 在 JS 文件中
        const component = document.getElementById('my-component');
        const apiUrl = component.dataset.apiUrl; // 获取 URL
        // fetch(apiUrl)...
        ```

#### 4. 实施计划

我们将采用增量、分步的方式进行重构，以降低风险。

1.  **试点文件 (Pilot):** 首先，我们将以 `/Users/apple/Taifish/TaifishingV4/app/templates/sync_sessions/management.html` 作为试点，完整地执行一次抽离操作。
2.  **创建目录:** 创建所需的 `app/static/css/pages/sync_sessions` 和 `app/static/js/pages/sync_sessions` 目录。
3.  **执行抽离:** 对 `management.html` 执行 **3.2** 和 **3.3** 中描述的步骤。
4.  **验证:** 验证 `management.html` 页面的功能和样式是否与重构前完全一致。
5.  **推广:** 试点成功后，我会为您创建一个详细的 Todo 列表，逐一处理 `templates` 目录下的其他文件。

#### 5. 预期收益

*   **提高可维护性:** HTML、CSS、JS 代码分离，职责清晰。
*   **减少文件体积:** HTML 文件将变得更小、更易于阅读。
*   **利用浏览器缓存:** 静态的 `.css` 和 `.js` 文件可以被浏览器高效缓存，加快页面加载速度。
*   **代码复用:** 公共的 JS 和 CSS 逻辑可以更容易地被抽象和复用。