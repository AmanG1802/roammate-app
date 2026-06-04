from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Pool is configured explicitly: the SQLAlchemy default (5 + 10 overflow) lets
# requests silently queue on connection acquisition once concurrency climbs,
# which is indistinguishable from "the app is slow". See docs/[31] D1.
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    future=True,
    echo=False,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db():
    # Commit only on a clean exit; roll back if the handler raised (or caught
    # and re-raised) mid-mutation so a half-applied transaction is never
    # committed by the trailing commit. See docs/[31] D2.
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
