# RAG System - Guia Rapida de Configuracion VPS

## Datos de tu VPS
- **IP:** `72.60.12.96`
- **Dominio:** `conocimiento.automatizaciones-physis.cloud`
- **Repositorio:** `https://github.com/BrianRuizMoreno/base-conocimiento`

---

## PASO 1: Conectar al VPS

```bash
ssh root@72.60.12.96
# Password: (tu contrasena)
```

---

## PASO 2: Ejecutar Setup Automatico

```bash
# Descargar y ejecutar script
curl -fsSL https://raw.githubusercontent.com/BrianRuizMoreno/base-conocimiento/main/scripts/setup-vps.sh | bash
```

**O manualmente:**

```bash
# 1. Actualizar
apt update && apt upgrade -y

# 2. Instalar dependencias
apt install -y nginx certbot python3-certbot-nginx git curl ufw fail2ban

# 3. Instalar Docker
curl -fsSL https://get.docker.com | bash
usermod -aG docker root

# 4. Instalar Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 5. Clonar proyecto
cd /opt
git clone https://github.com/BrianRuizMoreno/base-conocimiento.git
cd base-conocimiento

# 6. Copiar nginx config
cp nginx/conocimiento.conf /etc/nginx/sites-available/
ln -sf /etc/nginx/sites-available/conocimiento.conf /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

# 7. Firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw --force enable
```

---

## PASO 3: Configurar .env

```bash
cd /opt/base-conocimiento
cp .env.example .env
nano .env
```

**Variables OBLIGATORIAS:**

```env
# PostgreSQL (tu base existente)
DATABASE_URL=postgresql+asyncpg://usuario:password@IP_POSTGRES:5432/rag_system

# PIN de admin (genera primero)
ADMIN_PIN_HASH=$2b$12$...

# Clave secreta (32+ caracteres aleatorios)
SECRET_KEY=tu-clave-secreta-muy-larga-aqui

# Gemini API Key (recomendado)
GEMINI_API_KEY=tu-api-key-de-gemini
```

**Generar PIN hash:**
```bash
python3 -c "import bcrypt; print(bcrypt.hashpw(b'TU_PIN_AQUI', bcrypt.gensalt()).decode())"
```

---

## PASO 4: Configurar SSL

```bash
cd /opt/base-conocimiento
bash scripts/setup-ssl.sh
```

**O manualmente:**
```bash
certbot --nginx -d conocimiento.automatizaciones-physis.cloud --agree-tos --non-interactive --email tu@email.com
```

---

## PASO 5: Iniciar Proyecto

```bash
cd /opt/base-conocimiento
docker-compose up -d

# Verificar
docker-compose ps
curl http://localhost:8000/api/v1/health
```

---

## PASO 6: Verificar en Navegador

Abre:
- Frontend: `https://conocimiento.automatizaciones-physis.cloud`
- API Docs: `https://conocimiento.automatizaciones-physis.cloud/api/docs`
- Health: `https://conocimiento.automatizaciones-physis.cloud/api/v1/health`

---

## Comandos Utiles

```bash
# Ver logs
docker-compose logs -f rag-backend
docker-compose logs -f rag-frontend

# Reiniciar
docker-compose restart

# Actualizar (git pull + rebuild)
cd /opt/base-conocimiento
git pull
docker-compose down
docker-compose up -d --build

# Backup DB
pg_dump -h IP_POSTGRES -U usuario rag_system > backup_$(date +%Y%m%d).sql

# Ver SSL
certbot certificates
```

---

## Solucion de Problemas

### Error: "Cannot connect to Docker daemon"
```bash
systemctl start docker
systemctl enable docker
```

### Error: "Connection refused" a PostgreSQL
- Verificar que PostgreSQL acepta conexiones externas
- Verificar credenciales en `.env`

### Error SSL: "No valid IP addresses"
- Esperar 5-30 min a que propague el DNS
- Verificar: `nslookup conocimiento.automatizaciones-physis.cloud`

### Error: "Permission denied" en /opt
```bash
chmod -R 755 /opt/base-conocimiento
```

---

## Contacto

Si tienes problemas, revisa:
1. Logs: `docker-compose logs`
2. Estado: `docker-compose ps`
3. Documentacion: `docs/` en el repo
