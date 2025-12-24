import uuid
from contextlib import asynccontextmanager

import pandas as pd
from sqlalchemy import (
    Boolean,
    Column,
    Double,
    Integer,
    String,
    create_engine,
    delete,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Mindflow(Base):
    __tablename__ = "mindflows"
    user_id = Column(Integer, nullable=False)
    id = Column(
        String, nullable=False, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    last_modified = Column(Double, nullable=False)
    notes = Column(String, nullable=False)


class Reflection(Base):
    __tablename__ = "reflections"
    user_id = Column(Integer, nullable=False)
    id = Column(
        String, nullable=False, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    last_modified = Column(Double, nullable=False)
    time_spent = Column(Integer, nullable=False)
    is_interrupt_successfull = Column(Boolean, nullable=False)
    notes = Column(String, default=lambda: None)


class Reminder(Base):
    __tablename__ = "reminders"
    user_id = Column(Integer, nullable=False)
    id = Column(
        String, nullable=False, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    chat_id = Column(Integer, nullable=False)
    last_modified = Column(Double, nullable=False)
    scheduled_at = Column(Double, nullable=False)
    header = Column(String, default=lambda: None)


class Setting(Base):
    __tablename__ = "settings"
    user_id = Column(Integer, nullable=False)
    id = Column(
        String, nullable=False, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    salute_speech = Column(String, nullable=False)


engine = create_async_engine(
    "sqlite+aiosqlite:///data/user_data.db",
    echo=True,
    future=True,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def load_to_df(query):
    async with get_session() as session:
        result = await session.execute(query)
        result = result.scalars().all()

        df = pd.DataFrame([r.__dict__ for r in result])
        df = df.drop("_sa_instance_state", axis=1, errors="ignore")
        return df
