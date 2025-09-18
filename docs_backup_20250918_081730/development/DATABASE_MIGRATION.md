# 数据库迁移指南

## 概述

本项目使用Flask-Migrate管理数据库结构变更，确保开发过程中数据不丢失。每次修改模型后，都需要创建和应用迁移。

## 快速开始

### 1. 初始化开发环境

```bash
# 启动本地开发环境
./start_dev.sh
```

### 2. 开发新功能

```bash
# 开始新功能开发
./dev_workflow.sh start '功能名称'

# 修改模型文件后创建迁移
./dev_workflow.sh migrate '描述变更内容'

# 应用迁移
./dev_workflow.sh apply
```

## 详细命令

### 开发工作流命令

| 命令 | 描述 | 示例 |
|------|------|------|
| `start <name>` | 开始新功能开发 | `./dev_workflow.sh start '用户管理'` |
| `migrate <message>` | 创建数据库迁移 | `./dev_workflow.sh migrate '添加用户角色字段'` |
| `apply` | 应用数据库迁移 | `./dev_workflow.sh apply` |
| `rollback [steps]` | 回滚数据库迁移 | `./dev_workflow.sh rollback 1` |
| `backup [name]` | 备份数据库 | `./dev_workflow.sh backup '功能完成'` |
| `restore <file>` | 恢复数据库 | `./dev_workflow.sh restore userdata/backups/backup.db` |
| `status` | 显示开发状态 | `./dev_workflow.sh status` |

### 迁移管理命令

| 命令 | 描述 | 示例 |
|------|------|------|
| `./migrate.sh init` | 初始化迁移环境 | 首次使用 |
| `./migrate.sh create <message>` | 创建迁移 | `./migrate.sh create '添加表'` |
| `./migrate.sh upgrade [revision]` | 升级数据库 | `./migrate.sh upgrade` |
| `./migrate.sh downgrade <revision>` | 降级数据库 | `./migrate.sh downgrade -1` |
| `./migrate.sh current` | 显示当前版本 | `./migrate.sh current` |
| `./migrate.sh history` | 显示迁移历史 | `./migrate.sh history` |

## 开发流程

### 1. 开始新功能

```bash
# 创建功能分支
./dev_workflow.sh start '用户管理功能'

# 修改模型文件
# 编辑 app/models/user.py 等文件
```

### 2. 创建迁移

```bash
# 创建迁移文件
./dev_workflow.sh migrate '添加用户角色和权限字段'

# 检查生成的迁移文件
cat migrations/versions/xxxx_add_user_role.py
```

### 3. 应用迁移

```bash
# 应用迁移到数据库
./dev_workflow.sh apply

# 检查数据库状态
./dev_workflow.sh status
```

### 4. 测试和回滚

```bash
# 如果发现问题，回滚迁移
./dev_workflow.sh rollback 1

# 修复问题后重新应用
./dev_workflow.sh apply
```

### 5. 备份数据

```bash
# 功能完成后备份数据库
./dev_workflow.sh backup '用户管理功能完成'
```

## 最佳实践

### 1. 迁移文件命名

- 使用描述性的迁移消息
- 避免使用特殊字符
- 示例：
  - ✅ `添加用户角色字段`
  - ✅ `创建订单表`
  - ❌ `update`
  - ❌ `fix bug`

### 2. 模型修改

- 修改模型后立即创建迁移
- 不要累积多个模型变更
- 测试迁移的升级和降级

### 3. 数据安全

- 重要功能开发前备份数据库
- 定期创建备份
- 测试环境验证迁移

### 4. 团队协作

- 提交迁移文件到版本控制
- 团队成员拉取代码后运行 `./dev_workflow.sh apply`
- 不要手动修改迁移文件

## 常见问题

### Q: 迁移失败怎么办？

A: 使用回滚命令恢复：
```bash
./dev_workflow.sh rollback 1
```

### Q: 如何查看迁移历史？

A: 使用历史命令：
```bash
./migrate.sh history
```

### Q: 如何恢复数据库？

A: 使用恢复命令：
```bash
./dev_workflow.sh restore userdata/backups/backup_20240101_120000.db
```

### Q: 迁移文件在哪里？

A: 迁移文件在 `migrations/versions/` 目录下

## 文件结构

```
TaifishV4/
├── migrations/                 # 迁移文件目录
│   ├── versions/              # 迁移版本文件
│   ├── alembic.ini           # Alembic配置
│   └── env.py                # 迁移环境配置
├── dev_workflow.sh           # 开发工作流脚本
├── migrate.sh                # 迁移管理脚本
├── start_dev.sh              # 本地开发启动脚本
└── userdata/                 # 用户数据目录
    ├── taifish_dev.db        # SQLite数据库文件
    └── backups/              # 数据库备份目录
```

## 注意事项

1. **数据安全**：迁移会修改数据库结构，请确保重要数据已备份
2. **测试环境**：在生产环境应用迁移前，先在测试环境验证
3. **版本控制**：迁移文件必须提交到版本控制系统
4. **团队协作**：团队成员需要同步迁移文件并应用迁移

## 相关文档

- [Flask-Migrate官方文档](https://flask-migrate.readthedocs.io/)
- [Alembic文档](https://alembic.sqlalchemy.org/)
- [SQLAlchemy文档](https://docs.sqlalchemy.org/)
