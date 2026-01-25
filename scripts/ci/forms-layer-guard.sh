#!/usr/bin/env bash
# Forms 层门禁：禁止跨层依赖与 DB/query 访问

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_DIR="${ROOT_DIR}/app/forms"

RG_BIN="${RG_BIN:-rg}"
if ! command -v "${RG_BIN}" >/dev/null 2>&1; then
  echo "未检测到 rg 命令，请先安装 ripgrep，或设置 RG_BIN 指向可执行文件。" >&2
  exit 1
fi

if [[ ! -d "${TARGET_DIR}" ]]; then
  echo "未找到 ${TARGET_DIR}，跳过检查。"
  exit 0
fi

PATTERN="\\bfrom app\\.(models|services|repositories)\\b|\\bimport app\\.(models|services|repositories)\\b|db\\.session\\b|\\.query\\b"

hits="$("${RG_BIN}" -n --hidden --type py "${PATTERN}" "${TARGET_DIR}" || true)"
if [[ -n "${hits}" ]]; then
  echo "检测到 forms 层越界依赖/DB/query（禁止）：" >&2
  echo "${hits}" >&2
  echo "" >&2
  echo "Forms 层只允许字段定义/校验与模板配置，不应依赖 models/services/repositories，也不应触碰 db.session/Model.query。" >&2
  echo "参考：docs/Obsidian/standards/ui/design/modal-crud-forms.md" >&2
  exit 1
fi

echo "✅ Forms 层门禁通过：未发现跨层依赖/DB/query。"
