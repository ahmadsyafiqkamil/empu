from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from empu.config import Settings, get_settings

STUDIO_HEADER = "X-Studio-Key"


@dataclass(frozen=True)
class AuthContext:
    has_key: bool
    is_sandbox: bool = False


def _match(settings: Settings, x_studio_key: str | None) -> bool:
    secret = settings.studio_key
    if secret is None or not secret.get_secret_value():
        return False
    return bool(x_studio_key) and x_studio_key == secret.get_secret_value()


def optional_studio(
    x_studio_key: str | None = Header(default=None, alias=STUDIO_HEADER),
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> AuthContext:
    return AuthContext(has_key=_match(settings, x_studio_key))


def require_studio(auth: AuthContext = Depends(optional_studio)) -> AuthContext:  # noqa: B008
    if not auth.has_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "studio key required")
    return auth
