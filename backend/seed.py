import asyncio
import logging
from app.core.database import engine, Base, AsyncSessionLocal
from scripts.generate_demo_credentials import generate_and_seed_credentials

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

# Alias seed_data for backwards compatibility with pytest suite
seed_data = generate_and_seed_credentials

async def seed_db():
    logger.info("Starting database schema creation and full district/officer seeding...")
    await generate_and_seed_credentials()
    logger.info("Database seeding completed successfully.")

if __name__ == "__main__":
    asyncio.run(seed_db())
