from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api.routes.health import router as health_router
from app.api.routes.prescriptions import router as prescription_router
from app.api.routes.auth import router as auth_router
from app.api.routes.resources import router as resources_router
from app.api.routes.users import admin_router, router as users_router


app = FastAPI(title="Prescription OCR API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in (
            "http://localhost:5173,http://127.0.0.1:5173,"
            "http://localhost:3000,http://127.0.0.1:3000,"
            + os.getenv("FRONTEND_URL", "")
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router, prefix="/api/v1")
app.include_router(prescription_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(resources_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.get("/")
def root() -> dict[str, str]:
	return {
		"message": "Prescription OCR API đang hoạt động.",
		"docs": "/docs",
		"health": "/api/v1/health",
	}