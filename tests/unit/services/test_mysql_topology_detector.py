from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import pytest

from app.core.types import JsonValue
from app.services.mysql_clusters.topology_detector import (
    READ_ONLY_QUERY,
    REPLICA_STATUS_QUERY,
    SLAVE_STATUS_QUERY,
    MySQLTopologyDetector,
)


class _FakeConnection:
    def __init__(self, responses: dict[str, Any]) -> None:
        self.responses = responses
        self.queries: list[str] = []
        self.disconnected = False

    def connect(self) -> bool:
        return True

    def execute_query(
        self,
        query: str,
        params: Sequence[JsonValue] | Mapping[str, JsonValue] | None = None,
    ) -> Iterable[Sequence[JsonValue]]:
        del params
        self.queries.append(query)
        response = self.responses.get(query)
        if isinstance(response, Exception):
            raise response
        return response or []

    def disconnect(self) -> None:
        self.disconnected = True


@pytest.mark.unit
def test_mysql_topology_detector_normalizes_show_replica_status() -> None:
    connection = _FakeConnection(
        {
            REPLICA_STATUS_QUERY: [
                {
                    "Source_Host": "10.0.0.1",
                    "Source_Port": "3306",
                    "Replica_IO_Running": "Yes",
                    "Replica_SQL_Running": "No",
                    "Seconds_Behind_Source": "7",
                    "Last_SQL_Error": "SQL thread stopped",
                }
            ],
            READ_ONLY_QUERY: [{"read_only": "ON", "super_read_only": "OFF"}],
        },
    )

    detected = MySQLTopologyDetector().detect(connection)

    assert detected.to_dict()["replication_role"] == "replica"
    assert detected.to_dict()["replication_status"] == "unhealthy"
    assert detected.to_dict()["source_host"] == "10.0.0.1"
    assert detected.to_dict()["source_port"] == 3306
    assert detected.to_dict()["seconds_behind_source"] == 7
    assert detected.to_dict()["last_error"] == "SQL thread stopped"
    assert detected.to_dict()["read_only"] is True
    assert connection.queries == [REPLICA_STATUS_QUERY, READ_ONLY_QUERY]


@pytest.mark.unit
def test_mysql_topology_detector_falls_back_to_show_slave_status_when_replica_status_is_unsupported() -> None:
    connection = _FakeConnection(
        {
            REPLICA_STATUS_QUERY: RuntimeError("syntax error near 'REPLICA STATUS'"),
            SLAVE_STATUS_QUERY: [
                {
                    "Master_Host": "10.0.0.1",
                    "Master_Port": 3306,
                    "Slave_IO_Running": "Yes",
                    "Slave_SQL_Running": "Yes",
                    "Seconds_Behind_Master": 0,
                }
            ],
            READ_ONLY_QUERY: [{"read_only": 1, "super_read_only": 0}],
        },
    )

    detected = MySQLTopologyDetector().detect(connection)

    assert detected.to_dict()["replication_role"] == "replica"
    assert detected.to_dict()["replication_status"] == "healthy"
    assert detected.to_dict()["seconds_behind_source"] == 0
    assert connection.queries == [REPLICA_STATUS_QUERY, SLAVE_STATUS_QUERY, READ_ONLY_QUERY]


@pytest.mark.unit
def test_mysql_topology_detector_detects_primary_when_no_replication_rows_and_not_read_only() -> None:
    connection = _FakeConnection(
        {
            REPLICA_STATUS_QUERY: [],
            READ_ONLY_QUERY: [(0, 0)],
        },
    )

    detected = MySQLTopologyDetector().detect(connection)

    assert detected.to_dict() == {
        "replication_role": "primary",
        "replication_status": "healthy",
        "read_only": False,
        "super_read_only": False,
    }
