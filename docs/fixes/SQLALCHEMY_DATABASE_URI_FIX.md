# SQLAlchemy 数据库连接 URI 特殊字符转义修复

## 1. 问题背景

当数据库连接密码包含特殊字符（如 `@`, `:`, `?` 等）时，SQLAlchemy 在解析数据库连接 URI (DATABASE_URI) 时会发生错误，导致连接失败。

**问题原因**: 特殊字符未经过正确的 URL 转义，干扰了 URI 的解析。

## 2. 解决方案

为了解决此问题，我们引入了 `urllib.parse.quote_plus` 方法，对密码中的特殊字符进行转义。

### 修复逻辑

在构建 `DATABASE_URI` 时，我们对密码部分进行如下处理：

```python
from urllib.parse import quote_plus

password = "your_password_with_@_and_other_chars"
encoded_password = quote_plus(password)

DATABASE_URI = f"postgresql://user:{encoded_password}@host:port/dbname"
```

通过 `quote_plus`，密码中的所有特殊字符都会被转换为 URL 安全的格式（例如 `@` 会被转义为 `%40`），从而确保 `DATABASE_URI` 能够被正确解析。

### 应用范围

此修复已应用于所有支持的数据库连接配置中，包括：

- PostgreSQL
- MySQL
- SQL Server
- Oracle

## 3. 修复效果

- **支持特殊字符密码**: 用户现在可以在数据库密码中使用各种特殊字符，系统能够正确处理并成功连接数据库。
- **连接稳定性增强**: 避免了因密码特殊字符导致的连接失败问题，提升了系统的健壮性。
- **安全性提升**: 允许用户设置更复杂的密码，增强了数据库的安全性。