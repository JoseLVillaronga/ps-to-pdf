#!/usr/bin/env bash
# ==============================================================================
# Instalador y Gestor del Servicio Systemd para PS to PDF Web Converter
# ==============================================================================
set -e

# Colores para salida de terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SERVICE_NAME="ps-to-pdf"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/venv"
TEMPLATE_FILE="${SCRIPT_DIR}/systemd/ps-to-pdf.service.template"

# Detectar usuario y grupo actual si no se ejecutan como root
CURRENT_USER="${SUDO_USER:-$(id -un)}"
CURRENT_GROUP="$(id -gn "${CURRENT_USER}")"

# Cargar variables de .env si existe
PORT="5400"
HOST="0.0.0.0"
if [ -f "${SCRIPT_DIR}/.env" ]; then
    ENV_PORT=$(grep -E "^PORT=" "${SCRIPT_DIR}/.env" | cut -d '=' -f2 | tr -d ' "')
    ENV_HOST=$(grep -E "^HOST=" "${SCRIPT_DIR}/.env" | cut -d '=' -f2 | tr -d ' "')
    [ -n "${ENV_PORT}" ] && PORT="${ENV_PORT}"
    [ -n "${ENV_HOST}" ] && HOST="${ENV_HOST}"
fi

show_help() {
    echo -e "${BLUE}Gestor del Servicio Systemd - PS to PDF Web Converter${NC}"
    echo "Uso: $0 [OPCIÓN]"
    echo ""
    echo "Opciones disponibles:"
    echo "  --install     Instalar, habilitar e iniciar el servicio systemd (por defecto)"
    echo "  --uninstall   Detener, deshabilitar y eliminar el servicio systemd"
    echo "  --restart     Reiniciar el servicio systemd"
    echo "  --status      Consultar el estado del servicio"
    echo "  --logs        Ver logs en tiempo real (journalctl)"
    echo "  --help        Mostrar esta ayuda"
    echo ""
}

check_sudo() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${YELLOW}ℹ️  Se requieren permisos de administrador para gestionar systemd. Solicitando sudo...${NC}"
        SUDO="sudo"
    else
        SUDO=""
    fi
}

install_service() {
    echo -e "${BLUE}============================================================${NC}"
    echo -e "${GREEN}🚀 Instalando servicio systemd: ${SERVICE_NAME}${NC}"
    echo -e "${BLUE}============================================================${NC}"

    # 1. Verificar entorno virtual
    if [ ! -d "${VENV_DIR}" ]; then
        echo -e "${RED}❌ Error: No se encontró el entorno virtual en ${VENV_DIR}${NC}"
        echo "Por favor créelo con: python3 -m venv venv"
        exit 1
    fi

    # 2. Asegurar dependencias de producción (gunicorn)
    echo -e "${BLUE}📦 Verificando e instalando dependencias (incluyendo Gunicorn)...${NC}"
    "${VENV_DIR}/bin/pip" install -q -r "${SCRIPT_DIR}/requirements.txt"

    # 3. Preparar directorio de subidas y permisos
    mkdir -p "${SCRIPT_DIR}/uploads"
    chown -R "${CURRENT_USER}:${CURRENT_GROUP}" "${SCRIPT_DIR}/uploads"

    check_sudo

    # 4. Generar archivo de servicio a partir del template
    echo -e "${BLUE}⚙️  Configurando archivo de servicio en ${SERVICE_FILE}...${NC}"
    TEMP_SERVICE=$(mktemp)

    sed \
        -e "s|{{USER}}|${CURRENT_USER}|g" \
        -e "s|{{GROUP}}|${CURRENT_GROUP}|g" \
        -e "s|{{APP_DIR}}|${SCRIPT_DIR}|g" \
        -e "s|{{VENV_DIR}}|${VENV_DIR}|g" \
        -e "s|{{HOST}}|${HOST}|g" \
        -e "s|{{PORT}}|${PORT}|g" \
        "${TEMPLATE_FILE}" > "${TEMP_SERVICE}"

    ${SUDO} cp "${TEMP_SERVICE}" "${SERVICE_FILE}"
    ${SUDO} chmod 644 "${SERVICE_FILE}"
    rm -f "${TEMP_SERVICE}"

    # 5. Recargar y habilitar servicio
    echo -e "${BLUE}🔄 Recargando systemd daemon y habilitando servicio...${NC}"
    ${SUDO} systemctl daemon-reload
    ${SUDO} systemctl enable "${SERVICE_NAME}.service"
    ${SUDO} systemctl restart "${SERVICE_NAME}.service"

    echo ""
    echo -e "${GREEN}✅ ¡Servicio ${SERVICE_NAME} instalado y ejecutándose exitosamente!${NC}"
    echo -e "📡 URL: ${GREEN}http://${HOST}:${PORT}${NC} (Local: http://localhost:${PORT})"
    echo ""
    echo -e "${BLUE}Comandos útiles:${NC}"
    echo "  • Ver estado:     sudo systemctl status ${SERVICE_NAME}"
    echo "  • Ver logs:       sudo journalctl -u ${SERVICE_NAME} -f"
    echo "  • Reiniciar:      sudo systemctl restart ${SERVICE_NAME}"
    echo "  • Detener:        sudo systemctl stop ${SERVICE_NAME}"
    echo "  • Desinstalar:    ./install_service.sh --uninstall"
    echo ""
}

uninstall_service() {
    echo -e "${YELLOW}🛑 Desinstalando servicio systemd: ${SERVICE_NAME}...${NC}"
    check_sudo

    if [ -f "${SERVICE_FILE}" ]; then
        ${SUDO} systemctl stop "${SERVICE_NAME}.service" 2>/dev/null || true
        ${SUDO} systemctl disable "${SERVICE_NAME}.service" 2>/dev/null || true
        ${SUDO} rm -f "${SERVICE_FILE}"
        ${SUDO} systemctl daemon-reload
        echo -e "${GREEN}✅ Servicio desinstalado y eliminado correctamente.${NC}"
    else
        echo -e "${YELLOW}El servicio no estaba instalado en ${SERVICE_FILE}.${NC}"
    fi
}

service_status() {
    sudo systemctl status "${SERVICE_NAME}.service"
}

service_restart() {
    check_sudo
    echo -e "${BLUE}🔄 Reiniciando ${SERVICE_NAME}...${NC}"
    ${SUDO} systemctl restart "${SERVICE_NAME}.service"
    echo -e "${GREEN}✅ Reiniciado.${NC}"
    ${SUDO} systemctl status "${SERVICE_NAME}.service" --no-pager
}

service_logs() {
    echo -e "${BLUE}📜 Mostrando logs en vivo (Ctrl+C para salir)...${NC}"
    sudo journalctl -u "${SERVICE_NAME}.service" -f -o cat
}

# Procesamiento de argumentos
ACTION="${1:---install}"

case "${ACTION}" in
    --install|-i)
        install_service
        ;;
    --uninstall|-u)
        uninstall_service
        ;;
    --status|-s)
        service_status
        ;;
    --restart|-r)
        service_restart
        ;;
    --logs|-l)
        service_logs
        ;;
    --help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Opción desconocida: ${ACTION}${NC}"
        show_help
        exit 1
        ;;
esac
