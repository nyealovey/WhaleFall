"""实例级配置快照 Repository."""

from __future__ import annotations

from app import db
from app.models.instance_config_snapshot import InstanceConfigSnapshot


class InstanceConfigSnapshotsRepository:
    """实例级配置快照读写仓库."""

    @staticmethod
    def get_by_instance_and_key(*, instance_id: int, config_key: str) -> InstanceConfigSnapshot | None:
        return (
            InstanceConfigSnapshot.query.filter_by(
                instance_id=instance_id,
                config_key=config_key,
            )
            .order_by(InstanceConfigSnapshot.id.desc())
            .first()
        )

    @staticmethod
    def add(snapshot: InstanceConfigSnapshot) -> InstanceConfigSnapshot:
        db.session.add(snapshot)
        db.session.flush()
        return snapshot

    @staticmethod
    def flush() -> None:
        db.session.flush()
