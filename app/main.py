import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.database.db import init_db
from app.routers import analytics, auth, tickets, users, websocket
from app.seed import run_seed

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    if settings.seed_demo_data:
        thread = threading.Thread(target=run_seed, name="demo-seed", daemon=True)
        thread.start()
        logger.info("Demo seed started in background")
    yield


app = FastAPI(
    title="Smart Support Ticket Classifier API",
    description=(
        "Production-grade ML-powered support ticket classification platform. "
        "Uses TF-IDF + Logistic Regression for category prediction, "
        "a business rules engine for priority assignment, and keyword-based escalation detection. "
        "Includes JWT authentication, role-based access control, ticket workflow management, "
        "real-time WebSocket updates, and analytics export."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tickets.router)
app.include_router(analytics.router)
app.include_router(websocket.router)


@app.get("/health", tags=["Health"], summary="Health check for load balancers")
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.exception_handler(Exception)
async def global_exception_handler(_request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"},
    )


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi
