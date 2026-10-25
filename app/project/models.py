from django.db import models

class UploadedImage(models.Model):
    image = models.ImageField(upload_to='uploads/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image {self.id} - {self.created_at}"


class OCRDocument(models.Model):
    filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    extracted_text = models.TextField(blank=True, null=True)
    export_format = models.CharField(max_length=10, default="txt")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "project_ocrdocument"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.filename} ({self.export_format})"
