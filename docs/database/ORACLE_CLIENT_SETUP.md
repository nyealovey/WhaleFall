# Oracle客户端配置指南

## 概述

本项目支持Oracle数据库连接，需要安装Oracle Instant Client。本文档介绍在不同环境中配置Oracle客户端的详细步骤。

## 支持的Oracle版本

- **Oracle Instant Client**: 21.18.0.0.0
- **Python驱动**: oracledb 3.3.0
- **支持的操作系统**: Linux x64, macOS (Intel/Apple Silicon)

## 1. Docker环境配置

### 1.1 自动安装（推荐）

Dockerfile已自动包含Oracle Instant Client安装：

```dockerfile
# 安装Oracle Instant Client
ENV ORACLE_CLIENT_VERSION=21.18.0.0.0
ENV ORACLE_HOME=/opt/oracle/instantclient_21_18_0_0_0

# 下载并安装Oracle Instant Client for Linux
RUN mkdir -p $ORACLE_HOME && \
    wget -q https://download.oracle.com/otn_software/linux/instantclient/2118000/instantclient-basic-linux.x64-${ORACLE_CLIENT_VERSION}dbru.zip -O /tmp/instantclient-basic.zip && \
    wget -q https://download.oracle.com/otn_software/linux/instantclient/2118000/instantclient-sdk-linux.x64-${ORACLE_CLIENT_VERSION}dbru.zip -O /tmp/instantclient-sdk.zip && \
    unzip -q /tmp/instantclient-basic.zip -d /opt/oracle && \
    unzip -q /tmp/instantclient-sdk.zip -d /opt/oracle && \
    rm /tmp/instantclient-basic.zip /tmp/instantclient-sdk.zip && \
    echo "$ORACLE_HOME" > /etc/ld.so.conf.d/oracle-instantclient.conf && \
    ldconfig

# 设置Oracle环境变量
ENV LD_LIBRARY_PATH=$ORACLE_HOME:$LD_LIBRARY_PATH
ENV PATH=$ORACLE_HOME:$PATH
```

### 1.2 构建镜像

```bash
# 无代理环境
docker build -t whalefall:latest .

# 有代理环境
./build-proxy.sh http://proxy.company.com:8080
```

## 2. 本地开发环境配置

### 2.1 自动安装脚本

使用提供的安装脚本：

```bash
# 运行Oracle客户端安装脚本
./scripts/oracle/install-oracle-client.sh
```

### 2.2 手动安装

#### macOS安装

1. **下载Oracle Instant Client**
   ```bash
   # Intel Mac
   wget https://download.oracle.com/otn_software/mac/instantclient/2118000/instantclient-basic-macos.x64-21.18.0.0.0dbru.zip
   wget https://download.oracle.com/otn_software/mac/instantclient/2118000/instantclient-sdk-macos.x64-21.18.0.0.0dbru.zip
   
   # Apple Silicon Mac
   wget https://download.oracle.com/otn_software/mac/instantclient/2118000/instantclient-basic-macos.arm64-21.18.0.0.0dbru.zip
   wget https://download.oracle.com/otn_software/mac/instantclient/2118000/instantclient-sdk-macos.arm64-21.18.0.0.0dbru.zip
   ```

2. **解压和安装**
   ```bash
   unzip instantclient-basic-macos.*.zip
   unzip instantclient-sdk-macos.*.zip
   mkdir -p oracle_client
   cp -r instantclient_*/lib oracle_client/
   cp -r instantclient_*/sdk oracle_client/
   ```

3. **设置环境变量**
   ```bash
   export ORACLE_HOME=$(pwd)/oracle_client
   export DYLD_LIBRARY_PATH=$ORACLE_HOME/lib:$DYLD_LIBRARY_PATH
   export PATH=$ORACLE_HOME:$PATH
   ```

#### Linux安装

1. **下载Oracle Instant Client**
   ```bash
   wget https://download.oracle.com/otn_software/linux/instantclient/2118000/instantclient-basic-linux.x64-21.18.0.0.0dbru.zip
   wget https://download.oracle.com/otn_software/linux/instantclient/2118000/instantclient-sdk-linux.x64-21.18.0.0.0dbru.zip
   ```

2. **解压和安装**
   ```bash
   unzip instantclient-basic-linux.x64-21.18.0.0.0dbru.zip
   unzip instantclient-sdk-linux.x64-21.18.0.0.0dbru.zip
   mkdir -p oracle_client
   cp -r instantclient_*/lib oracle_client/
   cp -r instantclient_*/sdk oracle_client/
   ```

