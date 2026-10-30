from fastapi import APIRouter, Depends, HTTPException

from empu.api_schemas import PackYamlIn
from empu.auth import AuthContext, require_studio
from empu.config import Settings, get_settings
from empu.packs import (
    PackError,
    is_valid_pack_id,
    list_packs,
    load_pack,
    parse_yaml,
    write_pack,
)

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


def _parse_body(yaml_text: str):
    try:
        return parse_yaml(yaml_text)
    except PackError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/api/packs/validate")
def validate_pack(
    body: PackYamlIn,
    _auth: AuthContext = Depends(require_studio),
) -> dict:
    pack = _parse_body(body.yaml)
    return {
        "id": pack.id,
        "version": pack.version,
        "name": pack.name.model_dump(),
        "languages": pack.languages,
        "n_stages": len(pack.stages),
        "n_terms": len(pack.terms),
    }


@router.post("/api/packs", status_code=201)
def create_pack(
    body: PackYamlIn,
    _auth: AuthContext = Depends(require_studio),
    settings: Settings = Depends(get_settings),
) -> dict:
    pack = _parse_body(body.yaml)
    if not is_valid_pack_id(pack.id):
        raise HTTPException(400, f"pack id {pack.id!r} is not a valid slug ([a-z0-9_]+)")
    path = settings.packs_dir / f"{pack.id}.yaml"
    if path.exists():
        raise HTTPException(409, f"pack {pack.id!r} already exists")
    write_pack(pack, settings.packs_dir)
    return {"id": pack.id, "version": pack.version, "name": pack.name.model_dump()}