# UI Standards P1/P2 Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan.

**Goal:** 修复 UI 审计报告中的 P1/P2：补齐缺失的 `page_id`（并补齐对应 Page Entry 挂载点，避免 page-loader 报错），以及收敛 UI 标准中的歧义/不可执行点。

**Architecture:**
- P1：所有 extends `base.html` 的页面都设置稳定的 `page_id`，并在 `extra_js` 中引入对应页面脚本，页面脚本暴露 `window.<PageId>.mount(global)` 供 `app/static/js/bootstrap/page-loader.js` 统一启动。
- P2：将“颜色硬编码”“模板 inline onclick”“layout sizing 例外”明确为可审计/可门禁的规则，并在相关标准中建立单一真源的引用关系。

**Tech Stack:** Jinja2 templates, Vanilla JS(IIFE + window 挂载), Markdown standards, 仓库 CI 脚本（`./scripts/ci/eslint-report.sh quick`、`./scripts/ci/inline-px-style-guard.sh`）。

---

### Task 1: P1 补齐缺失 page_id + 页面入口挂载点

**Files:**
- Modify: `app/templates/about.html`
- Modify: `app/templates/accounts/statistics.html`
- Modify: `app/templates/errors/error.html`
- Modify: `app/static/js/modules/views/accounts/statistics.js`
- Create: `app/static/js/modules/views/about/index.js`
- Create: `app/static/js/modules/views/errors/error.js`

**Step 1: about.html 补齐 page_id + 引入页面入口脚本**
- 在文件顶部 `extends` 之后追加：

```jinja2
{% extends "base.html" %}
{% set page_id = 'AboutPage' %}
```

- 增加 `extra_js` block，引入 `js/modules/views/about/index.js`。

**Step 2: accounts/statistics.html 补齐 page_id（与页面脚本挂载一致）**
- 在文件顶部 `extends` 之后追加：

```jinja2
{% extends "base.html" %}
{% set page_id = 'AccountsStatisticsPage' %}
```

**Step 3: errors/error.html 补齐 page_id + 引入页面入口脚本**
- 在文件顶部 `extends` 之后追加：

```jinja2
{% extends "base.html" %}
{% set page_id = 'ErrorPage' %}
```

- 增加 `extra_js` block，引入 `js/modules/views/errors/error.js`。

**Step 4: 新增 AboutPage/ErrorPage 的最小入口脚本（避免 page-loader 找不到入口）**
- `app/static/js/modules/views/about/index.js`：

```javascript
(function (global) {
  "use strict";

  function mountAboutPage() {
    // noop: About 页面暂不需要 page-level JS，但仍保留稳定入口以满足 page-loader 契约。
  }

  global.AboutPage = {
    mount: function () {
      mountAboutPage(window);
    },
  };
})(window);
```

- `app/static/js/modules/views/errors/error.js`：

```javascript
(function (global) {
  "use strict";

  function mountErrorPage() {
    // noop: 错误页以静态展示为主；如需交互请通过 data-action + addEventListener 绑定。
  }

  global.ErrorPage = {
    mount: function () {
      mountErrorPage(window);
    },
  };
})(window);
```

**Step 5: 重构 accounts/statistics.js 为 Page Entry 形式（window.AccountsStatisticsPage.mount）**
- 目标：移除脚本内自行绑定 `DOMContentLoaded` 的做法，统一由 `page-loader` 调用 `mount`。
- 重构后的骨架应形如：

```javascript
function mountAccountsStatisticsPage(global) {
  "use strict";
  // 绑定 refresh button click -> AccountsStatisticsService.fetchStatistics -> 更新 DOM
}

window.AccountsStatisticsPage = {
  mount: function () {
    mountAccountsStatisticsPage(window);
  },
};
```

**Step 6: 验证（模板 page_id + 页面入口是否存在）**
- Run:

```bash
uv run python - <<'PY'
from __future__ import annotations

import glob
from pathlib import Path

from jinja2 import Environment, nodes

env = Environment()
unsafe = {"__proto__", "prototype", "constructor"}

missing = []
unsafe_page_ids = []

for path in glob.glob("app/templates/**/*.html", recursive=True):
    p = Path(path)
    source = p.read_text(encoding="utf-8")
    ast = env.parse(source)

    extends_base = any(
        isinstance(n.template, nodes.Const) and n.template.value == "base.html"
        for n in ast.find_all(nodes.Extends)
    )
    if not extends_base:
        continue

    page_id_nodes = [
        n
        for n in ast.find_all(nodes.Assign)
        if isinstance(n.target, nodes.Name) and n.target.name == "page_id"
    ]
    if not page_id_nodes:
        missing.append(path)
        continue

    for n in page_id_nodes:
        if isinstance(n.node, nodes.Const) and isinstance(n.node.value, str):
            if n.node.value in unsafe:
                unsafe_page_ids.append((path, n.node.value, n.lineno))

print("missing page_id:")
for p in missing:
    print("-", p)

print("unsafe page_id:")
for p, value, lineno in unsafe_page_ids:
    print(f"- {p}:{lineno} {value}")
PY
```
- Expected: `missing page_id:` 下无输出项（空列表）。


---

### Task 2: P2 收敛 UI 标准歧义与不可执行点

**Files:**
- Modify: `docs/Obsidian/standards/ui/color-guidelines.md`
- Create: `docs/Obsidian/standards/ui/template-event-binding-standards.md`
- Modify: `docs/Obsidian/standards/ui/grid-standards.md`
- Modify: `docs/Obsidian/standards/ui/layer/views-layer-standards.md`
- Modify: `docs/Obsidian/standards/ui/layout-sizing-guidelines.md`
- Modify (optional): `docs/Obsidian/standards/ui/README.md`

**Step 1: 明确“颜色硬编码”的 Token 定义文件例外边界**
- 更新 `color-guidelines.md` 的 MUST 规则，使其明确允许 `app/static/css/variables.css` 用于定义 Token 的颜色字面量，但禁止其余 CSS/HTML/JS 硬编码。

**Step 2: 新增“模板事件绑定规范”作为单一真源**
- 新增 `template-event-binding-standards.md`，明确 scope 为 `app/templates/**`：
  - MUST NOT：模板内联 `onclick="..."` 等 handler；
  - MUST：使用 `data-action` + JS 侧事件绑定/委托。

**Step 3: 解除 grid/views 标准中 onclick 规则的 scope 歧义**
- `grid-standards.md` 与 `views-layer-standards.md` 中将 `onclick` 禁令改为引用 `template-event-binding-standards.md`，并把措辞调整为“模板规则在模板标准中定义”。

**Step 4: layout sizing 例外条款改为可审计/可门禁表达**
- 更新 `layout-sizing-guidelines.md`：
  - 明确模板中“禁止新增 inline height/width: Npx”，并写清门禁 `./scripts/ci/inline-px-style-guard.sh` 的 baseline 机制（允许减少、禁止新增）。
  - 将“1px hairline”等微调示例改为“落在组件 CSS 内（非模板 inline）”。

**Step 5:（可选）更新 UI 标准索引 README 增加入口链接**


---

### Task 3: 运行校验与收尾

**Files:**
- (no code changes expected)

**Step 1: 模板 inline px style 门禁**
- Run: `./scripts/ci/inline-px-style-guard.sh`
- Expected: `检查通过`。

**Step 2: ESLint 快速报告**
- Run: `./scripts/ci/eslint-report.sh quick`
- Expected: 0 error。

**Step 3: 汇报变更点与验证结果**
