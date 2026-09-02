# 📄 PS to PDF — Conversor Web PostScript a PDF

Aplicación web modular, ligera y moderna para la conversión de documentos **PostScript (`.ps` y `.eps`) a formato PDF vectorial**. Diseñada con **Flask**, **Jinja2**, **Tailwind CSS local (100% Offline)** y optimizada tanto para dispositivos móviles como de escritorio.

---

## ✨ Características Principales

- 🌐 **100% Offline & Autónomo:** Incluye el bundle standalone de Tailwind CSS localmente en `static/js/tailwind.js`. Funciona de forma completamente autónoma sin depender de conexión a Internet ni CDNs externos.
- 📱 **Mobile-Friendly:** Interfaz táctil adaptada con áreas de selección de gran tamaño, subida intuitiva *Drag & Drop* y visualización de progreso.
- ⚡ **Conversión Vectorial de Alta Fidelidad:** Utiliza el motor nativo de **Ghostscript (`gs` / `ps2pdf`)** para preservar tipografías, trazos vectoriales y curvas de impresión.
- 🛡️ **Prevención Estricta de Fugas (Anti-Leaks):**
  - **Process / CPU Leaks:** Creación de grupos de procesos independientes (`start_new_session=True`) con terminación garantizada de procesos huérfanos o zombies ante timeouts (`SIGKILL` en process group).
  - **Disk Leaks:** Destrucción inmediata del archivo temporal `.ps` tras la conversión y purga automática periódica (TTL) de PDFs antiguos (`FILE_RETENTION_SECONDS`).
  - **Memory Leaks:** Reciclaje periódico de procesos worker con **Gunicorn** (`--max-requests 1000 --max-requests-jitter 50`).
- 🔒 **Seguridad y Privacidad:** Validación estricta de encabezados *magic bytes* PostScript (`%!PS` / `%!`), sandboxing con el flag `-dSAFER`, y aislamiento por UUID para evitar colisiones y *Path Traversal*.
- ⚙️ **Listo para Producción:** Incluye instalador automatizado para servicio **Systemd** con Gunicorn en el puerto **5400**.

---

## 🏛️ Arquitectura del Proyecto

El sistema sigue rigurosamente los principios de **Modularización Estricta (Ley 1)**, **Ataque a Causas Raíz (Ley 2)** y **Mínimo Blast Radius (Ley 3)**:

```text
ps-to-pdf/
├── app/
│   ├── __init__.py            # Application Factory (create_app)
│   ├── config.py              # Gestión modular de variables de entorno y límites
│   ├── routes/
│   │   ├── __init__.py
│   │   └── converter.py       # Endpoints HTTP y API REST (/, /convert, /download, /status)
│   ├── services/
│   │   ├── __init__.py
│   │   └── ps_converter.py    # Servicio desacoplado de validación, conversión y limpieza
│   ├── static/
│   │   ├── css/
│   │   │   └── custom.css     # Estilos complementarios, glassmorphism y micro-animaciones
│   │   └── js/
│   │       ├── tailwind.js    # Bundle local standalone de Tailwind CSS (Zero Internet)
│   │       └── app.js         # Frontend reactivo (Drag & Drop, AJAX, feedback y descarga)
│   └── templates/
│       ├── base.html          # Layout base responsive con badges de estado y diseño oscuro
│       └── index.html         # Vista principal con interfaz de conversión
├── systemd/
│   └── ps-to-pdf.service.template # Plantilla de unidad systemd con hardening de seguridad
├── tests/
│   ├── __init__.py
│   ├── test_converter.py      # Tests unitarios del conversor PostScript y anti-leaks
│   └── test_routes.py         # Tests de integración de endpoints HTTP y validaciones
├── .env.example               # Plantilla documentada de variables de entorno
├── install_service.sh         # Script instalador y gestor del servicio systemd
├── requirements.txt           # Dependencias fijadas (Flask, Gunicorn, pytest, etc.)
└── run.py                     # Punto de entrada para ejecución en desarrollo
```

---

## 📋 Requisitos del Sistema

1. **Python 3.10+** (probado y verificado en Python 3.12).
2. **Ghostscript** instalado en el sistema operativo:
   - **Debian / Ubuntu / Linux Mint:**
     ```bash
     sudo apt update && sudo apt install ghostscript
     ```
   - **Fedora / RHEL / CentOS:**
     ```bash
     sudo dnf install ghostscript
     ```
   - **Arch Linux:**
     ```bash
     sudo pacman -S ghostscript
     ```
   - **macOS (Homebrew):**
     ```bash
     brew install ghostscript
     ```

---

