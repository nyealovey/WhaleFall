# Module: `app/settings.py`

## Simplification Analysis

### Core Purpose

提供“单一真源”的配置读取/默认值/校验入口：把环境变量与 `.env`（可选）汇总成 `Settings`，供 `create_app(settings=...)` 消费。

### Unnecessary Complexity Found

- `app/settings.py:233`：已有 `_parse_csv_values`（支持 CSV）但在 `pydantic-settings` 默认 `enable_decoding=True` 时，复杂类型会先走 JSON 解码；当 env 采用 CSV（如 `env.example`），会在解码阶段直接抛 `SettingsError`，导致 validator 根本无法执行（“解析链路中间多了一层不必要的 JSON 解码前置”）。

### Code to Remove

- 本模块以“移除不必要的解码前置”为主（配置项级别简化），未做大规模删代码。
- Estimated LOC reduction: 0（当前改动以简化解析路径为主，净删空间有限）

### Simplification Recommendations

1. 禁用 settings 源层的 JSON decoding，将 CSV/JSON 兼容解析下沉到 field_validator
   - Current: 复杂类型 env 值先 JSON decode（CSV 会直接报错，违背 `env.example`）
   - Proposed: `SettingsConfigDict(enable_decoding=False)` + `_parse_csv_values` 支持：
     - CSV（`a,b,c`）
     - JSON 数组（`["a","b"]`）
   - Impact: 与 `env.example` 一致；避免“本可解析但在前置解码阶段失败”的链路复杂度

### YAGNI Violations

- 依赖“复杂类型必须 JSON env”这一隐含规则，但仓库提供的 `env.example` 使用 CSV；这类隐式约定会制造不必要的运行时失败面。

### Final Assessment

Total potential LOC reduction: 0（主要收益为配置解析路径的确定性与一致性）
Complexity score: Low
Recommended action: 已落地最小必要修复；后续仅在出现真实配置项冗余时再做删减
