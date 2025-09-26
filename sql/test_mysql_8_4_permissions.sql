-- =============================================
-- MySQL 8.4 权限测试脚本
-- 鲸落 - 数据同步管理平台
-- =============================================

-- 1. 测试基本连接
SELECT 'MySQL 8.4 权限测试开始' AS 状态;
SELECT @@VERSION AS MySQL版本;

-- 2. 测试SHOW DATABASES权限
SELECT 'SHOW DATABASES权限测试' AS 测试项目;
-- 请手动执行: SHOW DATABASES;

-- 3. 测试information_schema.SCHEMATA访问
SELECT 'information_schema.SCHEMATA访问测试' AS 测试项目;
SELECT COUNT(*) AS 数据库数量 FROM information_schema.SCHEMATA;
SELECT SCHEMA_NAME FROM information_schema.SCHEMATA ORDER BY SCHEMA_NAME;

-- 4. 测试information_schema.tables访问
SELECT 'information_schema.tables访问测试' AS 测试项目;
SELECT COUNT(*) AS 总表数量 FROM information_schema.tables;
SELECT COUNT(*) AS 用户表数量 FROM information_schema.tables WHERE table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys');

-- 5. 测试具体数据库的表信息
SELECT '具体数据库表信息测试' AS 测试项目;
SELECT 
    table_schema,
    COUNT(*) AS 表数量,
    SUM(data_length) AS 数据大小字节,
    SUM(index_length) AS 索引大小字节
FROM information_schema.tables 
WHERE table_schema NOT IN ('information_schema', 'performance_schema', 'mysql', 'sys')
GROUP BY table_schema
ORDER BY table_schema;

-- 6. 测试数据库大小查询（完整版本）
SELECT '数据库大小查询测试' AS 测试项目;
SELECT
    s.SCHEMA_NAME AS database_name,
    COALESCE(ROUND(SUM(COALESCE(t.data_length, 0) + COALESCE(t.index_length, 0)) / 1024 / 1024, 2), 0) AS size_mb,
    COALESCE(ROUND(SUM(COALESCE(t.data_length, 0)) / 1024 / 1024, 2), 0) AS data_size_mb,
    COALESCE(ROUND(SUM(COALESCE(t.index_length, 0)) / 1024 / 1024, 2), 0) AS index_size_mb
FROM
    information_schema.SCHEMATA s
LEFT JOIN
    information_schema.tables t ON s.SCHEMA_NAME = t.table_schema
GROUP BY
    s.SCHEMA_NAME
ORDER BY
    size_mb DESC;

-- 7. 测试特定数据库的详细信息
SELECT '特定数据库详细信息测试' AS 测试项目;
-- 请替换 'barcodemanage' 为实际的数据库名
SELECT 
    'barcodemanage' AS 数据库名,
    COUNT(*) AS 表数量,
    COALESCE(SUM(data_length), 0) AS 数据大小字节,
    COALESCE(SUM(index_length), 0) AS 索引大小字节,
    COALESCE(SUM(data_length + index_length), 0) AS 总大小字节
FROM information_schema.tables 
WHERE table_schema = 'barcodemanage';

-- 8. 测试权限详情
SELECT '当前用户权限详情' AS 测试项目;
SHOW GRANTS FOR CURRENT_USER();

-- 9. 测试结果总结
SELECT '权限测试完成' AS 状态;
SELECT '如果以上查询都能正常执行，说明权限设置正确' AS 说明;