3. **设置环境变量**
   ```bash
   export ORACLE_HOME=$(pwd)/oracle_client
   export LD_LIBRARY_PATH=$ORACLE_HOME/lib:$LD_LIBRARY_PATH
   export PATH=$ORACLE_HOME:$PATH
   ```

## 3. 环境变量配置

### 3.1 必需的环境变量

```bash
# Oracle客户端路径
export ORACLE_HOME=/path/to/oracle_client

# 库文件路径
export LD_LIBRARY_PATH=$ORACLE_HOME/lib:$LD_LIBRARY_PATH  # Linux
export DYLD_LIBRARY_PATH=$ORACLE_HOME/lib:$DYLD_LIBRARY_PATH  # macOS

# 可执行文件路径
export PATH=$ORACLE_HOME:$PATH
```

### 3.2 数据库连接配置

```bash
# Oracle数据库连接参数
export ORACLE_HOST=localhost
export ORACLE_PORT=1521
export ORACLE_SERVICE=XE
export ORACLE_USER=system
export ORACLE_PASSWORD=oracle
```

## 4. 测试连接

### 4.1 使用测试脚本

```bash
# 运行Oracle连接测试
python scripts/oracle/test-oracle-connection.py
```

### 4.2 手动测试

```python
import oracledb

# 测试驱动导入
print(f"Oracle驱动版本: {oracledb.__version__}")

# 测试客户端库
client_lib_path = oracledb.init_oracle_client()
print(f"Oracle客户端库路径: {client_lib_path}")

# 测试数据库连接
with oracledb.connect(
    user="system",
    password="oracle",
    dsn="localhost:1521/XE"
) as connection:
    with connection.cursor() as cursor:
        cursor.execute("SELECT SYSDATE FROM DUAL")
        result = cursor.fetchone()
        print(f"数据库时间: {result[0]}")
```

## 5. 常见问题解决

### 5.1 库文件找不到

**错误**: `oracledb.exceptions.DatabaseError: DPI-1047: Cannot locate a 64-bit Oracle Client library`

**解决方案**:
1. 检查`ORACLE_HOME`环境变量是否正确设置
2. 检查`LD_LIBRARY_PATH`或`DYLD_LIBRARY_PATH`是否包含Oracle库文件路径
3. 确认下载的是64位版本的Oracle Instant Client

### 5.2 权限问题

**错误**: `Permission denied` 或 `Access denied`

**解决方案**:
```bash
# 设置正确的权限
chmod -R 755 oracle_client/
chmod +x oracle_client/lib/*
```

### 5.3 版本不兼容

**错误**: `DPI-1047: Oracle Client library version is not supported`

**解决方案**:
1. 确保使用Oracle Instant Client 21.18.0.0.0或更高版本
2. 检查Python oracledb驱动版本是否为3.3.0或更高

### 5.4 网络连接问题

**错误**: `ORA-12541: TNS:no listener` 或 `ORA-12535: TNS:operation timed out`

**解决方案**:
1. 检查Oracle数据库服务是否运行
2. 确认网络连接和防火墙设置
3. 验证连接字符串格式：`host:port/service_name`

## 6. 性能优化

### 6.1 连接池配置

```python
import oracledb

# 创建连接池
pool = oracledb.create_pool(
    user="system",
    password="oracle",
    dsn="localhost:1521/XE",
    min=2,
    max=10,
    increment=1,
    encoding="UTF-8"
)

# 使用连接池
with pool.acquire() as connection:
    # 执行数据库操作
    pass
```

### 6.2 环境变量优化

```bash
# 设置Oracle优化参数
export ORACLE_SQLPLUS_RELEASE=21.0.0.0.0
export TNS_ADMIN=$ORACLE_HOME/network/admin
```

## 7. 安全注意事项

1. **密码安全**: 不要在代码中硬编码数据库密码
2. **网络安全**: 使用加密连接（TLS/SSL）
3. **权限控制**: 使用最小权限原则
4. **审计日志**: 启用Oracle审计功能

## 8. 参考资料

- [Oracle Instant Client下载页面](https://www.oracle.com/database/technologies/instant-client/downloads.html)
- [Python oracledb驱动文档](https://python-oracledb.readthedocs.io/)
- [Oracle数据库连接字符串格式](https://docs.oracle.com/en/database/oracle/oracle-database/21/netag/configuring-naming-methods.html)
