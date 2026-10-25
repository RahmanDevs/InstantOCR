from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime, timezone
from backend.database import Base

def utc_now():
    return datetime.now(timezone.utc)

# ORM Structured Skeleton for table (matching Django project_ocrdocument)
class OCRDocument(Base):
    __tablename__ = "project_ocrdocument"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    extracted_text = Column(Text, nullable=True)
    export_format = Column(String(10), default="txt")
    created_at = Column(DateTime(timezone=True), default=utc_now)
