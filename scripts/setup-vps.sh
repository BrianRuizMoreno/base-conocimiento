#!/bin/bash
set -e

echo "==============================================="
echo "  RAG System - VPS Setup (Traefik Edition)"
echo "  URL: https://conocimiento.automatizaciones-physis.cloud"
echo "==============================================="
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

if [ "$EUID" -ne 0 ]; then 
    log_error "Ejecuta como root: sudo bash setup-vps.sh"
    exit 1
fi

# 1. System update
log_info "1/4 - Actualizando sistema..."
apt update -qq && apt upgrade -y -qq 2>/dev/null || apt update -qq

# 2. Install dependencies
log_info "2/4 - Instalando dependencias..."
apt install -y -qq git curl python3 python3-pip 2>/dev/null || apt install -y git curl python3 python3-pip
pip3 install bcrypt 2>/dev/null || true

# 3. Verify Docker
log_info "3/4 - Verificando Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | bash
    systemctl enable docker
    systemctl start docker
fi
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Check PhysisNet exists
if ! docker network ls | grep -q "PhysisNet"; then
    log_error "La red 'PhysisNet' no existe. Verifica tu configuracion de Portainer/Docker Swarm."
    exit 1
fi

# 4. Clone/update project
log_info "4/4 - Descargando proyecto..."
PROJECT_DIR="/opt/base-conocimiento"
if [ -d "$PROJECT_DIR/.git" ]; then
    cd "$PROJECT_DIR"
    git fetch origin main
    git reset --hard origin/main
else
    rm -rf "$PROJECT_DIR"
    git clone https://github.com/BrianRuizMoreno/base-conocimiento.git "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

# Final message
echo ""
log_info "==============================================="
log_info "SETUP COMPLETADO!"
log_info "==============================================="
echo ""
echo "SIGUIENTES PASOS:"
echo ""
echo "1. Configurar .env:"
echo "   cd /opt/base-conocimiento"
echo "   cp .env.example .env"
echo "   nano .env"
echo ""
echo "   Variables requeridas:"
echo "   - DATABASE_URL (tu PostgreSQL en Portainer)"
echo "   - ADMIN_PIN_HASH (genera con el comando abajo)"
echo "   - SECRET_KEY (openssl rand -base64 32)"
echo ""
echo "2. Generar PIN hash:"
echo "   python3 -c \"import bcrypt; print(bcrypt.hashpw(b'TU_PIN_AQUI', bcrypt.gensalt()).decode())\""
echo ""
echo "3. Deploy:"
echo "   bash scripts/deploy.sh"
echo ""
echo "4. Verificar:"
echo "   https://conocimiento.automatizaciones-physis.cloud"
echo ""
