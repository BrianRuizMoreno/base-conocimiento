---
name: security-patterns
description: Security for the RAG system. PIN bcrypt hashing, API key encryption with Fernet, file upload validation, CORS, rate limiting, SQL injection prevention via SQLAlchemy.
---

# Security Patterns

## PIN Authentication
```python
import bcrypt
from fastapi import HTTPException, Header

ADMIN_PIN_HASH = os.getenv("ADMIN_PIN_HASH")

def verify_pin(pin: str) -> bool:
    return bcrypt.checkpw(pin.encode(), ADMIN_PIN_HASH.encode())

async def require_auth(x_auth_pin: str = Header(...)):
    if not verify_pin(x_auth_pin):
        raise HTTPException(status_code=401, detail="PIN inválido")
```

## API Key Encryption
```python
from cryptography.fernet import Fernet
import os

# Generate once: Fernet.generate_key()
ENCRYPTION_KEY = os.getenv("SECRET_KEY").encode()[:32] + b"=" * (32 - len(os.getenv("SECRET_KEY")) % 32)
cipher = Fernet(ENCRYPTION_KEY[:32] + b"=")

def encrypt_api_key(key: str) -> str:
    return cipher.encrypt(key.encode()).decode()

def decrypt_api_key(encrypted: str) -> str:
    return cipher.decrypt(encrypted.encode()).decode()
```

## API Key Validation (Integration Endpoints)
```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def validate_api_key(api_key: str = Security(api_key_header), db: AsyncSession = Depends(get_db)):
    # Hash prefix for lookup
    prefix = api_key[:8]
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    stmt = select(IntegrationKey).where(
        IntegrationKey.key_prefix == prefix,
        IntegrationKey.key_hash == key_hash,
        IntegrationKey.is_active == True
    )
    result = await db.execute(stmt)
    key = result.scalar_one_or_none()
    
    if not key:
        raise HTTPException(status_code=403, detail="API Key inválida")
    
    if key.expires_at and key.expires_at < datetime.now():
        raise HTTPException(status_code=403, detail="API Key expirada")
    
    # Update last_used
    key.last_used_at = datetime.now()
    await db.commit()
    
    return key
```

## File Upload Security
```python
from fastapi import UploadFile
import magic

ALLOWED_TYPES = {
    'application/pdf': 'pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
    'text/markdown': 'md',
    'application/json': 'json',
    'text/xml': 'xml',
    'image/jpeg': 'image',
    'image/png': 'image',
    'audio/mpeg': 'audio',
    'video/mp4': 'video',
}

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB

def validate_upload(file: UploadFile) -> str:
    # Check mime type
    content = file.file.read(2048)
    file.file.seek(0)
    mime = magic.from_buffer(content, mime=True)
    
    if mime not in ALLOWED_TYPES:
        raise HTTPException(400, f"Tipo de archivo no permitido: {mime}")
    
    # Check size (stream limit)
    # Handled by UploadFile size limit in FastAPI
    
    return ALLOWED_TYPES[mime]
```

## Rate Limiting
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Apply to chat endpoint
@app.post("/api/v1/chat")
@limiter.limit("30/minute")
async def chat(request: Request, ...):
    ...
```

## CORS
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

## SQL Injection Prevention
All queries use SQLAlchemy ORM (parameterized queries). Never use raw SQL concatenation.
