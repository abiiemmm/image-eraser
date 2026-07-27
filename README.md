# Image Eraser

Web app untuk menghapus background gambar secara otomatis pakai AI, tanpa login dan tanpa database. User upload gambar dari browser, backend memprosesnya pakai model AI, hasilnya (PNG transparan) langsung bisa dilihat & di-download.

Terdiri dari 2 aplikasi terpisah di `apps/`:

- **`apps/backend`** — REST API (FastAPI) yang melakukan background removal.
- **`apps/frontend`** — Web UI (Nuxt) tempat user upload gambar dan lihat hasilnya.

## Struktur Proyek

```
.
├── apps/
│   ├── backend/                 # FastAPI service
│   │   ├── app/
│   │   │   ├── core/
│   │   │   │   └── config.py     # Settings: nama project, CORS origins
│   │   │   ├── routers/
│   │   │   │   └── api.py        # Endpoint POST /api/remove-bg
│   │   │   ├── services/
│   │   │   │   └── eraser_service.py  # Logic AI: load model rembg, proses gambar
│   │   │   └── main.py           # Entry point: init FastAPI, CORS, register router
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── frontend/                 # Nuxt app (single-page)
│       ├── app.vue               # Seluruh UI: dropzone, preview, tombol proses & download
│       ├── nuxt.config.ts        # Config Nuxt, module Tailwind, runtimeConfig API base
│       └── Dockerfile
└── docker-compose.yml            # Orkestrasi 2 service: backend (:8000) & frontend (:3000)
```

## Apa yang dilakukan tiap app

### Backend (`apps/backend`)

FastAPI service dengan satu endpoint utama:

- **`POST /api/remove-bg`** — terima file gambar (`multipart/form-data`, field `image`), balikin gambar PNG transparan (background sudah dihapus) sebagai binary response (`image/png`).
  - Validasi: file harus bertipe `image/*`, kalau tidak return `400`.
  - Error saat pemrosesan return `500` dengan detail pesan.
- **`GET /`** — health check sederhana, balikin pesan status API.

Proses penghapusan background (`app/services/eraser_service.py`):
1. Model AI di-load sekali saat startup: [`rembg`](https://github.com/danielgatis/rembg) dengan model `isnet-general-use` (bagus untuk objek/logo dengan garis tegas).
2. Alpha matting **dimatikan** — pilihan sengaja supaya hasil potongan tegas/tajam, bukan halus (cocok untuk logo).
3. `post_process_mask=True` untuk membersihkan noise kecil di mask.
4. Hasil dibuka ulang dengan Pillow, dikonversi ke RGBA, dan di-encode ulang jadi PNG sebelum dikirim balik.

CORS diatur di `app/core/config.py` (`BACKEND_CORS_ORIGINS`), default cuma mengizinkan `http://localhost:3000`.

### Frontend (`apps/frontend`)

Single-page app (satu file `app.vue`) dengan alur:
1. **Upload** — drag & drop atau klik untuk pilih file gambar, langsung ditampilkan preview "Original".
2. **Proses** — tombol "Hapus Background" mengirim file ke backend (`POST {NUXT_PUBLIC_API_BASE}/api/remove-bg`) sebagai `FormData`, lalu menampilkan loading spinner.
3. **Hasil** — response (blob PNG) ditampilkan di panel "Hasil" dengan background checkerboard transparan.
4. **Download** — tombol "Download HD" untuk unduh hasil sebagai `image-eraser-result.png`.
5. **Reset** — tombol "Ulangi" untuk mengulang dari awal.

Alamat backend dibaca dari `runtimeConfig.public.apiBase` (env `NUXT_PUBLIC_API_BASE`), bukan hardcode, lihat `nuxt.config.ts`.

## Menjalankan dengan Docker

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

`docker-compose.yml` menjalankan 2 container (`eraser-backend`, `eraser-frontend`) dan menyimpan cache model AI (`u2net_cache` volume) supaya model tidak perlu di-download ulang tiap kali container dibangun ulang.

## Menjalankan Manual (Development)

### Backend

```bash
cd apps/backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API akan jalan di `http://localhost:8000`, docs otomatis di `http://localhost:8000/docs`.

### Frontend

```bash
cd apps/frontend
npm install
npm run dev
```

UI akan jalan di `http://localhost:3000`.

## Environment Variables

| Variable | Dipakai di | Default | Keterangan |
|---|---|---|---|
| `NUXT_PUBLIC_API_BASE` | frontend | `http://localhost:8000` | Base URL backend yang dipanggil dari browser |
| `BACKEND_CORS_ORIGINS` | backend (`app/core/config.py`) | `["http://localhost:3000"]` | Origin yang diizinkan akses API |

## Tech Stack

- **Backend**: FastAPI, `rembg` (model `isnet-general-use`), Pillow, Uvicorn
- **Frontend**: Nuxt 4, Vue 3, Tailwind CSS
- **Deployment**: Docker + Docker Compose
