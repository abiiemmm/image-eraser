import io
import logging
import time
import zipfile
import asyncio
from collections import defaultdict, deque

from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from app.services.eraser_service import process_image
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)
job_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_JOBS)
request_history: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(request: Request) -> None:
    now = time.monotonic()
    client = request.client.host if request.client else 'unknown'
    history = request_history[client]
    while history and now - history[0] > settings.RATE_LIMIT_WINDOW_SECONDS:
        history.popleft()
    if len(history) >= settings.RATE_LIMIT_REQUESTS:
        raise HTTPException(status_code=429, detail='Terlalu banyak request. Coba lagi nanti.')
    history.append(now)


async def read_valid_image(image: UploadFile) -> bytes:
    if not image.content_type or not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail='File harus berupa gambar')
    contents = await image.read()
    if not contents:
        raise HTTPException(status_code=400, detail='File gambar kosong')
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail='Ukuran gambar maksimal 10 MB')
    from PIL import Image, UnidentifiedImageError
    try:
        with Image.open(io.BytesIO(contents)) as source:
            source.verify()
            if source.format not in {'JPEG', 'PNG', 'WEBP'}:
                raise HTTPException(status_code=400, detail='Format yang didukung: JPG, PNG, atau WEBP')
            if source.width * source.height > settings.MAX_IMAGE_PIXELS:
                raise HTTPException(status_code=413, detail='Resolusi gambar terlalu besar')
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail='Format gambar tidak valid')
    return contents

@router.post("/remove-bg")
async def remove_background(request: Request, image: UploadFile = File(...)):
    check_rate_limit(request)
    try:
        contents = await read_valid_image(image)
        async with job_semaphore:
            result_bytes = await run_in_threadpool(process_image, contents)
        return Response(content=result_bytes, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Image processing failed: %s", e)
        raise HTTPException(status_code=500, detail="Gagal memproses gambar")
    finally:
        await image.close()


@router.post('/remove-bg/batch')
async def remove_background_batch(request: Request, images: list[UploadFile] = File(...)):
    check_rate_limit(request)
    if not images or len(images) > settings.MAX_BATCH_FILES:
        raise HTTPException(status_code=400, detail=f'Maksimal {settings.MAX_BATCH_FILES} gambar per batch')
    archive = io.BytesIO()
    try:
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
            for index, image in enumerate(images, start=1):
                try:
                    contents = await read_valid_image(image)
                    async with job_semaphore:
                        result = await run_in_threadpool(process_image, contents)
                    name = f'{index:02d}-{image.filename or "image"}'.rsplit('.', 1)[0] + '.png'
                    output.writestr(name, result)
                finally:
                    await image.close()
        return Response(content=archive.getvalue(), media_type='application/zip', headers={'Content-Disposition': 'attachment; filename=image-eraser-results.zip'})
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception('Batch processing failed: %s', exc)
        raise HTTPException(status_code=500, detail='Gagal memproses batch gambar')
