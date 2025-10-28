#!/bin/bash

###############################################################################
# 下载前端依赖库到本地
# 用途：避免依赖 CDN，将所有库存储到 app/static/vendor/
###############################################################################

set -e  # 遇到错误立即退出

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 基础目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENDOR_DIR="$PROJECT_ROOT/app/static/vendor"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}前端库本地化下载脚本${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# 检查是否安装了 curl
if ! command -v curl &> /dev/null; then
    echo -e "${RED}错误: 未找到 curl 命令${NC}"
    echo "请先安装 curl: brew install curl (macOS) 或 apt install curl (Linux)"
    exit 1
fi

# 创建 vendor 目录
mkdir -p "$VENDOR_DIR"
cd "$VENDOR_DIR"

###############################################################################
# 1. Axios - HTTP 客户端
###############################################################################
echo -e "${GREEN}[1/6] 下载 Axios...${NC}"
mkdir -p axios
curl -L -o axios/axios.min.js https://cdn.jsdelivr.net/npm/axios@1.6.2/dist/axios.min.js
curl -L -o axios/axios.min.js.map https://cdn.jsdelivr.net/npm/axios@1.6.2/dist/axios.min.js.map
echo "✓ Axios 下载完成"

###############################################################################
# 2. Just-Validate - 表单验证
###############################################################################
echo -e "${GREEN}[2/6] 下载 Just-Validate...${NC}"
mkdir -p just-validate
curl -L -o just-validate/just-validate.production.min.js https://unpkg.com/just-validate@4.3.0/dist/just-validate.production.min.js
echo "✓ Just-Validate 下载完成"

###############################################################################
# 3. NProgress - 加载进度条
###############################################################################
echo -e "${GREEN}[3/6] 下载 NProgress...${NC}"
mkdir -p nprogress
curl -L -o nprogress/nprogress.js https://unpkg.com/nprogress@0.2.0/nprogress.js
curl -L -o nprogress/nprogress.css https://unpkg.com/nprogress@0.2.0/nprogress.css
echo "✓ NProgress 下载完成"

###############################################################################
# 4. Ladda - 按钮加载状态
###############################################################################
echo -e "${GREEN}[4/6] 下载 Ladda...${NC}"
mkdir -p ladda
curl -L -o ladda/ladda.min.js https://cdn.jsdelivr.net/npm/ladda@2.0.0/dist/ladda.min.js
curl -L -o ladda/ladda.min.css https://cdn.jsdelivr.net/npm/ladda@2.0.0/dist/ladda.min.css
# Ladda 需要 spin.js
curl -L -o ladda/spin.min.js https://cdn.jsdelivr.net/npm/spin.js@4.1.1/spin.umd.js
echo "✓ Ladda 下载完成"

###############################################################################
# 5. SweetAlert2 - 美化对话框
###############################################################################
echo -e "${GREEN}[5/6] 下载 SweetAlert2...${NC}"
mkdir -p sweetalert2
curl -L -o sweetalert2/sweetalert2.all.min.js https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.all.min.js
echo "✓ SweetAlert2 下载完成"

###############################################################################
# 6. Tom Select - 标签选择器（可选）
###############################################################################
echo -e "${GREEN}[6/6] 下载 Tom Select (可选)...${NC}"
mkdir -p tom-select
curl -L -o tom-select/tom-select.complete.min.js https://cdn.jsdelivr.net/npm/tom-select@2.3.1/dist/js/tom-select.complete.min.js
curl -L -o tom-select/tom-select.bootstrap5.min.css https://cdn.jsdelivr.net/npm/tom-select@2.3.1/dist/css/tom-select.bootstrap5.min.css
echo "✓ Tom Select 下载完成"

###############################################################################
# 生成版本信息文件
###############################################################################
echo -e "${BLUE}生成版本信息...${NC}"
cat > "$VENDOR_DIR/VERSIONS.txt" << EOF
前端库版本信息
生成时间: $(date)

1. Axios v1.6.2
   - 文件: axios/axios.min.js
   - 官网: https://axios-http.com/
   - 大小: ~15KB (gzipped)

2. Just-Validate v4.3.0
   - 文件: just-validate/just-validate.production.min.js
   - 官网: https://just-validate.dev/
   - 大小: ~8KB (gzipped)

3. NProgress v0.2.0
   - 文件: nprogress/nprogress.js, nprogress/nprogress.css
   - 官网: https://ricostacruz.com/nprogress/
   - 大小: ~2KB (gzipped)

4. Ladda v2.0.0
   - 文件: ladda/ladda.min.js, ladda/ladda.min.css
   - 官网: https://ladda.dev/
   - 大小: ~5KB (gzipped)
   - 依赖: spin.js (已包含)

5. SweetAlert2 v11.x
   - 文件: sweetalert2/sweetalert2.all.min.js
   - 官网: https://sweetalert2.github.io/
   - 大小: ~40KB (gzipped)
   - 注: all.min.js 包含 CSS，无需单独引入

6. Tom Select v2.3.1
   - 文件: tom-select/tom-select.complete.min.js, tom-select/tom-select.bootstrap5.min.css
   - 官网: https://tom-select.js.org/
   - 大小: ~20KB (gzipped)

总大小: ~90KB (gzipped ~27KB)

现有库（保留）:
- jQuery (已有)
- Bootstrap (已有)
- Toastr (已有)
- Chart.js (已有)
- FontAwesome (已有)
EOF

###############################################################################
# 验证下载
###############################################################################
echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}验证下载结果...${NC}"
echo -e "${BLUE}================================================${NC}"

check_file() {
    if [ -f "$1" ]; then
        local size=$(du -h "$1" | cut -f1)
        echo -e "✓ $1 ${GREEN}($size)${NC}"
    else
        echo -e "✗ $1 ${RED}(缺失)${NC}"
        return 1
    fi
}

# 检查关键文件
check_file "axios/axios.min.js"
check_file "just-validate/just-validate.production.min.js"
check_file "nprogress/nprogress.js"
check_file "nprogress/nprogress.css"
check_file "ladda/ladda.min.js"
check_file "ladda/ladda.min.css"
check_file "sweetalert2/sweetalert2.all.min.js"
check_file "tom-select/tom-select.complete.min.js"
check_file "tom-select/tom-select.bootstrap5.min.css"

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}下载完成！${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "所有库已保存到: $VENDOR_DIR"
echo ""
echo "下一步:"
echo "1. 查看 docs/frontend_local_setup_guide.md 了解如何使用"
echo "2. 运行测试确保所有库正常工作"
echo ""
