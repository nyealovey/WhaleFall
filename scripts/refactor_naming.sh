#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}" )/.." && pwd)"
cd "$ROOT_DIR"

DRY_RUN=false
SKIP_TESTS=false

usage() {
    cat <<'EOF'
Usage: scripts/refactor_naming.sh [options]

Options:
  --dry-run       Preview all operations without modifying files.
  --skip-tests    Skip running make test / make quality after renames.
  -h, --help      Show this help text.

The script performs the following steps in order:
  1. Rename front-end directories (kebab-case enforcement)
  2. Rename backend / front-end files
  3. Update Python imports and front-end references
  4. Run validation commands (unless skipped / dry-run)
  5. Generate a report under docs/refactoring
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "[ERROR] Unknown option: $1" >&2
            usage
            exit 1
            ;;
    esac
done

timestamp="$(date +%Y%m%d_%H%M%S)"
report_suffix=$([[ "$DRY_RUN" == "true" ]] && echo "_dry-run" || echo "")
REPORT_PATH="$ROOT_DIR/docs/refactoring/重构执行报告_${timestamp}${report_suffix}.md"

log() {
    printf '%s\n' "$1"
}

append_report() {
    printf '%s\n' "$1" >> "$REPORT_PATH"
}

init_report() {
    cat >"$REPORT_PATH" <<EOF
# 命名规范重构执行报告

- 运行模式: $([[ "$DRY_RUN" == "true" ]] && echo "dry-run" || echo "apply")
- 启动时间: $(date)
- 脚本版本: 1.0.0

EOF
}

ensure_tool() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "[ERROR] Required tool '$1' is not available" >&2
        exit 1
    fi
}

ensure_tool git
ensure_tool python3

init_report

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "[ERROR] This script must run inside a git repository" >&2
    exit 1
fi

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

run_cmd() {
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[dry-run] $*"
    else
        "$@"
    fi
}

rename_entry() {
    local src="$1"
    local dest="$2"

    if [[ "$DRY_RUN" == "true" ]]; then
        log "[dry-run] git mv $src $dest"
        append_report "- dry-run 预览: $src → $dest"
        return
    fi

    if [[ -e "$dest" ]]; then
        log "[skip] $dest already exists"
        return
    fi

    if [[ ! -e "$src" ]]; then
        log "[warn] $src not found"
        return
    fi

    run_cmd git mv "$src" "$dest"
    append_report "- 资源重命名: $src → $dest"
}

rename_batch() {
    local title="$1"
    shift
    local entries=("$@")

    log "\n==> $title"
    append_report "\n## $title"
    for entry in "${entries[@]}"; do
        IFS="|" read -r src dest <<<"$entry"
        rename_entry "$src" "$dest"
    done
}

apply_replacements() {
    local title="$1"
    local root="$2"
    local extensions="$3"
    shift 3
    local entries=("$@")

    log "\n==> $title"
    append_report "\n## $title"

    local temp_file
    temp_file="$(mktemp)"
    for pair in "${entries[@]}"; do
        printf '%s\n' "$pair" >>"$temp_file"
    done

    if [[ "$DRY_RUN" == "true" ]]; then
        python3 <<PY
from pathlib import Path
root = Path("$root")
exts = set(x.strip().lower() for x in "$extensions".split(','))
pairs = []
with open("$temp_file", encoding='utf-8') as fh:
    for line in fh:
        if '|' not in line:
            continue
        old, new = line.rstrip('\n').split('|', 1)
        pairs.append((old, new))

hits = {}
for path in root.rglob('*'):
    if not path.is_file():
        continue
    suffix = path.suffix.lower().lstrip('.')
    if suffix not in exts:
        continue
    try:
        text = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        continue
    for old, _ in pairs:
        if old in text:
            hits.setdefault(old, []).append(str(path))
            break

if not hits:
    print("[dry-run] 没有匹配到需要替换的内容。")
else:
    for key, files in hits.items():
        print(f"[dry-run] '{key}' 出现在 {len(files)} 个文件中")
PY
        append_report "- dry-run 预览: $title"
    else
        python3 <<PY
from pathlib import Path
root = Path("$root")
exts = set(x.strip().lower() for x in "$extensions".split(','))
pairs = []
with open("$temp_file", encoding='utf-8') as fh:
    for line in fh:
        if '|' not in line:
            continue
        old, new = line.rstrip('\n').split('|', 1)
        pairs.append((old, new))

updated = []
for path in root.rglob('*'):
    if not path.is_file():
        continue
    suffix = path.suffix.lower().lstrip('.')
    if suffix not in exts:
        continue
    try:
        text = path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        continue
    new_text = text
    for old, new in pairs:
        new_text = new_text.replace(old, new)
    if new_text != text:
        path.write_text(new_text, encoding='utf-8')
        updated.append(str(path))

print(f"已更新 {len(updated)} 个文件。")
PY
        append_report "- 替换完成: $title"
    fi

    rm -f "$temp_file"
}

