"""Veeam restore point 标准化契约测试."""

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]


def test_veeam_repository_restore_point_normalization_only_keeps_confirmed_keys() -> None:
    source = (ROOT_DIR / "app/repositories/veeam_repository.py").read_text(encoding="utf-8")
    normalize_start = source.index("def _normalize_restore_points")
    serialize_start = source.index("def _serialize_snapshot_row")
    normalize_source = source[normalize_start:serialize_start]

    assert '"dataSize", "data_size", "dataSizeBytes", "data_size_bytes"' in normalize_source
    assert '"backupSize", "backup_size", "backupSizeBytes", "backup_size_bytes"' in normalize_source
    assert '"compressRatio", "compress_ratio"' in normalize_source

    removed_aliases = (
        "restorePointSizeBytes",
        "storageSizeBytes",
        "usedSizeBytes",
        "transferredSizeBytes",
        "backupFileSizeBytes",
        "compressionRatio",
    )
    for fragment in removed_aliases:
        assert fragment not in normalize_source
