#!/bin/bash
set -e

echo "==============================================="
echo "  RAG System - SSL Setup (Let's Encrypt)"
echo "==============================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

if [ "$EUID" -ne 0 ]; then 
    log_error "Por favor ejecuta como root"
    exit 1
fi

DOMAIN="conocimiento.automatizaciones-physis.cloud"

# Check if certbot is installed
if ! command -v certbot &> /dev/null; then
    log_info "Instalando Certbot..."
    apt install -y certbot python3-certbot-nginx
fi

# Check DNS propagation
log_info "Verificando DNS..."
if ! nslookup $DOMAIN > /dev/null 2>&1; then
    log_error "El dominio $DOMAIN no resuelve. Verifica el DNS en Hostinger."
    exit 1
fi

log_info "DNS verificado correctamente"

# Obtain SSL certificate
log_info "Obteniendo certificado SSL para $DOMAIN..."
certbot --nginx -d $DOMAIN \
    --agree-tos \
    --non-interactive \
    --email admin@automatizaciones-physis.cloud \
    --redirect

# Test auto-renewal
log_info "Probando auto-renovacion..."
certbot renew --dry-run

# Enable auto-renewal cron
systemctl enable certbot.timer
systemctl start certbot.timer

log_info "==============================================="
log_info "SSL configurado correctamente!"
log_info "==============================================="
echo ""
echo "Certificado: /etc/letsencrypt/live/automatizaciones-physis.cloud/"
echo "Renovacion automatica: activada"
echo ""
echo "Prueba: https://$DOMAIN"
echo ""
