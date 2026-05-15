# Guía de Despliegue

## Requisitos del Servidor

- VPS con Docker y Docker Compose
- PostgreSQL 14+ con pgvector
- 8GB RAM mínimo
- 100GB almacenamiento
- Puertos 8000 y 3000 disponibles

## Pasos de Despliegue

### 1. Clonar/Preparar el Proyecto

```bash
cd /opt
# Si usas git:
git clone <repo-url> rag-system
cd rag-system

# O copia los archivos manualmente
```

### 2. Configurar Variables de Entorno

```bash
cp .env.example .env
nano .env
```

Completa todas las variables (ver CONFIGURACION.md).

### 3. Verificar PostgreSQL

```bash
# Conecta a tu PostgreSQL (desde pgAdmin o psql)
psql -h localhost -U tu_usuario -d postgres

# Crear base de datos
CREATE DATABASE rag_system;
\c rag_system
CREATE EXTENSION IF NOT EXISTS vector;
```

### 4. Construir e Iniciar

```bash
docker-compose build
docker-compose up -d
```

### 5. Verificar Health Checks

```bash
# Backend
curl http://localhost:8000/api/v1/health
# Debe responder: {"status": "ok"}

# Frontend
# Abre http://tu-ip:3000
```

### 6. Configurar en Portainer

1. Abre Portainer en tu navegador
2. Ve a **Stacks** → **Add Stack**
3. Nombre: `rag-system`
4. Copia el contenido de `docker-compose.yml`
5. En **Environment variables**, pega tu `.env`
6. Click **Deploy the stack**

### 7. Configurar Dominio (opcional)

Si tienes un dominio apuntando a tu VPS:

```nginx
# /etc/nginx/sites-available/rag
server {
    listen 80;
    server_name rag.tudominio.com;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/rag /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Comandos Útiles

```bash
# Ver logs en tiempo real
docker-compose logs -f rag-backend
docker-compose logs -f rag-frontend

# Reiniciar servicio
docker-compose restart rag-backend

# Reconstruir sin caché
docker-compose build --no-cache

# Entrar al contenedor
docker-compose exec rag-backend bash

# Backup de base de datos
docker-compose exec postgres pg_dump -U user rag_system > backup.sql

# Restaurar base de datos
docker-compose exec -T postgres psql -U user rag_system < backup.sql
```

## Actualización

```bash
# Detener
docker-compose down

# Actualizar código
git pull

# Reconstruir
docker-compose build --no-cache

# Migrar base de datos
docker-compose run rag-backend alembic upgrade head

# Iniciar
docker-compose up -d
```

## Troubleshooting

### Contenedor no inicia
```bash
docker-compose logs rag-backend
# Busca errores de conexión a DB o falta de variables
```

### Migraciones fallan
```bash
docker-compose exec rag-backend alembic history
# Si hay conflictos:
docker-compose exec rag-backend alembic stamp head
docker-compose exec rag-backend alembic revision --autogenerate -m "fix"
docker-compose exec rag-backend alembic upgrade head
```

### Permisos de archivos
```bash
# Si no puede escribir en data/
sudo chown -R $USER:$USER data/
chmod -R 777 data/
```
