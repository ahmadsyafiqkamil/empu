import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlmodel import Session

from empu.auth import optional_studio
from empu.config import Settings, get_settings
from empu.db import get_session
from empu.export.common import ExportScope, entries_for_scope
from empu.export.csv_export import build_csv
from empu.export.eaf_export import build_eaf
from empu.export.json_export import build_json
from empu.export.zip_export import build_zip
from empu.models import Archive, Recording
from empu.packs import load_pack

router = APIRouter()


@router.get("/api/archives/{archive_id}/export")
def export_archive(
    archive_id: int,
    format: str = Query(..., pattern="^(json|csv|eaf|zip)$"),
    scope: ExportScope = Query("public"),
    session: Session = Depends(get_session),
    auth=Depends(optional_studio),
    settings: Settings = Depends(get_settings),
):
    if scope == "all" and not auth.has_key:
        raise HTTPException(401, "studio key required for scope=all")
    archive = session.get(Archive, archive_id)
    if archive is None:
        raise HTTPException(404, "archive not found")
    pack = load_pack(archive.craft_pack_id, settings.packs_dir)
    if format == "json":
        body = json.dumps(build_json(session, archive, pack, scope), ensure_ascii=False, indent=1)
        return Response(body, media_type="application/json")
    if format == "csv":
        return Response(
            build_csv(entries_for_scope(session, archive.id, scope), session),
            media_type="text/csv",
        )
    if format == "eaf":
        rows = entries_for_scope(session, archive.id, scope)
        rec_ids = {o.recording_id for _, occs in rows for o in occs}
        if len(rec_ids) != 1:
            raise HTTPException(400, "eaf export needs exactly one recording in scope; use zip")
        rec = session.get(Recording, next(iter(rec_ids)))
        return Response(build_eaf(rec, rows), media_type="application/xml")
    data = build_zip(session, archive, pack, scope, settings)
    return Response(
        data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{archive.slug}-{scope}.zip"'},
    )
