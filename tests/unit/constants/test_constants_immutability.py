"""验证常量集合的不可变性."""

from app.constants.http_methods import HttpMethod
from app.constants.status_types import InstanceStatus, JobStatus, SyncSessionStatus, SyncStatus, TaskStatus
from app.constants.user_roles import UserRole


def test_http_method_collections_are_tuples() -> None:
    """确保 HTTP 方法集合不可变."""
    assert isinstance(HttpMethod.ALL, tuple)
    assert isinstance(HttpMethod.SAFE_METHODS, tuple)
    assert HttpMethod.GET in HttpMethod.ALL


def test_status_collections_are_tuples() -> None:
    """确保状态常量集合使用 tuple."""
    assert isinstance(SyncStatus.ALL, tuple)
    assert isinstance(SyncStatus.TERMINAL, tuple)
    assert isinstance(SyncSessionStatus.ALL, tuple)
    assert isinstance(SyncSessionStatus.TERMINAL, tuple)
    assert isinstance(TaskStatus.ALL, tuple)
    assert isinstance(InstanceStatus.ALL, tuple)
    assert isinstance(JobStatus.ALL, tuple)


def test_user_role_permissions_are_immutable() -> None:
    """权限映射应返回拷贝,避免修改全局常量."""
    admin_perms = UserRole.get_permissions(UserRole.ADMIN)
    admin_perms.append("dummy")
    assert "dummy" not in UserRole.PERMISSIONS[UserRole.ADMIN]


def test_user_role_collections_are_tuples() -> None:
    """确保用户角色列表不可变."""
    assert isinstance(UserRole.ALL, tuple)
    assert isinstance(UserRole.PERMISSIONS[UserRole.VIEWER], tuple)
