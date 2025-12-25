#!/bin/bash
# 快速代码统计脚本

BASE_DIR="${1:-app}"
EXCLUDE_PATTERN="vendor"

echo "================================"
echo "代码统计 - $BASE_DIR"
echo "================================"
echo ""

# 总文件数
echo "总文件数:"
find "$BASE_DIR" -type f \( -name "*.py" -o -name "*.js" -o -name "*.css" -o -name "*.html" -o -name "*.yaml" -o -name "*.yml" \) | grep -v "$EXCLUDE_PATTERN" | wc -l

echo ""
echo "总代码行数:"
find "$BASE_DIR" -type f \( -name "*.py" -o -name "*.js" -o -name "*.css" -o -name "*.html" -o -name "*.yaml" -o -name "*.yml" \) | grep -v "$EXCLUDE_PATTERN" | xargs wc -l | tail -1

echo ""
echo "按文件类型统计:"
echo "--------------------------------"

for ext in py js css html yaml yml; do
    count=$(find "$BASE_DIR" -name "*.$ext" | grep -v "$EXCLUDE_PATTERN" | wc -l | tr -d ' ')
    if [ "$count" -gt 0 ]; then
        lines=$(find "$BASE_DIR" -name "*.$ext" | grep -v "$EXCLUDE_PATTERN" | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
        echo "$ext: $count 个文件, $lines 行"
    fi
done

echo ""
echo "代码行数最多的20个文件:"
echo "--------------------------------"
find "$BASE_DIR" -type f \( -name "*.py" -o -name "*.js" \) | grep -v "$EXCLUDE_PATTERN" | xargs wc -l 2>/dev/null | sort -rn | head -20
