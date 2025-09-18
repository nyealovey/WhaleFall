# 鲸落 - 数据库初始化文档

## 概述

本文档描述了鲸落系统的PostgreSQL数据库初始化过程，包括权限配置、分类规则和基础数据的设置。

## 数据库结构

### 核心表结构

1. **instances** - 数据库实例表
2. **accounts** - 账户表
3. **permission_configs** - 权限配置表
4. **account_classifications** - 账户分类表
5. **classification_rules** - 分类规则表
6. **account_classification_assignments** - 账户分类分配表

### 权限配置表 (permission_configs)

权限配置表存储了所有支持的数据库类型的权限信息，用于账户分类规则的配置。

#### 数据库类型支持

- **MySQL**: 46个权限配置
- **PostgreSQL**: 26个权限配置  
- **SQL Server**: 56个权限配置
- **Oracle**: 312个权限配置

#### 权限类别

**MySQL权限类别**:
- `global_privileges`: 全局权限（服务器权限）- 29个
- `database_privileges`: 数据库权限 - 17个

**PostgreSQL权限类别**:
- `predefined_roles`: 预定义角色 - 10个
- `role_attributes`: 角色属性 - 10个
- `database_privileges`: 数据库权限 - 4个
- `tablespace_privileges`: 表空间权限 - 2个

**SQL Server权限类别**:
- `server_roles`: 服务器角色 - 9个
- `database_roles`: 数据库角色 - 9个
- `server_permissions`: 服务器权限 - 19个
- `database_privileges`: 数据库权限 - 19个

**Oracle权限类别**:
- `system_privileges`: 系统权限 - 199个（基于SYS账户实际权限）
- `roles`: 角色 - 67个
- `tablespace_privileges`: 表空间权限 - 21个
- `tablespace_quotas`: 表空间配额 - 25个

## 初始化脚本

### 1. 权限配置初始化

```bash
# 运行权限配置初始化脚本
python scripts/init_permission_config.py
```

该脚本会：
- 清空现有权限配置
- 重新创建所有数据库类型的权限配置
- 确保权限配置与SYS账户实际权限完全匹配

### 2. 数据库迁移

```bash
# 创建数据库迁移
flask db migrate -m "初始化数据库结构"

# 应用数据库迁移
flask db upgrade
```

### 3. 默认分类规则初始化

系统会自动创建以下默认分类规则：

#### Oracle分类规则

1. **oracle_super** - 特权账户规则
   - 匹配条件：拥有DBA角色
   - 优先级：90

2. **oracle_grant** - 高风险账户规则
   - 匹配条件：拥有DBA角色
   - 优先级：95

#### PostgreSQL分类规则

1. **postgresql_super** - 特权账户规则
   - 匹配条件：拥有SUPERUSER角色属性
   - 优先级：90

2. **postgresql_grant** - 高风险账户规则
   - 匹配条件：拥有CREATEROLE角色属性
   - 优先级：95

## 权限配置详细说明

### MySQL权限配置

#### 全局权限 (global_privileges)

| 权限名称 | 描述 | 排序 |
|---------|------|------|
| ALTER | 修改表结构 | 1 |
| ALTER ROUTINE | 修改存储过程和函数 | 2 |
| CREATE | 创建数据库和表 | 3 |
| CREATE ROUTINE | 创建存储过程和函数 | 4 |
| CREATE TEMPORARY TABLES | 创建临时表 | 5 |
| CREATE USER | 创建用户权限 | 6 |
| CREATE VIEW | 创建视图 | 7 |
| DELETE | 删除数据 | 8 |
| DROP | 删除数据库和表 | 9 |
| EVENT | 创建、修改、删除事件 | 10 |
| EXECUTE | 执行存储过程和函数 | 11 |
| FILE | 文件操作权限 | 12 |
| GRANT OPTION | 授权权限，可以授予其他用户权限 | 13 |
| INDEX | 创建和删除索引 | 14 |
| INSERT | 插入数据 | 15 |
| LOCK TABLES | 锁定表 | 16 |
| PROCESS | 查看所有进程 | 17 |
| REFERENCES | 引用权限 | 18 |
| RELOAD | 重载权限表 | 19 |
| REPLICATION CLIENT | 复制客户端权限 | 20 |
| REPLICATION SLAVE | 复制从库权限 | 21 |
| SELECT | 查询数据 | 22 |
| SHOW DATABASES | 显示所有数据库 | 23 |
| SHOW VIEW | 显示视图 | 24 |
| SHUTDOWN | 关闭MySQL服务器 | 25 |
| SUPER | 超级权限，可以执行任何操作 | 26 |
| TRIGGER | 创建和删除触发器 | 27 |
| UPDATE | 更新数据 | 28 |
| USAGE | 无权限，仅用于连接 | 29 |

