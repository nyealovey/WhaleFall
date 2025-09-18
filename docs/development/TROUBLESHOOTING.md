# 故障排除指南

## 概述

本文档提供泰摸鱼吧开发环境中常见问题的解决方案，帮助开发者快速解决遇到的问题。

## 常见问题分类

### 1. 环境配置问题

#### Python版本问题

**问题**: Python版本不兼容
```
Error: Python 3.8 is not supported. Please use Python 3.11 or 3.12.
```

**解决方案**:
```bash
# 检查当前Python版本
python --version

# 安装Python 3.12
# macOS
brew install python@3.12

# Ubuntu/Debian
sudo apt install python3.12 python3.12-venv python3.12-pip

# 重新创建虚拟环境
rm -rf venv
python3.12 -m venv venv
source venv/bin/activate
```

#### 虚拟环境问题

**问题**: 虚拟环境激活失败
```
bash: venv/bin/activate: No such file or directory
```

**解决方案**:
```bash
# 重新创建虚拟环境
rm -rf venv
python3 -m venv venv
source venv/bin/activate

# 验证激活
which python
```

### 2. 依赖安装问题

#### pip安装失败

**问题**: 依赖包安装失败
```
ERROR: Could not find a version that satisfies the requirement
```

**解决方案**:
```bash
# 升级pip
pip install --upgrade pip

# 清理缓存
pip cache purge

# 使用国内镜像源
pip install -r requirements-local.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 或使用官方源
pip install -r requirements-local.txt --no-cache-dir
```

#### 编译错误

**问题**: 某些包编译失败
```
error: Microsoft Visual C++ 14.0 is required
```

**解决方案**:
```bash
# Windows: 安装Visual Studio Build Tools
# 下载地址: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# 或使用预编译包
pip install --only-binary=all -r requirements-local.txt

# macOS: 安装Xcode命令行工具
xcode-select --install
```

### 3. 数据库问题

#### PostgreSQL连接失败

**问题**: 无法连接到PostgreSQL数据库
```
psycopg2.OperationalError: could not connect to server
```

**解决方案**:
```bash
# 检查PostgreSQL服务状态
sudo systemctl status postgresql

# 启动PostgreSQL服务
sudo systemctl start postgresql

# 检查数据库连接
psql -h localhost -U taifish_user -d taifish_db

# 检查数据库配置
grep DATABASE_URL .env
```

#### 数据库迁移问题

**问题**: 迁移失败
```
ERROR: Can't locate revision identified by 'xxxx'
```

**解决方案**:
```bash
# 查看迁移历史
flask db history

# 重置迁移
rm -rf migrations/
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 4. Redis问题

#### Redis连接失败

**问题**: Redis连接超时
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**解决方案**:
```bash
# 检查Redis状态
./redis_manager.sh status

# 启动Redis
./redis_manager.sh start

# 检查端口占用
lsof -i :6379

# 重启Redis
./redis_manager.sh restart
```

#### Redis权限问题

**问题**: Redis权限被拒绝
```
Permission denied: /var/lib/redis/dump.rdb
```

**解决方案**:
```bash
# 修复Redis数据目录权限
sudo chown -R redis:redis /var/lib/redis
sudo chmod 755 /var/lib/redis

# 或使用项目Redis配置
./redis_manager.sh start
```

### 5. 端口占用问题

#### Flask端口占用

**问题**: 端口5001被占用
```
OSError: [Errno 48] Address already in use
```

**解决方案**:
```bash
# 查看端口占用
lsof -i :5001

# 杀死占用进程
kill -9 <PID>

# 或使用其他端口
export FLASK_PORT=5002
python app.py
```

#### Redis端口占用

**问题**: 端口6379被占用
```
Redis server can't start: bind: Address already in use
```

**解决方案**:
```bash
# 查看Redis进程
ps aux | grep redis

# 停止现有Redis
pkill redis-server

# 或使用其他端口
redis-server --port 6380
```

### 6. 权限问题

#### 文件权限问题

**问题**: 权限被拒绝
```
Permission denied: 'userdata/logs/'
```

**解决方案**:
```bash
# 修复用户数据目录权限
chmod -R 755 userdata/
chmod -R 755 userdata/logs/

