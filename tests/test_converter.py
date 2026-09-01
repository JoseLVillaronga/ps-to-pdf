import io
import shutil
import tempfile
from pathlib import Path
import pytest
from werkzeug.datastructures import FileStorage

from app.services.ps_converter import (
    PostScriptConverter,
    PostScriptConversionError,
)

SAMPLE_VALID_PS = b"""%!PS-Adobe-3.0
%%Title: Test Document
%%Pages: 1
%%BoundingBox: 0 0 300 300
%%EndComments
/Helvetica findfont 20 scalefont setfont
50 200 moveto
(Hola desde PostScript!) show
0.2 setlinewidth
50 180 moveto
250 180 lineto stroke
showpage
%%EOF
"""

SAMPLE_INVALID_PS = b"This is just a plain text file, not a valid PostScript file."


@pytest.fixture
def temp_converter():
    temp_dir = tempfile.mkdtemp()
    converter = PostScriptConverter(upload_folder=temp_dir, timeout_seconds=10)
    yield converter
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_system_readiness(temp_converter):
    status = temp_converter.check_system_readiness()
    assert "ready" in status
    assert "engine" in status


def test_validate_postscript_content_valid(temp_converter):
    temp_file = temp_converter.upload_folder / "test_valid.ps"
    temp_file.write_bytes(SAMPLE_VALID_PS)

    is_valid, msg = temp_converter.validate_postscript_content(temp_file)
    assert is_valid is True
    assert "válido" in msg.lower()


def test_validate_postscript_content_invalid(temp_converter):
    temp_file = temp_converter.upload_folder / "test_invalid.ps"
    temp_file.write_bytes(SAMPLE_INVALID_PS)

    is_valid, msg = temp_converter.validate_postscript_content(temp_file)
    assert is_valid is False
    assert "no contiene una cabecera" in msg.lower()


def test_validate_empty_file(temp_converter):
    temp_file = temp_converter.upload_folder / "test_empty.ps"
    temp_file.write_bytes(b"")

    is_valid, msg = temp_converter.validate_postscript_content(temp_file)
    assert is_valid is False
    assert "vacío" in msg.lower()


def test_conversion_with_invalid_content_raises_error(temp_converter):
    storage = FileStorage(
        stream=io.BytesIO(SAMPLE_INVALID_PS),
        filename="invalid.ps",
        content_type="application/postscript",
    )

    with pytest.raises(PostScriptConversionError) as exc_info:
        temp_converter.convert(storage, "invalid.ps")

    assert "rechazado" in str(exc_info.value).lower()


def test_conversion_successful_if_engine_available(temp_converter):
    status = temp_converter.check_system_readiness()
    if not status["ready"]:
        pytest.skip("Ghostscript/ps2pdf no está instalado en este entorno de test.")

    storage = FileStorage(
        stream=io.BytesIO(SAMPLE_VALID_PS),
        filename="sample.ps",
        content_type="application/postscript",
    )

    result = temp_converter.convert(storage, "sample.ps")

    assert result.file_id is not None
    assert result.original_filename == "sample.ps"
    assert result.pdf_filename == "sample.pdf"
    assert result.pdf_path.exists()
    assert result.pdf_size_bytes > 0
    assert result.conversion_time_ms >= 0

    # Verificar recuperación del archivo generado
    pdf_info = temp_converter.get_pdf_file(result.file_id)
    assert pdf_info is not None
    assert pdf_info[0] == result.pdf_path
    assert pdf_info[1] == "sample.pdf"

    # Verificar que el archivo .ps temporal de entrada fue borrado inmediatamente (anti-leak de disco)
    input_ps_path = result.pdf_path.parent / "input.ps"
    assert not input_ps_path.exists()


def test_cleanup_expired_jobs(temp_converter):
    # Crear carpeta simulada antigua
    old_job = temp_converter.upload_folder / "old-job-uuid"
    old_job.mkdir(parents=True, exist_ok=True)
    (old_job / "old.pdf").write_bytes(b"%PDF-1.4 dummy content")

    # Ejecutar limpieza con max_age_seconds=0 para forzar purga
    deleted = temp_converter.cleanup_expired_jobs(max_age_seconds=-1)
    assert deleted >= 1
    assert not old_job.exists()
