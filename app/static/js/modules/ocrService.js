import { showAlert } from "./alertHandler.js";

export function initOcrService() {
  const form = document.getElementById("ocrForm");
  const convertBtn = document.getElementById("convertBtn") || document.querySelector(".convert-btn");
  const fileInput = document.getElementById("imageInput");
  const progressWrapper = document.getElementById("progressWrapper");
  const progressFill = document.getElementById("progressFill");
  const progressText = document.getElementById("progressText");

  // Result Card Elements
  const resultCard = document.getElementById("resultCard");
  const resultTextarea = document.getElementById("resultTextarea");
  const resultStats = document.getElementById("resultStats");
  const copyResultBtn = document.getElementById("copyResultBtn");
  const copyBtnText = document.getElementById("copyBtnText");
  const quickDownloadBtns = document.querySelectorAll(".quick-dl-btn");

  let lastExtractionData = null;

  // Dynamic Backend Host resolution (supports localhost, 127.0.0.1, or custom window config)
  const backendHost = window.FASTAPI_BASE_URL || `${window.location.protocol}//${window.location.hostname || "127.0.0.1"}:8001`;
  const FASTAPI_PROCESS_URL = `${backendHost}/api/v1/ocr/process`;
  const FASTAPI_EXPORT_URL = `${backendHost}/api/v1/ocr/export`;
  const FASTAPI_CONVERT_TEXT_URL = `${backendHost}/api/v1/ocr/convert-text`;

  const triggerDownloadFromBlob = (blob, filename) => {
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = downloadUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(downloadUrl);
  };

  const handleProcessOCR = async (e) => {
    if (e) e.preventDefault();

    const file = fileInput?.files[0];
    const selectedFormat = document.querySelector('input[name="format"]:checked')?.value || "txt";

    if (!file) {
      showAlert("Pilih atau tempelkan (Ctrl+V) file gambar terlebih dahulu!", "warning");
      return;
    }

    // 1. Siapkan Payload FormData
    const formData = new FormData();
    formData.append("file", file);
    formData.append("format", selectedFormat);

    // UI Feedback: Disable button & tampilkan status
    convertBtn.disabled = true;
    const originalBtnText = convertBtn.innerHTML;
    convertBtn.innerHTML = `<i class="ri-loader-4-line ri-spin"></i> Memproses OCR...`;

    if (progressWrapper) progressWrapper.style.display = "block";
    if (progressFill) progressFill.style.width = "0%";
    if (progressText) progressText.textContent = "0%";

    // Simulasi Progress Bar Responsif
    let progress = 12;
    if (progressFill) progressFill.style.width = `${progress}%`;
    if (progressText) progressText.textContent = `${progress}%`;

    const progressInterval = setInterval(() => {
      if (progress < 85) {
        progress += Math.floor(Math.random() * 8) + 4;
        if (progressFill) progressFill.style.width = `${progress}%`;
        if (progressText) progressText.textContent = `${progress}%`;
      }
    }, 200);

    try {
      // 2. Kirim gambar ke FastAPI Backend OCR Engine
      const response = await fetch(FASTAPI_PROCESS_URL, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Gagal memproses file pada backend OCR.");
      }

      const data = await response.json();
      lastExtractionData = data;

      // Update progress indikator
      if (progressFill) progressFill.style.width = "90%";
      if (progressText) progressText.textContent = "90%";
      convertBtn.innerHTML = `<i class="ri-download-2-line"></i> Mengunduh Dokumen (${selectedFormat.toUpperCase()})...`;

      // 3. Ambil file hasil konversi yang valid (binary docx/pdf/xlsx/csv/json/txt)
      const exportUrl = `${FASTAPI_EXPORT_URL}?id=${data.id}&format=${selectedFormat}`;
      const exportResponse = await fetch(exportUrl);

      if (!exportResponse.ok) {
        throw new Error("Gagal mengunduh file format yang dipilih dari server.");
      }

      const blob = await exportResponse.blob();

      // Deteksi filename dari header atau susun nama file otomatis
      const disposition = exportResponse.headers.get("Content-Disposition");
      let downloadFilename = `hasil_ocr_${Date.now()}.${selectedFormat}`;
      if (disposition && disposition.indexOf("filename=") !== -1) {
        const filenameMatch = disposition.match(/filename="?([^";]+)"?/);
        if (filenameMatch && filenameMatch[1]) {
          downloadFilename = filenameMatch[1];
        }
      }

      // 4. Unduh file fisik ke komputer pengguna
      triggerDownloadFromBlob(blob, downloadFilename);

      // Selesaikan Progress
      clearInterval(progressInterval);
      if (progressFill) progressFill.style.width = "100%";
      if (progressText) progressText.textContent = "100%";

      // 5. Tampilkan Hasil Ekstraksi pada Result Card
      if (resultCard && resultTextarea) {
        resultTextarea.value = data.text || "(Tidak ada teks yang terdeteksi dalam gambar)";
        const words = (data.text || "").trim().split(/\s+/).filter(Boolean).length;
        const chars = (data.text || "").length;
        if (resultStats) {
          resultStats.textContent = `• ${chars} karakter, ${words} kata`;
        }
        resultCard.classList.remove("hidden");
      }

      showAlert(`Berhasil! Teks diekstrak dan dokumen '${downloadFilename}' terunduh.`, "success", 5000);
    } catch (error) {
      clearInterval(progressInterval);
      console.error("Error OCR Service:", error);
      showAlert(`Terjadi kesalahan: ${error.message}`, "error", 6000);
    } finally {
      // Reset UI State secara halus
      setTimeout(() => {
        convertBtn.disabled = false;
        convertBtn.innerHTML = originalBtnText;
        if (progressWrapper) progressWrapper.style.display = "none";
        if (progressFill) progressFill.style.width = "0%";
      }, 1400);
    }
  };

  // Event Listener: Salin Hasil Teks ke Clipboard
  if (copyResultBtn && resultTextarea) {
    copyResultBtn.addEventListener("click", async () => {
      const textToCopy = resultTextarea.value;
      if (!textToCopy) return;

      try {
        await navigator.clipboard.writeText(textToCopy);
        const originalText = copyBtnText ? copyBtnText.textContent : "Salin Teks";
        if (copyBtnText) copyBtnText.textContent = "Tersalin!";
        copyResultBtn.classList.add("text-emerald-600", "bg-emerald-50");

        setTimeout(() => {
          if (copyBtnText) copyBtnText.textContent = originalText;
          copyResultBtn.classList.remove("text-emerald-600", "bg-emerald-50");
        }, 2000);

        showAlert("Teks hasil OCR berhasil disalin ke clipboard!", "info", 2500);
      } catch (err) {
        console.error("Failed to copy text: ", err);
        showAlert("Gagal menyalin teks ke clipboard.", "warning");
      }
    });
  }

  // Event Listener: Unduh Ulang Cepat dalam Format Lain (Quick Export)
  quickDownloadBtns.forEach((btn) => {
    btn.addEventListener("click", async () => {
      const targetFormat = btn.dataset.format;
      const currentText = resultTextarea?.value || lastExtractionData?.text;

      if (!currentText) {
        showAlert("Belum ada teks OCR untuk diunduh.", "warning");
        return;
      }

      try {
        btn.disabled = true;
        btn.classList.add("opacity-50");

        let exportResponse;
        if (lastExtractionData && lastExtractionData.id) {
          exportResponse = await fetch(`${FASTAPI_EXPORT_URL}?id=${lastExtractionData.id}&format=${targetFormat}`);
        } else {
          exportResponse = await fetch(FASTAPI_CONVERT_TEXT_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              text: currentText,
              format: targetFormat,
              filename: "instantocr_export",
            }),
          });
        }

        if (!exportResponse.ok) {
          throw new Error("Gagal mengunduh format ini dari server.");
        }

        const blob = await exportResponse.blob();
        const disposition = exportResponse.headers.get("Content-Disposition");
        let dlName = `hasil_ocr_${Date.now()}.${targetFormat}`;
        if (disposition && disposition.indexOf("filename=") !== -1) {
          const match = disposition.match(/filename="?([^";]+)"?/);
          if (match && match[1]) dlName = match[1];
        }

        triggerDownloadFromBlob(blob, dlName);
        showAlert(`Format ${targetFormat.toUpperCase()} berhasil diunduh!`, "success", 3000);
      } catch (err) {
        showAlert(`Gagal unduh ${targetFormat.toUpperCase()}: ${err.message}`, "error");
      } finally {
        btn.disabled = false;
        btn.classList.remove("opacity-50");
      }
    });
  });

  if (form) {
    form.addEventListener("submit", handleProcessOCR);
  }
  if (convertBtn) {
    convertBtn.addEventListener("click", handleProcessOCR);
  }
}
