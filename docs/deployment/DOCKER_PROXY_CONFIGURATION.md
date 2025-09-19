# Docker代理配置指南

## 📋 概述

在生产环境中，由于网络限制，Docker可能无法直接访问Docker Hub等外部镜像仓库。本指南提供了多种配置Docker代理的方法，确保Docker能够正常拉取镜像和构建容器。

## 🔧 配置方法

### 方法1：Docker守护进程代理配置（推荐）

#### 1.1 创建Docker服务配置目录

```bash
sudo mkdir -p /etc/systemd/system/docker.service.d
```

#### 1.2 创建代理配置文件

```bash
sudo tee /etc/systemd/system/docker.service.d/http-proxy.conf > /dev/null <<EOF
[Service]
Environment="HTTP_PROXY=http://your-proxy-server:port"
Environment="HTTPS_PROXY=http://your-proxy-server:port"
Environment="NO_PROXY=localhost,127.0.0.1,::1,internal.company.com"
EOF
```

#### 1.3 重启Docker服务

```bash
# 重新加载systemd配置
sudo systemctl daemon-reload

# 重启Docker服务
sudo systemctl restart docker

# 检查Docker服务状态
sudo systemctl status docker
```

#### 1.4 验证代理配置

```bash
# 检查Docker是否使用代理
docker info | grep -i proxy

# 测试Docker Hub连接
docker pull hello-world
```

### 方法2：Docker客户端配置

#### 2.1 创建Docker客户端配置目录

```bash
mkdir -p ~/.docker
```

#### 2.2 配置Docker客户端代理

```bash
cat > ~/.docker/config.json <<EOF
{
  "proxies": {
    "default": {
      "httpProxy": "http://your-proxy-server:port",
      "httpsProxy": "http://your-proxy-server:port",
      "noProxy": "localhost,127.0.0.1,::1,internal.company.com"
    }
  }
}
EOF
```

### 方法3：Docker镜像源配置（国内用户推荐）

#### 3.1 配置Docker使用国内镜像源

```bash
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com",
    "https://registry.docker-cn.com"
  ]
}
EOF
```

#### 3.2 重启Docker服务

```bash
sudo systemctl restart docker
```

### 方法4：环境变量配置

#### 4.1 系统级环境变量

```bash
# 在/etc/environment中添加
echo 'HTTP_PROXY="http://your-proxy-server:port"' >> /etc/environment
echo 'HTTPS_PROXY="http://your-proxy-server:port"' >> /etc/environment
echo 'NO_PROXY="localhost,127.0.0.1,::1,internal.company.com"' >> /etc/environment

# 重新加载环境变量
source /etc/environment
```

#### 4.2 用户级环境变量

```bash
# 在~/.bashrc中添加
echo 'export HTTP_PROXY="http://your-proxy-server:port"' >> ~/.bashrc
echo 'export HTTPS_PROXY="http://your-proxy-server:port"' >> ~/.bashrc
echo 'export NO_PROXY="localhost,127.0.0.1,::1,internal.company.com"' >> ~/.bashrc

# 重新加载配置
source ~/.bashrc
```

## 🐳 项目特定配置

### 环境变量文件配置

#### 开发环境（env.development）

```ini
# ============================================================================
# 代理配置
# ============================================================================
# HTTP代理
HTTP_PROXY=http://proxy.company.com:8080
HTTPS_PROXY=http://proxy.company.com:8080

# 不使用代理的地址
NO_PROXY=localhost,127.0.0.1,::1,internal.company.com

# 小写版本（某些工具需要）
http_proxy=http://proxy.company.com:8080
https_proxy=http://proxy.company.com:8080
no_proxy=localhost,127.0.0.1,::1,internal.company.com
```

#### 生产环境（env.production）

```ini
# ============================================================================
# 代理配置
# ============================================================================
# HTTP代理
HTTP_PROXY=http://proxy.company.com:8080
HTTPS_PROXY=http://proxy.company.com:8080

# 不使用代理的地址
NO_PROXY=localhost,127.0.0.1,::1,internal.company.com

# 小写版本（某些工具需要）
http_proxy=http://proxy.company.com:8080
https_proxy=http://proxy.company.com:8080
no_proxy=localhost,127.0.0.1,::1,internal.company.com
```

### Docker Compose代理配置

#### 构建时代理配置

```yaml
services:
  whalefall:
    build:
      context: .
      dockerfile: Dockerfile.prod
      target: production
      args:
        HTTP_PROXY: ${HTTP_PROXY:-}
        HTTPS_PROXY: ${HTTPS_PROXY:-}
        NO_PROXY: ${NO_PROXY:-localhost,127.0.0.1,::1}
        BUILDKIT_INLINE_CACHE: 1
```

#### 运行时代理配置

