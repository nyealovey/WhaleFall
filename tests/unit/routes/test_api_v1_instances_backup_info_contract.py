from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app import create_app, db
from app.models.credential import Credential
from app.models.instance import Instance
from app.models.user import User
from app.models.veeam_machine_backup_snapshot import VeeamMachineBackupSnapshot
from app.models.veeam_source_binding import VeeamSourceBinding


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
                last_sync_at=datetime(2026, 3, 25, 3, 0, tzinfo=UTC),
            )
        )
        db.session.add(
            VeeamMachineBackupSnapshot(
                machine_name="db01.domain.com",
                normalized_machine_name="db01.domain.com",
                latest_backup_at=datetime(2026, 3, 25, 2, 0, tzinfo=UTC),
                job_name="daily-job",
                restore_point_name="rp-2",
                source_record_id="rp-2",
                raw_payload={"id": "rp-2"},
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
        assert data.get("match_candidates") == ["db01", "db01.domain.com"]
