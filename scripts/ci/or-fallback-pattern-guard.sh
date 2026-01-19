#!/usr/bin/env bash
# `or` 兜底高风险形态门禁（初期只覆盖最危险/最易语义漂移的形态）
#
# 目标：
# - 禁止在 services/repositories 中出现字段 alias/迁移链：`data.get("new") or data.get("old")`
# - 禁止 internal contract 相关模块在 version 不匹配时 silent fallback 为 `{}`/`[]`
#
# 参考：
# - docs/Obsidian/standards/backend/or-fallback-decision-table.md
# - docs/Obsidian/standards/backend/layer/schemas-layer-standards.md
# - docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

RG_BIN="${RG_BIN:-rg}"
if ! command -v "${RG_BIN}" >/dev/null 2>&1; then
  echo "未检测到 rg 命令，请先安装 ripgrep，或设置 RG_BIN 指向可执行文件。" >&2
  exit 1
fi

# 1) services/repositories: 禁止 `get(...) or get(...)` 字段 alias/迁移链
TARGETS_ALIAS_CHAIN=(
  "app/services"
  "app/repositories"
)

ALIAS_CHAIN_PATTERN="\\bget\\(['\\\"][A-Za-z0-9_]+['\\\"]\\)\\s*or\\s*[^\\n]*\\bget\\(['\\\"][A-Za-z0-9_]+['\\\"]\\)"

alias_hits="$("${RG_BIN}" -n --hidden --type py -- "${ALIAS_CHAIN_PATTERN}" "${TARGETS_ALIAS_CHAIN[@]}" || true)"
if [[ -n "${alias_hits}" ]]; then
  echo "检测到 services/repositories 中的字段 alias/迁移 or 兜底链（禁止）：" >&2
  echo "${alias_hits}" >&2
  echo "" >&2
  echo "请将字段 alias/迁移下沉到 schema/adapter（例如 Pydantic v2 AliasChoices 或 model_validator），避免覆盖合法 falsy 值导致语义漂移。" >&2
  echo "参考：docs/Obsidian/standards/backend/or-fallback-decision-table.md" >&2
  exit 1
fi

# 1.5) services/repositories: 禁止 `... or {}` / `... or []`（空集合语义必须显式化）
EMPTY_COLLECTION_FALLBACK_PATTERN="\\bor\\s*(\\{\\s*\\}|\\[\\s*\\])"

empty_fallback_hits="$("${RG_BIN}" -n --hidden --type py -- "${EMPTY_COLLECTION_FALLBACK_PATTERN}" "${TARGETS_ALIAS_CHAIN[@]}" || true)"
if [[ -n "${empty_fallback_hits}" ]]; then
  echo "检测到 services/repositories 中的空集合 or 兜底（禁止）：" >&2
  echo "${empty_fallback_hits}" >&2
  echo "" >&2
  echo "请将默认值/缺失处理下沉到 schema/adapter（Pydantic default/default_factory 或 explicit None/key-in-dict 判定），避免把缺失/None/显式空合并为同一语义。" >&2
  echo "参考：docs/Obsidian/standards/backend/or-fallback-decision-table.md" >&2
  exit 1
fi

# 2) internal contract: version 不匹配时禁止 return {} / []
TARGETS_INTERNAL_CONTRACT=(
  "app/schemas/internal_contracts"
  "app/services"
  "app/repositories"
)

# 多行匹配：if ...get("version")... != ...:\n  return {} / []
INTERNAL_CONTRACT_SILENT_FALLBACK_PATTERN="if\\s+[^\\n]*get\\(['\\\"]version['\\\"]\\)[^\\n]*!=[^\\n]*:\\s*\\n\\s*return\\s*(\\{\\}|\\[\\])"

contract_hits="$("${RG_BIN}" -n -U --hidden --type py -- "${INTERNAL_CONTRACT_SILENT_FALLBACK_PATTERN}" "${TARGETS_INTERNAL_CONTRACT[@]}" || true)"
if [[ -n "${contract_hits}" ]]; then
  echo "检测到 internal contract 版本不匹配时 silent fallback 为 {} / []（禁止）：" >&2
  echo "${contract_hits}" >&2
  echo "" >&2
echo "未知版本必须显式失败（fail-fast 或返回 InternalContractResult(ok=false, ...)），禁止 return {} / [] 继续消费。" >&2
echo "参考：docs/Obsidian/standards/backend/internal-data-contract-and-versioning.md" >&2
exit 1
fi

echo "✅ or 兜底高风险形态门禁通过。"
