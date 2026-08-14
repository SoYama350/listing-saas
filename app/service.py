from __future__ import annotations

from typing import Awaitable

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .config import decrypt, encrypt
from .db import db_session
from .models import Customer, Job, Store
from . import shopify, salla


async def get_or_create_customer(telegram_id: int | None, name: str = "Me") -> Customer:
    async with db_session() as s:
        if telegram_id is not None:
            q = await s.execute(select(Customer).where(Customer.telegram_id == telegram_id))
            cust = q.scalar_one_or_none()
            if cust:
                return cust
        cust = Customer(telegram_id=telegram_id, name=name)
        s.add(cust)
        await s.commit()
        await s.refresh(cust)
        return cust


async def list_stores(customer_id: int) -> list[Store]:
    async with db_session() as s:
        q = await s.execute(
            select(Store).where(Store.customer_id == customer_id).order_by(Store.created_at.desc())
        )
        return list(q.scalars())


async def add_store(
    customer_id: int,
    platform: str,
    name: str,
    shop: str,
    access_token: str,
    extra: str = "",
    make_default: bool = False,
) -> tuple[Store, str]:
    """Returns (store, message). Verifies the token first."""
    ok = False
    if platform == "shopify":
        ok = await shopify.verify(shop, access_token)
    elif platform == "salla":
        ok = await salla.verify(shop, access_token)
    if not ok:
        return None, "❌ Could not verify the store credentials. Check the shop URL and access token."

    async with db_session() as s:
        if make_default:
            q = await s.execute(select(Store).where(Store.customer_id == customer_id))
            for st in q.scalars():
                st.is_default = False
        store = Store(
            customer_id=customer_id,
            platform=platform,
            name=name or shop,
            shop=shop,
            access_token_enc=encrypt(access_token),
            extra_enc=encrypt(extra) if extra else "",
            is_default=make_default,
        )
        s.add(store)
        await s.commit()
        await s.refresh(store)
        return store, f"✅ {platform.title()} store '{store.name}' connected."


async def get_default_store(customer_id: int) -> Store | None:
    async with db_session() as s:
        q = await s.execute(
            select(Store)
            .where(Store.customer_id == customer_id)
            .order_by(Store.is_default.desc(), Store.created_at.desc())
        )
        return q.scalars().first()


async def list_jobs(customer_id: int, limit: int = 20) -> list[Job]:
    async with db_session() as s:
        q = await s.execute(
            select(Job)
            .where(Job.customer_id == customer_id)
            .order_by(Job.created_at.desc())
            .limit(limit)
        )
        return list(q.scalars())


async def create_job(customer_id: int, sheet_url: str) -> Job:
    store = await get_default_store(customer_id)
    if not store:
        raise ValueError("No store connected. Add a Shopify/Salla store first.")
    async with db_session() as s:
        job = Job(customer_id=customer_id, store_id=store.id, sheet_url=sheet_url, status="pending")
        s.add(job)
        await s.commit()
        await s.refresh(job)
        return job
