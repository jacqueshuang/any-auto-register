"""account_manager - 多平台账号管理后台"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.accounts import router as accounts_router
from api.actions import router as actions_router
from api.config import router as config_router
from api.platforms import router as platforms_router
from api.proxies import router as proxies_router
from api.tasks import router as tasks_router
from core.db import init_db
from core.registry import load_all

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"
FRONTEND_INDEX_FILE = FRONTEND_DIST_DIR / "index.html"

app = FastAPI(title="Account Manager", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(platforms_router, prefix="/api")
app.include_router(proxies_router, prefix="/api")
app.include_router(config_router, prefix="/api")
app.include_router(actions_router, prefix="/api")

assets_dir = FRONTEND_DIST_DIR / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.on_event("startup")
def on_startup():
    init_db()
    load_all()
    print("[OK] 数据库初始化完成")
    from core.registry import list_platforms

    print(f"[OK] 已加载平台: {[p['name'] for p in list_platforms()]}")
    from core.scheduler import scheduler

    scheduler.start()
    from services.solver_manager import autostart_enabled, start_async

    if autostart_enabled():
        start_async()
    else:
        print("[Solver] 已禁用自动启动")


@app.on_event("shutdown")
def on_shutdown():
    from core.scheduler import scheduler

    scheduler.stop()
    from services.solver_manager import stop

    stop()


@app.get("/api/solver/status")
def solver_status():
    from services.solver_manager import is_running

    return {"running": is_running()}


@app.post("/api/solver/restart")
def solver_restart():
    from services.solver_manager import start_async, stop

    stop()
    start_async()
    return {"message": "重启中"}


def _frontend_file(path: str) -> Path | None:
    if not FRONTEND_INDEX_FILE.exists():
        return None
    if not path:
        return FRONTEND_INDEX_FILE

    candidate = (FRONTEND_DIST_DIR / path).resolve()
    dist_root = FRONTEND_DIST_DIR.resolve()
    if dist_root not in candidate.parents or not candidate.is_file():
        return FRONTEND_INDEX_FILE
    return candidate


@app.get("/", include_in_schema=False)
def frontend_index():
    file_path = _frontend_file("")
    if file_path is None:
        raise HTTPException(status_code=404, detail="Frontend build not found")
    return FileResponse(file_path)


@app.get("/{full_path:path}", include_in_schema=False)
def frontend_routes(full_path: str):
    if full_path == "api" or full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")

    file_path = _frontend_file(full_path)
    if file_path is None:
        raise HTTPException(status_code=404, detail="Frontend build not found")
    return FileResponse(file_path)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