```yaml
services:
  whalefall:
    environment:
      # 运行时代理配置
      - HTTP_PROXY=${HTTP_PROXY:-}
      - HTTPS_PROXY=${HTTPS_PROXY:-}
      - NO_PROXY=${NO_PROXY:-localhost,127.0.0.1,::1}
```

## 🔍 验证和测试

### 检查Docker代理配置

```bash
# 检查Docker守护进程代理
docker info | grep -i proxy

# 检查Docker客户端配置
cat ~/.docker/config.json

# 检查环境变量
env | grep -i proxy
```

### 测试网络连接

```bash
# 测试代理连接
curl -I --proxy $HTTP_PROXY https://www.google.com

# 测试Docker Hub连接
docker pull hello-world

# 测试特定镜像拉取
docker pull postgres:15-alpine
```

### 检查Docker构建

```bash
# 测试Docker构建（使用代理）
docker build --build-arg HTTP_PROXY="$HTTP_PROXY" -t test .

# 检查构建日志中的代理使用情况
docker build --build-arg HTTP_PROXY="$HTTP_PROXY" -t test . 2>&1 | grep -i proxy
```

## 🚀 快速解决方案

### 方案1：使用国内镜像源（推荐）

```bash
# 1. 配置Docker镜像源
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
EOF

# 2. 重启Docker服务
sudo systemctl restart docker

# 3. 使用国内镜像源启动
./scripts/docker/start-prod-base-cn.sh
```

### 方案2：配置代理后使用原脚本

```bash
# 1. 配置Docker守护进程代理
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/http-proxy.conf > /dev/null <<EOF
[Service]
Environment="HTTP_PROXY=http://your-proxy-server:port"
Environment="HTTPS_PROXY=http://your-proxy-server:port"
Environment="NO_PROXY=localhost,127.0.0.1,::1"
EOF

# 2. 重启Docker服务
sudo systemctl daemon-reload
sudo systemctl restart docker

# 3. 使用原脚本启动
./scripts/docker/start-prod-base.sh
```

## ⚠️ 常见问题和解决方案

### 问题1：Docker无法连接到Docker Hub

**错误信息**：
```
Error response from daemon: Get "https://registry-1.docker.io/v2/": dial tcp: connect: connection refused
```

**解决方案**：
1. 配置Docker代理（方法1）
2. 使用国内镜像源（方法3）
3. 检查网络连接和防火墙设置

### 问题2：代理认证失败

**错误信息**：
```
Error response from daemon: Get "https://registry-1.docker.io/v2/": proxyconnect tcp: dial tcp: connect: connection refused
```

**解决方案**：
1. 检查代理服务器地址和端口
2. 如果代理需要认证，使用格式：`http://username:password@proxy-server:port`
3. 验证代理服务器是否可访问

### 问题3：环境变量不生效

**问题**：设置了环境变量但Docker仍然无法使用代理

**解决方案**：
1. 确保配置了Docker守护进程代理（方法1）
2. 重启Docker服务
3. 检查环境变量格式是否正确

### 问题4：部分镜像无法拉取

**问题**：某些镜像仍然无法从Docker Hub拉取

**解决方案**：
1. 检查NO_PROXY配置，确保不包含需要代理的地址
2. 尝试使用不同的镜像源
3. 手动拉取镜像：`docker pull registry.cn-hangzhou.aliyuncs.com/library/image-name`

## 📝 配置示例

### 完整的生产环境配置示例

```bash
#!/bin/bash
# 生产环境Docker代理配置脚本

# 1. 设置代理变量（根据实际情况修改）
PROXY_SERVER="http://proxy.company.com:8080"
NO_PROXY_LIST="localhost,127.0.0.1,::1,internal.company.com"

# 2. 配置Docker守护进程代理
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/http-proxy.conf > /dev/null <<EOF
[Service]
Environment="HTTP_PROXY=$PROXY_SERVER"
Environment="HTTPS_PROXY=$PROXY_SERVER"
Environment="NO_PROXY=$NO_PROXY_LIST"
EOF

# 3. 配置Docker镜像源
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
EOF

# 4. 重启Docker服务
sudo systemctl daemon-reload
sudo systemctl restart docker

# 5. 验证配置
echo "Docker代理配置完成！"
docker info | grep -i proxy
```

## 🔗 相关文档

- [Docker官方代理配置文档](https://docs.docker.com/network/proxy/)
- [Docker Compose环境变量配置](https://docs.docker.com/compose/environment-variables/)
- [Docker镜像源配置](https://docs.docker.com/registry/recipes/mirror/)

## 📞 技术支持

如果在配置过程中遇到问题，请：

1. 检查Docker服务状态：`sudo systemctl status docker`
2. 查看Docker日志：`sudo journalctl -u docker.service`
3. 验证网络连接：`curl -I --proxy $HTTP_PROXY https://www.google.com`
4. 联系系统管理员确认代理服务器配置

---

**更新时间**：2025-09-19  
**适用版本**：鲸落 v1.0.0+  
**维护人员**：AI Assistant
