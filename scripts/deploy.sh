#!/bin/bash
set -e

echo "==============================================="
echo "  RAG System - Deploy Completo"
echo "  VPS: 72.60.12.96"
echo "  Dominio: conocimiento.automatizaciones-physis.cloud"
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

# 1. System update
log_info "1/8 - Actualizando sistema..."
apt update -qq && apt upgrade -y -qq

# 2. Install dependencies
log_info "2/8 - Instalando dependencias..."
apt install -y -qq nginx git curl ufw fail2ban certbot python3-certbot-nginx

# 3. Install Docker if not present
log_info "3/8 - Verificando Docker..."
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

# 4. Clone/update project
log_info "4/8 - Descargando proyecto..."
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

# 5. Configure Nginx
log_info "5/8 - Configurando Nginx..."
cp nginx/conocimiento.conf /etc/nginx/sites-available/conocimiento
ln -sf /etc/nginx/sites-available/conocimiento /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
systemctl enable nginx

# 6. Configure firewall
log_info "6/8 - Configurando firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw --force enable

# 7. Configure SSL
log_info "7/8 - Configurando SSL..."
if ! certbot certificates | grep -q "conocimiento.automatizaciones-physis.cloud"; then
    certbot --nginx -d conocimiento.automatizaciones-physis.cloud \
        --agree-tos --non-interactive \
        --email admin@automatizaciones-physis.cloud
fi
systemctl enable certbot.timer
systemctl start certbot.timer

# 8. Start containers
log_info "8/8 - Iniciando contenedores..."
cd "$PROJECT_DIR"
if [ ! -f ".env" ]; then
    log_warn "ARCHIVO .env NO ENCONTRADO"
    log_warn "Por favor crea el archivo .env antes de continuar"
    log_warn "Ubicacion: $PROJECT_DIR/.env"
    log_warn "Ejemplo: cp .env.example .env && nano .env"
    exit 1
fi
docker-compose down 2>/dev/null || true
docker-compose up -d --build

# Verify
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
echo "Verificar estado:"
echo "  docker-compose ps"
echo "  docker-compose logs -f rag-backend"
echo ""
