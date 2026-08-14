from __future__ import annotations

import json
from typing import Any

import httpx

from .config import settings
from .types import EnrichedProduct, RawProduct

SYSTEM_PROMPT = (
    "You are an expert e-commerce copywriter for Shopify and Salla stores in the MENA market. "
    "You write fluent Modern Standard Arabic and clean English. "
    "You always return ONLY valid JSON, no markdown, no explanation."
)


def _user_prompt(p: RawProduct) -> str:
    tags = ", ".join(p.tags) if p.tags else "(none)"
    imgs = ", ".join(p.image_urls) if p.image_urls else "(none)"
    return json.dumps(
        {
            "task": "Generate localized product listing content from the raw supplier data.",
            "input": {
                "raw_title": p.title,
                "raw_price": p.price,
                "raw_description": p.description,
                "category": p.category,
                "supplier_tags": tags,
                "image_urls": imgs,
                "supplier_link": p.supplier_link,
            },
            "output_schema": {
                "title_ar": "string - catchy Arabic title (<=80 chars)",
                "title_en": "string - catchy English title (<=80 chars)",
                "description_ar": "string - persuasive Arabic description, 2-4 short paragraphs, "
                "mention key features & benefits. Use line breaks.",
                "description_en": "string - persuasive English description, 2-4 short paragraphs, "
                "mention key features & benefits. Use line breaks.",
                "tags_ar": "array of strings - 5-8 Arabic search tags",
                "category_ar": "string - Arabic category name (infer from product)",
            },
            "rules": [
                "Return ONLY a JSON object matching the schema, nothing else.",
                "Never invent specs that contradict the input; infer general category only.",
                "Prices: do not include, the caller sets them.",
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[-1] if text.startswith("json") else text
    # find first { ... last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


async def enrich_product(p: RawProduct, *, timeout: float = 60.0) -> EnrichedProduct:
    """Call the LLM to produce AR+EN titles, descriptions, tags."""
    ep = EnrichedProduct(raw=p)
    if not settings.openrouter_api_key:
        # No key configured: degrade gracefully using raw data
        ep.title_ar = p.title
        ep.title_en = p.title
        ep.description_ar = p.description or p.title
        ep.description_en = p.description or p.title
        ep.tags_ar = p.tags or [p.category or p.title]
        ep.category_ar = p.category or "عام"
        return ep

    payload = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _user_prompt(p)},
        ],
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.base_url,
        "X-Title": "Listing SaaS",
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()
    content = data["choices"][0]["message"]["content"]
    parsed = _extract_json(content)
    ep.title_ar = parsed.get("title_ar") or p.title
    ep.title_en = parsed.get("title_en") or p.title
    ep.description_ar = parsed.get("description_ar") or p.description or p.title
    ep.description_en = parsed.get("description_en") or p.description or p.title
    ep.tags_ar = parsed.get("tags_ar") or []
    ep.category_ar = parsed.get("category_ar") or p.category or "عام"
    return ep
