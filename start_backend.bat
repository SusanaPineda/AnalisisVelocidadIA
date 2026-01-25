@echo off
REM Script para iniciar el servidor FastAPI en Windows

REM Verificar si el entorno virtual existe
if exist "venv\Scripts\activate.bat" (
    echo Activando entorno virtual...
    call venv\Scripts\activate.bat
)

echo Iniciando servidor FastAPI...
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
