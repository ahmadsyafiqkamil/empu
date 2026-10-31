from fastapi import Depends, FastAPI

from empu.auth import require_studio
from empu.routes import (
    archives,
    ask,
    entries,
    eval,
    exports,
    health,
    jobs,
    media,
    packs,
    public,
    recordings,
    sandbox,
)


def create_app() -> FastAPI:
    app = FastAPI(title="Empu", version="0.1.0")
    app.include_router(health.router)
    app.include_router(packs.router)
    app.include_router(public.router)
    app.include_router(ask.router)
    app.include_router(exports.router)
    app.include_router(eval.router)
    app.include_router(sandbox.router)
    app.include_router(archives.router, dependencies=[Depends(require_studio)])
    app.include_router(recordings.router)
    app.include_router(jobs.router)
    app.include_router(entries.router)
    app.include_router(media.router)
    return app
