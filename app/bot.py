from __future__ import annotations

import asyncio
import json
from typing import Any

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Message,
)
from sqlalchemy import select

from .config import settings
from .db import db_session
from .jobs import run_job
from .models import Customer, Store
from . import service

bot = Bot(settings.telegram_bot_token) if settings.telegram_bot_token else None
dp = Dispatcher(storage=MemoryStorage())


class Flow(StatesGroup):
    choosing_platform = State()
    entering_shop = State()
    entering_token = State()
    entering_name = State()
    waiting_sheet = State()


# ── keyboards ──────────────────────────────────────────────────────────
def _platform_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 Shopify"), KeyboardButton(text="🟣 Salla")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _main_kb(has_store: bool) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text="📋 New listing job (send sheet)")]]
    if has_store:
        rows.append([KeyboardButton(text="🔗 Add another store")])
    rows.append([KeyboardButton(text="🗂 My stores"), KeyboardButton(text="🆘 Help")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


# ── helpers ────────────────────────────────────────────────────────────
async def _customer(tg_id: int, name: str) -> Customer:
    return await service.get_or_create_customer(tg_id, name)


async def _default_store(customer_id: int) -> Store | None:
    async with db_session() as s:
        q = await s.execute(
            select(Store)
            .where(Store.customer_id == customer_id)
            .order_by(Store.is_default.desc(), Store.created_at.desc())
        )
        return q.scalars().first()


async def _send(chat_id: int, text: str) -> None:
    if not bot:
        return
    # Telegram cap is 4096; chunk long messages
    for i in range(0, len(text), 3800):
        await bot.send_message(chat_id, text[i : i + 3800])


# ── handlers ───────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext):
    cust = await _customer(m.from_user.id, m.from_user.full_name)
    store = await _default_store(cust.id)
    await state.clear()
    await state.update_data(customer_id=cust.id)
    if store:
        await state.set_state(Flow.waiting_sheet)
        await m.answer(
            f"👋 Hi {cust.name}!\n\n"
            f"Your default store: <b>{store.platform}</b> · {store.name}\n\n"
            "Send me a Google Sheet link (shared: anyone with the link) and I'll list the products.",
            reply_markup=_main_kb(has_store=True),
        )
    else:
        await m.answer(
            "👋 Welcome to <b>Listing SaaS</b>!\n\n"
            "I'll list products from your Google Sheet to Shopify or Salla.\n"
            "First, which platform?",
            reply_markup=_platform_kb(),
        )
        await state.set_state(Flow.choosing_platform)


@dp.message(Command("help"))
async def cmd_help(m: Message):
    await m.answer(
        "<b>Listing SaaS bot</b>\n\n"
        "1. /start — check your store profile\n"
        "2. Send a Google Sheet link → products go live\n"
        "3. 🔗 Add another store — connect a new Shopify/Salla store\n"
        "4. 🗂 My stores — list connected stores\n\n"
        "Each new chat reuses your stored store profile; if none, I'll ask for the API.\n\n"
        "Sheet columns: title, price, description, image(s), category, tags."
    )


@dp.message(F.text == "🆘 Help")
async def kb_help(m: Message):
    await cmd_help(m)


@dp.message(F.text == "🗂 My stores")
async def kb_stores(m: Message, state: FSMContext):
    cust = await _customer(m.from_user.id, m.from_user.full_name)
    stores = await service.list_stores(cust.id)
    if not stores:
        await m.answer("No stores yet. Tap 🔗 Add another store.")
        return
    lines = ["<b>Your stores:</b>"]
    for s in stores:
        star = " ⭐default" if s.is_default else ""
        lines.append(f"• <b>{s.platform}</b> · {s.name} ({s.shop}){star}")
    await m.answer("\n".join(lines))


@dp.message(F.text == "🔗 Add another store")
async def kb_add_store(m: Message, state: FSMContext):
    cust = await _customer(m.from_user.id, m.from_user.full_name)
    await state.update_data(customer_id=cust.id)
    await m.answer("Which platform?", reply_markup=_platform_kb())
    await state.set_state(Flow.choosing_platform)


@dp.message(Flow.choosing_platform)
async def chose_platform(m: Message, state: FSMContext):
    text = (m.text or "").lower()
    if "shopify" in text:
        platform = "shopify"
        hint = "Send the shop URL, e.g. <code>my-store.myshopify.com</code>"
    elif "salla" in text:
        platform = "salla"
        hint = "Send your Salla store slug (e.g. <code>mybrand</code>) or just <code>salla</code>"
    else:
        await m.answer("Please choose 🛒 Shopify or 🟣 Salla.", reply_markup=_platform_kb())
        return
    await state.update_data(platform=platform)
    await m.answer(hint, reply_markup=ReplyKeyboardRemove())
    await state.set_state(Flow.entering_shop)


@dp.message(Flow.entering_shop)
async def entered_shop(m: Message, state: FSMContext):
    shop = (m.text or "").strip()
    if not shop:
        await m.answer("Please send the shop URL.")
        return
    await state.update_data(shop=shop)
    await m.answer(
        "Now send the <b>access token</b> (Admin API token).\n"
        "I'll verify it, then encrypt & store it for future runs.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(Flow.entering_token)


@dp.message(Flow.entering_token)
async def entered_token(m: Message, state: FSMContext):
    token = (m.text or "").strip()
    if not token:
        await m.answer("Please send the access token.")
        return
    data = await state.get_data()
    cust = await _customer(m.from_user.id, m.from_user.full_name)
    store, msg = await service.add_store(
        cust.id, data["platform"], data.get("shop", ""), data["shop"], token, make_default=True
    )
    if not store:
        await m.answer(msg + "\n\nTap 🔗 Add another store to retry.", reply_markup=_main_kb(False))
        await state.clear()
        return
    await m.answer(msg, reply_markup=_main_kb(True))
    await state.clear()
    await state.set_state(Flow.waiting_sheet)
    await state.update_data(customer_id=cust.id)


@dp.message(Flow.waiting_sheet)
async def got_sheet(m: Message, state: FSMContext):
    text = (m.text or "").strip()
    if text in ("📋 New listing job (send sheet)",):
        await m.answer("Paste the Google Sheet link (shared: anyone with the link).")
        return
    if "docs.google.com/spreadsheets" not in text and not text.startswith("https://"):
        await m.answer("That doesn't look like a Google Sheet link. Send the full URL.")
        return
    cust = await _customer(m.from_user.id, m.from_user.full_name)
    store = await _default_store(cust.id)
    if not store:
        await m.answer("No store connected. Tap 🔗 Add another store first.")
        await state.set_state(Flow.choosing_platform)
        return
    try:
        job = await service.create_job(cust.id, text)
    except ValueError as exc:
        await m.answer(str(exc))
        return

    await m.answer(f"🚀 Job #{job.id} started on <b>{store.platform}</b> · {store.name}. I'll report progress here.")

    async def progress(msg: str) -> None:
        await _send(m.chat.id, msg)

    asyncio.create_task(run_job(job.id, progress=progress))
    await state.set_state(Flow.waiting_sheet)


@dp.message()
async def fallback(m: Message, state: FSMContext):
    current = await state.get_state()
    if current is None:
        await cmd_start(m, state)
    else:
        await m.answer("I didn't get that. /start to reset.")


async def main() -> None:
    if not bot:
        print("⚠️  TELEGRAM_BOT_TOKEN not set; bot disabled.")
        return
    await bot.delete_webhook(drop_pending_updates=True)
    print("🤖 Telegram bot polling…")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
