"""调整 permission_configs: 移除表空间相关配置.

Revision ID: 20251230211000
Revises: 20251230190000
Create Date: 2025-12-30

变更:
- Oracle: 表空间相关权限归并到 system_privileges, 移除 tablespace_quotas.
- PostgreSQL: 移除 tablespace_privileges.
"""

from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "20251230211000"
down_revision = "20251230190000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL: 不再提供 tablespace_privileges 配置.
    op.execute(
        """
        DELETE FROM permission_configs
        WHERE db_type = 'postgresql'
          AND category = 'tablespace_privileges';
        """,
    )

    # Oracle: tablespace_privileges 归并到 system_privileges(避免 uq 冲突).
    op.execute(
        """
        UPDATE permission_configs
           SET category = 'system_privileges'
         WHERE db_type = 'oracle'
           AND category = 'tablespace_privileges'
           AND permission_name NOT IN (
               SELECT permission_name
                 FROM permission_configs
                WHERE db_type = 'oracle'
                  AND category = 'system_privileges'
           );
        """,
    )
    op.execute(
        """
        DELETE FROM permission_configs
        WHERE db_type = 'oracle'
          AND category = 'tablespace_privileges';
        """,
    )

    # Oracle: 不再采集/展示 tablespace_quotas, 因此移除配置项.
    op.execute(
        """
        DELETE FROM permission_configs
        WHERE db_type = 'oracle'
          AND category = 'tablespace_quotas';
        """,
    )


def downgrade() -> None:
    # PostgreSQL: 恢复 tablespace_privileges 配置项.
    op.execute(
        """
        INSERT INTO permission_configs
            (db_type, category, permission_name, description, is_active, sort_order, created_at, updated_at)
        VALUES
            ('postgresql', 'tablespace_privileges', 'CREATE', '在表空间中创建对象权限', TRUE, 1, NOW(), NOW()),
            ('postgresql', 'tablespace_privileges', 'USAGE', '使用表空间权限', TRUE, 2, NOW(), NOW())
        ON CONFLICT (db_type, category, permission_name) DO NOTHING;
        """,
    )

    # Oracle: 恢复 tablespace_quotas 配置项.
    op.execute(
        """
        INSERT INTO permission_configs
            (db_type, category, permission_name, description, is_active, sort_order, created_at, updated_at)
        VALUES
            ('oracle', 'tablespace_quotas', 'DEFAULT', '默认配额', TRUE, 1, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'NO QUOTA', '无配额', TRUE, 2, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'QUOTA', '配额', TRUE, 3, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'QUOTA 100E', '100E配额', TRUE, 4, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'QUOTA 100G', '100G配额', TRUE, 5, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'QUOTA 100K', '100K配额', TRUE, 6, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'QUOTA 100M', '100M配额', TRUE, 7, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'QUOTA 100P', '100P配额', TRUE, 8, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'QUOTA 100T', '100T配额', TRUE, 9, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'QUOTA 10E', '10E配额', TRUE, 10, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'QUOTA 10G', '10G配额', TRUE, 11, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'QUOTA 10K', '10K配额', TRUE, 12, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'QUOTA 10M', '10M配额', TRUE, 13, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'QUOTA 10P', '10P配额', TRUE, 14, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'QUOTA 10T', '10T配额', TRUE, 15, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'QUOTA 1E', '1E配额', TRUE, 16, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'QUOTA 1G', '1G配额', TRUE, 17, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'QUOTA 1K', '1K配额', TRUE, 18, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'QUOTA 1M', '1M配额', TRUE, 19, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'QUOTA 1P', '1P配额', TRUE, 20, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'QUOTA 1T', '1T配额', TRUE, 21, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'QUOTA UNLIMITED', '无限制配额', TRUE, 22, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'QUOTA 0', '0配额', TRUE, 23, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'QUOTA 5G', '5G配额', TRUE, 24, NOW(), NOW()),
            ('oracle', 'tablespace_quotas', 'QUOTA 50G', '50G配额', TRUE, 25, NOW(), NOW())
        ON CONFLICT (db_type, category, permission_name) DO NOTHING;
        """,
    )

    # Oracle: 将归并到 system_privileges 的 tablespace 权限拆回 tablespace_privileges.
    op.execute(
        """
        UPDATE permission_configs
           SET category = 'tablespace_privileges'
         WHERE db_type = 'oracle'
           AND category = 'system_privileges'
           AND permission_name IN (
               'ALTER ANY TABLESPACE',
               'CREATE ANY TABLESPACE',
               'DEBUG ANY TABLESPACE',
               'DEBUG TABLESPACE',
               'DROP ANY TABLESPACE',
               'MANAGE ANY TABLESPACE',
               'READ ANY TABLESPACE',
               'READ TABLESPACE',
               'SELECT ANY TABLESPACE',
               'SELECT TABLESPACE',
               'UPDATE ANY TABLESPACE',
               'UPDATE TABLESPACE',
               'WRITE ANY TABLESPACE',
               'WRITE TABLESPACE'
           );
        """,
    )

    # Oracle: 恢复与 system_privileges 重叠的 tablespace_privileges 选项(仅配置分组用途).
    op.execute(
        """
        INSERT INTO permission_configs
            (db_type, category, permission_name, description, is_active, sort_order, created_at, updated_at)
        VALUES
            ('oracle', 'tablespace_privileges', 'ALTER TABLESPACE', '修改表空间权限', TRUE, 2, NOW(), NOW()),
            ('oracle', 'tablespace_privileges', 'CREATE TABLESPACE', '创建表空间权限', TRUE, 4, NOW(), NOW()),
            ('oracle', 'tablespace_privileges', 'DROP TABLESPACE', '删除表空间权限', TRUE, 8, NOW(), NOW()),
            ('oracle', 'tablespace_privileges', 'MANAGE TABLESPACE', '管理表空间权限', TRUE, 10, NOW(), NOW()),
            ('oracle', 'tablespace_privileges', 'ON COMMIT REFRESH', '提交时刷新权限', TRUE, 11, NOW(), NOW()),
            ('oracle', 'tablespace_privileges', 'QUERY REWRITE', '查询重写权限', TRUE, 12, NOW(), NOW()),
            ('oracle', 'tablespace_privileges', 'UNLIMITED TABLESPACE', '无限制表空间权限', TRUE, 17, NOW(), NOW())
        ON CONFLICT (db_type, category, permission_name) DO NOTHING;
        """,
    )

