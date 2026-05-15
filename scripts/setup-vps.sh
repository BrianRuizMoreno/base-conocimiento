#!/bin/bash
set -e

echo "==============================================="
echo "  RAG System - VPS Setup Script"
echo "  Server: conocimiento.automatizaciones-physis.cloud"
echo "==============================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    log_error "Por favor ejecuta como root (sudo)"
    exit 1
fi

# Get VPS IP
VPS_IP=$(curl -s ifconfig.me)
log_info "IP detectada: $VPS_IP"

# Update system
log_info "Actualizando sistema..."
apt update && apt upgrade -y

# Install dependencies
log_info "Instalando dependencias..."
apt install -y \
    nginx \
    certbot \
    python3-certbot-nginx \
    git \
    curl \
    ufw \
    fail2ban

# Install Docker
log_info "Instalando Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    usermod -aG docker $SUDO_USER
    rm get-docker.sh
else
    log_warn "Docker ya esta instalado"
fi

# Install Docker Compose
log_info "Instalando Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
else
    log_warn "Docker Compose ya esta instalado"
fi

# Configure UFW Firewall
log_info "Configurando firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw --force enable

# Configure Fail2ban
log_info "Configurando Fail2ban..."
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
EOF

systemctl enable fail2ban
systemctl start fail2ban

# Clone project
log_info "Clonando proyecto..."
PROJECT_DIR="/opt/base-conocimiento"
if [ -d "$PROJECT_DIR" ]; then
    log_warn "El directorio ya existe. Actualizando..."
    cd "$PROJECT_DIR"
    git pull origin main
else
    git clone https://github.com/BrianRuizMoreno/base-conocimiento.git "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

# Configure Nginx
log_info "Configurando Nginx..."
cp nginx/conocimiento.conf /etc/nginx/sites-available/conocimiento
ln -sf /etc/nginx/sites-available/conocimiento /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test Nginx config
nginx -t
systemctl restart nginx
systemctl enable nginx

# Create .env file
log_info "Creando archivo .env..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    log_warn "IMPORTANTE: Edita el archivo .env con tus credenciales"
    log_warn "Ubicacion: $PROJECT_DIR/.env"
fi

# Setup SSL (will be done after DNS propagation)
log_info "==============================================="
log_info "Configuracion basica completa!"
log_info "==============================================="
echo ""
log_warn "PASOS MANUALES PENDIENTES:"
echo ""
echo "1. Edita el archivo .env:"
echo "   nano $PROJECT_DIR/.env"
echo ""
echo "   Variables requeridas:"
echo "   - DATABASE_URL (tu PostgreSQL existente)"
echo "   - ADMIN_PIN_HASH (genera con: python3 -c \"import bcrypt; print(bcrypt.hashpw(b'TU_PIN', bcrypt.gensalt()).decode())\")"
echo "   - SECRET_KEY (string aleatorio de 32+ caracteres)"
echo "   - GEMINI_API_KEY (opcional pero recomendado)"
echo ""
echo "2. Verifica que el DNS este propagado:"
echo "   nslookup conocimiento.automatizaciones-physis.cloud"
echo ""
echo "3. Ejecuta el script de SSL:"
echo "   bash scripts/setup-ssl.sh"
echo ""
echo "4. Inicia los contenedores:"
echo "   cd $PROJECT_DIR && docker-compose up -d"
echo ""
echo "5. Verifica el estado:"
echo "   curl https://conocimiento.automatizaciones-physis.cloud/api/v1/health"
echo ""
