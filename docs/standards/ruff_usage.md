# Ruff 使用与配置指南

本指南说明如何在 TaifishingV4 中使用 Ruff 进行静态检查、生成报告，并提供可选的配置示例与脚本调用方式，支持自动与手动两种工作流。

## 配置建议（pyproject.toml 片段）

> 若项目已有 Ruff 配置，可对比后按需合并；保持行宽 120 以符合仓库规范。

```toml
[tool.ruff]
target-version = "py311"
line-length = 120
indent-width = 4
src = ["app", "tests", "scripts"]
extend-exclude = ["migrations", "env.*", "userdata"]

[tool.ruff.lint]
select = [
    "F",     # 语法/导入类（含未使用导入、未用变量）
    "E", "W",# pycodestyle
    "I",     # import 排序/位置
    "D",     # docstring 规范
    "PL",    # pylint 风格与复杂度
    "G",     # 日志格式
    "S",     # bandit 安全规则
    "ANN",   # 类型注解
    "C90",   # 复杂度
]
ignore = [
    "D203", "D211", "D212", "D213",  # 与现有 docstring 习惯冲突的规则，按需微调
]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]           # 测试允许使用 assert
"scripts/**" = ["D100","D103"]  # 脚本可放宽 docstring
```

## 脚本：`scripts/ruff_report.sh`

- 作用：按模式选择规则运行 Ruff，生成带时间戳的报告到 `docs/reports/`。
- 运行前提：已安装 `ruff`（可用 `python3 -m pip install ruff`）。

### 使用方式

```bash
# 快速模式（默认，聚焦未使用导入/变量）
./scripts/ruff_report.sh

# 全量扫描（所有规则，生成大报告）
./scripts/ruff_report.sh full

# 样式/文档/导入集中清理
./scripts/ruff_report.sh style

# 安全相关规则（Bandit 前缀 S）
./scripts/ruff_report.sh security

# 自定义规则选择
RUFF_SELECT="F401,E501" ./scripts/ruff_report.sh custom

# 开启自动修复（支持 Ruff 可安全修复的规则）
FIX=true ./scripts/ruff_report.sh style
```

### 环境变量

- `RUFF_SELECT`：自定义规则选择（逗号分隔）；优先于模式默认值。
- `FIX=true`：开启 `--fix` 自动修复（谨慎用于 ALL）。
- `RUFF_EXTRA_ARGS`：追加给 Ruff 的其他参数，如 `--unsafe-fixes`。
- `TIMESTAMP`：自定义报告时间戳；未设置则自动生成当前时间。

### 输出

- 报告路径：`docs/reports/ruff_<mode>_<timestamp>.txt`
- 非 0 退出码：若存在告警或 Ruff 运行失败，脚本返回非 0，便于 CI 阶段阻断。

## 推荐工作流

1) 开发自检：`./scripts/ruff_report.sh`（quick 模式）  
2) 提交前：`FIX=true ./scripts/ruff_report.sh style`，再运行 `make quality`  
3) 阶段审计：`./scripts/ruff_report.sh full`，将报告纳入 `docs/reports/` 留档  

若需与 CI 集成，可在流水线中调用脚本并上传报告为构件，或直接运行 `ruff check .` 并按项目策略设置失败阈值。 
