#!/bin/bash

# Docker镜像导出脚本
# 用于将构建好的镜像导出并打包成部署包

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 配置变量
IMAGE_NAME="whalefall"
IMAGE_TAG="latest"
EXPORT_DIR="./deploy-package"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# 创建导出目录
create_export_dir() {
    log_info "创建导出目录..."
    mkdir -p "$EXPORT_DIR"
    log_success "导出目录创建完成: $EXPORT_DIR"
}

# 检查镜像是否存在
check_image() {
    log_info "检查Docker镜像..."
    if ! docker images | grep -q "$IMAGE_NAME.*$IMAGE_TAG"; then
        log_error "镜像 $IMAGE_NAME:$IMAGE_TAG 不存在，请先构建镜像"
        exit 1
    fi
    log_success "镜像检查通过"
}

# 导出Docker镜像
export_image() {
    log_info "导出Docker镜像..."
    local image_file="$EXPORT_DIR/${IMAGE_NAME}_${IMAGE_TAG}_${TIMESTAMP}.tar.gz"
    
    # 导出并压缩镜像
    docker save "$IMAGE_NAME:$IMAGE_TAG" | gzip > "$image_file"
    
    if [ -f "$image_file" ]; then
        local file_size=$(du -h "$image_file" | cut -f1)
        log_success "镜像导出完成: $image_file (大小: $file_size)"
    else
        log_error "镜像导出失败"
        exit 1
    fi
}

# 复制配置文件
copy_configs() {
    log_info "复制配置文件..."
    
    # 复制docker-compose文件
    cp docker-compose.base.yml "$EXPORT_DIR/"
    cp docker-compose.flask.yml "$EXPORT_DIR/"
    cp docker-compose.full.yml "$EXPORT_DIR/"
    
    # 复制环境配置文件
    cp env.production "$EXPORT_DIR/"
    
    # 复制Nginx配置
    mkdir -p "$EXPORT_DIR/nginx/conf.d"
    cp nginx/conf.d/*.conf "$EXPORT_DIR/nginx/conf.d/"
    
    # 复制SQL脚本
    mkdir -p "$EXPORT_DIR/sql"
    cp sql/*.sql "$EXPORT_DIR/sql/"
    
    # 复制部署脚本
    mkdir -p "$EXPORT_DIR/scripts/deployment"
    cp scripts/deployment/*.sh "$EXPORT_DIR/scripts/deployment/"
    chmod +x "$EXPORT_DIR/scripts/deployment/"*.sh
    
    log_success "配置文件复制完成"
}

# 创建部署说明文档
create_deployment_guide() {
    log_info "创建部署说明文档..."
    
    cat > "$EXPORT_DIR/DEPLOYMENT_GUIDE.md" << 'EOF'
# 鲸落 Docker 部署指南

## 📦 部署包内容

- `whalefall_*.tar.gz` - Docker镜像文件
- `docker-compose.*.yml` - Docker编排文件
- `env.production` - 环境配置文件
- `nginx/` - Nginx配置
- `sql/` - 数据库初始化脚本
- `scripts/deployment/` - 部署脚本

## 🚀 快速部署

### 1. 导入Docker镜像
```bash
# 解压并导入镜像
gunzip -c whalefall_*.tar.gz | docker load

# 验证镜像
docker images | grep whalefall
```

### 2. 配置环境变量
```bash
# 复制环境配置文件
cp env.production .env

# 编辑配置（修改密码等）
nano .env
```

### 3. 启动基础环境
```bash
# 启动PostgreSQL、Redis、Nginx
docker-compose -f docker-compose.base.yml up -d

# 等待服务启动
sleep 30

# 检查服务状态
docker-compose -f docker-compose.base.yml ps
```

### 4. 启动Flask应用
```bash
# 启动Flask应用
docker-compose -f docker-compose.flask.yml up -d

# 检查应用状态
docker-compose -f docker-compose.flask.yml ps
```

### 5. 验证部署
```bash
# 检查应用健康状态
curl http://localhost/health

# 查看日志
docker-compose -f docker-compose.flask.yml logs -f
```

## 🔧 高级配置

### 自定义配置
- 修改 `env.production` 中的数据库密码
- 调整 `nginx/conf.d/whalefall.conf` 中的Nginx配置
- 根据需要修改 `docker-compose.*.yml` 中的资源限制

### 数据持久化
- 数据目录: `./userdata/`
- 日志目录: `./userdata/logs/`
- 备份目录: `./userdata/backups/`

### 监控和维护
- 查看日志: `docker-compose logs -f`
- 重启服务: `docker-compose restart`
- 停止服务: `docker-compose down`

## 📞 技术支持

如有问题，请查看：
1. 应用日志: `docker-compose logs whalefall`
2. 数据库日志: `docker-compose logs postgres`
3. Nginx日志: `docker-compose logs nginx`

EOF

    log_success "部署说明文档创建完成"
}

# 创建部署脚本
create_deployment_script() {
    log_info "创建一键部署脚本..."
    
    cat > "$EXPORT_DIR/deploy.sh" << 'EOF'
#!/bin/bash

# 一键部署脚本
set -e

echo "🚀 开始部署鲸落应用..."

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker未运行，请先启动Docker"
    exit 1
fi

# 导入镜像
echo "📦 导入Docker镜像..."
gunzip -c whalefall_*.tar.gz | docker load

# 复制环境配置
echo "⚙️ 配置环境变量..."
cp env.production .env

# 启动基础环境
echo "🔧 启动基础环境..."
docker-compose -f docker-compose.base.yml up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 30

# 启动Flask应用
echo "🌐 启动Flask应用..."
docker-compose -f docker-compose.flask.yml up -d

# 检查状态
echo "✅ 检查服务状态..."
docker-compose -f docker-compose.flask.yml ps

echo "🎉 部署完成！"
echo "访问地址: http://localhost"
echo "查看日志: docker-compose logs -f"
EOF

    chmod +x "$EXPORT_DIR/deploy.sh"
    log_success "一键部署脚本创建完成"
}

# 创建压缩包
create_package() {
    log_info "创建部署压缩包..."
    local package_name="whalefall-deploy-${TIMESTAMP}.tar.gz"
    
    cd "$EXPORT_DIR"
    tar -czf "../$package_name" .
    cd ..
    
    local package_size=$(du -h "$package_name" | cut -f1)
    log_success "部署包创建完成: $package_name (大小: $package_size)"
}

# 显示部署信息
show_deployment_info() {
    log_info "部署包信息:"
    echo "📁 导出目录: $EXPORT_DIR"
    echo "📦 镜像文件: $(ls $EXPORT_DIR/*.tar.gz)"
    echo "📋 配置文件: $(ls $EXPORT_DIR/*.yml $EXPORT_DIR/*.md)"
    echo ""
    echo "🚀 部署到其他服务器:"
    echo "1. 将整个 $EXPORT_DIR 目录复制到目标服务器"
    echo "2. 进入目录执行: ./deploy.sh"
    echo "3. 或按照 DEPLOYMENT_GUIDE.md 手动部署"
}

# 主函数
main() {
    log_info "开始导出Docker镜像和部署包..."
    
    create_export_dir
    check_image
    export_image
    copy_configs
    create_deployment_guide
    create_deployment_script
    create_package
    show_deployment_info
    
    log_success "导出完成！"
}

# 执行主函数
main "$@"
