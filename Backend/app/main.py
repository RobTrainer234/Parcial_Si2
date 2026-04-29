from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.packages.finanzas_seguros import router as finanzas_seguros_router
from app.packages.gestion_auxilio import router as gestion_auxilio_router
from app.packages.inteligencia_triaje import router as inteligencia_triaje_router
from app.packages.operaciones_taller import router as operaciones_taller_router
from app.packages.reputacion_auditoria import router as reputacion_auditoria_router
from app.packages.seguridad_usuarios import router as seguridad_usuarios_router
from app.routers import health_router


def create_app() -> FastAPI:
    settings = get_settings()
    settings.local_media_root.mkdir(parents=True, exist_ok=True)
    app = FastAPI(title="Proyecto SI2 Backend")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allow_origins),
        allow_origin_regex=settings.cors_allow_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.mount("/media", StaticFiles(directory=settings.local_media_root), name="media")
    app.include_router(health_router)
    app.include_router(seguridad_usuarios_router)
    app.include_router(inteligencia_triaje_router)
    app.include_router(gestion_auxilio_router)
    app.include_router(finanzas_seguros_router)
    app.include_router(operaciones_taller_router)
    app.include_router(reputacion_auditoria_router)
    return app


app = create_app()
