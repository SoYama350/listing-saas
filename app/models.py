from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Customer(Base):
    """A store owner whose products we list. Can be you or a client."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int | None] = mapped_column(index=True, unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(200), default="Me")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    stores: Mapped[list[Store]] = relationship(back_populates="customer", cascade="all, delete-orphan")
    jobs: Mapped[list[Job]] = relationship(back_populates="customer", cascade="all, delete-orphan")


class Store(Base):
    """A connected Shopify or Salla store."""

    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"))
    platform: Mapped[str] = mapped_column(String(20))  # 'shopify' | 'salla'
    name: Mapped[str] = mapped_column(String(200))
    shop: Mapped[str] = mapped_column(String(200))  # my-store.myshopify.com or salla subdomain
    access_token_enc: Mapped[str] = mapped_column(Text)  # encrypted
    extra_enc: Mapped[str] = mapped_column(Text, default="")  # encrypted json (e.g. salla refresh token)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    customer: Mapped[Customer] = relationship(back_populates="stores")


class Job(Base):
    """One product-listing run (one sheet -> many products)."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"))
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"))
    sheet_url: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|running|done|error
    total: Mapped[int] = mapped_column(default=0)
    done: Mapped[int] = mapped_column(default=0)
    failed: Mapped[int] = mapped_column(default=0)
    report: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    customer: Mapped[Customer] = relationship(back_populates="jobs")


async def init_db(engine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
