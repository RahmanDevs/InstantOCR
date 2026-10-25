import io
import os
import re
import time
import uuid
import logging
from pathlib import Path
from typing import Optional, Dict
import aiofiles
from PIL import Image

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models import OCRDocument
from backend.services.hf_service import query_huggingface_ocr
from backend.services.ocr_service import process_easyocr
from backend.services.converter_service import DocumentConverter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ocr", tags=["OCR Engine"])

# Upload directory from settings
UPLOAD_DIR: Path = settings.UPLOAD_DIR
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Configuration Limits
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_FORMATS = {"txt", "pdf", "docx", "xlsx", "csv", "json"}
MAX_FILE_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
CHUNK_SIZE = 1024 * 1024  # 1MB per chunk

# Pillow Safety: Protect against Decompression Bombs (e.g. 50,000x50,000 malicious pixel bombs)
Image.MAX_IMAGE_PIXELS = 25_000_000

# Simple In-Memory Rate Limiter (Sliding Window per IP)
# Allows up to 20 OCR requests per 60 seconds per client IP
RATE_LIMIT_MAX_REQUESTS = 20
RATE_LIMIT_WINDOW_SECONDS = 60
_ip_request_history: Dict[str, list[float]] = {}


def check_rate_limit(request: Request):
    """Enforces rate limiting based on client IP."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    timestamps = _ip_request_history.get(client_ip, [])

    # Filter out timestamps older than the window
    valid_timestamps = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW_SECONDS]

    if len(valid_timestamps) >= RATE_LIMIT_MAX_REQUESTS:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        raise HTTPException(
            status_code=429,
            detail="Terlalu banyak permintaan konversi OCR. Mohon tunggu beberapa saat sebelum mencoba lagi."
        )

    valid_timestamps.append(now)
    _ip_request_history[client_ip] = valid_timestamps


def sanitize_filename(filename: str) -> str:
    """Sanitizes filename against path traversal and header injection."""
    clean = os.path.basename(filename or "document")
    # Replace anything that isn't alphanumeric, dot, underscore, or dash
    clean = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', clean)
    # Collapse multiple dots or underscores
    clean = re.sub(r'\.{2,}', '.', clean)
    clean = re.sub(r'_{2,}', '_', clean)
    return clean[:80] or "document"


class ConvertTextPayload(BaseModel):
    text: str = Field(..., description="Extracted OCR text to format")
    format: str = Field("txt", description="Desired export format")
    filename: Optional[str] = Field("instantocr_export", description="Base filename")


@router.post("/process")
async def process_ocr_image(
    request: Request,
    file: UploadFile = File(...),
    format: str = Form("txt"),
    db: Session = Depends(get_db)
):
    """
    Validates file extension, size (stream-checked), and image integrity.
    Extracts text via HuggingFace with automatic fallback to EasyOCR,
    saves record in database, and returns metadata & download URLs.
    """
    check_rate_limit(request)

    # 1. Validasi Format Ekspor
    export_format = (format or "txt").lower().strip()
    if export_format not in ALLOWED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Format ekspor tidak didukung. Pilihan yang valid: {', '.join(sorted(ALLOWED_FORMATS))}"
        )

    # 2. Validasi Ekstensi File
    raw_name = file.filename or "image.png"
    safe_filename = sanitize_filename(raw_name)
    file_ext = os.path.splitext(safe_filename)[1].lower()

    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Ekstensi file '{file_ext}' tidak diperbolehkan. Gunakan: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # 3. Stream & Batasi Ukuran File (Anti-OOM DoS)
    byte_chunks = []
    total_size = 0

    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > MAX_FILE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"Ukuran file melebihi batas maksimum {settings.MAX_UPLOAD_SIZE_MB}MB."
            )
        byte_chunks.append(chunk)

    if total_size == 0:
        raise HTTPException(status_code=400, detail="File yang diunggah kosong.")

    file_bytes = b"".join(byte_chunks)

    # 4. Validasi Integritas Gambar & Proteksi Decompression Bomb
    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            img.verify()
    except Image.DecompressionBombError:
        raise HTTPException(
            status_code=400,
            detail="Gambar terlalu besar atau terdeteksi sebagai decompression bomb."
        )
    except Exception as img_err:
        logger.warning(f"File validation failed: {img_err}")
        raise HTTPException(
            status_code=400,
            detail="File bukan gambar yang valid atau data gambar rusak."
        )

    # 5. Simpan File ke Storage Lokal
    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
    full_file_path = UPLOAD_DIR / unique_filename
    relative_path = f"uploads/{unique_filename}"

    try:
        async with aiofiles.open(str(full_file_path), "wb") as out_file:
            await out_file.write(file_bytes)
    except Exception as write_err:
        logger.error(f"Gagal menulis file: {write_err}")
        raise HTTPException(status_code=500, detail="Gagal menyimpan file di server.")

    extracted_text = ""
    engine_used = "huggingface"

    # 6. OCR Pipeline Execution
    try:
        hf_response = await query_huggingface_ocr(file_bytes)

        if isinstance(hf_response, dict) and "error" in hf_response:
            raise Exception(f"Hugging Face API: {hf_response.get('error')}")

        if isinstance(hf_response, list) and len(hf_response) > 0:
            extracted_text = hf_response[0].get("generated_text", "")
        elif isinstance(hf_response, dict):
            extracted_text = hf_response.get("text", str(hf_response))

    except Exception as hf_err:
        logger.info(f"Hugging Face fallback trigger ({hf_err}). Mengalihkan ke EasyOCR lokal...")
        engine_used = "easyocr_fallback"

        try:
            extracted_text = await process_easyocr(str(full_file_path))
        except Exception as ocr_err:
            logger.error(f"EasyOCR Lokal gagal: {ocr_err}")
            if full_file_path.exists():
                full_file_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=500,
                detail="Gagal mengekstraksi teks dari gambar melalui semua engine OCR."
            )

    # 7. Simpan Record ke Database
    db_record = OCRDocument(
        filename=safe_filename,
        file_path=relative_path,
        extracted_text=extracted_text,
        export_format=export_format
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    return {
        "status": "success",
        "id": db_record.id,
        "filename": safe_filename,
        "engine_used": engine_used,
        "format": export_format,
        "text": extracted_text,
        "character_count": len(extracted_text),
        "line_count": len(extracted_text.splitlines()),
        "file_url": f"/{relative_path}",
        "download_url": f"/api/v1/ocr/export?id={db_record.id}&format={export_format}"
    }


@router.get("/export")
def export_ocr_document(
    id: Optional[int] = Query(None, description="Document ID in database"),
    format: str = Query("txt", description="Desired export format (txt, pdf, docx, xlsx, csv, json)"),
    db: Session = Depends(get_db)
):
    """
    Exports a stored OCR document in the chosen format with sanitized headers.
    """
    if id is None:
        raise HTTPException(status_code=400, detail="Parameter 'id' dokumen diperlukan.")

    doc = db.query(OCRDocument).filter(OCRDocument.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumen OCR tidak ditemukan.")

    requested_format = (format or doc.export_format or "txt").lower().strip()
    if requested_format not in ALLOWED_FORMATS:
        raise HTTPException(status_code=400, detail=f"Format tidak valid: {requested_format}")

    safe_base = sanitize_filename(os.path.splitext(doc.filename)[0])
    file_bytes, content_type, ext = DocumentConverter.convert(
        text=doc.extracted_text or "",
        format_type=requested_format,
        filename=safe_base
    )

    download_filename = f"{safe_base}_{doc.id}.{ext}"

    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{download_filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )


@router.post("/convert-text")
def convert_extracted_text(payload: ConvertTextPayload):
    """
    Instantly converts arbitrary extracted text to the specified format
    without requiring a stored database document.
    """
    requested_format = payload.format.lower().strip()
    if requested_format not in ALLOWED_FORMATS:
        raise HTTPException(status_code=400, detail=f"Format tidak valid: {requested_format}")

    safe_base = sanitize_filename(payload.filename or "instantocr_export")
    file_bytes, content_type, ext = DocumentConverter.convert(
        text=payload.text,
        format_type=requested_format,
        filename=safe_base
    )

    download_filename = f"{safe_base}.{ext}"

    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{download_filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )
