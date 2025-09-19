#!/bin/bash

# SSL证书生成脚本
# 用于生成本地开发环境的SSL证书

set -e

echo "🔐 生成SSL证书..."
echo "=================================="

# 创建SSL目录
SSL_DIR="nginx/local/ssl"
mkdir -p "$SSL_DIR"

# 证书配置
CERT_FILE="$SSL_DIR/cert.pem"
KEY_FILE="$SSL_DIR/key.pem"
CSR_FILE="$SSL_DIR/cert.csr"
CONFIG_FILE="$SSL_DIR/openssl.conf"

# 生成OpenSSL配置文件
echo "📝 创建OpenSSL配置文件..."
cat > "$CONFIG_FILE" << 'EOF'
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
C=CN
ST=Beijing
L=Beijing
O=Whalefall Development
OU=IT Department
CN=localhost

[v3_req]
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = *.localhost
DNS.3 = whalefall.local
DNS.4 = *.whalefall.local
IP.1 = 127.0.0.1
IP.2 = ::1
EOF

echo "✅ OpenSSL配置文件已创建: $CONFIG_FILE"

# 生成私钥
echo "🔑 生成私钥..."
openssl genrsa -out "$KEY_FILE" 2048
echo "✅ 私钥已生成: $KEY_FILE"

# 生成证书签名请求
echo "📋 生成证书签名请求..."
openssl req -new -key "$KEY_FILE" -out "$CSR_FILE" -config "$CONFIG_FILE"
echo "✅ 证书签名请求已生成: $CSR_FILE"

# 生成自签名证书
echo "📜 生成自签名证书..."
openssl x509 -req -in "$CSR_FILE" -signkey "$KEY_FILE" -out "$CERT_FILE" -days 365 -extensions v3_req -extfile "$CONFIG_FILE"
echo "✅ 自签名证书已生成: $CERT_FILE"

# 设置权限
echo "🔒 设置证书文件权限..."
chmod 600 "$KEY_FILE"
chmod 644 "$CERT_FILE"
chmod 644 "$CSR_FILE"
chmod 644 "$CONFIG_FILE"

# 显示证书信息
echo "📊 证书信息:"
echo "   证书文件: $CERT_FILE"
echo "   私钥文件: $KEY_FILE"
echo "   有效期: 365天"
echo "   主题: CN=localhost"
echo "   SAN: localhost, *.localhost, whalefall.local, *.whalefall.local, 127.0.0.1, ::1"

# 验证证书
echo "🔍 验证证书..."
if openssl x509 -in "$CERT_FILE" -text -noout > /dev/null 2>&1; then
    echo "✅ 证书验证成功"
else
    echo "❌ 证书验证失败"
    exit 1
fi

echo "=================================="
echo "🎉 SSL证书生成完成！"
echo ""
echo "📁 证书文件位置:"
echo "   证书: $CERT_FILE"
echo "   私钥: $KEY_FILE"
echo ""
echo "🌐 支持的域名:"
echo "   https://localhost"
echo "   https://whalefall.local"
echo "   https://127.0.0.1"
echo ""
echo "⚠️  注意: 这是自签名证书，浏览器会显示安全警告"
echo "   点击'高级' -> '继续访问'即可正常使用"
echo "=================================="
