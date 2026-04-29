import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import get_settings
from routers import (
    assignments,
    auth,
    exercises,
    plan_templates,
    plans,
    users,
    weekly_split_templates,
)
from routers.deps import get_current_user
from fastapi import Depends

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

settings = get_settings()

app = FastAPI(title="Virtuagym Assessment Test - Workout Plan Manager", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

uploads_path = Path(settings.uploads_dir)
uploads_path.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

protected = [Depends(get_current_user)]

# Public routes
app.include_router(auth.router, prefix="/api/auth")

# Protected routes
app.include_router(users.router, prefix="/api/users", dependencies=protected)
app.include_router(exercises.router, prefix="/api/exercises", dependencies=protected)
app.include_router(
    plan_templates.router, prefix="/api/plan-templates", dependencies=protected
)
app.include_router(
    weekly_split_templates.router,
    prefix="/api/weekly-split-templates",
    dependencies=protected,
)
app.include_router(plans.router, prefix="/api/plans", dependencies=protected)
app.include_router(assignments.router, prefix="/api/assignments", dependencies=protected)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
