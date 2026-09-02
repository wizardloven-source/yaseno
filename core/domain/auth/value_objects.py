# core/domain/auth/value_objects.py
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class UserId:
    value: UUID

    @classmethod
    def generate(cls) -> "UserId":
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> "UserId":
        return cls(UUID(value))


@dataclass(frozen=True)
class RoleId:
    value: UUID

    @classmethod
    def generate(cls) -> "RoleId":
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> "RoleId":
        return cls(UUID(value))


@dataclass(frozen=True)
class PermissionId:
    value: UUID

    @classmethod
    def generate(cls) -> "PermissionId":
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> "PermissionId":
        return cls(UUID(value))