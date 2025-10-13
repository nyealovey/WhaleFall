-- 账户分类颜色统一整改 - 数据库迁移语句
-- 将现有的颜色值转换为颜色键名

-- 备份当前数据（可选）
-- CREATE TABLE account_classifications_backup AS SELECT * FROM account_classifications;

-- 更新现有分类的颜色值为标准颜色键名
UPDATE account_classifications 
SET color = CASE 
    -- 绿色系 -> primary/success
    WHEN color IN ('#18bc9c', '#1abc9c', '#16a085', '#17a2b8', '#20c997') THEN 'primary'
    
    -- 红色系 -> danger
    WHEN color IN ('#e74c3c', '#dc3545', '#c0392b', '#e55353', '#f56565') THEN 'danger'
    
    -- 橙色系 -> warning
    WHEN color IN ('#f39c12', '#fd7e14', '#e67e22', '#ff9500', '#f6ad55') THEN 'warning'
    
    -- 蓝色系 -> info
    WHEN color IN ('#3498db', '#007bff', '#2980b9', '#0ea5e9', '#3b82f6') THEN 'info'
    
    -- 灰色系 -> secondary
    WHEN color IN ('#95a5a6', '#6c757d', '#7f8c8d', '#9ca3af', '#64748b') THEN 'secondary'
    
    -- 深色系 -> dark
    WHEN color IN ('#2c3e50', '#343a40', '#1a202c', '#374151', '#1f2937') THEN 'dark'
    
    -- 浅色系 -> light
    WHEN color IN ('#ecf0f1', '#f8f9fa', '#e9ecef', '#f3f4f6', '#f1f5f9') THEN 'light'
    
    -- 紫色系 -> info (映射到蓝色)
    WHEN color LIKE '#%' AND (
        color IN ('#9b59b6', '#8e44ad', '#6f42c1', '#7c3aed', '#8b5cf6')
    ) THEN 'info'
    
    -- 其他颜色值 -> info (默认)
    WHEN color LIKE '#%' THEN 'info'
    
    -- 如果已经是键名，保持不变
    WHEN color IN ('primary', 'danger', 'warning', 'info', 'secondary', 'success', 'dark', 'light') THEN color
    
    -- 默认值
    ELSE 'info'
END
WHERE color IS NOT NULL;

-- 处理空值
UPDATE account_classifications 
SET color = 'info' 
WHERE color IS NULL OR color = '';

-- 验证更新结果
SELECT 
    color,
    COUNT(*) as count,
    GROUP_CONCAT(name SEPARATOR ', ') as classification_names
FROM account_classifications 
GROUP BY color
ORDER BY count DESC;

-- 显示更新统计
SELECT 
    '更新完成' as status,
    COUNT(*) as total_classifications,
    COUNT(DISTINCT color) as unique_colors
FROM account_classifications;