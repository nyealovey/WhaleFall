#!/bin/bash

# Oracle Instant Client 安装脚本
# 用于在本地开发环境中安装Oracle客户端

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}📊 $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        ARCH=$(uname -m)
        if [[ "$ARCH" == "x86_64" ]]; then
            ARCH="x64"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        ARCH=$(uname -m)
        if [[ "$ARCH" == "arm64" ]]; then
            ARCH="arm64"
        else
            ARCH="x64"
        fi
    else
        log_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi
    
    log_info "检测到操作系统: $OS ($ARCH)"
}

# 检查Oracle客户端是否已安装
check_existing() {
    if [ -d "oracle_client" ] && [ -f "oracle_client/lib/libclntsh.dylib" ] || [ -f "oracle_client/lib/libclntsh.so" ]; then
        log_warning "Oracle客户端已存在"
        read -p "是否重新安装? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "跳过安装"
            exit 0
        fi
    fi
}

# 下载Oracle Instant Client
download_oracle_client() {
    local version="21.18.0.0.0"
    local base_url="https://download.oracle.com/otn_software"
    
    log_info "开始下载Oracle Instant Client $version..."
    
    # 创建临时目录
    mkdir -p /tmp/oracle_client
    cd /tmp/oracle_client
    
    if [[ "$OS" == "linux" ]]; then
        # Linux版本
        local basic_zip="instantclient-basic-linux.x64-${version}dbru.zip"
        local sdk_zip="instantclient-sdk-linux.x64-${version}dbru.zip"
        
        log_info "下载Linux版本..."
        wget -q "${base_url}/linux/instantclient/2118000/${basic_zip}"
        wget -q "${base_url}/linux/instantclient/2118000/${sdk_zip}"
        
    elif [[ "$OS" == "macos" ]]; then
        # macOS版本
        local basic_zip="instantclient-basic-macos.${ARCH}-${version}dbru.zip"
        local sdk_zip="instantclient-sdk-macos.${ARCH}-${version}dbru.zip"
        
        log_info "下载macOS版本..."
        wget -q "${base_url}/mac/instantclient/2118000/${basic_zip}"
        wget -q "${base_url}/mac/instantclient/2118000/${sdk_zip}"
    fi
    
    log_success "下载完成"
}

# 安装Oracle Instant Client
install_oracle_client() {
    local version="21.18.0.0.0"
    
    log_info "开始安装Oracle Instant Client..."
    
    # 解压文件
    unzip -q "instantclient-basic-*.zip"
    unzip -q "instantclient-sdk-*.zip"
    
    # 创建目标目录
    local target_dir="oracle_client"
    mkdir -p "$target_dir"
    
    # 复制文件
    cp -r instantclient_*/lib "$target_dir/"
    cp -r instantclient_*/sdk "$target_dir/" 2>/dev/null || true
    
    # 设置权限
    chmod -R 755 "$target_dir"
    
    log_success "安装完成"
}

# 配置环境变量
configure_environment() {
    local target_dir="oracle_client"
    
    log_info "配置环境变量..."
    
    # 创建环境变量文件
    cat > oracle_env.sh << EOF
#!/bin/bash
# Oracle Instant Client 环境变量配置

export ORACLE_HOME=\$(pwd)/$target_dir
export LD_LIBRARY_PATH=\$ORACLE_HOME/lib:\$LD_LIBRARY_PATH
export PATH=\$ORACLE_HOME:\$PATH

# macOS特殊配置
if [[ "\$OSTYPE" == "darwin"* ]]; then
    export DYLD_LIBRARY_PATH=\$ORACLE_HOME/lib:\$DYLD_LIBRARY_PATH
fi

echo "Oracle环境变量已设置"
echo "ORACLE_HOME: \$ORACLE_HOME"
EOF
    
    chmod +x oracle_env.sh
    
    log_success "环境变量配置完成"
    log_info "使用方法: source oracle_env.sh"
}

# 验证安装
verify_installation() {
    local target_dir="oracle_client"
    
    log_info "验证安装..."
    
    if [ -d "$target_dir" ]; then
        log_success "Oracle客户端目录创建成功"
        
        # 检查关键文件
        if [[ "$OS" == "linux" ]]; then
            if [ -f "$target_dir/lib/libclntsh.so" ]; then
                log_success "Oracle客户端库文件验证通过"
            else
                log_error "Oracle客户端库文件缺失"
                exit 1
            fi
        elif [[ "$OS" == "macos" ]]; then
            if [ -f "$target_dir/lib/libclntsh.dylib" ]; then
                log_success "Oracle客户端库文件验证通过"
            else
                log_error "Oracle客户端库文件缺失"
                exit 1
            fi
        fi
        
        # 显示文件列表
        log_info "安装的文件:"
        ls -la "$target_dir/lib/" | head -10
        
    else
        log_error "Oracle客户端目录创建失败"
        exit 1
    fi
}

# 清理临时文件
cleanup() {
    log_info "清理临时文件..."
    cd /tmp
    rm -rf oracle_client
    log_success "清理完成"
}

# 显示使用说明
show_usage() {
    echo ""
    log_info "使用说明:"
    echo "1. 激活Oracle环境:"
    echo "   source oracle_env.sh"
    echo ""
    echo "2. 在Python中测试连接:"
    echo "   python -c \"import oracledb; print('Oracle驱动加载成功')\""
    echo ""
    echo "3. 在Flask应用中测试:"
    echo "   python app.py"
    echo ""
    log_warning "注意: 每次使用前都需要执行 'source oracle_env.sh'"
}

# 主函数
main() {
    log_info "开始安装Oracle Instant Client..."
    
    detect_os
    check_existing
    download_oracle_client
    install_oracle_client
    configure_environment
    verify_installation
    cleanup
    show_usage
    
    log_success "Oracle Instant Client安装完成！"
}

# 执行主函数
main "$@"
