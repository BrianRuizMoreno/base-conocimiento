"""Auth router."""

from fastapi import APIRouter, HTTPException, Header, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.security import verify_pin
from app.core.config import settings

router = APIRouter()


@router.post("/verify")
async def verify_auth(
    x_auth_pin: str = Header(..., alias="X-Auth-PIN"),
    db: AsyncSession = Depends(get_db)
):
    """Verify admin PIN."""
    if not verify_pin(x_auth_pin, settings.ADMIN_PIN_HASH):
        raise HTTPException(status_code=401, detail="PIN invalido")
    return {"success": True, "data": {"role": "admin"}}
