#!/usr/bin/env python3
"""
Punto de entrada principal para ejecutar la aplicación Web de conversión PostScript a PDF.
"""
from app import create_app
from app.config import Config

app = create_app(Config)

if __name__ == "__main__":
    host = app.config["HOST"]
    port = app.config["PORT"]
    debug = app.config["DEBUG"]

    print("=" * 60)
    print("🚀 Servidor PostScript a PDF iniciado exitosamente")
    print(f"📡 Escuchando en: http://{host}:{port} (Local: http://localhost:{port})")
    print(f"⚙️  Modo Debug: {'Activado' if debug else 'Desactivado'}")
    print(f"📁 Directorio de subidas: {app.config['UPLOAD_FOLDER']}")
    print("=" * 60)

    app.run(host=host, port=port, debug=debug)
