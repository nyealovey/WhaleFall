# MySQL 数据库大小查询语句大全

## 1. 查询所有数据库大小

### 1.1 基础查询（推荐）
```sql
-- 查询所有数据库的大小，按大小降序排列
SELECT 
    table_schema AS '数据库',
    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS '大小(MB)',
    ROUND(SUM(data_length) / 1024 / 1024, 2) AS '数据大小(MB)',
    ROUND(SUM(index_length) / 1024 / 1024, 2) AS '索引大小(MB)',
    COUNT(*) AS '表数量'
FROM 
    information_schema.TABLES
GROUP BY 
    table_schema
ORDER BY 
    SUM(data_length + index_length) DESC;
```

### 1.2 带单位自动转换（GB/MB/KB）
```sql
-- 自动选择合适的单位显示
SELECT 
    table_schema AS '数据库',
    CONCAT(
        ROUND(
            SUM(data_length + index_length) / 
            POWER(1024, 
                CASE 
                    WHEN SUM(data_length + index_length) >= 1073741824 THEN 3  -- GB
                    WHEN SUM(data_length + index_length) >= 1048576 THEN 2     -- MB
                    ELSE 1                                                      -- KB
                END
            ), 2
        ),
        CASE 
            WHEN SUM(data_length + index_length) >= 1073741824 THEN ' GB'
            WHEN SUM(data_length + index_length) >= 1048576 THEN ' MB'
            ELSE ' KB'
        END
    ) AS '大小',
    COUNT(*) AS '表数量'
FROM 
    information_schema.TABLES
GROUP BY 
    table_schema
ORDER BY 
    SUM(data_length + index_length) DESC;
```

### 1.3 排除系统数据库
```sql
-- 只查询用户数据库，排除系统库
SELECT 
    table_schema AS '数据库',
    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS '大小(MB)',
    COUNT(*) AS '表数量'
FROM 
    information_schema.TABLES
WHERE 
    table_schema NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')
GROUP BY 
    table_schema
ORDER BY 
    SUM(data_length + index_length) DESC;
```

---

## 2. 查询指定数据库大小

### 2.1 单个数据库总大小
```sql
-- 查询指定数据库的总大小
SELECT 
    table_schema AS '数据库',
    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS '总大小(MB)',
    ROUND(SUM(data_length) / 1024 / 1024, 2) AS '数据大小(MB)',
    ROUND(SUM(index_length) / 1024 / 1024, 2) AS '索引大小(MB)',
    ROUND(SUM(data_free) / 1024 / 1024, 2) AS '碎片大小(MB)',
    COUNT(*) AS '表数量'
FROM 
    information_schema.TABLES
WHERE 
    table_schema = 'your_database_name'
GROUP BY 
    table_schema;
```

### 2.2 数据库详细信息
```sql
-- 查询数据库的详细统计信息
SELECT 
    'your_database_name' AS '数据库',
    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS '总大小(MB)',
    ROUND(SUM(data_length) / 1024 / 1024, 2) AS '数据(MB)',
    ROUND(SUM(index_length) / 1024 / 1024, 2) AS '索引(MB)',
    ROUND(SUM(data_free) / 1024 / 1024, 2) AS '碎片(MB)',
    COUNT(*) AS '表数量',
    SUM(table_rows) AS '总行数',
    ROUND(AVG(avg_row_length), 2) AS '平均行长度(字节)'
FROM 
    information_schema.TABLES
WHERE 
    table_schema = 'your_database_name';
```

---

## 3. 查询数据库中各表大小

### 3.1 基础表大小查询
```sql
-- 查询指定数据库中所有表的大小
SELECT 
    table_name AS '表名',
    table_rows AS '行数',
    ROUND(data_length / 1024 / 1024, 2) AS '数据大小(MB)',
    ROUND(index_length / 1024 / 1024, 2) AS '索引大小(MB)',
    ROUND((data_length + index_length) / 1024 / 1024, 2) AS '总大小(MB)',
    ROUND(data_free / 1024 / 1024, 2) AS '碎片(MB)',
    engine AS '引擎'
FROM 
    information_schema.TABLES
WHERE 
    table_schema = 'your_database_name'
ORDER BY 
    (data_length + index_length) DESC;
```

