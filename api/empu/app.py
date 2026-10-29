from fastapi import Depends, FastAPI

from empu.auth import require_studio
from empu.routes import (
    archives,
    entries,
    eval,
    exports,
    health,
    jobs,
    media,
    packs,
    public,
    recordings,
)


def create_app() -> FastAPI:
    app = FastAPI(title="Empu", version="0.1.0")
    app.include_router(health.router)
    app.include_router(packs.router)
    app.include_router(public.router)
    app.include_router(exports.router)
    app.include_router(eval.router)
    app.include_router(archives.router, dependencies=[Depends(require_studio)])
    app.include_router(recordings.router, dependencies=[Depends(require_studio)])
    app.include_router(jobs.router, dependencies=[Depends(require_studio)])
    app.include_router(entries.router, dependencies=[Depends(require_studio)])
    app.include_router(media.router)
    return app
