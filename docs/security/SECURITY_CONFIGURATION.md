# 安全配置指南

## 🔒 概述

本指南说明如何安全地配置鲸落项目，避免硬编码密码和密钥等安全风险。

## ⚠️ 安全警告

**重要**: 本项目已移除所有硬编码密码和密钥，所有敏感信息必须通过环境变量配置。

## 🔧 必需的环境变量

### 数据库配置

```bash
# PostgreSQL数据库连接
DATABASE_URL=postgresql://whalefall_user:your_secure_password@localhost:5432/whalefall_dev

# Redis缓存连接
CACHE_REDIS_URL=redis://:your_redis_password@localhost:6379/0
```

### 安全配置

```bash
# Flask应用密钥（必须设置）
SECRET_KEY=your_very_secure_secret_key_here

# JWT令牌密钥（必须设置）
JWT_SECRET_KEY=your_very_secure_jwt_secret_key_here

# 密码哈希轮数
BCRYPT_LOG_ROUNDS=12
```

### 应用配置

```bash
# 应用信息
APP_NAME=鲸落
APP_VERSION=1.0.1
FLASK_ENV=development
FLASK_DEBUG=1
LOG_LEVEL=DEBUG
```

## 🚀 快速配置

### 1. 复制环境配置文件

```bash
# 开发环境
cp env.development .env

# 生产环境
cp env.production .env
```

### 2. 编辑环境变量

```bash
# 编辑.env文件
vim .env
```

**重要**: 必须修改以下敏感信息：
- `POSTGRES_PASSWORD` - 数据库密码
- `REDIS_PASSWORD` - Redis密码
- `SECRET_KEY` - Flask密钥
- `JWT_SECRET_KEY` - JWT密钥

### 3. 验证配置

```bash
# 验证环境变量
./scripts/validate_env.sh

# 验证安全配置
python scripts/security/validate_security_config.py
```

## 🔍 安全检查

### 自动检查

项目提供了安全配置验证脚本：

```bash
# 检查硬编码凭据
python scripts/security/validate_security_config.py

# 检查环境变量
./scripts/validate_env.sh
```

### 手动检查

1. **检查代码中是否有硬编码密码**
   ```bash
   grep -r "password.*=" app/
   grep -r "Taifish2024" app/
   ```

2. **检查环境变量是否正确设置**
   ```bash
   echo $DATABASE_URL
   echo $CACHE_REDIS_URL
   echo $SECRET_KEY
   ```

## 🛡️ 安全最佳实践

### 1. 密码安全

- 使用强密码（至少12位，包含大小写字母、数字和特殊字符）
- 定期更换密码
- 不同环境使用不同的密码
- 不要在代码中硬编码密码

### 2. 密钥管理

- 使用随机生成的密钥
- 密钥长度至少32位
- 定期轮换密钥
- 使用环境变量存储密钥

### 3. 环境隔离

- 开发、测试、生产环境使用不同的配置
- 生产环境使用更强的密码和密钥
- 限制生产环境访问权限

### 4. 文件安全

- `.env`文件不要提交到版本控制
- 使用`.gitignore`忽略敏感文件
- 设置适当的文件权限

## 🚨 常见问题

### Q: 应用启动失败，提示缺少环境变量

**A**: 确保所有必需的环境变量都已设置：

```bash
# 检查环境变量
./scripts/validate_env.sh

# 如果缺少，请设置环境变量
export DATABASE_URL="postgresql://user:pass@localhost:5432/db"
export CACHE_REDIS_URL="redis://:pass@localhost:6379/0"
export SECRET_KEY="your_secret_key"
export JWT_SECRET_KEY="your_jwt_secret_key"
```

### Q: 如何生成安全的密钥？

**A**: 使用以下方法生成安全密钥：

```python
import secrets
import string

# 生成32位随机密钥
secret_key = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
print(secret_key)
```

或者使用OpenSSL：

```bash
# 生成32位随机密钥
openssl rand -hex 32
```

### Q: 生产环境如何配置？

**A**: 生产环境配置建议：

1. 使用强密码和密钥
2. 设置`FLASK_ENV=production`
3. 设置`FLASK_DEBUG=0`
4. 使用HTTPS
5. 定期备份配置

## 📚 相关文档

- [环境变量配置指南](../guides/ENVIRONMENT_VARIABLES.md)
- [部署安全指南](../deployment/SECURITY_DEPLOYMENT.md)
- [密码管理指南](../guides/ADMIN_PASSWORD_MANAGEMENT.md)

## 🔄 更新日志

- **v1.0.1** - 移除硬编码密码，强制使用环境变量
- **v1.0.0** - 初始安全配置指南