## 🚀 Instalación y Puesta en Marcha

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/ps-to-pdf.git
cd ps-to-pdf
```

### 2. Configurar el entorno virtual
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
Crea el archivo `.env` a partir de la plantilla:
```bash
cp .env.example .env
```

Parámetros disponibles en `.env`:
| Variable | Descripción | Valor por Defecto |
| :--- | :--- | :--- |
| `PORT` | Puerto de escucha del servidor web | `5400` |
| `HOST` | Dirección IP de enlace | `0.0.0.0` |
| `FLASK_DEBUG` | Habilita el modo de depuración de Flask | `False` |
| `SECRET_KEY` | Clave de sesión y seguridad | `cadena_aleatoria` |
| `MAX_CONTENT_LENGTH` | Tamaño máximo de archivo permitido en bytes (32 MB) | `33554432` |
| `UPLOAD_FOLDER` | Directorio temporal de conversiones | `uploads` |
| `CONVERSION_TIMEOUT_SECONDS` | Tiempo límite de ejecución de Ghostscript (segundos) | `60` |
| `FILE_RETENTION_SECONDS` | TTL de retención de archivos antes de purga automática | `3600` (1 hora) |

---

## 💻 Ejecución en Modo Desarrollo

Para iniciar el servidor de desarrollo en el puerto **5400**:

```bash
./venv/bin/python run.py
```

Accede desde tu navegador en:
- **Local:** [http://localhost:5400](http://localhost:5400)
- **Red Local / Móviles:** `http://<IP-LOCAL>:5400`

---

## 🛠️ Instalación como Servicio Systemd (Producción)

Se incluye el script gestor automatizado `install_service.sh`, el cual configura **Gunicorn** como servidor WSGI de producción y lo registra como servicio del sistema.

### Instalar y activar el servicio:
```bash
chmod +x install_service.sh
./install_service.sh
```

### Comandos de gestión disponibles:
```bash
./install_service.sh --status     # Consultar estado del servicio
./install_service.sh --logs       # Ver logs en vivo (journalctl -f)
./install_service.sh --restart    # Reiniciar el servicio
./install_service.sh --uninstall  # Detener, deshabilitar y remover el servicio
```

---

## 🧪 Pruebas Automatizadas (Unit & Integration Tests)

La suite de pruebas cubre validación de cabeceras, conversión real de archivos PostScript, detección de motores, rechazo de archivos inválidos, aislamiento de temporales y endpoints HTTP.

Para ejecutar todas las pruebas con `pytest`:

```bash
./venv/bin/pytest tests/ -v
```

### Cobertura de pruebas:
- `tests/test_converter.py`:
  - `test_system_readiness`: Comprueba detección de `gs` / `ps2pdf`.
  - `test_validate_postscript_content_valid`: Valida archivos `.ps` correctos (`%!PS`).
  - `test_validate_postscript_content_invalid`: Rechaza archivos no PostScript.
  - `test_validate_empty_file`: Rechaza archivos vacíos (0 bytes).
  - `test_conversion_with_invalid_content_raises_error`: Verifica excepciones estructuradas.
  - `test_conversion_successful_if_engine_available`: Conversión completa `.ps` -> `.pdf` y verificación de borrado inmediato del `.ps` temporal.
  - `test_cleanup_expired_jobs`: Verifica purga de directorios temporales que superan el TTL.
- `tests/test_routes.py`:
  - `test_index_route`: Comprueba renderizado de la vista Jinja2 (`/`).
  - `test_system_status_api`: Comprueba el endpoint JSON de salud (`/api/status`).
  - `test_convert_missing_file_payload`: Manejo de error 400 cuando falta el archivo.
  - `test_convert_invalid_extension`: Manejo de error 400 para extensiones no admitidas.
  - `test_convert_invalid_postscript_content`: Manejo de error 422 para contenido no válido.
  - `test_download_nonexistent_file`: Manejo de error 404 al solicitar un ID inexistente.
  - `test_favicon_route`: Comprueba el servicio del favicon vectorial en memoria (`/favicon.ico`).

---

## 📡 Documentación de la API REST

### 1. `POST /api/convert`
Convierte un archivo PostScript subido mediante formulario `multipart/form-data`.
- **Payload:** `file` (archivo `.ps` o `.eps`).
- **Respuesta de éxito (200 OK):**
  ```json
  {
    "success": true,
    "data": {
      "file_id": "c97acb87-b40c-4659-a39f-833ffbb03924",
      "original_filename": "documento.ps",
      "pdf_filename": "documento.pdf",
      "original_size": "340.9 KB",
      "pdf_size": "44.1 KB",
      "conversion_time_ms": 738.6,
      "download_url": "/download/c97acb87-b40c-4659-a39f-833ffbb03924"
    }
  }
  ```

### 2. `GET /download/<file_id>`
Descarga el archivo PDF generado.
- **Headers:** `Content-Type: application/pdf`, `Content-Disposition: attachment; filename="<nombre>.pdf"`

### 3. `GET /api/status`
Consulta el estado de salud del servidor y la disponibilidad de Ghostscript.
- **Respuesta de éxito (200 OK):**
  ```json
  {
    "success": true,
    "status": {
      "ready": true,
      "engine": "gs",
      "binary_path": "/usr/bin/gs",
      "version": "GPL Ghostscript 10.02.1"
    }
  }
  ```

---

## 📜 Licencia y Principios

Desarrollado bajo las **Leyes Universales de Ingeniería de José Luis Villaronga** y el **Modelo Ético Adaptativo (MEA v2.1)**.

Este proyecto está bajo la Licencia MIT. Para más detalles, consulte el archivo [LICENSE](LICENSE).
