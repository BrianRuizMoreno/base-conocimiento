# Guia de Despliegue - RAG System

## Opcion recomendada: Docker Compose (todo automatico)

El `docker-compose.yml` incluido levanta **todo automatico**: PostgreSQL + pgvector, backend FastAPI y frontend Nginx.

### Requisitos

- Docker + Docker Compose instalados
- Git

### 1. Clonar el repositorio

```bash
git clone https://github.com/BrianRuizMoreno/base-conocimiento.git
cd base-conocimiento
```

### 2. Configurar variables de entorno (solo 2 campos)

```bash
cp .env.example .env
```

Edita `.env` y **solo cambia estos 2 valores**:

```env
ADMIN_PIN_HASH=          # Hash bcrypt de tu PIN (ver paso 3)
SECRET_KEY=              # Clave aleatoria de 32+ caracteres (ver paso 4)
```

**Deja todo lo demas igual.** PostgreSQL ya esta configurado para Docker.

### 3. Generar tu PIN de admin

```bash
# En cualquier terminal con Python:
python3 -c "import bcrypt; print(bcrypt.hashpw(b'TU_PIN_AQUI', bcrypt.gensalt()).decode())"
```

Ejemplo si tu PIN es `1234`:
```bash
python3 -c "import bcrypt; print(bcrypt.hashpw(b'1234', bcrypt.gensalt()).decode())"
```

Copia el hash resultado y pegalo en `ADMIN_PIN_HASH` del `.env`.

### 4. Generar SECRET_KEY

```bash
openssl rand -base64 32
```

Copia el resultado y pegalo en `SECRET_KEY` del `.env`.

### 5. Levantar todo

```bash
docker-compose up -d --build
```

Esto construye y levanta 3 servicios:
- **PostgreSQL + pgvector:** puerto `5432`
- **Backend FastAPI:** `http://TU_IP:8000`
- **Frontend Nginx:** `http://TU_IP:3000`

### 6. Verificar que funciona

```bash
# Espera 20 segundos a que todo inicie...
curl http://localhost:8000/api/v1/health
```

Respuesta esperada:
```json
{"status": "ok", "database": "connected"}
```

### 7. Acceder al sistema

Abre en tu navegador:
```
http://TU_IP:3000
```

Ingresa el PIN que pusiste en el paso 3.

---

## Primer uso: agregar API Key de Gemini

1. Entra al panel: **Admin > Configuracion**
2. En "API Keys", selecciona proveedor **Gemini**
3. Pega tu API key de [Google AI Studio](https://aistudio.google.com/app/apikey)
4. Dale un label (ej: "Key principal") y prioridad `0`
5. Click en **Agregar**

Ahora el sistema puede hacer OCR, chat y embeddings.

---

## Comandos utiles

```bash
# Ver logs
docker-compose logs -f rag-backend
docker-compose logs -f rag-postgres

# Reiniciar
docker-compose restart

# Actualizar despues de git pull
git pull origin main
docker-compose up -d --build

# Detener todo
docker-compose down

# Detener y borrar datos (CUIDADO)
docker-compose down -v
```

---

## Opcion alternativa: PostgreSQL externo (Portainer)

Si ya tienes PostgreSQL en Portainer u otro servidor:

1. Asegurate de que tenga la extension `pgvector`:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

2. Cambia `DATABASE_URL` en `.env`:
   ```env
   DATABASE_URL=postgresql+asyncpg://TU_USER:TU_PASS@TU_IP:5432/TU_DB
   ```

3. Borra o comenta el servicio `postgres` del `docker-compose.yml`.

4. Levanta solo backend + frontend:
   ```bash
   docker-compose up -d --build rag-backend rag-frontend
   ```
