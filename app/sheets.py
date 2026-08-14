from __future__ import annotations

import csv
import io
import re
from typing import Iterable

import httpx

from .types import RawProduct

# turns /d/<id>/edit... or /spreadsheets/d/<id>/... into the CSV export url
_SHEET_ID_RE = re.compile(r"/(?:spreadsheets/)?d/(?P<id>[A-Za-z0-9_-]+)")


def _to_csv_urls(sheet_url: str) -> list[str]:
    m = _SHEET_ID_RE.search(sheet_url)
    if not m:
        # maybe it's already a bare id
        if re.fullmatch(r"[A-Za-z0-9_-]+", sheet_url.strip()):
            sid = sheet_url.strip()
        else:
            raise ValueError(f"Could not find a Google Sheet id in: {sheet_url}")
    else:
        sid = m.group("id")

    gid_m = re.search(r"[#&?]gid=(?P<gid>\d+)", sheet_url)
    gid = gid_m.group("gid") if gid_m else "0"
    return [
        f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv&gid={gid}",
        f"https://docs.google.com/spreadsheets/d/{sid}/gviz/tq?tqx=out:csv&gid={gid}",
    ]


def _split_urls(val: str) -> list[str]:
    parts = re.split(r"[\s,;|]+", val.strip())
    return [p for p in parts if p.startswith("http")]


def _row_to_product(headers: list[str], row: list[str]) -> RawProduct | None:
    rec = dict(zip(headers, row))
    norm = {k.strip().lower(): (v or "").strip() for k, v in rec.items()}

    def pick(*keys: str) -> str:
        for k in keys:
            for hk, hv in norm.items():
                if k in hk:
                    return hv
        return ""

    title = pick("title", "name", "product", "اسم", "المنتج", "الاسم")
    price = pick("price", "سعر", "السعر")
    if not title:
        return None

    images = _split_urls(pick("image", "img", "صور", "الصور", "رابط الصورة"))
    if not images:
        # maybe a column literally named 'image urls' with multiple links
        for hk, hv in norm.items():
            if "image" in hk or "صور" in hk:
                images.extend(_split_urls(hv))

    tags = [t.strip() for t in re.split(r"[,;|]", pick("tag", "وسم", "الوسم")) if t.strip()]
    return RawProduct(
        title=title,
        price=price,
        description=pick("desc", "description", "وصف", "الوصف", "details"),
        image_urls=images,
        category=pick("categ", "section", "قسم", "الفئة", "category"),
        tags=tags,
        supplier_link=pick("supplier", "source", "مورد", "رابط المورد", "link"),
    )


def _parse_csv(text: str) -> Iterable[RawProduct]:
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return []
    headers = rows[0]
    products: list[RawProduct] = []
    for row in rows[1:]:
        if not any(cell.strip() for cell in row):
            continue
        p = _row_to_product(headers, row)
        if p:
            products.append(p)
    return products


async def read_sheet(sheet_url: str, *, timeout: float = 30.0) -> list[RawProduct]:
    """Fetch a Google Sheet (public / anyone-with-link) and return parsed products."""
    urls = _to_csv_urls(sheet_url)
    last_err: Exception | None = None
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for url in urls:
            try:
                resp = await client.get(url)
                if resp.status_code == 200 and resp.text.strip():
                    products = list(_parse_csv(resp.text))
                    if products:
                        return products
            except httpx.HTTPError as exc:
                last_err = exc
    if last_err:
        raise last_err
    raise ValueError(
        "Could not read the sheet. Make sure it is shared as 'Anyone with the link - Viewer'."
    )
