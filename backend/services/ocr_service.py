import logging
from pathlib import Path
from typing import Optional
import anyio
import easyocr
from PIL import Image

logger = logging.getLogger(__name__)

_reader_instance: Optional[easyocr.Reader] = None
MAX_IMAGE_DIMENSION = 2800  # Resize oversized images to prevent EasyOCR memory explosions


def get_ocr_reader() -> easyocr.Reader:
    """
    Lazy singleton loader for EasyOCR reader.
    Initializes models with Indo-European language support.
    """
    global _reader_instance
    if _reader_instance is None:
        logger.info("Initializing EasyOCR reader (languages: id, en)...")
        _reader_instance = easyocr.Reader(["id", "en"], gpu=False)
    return _reader_instance


def preprocess_image_for_ocr(file_path: str) -> str:
    """
    Preprocesses image to optimize OCR accuracy and memory footprint.
    Normalizes color space to RGB and scales down giant resolutions if needed.
    """
    try:
        path = Path(file_path)
        with Image.open(path) as img:
            needs_save = False

            # Convert non-RGB (RGBA, P, 1) to RGB
            if img.mode != "RGB":
                img = img.convert("RGB")
                needs_save = True

            # Downsample if image exceeds max dimensions
            width, height = img.size
            if max(width, height) > MAX_IMAGE_DIMENSION:
                scale = MAX_IMAGE_DIMENSION / max(width, height)
                new_size = (int(width * scale), int(height * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                needs_save = True

            if needs_save:
                img.save(file_path, quality=95)

    except Exception as e:
        logger.warning(f"Image preprocessing skipped: {e}")

    return file_path


async def process_easyocr(file_path: str) -> str:
    """
    Processes a local image file with EasyOCR asynchronously via thread pool
    to prevent event loop blocking.
    """
    try:
        # Preprocessing on worker thread
        processed_path = await anyio.to_thread.run_sync(preprocess_image_for_ocr, file_path)

        reader = get_ocr_reader()

        def _run_readtext():
            return reader.readtext(processed_path, detail=0)

        # Offload synchronous CPU-heavy OCR task to worker thread pool
        results = await anyio.to_thread.run_sync(_run_readtext)

        extracted_text = "\n".join(results)
        return extracted_text

    except Exception as e:
        logger.error(f"Error executing EasyOCR: {e}")
        raise e
