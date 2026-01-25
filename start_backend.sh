#!/bin/bash
# Script para iniciar el servidor FastAPI en WSL/Linux

# Verificar si el entorno virtual existe
if [ -d "venv" ]; then
    echo "Activando entorno virtual..."
    source venv/bin/activate
fi

echo "Iniciando servidor FastAPI..."
cd backend
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
