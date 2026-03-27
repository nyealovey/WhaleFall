from __future__ import annotations

import pytest

from app import create_app, db
from app.models.credential import Credential
from app.models.instance import Instance
from app.models.user import User
from app.models.veeam_machine_backup_snapshot import VeeamMachineBackupSnapshot
from app.models.veeam_source_binding import VeeamSourceBinding
from app.utils.time_utils import time_utils


@pytest.mark.unit
def test_api_v1_instance_backup_info_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["instances"],
                db.metadata.tables["credentials"],
                db.metadata.tables["veeam_source_bindings"],
                db.metadata.tables["veeam_machine_backup_snapshots"],
            ],
        )

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)

        instance = Instance(
            name="db01",
            db_type="mysql",
            host="127.0.0.1",
            port=3306,
            is_active=True,
        )
        credential = Credential(
            name="veeam-admin",
            credential_type="veeam",
            username="backup-admin",
            password="VeeamPass123",
            is_active=True,
        )
        db.session.add_all([instance, credential])
        db.session.flush()
        db.session.add(
            VeeamSourceBinding(
                credential_id=credential.id,
                server_host="10.0.0.10",
                server_port=9419,
                api_version="1.3-rev1",
                verify_ssl=True,
                match_domains=["domain.com"],
                last_sync_at=time_utils.now(),
            )
        )
        db.session.add(
            VeeamMachineBackupSnapshot(
                machine_name="db01.domain.com",
                normalized_machine_name="db01.domain.com",
                latest_backup_at=time_utils.now(),
                backup_id="backup-1",
                backup_file_id="file-2",
                job_name="daily-job",
                restore_point_name="rp-2",
                source_record_id="rp-2",
                restore_point_size_bytes=1024,
                backup_chain_size_bytes=None,
                restore_point_count=2,
                raw_payload={
                    "id": "rp-2",
                    "restore_point_times": [
                        "2026-03-25T02:00:00+00:00",
                        "2026-03-25T01:30:00+00:00",
                    ],
                    "restore_points": [
                        {
                            "id": "restore-point-2",
                            "name": "db01-full-20260325T020000.vib",
                            "backupId": "backup-1",
                            "objectId": "object-1",
                            "restorePointIds": ["rp-2"],
                            "dataSize": 425819216,
                            "backupSize": 117592064,
                            "compressRatio": 27,
                            "creationTime": "2026-03-25T02:00:00+00:00",
                        },
                        {
                            "id": "restore-point-1",
                            "name": "db01-full-20260325T013000.vib",
                            "backupId": "backup-1",
                            "objectId": "object-1",
                            "restorePointIds": ["rp-1b"],
                            "dataSize": 225819216,
                            "backupSize": 17592064,
                            "compressRatio": 31,
                            "creationTime": "2026-03-25T01:30:00+00:00",
                        },
                    ],
                },
            )
        )
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        response = client.get(f"/api/v1/instances/{instance.id}/backup-info")
        assert response.status_code == 200
        payload = response.get_json()
        assert isinstance(payload, dict)
        data = payload.get("data")
        assert isinstance(data, dict)
        assert data.get("instance_id") == instance.id
        assert data.get("backup_status") == "backed_up"
        assert data.get("matched_machine_name") == "db01.domain.com"
        assert data.get("job_name") == "daily-job"
        assert data.get("restore_point_name") == "rp-2"
        assert data.get("restore_point_size_bytes") == 1024
        assert data.get("backup_chain_size_bytes") == 135184128
        assert data.get("restore_point_count") == 2
        assert data.get("backup_metrics_coverage") == {
            "expected_restore_point_count": 2,
            "enriched_restore_point_count": 2,
            "missing_restore_point_count": 0,
            "partial": False,
        }
        assert data.get("restore_point_times") == [
            "2026-03-25T02:00:00+00:00",
            "2026-03-25T01:30:00+00:00",
        ]
        assert data.get("restore_points") == [
            {
                "id": "restore-point-2",
                "name": "db01-full-20260325T020000.vib",
                "backup_id": "backup-1",
                "object_id": "object-1",
                "restore_point_ids": ["rp-2"],
                "data_size_bytes": 425819216,
                "backup_size_bytes": 117592064,
                "compress_ratio": 27,
                "creation_time": "2026-03-25T02:00:00+00:00",
            },
            {
                "id": "restore-point-1",
                "name": "db01-full-20260325T013000.vib",
                "backup_id": "backup-1",
                "object_id": "object-1",
                "restore_point_ids": ["rp-1b"],
                "data_size_bytes": 225819216,
                "backup_size_bytes": 17592064,
                "compress_ratio": 31,
                "creation_time": "2026-03-25T01:30:00+00:00",
            },
        ]
        assert data.get("match_candidates") == ["db01", "db01.domain.com"]
