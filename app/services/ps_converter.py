import os
import shutil
import signal
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


@dataclass
class ConversionResult:
    file_id: str
    original_filename: str
    pdf_filename: str
    original_size_bytes: int
    pdf_size_bytes: int
    pdf_path: Path
    conversion_time_ms: float


class PostScriptConversionError(Exception):
    """Excepción lanzada cuando la conversión PostScript falla."""
    pass


class PostScriptConverter:
    """
    Servicio modular encargado de la validación y conversión de PostScript a PDF.
    Diseñado para prevenir fugas de memoria, disco y procesos zombies.
    """

    MAGIC_HEADERS = [
        b"%!",                 # Encabezado PostScript estándar (%!PS-Adobe...)
        b"\x04%!",             # Encabezado con carácter de control PostScript
        b"\xc5\xd0\xd3\xc6",   # Encabezado binario EPS (Encapsulated PostScript)
    ]

    def __init__(self, upload_folder: str, timeout_seconds: int = 60, retention_seconds: int = 3600):
        self.upload_folder = Path(upload_folder)
        self.timeout_seconds = timeout_seconds
        self.retention_seconds = retention_seconds
        self.upload_folder.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_converter_binary() -> Tuple[Optional[str], str]:
        """
        Detecta el ejecutable de conversión disponible.
        Prioriza 'gs' directo para evitar envoltorios bash intermedios y reducir sobrecarga.
        """
        gs_bin = shutil.which("gs")
        if gs_bin:
            return gs_bin, "gs"

        ps2pdf_bin = shutil.which("ps2pdf")
        if ps2pdf_bin:
            return ps2pdf_bin, "ps2pdf"

        return None, "none"

    def check_system_readiness(self) -> dict:
        """Verifica el estado del motor de conversión en el sistema."""
        bin_path, bin_type = self.get_converter_binary()
        if not bin_path:
            return {
                "ready": False,
                "engine": "none",
                "message": "Ghostscript/ps2pdf no está instalado en el sistema.",
            }

        version_info = "desconocida"
        try:
            res = subprocess.run(
                ["gs", "-v"] if bin_type == "gs" else [bin_path, "-v"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0 and res.stdout:
                version_info = res.stdout.splitlines()[0]
        except Exception:
            pass

        return {
            "ready": True,
            "engine": bin_type,
            "binary_path": bin_path,
            "version": version_info,
        }

    def cleanup_expired_jobs(self, max_age_seconds: Optional[int] = None) -> int:
        """
        Elimina directorios temporales de conversiones antiguas para evitar saturación del disco.
        Retorna el número de directorios eliminados.
        """
        max_age = max_age_seconds if max_age_seconds is not None else self.retention_seconds
        now = time.time()
        deleted_count = 0

        if not self.upload_folder.exists():
            return 0

        try:
            for item in self.upload_folder.iterdir():
                if item.is_dir():
                    try:
                        dir_mtime = item.stat().st_mtime
                        if (now - dir_mtime) > max_age:
                            shutil.rmtree(item, ignore_errors=True)
                            deleted_count += 1
                    except OSError:
                        pass
        except Exception:
            pass

        return deleted_count

    def validate_postscript_content(self, file_path: Path) -> Tuple[bool, str]:
        """Valida que el archivo exista, no esté vacío y contenga una cabecera PostScript válida."""
        if not file_path.exists() or file_path.stat().st_size == 0:
            return False, "El archivo está vacío o no existe."

        try:
            with open(file_path, "rb") as f:
                header = f.read(512)

            is_valid = any(header.startswith(magic) or magic in header[:32] for magic in self.MAGIC_HEADERS)
            if not is_valid:
                # Permite verificación si contiene texto %! en las primeras líneas
                text_snippet = header.decode("latin1", errors="ignore")
                if "%!" in text_snippet[:64]:
                    is_valid = True

            if not is_valid:
                return False, "El archivo no contiene una cabecera PostScript válida (%!PS o EPS)."

            return True, "Archivo PostScript válido."
        except Exception as e:
            return False, f"Error al validar el archivo: {str(e)}"

    def convert(self, file_stream, filename: str) -> ConversionResult:
        """
        Guarda el flujo de archivo, valida su contenido y lo convierte a PDF.
        Garantiza:
        1. Limpieza de temporales y retención controlada (anti-disk-leak).
        2. Terminación garantizada de subprocesos y grupos de procesos (anti-process-leak).
        """
        # Ejecutar limpieza oportunista de archivos expirados
        self.cleanup_expired_jobs()

        bin_path, bin_type = self.get_converter_binary()
        if not bin_path:
            raise PostScriptConversionError(
                "Motor de conversión no disponible. Asegúrese de que Ghostscript ('gs' / 'ps2pdf') esté instalado."
            )

        file_id = str(uuid.uuid4())
        job_dir = self.upload_folder / file_id
        job_dir.mkdir(parents=True, exist_ok=True)

        safe_input_path = job_dir / "input.ps"
        pdf_output_name = Path(filename).stem + ".pdf"
        output_pdf_path = job_dir / pdf_output_name

        try:
            # Guardar archivo entrante
            file_stream.save(str(safe_input_path))
            original_size = safe_input_path.stat().st_size

            # Validar estructura PostScript
            is_valid, validation_msg = self.validate_postscript_content(safe_input_path)
            if not is_valid:
                shutil.rmtree(job_dir, ignore_errors=True)
                raise PostScriptConversionError(f"Archivo rechazado: {validation_msg}")

            # Comando seguro según motor
            if bin_type == "gs":
                cmd = [
                    bin_path,
                    "-sDEVICE=pdfwrite",
                    "-dSAFER",
                    "-dNOPAUSE",
                    "-dBATCH",
                    "-dPDFSETTINGS=/default",
                    f"-sOutputFile={output_pdf_path}",
                    str(safe_input_path),
                ]
            else:  # fallback ps2pdf
                cmd = [
                    bin_path,
                    "-dSAFER",
                    "-dPDFSETTINGS=/default",
                    str(safe_input_path),
                    str(output_pdf_path),
                ]

            start_time = time.perf_counter()

            # Ejecutar con grupo de procesos aislado para evitar procesos huérfanos/zombies
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,  # Crea un nuevo process group
            )

            try:
                stdout_data, stderr_data = proc.communicate(timeout=self.timeout_seconds)
            except subprocess.TimeoutExpired:
                # Terminar todo el grupo de procesos para evitar procesos colgados
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except OSError:
                    pass
                proc.communicate()
                shutil.rmtree(job_dir, ignore_errors=True)
                raise PostScriptConversionError(
                    f"La conversión excedió el tiempo límite permitido ({self.timeout_seconds}s)."
                )

            if proc.returncode != 0 or not output_pdf_path.exists():
                error_details = stderr_data.strip() or stdout_data.strip() or "Error de sintaxis PostScript."
                shutil.rmtree(job_dir, ignore_errors=True)
                raise PostScriptConversionError(f"Fallo en la conversión PostScript: {error_details}")

            end_time = time.perf_counter()
            conversion_time_ms = round((end_time - start_time) * 1000, 2)
            pdf_size = output_pdf_path.stat().st_size

            # Anti-disk-leak: eliminar inmediatamente el archivo .ps de entrada
            try:
                safe_input_path.unlink(missing_ok=True)
            except OSError:
                pass

            return ConversionResult(
                file_id=file_id,
                original_filename=filename,
                pdf_filename=pdf_output_name,
                original_size_bytes=original_size,
                pdf_size_bytes=pdf_size,
                pdf_path=output_pdf_path,
                conversion_time_ms=conversion_time_ms,
            )

        except PostScriptConversionError:
            raise
        except Exception as e:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise PostScriptConversionError(f"Error inesperado durante la conversión: {str(e)}")

    def get_pdf_file(self, file_id: str) -> Optional[Tuple[Path, str]]:
        """Busca el archivo PDF generado para un file_id dado."""
        job_dir = self.upload_folder / file_id
        if not job_dir.exists() or not job_dir.is_dir():
            return None

        pdf_files = list(job_dir.glob("*.pdf"))
        if not pdf_files:
            return None

        pdf_path = pdf_files[0]
        return pdf_path, pdf_path.name
