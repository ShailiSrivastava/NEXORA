from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.agent import router as agent_router
from app.api.routes.evaluation import router as evaluation_router
from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.match import router as match_router
from app.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.project_name,
        version=settings.app_version,
        description="Agentic AI Career Intelligence Platform",
        debug=settings.debug,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(match_router)
    app.include_router(agent_router)
    app.include_router(jobs_router)
    app.include_router(evaluation_router)

    @app.get("/")
    def root() -> dict[str, str]:
        return {"message": f"{settings.project_name} is running"}

    return app


app = create_app()
