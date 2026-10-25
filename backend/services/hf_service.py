import logging
import httpx
from backend.config import settings

logger = logging.getLogger(__name__)

async def query_huggingface_ocr(file_bytes: bytes) -> dict:
    """
    Sends image bytes to the Hugging Face Inference API.
    Raises ValueError or httpx.HTTPError if unconfigured or request fails.
    """
    token = settings.effective_hf_token
    model_url = settings.effective_hf_model_url

    if not token or token == "your_huggingface_api_token_here":
        raise ValueError("Hugging Face API token is not configured.")

    if not model_url:
        raise ValueError("Hugging Face model URL is not configured.")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            model_url,
            headers=headers,
            content=file_bytes
        )

    if response.status_code != 200:
        logger.warning(f"Hugging Face API returned status {response.status_code}: {response.text}")
        return {"error": f"HF API Error: {response.status_code}", "detail": response.text}

    return response.json()
