from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import api
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

@app.get("/")
def read_root():
    return {"message": "Magic Eraser API is Running (FastAPI) 🚀"}

# Entry point untuk debugging langsung
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)