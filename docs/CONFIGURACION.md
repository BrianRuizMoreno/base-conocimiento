# Manual de Configuración

## Índice
1. [Requisitos Previos](#requisitos-previos)
2. [Variables de Entorno](#variables-de-entorno)
3. [Obtener API Keys](#obtener-api-keys)
4. [Configurar PostgreSQL](#configurar-postgresql)
5. [Generar PIN de Admin](#generar-pin-de-admin)
6. [Despliegue Docker](#despliegue-docker)
7. [Configurar Modelos](#configurar-modelos)
8. [Primer Arranque](#primer-arranque)
9. [Solución de Problemas](#solución-de-problemas)

---

## Requisitos Previos

- VPS con Docker y Docker Compose instalados
- PostgreSQL 14+ con extensión pgvector
- 8GB RAM mínimo (tu VPS tiene 8GB ✓)
- 100GB almacenamiento (tu VPS tiene 100GB ✓)
- Puertos 8000 (backend) y 3000 (frontend) disponibles

## Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
# ─── Database ───
# Tu PostgreSQL existente en Portainer
DATABASE_URL=postgresql+asyncpg://USUARIO:PASSWORD@IP_DEL_POSTGRES:5432/rag_system

# ─── Seguridad ───
ADMIN_PIN_HASH=$2b$12$...          # Hash bcrypt del PIN (ver sección abajo)
SECRET_KEY=tu-clave-secreta-32-chars-o-mas

# ─── Proveedores IA (completa los que vas a usar) ───
GEMINI_API_KEY=tu-api-key-de-gemini
OPENAI_API_KEY=sk-...               # opcional
ANTHROPIC_API_KEY=sk-ant-...        # opcional

# ─── Web Search ───
TAVILY_API_KEY=tvly-...             # opcional, para comparativa de mercado

# ─── Environment ───
ENVIRONMENT=production
```

## Obtener API Keys

### Google Gemini (OCR + Chat + Embeddings — Gratis)
1. Ve a [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Crea una API Key
3. Copia la clave a `GEMINI_API_KEY`
4. Límite gratuito: 1,500 requests/día

### OpenAI (Chat + Embeddings — Opcional)
1. Ve a [OpenAI Platform](https://platform.openai.com/api-keys)
2. Crea una API Key
3. Copia a `OPENAI_API_KEY`

### Anthropic Claude (Chat — Opcional)
1. Ve a [Anthropic Console](https://console.anthropic.com/)
2. Crea una API Key
3. Copia a `ANTHROPIC_API_KEY`

### Tavily (Web Search — Opcional)
1. Ve a [Tavily](https://tavily.com/)
2. Regístrate (1,000 búsquedas gratis/mes)
3. Copia la API Key a `TAVILY_API_KEY`

## Configurar PostgreSQL

### 1. Crear la base de datos
```sql
CREATE DATABASE rag_system;
```

### 2. Instalar pgvector
```sql
\c rag_system
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. Verificar
```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

## Generar PIN de Admin

El sistema usa un PIN simple para autenticación del administrador.

```python
import bcrypt

pin = "1234"  # Cambia esto por tu PIN seguro
hashed = bcrypt.hashpw(pin.encode(), bcrypt.gensalt())
print(hashed.decode())
```

Copia el hash generado a `ADMIN_PIN_HASH` en tu `.env`.

## Despliegue Docker

### 1. Construir imágenes
```bash
docker-compose build
```

### 2. Iniciar servicios
```bash
docker-compose up -d
```

### 3. Verificar estado
```bash
# Backend
curl http://localhost:8000/api/v1/health

# Frontend
# Abre http://localhost:3000 en tu navegador
```

### 4. Ver logs
```bash
docker-compose logs -f rag-backend
docker-compose logs -f rag-frontend
```

## Configurar Modelos (desde la UI)

Una vez desplegado, accede al panel de administración:

1. Ve a **Configuración** → **Proveedores**
2. Ingresa las API keys
3. Selecciona el modelo para Chat (ej: `gemini-2.0-flash`)
4. Ajusta parámetros:
   - **Top-P**: 0.6 (default)
   - **Temperatura**: 0.2 (default)
5. Selecciona el modelo para Embeddings (ej: `text-embedding-004`)
6. Guardar

## Primer Arranque

1. Abre http://localhost:3000
2. Ingresa tu PIN de admin
3. Crea tu primera colección de conocimiento
4. Sube un documento de prueba
5. Ve a Chat y haz una pregunta

## Solución de Problemas

### Error: "pgvector extension not found"
```bash
# Conecta a tu PostgreSQL y ejecuta:
CREATE EXTENSION IF NOT EXISTS vector;
```

### Error: "Connection refused" al backend
- Verifica que PostgreSQL esté accesible desde la red Docker
- Revisa `DATABASE_URL` en `.env`

### Error: "API key invalid" en Gemini
- Verifica que la API key esté activa en Google AI Studio
- Revisa que no hayas excedido el límite diario (1,500 requests)

### Error: "Permission denied" en carpeta data/
```bash
chmod -R 777 data/
```

### Puerto ya en uso
Edita `docker-compose.yml` y cambia los puertos:
```yaml
ports:
  - "8080:8000"    # backend
  - "8081:80"      # frontend
```

## Actualización

Para actualizar el sistema después de cambios:

```bash
git pull  # si usas git
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```
