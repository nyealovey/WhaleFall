-- 账户分类颜色统一整改 - 简化版数据库迁移语句
-- 将现有的颜色值转换为颜色键名

-- 第一步：备份当前数据（推荐）
-- CREATE TABLE account_classifications_backup AS SELECT * FROM account_classifications;

-- 第二步：查看当前颜色分布
SELECT color, COUNT(*) as count FROM account_classifications GROUP BY color;

-- 第三步：更新颜色值为键名
-- 绿色系 -> primary
UPDATE account_classifications SET color = 'primary' 
WHERE color IN ('#18bc9c', '#1abc9c', '#16a085', '#17a2b8', '#20c997');

-- 红色系 -> danger  
UPDATE account_classifications SET color = 'danger'
WHERE color IN ('#e74c3c', '#dc3545', '#c0392b', '#e55353', '#f56565');

-- 橙色系 -> warning
UPDATE account_classifications SET color = 'warning'
WHERE color IN ('#f39c12', '#fd7e14', '#e67e22', '#ff9500', '#f6ad55');

-- 蓝色系 -> info
UPDATE account_classifications SET color = 'info'
WHERE color IN ('#3498db', '#007bff', '#2980b9', '#0ea5e9', '#3b82f6');

-- 灰色系 -> secondary
UPDATE account_classifications SET color = 'secondary'
WHERE color IN ('#95a5a6', '#6c757d', '#7f8c8d', '#9ca3af', '#64748b');

-- 深色系 -> dark
UPDATE account_classifications SET color = 'dark'
WHERE color IN ('#2c3e50', '#343a40', '#1a202c', '#374151', '#1f2937');

-- 浅色系 -> light
UPDATE account_classifications SET color = 'light'
WHERE color IN ('#ecf0f1', '#f8f9fa', '#e9ecef', '#f3f4f6', '#f1f5f9');

-- 紫色系 -> info (映射到蓝色)
UPDATE account_classifications SET color = 'info'
WHERE color IN ('#9b59b6', '#8e44ad', '#6f42c1', '#7c3aed', '#8b5cf6');

-- 其他十六进制颜色 -> info (默认)
UPDATE account_classifications SET color = 'info'
WHERE color LIKE '#%' AND color NOT IN ('primary', 'danger', 'warning', 'info', 'secondary', 'success', 'dark', 'light');

-- 处理空值和无效值
UPDATE account_classifications SET color = 'info' 
WHERE color IS NULL OR color = '' OR color NOT IN ('primary', 'danger', 'warning', 'info', 'secondary', 'success', 'dark', 'light');

-- 第四步：验证更新结果
SELECT color, COUNT(*) as count FROM account_classifications GROUP BY color ORDER BY count DESC;

-- 第五步：显示所有分类
SELECT id, name, color, description FROM account_classifications ORDER BY color, name;

-- 第六步：最终统计
SELECT 
    COUNT(*) as total_classifications,
    COUNT(DISTINCT color) as unique_colors
FROM account_classifications;