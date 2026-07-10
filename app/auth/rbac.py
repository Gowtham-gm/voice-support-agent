from enum import Enum


class Role(str, Enum):
    CUSTOMER = "customer"
    SUPPORT_AGENT = "support_agent"
    ADMIN = "admin"


# Endpoint-level permission map: which roles may call which capability.
PERMISSIONS: dict[str, set[Role]] = {
    "chat": {Role.CUSTOMER, Role.SUPPORT_AGENT, Role.ADMIN},
    "voice": {Role.CUSTOMER, Role.SUPPORT_AGENT, Role.ADMIN},
    "view_all_sessions": {Role.SUPPORT_AGENT, Role.ADMIN},
    "manage_users": {Role.ADMIN},
}


def role_has_permission(role: Role, permission: str) -> bool:
    allowed = PERMISSIONS.get(permission, set())
    return role in allowed