# 检查目录所有权
ls -la userdata/
```

#### 脚本执行权限

**问题**: 脚本无法执行
```
bash: ./setup_dev_environment.sh: Permission denied
```

**解决方案**:
```bash
# 添加执行权限
chmod +x *.sh
chmod +x scripts/*.sh

# 验证权限
ls -la *.sh
```

### 7. 网络问题

#### 依赖下载失败

**问题**: 网络超时
```
ReadTimeoutError: HTTPSConnectionPool
```

**解决方案**:
```bash
# 增加超时时间
pip install --timeout 1000 -r requirements-local.txt

# 使用国内镜像
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ -r requirements-local.txt

# 使用代理
pip install --proxy http://proxy:port -r requirements-local.txt
```

#### Git克隆失败

**问题**: Git克隆超时
```
fatal: unable to access 'https://github.com/...': Operation timed out
```

**解决方案**:
```bash
# 配置Git代理
git config --global http.proxy http://proxy:port
git config --global https.proxy https://proxy:port

# 或使用SSH
git clone git@github.com:user/repo.git
```

### 8. 应用启动问题

#### Flask应用启动失败

**问题**: 应用无法启动
```
ModuleNotFoundError: No module named 'app'
```

**解决方案**:
```bash
# 检查当前目录
pwd

# 确保在项目根目录
cd /path/to/TaifishV4

# 检查Python路径
export PYTHONPATH=$PWD:$PYTHONPATH
python app.py
```

#### 模板文件未找到

**问题**: 模板文件找不到
```
TemplateNotFound: index.html
```

**解决方案**:
```bash
# 检查模板目录
ls -la app/templates/

# 确保模板文件存在
touch app/templates/index.html

# 检查Flask配置
python -c "from app import create_app; app = create_app(); print(app.template_folder)"
```

### 9. 性能问题

#### 应用响应慢

**问题**: 页面加载缓慢
```
页面加载时间超过5秒
```

**解决方案**:
```bash
# 检查Redis连接
./redis_manager.sh status

# 检查数据库连接
python test_database.py

# 使用PostgreSQL数据库（开发环境）
export DATABASE_URL="postgresql://taifish_user:password@localhost:5432/taifish_dev"
python app.py
```

#### 内存使用过高

**问题**: 内存使用超过2GB
```
Memory usage: 2.5GB
```

**解决方案**:
```bash
# 检查进程内存使用
ps aux | grep python

# 重启应用
pkill -f "python app.py"
python app.py

# 优化Redis内存
redis-cli CONFIG SET maxmemory 256mb
```

### 10. 开发工具问题

#### 代码检查失败

**问题**: flake8检查失败
```
E501 line too long (120 > 79 characters)
```

**解决方案**:
```bash
# 安装代码检查工具
pip install flake8 black isort

# 运行代码格式化
black app/
isort app/

# 运行代码检查
flake8 app/ --max-line-length=120
```

#### 测试失败

**问题**: 测试用例失败
```
FAILED tests/test_models.py::test_user_creation
```

**解决方案**:
```bash
# 运行特定测试
pytest tests/test_models.py::test_user_creation -v

# 查看详细错误
pytest tests/test_models.py::test_user_creation -v -s

# 重新创建测试数据库
python scripts/init_database.py
python test_database.py
```

## 调试技巧

### 1. 启用详细日志

```bash
# 设置环境变量
export FLASK_DEBUG=True
export FLASK_ENV=development

# 启动应用
python app.py
```

### 2. 使用调试器

```python
# 在代码中添加断点
import pdb; pdb.set_trace()

# 或使用ipdb
import ipdb; ipdb.set_trace()
```

### 3. 检查系统资源

```bash
# 检查内存使用
free -h

# 检查磁盘空间
df -h

# 检查进程
ps aux | grep python
```

### 4. 网络诊断

```bash
# 检查端口监听
netstat -tlnp | grep :5001

# 检查网络连接
telnet localhost 5001

# 检查DNS解析
nslookup github.com
```

## 预防措施

### 1. 定期维护

```bash
# 清理Python缓存
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete

# 清理日志文件
find userdata/logs -name "*.log" -mtime +7 -delete

# 更新依赖
pip install --upgrade -r requirements-local.txt
```

### 2. 备份重要数据

```bash
# 备份数据库
pg_dump -h localhost -U taifish_user -d taifish_db > userdata/backups/backup_$(date +%Y%m%d_%H%M%S).sql

# 备份Redis数据
redis-cli BGSAVE
```

### 3. 监控系统状态

```bash
# 创建监控脚本
cat > monitor.sh << 'EOF'
#!/bin/bash
echo "=== 系统状态监控 ==="
echo "时间: $(date)"
echo "内存使用: $(free -h | grep Mem)"
echo "磁盘使用: $(df -h | grep /)"
echo "Python进程: $(ps aux | grep python | wc -l)"
echo "Redis状态: $(./redis_manager.sh status 2>/dev/null || echo 'Redis未运行')"
EOF

chmod +x monitor.sh
```

## 获取帮助

### 1. 查看日志

```bash
# 应用日志
tail -f userdata/logs/app.log

# 错误日志
tail -f userdata/logs/error.log

# Redis日志
./redis_manager.sh logs
```

### 2. 收集系统信息

```bash
# 创建诊断报告
cat > system_info.txt << 'EOF'
=== 系统信息 ===
操作系统: $(uname -a)
Python版本: $(python --version)
Pip版本: $(pip --version)
Redis版本: $(redis-server --version 2>/dev/null || echo 'Redis未安装')
磁盘空间: $(df -h)
内存使用: $(free -h)
网络连接: $(netstat -tlnp | grep -E ':(5001|6379)')
EOF
```

### 3. 联系支持

如果以上方法都无法解决问题，请：

1. 收集系统信息
2. 记录错误日志
3. 描述复现步骤
4. 联系项目维护者

---

**注意**: 本文档会定期更新，请确保使用最新版本。如果发现新的问题或解决方案，欢迎贡献。
