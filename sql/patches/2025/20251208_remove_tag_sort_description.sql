-- 标签管理清理脚本：移除排序与描述字段
-- 注意：执行前请先备份 tags 表数据

BEGIN;

-- 移除无用字段
ALTER TABLE tags
    DROP COLUMN IF EXISTS description,
    DROP COLUMN IF EXISTS sort_order;

COMMIT;

-- 回滚参考（如需恢复字段可按需执行）
-- ALTER TABLE tags ADD COLUMN description TEXT NULL;
-- ALTER TABLE tags ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0;
-- UPDATE tags SET sort_order = 0 WHERE sort_order IS NULL;
-- ALTER TABLE tags ALTER COLUMN sort_order DROP DEFAULT;
