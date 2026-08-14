from __future__ import annotations

import json
from typing import Any

import httpx

from .types import EnrichedProduct

GRAPHQL_URL = "{shop}/admin/api/2024-10/graphql.json"
REST_PRODUCTS_URL = "{shop}/admin/api/2024-10/products.json"


def _shop_url(shop: str) -> str:
    shop = shop.strip()
    if not shop.startswith("http"):
        shop = "https://" + shop
    return shop.rstrip("/")


async def _upload_image(client: httpx.AsyncClient, shop: str, image_url: str) -> str | None:
    """Return an HTTPS image URL Shopify can fetch. We just pass the source URL
    and let Shopify fetch it via the product create payload."""
    return image_url


async def create_product(
    shop: str, access_token: str, product: EnrichedProduct, *, timeout: float = 60.0
) -> dict[str, Any]:
    """Create a product on Shopify using the REST Admin API (simple, reliable)."""
    base = _shop_url(shop)
    headers = {"X-Shopify-Access-Token": access_token, "Content-Type": "application/json"}

    images = [{"src": u} for u in product.raw.image_urls if u]
    tags = ",".join(product.tags_ar[:8]) if product.tags_ar else (product.raw.category or "")

    body = {
        "product": {
            "title": product.title_en or product.raw.title,
            "body_html": f"<p>{(product.description_en or product.raw.description).replace(chr(10), '</p><p>')}</p>",
            "vendor": "Supplier",
            "product_type": product.raw.category or "General",
            "tags": tags,
            "variants": [{"price": str(product.raw.price or "0.00")}],
            "images": images,
            "status": "active",
            "metafields": [
                {"namespace": "global", "key": "title_ar", "value": product.title_ar, "type": "single_line_text_field"},
                {
                    "namespace": "global",
                    "key": "description_ar",
                    "value": product.description_ar,
                    "type": "multi_line_text_field",
                },
            ],
        }
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(
                REST_PRODUCTS_URL.format(shop=base), json=body, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            pid = data.get("product", {}).get("id")
            return {"ok": True, "id": pid, "platform": "shopify"}
        except httpx.HTTPStatusError as exc:
            return {"ok": False, "error": f"{exc.response.status_code}: {exc.response.text[:300]}"}
        except httpx.HTTPError as exc:
            return {"ok": False, "error": str(exc)}


async def verify(shop: str, access_token: str, *, timeout: float = 20.0) -> bool:
    base = _shop_url(shop)
    headers = {"X-Shopify-Access-Token": access_token}
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.get(
                f"{base}/admin/api/2024-10/shop.json", headers=headers
            )
            return resp.status_code == 200
        except httpx.HTTPError:
            return False
