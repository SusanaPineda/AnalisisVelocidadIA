# Integración con Flutter — Backend de Análisis Biomecánico

**Sí, se puede.** El backend FastAPI es una API REST estándar y Flutter puede consumirla sin problema. Esta guía te indica qué hacer en backend y en la app móvil.

---

## 1. Resumen de la arquitectura

```
┌─────────────────────┐         HTTP/REST          ┌──────────────────────────┐
│   App Flutter       │  ───────────────────────►  │   Backend FastAPI        │
│   (iOS / Android)   │   • Subir video            │   (tu PC o servidor)     │
│                     │   • Analizar               │   • /api/upload          │
│                     │   • Descargar overlay      │   • /api/analyze/...     │
└─────────────────────┘                            └──────────────────────────┘
```

- **Backend:** Ya tienes CORS abierto y el servidor escuchando en `0.0.0.0` (accesible desde la red local o desde un servidor).
- **Flutter:** Solo necesita hacer peticiones HTTP (subida multipart, JSON, descarga de vídeo) a la URL base del API.

---

## 2. Qué hacer en el backend

### 2.1 Desarrollo (misma red que el móvil)

El backend ya usa `--host 0.0.0.0` en `start_backend.sh` / `start_backend.bat`, así que basta con:

1. Iniciar el backend en tu PC (WSL o Windows).
2. Obtener la **IP local** de tu máquina (ej. `192.168.1.10`).
3. En Flutter, usar como base: `http://192.168.1.10:8000` (puerto por defecto 8000).

**Obtener IP:**

- **WSL/Linux:** `hostname -I | awk '{print $1}'`
- **Windows (PowerShell):** `ipconfig` y buscar la IPv4 de tu adaptador (Wi‑Fi o Ethernet).

Asegúrate de que el móvil/emulador esté en la **misma red** que el PC.

### 2.2 Producción (app publicada)

Para una app en stores, el backend **debe estar en un servidor accesible por internet** y, recomendablemente, con **HTTPS**:

- Ejemplos: **Railway**, **Render**, **Fly.io**, **AWS**, **Google Cloud**, etc.
- Despliega el mismo proyecto FastAPI ( `uvicorn app.main:app --host 0.0.0.0 --port 8000` o el puerto que use el servicio).
- En Flutter, la base URL será la de tu servicio, ej. `https://tu-app.railway.app`.

CORS ya está con `allow_origins=["*"]`. En producción puedes restringir orígenes si lo necesitas (ver nota al final).

---

## 3. Qué hacer en Flutter

### 3.1 Dependencias

En `pubspec.yaml`:

```yaml
dependencies:
  flutter:
    sdk: flutter
  dio: ^5.4.0   # HTTP client con soporte multipart (recomendado)
  # opcional: http: ^1.1.0
```

### 3.2 Configuración de la URL base

Define la URL según entorno (desarrollo vs producción):

```dart
// lib/config/api_config.dart

class ApiConfig {
  static const bool isProduction = bool.fromEnvironment(
    'dart.vm.product',
    defaultValue: false,
  );

  /// Cambia esto: IP de tu PC en desarrollo, URL del servidor en producción.
  static const String baseUrl = isProduction
      ? 'https://tu-backend.railway.app'
      : 'http://192.168.1.10:8000';  // ¡Usa tu IP local!
}
```

### 3.3 Cliente API (ejemplo con Dio)

```dart
// lib/services/speed_climbing_api.dart

import 'package:dio/dio.dart';
import '../config/api_config.dart';

class SpeedClimbingApi {
  final Dio _dio = Dio(BaseOptions(
    baseUrl: ApiConfig.baseUrl,
    connectTimeout: const Duration(seconds: 30),
    receiveTimeout: const Duration(seconds: 120),
    sendTimeout: const Duration(seconds: 120),
  ));

  /// GET /health
  Future<Map<String, dynamic>> healthCheck() async {
    final r = await _dio.get('/health');
    return r.data as Map<String, dynamic>;
  }

  /// POST /api/upload — Subir video
  Future<VideoUploadResponse> uploadVideo(File videoFile) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(
        videoFile.path,
        filename: videoFile.path.split('/').last,
      ),
    });

    final r = await _dio.post('/api/upload', data: formData);
    return VideoUploadResponse.fromJson(r.data as Map<String, dynamic>);
  }

  /// GET /api/analyze/{video_id} — Análisis rápido (holds auto)
  Future<AnalysisResult> analyzeVideo(String videoId, {double climberWeight = 70.0}) async {
    final r = await _dio.get(
      '/api/analyze/$videoId',
      queryParameters: {'climber_weight': climberWeight},
    );
    return AnalysisResult.fromJson(r.data as Map<String, dynamic>);
  }

  /// POST /api/analyze/{video_id} — Análisis con holds custom, ROI, etc.
  Future<AnalysisResult> analyzeVideoWithHolds(
    String videoId, {
    double climberWeight = 70.0,
    List<List<int>>? customHolds,
    int? finishHoldIndex,
    List<int>? roi,
  }) async {
    final body = <String, dynamic>{
      'climber_weight': climberWeight,
    };
    if (customHolds != null) body['custom_holds'] = customHolds;
    if (finishHoldIndex != null) body['finish_hold_index'] = finishHoldIndex;
    if (roi != null && roi.length == 4) body['roi'] = roi;

    final r = await _dio.post('/api/analyze/$videoId', data: body);
    return AnalysisResult.fromJson(r.data as Map<String, dynamic>);
  }

  /// GET /api/overlay/{video_id} — Descargar video con overlay
  Future<String> downloadOverlayVideo(String videoId, String savePath) async {
    await _dio.download('/api/overlay/$videoId', savePath);
    return savePath;
  }

  /// GET /api/videos — Listar videos subidos
  Future<List<VideoInfo>> listVideos() async {
    final r = await _dio.get('/api/videos');
    final list = (r.data as Map)['videos'] as List;
    return list.map((e) => VideoInfo.fromJson(e as Map<String, dynamic>)).toList();
  }
}
```

