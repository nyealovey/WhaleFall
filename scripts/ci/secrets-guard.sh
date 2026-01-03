#!/usr/bin/env bash
# 生产环境模板密钥门禁：禁止把真实密钥/口令写入 env.example 并提交到仓库

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_FILE="${ROOT_DIR}/env.example"

if [[ ! -f "${TARGET_FILE}" ]]; then
  echo "未找到 env.example，跳过检查。"
  exit 0
fi

# 说明：
# - env.example 是“示例模板”，真实值应放在未跟踪的 .env 或由部署系统/密钥管理系统注入。
# - 这里仅对最核心的敏感项做“非空值”拦截，避免误把真实密钥提交进仓库。
SENSITIVE_VALUE_PATTERN='^(POSTGRES_PASSWORD|REDIS_PASSWORD|SECRET_KEY|JWT_SECRET_KEY|PASSWORD_ENCRYPTION_KEY)=.*[^[:space:]]'

RG_BIN="${RG_BIN:-rg}"
if command -v "${RG_BIN}" >/dev/null 2>&1; then
  MATCH_CMD=("${RG_BIN}" -n "${SENSITIVE_VALUE_PATTERN}" "${TARGET_FILE}")
elif command -v grep >/dev/null 2>&1; then
  MATCH_CMD=(grep -nE "${SENSITIVE_VALUE_PATTERN}" "${TARGET_FILE}")
else
  echo "未检测到 rg/grep 命令，无法执行 env.example 密钥门禁检查。" >&2
  exit 1
fi

if "${MATCH_CMD[@]}"; then
  echo "" >&2
  echo "检测到 env.example 中存在非空敏感值。" >&2
  echo "请将这些变量改为占位符(空值)，并把真实值放入未跟踪的 .env 或通过密钥管理系统注入。" >&2
  exit 1
fi

echo "✅ env.example 模板检查通过：未发现非空敏感值。"