run_tests() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log "\n==> Dry-run 模式，跳过测试"
        append_report "\n## 测试\n- dry-run 模式跳过测试"
        return
    fi

    if [[ "$SKIP_TESTS" == "true" ]]; then
        log "\n==> 已按参数要求跳过测试"
        append_report "\n## 测试\n- 用户参数指定跳过测试"
        return
    fi

    log "\n==> 运行 make test"
    if run_cmd make test; then
        append_report "- make test 通过"
    else
        append_report "- make test 失败"
        exit 1
    fi

    log "\n==> 运行 make quality"
    if run_cmd make quality; then
        append_report "- make quality 通过"
    else
        append_report "- make quality 失败"
        exit 1
    fi
}

# -----------------------------------------------------------------------------
# Rename definitions
# -----------------------------------------------------------------------------

FRONTEND_DIR_RENAMES=(
    "app/static/css/pages/capacity_stats|app/static/css/pages/capacity-stats"
    "app/static/js/common/capacity_stats|app/static/js/common/capacity-stats"
    "app/static/js/pages/capacity_stats|app/static/js/pages/capacity-stats"
    "app/static/js/pages/accounts/classification_rules|app/static/js/pages/accounts/classification-rules"
    "app/templates/accounts/classification_rules|app/templates/accounts/classification-rules"
)

BACKEND_FILE_RENAMES=(
    "app/routes/database_aggr.py|app/routes/database_aggregations.py"
    "app/routes/instance_aggr.py|app/routes/instance_aggregations.py"
    "app/views/account_classification_form_view.py|app/views/classification_forms.py"
    "app/views/change_password_form_view.py|app/views/password_forms.py"
    "app/views/credential_form_view.py|app/views/credential_forms.py"
    "app/views/instance_form_view.py|app/views/instance_forms.py"
    "app/views/scheduler_job_form_view.py|app/views/scheduler_forms.py"
    "app/views/tag_form_view.py|app/views/tag_forms.py"
    "app/views/user_form_view.py|app/views/user_forms.py"
    "app/services/form_service/change_password_form_service.py|app/services/form_service/password_service.py"
    "app/services/form_service/classification_form_service.py|app/services/form_service/classification_service.py"
    "app/services/form_service/classification_rule_form_service.py|app/services/form_service/classification_rule_service.py"
    "app/services/form_service/credentials_form_service.py|app/services/form_service/credential_service.py"
    "app/services/form_service/instances_form_service.py|app/services/form_service/instance_service.py"
    "app/services/form_service/resource_form_service.py|app/services/form_service/resource_service.py"
    "app/services/form_service/scheduler_job_form_service.py|app/services/form_service/scheduler_job_service.py"
    "app/services/form_service/tags_form_service.py|app/services/form_service/tag_service.py"
    "app/services/form_service/users_form_service.py|app/services/form_service/user_service.py"
)

