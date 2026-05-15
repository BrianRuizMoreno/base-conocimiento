#!/bin/bash
set -e

echo "==============================================="
echo "  RAG System - Deploy (Docker Swarm Stack)"
echo "  VPS: 72.60.12.96"
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
    log_error "Ejecuta como root: sudo bash deploy.sh"
    exit 1
fi

PROJECT_DIR="/opt/base-conocimiento"

# 1. Update code
log_info "1/5 - Actualizando codigo..."
cd "$PROJECT_DIR"
git fetch origin main
git reset --hard origin/main

# 2. Check .env
log_info "2/5 - Verificando .env..."
if [ ! -f ".env" ]; then
    log_warn "ARCHIVO .env NO ENCONTRADO"
    log_warn "Por favor crea el archivo .env:"
    log_warn "  cd $PROJECT_DIR"
    log_warn "  cp .env.example .env"
    log_warn "  nano .env"
    exit 1
fi

# 3. Build images
log_info "3/5 - Construyendo imagenes..."
docker-compose build

# 4. Deploy stack
log_info "4/5 - Deployando stack..."
docker stack deploy -c docker-stack.yml rag-system

# 5. Cleanup
log_info "5/5 - Limpiando..."
docker system prune -f

# 6. Verify
echo ""
log_info "==============================================="
log_info "DEPLOY COMPLETADO!"
log_info "==============================================="
echo ""
echo "URLs:"
echo "  Frontend: https://conocimiento.automatizaciones-physis.cloud"
echo "  API:      https://conocimiento.automatizaciones-physis.cloud/api/v1"
echo "  Health:   https://conocimiento.automatizaciones-physis.cloud/api/v1/health"
echo ""
echo "Comandos utiles:"
echo "  docker stack ps rag-system"
echo "  docker service logs rag-system_rag-backend"
echo "  docker service logs rag-system_rag-frontend"
echo ""
