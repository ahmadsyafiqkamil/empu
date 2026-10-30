from dataclasses import dataclass

from fastapi import Cookie, Depends, Header, HTTPException, status

from empu.config import Settings, get_settings

STUDIO_HEADER = "X-Studio-Key"
# Media tags (<video>, <img>) cannot send custom headers, so the browser must
# prove the studio key through a cookie; it is sent with every same-origin
# media request. optional_studio accepts the key from either source.
STUDIO_COOKIE = "empu_studio_key"


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
    empu_studio_key: str | None = Cookie(default=None, alias=STUDIO_COOKIE),
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> AuthContext:
    # Header wins when present; the cookie is a fallback for browser media tags.
    candidate = x_studio_key or empu_studio_key
    return AuthContext(has_key=_match(settings, candidate))


def require_studio(auth: AuthContext = Depends(optional_studio)) -> AuthContext:  # noqa: B008
    if not auth.has_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "studio key required")
    return auth
