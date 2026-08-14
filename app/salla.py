from __future__ import annotations

from typing import Any

import httpx

from .types import EnrichedProduct

BASE = "https://api.salla.dev/admin/v1"


async def create_product(
    shop: str, access_token: str, product: EnrichedProduct, *, timeout: float = 60.0
) -> dict[str, Any]:
    """Create a product on Salla using the Admin API (v1).

    access_token is the merchant OAuth access token.
    shop is the store slug (optional, used only for display).
    """
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    images = [{"src": u, "alt": product.title_ar} for u in product.raw.image_urls if u]
    price = str(product.raw.price or "0").strip()

    body: dict[str, Any] = {
        "name": product.title_ar or product.raw.title,
        "description": product.description_ar or product.raw.description,
        "price": {"amount": price, "currency": "SAR"},
        "product_type": "product",
        "status": "published",
        "images": images,
        "tags": [{"name": t} for t in (product.tags_ar or [product.category_ar])],
    }
    if product.raw.category:
        body["categories"] = [{"name": product.raw.category}]

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            resp = await client.post(f"{BASE}/products", json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            pid = data.get("data", {}).get("id") if isinstance(data, dict) else None
            return {"ok": True, "id": pid, "platform": "salla"}
        except httpx.HTTPStatusError as exc:
            return {"ok": False, "error": f"{exc.response.status_code}: {exc.response.text[:300]}"}
        except httpx.HTTPError as exc:
            return {"ok": False, "error": str(exc)}


async def verify(shop: str, access_token: str, *, timeout: float = 20.0) -> bool:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        try:
            resp = await client.get(f"{BASE}/store/info", headers=headers)
            return resp.status_code == 200
        except httpx.HTTPError:
            return False
