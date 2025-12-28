#!/usr/bin/env bash
# UI 术语漂移门禁：锁定现状 baseline，禁止新增“已废弃/不推荐”的状态用词命中

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASELINE_FILE="${ROOT_DIR}/scripts/ci/baselines/ui-terminology-guard.txt"

RG_BIN="${RG_BIN:-rg}"
UPDATE_BASELINE="false"

if [[ "${1:-}" == "--update-baseline" ]]; then
  UPDATE_BASELINE="true"
  shift
fi

if ! command -v "${RG_BIN}" >/dev/null 2>&1; then
  echo "未检测到 rg 命令，请先安装 ripgrep，或设置 RG_BIN 指向可执行文件。" >&2
  exit 1
fi

cd "${ROOT_DIR}"

# 说明：
# - 仅做“禁止新增”，允许存量逐步清零
# - 规则应该保持保守，避免误伤技术语义（如 disabled 按钮）
# - 若确需新增命中，请先更新 docs/standards/terminology.md 并在评审中说明边界
TARGETS=(
  "app/templates"
  "app/static/js"
  "app/routes"
  "app/constants/system_constants.py"
  "app/constants/filter_options.py"
  "app/services/files"
)

# 禁止新增的漂移词（状态用词维度）
PATTERN="禁用|进行中|执行中|排队中"

current_file="$(mktemp)"
baseline_sorted_file="$(mktemp)"
trap 'rm -f "${current_file}" "${baseline_sorted_file}"' EXIT

# rg 无命中会返回 1，这里视为“当前 0 命中”
("${RG_BIN}" -n --hidden -S "${PATTERN}" "${TARGETS[@]}" || true) | LC_ALL=C sort >"${current_file}"

current_count="$(wc -l <"${current_file}" | tr -d '[:space:]')"

if [[ "${UPDATE_BASELINE}" == "true" ]]; then
  mkdir -p "$(dirname "${BASELINE_FILE}")"
  cp "${current_file}" "${BASELINE_FILE}"
  echo "已更新 baseline：${BASELINE_FILE}"
  echo "当前命中数：${current_count}"
  exit 0
fi

if [[ ! -f "${BASELINE_FILE}" ]]; then
  echo "未找到 baseline 文件：${BASELINE_FILE}" >&2
  echo "请先运行：./scripts/ci/ui-terminology-guard.sh --update-baseline" >&2
  exit 1
fi

LC_ALL=C sort "${BASELINE_FILE}" >"${baseline_sorted_file}"

new_hits="$(comm -13 "${baseline_sorted_file}" "${current_file}" || true)"
if [[ -n "${new_hits}" ]]; then
  echo "检测到新增的 UI 术语漂移命中（禁止新增）：" >&2
  echo "${new_hits}" >&2
  echo "请参考 docs/standards/terminology.md（状态用词），统一为 canonical 词表。" >&2
  exit 1
fi

echo "检查通过：当前命中数 ${current_count}（允许减少，禁止新增）。"

