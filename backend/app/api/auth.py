"""Auth router."""

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.core.security import verify_pin
from app.core.config import settings
from app.db.models import User

router = APIRouter()


class AuthRequest(BaseModel):
    pin: str


class AuthResponse(BaseModel):
    success: bool
    data: dict | None = None
    error: str | None = None


@router.post("/verify", response_model=AuthResponse)
async def verify_auth(
    request: AuthRequest,
    db: AsyncSession = Depends(get_db)
):
    """Verify admin PIN."""
    # First check if admin user exists in DB
    result = await db.execute(select(User).where(User.username == "admin"))
    admin = result.scalar_one_or_none()
    
    if admin and verify_pin(request.pin, admin.pin_hash):
        return AuthResponse(
            success=True,
            data={"role": admin.role, "username": admin.username}
        )
    
    # Fallback to env PIN hash
    if settings.ADMIN_PIN_HASH and verify_pin(request.pin, settings.ADMIN_PIN_HASH):
        return AuthResponse(
            success=True,
            data={"role": "admin", "username": "admin"}
        )
    
    return AuthResponse(success=False, error="PIN invalido")


async def require_auth(x_auth_pin: str = Header(..., alias="X-Auth-PIN"), db: AsyncSession = Depends(get_db)):
    """Dependency to require authentication."""
    result = await db.execute(select(User).where(User.username == "admin"))
    admin = result.scalar_one_or_none()
    
    if admin and verify_pin(x_auth_pin, admin.pin_hash):
        return admin
    
    if settings.ADMIN_PIN_HASH and verify_pin(x_auth_pin, settings.ADMIN_PIN_HASH):
        if admin:
            return admin
        # If env PIN matches but no DB user exists, return a minimal user object
        return User(
            id="00000000-0000-0000-0000-000000000000",
            username="admin",
            pin_hash=settings.ADMIN_PIN_HASH,
            role="admin",
            is_active=True
        )
    
    raise HTTPException(status_code=401, detail="PIN invalido")
