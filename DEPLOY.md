# Guia de Despliegue - RAG System

## Requisitos del Servidor (VPS Hostinger)

- **SO:** Ubuntu 22.04 LTS
- **RAM:** 8 GB (minimo recomendado)
- **CPU:** 2 cores
- **Disco:** 100 GB SSD
- **Docker + Docker Compose** instalados
- **PostgreSQL 15+ con pgvector** (puede ser contenedor o instancia gestionada)

## Estructura del Proyecto

```
rag-system/
├── backend/          # FastAPI + Alembic
├── frontend/         # React + Vite + Nginx
├── data/             # Uploads de documentos (volumen Docker)
├── docker-compose.yml
└── .env
```

## 1. Preparar el Servidor

### 1.1 Instalar Docker y Docker Compose

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

### 1.2 Preparar PostgreSQL con pgvector

Si tienes PostgreSQL externo (Portainer), asegurate de que la extension `pgvector` este instalada:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Si prefieres levantar PostgreSQL local con Docker:

```bash
docker run -d \
  --name rag-postgres \
  -e POSTGRES_USER=raguser \
  -e POSTGRES_PASSWORD=ragpass \
  -e POSTGRES_DB=rag_system \
  -v pgdata:/var/lib/postgresql/data \
  -p 5432:5432 \
  ankane/pgvector:latest
```

## 2. Configurar Variables de Entorno

```bash
cp .env.example .env
nano .env
```

Valores minimos requeridos:

```env
DATABASE_URL=postgresql+asyncpg://raguser:ragpass@TU_IP:5432/rag_system
ADMIN_PIN_HASH=$2b$12$...  # bcrypt hash de tu PIN
SECRET_KEY=tu-clave-secreta-32-caracteres-minimo
GEMINI_API_KEY=tu-api-key-de-gemini
ENVIRONMENT=production
CORS_ORIGINS=https://tu-dominio.com
```

**Generar PIN hash:**

```bash
python3 -c "import bcrypt; print(bcrypt.hashpw(b'TU_PIN', bcrypt.gensalt()).decode())"
```

**Generar SECRET_KEY:**

```bash
openssl rand -base64 32
```

## 3. Desplegar con Docker Compose

```bash
git clone https://github.com/BrianRuizMoreno/base-conocimiento.git
cd base-conocimiento
```

### Opcion A: Despliegue local/directo

```bash
docker-compose up -d --build
```

Esto construye y levanta:
- **Backend:** http://localhost:8000
- **Frontend:** http://localhost:3000

### Opcion B: Despliegue con Traefik (recomendado para produccion)

Si usas Traefik como reverse proxy:

```bash
docker-compose -f docker-compose-traefik.yml up -d --build
```

Configura tus labels de Traefik en el `docker-compose-traefik.yml`.

## 4. Verificar el Despliegue

### 4.1 Health check

```bash
curl http://localhost:8000/api/v1/health
```

Respuesta esperada:
```json
{"status": "ok", "version": "1.0.0", "database": "connected"}
```

### 4.2 Ver logs

```bash
# Backend
docker logs -f rag-backend

# Frontend
docker logs -f rag-frontend
```

### 4.3 Acceder al panel

Abre en tu navegador:
- Sin dominio: `http://TU_IP:3000`
- Con dominio: `https://tu-dominio.com`

Ingresa el PIN que configuraste en `ADMIN_PIN_HASH`.

## 5. Primer Uso

1. Ve a **Admin > Configuracion**
2. Agrega al menos una **API Key de Gemini** (gratis en aistudio.google.com)
3. Crea una **Coleccion** desde el Dashboard
4. Sube documentos (PDF, DOCX, imagenes, audio, video)
5. Ve al **Chat** y empieza a preguntar

## 6. Configurar n8n (Opcional)

1. En **Admin > Configuracion**, configura `N8N_WEBHOOK_URL`
2. Ve a **Admin > Sectores** y crea un sector
3. Genera un **Token de sector** para integracion
4. Usa el token en n8n con header `X-API-Key`

## 7. Mantenimiento

### Actualizar despues de git pull

```bash
git pull origin main
docker-compose up -d --build
```

### Backup de datos

```bash
# Backup PostgreSQL
docker exec rag-postgres pg_dump -U raguser rag_system > backup.sql

# Backup uploads
rsync -av data/ /ruta/backup/data/
```

### Escalado

Si necesitas mas capacidad:
- Aumenta `workers` en `backend/Dockerfile` (actualmente 2)
- Usa Redis para cachear embeddings
- Configura Celery para procesamiento en background

## Troubleshooting

| Problema | Solucion |
|---|---|
| `alembic upgrade head` falla | Verifica `DATABASE_URL` y que PostgreSQL tenga pgvector |
| Frontend no carga API | Verifica `CORS_ORIGINS` y que nginx apunte al backend correcto |
| OCR no funciona | Verifica que `GEMINI_API_KEY` este configurada |
| Archivos >20MB fallan | Verifica `MAX_FILE_SIZE` y espacio en disco |
| "PIN invalido" | Verifica que `ADMIN_PIN_HASH` sea bcrypt valido |

---

**URL del Repositorio:** https://github.com/BrianRuizMoreno/base-conocimiento
