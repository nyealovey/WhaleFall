# 数据库驱动配置指南

## 支持的数据库

### ✅ 完全支持
- **MySQL**: PyMySQL 1.0.2
- **PostgreSQL**: psycopg2-binary 2.9.3

### ⚠️ 需要额外配置
- **SQL Server**: 需要系统依赖
- **Oracle**: 需要Oracle Instant Client

## 快速安装

### MySQL & PostgreSQL
```bash
pip install PyMySQL==1.0.2 psycopg2-binary==2.9.3
```

### SQL Server
```bash
# macOS
brew install freetds
pip install pymssql==2.2.5

# 或使用Docker
docker pull mcr.microsoft.com/mssql/server:2019-latest
```

### Oracle
```bash
# 安装驱动
pip install python-oracledb==3.3.0

# macOS - 安装客户端
brew install instantclient-basic instantclient-sdk

# 设置环境变量
export ORACLE_HOME=/opt/homebrew/lib/instantclient_21_8
export LD_LIBRARY_PATH=$ORACLE_HOME:$LD_LIBRARY_PATH
export PATH=$ORACLE_HOME:$PATH
```

## Docker环境

Docker镜像已预装所有数据库驱动，包括Oracle Instant Client，无需额外配置。

## 测试连接

```python
# 测试Oracle连接
import oracledb
with oracledb.connect(user="system", password="oracle", dsn="localhost:1521/XE") as conn:
    print("Oracle连接成功")
```
- 需要根据实际使用的数据库安装相应驱动
- 可以使用Docker简化部署
- 可以分阶段添加数据库支持

## 🔄 动态驱动检测

系统会自动检测可用的数据库驱动，并提供相应的连接方法：

```python
from app.services.database_drivers import driver_manager

# 检查驱动状态
print(driver_manager.get_status_report())

# 获取连接字符串
conn_str = driver_manager.get_connection_string(
    db_type='MySQL',
    host='localhost',
    port=3306,
    username='user',
    password='pass',
    database='mydb'
)
```

## 💡 建议

1. **继续开发**: 当前配置完全支持核心功能开发
2. **按需添加**: 根据实际需要逐步添加数据库支持
3. **使用Docker**: 生产环境使用Docker简化依赖管理
4. **测试优先**: 先完成功能开发，再优化数据库支持

## 🎯 下一步

1. 继续开发核心功能
2. 完成用户认证系统
3. 实现实例管理功能
4. 根据实际需要添加数据库驱动
