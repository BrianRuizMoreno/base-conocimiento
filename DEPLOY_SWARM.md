# Guia de Despliegue - RAG System en tu Docker Swarm / Portainer

> **Pre-requisito:** Ya tienes PostgreSQL con pgvector instalado, base de datos `rag_system` creada, y la extension `vector` activada.
>
> Tu PostgreSQL esta en la red `PhysisNet` (ya configurada).

---

## Paso 1: Crear el archivo .env en tu servidor

Conectate por SSH a tu servidor:

```bash
mkdir -p ~/rag-system && cd ~/rag-system
nano .env
```

Pega esto (la base de datos ya esta configurada para tu PostgreSQL):

```env
# ============ CAMBIAR ESTOS 2 ============

# Hash bcrypt de tu PIN (generar con Python, ver abajo)
ADMIN_PIN_HASH=

# Clave secreta (generar con: openssl rand -base64 32)
SECRET_KEY=

# ============ DEJAR TODO ESTO IGUAL ============
DATABASE_URL=postgresql+asyncpg://postgres:e4f0a7582698c2064991b82c788479@postgres:5432/rag_system
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

### Como generar ADMIN_PIN_HASH

Desde tu PC o el servidor (necesitas Python con bcrypt):

```bash
python3 -c "import bcrypt; print(bcrypt.hashpw(b'1234', bcrypt.gensalt()).decode())"
```

Reemplaza `1234` con el PIN que quieras. Copia el hash largo que devuelve y pegalo en `ADMIN_PIN_HASH`.

### Como generar SECRET_KEY

```bash
openssl rand -base64 32
```

Copia el resultado y pegalo en `SECRET_KEY`.

---

## Paso 2: Descargar el archivo de Docker Swarm

En la misma terminal (dentro de `~/rag-system`):

```bash
curl -o docker-compose.swarm.yml https://raw.githubusercontent.com/BrianRuizMoreno/base-conocimiento/main/docker-compose.swarm.yml
```

---

## Paso 3: Corregir la IP del backend

Abrí el archivo:

```bash
nano docker-compose.swarm.yml
```

Buscá esta línea:

```yaml
VITE_API_URL=http://TU_IP_O_DOMINIO:8000/api/v1
```

Cambiala por la **IP publica de tu VPS** (la que usas para entrar a Portainer):

```yaml
VITE_API_URL=http://123.456.78.90:8000/api/v1
```

**Guardar:** `Ctrl+O`, `Enter`, `Ctrl+X`

---

## Paso 4: Deploy en Docker Swarm

```bash
cd ~/rag-system
docker stack deploy -c docker-compose.swarm.yml rag-system
```

Esto levanta:
- **Backend:** `http://TU_IP:8000`
- **Frontend:** `http://TU_IP:3000`

Espera 2-3 minutos a que descargue las imagenes e inicie.

---

## Paso 5: Verificar que levanto bien

```bash
# Ver los servicios activos
docker service ls | grep rag

# Ver logs del backend (espera a que diga "Application startup complete")
docker service logs rag-system_rag-backend -f
```

Cuando veas que termino de iniciar, probá:

```bash
curl http://localhost:8000/api/v1/health
```

Deberia responder:
```json
{"status": "ok", "database": "connected"}
```

---

## Paso 6: Entrar al sistema

Abri tu navegador:

```
http://TU_IP:3000
```

Ingresa el PIN que pusiste en el paso 1.

---

## Paso 7: Agregar API Key de Gemini (desde el panel)

1. Entra a **Admin > Configuracion**
2. En **API Keys**, selecciona **Gemini**
3. Pega tu key de [Google AI Studio](https://aistudio.google.com/app/apikey)
4. Dale un label (ej: "Principal") y prioridad `0`
5. Click en **Agregar**

Listo, el sistema ya puede hacer OCR, chat y embeddings.

---

## Comandos utiles para el futuro

```bash
# Ver logs del backend en vivo
docker service logs rag-system_rag-backend -f --tail 100

# Reiniciar el backend
docker service update --force rag-system_rag-backend

# Ver que contenedores estan corriendo
docker stack ps rag-system

# Eliminar todo el stack (CUIDADO, no borra volumenes)
docker stack rm rag-system
```

---

## Si algo falla...

### "Cannot connect to database"

Tu PostgreSQL no esta en la red `PhysisNet`. Verificar:

```bash
# Ver en que red esta tu postgres
docker inspect nombre-contenedor-postgres -f '{{json .NetworkSettings.Networks}}'
```

Deberia mostrar `PhysisNet`. Si no esta, conectarlo:

```bash
docker network connect PhysisNet nombre-contenedor-postgres
```

Luego reinicia el stack:

```bash
docker service update --force rag-system_rag-backend
```

### Frontend muestra "502 Bad Gateway" o no carga

Verifica que `VITE_API_URL` tenga la **IP publica** de tu servidor, no `localhost`.

### Puerto 8000 o 3000 ya en uso

Si tenes Traefik u otro proxy en el puerto 80/443, cambia los puertos en el `docker-compose.swarm.yml`:

```yaml
    ports:
      - "8001:8000"  # Backend en 8001
```

Y recuerda cambiar tambien `VITE_API_URL` para que apunte al nuevo puerto.

---

**Repositorio:** https://github.com/BrianRuizMoreno/base-conocimiento
