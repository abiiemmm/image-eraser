from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
from app.services.eraser_service import process_image

router = APIRouter()

@router.post("/remove-bg")
async def remove_background(image: UploadFile = File(...)):
    # 1. Validasi File
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File harus berupa gambar")
    
    try:
        # 2. Baca file ke memory (RAM)
        contents = await image.read()
        
        # 3. Proses AI (CPU/GPU bound)
        result_bytes = process_image(contents)
        
        # 4. Return langsung sebagai Image Blob (image/png)
        # Agar frontend bisa langsung menampilkan tanpa decode base64
        return Response(content=result_bytes, media_type="image/png")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")