from fastapi import APIRouter

router = APIRouter()


@router.get("/api/archives")
def list_archives() -> list:
    return []
