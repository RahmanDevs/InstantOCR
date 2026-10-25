from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.routers import ocr
from backend.database import engine, Base

# Create DB tables if not present
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Instant-OCR Engine API",
    version="1.0.0",
    description="AI-Powered OCR Service powered by FastAPI & Hugging Face"
)

# Konfigurasi CORS dinamis dari settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Router
app.include_router(ocr.router)

@app.get("/")
def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "message": "Instant-OCR API Service Running",
        "cors_origins": settings.parsed_cors_origins
    }
