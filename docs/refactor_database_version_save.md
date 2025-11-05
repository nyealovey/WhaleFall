# 数据库版本信息统一保存方案

## 背景与目标
- 在“连接测试”操作中，前端可以拿到数据库版本字符串，但历史实现只更新了 `last_connected` 字段，`database_version`、`main_version`、`detailed_version` 始终为空。
- 目标是 **统一在连接测试流程中保存数据库版本信息**，无论是单个实例测试、批量测试还是 API 调用，都能写入上述三个字段。

## 核心问题
1. `ConnectionTestService.test_connection()` 仅返回版本字符串，没有解析和持久化。
2. `Instance.test_connection()` 虽然具备持久化逻辑，但从未被服务层调用。
3. 路由层 `_test_existing_instance()` 也只是简单地把结果返回给前端。

## 改造方案
### 设计原则
- **单一入口**：所有连接测试仍通过 `ConnectionTestService.test_connection()` 调用。
- **集中保存**：服务层负责解析版本并保存，调用方无需关心持久化细节。
- **兼容现有调用**：返回结构保持原有字段，并附带解析后的版本信息，避免影响前端。

### 新的处理流程
```
连接测试入口（路由 / 批量任务等）
  → ConnectionTestService.test_connection(instance)
      → 建立连接并拉取版本字符串
      → DatabaseVersionParser 解析版本
      → 更新 instance.last_connected 以及版本字段
      → db.session.commit()
      → 返回 { success, message, version, database_version,
               main_version, detailed_version }
```

### 关键代码要点
- 解析逻辑使用 `DatabaseVersionParser.parse_version(instance.db_type, version_info)`。
- 成功时写入：
  - `instance.database_version = parsed["original"]`
  - `instance.main_version = parsed["main_version"]`
  - `instance.detailed_version = parsed["detailed_version"]`
- 失败时不覆盖已有版本信息，只返回错误消息。

## 数据字段说明
| 字段 | 含义 | 示例 |
| ---- | ---- | ---- |
| `database_version` | 原始版本字符串 | `PostgreSQL 15.3 (Ubuntu 15.3-1.pgdg22.04+1)` |
| `main_version` | 主版本号 | `15.3` |
| `detailed_version` | 详细版本号，缺省时与主版本相同 | `15.3.0` |

## 实施步骤建议
1. **更新服务层**  
   修改 `ConnectionTestService.test_connection()`，在成功分支中解析版本并 `commit`。
2. **整理日志输出（可选）**  
   统一在成功日志中追加版本字段，便于排查。
3. **清理无用方法（可选）**  
   `Instance.test_connection()` 如无引用，可标记废弃或移除。

## 测试验证
- **单元测试**：模拟成功连接，断言实例对象的三个版本字段被赋值。
- **集成测试**：依次对 MySQL / PostgreSQL / SQL Server / Oracle 做连接测试，确认数据库中字段被更新。
- **回归测试**：验证连接失败场景不会将历史版本清空，前端提示保持不变。

## 运营支持
- 若需要回填历史数据，可写脚本遍历实例并调用新的 `test_connection()`。
- 配合监控/日志，若发现版本解析失败，检查原始字符串是否符合预期格式。

## 回滚策略
- 代码层面使用 `git revert` 即可。
- 如需清空错误写入的版本，可执行：
  ```sql
  UPDATE instances
     SET database_version = NULL,
         main_version = NULL,
         detailed_version = NULL
   WHERE updated_at >= '<错误发布时间>';
  ```

## 完成检查清单
- [ ] 所有数据库类型连接测试后均写入版本字段
- [ ] 批量测试也能写入版本信息
- [ ] 连接失败不会抹掉旧数据
- [ ] 相关单元测试/集成测试通过
- [ ] 文档和变更记录已更新
