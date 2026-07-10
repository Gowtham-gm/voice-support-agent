import time
from collections import defaultdict, deque

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.rbac import Role, role_has_permission
from app.core.config import settings
from app.core.security import decode_token
from app.db.models import User
from app.db.session import get_db
from app.exceptions import AuthenticationError, AuthorizationError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise AuthenticationError(str(exc)) from exc

    if payload.get("type") != "access":
        raise AuthenticationError("Expected an access token")

    user_id = payload.get("sub")
    user = db.get(User, user_id)
    if user is None:
        raise AuthenticationError("User no longer exists")
    return user


def require_permission(permission: str):
    """Dependency factory enforcing RBAC for a named capability."""

    def _guard(current_user: User = Depends(get_current_user)) -> User:
        role = Role(current_user.role)
        if not role_has_permission(role, permission):
            raise AuthorizationError(
                f"Role '{role.value}' is not permitted to perform '{permission}'"
            )
        return current_user

    return _guard


# --- Minimal in-process sliding-window rate limiter (swap for Redis+slowapi in prod) ---
_request_log: dict[str, deque] = defaultdict(deque)


def rate_limiter(request: Request) -> None:
    client_key = request.client.host if request.client else "unknown"
    now = time.time()
    window = 60.0
    log = _request_log[client_key]

    while log and now - log[0] > window:
        log.popleft()

    if len(log) >= settings.RATE_LIMIT_PER_MINUTE:
        from app.exceptions import AppException
        from fastapi import status

        raise AppException("Rate limit exceeded, slow down.", status.HTTP_429_TOO_MANY_REQUESTS)

    log.append(now)
