#!/bin/bash
# Script para instalar ffmpeg (requerido para conversión de video a MP4 con H.264)

echo "=========================================="
echo "Instalando ffmpeg para conversión de video"
echo "=========================================="
echo ""

# Verificar si ya está instalado
if command -v ffmpeg &> /dev/null; then
    echo "✓ ffmpeg ya está instalado"
    ffmpeg -version | head -n 1
    exit 0
fi

echo "Instalando ffmpeg..."
sudo apt update
sudo apt install -y ffmpeg

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ ffmpeg instalado correctamente"
    ffmpeg -version | head -n 1
    echo ""
    echo "Ahora los videos se convertirán automáticamente a MP4 con H.264"
else
    echo ""
    echo "✗ Error al instalar ffmpeg"
    echo "Intenta instalarlo manualmente: sudo apt install ffmpeg"
    exit 1
fi
