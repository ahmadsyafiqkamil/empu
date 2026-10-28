from fastapi import APIRouter, Depends, HTTPException

from empu.config import Settings, get_settings
from empu.packs import PackError, list_packs, load_pack

router = APIRouter()


@router.get("/api/packs")
def packs(settings: Settings = Depends(get_settings)) -> list[dict]:
    return [
        {"id": p.id, "version": p.version, "name": p.name.model_dump()}
        for p in list_packs(settings.packs_dir)
    ]


@router.get("/api/packs/{pack_id}")
def pack_detail(pack_id: str, settings: Settings = Depends(get_settings)) -> dict:
    try:
        p = load_pack(pack_id, settings.packs_dir)
    except PackError as e:
        raise HTTPException(404, str(e)) from e
    return p.model_dump()
