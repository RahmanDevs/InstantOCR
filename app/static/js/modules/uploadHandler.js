// Catatan: Di ES Modules browser, ekstensi .js WAJIB ditulis!
import { showAlert } from "./alertHandler.js";

let currentBlobUrl = null;

export function initUploadHandler() {
  const uploadArea = document.getElementById("uploadArea") || document.querySelector(".upload-area");
  const fileInput = document.getElementById("imageInput");
  const removeFileBtn = document.getElementById("removeFileBtn");

  if (uploadArea && fileInput) {
    // 1. Klik Area Upload (Aman dari event bubbling tombol remove)
    uploadArea.addEventListener("click", (e) => {
      // Buka file picker HANYA jika yang diklik BUKAN tombol hapus atau elemen di dalam tombol hapus
      if (!e.target.closest("#removeFileBtn") && e.target !== fileInput) {
        fileInput.click();
      }
    });

    // 2. Drag & Drop Event Handlers
    ["dragenter", "dragover"].forEach((eventName) => {
      uploadArea.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.add("drag-active", "border-indigo-500", "bg-indigo-50/5");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      uploadArea.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadArea.classList.remove("drag-active", "border-indigo-500", "bg-indigo-50/5");
      });
    });

    // 3. Drop File
    uploadArea.addEventListener("drop", (e) => {
      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        // Gunakan DataTransfer agar kompatibel lintas browser
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(files[0]);
        fileInput.files = dataTransfer.files;

        handleFileSelection(files[0]);
      }
    });

    // 4. Input Change Event (Saat pilih via File Explorer)
    fileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleFileSelection(e.target.files[0]);
      }
    });
  }

  // 5. Tombol Hapus / Remove File
  if (removeFileBtn) {
    removeFileBtn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation(); // Mencegah pemicuan click pada uploadArea
      resetUploadState();
    });
  }

  // 6. Dukungan Paste dari Clipboard (Ctrl + V)
  window.addEventListener("paste", (e) => {
    const items = e.clipboardData?.items;
    if (!items || !fileInput) return;

    for (let i = 0; i < items.length; i++) {
      if (items[i].type && items[i].type.startsWith("image/")) {
        const file = items[i].getAsFile();
        if (file) {
          const dataTransfer = new DataTransfer();
          dataTransfer.items.add(file);
          fileInput.files = dataTransfer.files;

          handleFileSelection(file);
          showAlert("Gambar dari clipboard berhasil ditempelkan!", "info", 3500);
          break;
        }
      }
    }
  });
}

function handleFileSelection(file) {
  const previewImage = document.getElementById("previewImage");
  const uploadPlaceholder = document.getElementById("uploadPlaceholder") || document.querySelector(".upload-placeholder");
  const fileInfo = document.getElementById("fileInfo");
  const fileName = document.getElementById("fileName");
  const fileSize = document.getElementById("fileSize");
  const removeFileBtn = document.getElementById("removeFileBtn");
  const progressFill = document.getElementById("progressFill");
  const progressText = document.getElementById("progressText");

  // Validasi 1: Tipe File Gambar
  const validTypes = ["image/jpeg", "image/png", "image/webp", "image/jpg"];
  if (!validTypes.includes(file.type)) {
    showAlert("Format file tidak didukung! Mohon hanya unggah gambar (.jpg, .jpeg, .png, .webp).", "warning");
    resetUploadState();
    return;
  }

  // Validasi 2: Ukuran File (Max 10MB)
  const maxSizeMB = 10;
  if (file.size > maxSizeMB * 1024 * 1024) {
    showAlert(`Ukuran file terlalu besar! Maksimal ${maxSizeMB}MB.`, "error");
    resetUploadState();
    return;
  }

  const calculatedSize = (file.size / (1024 * 1024)).toFixed(2) + " MB";

  // Update Tampilan Info File
  if (fileName) fileName.innerText = file.name;
  if (fileSize) fileSize.innerText = calculatedSize;

  if (fileInfo) {
    fileInfo.textContent = `${file.name} (${calculatedSize})`;
    fileInfo.hidden = false;
    fileInfo.classList.remove("hidden");
  }

  // Set Preview Gambar via ObjectURL
  if (previewImage) {
    if (currentBlobUrl) URL.revokeObjectURL(currentBlobUrl);
    currentBlobUrl = URL.createObjectURL(file);
    previewImage.src = currentBlobUrl;
    previewImage.hidden = false;
    previewImage.classList.remove("hidden");

    if (uploadPlaceholder) {
      uploadPlaceholder.hidden = true;
      uploadPlaceholder.classList.add("hidden");
    }
  }

  // Tampilkan Tombol Hapus
  if (removeFileBtn) {
    removeFileBtn.hidden = false;
    removeFileBtn.classList.remove("hidden");
  }

  // Reset Progress Bar
  if (progressFill) progressFill.style.width = "0%";
  if (progressText) progressText.textContent = "0%";
}

export function resetUploadState() {
  const fileInput = document.getElementById("imageInput");
  const previewImage = document.getElementById("previewImage");
  const uploadPlaceholder = document.getElementById("uploadPlaceholder") || document.querySelector(".upload-placeholder");
  const fileInfo = document.getElementById("fileInfo");
  const fileName = document.getElementById("fileName");
  const fileSize = document.getElementById("fileSize");
  const removeFileBtn = document.getElementById("removeFileBtn");
  const progressWrapper = document.getElementById("progressWrapper");
  const progressFill = document.getElementById("progressFill");
  const progressText = document.getElementById("progressText");

  // Reset File Input Value
  if (fileInput) fileInput.value = "";

  // Hapus Memory Blob Preview
  if (currentBlobUrl) {
    URL.revokeObjectURL(currentBlobUrl);
    currentBlobUrl = null;
  }

  // Sembunyikan Gambar Preview
  if (previewImage) {
    previewImage.src = "";
    previewImage.hidden = true;
    previewImage.classList.add("hidden");
  }

  // Kembalikan Tampilan Placeholder
  if (uploadPlaceholder) {
    uploadPlaceholder.hidden = false;
    uploadPlaceholder.classList.remove("hidden");
  }

  // Sembunyikan Teks File Info & Tombol Hapus
  if (fileInfo) {
    fileInfo.hidden = true;
    fileInfo.classList.add("hidden");
  }
  if (fileName) fileName.innerText = "";
  if (fileSize) fileSize.innerText = "";

  if (removeFileBtn) {
    removeFileBtn.hidden = true;
    removeFileBtn.classList.add("hidden");
  }

  // Reset Progress Bar Elements
  if (progressWrapper) progressWrapper.style.display = "none";
  if (progressFill) progressFill.style.width = "0%";
  if (progressText) progressText.textContent = "0%";

  // Sembunyikan Hasil Ekstraksi
  const resultCard = document.getElementById("resultCard");
  if (resultCard) {
    resultCard.classList.add("hidden");
  }
}
