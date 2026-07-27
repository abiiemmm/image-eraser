# GANTI DENGAN IMPORT INI (Pydantic V2)
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Image Eraser API"
    API_V1_STR: str = "/api"
    BACKEND_CORS_ORIGINS: list = ["http://localhost:3000"]

    class Config:
        case_sensitive = True

# PENTING: Baris ini tidak boleh hilang! 
# Error sebelumnya terjadi karena baris ini hilang atau gagal di-load.
settings = Settings()