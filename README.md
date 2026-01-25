# Sistema de Análisis Biomecánico para Escalada de Velocidad

Sistema completo para analizar el rendimiento en escalada de velocidad mediante visión por computadora y análisis biomecánico.

## 🏗️ Estructura del Proyecto

```
AnalisisVelocidadIA/
├── backend/
│   └── app/
│       ├── __init__.py
│       ├── main.py                 # Aplicación FastAPI principal
│       ├── api/
│       │   ├── __init__.py
│       │   └── routes.py           # Endpoints de la API
│       ├── core/
│       │   ├── __init__.py
│       │   └── config.py           # Configuración de la aplicación
│       ├── models/
│       │   ├── __init__.py
│       │   └── schemas.py           # Modelos Pydantic
│       └── services/
│           ├── __init__.py
│           ├── vision/
│           │   ├── __init__.py
│           │   ├── hold_detector.py      # Detección de presas rojas
│           │   ├── pose_tracker.py       # Tracking de pose con MediaPipe
│           │   └── video_overlay.py      # Generación de video con overlay
│           └── biomechanics/
│               ├── __init__.py
│               └── analyzer.py           # Análisis biomecánico
├── frontend/
│   ├── index.html                  # Interfaz web principal
│   ├── style.css                   # Estilos CSS
│   └── app.js                      # Lógica JavaScript del frontend
├── uploads/                        # Videos subidos (se crea automáticamente)
├── processed/                      # Videos procesados (se crea automáticamente)
├── requirements.txt                 # Dependencias de Python
└── README.md                       # Este archivo
```

## 🚀 Instalación

### ⚠️ Importante: Recomendación de Entorno

**Recomendamos usar WSL (Windows Subsystem for Linux) con Ubuntu** para mejor compatibilidad con MediaPipe y OpenCV.

### Instalación Rápida

**Para WSL/Ubuntu (Recomendado):**
```bash
chmod +x install_wsl.sh
./install_wsl.sh
```

**Para Windows Nativo:**
```bash
install_windows.bat
```

### Instalación Manual

Para instrucciones detalladas paso a paso, consulta **[INSTALL.md](INSTALL.md)** que incluye:
- Guía completa para WSL/Ubuntu
- Guía completa para Windows nativo
- Solución de problemas comunes
- Verificación de instalación

### Verificar Instalación

Después de instalar, ejecuta:
```bash
python verify_installation.py
# o en Windows:
python verify_installation.py
```

### Requisitos Previos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- **Para Windows:** Visual C++ Build Tools (requerido para MediaPipe)

### 🔧 Configuración de WSL en Cursor

Si usas **Cursor** (o VS Code) con WSL, el proyecto incluye configuración automática:

1. **El terminal se abrirá automáticamente en WSL** con la ruta correcta del proyecto
2. **Tareas predefinidas** para iniciar el backend y ejecutar comandos comunes
3. **Configuración de depuración** lista para usar

**Para más detalles:** Consulta [`.vscode/README_WSL.md`](.vscode/README_WSL.md)

**Uso rápido:**
- Presiona `` Ctrl + ` `` para abrir el terminal en WSL
- Usa `Ctrl + Shift + P` → "Tasks: Run Task" para ejecutar tareas predefinidas

## 🏃 Uso

### Gestión de Entornos Virtuales

**Ver entornos virtuales disponibles:**

El proyecto incluye un entorno virtual en `venv/`. Para verificar si existe y qué paquetes tiene instalados:

```bash
# Verificar si el entorno virtual existe
ls -la venv/

# Ver paquetes instalados (sin activar)
venv/bin/pip list  # En WSL/Linux
venv\Scripts\pip list  # En Windows
```

**Activar el entorno virtual:**

```bash
# Desde el directorio raíz del proyecto
source venv/bin/activate  # En WSL/Linux
# o
venv\Scripts\activate     # En Windows
```

Verás `(venv)` al inicio de tu prompt cuando esté activado.

**Desactivar el entorno virtual:**

```bash
deactivate
```

### Iniciar el Backend

**Opción 1: Usar el script de inicio (Recomendado)**

Para **WSL/Linux:**
```bash
chmod +x start_backend.sh
./start_backend.sh
```

Para **Windows:**
```bash
start_backend.bat
```

**Opción 2: Inicio manual**

1. **Activar el entorno virtual:**
   ```bash
   # Desde el directorio raíz del proyecto
   source venv/bin/activate  # En WSL/Linux
   # o
   venv\Scripts\activate      # En Windows
   ```
   
   Verificarás que está activado porque verás `(venv)` al inicio de tu prompt.

2. **Navegar al directorio del backend:**
   ```bash
   cd backend
   ```

3. **Iniciar el servidor FastAPI:**
   ```bash
   # En WSL/Linux
   python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   
   # En Windows
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   
   **Nota:** Si el comando `uvicorn` no se encuentra, asegúrate de que el entorno virtual esté activado y que las dependencias estén instaladas (`pip install -r requirements.txt`).

