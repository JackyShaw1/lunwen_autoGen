from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.seed import init_db
from app.api.auth import router as auth_router
from app.api.cases import router as cases_router
from app.api.dashboard import router as dashboard_router
from app.api.admin import router as admin_router
from app.api.websocket import router as ws_router
from app.api.materials import router as materials_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(cases_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(materials_router, prefix="/api")
app.include_router(ws_router)


@app.get("/api/health")
def health():
    from app.config import get_settings

    s = get_settings()
    return {
        "status": "ok",
        "app": s.app_name,
        "generation_mode": "llm" if (s.openai_api_key and not s.use_mock_generation) else "mock",
        "model": s.openai_model if s.openai_api_key and not s.use_mock_generation else None,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.backend_port, reload=settings.debug)
