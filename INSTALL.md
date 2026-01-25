# Guía de Instalación - Sistema de Análisis Biomecánico

Esta guía te ayudará a instalar el sistema tanto en Windows nativo como en WSL (Ubuntu).

## 🎯 Recomendación: WSL con Ubuntu

**Recomendamos usar WSL con Ubuntu** porque:
- MediaPipe y OpenCV funcionan mejor en Linux
- Menos problemas de compatibilidad
- Mejor rendimiento para procesamiento de video
- Instalación más sencilla

---

## 📦 Opción 1: Instalación en WSL (Ubuntu) - RECOMENDADO

### Paso 1: Instalar WSL y Ubuntu

Si aún no tienes WSL instalado:

1. **Abrir PowerShell como Administrador** y ejecutar:
   ```powershell
   wsl --install
   ```

2. Reiniciar el equipo cuando se solicite

3. Después del reinicio, se abrirá Ubuntu automáticamente. Configura tu usuario y contraseña.

### Paso 2: Actualizar el sistema Ubuntu

```bash
sudo apt update
sudo apt upgrade -y
```

### Paso 3: Instalar Python y herramientas necesarias

```bash
# Instalar Python 3.10 o superior
sudo apt install python3 python3-pip python3-venv -y

# Instalar herramientas de compilación (necesarias para algunas dependencias)
sudo apt install build-essential -y

# Instalar dependencias del sistema para OpenCV y MediaPipe
# Nota: libgl1-mesa-glx fue reemplazado por libgl1 en versiones modernas de Ubuntu
sudo apt install libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 -y
```

### Paso 4: Navegar al proyecto en WSL

```bash
# Si el proyecto está en Windows, acceder desde WSL
cd /mnt/c/Users/Alvaro/Documents/AnalisisVelocidadIA

# O clonar/copiar el proyecto dentro de WSL
# cd ~
# mkdir proyectos
# cd proyectos
# (copiar archivos aquí)
```

### Paso 5: Crear entorno virtual

```bash
# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate
```

### Paso 6: Instalar dependencias

```bash
# Actualizar pip
pip install --upgrade pip

# Instalar dependencias
pip install -r requirements.txt
```

### Paso 7: Verificar instalación

```bash
# Ejecutar script de verificación
python3 verify_installation.py
```

### Paso 8: Iniciar el servidor

```bash
# Desde el directorio raíz del proyecto
cd backend
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Nota:** Para acceder desde Windows, usa `http://localhost:8000` en tu navegador.

---

## 🪟 Opción 2: Instalación en Windows Nativo

### Paso 1: Instalar Python

