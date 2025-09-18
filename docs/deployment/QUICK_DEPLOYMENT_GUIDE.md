# 鲸落 - 快速部署指南

## 概述

本指南提供最快速的Docker部署方案，适合生产环境使用。

## 一键部署

### 1. 服务器准备

```bash
# 在Debian服务器上执行
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
sudo apt install docker-compose-plugin -y

# 重新登录以应用Docker权限
exit
# 重新SSH登录
```

### 2. 项目部署

```bash
# 克隆项目
git clone https://github.com/your-username/TaifishingV4.git
cd TaifishingV4

# 配置环境变量
cp env.prod .env
nano .env  # 修改数据库密码等配置

# 一键部署
./scripts/deploy.sh prod start
```

### 3. 验证部署

```bash
# 检查服务状态
./scripts/deploy.sh prod status

# 查看管理员密码
./scripts/deploy.sh prod admin

# 访问应用
curl http://localhost/health
```

## 常用命令

```bash
# 启动服务
./scripts/deploy.sh prod start

# 停止服务
./scripts/deploy.sh prod stop

# 重启服务
./scripts/deploy.sh prod restart

# 查看日志
./scripts/deploy.sh prod logs

# 查看特定服务日志
./scripts/deploy.sh prod logs whalefall

# 备份数据
./scripts/deploy.sh prod backup

# 清理资源
./scripts/deploy.sh cleanup
```

## 配置说明

### 环境变量配置

编辑 `.env` 文件，修改以下关键配置：

```ini
# 数据库密码
POSTGRES_PASSWORD=your-secure-db-password

# Redis密码
REDIS_PASSWORD=your-redis-password

# 应用密钥
SECRET_KEY=your-super-secret-key

# 管理员密码
DEFAULT_ADMIN_PASSWORD=your-admin-password
```

### SSL证书配置

#### 使用Let's Encrypt

```bash
# 安装Certbot
sudo apt install certbot -y

# 获取证书
sudo certbot certonly --standalone -d your-domain.com

# 复制证书
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/key.pem
sudo chown -R $USER:$USER nginx/ssl
```

#### 使用自签名证书

```bash
# 创建证书目录
mkdir -p nginx/ssl

# 生成自签名证书
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx/ssl/key.pem \
    -out nginx/ssl/cert.pem \
    -subj "/C=CN/ST=State/L=City/O=Organization/CN=your-domain.com"
```

## 故障排除

### 服务无法启动

```bash
# 查看详细日志
./scripts/deploy.sh prod logs

# 检查端口占用
netstat -tlnp | grep :80
netstat -tlnp | grep :443

# 重启服务
./scripts/deploy.sh prod restart
```

### 数据库连接失败

```bash
# 检查数据库状态
docker ps | grep postgres

# 查看数据库日志
./scripts/deploy.sh prod logs postgres

# 重新创建管理员
./scripts/deploy.sh prod admin
```

### SSL证书问题

```bash
# 检查证书文件
ls -la nginx/ssl/

# 测试SSL连接
openssl s_client -connect your-domain.com:443
```

## 维护操作

### 定期备份

```bash
# 设置定时备份
crontab -e

# 添加以下行（每天凌晨2点备份）
0 2 * * * /opt/whalefall/scripts/deploy.sh prod backup
```

### 更新部署

```bash
# 拉取最新代码
git pull origin main

# 重新构建和部署
./scripts/deploy.sh prod build
./scripts/deploy.sh prod restart
```

### 监控资源

```bash
# 查看容器状态
docker ps

# 查看资源使用
docker stats

# 查看磁盘使用
df -h
```

## 安全建议

1. **修改默认密码**: 立即修改数据库和管理员密码
2. **配置防火墙**: 只开放80/443端口
3. **定期更新**: 保持系统和依赖包最新
4. **监控日志**: 定期检查应用和系统日志
5. **备份数据**: 设置自动备份策略

## 性能优化

### 数据库优化

```sql
-- 连接数据库
docker exec -it whalefall_postgres psql -U whalefall_user -d whalefall_prod

-- 创建索引
CREATE INDEX CONCURRENTLY idx_accounts_username ON accounts(username);
CREATE INDEX CONCURRENTLY idx_instances_name ON instances(name);
```

### Redis优化

```bash
# 连接Redis
docker exec -it whalefall_redis redis-cli

# 查看内存使用
INFO memory

# 清理过期键
FLUSHDB
```

## 联系支持

- 项目文档: `/docs/`
- 详细部署指南: `docs/deployment/DOCKER_PRODUCTION_DEPLOYMENT.md`
- 技术支持: 提交GitHub Issue
