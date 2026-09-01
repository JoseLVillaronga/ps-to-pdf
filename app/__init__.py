import os
from pathlib import Path
from flask import Flask, jsonify
from app.config import Config


def create_app(config_class=Config) -> Flask:
    """Fábrica de aplicaciones Flask para el servicio de conversión."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Asegurar que el directorio de almacenamiento temporal exista
    upload_dir = Path(app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Manejo de error para archivos que superen MAX_CONTENT_LENGTH
    @app.errorhandler(413)
    def request_entity_too_large(error):
        max_mb = app.config["MAX_CONTENT_LENGTH"] / (1024 * 1024)
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"El archivo excede el tamaño máximo permitido de {max_mb:.0f} MB.",
                }
            ),
            413,
        )

    # Registrar blueprints
    from app.routes.converter import converter_bp

    app.register_blueprint(converter_bp)

    return app
