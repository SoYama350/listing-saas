from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Awaitable, Callable

from sqlalchemy import select

from . import salla, shopify
from .config import decrypt
from .db import db_session
from .llm import enrich_product
from .models import Job, Store
from .sheets import read_sheet
from .types import EnrichedProduct

ProgressCb = Callable[[str], Awaitable[None]]


@dataclass
class JobContext:
    job_id: int
    store_id: int


async def _load_store(store_id: int) -> Store | None:
    async with db_session() as s:
        st = await s.get(Store, store_id)
        if st:
            await s.refresh(st)
        return st


async def _push(platform: str, shop: str, token: str, ep: EnrichedProduct) -> dict:
    if platform == "shopify":
        return await shopify.create_product(shop, token, ep)
    return await salla.create_product(shop, token, ep)


def _qa_sample(products: list[EnrichedProduct], n: int = 5) -> str:
    if not products:
        return "No products to QA."
    sample = random.sample(products, min(n, len(products)))
    lines = [f"🔍 QA sample ({len(sample)} of {len(products)}):"]
    for i, ep in enumerate(sample, 1):
        status = "✅" if ep.pushed else "❌"
        lines.append(
            f"{status} {i}. {ep.title_en or ep.raw.title}\n"
            f"   AR: {ep.title_ar}\n   Tags: {', '.join(ep.tags_ar[:5])}"
        )
        if ep.error:
            lines.append(f"   ⚠️ {ep.error[:120]}")
    return "\n".join(lines)


async def run_job(job_id: int, progress: ProgressCb | None = None) -> None:
    async def say(msg: str) -> None:
        if progress:
            await progress(msg)

    async with db_session() as s:
        job = await s.get(Job, job_id)
        if not job:
            return
        job.status = "running"
        await s.commit()

    try:
        await say("📥 Reading your Google Sheet…")
        store = await _load_store(job.store_id)
        if not store:
            raise RuntimeError("Store not found")
        token = decrypt(store.access_token_enc)

        raw_products = await read_sheet(job.sheet_url)
        total = len(raw_products)
        async with db_session() as s:
            j = await s.get(Job, job_id)
            j.total = total
            await s.commit()
        await say(f"✅ Found {total} products. Generating listings…")

        enriched: list[EnrichedProduct] = []
        done = 0
        failed = 0
        for idx, rp in enumerate(raw_products, 1):
            ep = EnrichedProduct(raw=rp)
            try:
                ep = await enrich_product(rp)
                result = await _push(store.platform, store.shop, token, ep)
                if result.get("ok"):
                    ep.pushed = True
                    ep.shopify_result = result if store.platform == "shopify" else {}
                    ep.salla_result = result if store.platform == "salla" else {}
                    done += 1
                else:
                    ep.error = result.get("error", "unknown")
                    failed += 1
                    await say(f"⚠️ [{idx}/{total}] {rp.title[:40]} → {ep.error[:80]}")
            except Exception as exc:  # noqa: BLE001
                ep.error = str(exc)[:200]
                failed += 1
            enriched.append(ep)

            if idx % 5 == 0 or idx == total:
                async with db_session() as s:
                    j = await s.get(Job, job_id)
                    j.done = done
                    j.failed = failed
                    await s.commit()
                await say(f"📊 Progress: {idx}/{total} (✅ {done}, ❌ {failed})")

        qa = _qa_sample(enriched)
        report = (
            f"📦 Job complete.\nTotal: {total}\nPublished: {done}\nFailed: {failed}\n\n{qa}"
        )
        async with db_session() as s:
            j = await s.get(Job, job_id)
            j.status = "done" if failed == 0 else ("done" if done > 0 else "error")
            j.done = done
            j.failed = failed
            j.report = report
            await s.commit()
        await say(report)

    except Exception as exc:  # noqa: BLE001
        async with db_session() as s:
            j = await s.get(Job, job_id)
            j.status = "error"
            j.report = f"❌ Job failed: {exc}"
            await s.commit()
        await say(f"❌ Job failed: {exc}")
