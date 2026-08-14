from __future__ import annotations

import asyncio

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .config import settings
from .db import startup_db
from .jobs import run_job
from . import service

templates = Jinja2Templates(directory="app/templates")

app = FastAPI(title="Listing SaaS")


@app.on_event("startup")
async def _startup() -> None:
    await startup_db()


# ── simple session: store customer id in a signed cookie ──────────────
def _customer_id(request: Request) -> int:
    cid = request.cookies.get("cid")
    if not cid:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    try:
        return int(cid)
    except ValueError:
        raise HTTPException(status_code=303, headers={"Location": "/login"})


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    cid = request.cookies.get("cid")
    if not cid:
        return RedirectResponse("/login", status_code=303)
    customer = await service.get_or_create_customer(None)
    # update the customer name to 'Me' if needed (id-only flow)
    stores = await service.list_stores(int(cid))
    jobs = await service.list_jobs(int(cid))
    return templates.TemplateResponse(
        request,
        "index.html",
        {"stores": stores, "jobs": jobs, "customer_id": int(cid)},
    )


@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse(request, "login.html", {})


@app.post("/login")
async def login(name: str = Form("Me")):
    customer = await service.get_or_create_customer(None, name)
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie("cid", str(customer.id), httponly=True, max_age=60 * 60 * 24 * 30)
    return resp


@app.post("/stores")
async def add_store_route(
    request: Request,
    platform: str = Form(...),
    name: str = Form(""),
    shop: str = Form(...),
    access_token: str = Form(...),
    make_default: bool = Form(False),
):
    cid = _customer_id(request)
    store, msg = await service.add_store(cid, platform, name, shop, access_token, make_default=make_default or True)
    # ignore message in redirect; show via query
    return RedirectResponse(f"/?msg={msg.replace(' ', '+')}", status_code=303)


@app.post("/jobs")
async def create_job_route(request: Request, sheet_url: str = Form(...)):
    cid = _customer_id(request)
    try:
        job = await service.create_job(cid, sheet_url)
    except ValueError as exc:
        return RedirectResponse(f"/?msg={str(exc).replace(' ', '+')}", status_code=303)
    asyncio.create_task(run_job(job.id))
    return RedirectResponse(f"/?msg=Job+{job.id}+started", status_code=303)


@app.get("/healthz")
async def healthz():
    return {"ok": True}
