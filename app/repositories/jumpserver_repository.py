"""JumpServer 数据源与资产快照 Repository."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import inspect

from app import db
from app.models.instance import Instance
from app.models.jumpserver_asset_snapshot import JumpServerAssetSnapshot
from app.models.jumpserver_source_binding import JumpServerSourceBinding


class JumpServerRepository:
    """JumpServer 绑定与快照访问."""

    @staticmethod
    def _has_asset_snapshot_table() -> bool:
        inspector = inspect(db.engine)
        return inspector.has_table(JumpServerAssetSnapshot.__tablename__)

    @staticmethod
    def get_binding() -> JumpServerSourceBinding | None:
        """获取当前全局绑定."""
        return JumpServerSourceBinding.query.order_by(JumpServerSourceBinding.id.asc()).first()

    @staticmethod
    def add_binding(binding: JumpServerSourceBinding) -> JumpServerSourceBinding:
        """新增或更新绑定."""
        db.session.add(binding)
        db.session.flush()
        return binding

    @staticmethod
    def delete_binding(binding: JumpServerSourceBinding) -> None:
        """删除绑定."""
        db.session.delete(binding)

    @staticmethod
    def clear_asset_snapshots() -> None:
        """清空全部快照."""
        if not JumpServerRepository._has_asset_snapshot_table():
            return
        JumpServerAssetSnapshot.query.delete()

    @staticmethod
    def replace_asset_snapshots(
        assets: Iterable["JumpServerDatabaseAsset"],
        *,
        sync_run_id: str,
        synced_at: datetime,
    ) -> None:
        """以本次同步结果替换快照内容."""
        from app.services.jumpserver.provider import JumpServerDatabaseAsset

        existing = {
            row.external_id: row
            for row in JumpServerAssetSnapshot.query.order_by(JumpServerAssetSnapshot.id.asc()).all()
        }
        keep_external_ids: set[str] = set()
        for asset in assets:
            if not isinstance(asset, JumpServerDatabaseAsset):
                continue
            keep_external_ids.add(asset.external_id)
            row = existing.get(asset.external_id)
            if row is None:
                row = JumpServerAssetSnapshot(external_id=asset.external_id, name=asset.name)
            row.name = asset.name
            row.db_type = asset.db_type
            row.host = asset.host
            row.port = asset.port
            row.raw_payload = asset.raw_payload
            row.sync_run_id = sync_run_id
            row.synced_at = synced_at
            db.session.add(row)

        for external_id, row in existing.items():
            if external_id not in keep_external_ids:
                db.session.delete(row)

        db.session.flush()

    @staticmethod
    def fetch_managed_instance_ids(instances: list[Instance]) -> set[int]:
        """按 db_type + host + port 匹配已托管实例."""
        if not instances or not JumpServerRepository._has_asset_snapshot_table():
            return set()

        hosts = sorted({str(instance.host).strip() for instance in instances if getattr(instance, "host", None)})
        ports = sorted({int(instance.port) for instance in instances if getattr(instance, "port", None) is not None})
        db_types = sorted(
            {str(instance.db_type).strip().lower() for instance in instances if getattr(instance, "db_type", None)}
        )
        if not hosts or not ports or not db_types:
            return set()

        snapshots = (
            JumpServerAssetSnapshot.query.filter(JumpServerAssetSnapshot.host.in_(hosts))
            .filter(JumpServerAssetSnapshot.port.in_(ports))
            .filter(JumpServerAssetSnapshot.db_type.in_(db_types))
            .all()
        )
        managed_keys = {
            (
                str(snapshot.db_type).strip().lower(),
                str(snapshot.host).strip(),
                int(snapshot.port),
            )
            for snapshot in snapshots
        }
        return {
            int(instance.id)
            for instance in instances
            if (
                str(instance.db_type).strip().lower(),
                str(instance.host).strip(),
                int(instance.port),
            )
            in managed_keys
        }
