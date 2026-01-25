#!/usr/bin/env python3
"""
Script de verificación de instalación
Verifica que todas las dependencias estén correctamente instaladas
"""
import sys
import importlib

def check_python_version():
    """Verifica la versión de Python"""
    version = sys.version_info
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("✗ Se requiere Python 3.8 o superior")
        return False
    return True

def check_package(package_name, import_name=None):
    """Verifica si un paquete está instalado"""
    if import_name is None:
        import_name = package_name
    
    try:
        module = importlib.import_module(import_name)
        version = getattr(module, '__version__', 'unknown')
        print(f"✓ {package_name}: {version}")
        return True
    except ImportError:
        print(f"✗ {package_name}: NO INSTALADO")
        return False
    except Exception as e:
        print(f"✗ {package_name}: ERROR - {e}")
        return False

def check_opencv():
    """Verifica OpenCV específicamente"""
    try:
        import cv2
        print(f"✓ opencv-python: {cv2.__version__}")
        
        # Verificar funcionalidad básica
        import numpy as np
        test_img = np.zeros((100, 100, 3), dtype=np.uint8)
        if test_img is not None:
            print("  ✓ OpenCV funciona correctamente")
        return True
    except ImportError:
        print("✗ opencv-python: NO INSTALADO")
        return False
    except Exception as e:
        print(f"✗ opencv-python: ERROR - {e}")
        return False

def check_mediapipe():
    """Verifica MediaPipe específicamente"""
    try:
        import mediapipe as mp
        print(f"✓ mediapipe: {mp.__version__}")
        
        # Verificar que se puede inicializar Pose
        mp_pose = mp.solutions.pose
        print("  ✓ MediaPipe Pose disponible")
        return True
    except ImportError:
        print("✗ mediapipe: NO INSTALADO")
        print("  Sugerencia: En Windows, instala Visual C++ Build Tools")
        print("  O usa WSL (recomendado)")
        return False
    except Exception as e:
        print(f"✗ mediapipe: ERROR - {e}")
        return False

def check_fastapi():
    """Verifica FastAPI específicamente"""
    try:
        import fastapi
        import uvicorn
        print(f"✓ fastapi: {fastapi.__version__}")
        print(f"✓ uvicorn: {uvicorn.__version__}")
        return True
    except ImportError as e:
        print(f"✗ FastAPI/Uvicorn: NO INSTALADO - {e}")
        return False

def check_project_structure():
    """Verifica la estructura del proyecto"""
    import os
    from pathlib import Path
    
    required_dirs = [
        'backend/app',
        'backend/app/api',
        'backend/app/core',
        'backend/app/models',
        'backend/app/services',
        'backend/app/services/vision',
        'backend/app/services/biomechanics',
        'frontend'
    ]
    
    required_files = [
        'backend/app/main.py',
        'backend/app/api/routes.py',
        'backend/app/core/config.py',
        'backend/app/models/schemas.py',
        'backend/app/services/vision/hold_detector.py',
        'backend/app/services/vision/pose_tracker.py',
        'backend/app/services/biomechanics/analyzer.py',
        'frontend/index.html',
        'frontend/app.js',
        'requirements.txt'
    ]
    
    print("\n📁 Verificando estructura del proyecto...")
    all_ok = True
    
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✓ {dir_path}/")
        else:
            print(f"✗ {dir_path}/ - NO ENCONTRADO")
            all_ok = False
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} - NO ENCONTRADO")
            all_ok = False
    
    return all_ok

def main():
    """Función principal"""
    print("=" * 60)
    print("🔍 Verificación de Instalación")
    print("Sistema de Análisis Biomecánico - Escalada de Velocidad")
    print("=" * 60)
    
    results = []
    
    print("\n🐍 Verificando Python...")
    results.append(check_python_version())
    
    print("\n📦 Verificando paquetes principales...")
    results.append(check_package("fastapi"))
    results.append(check_fastapi())
    results.append(check_package("pydantic"))
    results.append(check_package("numpy"))
    
    print("\n👁️ Verificando paquetes de visión por computadora...")
    results.append(check_opencv())
    results.append(check_mediapipe())
    
    print("\n📁 Verificando estructura del proyecto...")
    results.append(check_project_structure())
    
    print("\n" + "=" * 60)
    if all(results):
        print("✅ ¡TODAS LAS VERIFICACIONES PASARON!")
        print("\nPuedes iniciar el servidor con:")
        print("  cd backend")
        print("  python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    else:
        print("❌ ALGUNAS VERIFICACIONES FALLARON")
        print("\nRevisa los errores arriba y consulta INSTALL.md para ayuda")
        sys.exit(1)
    print("=" * 60)

if __name__ == "__main__":
    main()
