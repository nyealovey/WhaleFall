#!/usr/bin/env bash
# API v1 层门禁：禁止 API 端点直依赖 models/routes 或直接触 DB/query

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_DIR="${ROOT_DIR}/app/api/v1"

RG_BIN="${RG_BIN:-rg}"
if ! command -v "${RG_BIN}" >/dev/null 2>&1; then
  echo "未检测到 rg 命令，请先安装 ripgrep，或设置 RG_BIN 指向可执行文件。" >&2
  exit 1
fi

if [[ ! -d "${TARGET_DIR}" ]]; then
  echo "未找到 ${TARGET_DIR}，跳过检查。"
  exit 0
fi

PATTERN="\\bfrom app\\.(models|routes)\\b|\\bimport app\\.(models|routes)\\b|db\\.session\\b|\\.query\\b"

hits="$("${RG_BIN}" -n --hidden --type py "${PATTERN}" "${TARGET_DIR}" || true)"
if [[ -n "${hits}" ]]; then
  echo "检测到 API v1 层越界依赖/DB/query（禁止）：" >&2
  echo "${hits}" >&2
  echo "" >&2
  echo "API v1 仅负责参数解析/校验与调用 Service，不应 import models/routes，也不应直接触碰 db.session/Model.query。" >&2
  echo "参考：docs/Obsidian/standards/backend/layer/api-layer-standards.md" >&2
  exit 1
fi

echo "✅ API v1 层门禁通过：未发现 models/routes 依赖或 DB/query。"