El servidor estará disponible en `http://localhost:8000`

**Documentación de la API:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Iniciar el Frontend

**Opción 1: Servir con un servidor HTTP (Recomendado)**

En una **nueva terminal**, ejecuta:
```bash
cd frontend
python3 -m http.server 8080
```

Luego abre `http://localhost:8080` en tu navegador.

**Opción 2: Abrir directamente el archivo HTML**

Puedes abrir `frontend/index.html` directamente en el navegador, pero algunas funcionalidades pueden estar limitadas por políticas CORS.

### Usar la Aplicación

1. **Asegúrate de que el backend esté corriendo** en `http://localhost:8000`
2. **Abre el frontend** en `http://localhost:8080` (o el archivo HTML directamente)
3. **Usar la interfaz:**
   - Ingresar el peso del escalador (kg)
   - Seleccionar un archivo de video
   - Hacer clic en "Subir y Analizar"
   - Esperar a que se complete el análisis
   - Ver los resultados en el dashboard

## 📡 Endpoints de la API

### `POST /api/upload`
Sube un archivo de video para análisis.

**Request:**
- `file`: Archivo de video (multipart/form-data)

**Response:**
```json
{
  "video_id": "uuid",
  "filename": "video.mp4",
  "message": "Video uploaded successfully",
  "uploaded_at": "2024-01-01T12:00:00"
}
```

### `GET /api/analyze/{video_id}`
Inicia el análisis del video y devuelve los resultados.

**Query Parameters:**
- `climber_weight` (float): Peso del escalador en kg (default: 70.0)

**Response:**
```json
{
  "video_id": "uuid",
  "total_duration": 10.5,
  "reaction_time": 0.234,
  "total_time": 10.5,
  "frame_count": 315,
  "fps": 30.0,
  "frames": [...],
  "steps": [...],
  "forces": [...],
  "power_curve": [...],
  "climber_weight": 70.0,
  "analyzed_at": "2024-01-01T12:00:00"
}
```

### `GET /api/overlay/{video_id}`
Devuelve el video procesado con el esqueleto y métricas dibujadas.

**Response:**
- Archivo de video MP4

### `GET /api/videos`
Lista todos los videos subidos.

## 🔬 Funcionalidades

### Módulo de Visión
- **Detección de Presas Rojas**: Usa thresholding HSV para detectar presas rojas en el primer frame
- **Tracking de Pose**: MediaPipe Pose para rastrear 33 landmarks corporales
- **Cálculo de Centro de Masas**: Calculado a partir de los landmarks con pesos de segmentos corporales
- **Suavizado de Datos**: Filtro de media móvil para suavizar el CoM

### Módulo Biomecánico
- **Tiempo de Reacción**: Basado en la aceleración del CoM que cruza un umbral
- **Tiempos por Paso**: Detecta cuando el CoM cruza umbrales de presas
- **Estimación de Fuerzas**: `F = m * (g + a)` distribuida según proximidad del CoM a los apoyos activos
- **Curva de Potencia**: `P = F * v` calculada para cada frame

## 🛠️ Tecnologías Utilizadas

### Backend
- **FastAPI**: Framework web moderno y rápido
- **OpenCV**: Procesamiento de video e imágenes
- **MediaPipe**: Detección y tracking de pose humana
- **Pydantic**: Validación de datos y modelos
- **NumPy**: Cálculos numéricos

### Frontend
- **HTML5/CSS3**: Estructura y estilos
- **JavaScript (Vanilla)**: Lógica del cliente
- **Tailwind CSS**: Framework CSS utility-first
- **Chart.js**: Gráficas interactivas

## 📝 Notas Técnicas

- Los videos se procesan frame por frame
- El análisis puede tardar varios minutos dependiendo de la duración del video
- Los videos procesados se guardan en `processed/` para reutilización
- El sistema detecta automáticamente las presas rojas usando umbrales HSV configurables

## 🔧 Configuración

Los parámetros de configuración se encuentran en `backend/app/core/config.py`:

- `MIN_DETECTION_CONFIDENCE`: Confianza mínima para detección de pose (0.5)
- `MIN_TRACKING_CONFIDENCE`: Confianza mínima para tracking de pose (0.5)
- `DEFAULT_CLIMBER_WEIGHT`: Peso por defecto del escalador (70 kg)
- `SMOOTHING_WINDOW`: Ventana para filtro de media móvil (5 frames)
- `RED_HOLD_LOWER_HSV` / `RED_HOLD_UPPER_HSV`: Umbrales HSV para detección de presas rojas

## 📄 Licencia

Este proyecto es de código abierto y está disponible para uso educativo y de investigación.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o pull request para sugerencias y mejoras.