### 3.2 Top N 最大的表
```sql
-- 查询数据库中最大的10张表
SELECT 
    table_name AS '表名',
    ROUND((data_length + index_length) / 1024 / 1024, 2) AS '大小(MB)',
    table_rows AS '行数',
    ROUND(data_length / 1024 / 1024, 2) AS '数据(MB)',
    ROUND(index_length / 1024 / 1024, 2) AS '索引(MB)',
    engine AS '引擎',
    create_time AS '创建时间',
    update_time AS '更新时间'
FROM 
    information_schema.TABLES
WHERE 
    table_schema = 'your_database_name'
ORDER BY 
    (data_length + index_length) DESC
LIMIT 10;
```

### 3.3 表大小详细分析
```sql
-- 详细分析表的存储情况
SELECT 
    table_name AS '表名',
    engine AS '引擎',
    table_rows AS '行数',
    avg_row_length AS '平均行长度(字节)',
    ROUND((data_length + index_length) / 1024 / 1024, 2) AS '总大小(MB)',
    ROUND(data_length / 1024 / 1024, 2) AS '数据(MB)',
    ROUND(index_length / 1024 / 1024, 2) AS '索引(MB)',
    ROUND(data_free / 1024 / 1024, 2) AS '碎片(MB)',
    ROUND(index_length / data_length * 100, 2) AS '索引率(%)',
    ROUND(data_free / (data_length + index_length + data_free) * 100, 2) AS '碎片率(%)',
    create_time AS '创建时间',
    update_time AS '更新时间'
FROM 
    information_schema.TABLES
WHERE 
    table_schema = 'your_database_name'
    AND table_type = 'BASE TABLE'
ORDER BY 
    (data_length + index_length) DESC;
```

---

## 4. 按表类型分组统计

### 4.1 按存储引擎统计
```sql
-- 按存储引擎分组统计
SELECT 
    engine AS '存储引擎',
    COUNT(*) AS '表数量',
    SUM(table_rows) AS '总行数',
    ROUND(SUM(data_length) / 1024 / 1024, 2) AS '数据大小(MB)',
    ROUND(SUM(index_length) / 1024 / 1024, 2) AS '索引大小(MB)',
    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS '总大小(MB)'
FROM 
    information_schema.TABLES
WHERE 
    table_schema = 'your_database_name'
GROUP BY 
    engine
ORDER BY 
    SUM(data_length + index_length) DESC;
```

### 4.2 按表名前缀统计
```sql
-- 按表名前缀分组统计（适用于有命名规范的项目）
SELECT 
    SUBSTRING_INDEX(table_name, '_', 1) AS '表前缀',
    COUNT(*) AS '表数量',
    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS '总大小(MB)',
    SUM(table_rows) AS '总行数'
FROM 
    information_schema.TABLES
WHERE 
    table_schema = 'your_database_name'
GROUP BY 
    SUBSTRING_INDEX(table_name, '_', 1)
ORDER BY 
    SUM(data_length + index_length) DESC;
```

---

## 5. 碎片分析

### 5.1 查找碎片较多的表
```sql
-- 查找碎片超过100MB的表
SELECT 
    table_schema AS '数据库',
    table_name AS '表名',
    ROUND(data_free / 1024 / 1024, 2) AS '碎片大小(MB)',
    ROUND((data_length + index_length) / 1024 / 1024, 2) AS '表大小(MB)',
    ROUND(data_free / (data_length + index_length + data_free) * 100, 2) AS '碎片率(%)',
    engine AS '引擎'
FROM 
    information_schema.TABLES
WHERE 
    table_schema = 'your_database_name'
    AND data_free > 104857600  -- 100MB
ORDER BY 
    data_free DESC;
```

### 5.2 碎片率分析
```sql
-- 分析碎片率超过10%的表
SELECT 
    table_name AS '表名',
    ROUND((data_length + index_length) / 1024 / 1024, 2) AS '表大小(MB)',
    ROUND(data_free / 1024 / 1024, 2) AS '碎片(MB)',
    ROUND(data_free / (data_length + index_length + data_free) * 100, 2) AS '碎片率(%)',
    CONCAT('OPTIMIZE TABLE `', table_schema, '`.`', table_name, '`;') AS '优化语句'
FROM 
    information_schema.TABLES
WHERE 
    table_schema = 'your_database_name'
    AND data_free > 0
    AND (data_free / (data_length + index_length + data_free)) > 0.1
ORDER BY 
    data_free DESC;
```

---

## 6. 增长趋势分析

