# Guia de Despliegue - RAG System en Docker Swarm / Portainer

> **Pre-requisito:** Ya tienes PostgreSQL con pgvector instalado y la base de datos `rag_system` creada.

---

## Paso 1: Conectar tu PostgreSQL a la red de Docker Swarm

Tu PostgreSQL ya existe en Portainer. Para que el backend lo vea, tenes que conectarlo a una **overlay network**.

### 1.1 Crear la red (una sola vez)

Conectate por SSH a tu servidor y ejecuta:

```bash
docker network create --driver overlay --attachable rag-network
```

### 1.2 Conectar tu contenedor PostgreSQL a esa red

En Portainer:
1. Andá a tu **Stack de PostgreSQL**
2. Editá el stack y agregale al servicio de postgres:

```yaml
networks:
  - rag-network
```

O si preferis por SSH:

```bash
docker network connect rag-network nombre-de-tu-contenedor-postgres
```

---

## Paso 2: Preparar el .env en tu servidor

Conectate por SSH a tu servidor:

```bash
mkdir -p ~/rag-system && cd ~/rag-system
```

Crea el archivo `.env`:

```bash
nano .env
```

Pega y completa **solo estos 3 campos**:

```env
# ============ CAMBIAR ESTOS 3 ============

# URL de tu PostgreSQL (si esta en el mismo swarm, usa el nombre del servicio)
# Ejemplo si tu servicio de postgres se llama "postgres" en el stack "db":
DATABASE_URL=postgresql+asyncpg://postgres:TU_PASSWORD@postgres:5432/rag_system

# Si tu PostgreSQL esta en otro stack o IP fija, usa la IP interna:
# DATABASE_URL=postgresql+asyncpg://postgres:TU_PASSWORD@172.18.0.2:5432/rag_system

# Hash bcrypt de tu PIN (generar en tu PC con Python)
ADMIN_PIN_HASH=$2b$12$...

# Clave secreta (generar con: openssl rand -base64 32)
SECRET_KEY=tu-clave-secreta-32-caracteres-minimo

# ============ DEJAR TODO ESTO IGUAL ============
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=http://localhost:3000
MAX_FILE_SIZE=524288000
UPLOAD_DIR=/app/data
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
DEFAULT_TEMPERATURE=0.2
DEFAULT_TOP_P=0.6
DEFAULT_MAX_TOKENS=2048
N8N_WEBHOOK_URL=
```

**Guardar:** `Ctrl+O`, `Enter`, `Ctrl+X`

---

## Paso 3: Descargar el docker-compose.swarm.yml

```bash
curl -o docker-compose.swarm.yml https://raw.githubusercontent.com/BrianRuizMoreno/base-conocimiento/main/docker-compose.swarm.yml
```

O si clonaste el repo completo:

```bash
git clone https://github.com/BrianRuizMoreno/base-conocimiento.git
cd base-conocimiento
cp docker-compose.swarm.yml ~/rag-system/
cp .env.example ~/rag-system/.env
```

---

## Paso 4: Deploy en Docker Swarm

```bash
cd ~/rag-system
docker stack deploy -c docker-compose.swarm.yml rag-system --with-registry-auth
```

Esto levanta:
- **Backend:** puerto `8000`
- **Frontend:** puerto `3000`

---

## Paso 5: Verificar que levanto bien

```bash
# Ver los servicios
docker service ls | grep rag

# Ver logs del backend
docker service logs rag-system_rag-backend -f

# Ver logs del frontend
docker service logs rag-system_rag-frontend -f
```

Espera 1-2 minutos a que las imagenes se descarguen y el backend inicie.

---

## Paso 6: Probar que funciona

Desde tu PC o del mismo servidor:

```bash
curl http://IP_DE_TU_SERVIDOR:8000/api/v1/health
```

Deberia responder:
```json
{"status": "ok", "database": "connected"}
```

Abri el navegador:
```
http://IP_DE_TU_SERVIDOR:3000
```

Ingresa tu PIN.

---

## Paso 7: Agregar API Key de Gemini (desde el panel)

1. Entra a **Admin > Configuracion**
2. En **API Keys**, selecciona **Gemini**
3. Pega tu key de [Google AI Studio](https://aistudio.google.com/app/apikey)
4. Dale un label y prioridad `0`
5. Click en **Agregar**

Listo, el sistema ya puede hacer OCR, chat y embeddings.

---

## Paso 8: (Opcional) Dominio + HTTPS con Traefik

Si tenes Traefik en tu Swarm, agrega labels al `docker-compose.swarm.yml`:

```yaml
  rag-frontend:
    # ... lo que ya esta ...
    deploy:
      labels:
        - "traefik.enable=true"
        - "traefik.http.routers.rag.rule=Host(`tu-dominio.com`)"
        - "traefik.http.routers.rag.entrypoints=websecure"
        - "traefik.http.routers.rag.tls.certresolver=letsencrypt"
        - "traefik.http.services.rag.loadbalancer.server.port=80"
```

Y quita el `ports: - "3000:80"` si no queres acceso directo por IP.

---

## Comandos utiles para mantenimiento

```bash
# Ver estado de todo el stack
docker stack ps rag-system

# Ver logs en vivo del backend
docker service logs rag-system_rag-backend -f --tail 100

# Reiniciar un servicio
docker service update --force rag-system_rag-backend

# Escalar backend a 2 replicas (si tenes mas RAM)
docker service scale rag-system_rag-backend=2

# Eliminar todo el stack (CUIDADO, no borra volumenes)
docker stack rm rag-system

# Ver volumenes
docker volume ls | grep rag
```

---

## Si algo falla...

### "Cannot connect to database"

Tu PostgreSQL no esta en la misma red `rag-network`. Verificar:

```bash
# Ver en que red esta tu postgres
docker inspect nombre-contenedor-postgres -f '{{json .NetworkSettings.Networks}}'

# Conectarlo manualmente
docker network connect rag-network nombre-contenedor-postgres
```

### "Connection refused" al puerto 8000

El backend aun no termino de iniciar. Espera 2 minutos o revisa logs:

```bash
docker service logs rag-system_rag-backend --tail 50
```

### Frontend muestra "502 Bad Gateway"

El frontend no llega al backend. Verifica que `VITE_API_URL` en el `docker-compose.swarm.yml` tenga la **IP publica o interna correcta** de tu servidor, no `localhost`.

---

**Repositorio:** https://github.com/BrianRuizMoreno/base-conocimiento
