"""Settings router."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db

router = APIRouter()

# TODO: Implement settings endpoints
# GET / - get current settings
# PUT / - update settings
# GET /keys - list API keys
# POST /keys - save API key
# DELETE /keys/{provider} - remove API key
# GET /integration-keys - list integration keys
# POST /integration-keys - create integration key
# DELETE /integration-keys/{id} - revoke key