Necesitarás definir los modelos `VideoUploadResponse`, `AnalysisResult`, `VideoInfo` según los JSON que devuelve el backend (ver sección 4).

### 3.4 Uso típico en la app

```dart
final api = SpeedClimbingApi();

// 1. Subir video
final upload = await api.uploadVideo(myVideoFile);
final videoId = upload.videoId;

// 2. Analizar
final result = await api.analyzeVideo(videoId, climberWeight: 72.0);

// 3. Descargar overlay (opcional)
final path = await getApplicationDocumentsDirectory();
final overlayPath = '${path.path}/overlay_$videoId.mp4';
await api.downloadOverlayVideo(videoId, overlayPath);
```

---

## 4. Endpoints del API (referencia rápida)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Estado del servidor |
| `POST` | `/api/upload` | Subir video (multipart `file`) |
| `GET` | `/api/analyze/{video_id}?climber_weight=70` | Análisis con holds automáticos |
| `POST` | `/api/analyze/{video_id}` | Análisis con `custom_holds`, `roi`, `finish_hold_index` |
| `GET` | `/api/overlay/{video_id}` | Vídeo procesado con overlay (MP4/AVI) |
| `GET` | `/api/videos` | Listar videos subidos |
| `GET` | `/api/pose-stats/{video_id}` | Estadísticas de detección de pose |
| `GET` | `/api/first-frame/{video_id}` | Primera frame en base64 |
| `POST` | `/api/detect-holds/{video_id}` | Detección de presas con HSV custom |

Schemas relevantes en `backend/app/models/schemas.py` y respuestas JSON estándar de FastAPI.

---

## 5. Android: HTTP en desarrollo (cleartext)

Si usas `http://` en desarrollo, Android bloquea tráfico no cifrado por defecto. Hay que permitirlo:

**`android/app/src/main/res/xml/network_security_config.xml`** (crear si no existe):

```xml
<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <domain-config cleartextTrafficPermitted="true">
        <domain includeSubdomains="true">192.168.1.10</domain>
        <domain includeSubdomains="true">10.0.2.2</domain>
        <domain includeSubdomains="true">localhost</domain>
    </domain-config>
</network-security-config>
```

Sustituye `192.168.1.10` por tu IP. `10.0.2.2` es la dirección del host desde el emulador Android.

En **`android/app/src/main/AndroidManifest.xml`**, en `<application>`:

```xml
<application
    android:networkSecurityConfig="@xml/network_security_config"
    ...>
```

---

## 6. iOS: HTTP en desarrollo (ATS)

Para permitir `http://` en desarrollo en iOS, en **`ios/Runner/Info.plist`**:

```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
    <!-- O más restrictivo, solo tu IP:
    <key>NSExceptionDomains</key>
    <dict>
        <key>192.168.1.10</key>
        <dict>
            <key>NSExceptionAllowsInsecureHTTPLoads</key>
            <true/>
        </dict>
    </dict>
    -->
</dict>
```

En producción conviene usar solo HTTPS y quitar estas excepciones.

---

## 7. Emuladores

- **Android:** La IP del host suele ser `10.0.2.2`. Usa `http://10.0.2.2:8000` si corres el backend en tu PC.
- **iOS Simulator:** Suele compartir red con el Mac, así que la IP local del Mac (ej. `192.168.1.10`) suele funcionar.

---

## 8. Checklist rápido

- [ ] Backend corriendo con `--host 0.0.0.0` (ya lo tienes).
- [ ] Flutter: `dio` (o `http`) y modelos para las respuestas del API.
- [ ] `ApiConfig.baseUrl` con tu IP en desarrollo o URL HTTPS en producción.
- [ ] Android: `network_security_config` y `AndroidManifest` si usas HTTP.
- [ ] iOS: `Info.plist` ATS si usas HTTP.
- [ ] Producción: backend desplegado con HTTPS y `baseUrl` actualizada.

---

