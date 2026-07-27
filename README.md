# Image Eraser

Hapus background gambar otomatis (AI background remover) dengan backend FastAPI + `rembg`, dan frontend Nuxt.

## Struktur Proyek

```
.
├── apps/
│   ├── backend/               # FastAPI service
│   │   ├── app/
│   │   │   ├── core/           # Konfigurasi (settings, CORS, dsb.)
│   │   │   ├── routers/        # Endpoint API
│   │   │   ├── services/       # Logic pemrosesan gambar (rembg)
│   │   │   └── main.py         # Entry point FastAPI
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── frontend/               # Nuxt app
│       ├── app.vue
│       ├── nuxt.config.ts
│       └── Dockerfile
└── docker-compose.yml
```

## Menjalankan dengan Docker

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

## Menjalankan Manual (Development)

### Backend

```bash
cd apps/backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd apps/frontend
npm install
npm run dev
```

Frontend membaca alamat backend dari environment variable `NUXT_PUBLIC_API_BASE`
(default: `http://localhost:8000`), lihat `apps/frontend/nuxt.config.ts`.