FRONTEND_FILE_RENAMES=(
    "app/static/js/common/permission_policy_center.js|app/static/js/common/permission-policy-center.js"
    "app/static/js/common/capacity-stats/chart_renderer.js|app/static/js/common/capacity-stats/chart-renderer.js"
    "app/static/js/common/capacity-stats/data_source.js|app/static/js/common/capacity-stats/data-source.js"
    "app/static/js/common/capacity-stats/summary_cards.js|app/static/js/common/capacity-stats/summary-cards.js"
    "app/static/js/components/tag_selector.js|app/static/js/components/tag-selector.js"
    "app/static/js/components/filters/filter_utils.js|app/static/js/components/filters/filter-utils.js"
    "app/static/js/pages/accounts/account_classification.js|app/static/js/pages/accounts/account-classification.js"
    "app/static/js/pages/admin/aggregations_chart.js|app/static/js/pages/admin/aggregations-chart.js"
    "app/static/js/pages/auth/change_password.js|app/static/js/pages/auth/change-password.js"
    "app/static/js/pages/capacity-stats/database_aggregations.js|app/static/js/pages/capacity-stats/database-aggregations.js"
    "app/static/js/pages/capacity-stats/instance_aggregations.js|app/static/js/pages/capacity-stats/instance-aggregations.js"
    "app/static/js/pages/history/sync_sessions.js|app/static/js/pages/history/sync-sessions.js"
    "app/static/js/pages/tags/batch_assign.js|app/static/js/pages/tags/batch-assign.js"
    "app/static/css/components/filters/filter_common.css|app/static/css/components/filters/filter-common.css"
    "app/static/css/components/tag_selector.css|app/static/css/components/tag-selector.css"
    "app/static/css/pages/accounts/account_classification.css|app/static/css/pages/accounts/account-classification.css"
    "app/static/css/pages/auth/change_password.css|app/static/css/pages/auth/change-password.css"
    "app/static/css/pages/capacity-stats/database_aggregations.css|app/static/css/pages/capacity-stats/database-aggregations.css"
    "app/static/css/pages/capacity-stats/instance_aggregations.css|app/static/css/pages/capacity-stats/instance-aggregations.css"
    "app/static/css/pages/history/sync_sessions.css|app/static/css/pages/history/sync-sessions.css"
    "app/static/css/pages/tags/batch_assign.css|app/static/css/pages/tags/batch-assign.css"
)

BACKEND_REPLACEMENTS=(
    "from app.routes.database_aggr|from app.routes.database_aggregations"
    "from app.routes.instance_aggr|from app.routes.instance_aggregations"
    "database_aggr.|database_aggregations."
    "instance_aggr.|instance_aggregations."
    "account_classification_form_view|classification_forms"
    "change_password_form_view|password_forms"
    "credential_form_view|credential_forms"
    "instance_form_view|instance_forms"
    "scheduler_job_form_view|scheduler_forms"
    "tag_form_view|tag_forms"
    "user_form_view|user_forms"
    "change_password_form_service|password_service"
    "classification_form_service|classification_service"
    "classification_rule_form_service|classification_rule_service"
    "credentials_form_service|credential_service"
    "instances_form_service|instance_service"
    "resource_form_service|resource_service"
    "scheduler_job_form_service|scheduler_job_service"
    "tags_form_service|tag_service"
    "users_form_service|user_service"
)

FRONTEND_REPLACEMENTS=(
    "capacity_stats/|capacity-stats/"
    "classification_rules/|classification-rules/"
    "permission_policy_center.js|permission-policy-center.js"
    "chart_renderer.js|chart-renderer.js"
    "data_source.js|data-source.js"
    "summary_cards.js|summary-cards.js"
    "tag_selector.js|tag-selector.js"
    "filter_utils.js|filter-utils.js"
    "account_classification.js|account-classification.js"
    "aggregations_chart.js|aggregations-chart.js"
    "change_password.js|change-password.js"
    "database_aggregations.js|database-aggregations.js"
    "instance_aggregations.js|instance-aggregations.js"
    "sync_sessions.js|sync-sessions.js"
    "batch_assign.js|batch-assign.js"
    "filter_common.css|filter-common.css"
    "account_classification.css|account-classification.css"
    "change_password.css|change-password.css"
    "database_aggregations.css|database-aggregations.css"
    "instance_aggregations.css|instance-aggregations.css"
    "tag_selector.css|tag-selector.css"
    "batch_assign.css|batch-assign.css"
)

# -----------------------------------------------------------------------------
# Execution pipeline
# -----------------------------------------------------------------------------

rename_batch "前端目录重命名" "${FRONTEND_DIR_RENAMES[@]}"
rename_batch "后端/服务文件重命名" "${BACKEND_FILE_RENAMES[@]}"
rename_batch "前端 JS/CSS 文件重命名" "${FRONTEND_FILE_RENAMES[@]}"

apply_replacements "更新 Python 导入/引用" "$ROOT_DIR/app" "py" "${BACKEND_REPLACEMENTS[@]}"
apply_replacements "更新前端引用" "$ROOT_DIR" "html,js,css" "${FRONTEND_REPLACEMENTS[@]}"

run_tests

append_report "\n## 完成\n- 结束时间: $(date)\n- 报告文件: $REPORT_PATH"

log "\n全部步骤已完成。报告已生成: $REPORT_PATH"

exit 0