## 9. Ejecutar el análisis en el propio móvil (on-device)

Si quieres que **todo el análisis se ejecute en el mismo dispositivo** donde corre la app Flutter (sin PC ni servidor), la situación cambia: **no puedes ejecutar el backend Python tal cual dentro de la app**. iOS y Android no ejecutan Python de forma nativa y Flutter usa Dart. Las opciones realistas son estas.

### 9.1 Por qué no puedes “meter” el backend en la app

El backend actual usa **Python** + **OpenCV** + **MediaPipe** + FastAPI. Las apps Flutter son **Dart** y se distribuyen como binarios nativos. No hay una forma estándar de empaquetar y ejecutar ese stack Python completo dentro de una app Flutter como si fuera un servidor en el móvil.

### 9.2 Opción A: Reimplementar el pipeline en Flutter (recomendada para on-device)

**Idea:** Hacer en la app lo mismo que hace el backend, pero en Dart y con APIs móviles.

| Parte del backend | Cómo llevarlo al móvil |
|-------------------|------------------------|
| **Pose (MediaPipe)** | `google_ml_kit` (Pose Detection) o paquetes como `pose_detection_plugin` / `mediapipe_pose_detection`. Hay modelos que corren on-device. |
| **Detección de presas** | Lógica más simple en Dart (p. ej. por color en frames, o un modelo pequeño con TFLite si lo necesitas). |
| **Análisis biomecánico** | Es sobre todo **matemáticas** (CoM, tiempos, fuerzas). Se puede **portar a Dart** sin problema; los esquemas y fórmulas están en `analyzer.py`. |

**Ventajas:** Todo en el móvil, sin red, sin servidor. **Desventajas:** Hay que reescribir la lógica (sobre todo pose + presas) en Dart y adaptar a los plugins que uses.

### 9.3 Opción B: Plugins nativos (Kotlin/Swift)

**Idea:** Implementar pose + presas + análisis en **Kotlin** (Android) y **Swift** (iOS) usando MediaPipe y OpenCV móviles. La app Flutter solo llama a ese código mediante **platform channels**.

**Ventajas:** Reutilizas MediaPipe/OpenCV “oficiales” en móvil. **Desventajas:** Duplicar lógica en dos lenguajes, más complejidad y mantenimiento.

### 9.4 Opción C: Python en el dispositivo (solo Android, experimental)

Herramientas como **Chaquopy** permiten ejecutar **Python en Android** dentro de una app. En teoría podrías empaquetar tu backend (o una versión recortada) y que la app lo invoque.

**Problemas:** Solo Android, APKs más grandes, capas extra de integración, y en iOS no hay equivalente directo. Solo tiene sentido si ya dominas Chaquopy y te interesa experimentar.

### 9.5 Resumen práctico

- **Objetivo: todo en el móvil, sin servidor**  
  → Opción **A** (Flutter + ML Kit / pose detection + Dart para biomecánica) o **B** (plugins nativos).

- **Objetivo: reutilizar el backend Python sin reescribir**  
  → Mantener la arquitectura **app ↔ servidor** (PC o cloud). El análisis no se ejecuta en el móvil.

- **Punto clave:** El **análisis biomecánico** (CoM, pasos, fuerzas, etc.) es portable a Dart o a cualquier lenguaje; lo que cuesta es **pose** y **detección de presas** en el ecosistema móvil.

Si te decides por la **Opción A**, un buen siguiente paso es: (1) añadir `google_ml_kit` (u otro pose detector) y `image` para decodificar frames del vídeo, (2) extraer landmarks frame a frame, y (3) portar las funciones de `BiomechanicalAnalyzer` a Dart usando los mismos índices de landmarks y fórmulas.

---

## 10. CORS en producción (opcional)

En desarrollo, el backend usa `allow_origins=["*"]` por defecto. En producción puedes restringir orígenes por seguridad.

**Opción A – Variable de entorno:** Define `CORS_ORIGINS` como lista separada por comas, por ejemplo:

```bash
export CORS_ORIGINS="https://tu-app.com,https://www.tu-app.com"
```

Si no se define, se usa `["*"]` (como ahora). El backend lee esta variable en el arranque (ver `app/main.py` y `app/core/config.py`).

**Opción B – Editar `main.py` a mano:** Sustituir `allow_origins=["*"]` por algo como:

```python
allow_origins=[
    "https://tu-dominio.com",
    "https://www.tu-dominio.com",
],
```

Las apps nativas (Flutter iOS/Android) no envían `Origin` en muchas peticiones, por lo que CORS no las afecta. Restringir CORS es útil sobre todo si también sirves un frontend web contra el mismo API.

---

Con esto puedes **usar el backend desde Flutter** (vía API) o **llevar el análisis al móvil** (on-device) según lo que necesites. Si quieres, el siguiente paso puede ser: definir los modelos Dart para el API, un ejemplo de pantalla que suba video y muestre el resultado, o un esqueleto de análisis on-device con ML Kit + Dart.
