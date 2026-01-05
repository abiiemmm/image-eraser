from rembg import remove, new_session
import io
from PIL import Image

# Kita tetap gunakan model terbaik ini
model_name = "isnet-general-use"
# Opsi alternatif jika isnet masih kurang tajam untuk logo: coba ganti jadi "u2net" (model klasik kadang lebih tegas)
# model_name = "u2net" 

session = new_session(model_name)

def process_image(file_bytes: bytes) -> bytes:
    """
    Memproses gambar dengan konfigurasi khusus untuk ketajaman (Logo Specialist).
    """
    try:
        # --- KONFIGURASI "SHARP EDGE / LOGO SPECIALIST" ---
        
        # Untuk objek dengan garis tegas seperti logo, mematikan alpha matting
        # seringkali memberikan hasil yang lebih utuh dan tajam daripada mencoba menghaluskannya.
        output_data = remove(
            file_bytes, 
            session=session,
            
            # 1. MATIKAN Alpha Matting. 
            # Kita ingin potongan yang tegas, bukan halus.
            alpha_matting=False,
            
            # (Parameter alpha_matting_* lainnya tidak akan berfungsi jika alpha_matting=False)
            
            # 2. Post Process Mask tetap ON
            # Berguna untuk menghilangkan titik-titik noise kecil yang mungkin tertinggal.
            post_process_mask=True
        )
        
        # --- POLESAN TAMBAHAN ---
        img = Image.open(io.BytesIO(output_data)).convert("RGBA")
        
        # Tips Pro: Jika hasil ini masih ada sedikit garis putih (halo),
        # kita tidak bisa pakai 'erode' dari rembg lagi.
        # Solusinya di dunia nyata adalah menggunakan trik "Inner Shadow" di CSS frontend,
        # tapi untuk backend, settingan ini adalah yang paling maksimal untuk menjaga keutuhan logo.

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    except Exception as e:
        print(f"Error processing image: {e}")
        raise e