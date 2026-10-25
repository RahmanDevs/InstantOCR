import io
import json
from PIL import Image, ImageDraw
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.converter_service import DocumentConverter
from backend.routers.ocr import sanitize_filename

client = TestClient(app)

def create_sample_image(text: str = "TEST OCR PASS") -> bytes:
    """Generate a clean test PNG image with readable text"""
    img = Image.new("RGB", (220, 60), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((10, 20), text, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def test_document_converters():
    sample_text = "Sample OCR line 1\nSample OCR line 2\n12345 Numbers"

    # TXT
    txt_bytes = DocumentConverter.to_txt(sample_text)
    assert sample_text.encode("utf-8") == txt_bytes

    # PDF (Magic bytes %PDF-)
    pdf_bytes = DocumentConverter.to_pdf(sample_text)
    assert pdf_bytes.startswith(b"%PDF-")

    # DOCX (ZIP archive header PK\x03\x04)
    docx_bytes = DocumentConverter.to_docx(sample_text)
    assert docx_bytes.startswith(b"PK\x03\x04")

    # XLSX (ZIP archive header PK\x03\x04)
    xlsx_bytes = DocumentConverter.to_xlsx(sample_text)
    assert xlsx_bytes.startswith(b"PK\x03\x04")

    # CSV
    csv_bytes = DocumentConverter.to_csv(sample_text)
    assert b"Line,Extracted_Text" in csv_bytes
    assert b"Sample OCR line 1" in csv_bytes

    # JSON
    json_bytes = DocumentConverter.to_json(sample_text, "test.png")
    data = json.loads(json_bytes.decode("utf-8"))
    assert data["status"] == "success"
    assert data["extracted_text"] == sample_text
    assert data["word_count"] == 10

def test_api_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

def test_sanitize_filename():
    assert sanitize_filename("../../../etc/passwd.png") == "passwd.png"
    assert sanitize_filename("my file <weird> * name.jpg") == "my_file_weird_name.jpg"
    assert sanitize_filename("") == "document"

def test_process_ocr_invalid_extension():
    response = client.post(
        "/api/v1/ocr/process",
        files={"file": ("malicious.exe", b"MZDummyPayload", "application/x-msdownload")},
        data={"format": "txt"}
    )
    assert response.status_code == 400
    assert "tidak diperbolehkan" in response.json()["detail"]

def test_process_ocr_corrupt_image():
    response = client.post(
        "/api/v1/ocr/process",
        files={"file": ("test.png", b"not_a_real_image_bytes", "image/png")},
        data={"format": "txt"}
    )
    assert response.status_code == 400
    assert "bukan gambar yang valid" in response.json()["detail"]

def test_process_ocr_and_export():
    image_bytes = create_sample_image()
    response = client.post(
        "/api/v1/ocr/process",
        files={"file": ("sample test.png", image_bytes, "image/png")},
        data={"format": "docx"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    doc_id = data["id"]
    assert doc_id > 0
    assert "character_count" in data

    formats_and_headers = [
        ("txt", b""),
        ("pdf", b"%PDF-"),
        ("docx", b"PK\x03\x04"),
        ("xlsx", b"PK\x03\x04"),
        ("csv", b"Line,Extracted_Text"),
        ("json", b'"status": "success"')
    ]

    for fmt, expected_prefix in formats_and_headers:
        export_res = client.get(f"/api/v1/ocr/export?id={doc_id}&format={fmt}")
        assert export_res.status_code == 200
        assert f".{fmt}\"" in export_res.headers["content-disposition"]
        if expected_prefix:
            assert expected_prefix in export_res.content

def test_convert_text_direct_endpoint():
    payload = {
        "text": "Instant Direct Conversion Test\nLine 2",
        "format": "pdf",
        "filename": "my_exported_file"
    }
    response = client.post("/api/v1/ocr/convert-text", json=payload)
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")
    assert "my_exported_file.pdf" in response.headers["content-disposition"]

if __name__ == "__main__":
    pytest.main(["-v", __file__])
