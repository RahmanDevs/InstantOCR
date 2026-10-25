from django.contrib import admin
from .models import UploadedImage, OCRDocument

@admin.register(UploadedImage)
class UploadedImageAdmin(admin.ModelAdmin):
    list_display = ("id", "image", "created_at")
    list_filter = ("created_at",)

@admin.register(OCRDocument)
class OCRDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "filename", "export_format", "created_at")
    list_filter = ("export_format", "created_at")
    search_fields = ("filename", "extracted_text")
