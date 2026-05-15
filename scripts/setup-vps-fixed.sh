#!/bin/bash
set -e

echo "==============================================="
echo "  RAG System - VPS Setup (FIXED)"
echo "  Server: conocimiento.automatizaciones-physis.cloud"
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
    log_error "Ejecuta como root: sudo bash setup-vps-fixed.sh"
    exit 1
fi

# 1. System update
log_info "1/6 - Actualizando sistema..."
apt update -qq && apt upgrade -y -qq 2>/dev/null || apt update -qq

# 2. Install dependencies
log_info "2/6 - Instalando dependencias..."
apt install -y -qq nginx git curl ufw fail2ban certbot python3-certbot-nginx 2>/dev/null || apt install -y nginx git curl ufw fail2ban certbot python3-certbot-nginx

# 3. Install Docker if not present
log_info "3/6 - Verificando Docker..."
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
log_info "4/6 - Descargando proyecto..."
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

# 5. Configure Nginx (HTTP first, then Certbot, then HTTPS)
log_info "5/6 - Configurando Nginx..."

# Step A: Start with HTTP-only config
cp nginx/conocimiento-http.conf /etc/nginx/sites-available/conocimiento
ln -sf /etc/nginx/sites-available/conocimiento /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test and reload nginx with HTTP only
nginx -t && systemctl reload nginx

# Step B: Get SSL certificate
domain="conocimiento.automatizaciones-physis.cloud"
if ! certbot certificates 2>/dev/null | grep -q "$domain"; then
    log_info "Obteniendo certificado SSL..."
    certbot --nginx -d "$domain" \
        --agree-tos --non-interactive \
        --email admin@automatizaciones-physis.cloud \
        --redirect
fi

# Enable auto-renewal
systemctl enable certbot.timer
systemctl start certbot.timer

# 6. Configure firewall
log_info "6/6 - Configurando firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw --force enable

echo ""
log_info "==============================================="
log_info "SETUP COMPLETADO!"
log_info "==============================================="
echo ""
echo "URLs:"
echo "  HTTP:  http://conocimiento.automatizaciones-physis.cloud"
echo "  HTTPS: https://conocimiento.automatizaciones-physis.cloud (SSL activo)"
echo ""
echo "SIGUIENTES PASOS:"
echo "1. cd /opt/base-conocimiento"
echo "2. cp .env.example .env"
echo "3. nano .env  (completar variables)"
echo "4. docker-compose up -d"
echo ""