1. Descargar Python 3.10 o superior desde [python.org](https://www.python.org/downloads/)
2. **IMPORTANTE:** Marcar la opción "Add Python to PATH" durante la instalación
3. Verificar instalación:
   ```powershell
   python --version
   pip --version
   ```

### Paso 2: Instalar Visual C++ Build Tools (Requerido para MediaPipe)

MediaPipe requiere compiladores de C++ en Windows:

1. Descargar **Visual Studio Build Tools** desde: https://visualstudio.microsoft.com/downloads/
2. Instalar "Desktop development with C++" workload
3. O instalar **Microsoft C++ Build Tools**: https://visualstudio.microsoft.com/visual-cpp-build-tools/

### Paso 3: Navegar al proyecto

```powershell
cd C:\Users\Alvaro\Documents\AnalisisVelocidadIA
```

### Paso 4: Crear entorno virtual

```powershell
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
.\venv\Scripts\activate
```

### Paso 5: Actualizar pip y herramientas

```powershell
python -m pip install --upgrade pip setuptools wheel
```

### Paso 6: Instalar dependencias (puede tardar varios minutos)

```powershell
# Instalar dependencias una por una para identificar problemas
pip install fastapi uvicorn[standard] python-multipart
pip install numpy
pip install opencv-python
pip install mediapipe
pip install pydantic
pip install python-dotenv
```

**Nota:** Si MediaPipe falla, intenta:
```powershell
pip install mediapipe --no-cache-dir
```

### Paso 7: Verificar instalación

```powershell
python verify_installation.py
```

### Paso 8: Iniciar el servidor

```powershell
# Opción 1: Usar el script batch
.\start_backend.bat

# Opción 2: Manualmente
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🔍 Solución de Problemas Comunes

### Error: "No module named 'cv2'"

**Solución:**
```bash
# En WSL/Linux
pip install opencv-python-headless

# O reinstalar
pip uninstall opencv-python
pip install opencv-python
```

### Error: MediaPipe no se instala en Windows

**Solución:**
1. Asegúrate de tener Visual C++ Build Tools instalado
2. Intenta instalar con:
   ```powershell
   pip install mediapipe --no-cache-dir --verbose
   ```
3. Si persiste, usa WSL (recomendado)

### Error: "Package 'libgl1-mesa-glx' has no installation candidate"

**Solución:**
Este error ocurre en versiones modernas de Ubuntu (22.04+) donde `libgl1-mesa-glx` fue reemplazado por `libgl1`:
```bash
# Usar el paquete correcto para versiones modernas
sudo apt install libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 -y
```

### Error: "cannot execute: required file not found" al usar pip en venv

**Solución:**
Este error ocurre cuando el entorno virtual fue creado en Windows y se intenta usar en WSL (o viceversa). Los entornos virtuales no son portables entre sistemas operativos:
```bash
# Eliminar el entorno virtual existente
rm -rf venv

# Crear un nuevo entorno virtual desde WSL
python3 -m venv venv

# Activar el entorno virtual
source venv/bin/activate

# Actualizar pip
pip install --upgrade pip

# Instalar dependencias
pip install -r requirements.txt
```

**Nota importante:** Si trabajas con el proyecto desde Windows y WSL, crea entornos virtuales separados para cada sistema, o usa solo uno de los dos sistemas.

### Error: "Permission denied" en Linux/WSL

**Solución:**
```bash
# Dar permisos de ejecución a scripts
chmod +x start_backend.sh
chmod +x verify_installation.py
```

### Error: Puerto 8000 ya en uso

**Solución:**
```bash
# Cambiar puerto en el comando
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# O matar el proceso que usa el puerto
# En Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# En Linux/WSL:
lsof -ti:8000 | xargs kill -9
```

### Error al procesar videos: "Could not open video"

**Solución:**
- Verifica que el formato de video sea compatible (MP4, AVI, MOV, MKV)
- Asegúrate de que el archivo no esté corrupto
- En WSL, verifica permisos de lectura del archivo

---

## ✅ Verificación Final

Después de la instalación, verifica que todo funcione:

1. **Servidor iniciado correctamente:**
   - Abre `http://localhost:8000` en tu navegador
   - Deberías ver: `{"message": "Speed Climbing Biomechanical Analysis API", "version": "1.0.0"}`

2. **Documentación de la API:**
   - Abre `http://localhost:8000/docs` para Swagger UI

3. **Frontend:**
   - Abre `frontend/index.html` en tu navegador
   - O sirve con un servidor HTTP:
     ```bash
     # En WSL/Linux
     cd frontend
     python3 -m http.server 8080
     
     # En Windows PowerShell
     cd frontend
     python -m http.server 8080
     ```

---

## 📝 Notas Adicionales

### Acceso desde Windows a WSL

Si instalas en WSL pero quieres acceder desde Windows:
- El servidor en WSL escuchando en `0.0.0.0:8000` será accesible desde Windows en `http://localhost:8000`
- Los archivos en `/mnt/c/` son accesibles desde ambos sistemas

### Rendimiento

- WSL puede ser más lento para operaciones de I/O de archivos grandes
- Para mejor rendimiento, copia los videos dentro de WSL (`~/proyectos/AnalisisVelocidadIA/`)

### Actualizar Dependencias

```bash
# Activar entorno virtual primero
source venv/bin/activate  # WSL/Linux
# o
.\venv\Scripts\activate  # Windows

# Actualizar todas las dependencias
pip install --upgrade -r requirements.txt
```

---

## 🆘 ¿Necesitas Ayuda?

Si encuentras problemas durante la instalación:

1. Ejecuta `python verify_installation.py` para diagnóstico
2. Revisa los logs de error
3. Verifica que todas las dependencias del sistema estén instaladas
4. Considera usar WSL si estás en Windows y tienes problemas
