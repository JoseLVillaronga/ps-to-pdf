import os
from pathlib import Path
from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    render_template,
    request,
    send_file,
)
from werkzeug.utils import secure_filename

from app.services.ps_converter import (
    PostScriptConversionError,
    PostScriptConverter,
)

converter_bp = Blueprint("converter", __name__)


def get_converter() -> PostScriptConverter:
    """Helper para instanciar el servicio con la configuración activa."""
    return PostScriptConverter(
        upload_folder=current_app.config["UPLOAD_FOLDER"],
        timeout_seconds=current_app.config["CONVERSION_TIMEOUT_SECONDS"],
        retention_seconds=current_app.config.get("FILE_RETENTION_SECONDS", 3600),
    )


def format_size(bytes_num: int) -> str:
    """Formatea bytes a una cadena legible (KB, MB, etc.)."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_num < 1024.0:
            return f"{bytes_num:.1f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.1f} TB"


@converter_bp.route("/favicon.ico", methods=["GET"])
def favicon():
    """Favicon SVG para evitar errores 404 en navegadores."""
    favicon_path = Path(current_app.root_path) / "static" / "images" / "favicon.svg"
    if favicon_path.exists():
        return send_file(favicon_path, mimetype="image/svg+xml")
    
    svg_icon = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path></svg>"""
    return Response(svg_icon, mimetype="image/svg+xml")


@converter_bp.route("/", methods=["GET"])
def index():
    """Página principal de la aplicación."""
    converter = get_converter()
    system_status = converter.check_system_readiness()
    max_size_mb = current_app.config["MAX_CONTENT_LENGTH"] / (1024 * 1024)
    return render_template(
        "index.html",
        system_status=system_status,
        max_size_mb=int(max_size_mb),
    )


@converter_bp.route("/api/status", methods=["GET"])
def system_status():
    """Endpoint de comprobación de salud y motor de conversión."""
    converter = get_converter()
    status = converter.check_system_readiness()
    return jsonify({"success": True, "status": status})


@converter_bp.route("/api/convert", methods=["POST"])
def convert_postscript():
    """Endpoint API para recibir un archivo PostScript y convertirlo a PDF."""
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No se envió ningún archivo."}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"success": False, "error": "Nombre de archivo no válido o vacío."}), 400

    original_filename = secure_filename(file.filename) or "document.ps"
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else ""

    allowed_exts = current_app.config["ALLOWED_EXTENSIONS"]
    if ext not in allowed_exts:
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Extensión '.{ext}' no permitida. Solo se admiten: {', '.join(allowed_exts)}",
                }
            ),
            400,
        )

    converter = get_converter()

    try:
        result = converter.convert(file, original_filename)
        return jsonify(
            {
                "success": True,
                "data": {
                    "file_id": result.file_id,
                    "original_filename": result.original_filename,
                    "pdf_filename": result.pdf_filename,
                    "original_size": format_size(result.original_size_bytes),
                    "pdf_size": format_size(result.pdf_size_bytes),
                    "conversion_time_ms": result.conversion_time_ms,
                    "download_url": f"/download/{result.file_id}",
                },
            }
        )
    except PostScriptConversionError as e:
        return jsonify({"success": False, "error": str(e)}), 422
    except Exception as e:
        current_app.logger.exception("Error inesperado en conversión")
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Error interno del servidor durante la conversión: {str(e)}",
                }
            ),
            500,
        )


@converter_bp.route("/download/<file_id>", methods=["GET"])
def download_pdf(file_id: str):
    """Descarga el PDF generado a partir del file_id."""
    safe_file_id = secure_filename(file_id)
    converter = get_converter()
    pdf_info = converter.get_pdf_file(safe_file_id)

    if not pdf_info:
        return jsonify({"success": False, "error": "Archivo no encontrado o expirado."}), 404

    pdf_path, filename = pdf_info
    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )
