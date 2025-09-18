# 环境部署指南

## 🔐 密码加密密钥管理

### 生产环境部署

#### 1. 生成新的安全密钥
```bash
# 生成32字节的随机密钥
python -c "
import secrets
import base64
key = secrets.token_bytes(32)
encoded_key = base64.b64encode(key).decode('utf-8')
print(f'PASSWORD_ENCRYPTION_KEY={encoded_key}')
"
```

#### 2. 环境变量配置
```bash
# 生产环境 .env 文件
PASSWORD_ENCRYPTION_KEY=你的新密钥
REDIS_URL=redis://:你的redis密码@redis服务器:6379/0
CACHE_REDIS_URL=redis://:你的redis密码@redis服务器:6379/0
SECRET_KEY=你的Flask密钥
JWT_SECRET_KEY=你的JWT密钥
```

#### 3. 数据库迁移
- 新环境：直接使用新密钥
- 现有环境：**不要修改密钥**，除非要重新配置所有数据库连接

### 开发环境

#### 1. 使用固定密钥（团队共享）
```bash
# 开发环境使用固定密钥，便于团队协作
PASSWORD_ENCRYPTION_KEY=dev-key-for-team-sharing
```

#### 2. 或者使用环境变量
```bash
export PASSWORD_ENCRYPTION_KEY="你的开发密钥"
```

## 🚀 部署步骤

### 1. 新环境部署
1. 生成新的`PASSWORD_ENCRYPTION_KEY`
2. 配置环境变量
3. 重新配置所有数据库连接
4. 测试所有功能

### 2. 现有环境迁移
1. **备份现有数据**
2. 导出所有数据库连接信息
3. 生成新密钥
4. 重新配置所有连接
5. 验证功能正常

## ⚠️ 安全建议

1. **生产环境密钥**：使用强随机密钥，定期轮换
2. **开发环境密钥**：可以使用固定密钥便于团队协作
3. **密钥存储**：使用环境变量或密钥管理服务
4. **备份策略**：修改密钥前务必备份所有加密数据

## 🔄 密钥轮换流程

如果需要轮换密钥：

1. 导出所有加密的密码
2. 生成新密钥
3. 使用新密钥重新加密密码
4. 更新环境变量
5. 重启应用
6. 验证所有连接正常

## 📝 注意事项

- **永远不要**在生产环境中使用开发密钥
- **永远不要**在代码中硬编码密钥
- **永远不要**将密钥提交到版本控制系统
- 修改密钥前**务必备份**所有加密数据
