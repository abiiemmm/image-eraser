from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import api
from app.services.eraser_service import load_model
import uvicorn

app = FastAPI(title=settings.PROJECT_NAME)

# Setup CORS (Agar Nuxt bisa akses)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Router
app.include_router(api.router, prefix="/api")


@app.on_event("startup")
def startup() -> None:
    load_model()

@app.get("/")
def read_root():
    return {"message": "Image Eraser API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    from app.services import eraser_service
    return {"status": "ready" if eraser_service.session is not None else "loading"}

# Entry point untuk debugging langsung
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
