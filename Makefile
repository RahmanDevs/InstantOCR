.PHONY: help init install run run-frontend run-backend migrate test clean check

PYTHON := .venv/bin/python
PIP := .venv/bin/pip
DJANGO_MANAGE := $(PYTHON) app/manage.py
UVICORN := .venv/bin/uvicorn

# ANSI Colors
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
CYAN := \033[0;36m
NC := \033[0m # No Color

help: ## Tampilkan daftar panduan perintah Makefile
	@echo "$(BLUE)=============================================================$(NC)"
	@echo "$(CYAN)⚡ InstantOCR - Automation & Development CLI$(NC)"
	@echo "$(BLUE)=============================================================$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-18s$(NC) %s\n", $$1, $$2}'
	@echo ""

init: ## Inisialisasi environment (.venv, requirements, .env, migrations)
	@echo "$(GREEN)--> [1/4] Menyiapkan Virtual Environment (.venv)...$(NC)"
	@if [ ! -d .venv ]; then \
		python3 -m venv --system-site-packages .venv; \
	fi
	@echo "$(GREEN)--> [2/4] Menginstall dan memperbarui dependensi...$(NC)"
	@$(PIP) install -r requirements.txt
	@echo "$(GREEN)--> [3/4] Menyiapkan environment file (.env)...$(NC)"
	@if [ ! -f .env ]; then \
		cp env.example .env; \
		echo "$(YELLOW)File .env berhasil dibuat dari env.example.$(NC)"; \
	fi
	@echo "$(GREEN)--> [4/4] Menjalankan migrasi database Django...$(NC)"
	@$(DJANGO_MANAGE) makemigrations
	@$(DJANGO_MANAGE) migrate
	@echo "$(GREEN)✔ Inisialisasi InstantOCR selesai! Jalankan 'make run' untuk mulai.$(NC)"

install: ## Install semua dependensi dari requirements.txt
	@$(PIP) install -r requirements.txt

migrate: ## Jalankan migrasi schema database Django
	@$(DJANGO_MANAGE) makemigrations
	@$(DJANGO_MANAGE) migrate

run-frontend: ## Jalankan Django Server (Frontend) di port 8000
	@echo "$(GREEN)--> Menjalankan Django Frontend di http://127.0.0.1:8000...$(NC)"
	@$(DJANGO_MANAGE) runserver 127.0.0.1:8000

run-backend: ## Jalankan FastAPI Server (Backend OCR) di port 8001
	@echo "$(GREEN)--> Menjalankan FastAPI OCR Engine di http://127.0.0.1:8001...$(NC)"
	@$(PYTHON) -m uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload

run: ## Jalankan Backend (FastAPI :8001) dan Frontend (Django :8000) bersamaan
	@echo "$(CYAN)--> Menjalankan InstantOCR (Django :8000 & FastAPI :8001)...$(NC)"
	@trap 'kill 0' EXIT INT TERM; \
	$(DJANGO_MANAGE) runserver 127.0.0.1:8000 & \
	$(PYTHON) -m uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload & \
	wait

test: ## Jalankan seluruh test suite unit & integrasi OCR
	@echo "$(GREEN)--> Menjalankan Test Suite (Pytest)...$(NC)"
	@PYTHONPATH=. $(PYTHON) -m pytest tests/test_ocr_suite.py -v

check: ## Periksa integritas sistem Django dan modul Python
	@echo "$(GREEN)--> Memeriksa Django...$(NC)"
	@$(DJANGO_MANAGE) check
	@echo "$(GREEN)--> Memeriksa modul dependensi...$(NC)"
	@$(PYTHON) -c "import fastapi, uvicorn, sqlalchemy, pydantic_settings, openpyxl, pandas; print('Core modules OK!')"

clean: ## Bersihkan cache pycache, bytecode .pyc, dan temporary test uploads
	@echo "$(YELLOW)--> Membersihkan temporary files & __pycache__...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find app/project/uploads/ -type f ! -name ".gitkeep" -delete 2>/dev/null || true
	@echo "$(GREEN)✔ Selesai dibersihkan.$(NC)"
