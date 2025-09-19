# Nginx 502 Bad Gateway 修复总结

## 问题描述

访问 `http://localhost/` 时出现 **502 Bad Gateway** 错误，Nginx 无法连接到后端 Flask 应用。

## 错误原因

Nginx 容器配置中的 upstream 服务器地址不正确：

```nginx
# 错误的配置
upstream whalefall_backend {
    server whalefall:5001;  # ❌ 指向不存在的容器
}
```

**问题分析**：
- Flask 应用运行在主机上（`127.0.0.1:5001`），不是 Docker 容器
- Nginx 容器无法通过 `whalefall:5001` 访问主机上的服务
- 需要使用 Docker Desktop 的特殊主机名来访问主机服务

## 修复方案

### 1. 更新 Nginx 配置

修改 `nginx/conf.d/whalefall.conf` 文件：

```nginx
# 修复后的配置
upstream whalefall_backend {
    server host.docker.internal:5001;  # ✅ 指向主机上的服务
}
```

### 2. 重启 Nginx 容器

```bash
docker restart whalefall_nginx
```

## 修复结果

✅ **Nginx 状态**：从 "unhealthy" 变为 "healthy"  
✅ **HTTP 响应**：正常返回 302 重定向到登录页面  
✅ **登录页面**：正常返回 200 状态码  
✅ **代理功能**：Nginx 成功代理请求到 Flask 应用  

## 验证方法

### 1. 检查 Nginx 状态
```bash
docker ps | grep nginx
# 应该显示 "healthy" 状态
```

### 2. 测试 HTTP 访问
```bash
# 测试根路径（应该重定向到登录页）
curl -I http://localhost/

# 测试登录页面
curl -I http://localhost/auth/login
```

### 3. 检查 Nginx 日志
```bash
docker logs whalefall_nginx
```

## 技术说明

### Docker Desktop 网络访问

在 Docker Desktop for Mac/Windows 中，容器访问主机服务需要使用特殊的主机名：

- **`host.docker.internal`**：指向主机（Docker Desktop 提供）
- **`127.0.0.1`**：在容器内部指向容器本身，不是主机
- **`localhost`**：在容器内部指向容器本身，不是主机

### 网络架构

```
Internet → Nginx Container → host.docker.internal:5001 → Flask App (Host)
```

## 相关文件

- **配置文件**：`nginx/conf.d/whalefall.conf`
- **Docker 配置**：`docker-compose.base.yml`
- **网络**：`taifishingv4_whalefall_network`

## 注意事项

1. **环境差异**：在 Linux 环境中可能需要使用 `172.17.0.1` 或 `host-gateway`
2. **端口映射**：确保 Flask 应用在 5001 端口监听
3. **防火墙**：确保主机防火墙允许 5001 端口访问
4. **健康检查**：Nginx 健康检查现在可以正常工作

## 后续优化建议

1. **使用 Docker Compose 网络**：将 Flask 应用也容器化，使用内部网络通信
2. **负载均衡**：如果有多个 Flask 实例，可以配置多个 upstream 服务器
3. **SSL 终止**：在 Nginx 层面配置 HTTPS
4. **缓存优化**：配置静态文件缓存和反向代理缓存

---

**修复时间**：2025-09-19  
**修复人员**：AI Assistant  
**影响范围**：Nginx 代理配置  
**测试状态**：✅ 通过
