"""Seed data for initial setup."""

import asyncio
import bcrypt
from sqlalchemy import select
from app.db.database import SessionLocal
from app.db.models import User, Pricing
from app.core.config import settings


async def seed_database():
    """Create initial data if not exists."""
    async with SessionLocal() as session:
        # Check if admin exists
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            print("Creating admin user...")
            # Create admin user from env PIN hash
            admin = User(
                username="admin",
                pin_hash=settings.ADMIN_PIN_HASH,
                role="admin",
                is_active=True
            )
            session.add(admin)
        
        # Seed pricing data
        result = await session.execute(select(Pricing))
        if not result.scalars().first():
            print("Seeding pricing data...")
            pricing_data = [
                Pricing(provider="gemini", model="gemini-2.0-flash", input_price_per_1m=0.0, output_price_per_1m=0.0),
                Pricing(provider="gemini", model="gemini-2.5-flash", input_price_per_1m=0.15, output_price_per_1m=0.6),
                Pricing(provider="gemini", model="text-embedding-004", input_price_per_1m=0.0, output_price_per_1m=0.0),
                Pricing(provider="openai", model="gpt-4o-mini", input_price_per_1m=0.15, output_price_per_1m=0.6),
                Pricing(provider="openai", model="gpt-4o", input_price_per_1m=2.5, output_price_per_1m=10.0),
                Pricing(provider="openai", model="text-embedding-3-small", input_price_per_1m=0.02, output_price_per_1m=0.0),
                Pricing(provider="anthropic", model="claude-3-haiku", input_price_per_1m=0.25, output_price_per_1m=1.25),
                Pricing(provider="anthropic", model="claude-3.5-sonnet", input_price_per_1m=3.0, output_price_per_1m=15.0),
            ]
            session.add_all(pricing_data)
        
        await session.commit()
        print("Seed completed!")


if __name__ == "__main__":
    asyncio.run(seed_database())