### 6.1 最近更新的表
```sql
-- 查询最近更新的表（可能增长较快）
SELECT 
    table_name AS '表名',
    ROUND((data_length + index_length) / 1024 / 1024, 2) AS '大小(MB)',
    table_rows AS '行数',
    update_time AS '最后更新时间',
    TIMESTAMPDIFF(DAY, update_time, NOW()) AS '距今天数'
FROM 
    information_schema.TABLES
WHERE 
    table_schema = 'your_database_name'
    AND update_time IS NOT NULL
ORDER BY 
    update_time DESC
LIMIT 20;
```

### 6.2 按创建时间分组
```sql
-- 按表创建时间分组统计
SELECT 
    DATE_FORMAT(create_time, '%Y-%m') AS '创建月份',
    COUNT(*) AS '表数量',
    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS '总大小(MB)'
FROM 
    information_schema.TABLES
WHERE 
    table_schema = 'your_database_name'
    AND create_time IS NOT NULL
GROUP BY 
    DATE_FORMAT(create_time, '%Y-%m')
ORDER BY 
    create_time DESC;
```

---

## 7. 实用组合查询

### 7.1 数据库健康检查
```sql
-- 综合健康检查报告
SELECT 
    '数据库总大小' AS '指标',
    CONCAT(ROUND(SUM(data_length + index_length) / 1024 / 1024 / 1024, 2), ' GB') AS '值'
FROM information_schema.TABLES WHERE table_schema = 'your_database_name'
UNION ALL
SELECT 
    '表数量',
    COUNT(*)
FROM information_schema.TABLES WHERE table_schema = 'your_database_name'
UNION ALL
SELECT 
    '总行数',
    FORMAT(SUM(table_rows), 0)
FROM information_schema.TABLES WHERE table_schema = 'your_database_name'
UNION ALL
SELECT 
    '碎片总大小',
    CONCAT(ROUND(SUM(data_free) / 1024 / 1024, 2), ' MB')
FROM information_schema.TABLES WHERE table_schema = 'your_database_name'
UNION ALL
SELECT 
    '最大的表',
    table_name
FROM information_schema.TABLES 
WHERE table_schema = 'your_database_name'
ORDER BY (data_length + index_length) DESC LIMIT 1;
```

### 7.2 快速诊断脚本
```sql
-- 一键诊断数据库存储情况
SELECT 
    'TOP 5 最大的表' AS '类别',
    table_name AS '名称',
    CONCAT(ROUND((data_length + index_length) / 1024 / 1024, 2), ' MB') AS '大小'
FROM information_schema.TABLES
WHERE table_schema = 'your_database_name'
ORDER BY (data_length + index_length) DESC
LIMIT 5

UNION ALL

SELECT 
    'TOP 5 碎片最多的表',
    table_name,
    CONCAT(ROUND(data_free / 1024 / 1024, 2), ' MB')
FROM information_schema.TABLES
WHERE table_schema = 'your_database_name' AND data_free > 0
ORDER BY data_free DESC
LIMIT 5

UNION ALL

SELECT 
    'TOP 5 行数最多的表',
    table_name,
    FORMAT(table_rows, 0)
FROM information_schema.TABLES
WHERE table_schema = 'your_database_name'
ORDER BY table_rows DESC
LIMIT 5;
```

---

## 8. 导出友好格式

### 8.1 CSV导出格式
```sql
-- 适合导出到CSV的格式
SELECT 
    table_schema AS 'Database',
    table_name AS 'Table',
    engine AS 'Engine',
    table_rows AS 'Rows',
    ROUND(data_length / 1024 / 1024, 2) AS 'Data_MB',
    ROUND(index_length / 1024 / 1024, 2) AS 'Index_MB',
    ROUND((data_length + index_length) / 1024 / 1024, 2) AS 'Total_MB',
    ROUND(data_free / 1024 / 1024, 2) AS 'Free_MB',
    create_time AS 'Created',
    update_time AS 'Updated'
FROM 
    information_schema.TABLES
WHERE 
    table_schema = 'your_database_name'
ORDER BY 
    (data_length + index_length) DESC;
```

### 8.2 JSON格式（MySQL 5.7+）
```sql
-- 生成JSON格式的统计信息
SELECT JSON_OBJECT(
    'database', table_schema,
    'total_size_mb', ROUND(SUM(data_length + index_length) / 1024 / 1024, 2),
    'data_size_mb', ROUND(SUM(data_length) / 1024 / 1024, 2),
    'index_size_mb', ROUND(SUM(index_length) / 1024 / 1024, 2),
    'table_count', COUNT(*),
    'total_rows', SUM(table_rows)
) AS database_stats
FROM information_schema.TABLES
WHERE table_schema = 'your_database_name';
```

