import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
base_dir = Path(__file__).resolve().parent.parent
load_dotenv(base_dir / ".env")


class Config:
    """Configuración principal de la aplicación."""

    BASE_DIR = base_dir
    SECRET_KEY = os.getenv("SECRET_KEY", "ps-to-pdf-default-insecure-key-dev")

    # Configuración de red
    PORT = int(os.getenv("PORT", 5400))
    HOST = os.getenv("HOST", "0.0.0.0")
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")

    # Configuración de archivos y cargas
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 32 * 1024 * 1024))  # 32MB
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    
    # Resolver ruta absoluta para el directorio de subidas/conversiones
    if not os.path.isabs(UPLOAD_FOLDER):
        UPLOAD_FOLDER = str(base_dir / UPLOAD_FOLDER)

    # Extensiones y tipos permitidos
    ALLOWED_EXTENSIONS = {"ps", "eps"}
    
    # Tiempo límite de ejecución de conversión en segundos
    CONVERSION_TIMEOUT_SECONDS = int(os.getenv("CONVERSION_TIMEOUT_SECONDS", 60))

    # Tiempo de retención de archivos generados antes de limpieza automática (en segundos, defecto: 1 hora)
    FILE_RETENTION_SECONDS = int(os.getenv("FILE_RETENTION_SECONDS", 3600))
