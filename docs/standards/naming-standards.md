# 命名规范与命名守卫使用指南

> 状态：Active  
> 负责人：WhaleFall Team  
> 创建：2025-12-25  
> 更新：2025-12-25  
> 范围：仓库内所有文件/目录/符号命名

## 1. 一句话结论

- 命名规则以根目录 `AGENTS.md` 为准；本文件补充“如何用脚本做命名巡检/重命名”。

## 2. 必须遵守的命名要点（摘要）

- Python：模块/函数/变量用 `snake_case`；类用 `CapWords`；常量用 `CAPS_WITH_UNDER`。
- 前端：JS/CSS/目录用 `kebab-case`；变量/函数用 `camelCase`。
- 禁止缩写文件名（必须使用完整单词）。
- 蓝图函数必须是动词短语，禁止 `api_` 前缀或 `_api` 后缀。

> 详细规则见：`AGENTS.md` 与 `docs/standards/coding-standards.md`。

## 3. 命名守卫脚本

仓库提供命名巡检脚本，用于发现“应当统一的命名漂移”（例如历史残留前缀/错误后缀）。

- 仅巡检（推荐）：

```bash
./scripts/refactor_naming.sh --dry-run
```

- 执行重命名：

```bash
./scripts/refactor_naming.sh
```

## 4. 执行重命名的推荐流程

1. 先执行 `./scripts/refactor_naming.sh --dry-run` 获取影响范围。
2. 确认不会误伤公共 API/配置项/对外协议。
3. 执行重命名后，必须全仓搜索旧名字并修复引用。
4. 运行质量门禁：`make format`、`make quality`（必要时再跑测试）。

## 5. 常见问题

- “脚本通过但代码里仍有不一致”：说明不一致不在脚本规则覆盖范围内，应补充规则或在评审中统一口径。
- “改名后 import 失败”：优先用全仓搜索确认所有引用都已更新，尤其是模板与静态资源引用。
