from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlmodel import Session

from empu.auth import optional_studio
from empu.config import Settings, get_settings
from empu.db import get_session
from empu.media import abs_from_rel, can_access_media

router = APIRouter()


def _check(session: Session, rel: str, has_key: bool, settings: Settings):
    try:
        path = abs_from_rel(settings.data_dir, rel)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    if not can_access_media(session, rel, has_key=has_key):
        raise HTTPException(401 if not has_key else 403, "forbidden")
    if not path.is_file():
        raise HTTPException(404, "not found")
    return path


@router.get("/media/{path:path}")
def media(
    path: str,
    request: Request,
    session: Session = Depends(get_session),  # noqa: B008
    auth=Depends(optional_studio),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
):
    file_path = _check(session, path, auth.has_key, settings)
    return FileResponse(file_path, filename=file_path.name)


@router.get("/api/media-auth")
def media_auth(
    path: str = Query(...),
    session: Session = Depends(get_session),  # noqa: B008
    auth=Depends(optional_studio),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
):
    _check(session, path.lstrip("/"), auth.has_key, settings)
    return {"ok": True}
