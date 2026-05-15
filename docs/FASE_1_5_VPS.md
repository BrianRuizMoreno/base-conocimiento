# Fase 1.5: Configuración VPS + SSL + Autodeploy

## Checklist de Configuración

### 1. GitHub Secrets (configurar en el repo)

Ve a tu repo → Settings → Secrets and variables → Actions → New repository secret

| Secret Name | Value | Descripción |
|---|---|---|
| `VPS_HOST` | `72.60.12.96` | IP de tu VPS |
| `VPS_USER` | `root` | Usuario SSH |
| `VPS_PASSWORD` | `Physis-princ1p@l` | Contraseña SSH |

⚠️ **IMPORTANTE**: Después de configurar esto, considera:
- Cambiar la contraseña root por una más segura
- O mejor: usar SSH keys en lugar de contraseña

### 2. Configurar DNS en Hostinger

Ya creado:
- A Record: `conocimiento` → `72.60.12.96` (TTL: 5000)

Verificar propagación:
```bash
nslookup conocimiento.automatizaciones-physis.cloud
```

### 3. Configurar VPS (conectar por SSH)

```bash
# Conectar
ssh root@72.60.12.96
# Password: Physis-princ1p@l

# 1. Actualizar sistema
apt update && apt upgrade -y

# 2. Instalar dependencias
apt install -y nginx certbot python3-certbot-nginx git docker.io docker-compose

# 3. Clonar proyecto
mkdir -p /opt
cd /opt
git clone https://github.com/BrianRuizMoreno/base-conocimiento.git
cd base-conocimiento

# 4. Crear .env
cp .env.example .env
nano .env
```

Editar `.env`:
```env
DATABASE_URL=postgresql+asyncpg://TU_USUARIO:TU_PASSWORD@TU_IP_POSTGRES:5432/rag_system
ADMIN_PIN_HASH=$2b$12$...  # bcrypt hash de tu PIN
SECRET_KEY=tu-clave-secreta-muy-larga-32-caracteres
GEMINI_API_KEY=tu-api-key
```

```bash
# 5. Configurar Nginx
cat > /etc/nginx/sites-available/conocimiento << 'EOF'
server {
    listen 80;
    server_name conocimiento.automatizaciones-physis.cloud;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name conocimiento.automatizaciones-physis.cloud;
    
    ssl_certificate /etc/letsencrypt/live/automatizaciones-physis.cloud/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/automatizaciones-physis.cloud/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Activar sitio
ln -sf /etc/nginx/sites-available/conocimiento /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

# 6. Obtener SSL (Let's Encrypt)
certbot --nginx -d conocimiento.automatizaciones-physis.cloud \
  --agree-tos --non-interactive \
  --email tu-email@ejemplo.com

# Verificar auto-renovación
certbot renew --dry-run

# 7. Iniciar proyecto
cd /opt/base-conocimiento
docker-compose up -d

# 8. Verificar
curl http://localhost:8000/api/v1/health
```

### 4. Cambiar repo a privado (opcional)

GitHub repo → Settings → Danger Zone → Change visibility → Private

### 5. Verificar Deploy Automático

Haz cualquier cambio en `main` y haz push. GitHub Actions se activará automáticamente.

Monitor: Repo → Actions tab

### 6. URLs Finales

| URL | Servicio |
|---|---|
| `https://conocimiento.automatizaciones-physis.cloud` | Frontend (React) |
| `https://conocimiento.automatizaciones-physis.cloud/api` | Backend API |
| `https://conocimiento.automatizaciones-physis.cloud/api/docs` | Swagger UI |

## Seguridad Recomendada

1. **Cambiar contraseña root** después de la configuración inicial
2. **Usar SSH keys** en lugar de contraseña para GitHub Actions
3. **Desactivar login root por SSH** después de configurar un usuario sudo
4. **UFW Firewall**:
   ```bash
   ufw default deny incoming
   ufw default allow outgoing
   ufw allow ssh
   ufw allow http
   ufw allow https
   ufw enable
   ```

## Troubleshooting

### Certbot falla
```bash
# Verificar que el dominio resuelve a tu IP
dig conocimiento.automatizaciones-physis.cloud

# Verificar que Nginx sirve el challenge
curl http://conocimiento.automatizaciones-physis.cloud/.well-known/acme-challenge/test
```

### Docker no inicia
```bash
# Ver logs
docker-compose logs rag-backend
docker-compose logs rag-frontend

# Reiniciar
docker-compose restart
```

### GitHub Actions falla
```bash
# Verificar que el VPS es accesible desde GitHub
# Revisar secrets en GitHub repo settings
```
