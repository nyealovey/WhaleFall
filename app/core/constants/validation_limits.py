"""输入校验/阈值常量.

集中管理 schema/settings/API 中的业务阈值, 避免 magic number 分散在各层.
"""

from __future__ import annotations

from typing import Final

# User auth/password
USER_PASSWORD_MIN_LENGTH: Final[int] = 8
USER_PASSWORD_MAX_LENGTH: Final[int] = 128

# Credential(write path)
CREDENTIAL_USERNAME_MIN_LENGTH: Final[int] = 3
CREDENTIAL_USERNAME_MAX_LENGTH: Final[int] = 50
CREDENTIAL_PASSWORD_MIN_LENGTH: Final[int] = 6
CREDENTIAL_PASSWORD_MAX_LENGTH: Final[int] = 128

# Instance(write path)
INSTANCE_NAME_MAX_LENGTH: Final[int] = 100
HOST_MAX_LENGTH: Final[int] = 255
DATABASE_NAME_MAX_LENGTH: Final[int] = 64
DESCRIPTION_MAX_LENGTH: Final[int] = 500

# Network / address validation
PORT_MIN: Final[int] = 1
PORT_MAX: Final[int] = 65535
IPV4_OCTET_MAX: Final[int] = 255

# API pagination/query limits
DATABASE_TABLE_SIZES_LIMIT_MAX: Final[int] = 2000

# Settings validation constraints
BCRYPT_LOG_ROUNDS_MIN: Final[int] = 4
HOUR_OF_DAY_MIN: Final[int] = 0
HOUR_OF_DAY_MAX: Final[int] = 23

