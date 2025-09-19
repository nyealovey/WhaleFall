# Nginx配置切换指南

## 概述

当Flask应用从主机运行切换到Docker容器运行时，需要相应修改Nginx配置。本指南提供了完整的切换方案和自动化脚本。

## 配置对比

### 当前配置（主机Flask）

```nginx
upstream whalefall_backend {
    server host.docker.internal:5001;  # 指向主机上的Flask应用
}
```

**适用场景**：
- Flask应用运行在主机上（`uv run python app.py`）
- Nginx运行在Docker容器中
- 开发环境或混合部署

### 目标配置（容器Flask）

```nginx
upstream whalefall_backend {
    server whalefall_app:5001;  # 指向Docker容器中的Flask应用
}
```

**适用场景**：
- Flask应用运行在Docker容器中
- 所有服务都在Docker网络中
- 生产环境统一部署

## 切换方案

### 方案1：使用自动化脚本（推荐）

```bash
# 查看当前配置状态
./scripts/switch-nginx-config.sh status

# 切换到容器Flask配置
./scripts/switch-nginx-config.sh docker

# 切换到主机Flask配置
./scripts/switch-nginx-config.sh host
```

### 方案2：手动修改配置

1. **编辑Nginx配置文件**：
   ```bash
   vim nginx/conf.d/whalefall.conf
   ```

2. **修改upstream服务器**：
   ```nginx
   # 从主机Flask切换到容器Flask
   upstream whalefall_backend {
       server whalefall_app:5001;  # 修改这一行
   }
   ```

3. **重启Nginx容器**：
   ```bash
   docker restart whalefall_nginx
   ```

### 方案3：使用不同的配置文件

```bash
# 备份当前配置
cp nginx/conf.d/whalefall.conf nginx/conf.d/whalefall-host.conf

# 使用容器Flask配置
cp nginx/conf.d/whalefall-docker.conf nginx/conf.d/whalefall.conf

# 重启Nginx
docker restart whalefall_nginx
```

## 部署场景

### 场景1：开发环境（当前）

```bash
# 启动基础环境
docker-compose -f docker-compose.base.yml up -d

# 在主机运行Flask
uv run python app.py

# Nginx配置：host.docker.internal:5001
```

### 场景2：容器化开发

```bash
# 构建Flask镜像
docker build -t whalefall:latest .

# 启动完整环境
docker-compose -f docker-compose.full.yml up -d

# Nginx配置：whalefall_app:5001
```

### 场景3：生产环境

```bash
# 使用生产环境配置
cp env.production .env

# 启动完整环境
docker-compose -f docker-compose.full.yml up -d

# Nginx配置：whalefall_app:5001
```

## 网络架构对比

### 主机Flask架构

```
Internet → Nginx Container → host.docker.internal:5001 → Flask App (Host)
                ↓
        Docker Network (whalefall_network)
                ↓
        PostgreSQL Container + Redis Container
```

### 容器Flask架构

```
Internet → Nginx Container → whalefall_app:5001 → Flask Container
                ↓
        Docker Network (whalefall_network)
                ↓
        PostgreSQL Container + Redis Container
```

## 验证方法

### 1. 检查Nginx配置

```bash
# 查看当前upstream配置
docker exec whalefall_nginx cat /etc/nginx/conf.d/whalefall.conf | grep -A 3 upstream
```

### 2. 测试连接

```bash
# 测试HTTP访问
curl -I http://localhost/

# 测试登录页面
curl -I http://localhost/auth/login

# 检查Nginx日志
docker logs whalefall_nginx
```

### 3. 检查容器状态

```bash
# 查看所有容器状态
docker ps

# 检查网络连接
docker network inspect whalefall_network
```

## 故障排除

### 问题1：502 Bad Gateway

**原因**：Nginx无法连接到Flask应用

**解决方案**：
1. 检查upstream配置是否正确
2. 确认Flask应用是否在指定端口运行
3. 检查Docker网络连接

```bash
# 检查Flask应用状态
docker ps | grep whalefall

# 测试网络连接
docker exec whalefall_nginx ping whalefall_app
```

### 问题2：连接超时

**原因**：Flask应用启动时间过长

**解决方案**：
1. 增加Nginx超时配置
2. 添加健康检查
3. 优化Flask应用启动时间

### 问题3：DNS解析失败

**原因**：容器名无法解析

**解决方案**：
1. 确保所有容器在同一网络中
2. 检查容器名是否正确
3. 使用服务名而不是容器名

## 最佳实践

### 1. 配置管理

- 使用版本控制管理配置文件
- 为不同环境创建不同的配置模板
- 使用自动化脚本减少手动错误

### 2. 监控和日志

- 配置Nginx访问日志和错误日志
- 监控容器健康状态
- 设置告警机制

### 3. 安全考虑

- 使用内部网络通信
- 配置适当的防火墙规则
- 定期更新容器镜像

## 相关文件

- **Nginx配置**：`nginx/conf.d/whalefall.conf`
- **容器Flask配置**：`nginx/conf.d/whalefall-docker.conf`
- **切换脚本**：`scripts/switch-nginx-config.sh`
- **完整部署**：`docker-compose.full.yml`
- **基础环境**：`docker-compose.base.yml`
- **Flask环境**：`docker-compose.flask.yml`

## 总结

通过本指南，您可以轻松地在主机Flask和容器Flask之间切换Nginx配置。建议在开发阶段使用主机Flask模式，在生产环境使用容器Flask模式，以获得更好的隔离性和可维护性。

---

**更新时间**：2025-09-19  
**适用版本**：鲸落 v4.0.0+  
**维护人员**：AI Assistant