### PostgreSQL权限配置

#### 预定义角色 (predefined_roles)

| 角色名称 | 描述 | 排序 |
|---------|------|------|
| SUPERUSER | 超级用户角色，拥有所有权限 | 1 |
| CREATEDB | 创建数据库角色 | 2 |
| CREATEROLE | 创建角色角色 | 3 |
| INHERIT | 继承权限角色 | 4 |
| LOGIN | 登录角色 | 5 |
| REPLICATION | 复制角色 | 6 |
| BYPASSRLS | 绕过行级安全角色 | 7 |
| CONNECTION LIMIT | 连接限制角色 | 8 |
| VALID UNTIL | 有效期限制角色 | 9 |
| PASSWORD | 密码角色 | 10 |

### Oracle权限配置

#### 系统权限 (system_privileges) - 基于SYS账户实际权限

Oracle系统权限配置基于SYS账户的实际权限，确保100%准确性：

**核心权限示例**:
- `CREATE SESSION` - 创建会话权限
- `CREATE USER` - 创建用户权限
- `ALTER USER` - 修改用户权限
- `DROP USER` - 删除用户权限
- `CREATE ROLE` - 创建角色权限
- `ALTER ANY ROLE` - 修改任意角色权限
- `DROP ANY ROLE` - 删除任意角色权限
- `GRANT ANY PRIVILEGE` - 授予任意权限
- `GRANT ANY ROLE` - 授予任意角色
- `CREATE TABLE` - 创建表权限
- `CREATE ANY TABLE` - 创建任意表权限
- `ALTER ANY TABLE` - 修改任意表权限
- `DROP ANY TABLE` - 删除任意表权限
- `SELECT ANY TABLE` - 查询任意表权限
- `INSERT ANY TABLE` - 插入任意表权限
- `UPDATE ANY TABLE` - 更新任意表权限
- `DELETE ANY TABLE` - 删除任意表权限

**重要说明**:
- 所有权限都基于SYS账户的实际权限
- 已删除不存在的权限（如`DROP ROLE`、`CREATE INDEX`等）
- 确保权限配置与SYS账户实际权限完全匹配

## 数据验证

### 权限配置验证

```python
# 验证权限配置完整性
from app import create_app
from app.models.permission_config import PermissionConfig

app = create_app()
with app.app_context():
    # 检查各数据库类型的权限配置数量
    for db_type in ['mysql', 'postgresql', 'sqlserver', 'oracle']:
        count = PermissionConfig.query.filter_by(db_type=db_type).count()
        print(f"{db_type.upper()}: {count}个权限配置")
```

### Oracle权限准确性验证

```python
# 验证Oracle权限与SYS账户实际权限的匹配度
from app.models.account import Account
from app.models.instance import Instance
import json

# 获取SYS账户实际权限
sys_account = Account.query.filter_by(username='SYS').first()
if sys_account and sys_account.permissions:
    sys_perms = set(json.loads(sys_account.permissions)['system_privileges'])
    
    # 获取配置表中的权限
    config_perms = set()
    for perm in PermissionConfig.query.filter_by(db_type='oracle', category='system_privileges').all():
        config_perms.add(perm.permission_name)
    
    # 验证匹配度
    if sys_perms == config_perms:
        print("✅ Oracle权限配置与SYS账户实际权限完全匹配")
    else:
        print("❌ Oracle权限配置与SYS账户实际权限不匹配")
```

## 维护说明

### 添加新权限

1. 在`scripts/init_permission_config.py`中添加新权限
2. 运行初始化脚本更新权限配置
3. 更新相关文档

### 修改权限配置

1. 直接修改数据库中的权限配置
2. 或者修改初始化脚本后重新运行

### 权限配置备份

```bash
# 备份权限配置
python -c "
from app import create_app
from app.models.permission_config import PermissionConfig
import json

app = create_app()
with app.app_context():
    perms = PermissionConfig.query.all()
    data = [perm.to_dict() for perm in perms]
    with open('permission_config_backup.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'已备份 {len(data)} 个权限配置')
"
```

## 故障排除

### 权限配置不匹配

如果发现权限配置与实际权限不匹配：

1. 检查SYS账户的实际权限
2. 对比权限配置表
3. 运行权限配置初始化脚本
4. 验证修复结果

### 分类规则不工作

如果分类规则不工作：

1. 检查规则表达式格式
2. 验证权限配置是否存在
3. 检查账户权限数据
4. 查看分类服务日志

## 版本历史

- **v1.0** - 初始版本，基础权限配置
- **v2.0** - 添加PostgreSQL和Oracle支持
- **v3.0** - 基于SYS账户实际权限优化Oracle配置
- **v4.0** - 修复权限配置错误，确保100%准确性