---

## 9. 常用快捷命令

### 9.1 命令行快速查询
```bash
# 使用mysql命令行快速查询所有数据库大小
mysql -u root -p -e "
SELECT 
    table_schema AS 'Database',
    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size_MB'
FROM information_schema.TABLES
GROUP BY table_schema
ORDER BY SUM(data_length + index_length) DESC;
"

# 查询指定数据库
mysql -u root -p -e "
SELECT 
    table_name AS 'Table',
    ROUND((data_length + index_length) / 1024 / 1024, 2) AS 'Size_MB'
FROM information_schema.TABLES
WHERE table_schema = 'your_database_name'
ORDER BY (data_length + index_length) DESC;
"
```

### 9.2 保存为存储过程
```sql
-- 创建存储过程方便重复使用
DELIMITER //

CREATE PROCEDURE sp_database_size_report(IN db_name VARCHAR(64))
BEGIN
    SELECT 
        table_name AS '表名',
        ROUND((data_length + index_length) / 1024 / 1024, 2) AS '大小(MB)',
        table_rows AS '行数',
        engine AS '引擎'
    FROM 
        information_schema.TABLES
    WHERE 
        table_schema = db_name
    ORDER BY 
        (data_length + index_length) DESC;
END //

DELIMITER ;

-- 使用方法
CALL sp_database_size_report('your_database_name');
```

---

## 10. 注意事项

### 10.1 权限要求
```sql
-- 需要以下权限才能查询 information_schema
GRANT SELECT ON information_schema.* TO 'your_user'@'localhost';
```

### 10.2 性能考虑
- `information_schema.TABLES` 查询可能较慢，特别是数据库很多时
- 对于大型数据库，建议在业务低峰期执行
- `table_rows` 是估算值（InnoDB），不是精确值

### 10.3 精确行数查询
```sql
-- 如需精确行数（慢，慎用）
SELECT COUNT(*) FROM your_database.your_table;
```

### 10.4 数据库大小 vs 磁盘占用
```sql
-- 查看实际磁盘占用（需要文件系统权限）
-- Linux: du -sh /var/lib/mysql/your_database_name/
-- 或使用系统表
SELECT 
    table_schema,
    SUM(data_length + index_length) / 1024 / 1024 AS 'Size_MB'
FROM information_schema.TABLES
GROUP BY table_schema;
```

---

## 11. 实战示例

### 示例1: 找出需要优化的表
```sql
-- 找出大于1GB且碎片率超过20%的表
SELECT 
    table_name AS '表名',
    ROUND((data_length + index_length) / 1024 / 1024 / 1024, 2) AS '大小(GB)',
    ROUND(data_free / 1024 / 1024, 2) AS '碎片(MB)',
    ROUND(data_free / (data_length + index_length + data_free) * 100, 2) AS '碎片率(%)',
    CONCAT('OPTIMIZE TABLE `', table_name, '`;') AS '优化命令'
FROM 
    information_schema.TABLES
WHERE 
    table_schema = 'your_database_name'
    AND (data_length + index_length) > 1073741824  -- 1GB
    AND data_free / (data_length + index_length + data_free) > 0.2
ORDER BY 
    data_free DESC;
```

### 示例2: 监控数据库增长
```sql
-- 创建监控表
CREATE TABLE db_size_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    database_name VARCHAR(64),
    size_mb DECIMAL(15,2),
    table_count INT,
    total_rows BIGINT,
    check_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 插入当前数据
INSERT INTO db_size_history (database_name, size_mb, table_count, total_rows)
SELECT 
    table_schema,
    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2),
    COUNT(*),
    SUM(table_rows)
FROM 
    information_schema.TABLES
WHERE 
    table_schema = 'your_database_name'
GROUP BY 
    table_schema;

-- 查看增长趋势
SELECT * FROM db_size_history ORDER BY check_time DESC LIMIT 10;
```

---

**使用提示**:
1. 将 `your_database_name` 替换为实际数据库名
2. 根据需要调整单位（MB/GB）和排序方式
3. 大型数据库建议在低峰期执行
4. 定期监控可以及时发现异常增长
