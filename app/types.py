from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RawProduct:
    title: str
    price: str
    description: str = ""
    image_urls: list[str] = field(default_factory=list)
    category: str = ""
    tags: list[str] = field(default_factory=list)
    supplier_link: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class EnrichedProduct:
    raw: RawProduct
    title_ar: str = ""
    title_en: str = ""
    description_ar: str = ""
    description_en: str = ""
    tags_ar: list[str] = field(default_factory=list)
    category_ar: str = ""
    shopify_result: dict[str, Any] = field(default_factory=dict)
    salla_result: dict[str, Any] = field(default_factory=dict)
    pushed: bool = False
    error: str = ""
