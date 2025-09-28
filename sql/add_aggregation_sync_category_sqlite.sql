-- 添加聚合同步分类支持 (SQLite版本)
-- 为同步会话管理添加 aggregation 分类

-- 注意：SQLite不支持直接修改CHECK约束，需要重建表
-- 这里只是添加注释，实际约束会在应用层面处理

-- 添加注释（SQLite支持有限，这里只是文档说明）
-- sync_sessions.sync_category: 同步分类: account(账户), capacity(容量), config(配置), aggregation(聚合), other(其他)
-- sync_instance_records.sync_category: 同步分类: account(账户), capacity(容量), config(配置), aggregation(聚合), other(其他)

-- 由于SQLite的限制，约束检查将在应用层面进行
-- 数据库约束将在下次重建表时更新
