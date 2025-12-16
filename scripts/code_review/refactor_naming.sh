#!/usr/bin/env bash
#
# 命名规范检查脚本
# ------------------------------------------------------------------
# 用法：
#   ./scripts/refactor_naming.sh --dry-run   # 只检测
#   ./scripts/refactor_naming.sh             # 检测并给出修复建议
#

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_PATH="$REPO_ROOT/docs/reports/naming_guard_report.txt"
DRY_RUN=false

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
  shift || true
fi

if ! command -v rg >/dev/null 2>&1; then
  echo "❌ 缺少 ripgrep (rg) 命令，请先安装后再执行脚本。" >&2
  exit 1
fi

issues=()

add_issue() {
  issues+=("$1")
}

check_file_targets() {
  local desc="$1"
  shift
  local has_issue=false
  for entry in "$@"; do
    IFS="|" read -r old_path new_path <<<"$entry"
    if [[ -e "$REPO_ROOT/$old_path" ]]; then
      has_issue=true
      add_issue "[$desc] 需要重命名：$old_path → $new_path"
    fi
  done
  if [[ "$has_issue" == false ]]; then
    echo "✅ $desc 无需处理"
  else
    echo "⚠️ $desc 检测到未重命名文件"
  fi
}

check_pattern() {
  local desc="$1"
  local pattern="$2"
  local search_path="$3"
  local matches
  matches="$(rg -n --glob '*.py' "$pattern" "$REPO_ROOT/$search_path" 2>/dev/null || true)"
  if [[ -n "$matches" ]]; then
    add_issue "[$desc] 发现以下违规："$'\n'"$matches"
    echo "⚠️ $desc 存在违规"
  else
    echo "✅ $desc 正常"
  fi
}

echo "🔍 正在检测命名规范..."

check_file_targets "后端路由文件" \
  "app/routes/database_aggr.py|app/routes/database_aggregations.py" \
  "app/routes/instance_aggr.py|app/routes/instance_aggregations.py"

check_file_targets "后端视图文件" \
  "app/views/account_classification_form_view.py|app/views/classification_forms.py" \
  "app/views/change_password_form_view.py|app/views/password_forms.py" \
  "app/views/credential_form_view.py|app/views/credential_forms.py" \
  "app/views/instance_form_view.py|app/views/instance_forms.py" \
  "app/views/scheduler_job_form_view.py|app/views/scheduler_forms.py" \
  "app/views/tag_form_view.py|app/views/tag_forms.py" \
  "app/views/user_form_view.py|app/views/user_forms.py" \
  "app/views/mixins/resource_form_view.py|app/views/mixins/resource_forms.py"

check_file_targets "表单服务文件" \
  "app/services/form_service/change_password_form_service.py|app/services/form_service/password_service.py" \
  "app/services/form_service/classification_form_service.py|app/services/form_service/classification_service.py" \
  "app/services/form_service/classification_rule_form_service.py|app/services/form_service/classification_rule_service.py" \
  "app/services/form_service/credentials_form_service.py|app/services/form_service/credential_service.py" \
  "app/services/form_service/instances_form_service.py|app/services/form_service/instance_service.py" \
  "app/services/form_service/resource_form_service.py|app/services/form_service/resource_service.py" \
  "app/services/form_service/scheduler_job_form_service.py|app/services/form_service/scheduler_job_service.py" \
  "app/services/form_service/tags_form_service.py|app/services/form_service/tag_service.py" \
  "app/services/form_service/users_form_service.py|app/services/form_service/user_service.py"

check_pattern "api_ 前缀函数" "def\s+api_[A-Za-z0-9_]+\s*\(" "app/routes"
check_pattern "_api 后缀函数" "def\s+[A-Za-z0-9_]+_api\s*\(" "app/routes"
check_pattern "_optimized 函数名" "def\s+[A-Za-z0-9_]+_optimized\s*\(" "app"
check_pattern "databases_aggregations 复数错误" "databases_aggregations" "app/routes"
check_pattern "instances_aggregations 复数错误" "instances_aggregations" "app/routes"

echo
mkdir -p "$(dirname "$REPORT_PATH")"

timestamp="$(date +"%Y-%m-%d %H:%M:%S")"
{
  echo "命名守卫检查报告（生成时间：$timestamp）"
  echo "规则依据：仓库规范 3.2 命名守卫"
  echo "检查范围：app/ 及 routes、views、form_service 等 Python 文件"
  echo
  if (( ${#issues[@]} == 0 )); then
    echo "结果：未发现违规项。"
  else
    echo "结果：发现以下违规项："
    printf '%s\n' "${issues[@]}"
  fi
} >"$REPORT_PATH"

if (( ${#issues[@]} == 0 )); then
  echo "🎉 无需要替换的内容"
  echo "报告已生成：$REPORT_PATH"
  exit 0
fi

echo "❌ 检测到以下命名问题（报告已写入 $REPORT_PATH）："
printf '%s\n' "${issues[@]}"
echo
echo "👉 请根据 docs/refactoring/name/ 命名重构指南执行重命名。"

if [[ "$DRY_RUN" == true ]]; then
  exit 1
fi

echo "提示：修复后建议运行 make test / make quality 以及 ./scripts/refactor_naming.sh --dry-run"
exit 1
