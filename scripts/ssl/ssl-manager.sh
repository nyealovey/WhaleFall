#!/bin/bash

# SSL证书管理脚本
# 用于管理本地开发环境的SSL证书

set -e

SSL_DIR="nginx/local/ssl"
CERT_FILE="$SSL_DIR/cert.pem"
KEY_FILE="$SSL_DIR/key.pem"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 显示帮助信息
show_help() {
    echo "🔐 SSL证书管理脚本"
    echo "=================================="
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  generate    生成新的SSL证书"
    echo "  check       检查证书状态"
    echo "  renew       续期证书"
    echo "  info        显示证书信息"
    echo "  clean       清理证书文件"
    echo "  install     安装证书到系统信任库"
    echo "  help        显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 generate    # 生成新证书"
    echo "  $0 check       # 检查证书状态"
    echo "  $0 info        # 显示证书信息"
}

# 检查证书是否存在
check_cert_exists() {
    if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
        return 0
    else
        return 1
    fi
}

# 生成证书
generate_cert() {
    echo -e "${BLUE}🔐 生成SSL证书...${NC}"
    echo "=================================="
    
    if check_cert_exists; then
        echo -e "${YELLOW}⚠️  证书已存在，是否要重新生成？${NC}"
        read -p "输入 y 继续，其他键取消: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "操作已取消"
            return 0
        fi
    fi
    
    # 调用证书生成脚本
    ./scripts/generate-ssl-cert.sh
    
    echo -e "${GREEN}✅ 证书生成完成${NC}"
}

# 检查证书状态
check_cert() {
    echo -e "${BLUE}🔍 检查证书状态...${NC}"
    echo "=================================="
    
    if ! check_cert_exists; then
        echo -e "${RED}❌ 证书文件不存在${NC}"
        echo "请运行: $0 generate"
        return 1
    fi
    
    # 检查证书有效期
    if openssl x509 -in "$CERT_FILE" -checkend 0 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 证书有效${NC}"
    else
        echo -e "${RED}❌ 证书已过期${NC}"
        return 1
    fi
    
    # 检查证书和私钥是否匹配
    if openssl x509 -noout -modulus -in "$CERT_FILE" | openssl md5 > /dev/null 2>&1 && \
       openssl rsa -noout -modulus -in "$KEY_FILE" | openssl md5 > /dev/null 2>&1; then
        CERT_MOD=$(openssl x509 -noout -modulus -in "$CERT_FILE" | openssl md5)
        KEY_MOD=$(openssl rsa -noout -modulus -in "$KEY_FILE" | openssl md5)
        
        if [ "$CERT_MOD" = "$KEY_MOD" ]; then
            echo -e "${GREEN}✅ 证书和私钥匹配${NC}"
        else
            echo -e "${RED}❌ 证书和私钥不匹配${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ 证书或私钥格式错误${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ 证书状态检查通过${NC}"
}

# 续期证书
renew_cert() {
    echo -e "${BLUE}🔄 续期SSL证书...${NC}"
    echo "=================================="
    
    if ! check_cert_exists; then
        echo -e "${RED}❌ 证书文件不存在${NC}"
        echo "请运行: $0 generate"
        return 1
    fi
    
    # 备份现有证书
    echo "📦 备份现有证书..."
    cp "$CERT_FILE" "$CERT_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$KEY_FILE" "$KEY_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    
    # 生成新证书
    generate_cert
    
    echo -e "${GREEN}✅ 证书续期完成${NC}"
}

# 显示证书信息
show_cert_info() {
    echo -e "${BLUE}📊 证书信息...${NC}"
    echo "=================================="
    
    if ! check_cert_exists; then
        echo -e "${RED}❌ 证书文件不存在${NC}"
        echo "请运行: $0 generate"
        return 1
    fi
    
    echo "📜 证书详情:"
    openssl x509 -in "$CERT_FILE" -text -noout | grep -E "(Subject:|Issuer:|Not Before:|Not After:|DNS:|IP Address:)"
    
    echo ""
    echo "🔑 私钥信息:"
    openssl rsa -in "$KEY_FILE" -text -noout | grep -E "(RSA Private-Key|Public-Key:)"
    
    echo ""
    echo "📁 文件信息:"
    echo "   证书文件: $CERT_FILE"
    echo "   私钥文件: $KEY_FILE"
    echo "   证书大小: $(du -h "$CERT_FILE" | cut -f1)"
    echo "   私钥大小: $(du -h "$KEY_FILE" | cut -f1)"
    
    echo ""
    echo "🌐 支持的域名:"
    openssl x509 -in "$CERT_FILE" -text -noout | grep -A 10 "Subject Alternative Name" | grep -E "(DNS:|IP Address:)" | sed 's/^[[:space:]]*/   /'
}

# 清理证书文件
clean_cert() {
    echo -e "${BLUE}🧹 清理证书文件...${NC}"
    echo "=================================="
    
    if ! check_cert_exists; then
        echo -e "${YELLOW}⚠️  证书文件不存在${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}⚠️  这将删除所有证书文件，是否继续？${NC}"
    read -p "输入 y 继续，其他键取消: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "操作已取消"
        return 0
    fi
    
    rm -f "$CERT_FILE" "$KEY_FILE" "$SSL_DIR"/*.csr "$SSL_DIR"/*.conf "$SSL_DIR"/*.backup.*
    echo -e "${GREEN}✅ 证书文件已清理${NC}"
}

# 安装证书到系统信任库
install_cert() {
    echo -e "${BLUE}📥 安装证书到系统信任库...${NC}"
    echo "=================================="
    
    if ! check_cert_exists; then
        echo -e "${RED}❌ 证书文件不存在${NC}"
        echo "请运行: $0 generate"
        return 1
    fi
    
    # 检测操作系统
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        echo "🍎 检测到macOS系统"
        echo "请手动将证书添加到钥匙串："
        echo "1. 打开钥匙串访问"
        echo "2. 将 $CERT_FILE 拖拽到'系统'钥匙串"
        echo "3. 双击证书，展开'信任'"
        echo "4. 将'使用此证书时'设置为'始终信任'"
        echo ""
        echo "或运行以下命令："
        echo "sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain $CERT_FILE"
        
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        echo "🐧 检测到Linux系统"
        echo "请手动将证书添加到系统信任库："
        echo "sudo cp $CERT_FILE /usr/local/share/ca-certificates/whalefall-local.crt"
        echo "sudo update-ca-certificates"
        
    else
        echo -e "${YELLOW}⚠️  不支持的操作系统: $OSTYPE${NC}"
        echo "请手动将证书添加到系统信任库"
    fi
}

# 主函数
main() {
    case "${1:-help}" in
        generate)
            generate_cert
            ;;
        check)
            check_cert
            ;;
        renew)
            renew_cert
            ;;
        info)
            show_cert_info
            ;;
        clean)
            clean_cert
            ;;
        install)
            install_cert
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}❌ 未知命令: $1${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
