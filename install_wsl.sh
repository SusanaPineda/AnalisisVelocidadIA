#!/bin/bash
# Script de instalación automática para WSL/Ubuntu
# Ejecutar desde el directorio raíz del proyecto

set -e  # Salir si hay algún error

echo "=========================================="
echo "Instalación Automática - WSL/Ubuntu"
echo "Sistema de Análisis Biomecánico"
echo "=========================================="
echo ""

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar que estamos en el directorio correcto
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: No se encontró requirements.txt${NC}"
    echo "Por favor ejecuta este script desde el directorio raíz del proyecto"
    exit 1
fi

echo -e "${YELLOW}Paso 1: Actualizando sistema...${NC}"
sudo apt update
sudo apt upgrade -y

echo -e "${YELLOW}Paso 2: Instalando Python y herramientas...${NC}"
sudo apt install python3 python3-pip python3-venv build-essential -y

echo -e "${YELLOW}Paso 3: Instalando dependencias del sistema para OpenCV y MediaPipe...${NC}"
# Nota: libgl1-mesa-glx fue reemplazado por libgl1 en versiones modernas de Ubuntu
sudo apt install libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 -y

echo -e "${YELLOW}Paso 4: Creando entorno virtual...${NC}"
if [ -d "venv" ]; then
    echo "El entorno virtual ya existe. ¿Deseas recrearlo? (s/n)"
    read -r response
    if [[ "$response" =~ ^[Ss]$ ]]; then
        rm -rf venv
        python3 -m venv venv
    fi
else
    python3 -m venv venv
fi

echo -e "${YELLOW}Paso 5: Activando entorno virtual...${NC}"
source venv/bin/activate

echo -e "${YELLOW}Paso 6: Actualizando pip...${NC}"
pip install --upgrade pip setuptools wheel

echo -e "${YELLOW}Paso 7: Instalando dependencias de Python...${NC}"
echo "Esto puede tardar varios minutos..."
pip install -r requirements.txt

echo -e "${YELLOW}Paso 8: Verificando instalación...${NC}"
python3 verify_installation.py

echo ""
echo -e "${GREEN}=========================================="
echo "¡Instalación completada!"
echo "==========================================${NC}"
echo ""
echo "Para iniciar el servidor:"
echo "  1. Activa el entorno virtual: source venv/bin/activate"
echo "  2. Ve al directorio backend: cd backend"
echo "  3. Inicia el servidor: python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "O usa el script: ./start_backend.sh"
echo ""
