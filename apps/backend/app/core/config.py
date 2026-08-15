# GANTI DENGAN IMPORT INI (Pydantic V2)
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Image Eraser API"
    API_V1_STR: str = "/api"
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    MAX_UPLOAD_SIZE: int = Field(default=10 * 1024 * 1024, gt=0)
    MAX_IMAGE_PIXELS: int = Field(default=40_000_000, gt=0)
    MAX_BATCH_FILES: int = Field(default=10, gt=0)
    MAX_CONCURRENT_JOBS: int = Field(default=2, gt=0)
    RATE_LIMIT_REQUESTS: int = Field(default=20, gt=0)
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, gt=0)

    class Config:
        case_sensitive = True

# PENTING: Baris ini tidak boleh hilang! 
# Error sebelumnya terjadi karena baris ini hilang atau gagal di-load.
settings = Settings()
