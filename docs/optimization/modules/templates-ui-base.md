# UI 基础壳（templates/base.html + templates/components + templates/errors + routes/main.py）

## Core Purpose

- 提供全站基础布局与资源引入（`app/templates/base.html`）。
- 提供页面可复用的 Jinja 组件/宏（`app/templates/components/*`）。
- 提供统一错误页（`app/templates/errors/error.html`）。
- 提供首页/关于页/站点图标等基础路由（`app/routes/main.py`）。

## Unnecessary Complexity Found

- （已落地）`app/templates/components/filters/macros.html:66`：`status_sync_filter` 与 `status_active_filter` 完全等价，造成重复实现与维护面。
- （已落地）`app/templates/base.html:8` / `app/templates/base.html:66` / `app/templates/base.html:236`：`config.APP_NAME or '鲸落'` 在多处重复拼装，且模板中混入 tab 缩进，增加 diff 噪音与阅读成本。
- （已落地）`app/routes/main.py:95`：文件尾部存在历史性注释残留（与当前路由实现无关）。

## Code to Remove

- `app/templates/components/filters/macros.html:66`：将 `status_sync_filter` 改为别名调用（避免重复实现；可删 LOC 估算：~1）。
- `app/routes/main.py:95`：移除无关历史注释（可删 LOC 估算：~1）。

## Simplification Recommendations

1. 基础模板保持“少变量、少重复、少噪音”
   - `base.html` 内部允许少量局部变量（如 `app_name`）来消除重复表达式，但避免为了“可能的复用”引入更多宏/抽象层。
2. 组件宏优先复用已存在宏，而不是复制粘贴
   - 对等语义的宏用别名（wrapper）收敛到单一实现。

## YAGNI Violations

- 重复定义 `status` 筛选宏（同参数/同输出）。
- 模板中保留与当前实现无关的历史注释。

## Final Assessment

- 可删 LOC 估算：~2（已落地；其余为降噪/去重复表达式，LOC 变化不大）
- Complexity: Medium -> Lower（主要是模板重复与缩进噪音减少）
- Recommended action: Done（保持全站行为不变，仅做模板/宏层面的去重复与对齐）。

