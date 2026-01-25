@echo off
REM Script de instalación automática para Windows
REM Ejecutar desde el directorio raíz del proyecto

echo ==========================================
echo Instalacion Automatica - Windows
echo Sistema de Analisis Biomecanico
echo ==========================================
echo.

REM Verificar que estamos en el directorio correcto
if not exist "requirements.txt" (
    echo Error: No se encontro requirements.txt
    echo Por favor ejecuta este script desde el directorio raiz del proyecto
    pause
    exit /b 1
)

echo Paso 1: Verificando Python...
python --version
if errorlevel 1 (
    echo ERROR: Python no esta instalado o no esta en PATH
    echo Por favor instala Python desde https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo Paso 2: Creando entorno virtual...
if exist "venv" (
    echo El entorno virtual ya existe. ¿Deseas recrearlo? (S/N)
    set /p response=
    if /i "%response%"=="S" (
        rmdir /s /q venv
        python -m venv venv
    )
) else (
    python -m venv venv
)

echo.
echo Paso 3: Activando entorno virtual...
call venv\Scripts\activate.bat

echo.
echo Paso 4: Actualizando pip...
python -m pip install --upgrade pip setuptools wheel

echo.
echo Paso 5: Instalando dependencias de Python...
echo Esto puede tardar varios minutos...
echo.
echo Instalando FastAPI y Uvicorn...
pip install fastapi uvicorn[standard] python-multipart
echo.
echo Instalando NumPy...
pip install numpy
echo.
echo Instalando OpenCV...
pip install opencv-python
echo.
echo Instalando MediaPipe...
echo NOTA: MediaPipe puede tardar mucho tiempo en Windows
echo Si falla, considera usar WSL (recomendado)
pip install mediapipe
echo.
echo Instalando Pydantic...
pip install pydantic
echo.
echo Instalando python-dotenv...
pip install python-dotenv

echo.
echo Paso 6: Verificando instalacion...
python verify_installation.py

echo.
echo ==========================================
echo ¡Instalacion completada!
echo ==========================================
echo.
echo Para iniciar el servidor:
echo   1. Activa el entorno virtual: venv\Scripts\activate
echo   2. Ve al directorio backend: cd backend
echo   3. Inicia el servidor: python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
echo.
echo O usa el script: start_backend.bat
echo.
pause
