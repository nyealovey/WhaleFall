# Oracle Instant Client 设置指南

## 问题说明

如果您遇到以下错误：
```
ModuleNotFoundError: No module named 'flask'
```

这表示您没有在虚拟环境中运行应用。

## 解决方案

### 方法1：使用启动脚本（推荐）

```bash
# 使用我们提供的启动脚本
./start_app.sh
```

### 方法2：手动激活虚拟环境

```bash
# 1. 激活虚拟环境
source venv/bin/activate

# 2. 验证环境
python3 -c "import flask; print('Flask已安装')"

# 3. 启动应用
python3 app.py
```

### 方法3：使用Flask命令

```bash
# 1. 激活虚拟环境
source venv/bin/activate

# 2. 设置环境变量
export FLASK_APP=app
export FLASK_ENV=development

# 3. 启动应用
flask run --host=0.0.0.0 --port=5001
```

## Oracle Instant Client 配置

Oracle Instant Client 环境变量已配置在 `.env` 文件中：

```bash
# Oracle Instant Client配置
DYLD_LIBRARY_PATH=/Users/apple/Downloads/instantclient_23_3
```

应用启动时会自动加载这些环境变量。

## 验证安装

运行以下命令验证Oracle配置：

```bash
# 激活虚拟环境
source venv/bin/activate

# 测试Oracle连接
python3 -c "
import cx_Oracle
print(f'cx_Oracle版本: {cx_Oracle.version}')
print(f'Oracle Client版本: {cx_Oracle.clientversion()}')
"
```

## 常见问题

### 1. ModuleNotFoundError: No module named 'flask'
**原因**: 没有在虚拟环境中运行
**解决**: 先运行 `source venv/bin/activate`

### 2. DPI-1047: Cannot locate an Oracle Client library
**原因**: Oracle Instant Client路径不正确
**解决**: 检查 `.env` 文件中的 `DYLD_LIBRARY_PATH` 设置

### 3. 应用启动后无法访问
**原因**: 端口被占用或防火墙阻止
**解决**: 检查端口5001是否可用，或使用其他端口

## 快速启动

```bash
# 一键启动（推荐）
./start_app.sh

# 或者手动启动
source venv/bin/activate && python3 app.py
```
