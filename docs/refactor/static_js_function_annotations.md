# app/static/js 函数注释重构计划

## 目标
- 为 `app/static/js/` 下的所有函数、类和导出工厂补充简洁的行级或块级注释，说明用途、关键参数、副作用。
- 注释遵循统一格式，避免破坏现有逻辑与 lint 规则，同时保持中文描述、易读性。

## 范围与优先级
1. **核心公共模块**（优先级高）
   - `modules/services/`
   - `modules/stores/`
   - `modules/views/components/`
   - `core/`、`common/`
2. **页面视图层**
   - `modules/views/**`
   - `bootstrap/**`（入口装配）
3. **遗留脚本**
   - `vendor` 以外的自定义 JS（若存在）

## 注释风格
- 采用单行 `//` 或块状 `/** ... */`；针对复杂函数用块状描述。
- 模板示例：
  ```js
  /**
   * 说明一句话
   * @param {...}
   * @returns {...}
   */
  function xxx() {
    // ...
  }
  ```
- 对事件处理、闭包、导出 API 在声明处注释，不在每一行重复。

## 执行步骤
1. **脚本清单**：使用 `find app/static/js -name '*.js'` 导出路径列表，记录在 `docs/refactor/static_js_files.md`。
2. **模块分批**：按目录划分批次，每次 PR 涵盖 1~2 个子目录，确保可读性。
3. **审阅与验证**：
   - 每次注释修改后运行 `npm`/`pytest`（若相关）以防格式问题。
   - 重点检查 ESLint/格式化结果，保持 120 字符限制。
4. **工具**：可用 `rg` 搜索无注释函数，或编写脚本检测 `function` 声明前是否包含 `//`。

## 约束
- 仅添加注释，不改动函数逻辑；如需重构另开任务。
- 保持注释语言为中文；可嵌入必要的英文专有词。
- 避免在 `vendor/`、第三方库中注释或修改。

## 验收标准
- `app/static/js` 下每个自定义函数、类、导出均有明确用途注释。
- 文档更新记录在 `CHANGELOG.md`（可选）。
- 通过 `./scripts/refactor_naming.sh --dry-run`，确保命名规范未被破坏。

## 建议进度
1. **阶段 1**：`modules/services` + `modules/stores`
2. **阶段 2**：`modules/views/components` + `modules/views/accounts/*`
3. **阶段 3**：`modules/views/instances/*` + 其他页面
4. **阶段 4**：`core/`、`common/` 与零散脚本

每阶段完成后更新该文档，记录覆盖范围与 TODO。
