# 📦 Listing SaaS

**Upload a Google Sheet of products → they go live on Shopify or Salla** with auto-generated Arabic + English titles, descriptions, and tags. Run it from your **laptop** (web dashboard) or your **phone** (Telegram bot) — no laptop needed for daily use.

Built for the "50 products per store" freelance workflow: a client sends a sheet, you forward it to the bot, and the products get listed automatically with a QA report back to you.

---

## ✨ Features

- **Two platforms** — Shopify and Salla, switchable via a toggle (web) or buttons (Telegram)
- **Bilingual content** — AI generates Arabic + English titles, descriptions, and search tags from raw supplier data
- **Telegram bot** — fully conversational: asks for platform + API token on first chat, then reuses your stored profile so you can list from your phone
- **Web dashboard** — mobile-friendly, for when you're on a laptop
- **Encrypted credentials** — store access tokens are encrypted at rest (Fernet)
- **Live progress** — streams per-batch progress + a QA sample of 5 random products when done
- **Free to run** — OpenRouter free LLM model by default; Telegram is free

---

## 🏗️ Architecture

```
Google Sheet ──► FastAPI backend ──► OpenRouter LLM (AR+EN content)
                        │
                        ├──► Shopify Admin API  ──► products live
                        └──► Salla Admin API    ──► products live
                        │
            ┌───────────┴───────────┐
       Web dashboard (FastAPI)   Telegram bot (aiogram 3)
            (laptop)                 (phone)
```

| Component | Tech |
|---|---|
| Web dashboard | FastAPI + Jinja2 (mobile-first HTML) |
| Telegram bot | aiogram 3 (FSM conversational flow) |
| Store APIs | Shopify REST Admin API (2024-10), Salla Admin API v1 |
| LLM | OpenRouter (free model default; swappable) |
| Database | SQLite + SQLAlchemy async |
| Credential storage | Fernet (symmetric encryption) |

---

## 🚀 Quick start

### Prerequisites

- **Python 3.11+** ([install](https://www.python.org/downloads/))
- **pip** (comes with Python)
- A **Telegram account** (for the bot)
- An **OpenRouter account** (free signup → [openrouter.ai](https://openrouter.ai))
- A **Shopify or Salla store** with Admin API access (for real listings)

### 1. Get the code

```bash
git clone https://github.com/SoYama350/listing-saas.git
cd listing-saas
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **Tip:** use a virtual environment to keep things clean:
> ```bash
> python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
> pip install -r requirements.txt
> ```

### 3. Create your settings file

```bash
cp .env.example .env
```

Then open `.env` in any text editor and fill in the values (see [Configuration](#️-configuration) below).

### 4. Run it

```bash
python -m app.main
```

- **Web dashboard:** open <http://localhost:8000>
- **Telegram bot:** message your bot (the one you created with @BotFather)

Both run at the same time from one command.

---

## ⚙️ Configuration

All settings live in `.env`. Here's what each one means and where to get it:

| Variable | Required | What it is | How to get it |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes (for bot) | Your bot's token | Message `@BotFather` on Telegram → `/newbot` → copy the token |
| `OPENROUTER_API_KEY` | Yes (for AI content) | LLM API key | Sign up at [openrouter.ai](https://openrouter.ai) → Keys → create |
| `OPENROUTER_MODEL` | No | Which model to use | Default: `google/gemini-2.0-flash-exp:free`. See [models](https://openrouter.ai/models) |
| `CREDENTIAL_ENCRYPTION_KEY` | Yes | Encrypts store tokens at rest | Run this to generate one: <br>`python -c "import secrets,base64;print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"` |
| `APP_SECRET_KEY` | No | Signs web session cookies | Any long random string |
| `DATABASE_URL` | No | Database location | Default: `sqlite+aiosqlite:///./listingsaas.db` |
| `BASE_URL` | No | Your public URL (for OpenRouter referer) | Default: `http://localhost:8000` |
| `OWNER_TELEGRAM_ID` | No | Your Telegram user id (future admin) | Message `@userinfobot` on Telegram |

### Minimal `.env` example

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxx
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free
CREDENTIAL_ENCRYPTION_KEY=generated-key-from-the-command-above
```

---

## 📋 Google Sheet format

Share your sheet as **Anyone with the link → Viewer** (File → Share → General access → "Anyone with the link").

### Columns

The reader matches columns by name (fuzzy match), so order doesn't matter. English and Arabic names both work:

| Field | English names | Arabic names |
|---|---|---|
| Product name | `title`, `name`, `product` | `اسم`, `المنتج`, `الاسم` |
| Price | `price` | `سعر`, `السعر` |
| Description | `description`, `desc`, `details` | `وصف`, `الوصف` |
| Image(s) | `image`, `img` | `صور`, `الصور`, `رابط الصورة` |
| Category | `category`, `section` | `قسم`, `الفئة` |
| Tags | `tag`, `tags` | `وسم`, `الوسم` |
| Supplier link | `supplier`, `source`, `link` | `مورد`, `رابط المورد` |

### Example row

| title | price | description | image | category | tags |
|---|---|---|---|---|---|
| Wireless Earbuds Pro | 99 | Bluetooth 5.3, 30h battery | https://img.example.com/a.jpg | Electronics | audio, wireless, bluetooth |

**Multiple images:** put several URLs in one cell, separated by spaces, commas, or `|`:
```
https://img.example.com/a.jpg https://img.example.com/b.jpg
```

---

## 🔌 Connecting a store

### Shopify

1. In your Shopify admin: **Settings → Apps and sales channels → Develop apps → Create a custom app**
2. Give it **Admin API** access with the `write_products` scope
3. Install the app → copy the **Admin API access token**
4. In Listing SaaS (web or Telegram): platform = **Shopify**, shop = `your-store.myshopify.com`, token = the access token

### Salla

1. Go to the [Salla Partner Portal](https://salla.partners) → create an app
2. Complete OAuth for the merchant store → get the **access token** (Bearer)
3. In Listing SaaS: platform = **Salla**, shop = your store slug (e.g. `mybrand`), token = the access token

Both are **verified on save** (a test API call) and then **encrypted at rest**. If verification fails, you'll get a clear error and can retry.

---

## 🤖 Using the Telegram bot

The bot is conversational and remembers your store profile.

### First time (no store yet)

```
You: /start
Bot:  Welcome! Which platform?  [🛒 Shopify] [🟣 Salla]
You:  🛒 Shopify
Bot:  Send the shop URL, e.g. my-store.myshopify.com
You:  my-store.myshopify.com
Bot:  Now send the access token. I'll verify, then encrypt & store it.
You:  shpat_xxxxxxxxxxxx
Bot:  ✅ Shopify store 'my-store' connected.
      Send me a Google Sheet link and I'll list the products.
```

### Every time after (profile saved)

```
You: /start
Bot:  Hi! Your default store: Shopify · my-store
      Send me a Google Sheet link and I'll list the products.
You:  https://docs.google.com/spreadsheets/d/...
Bot:  🚀 Job #1 started on Shopify · my-store. I'll report progress here.
Bot:  📥 Reading your Google Sheet…
Bot:  ✅ Found 50 products. Generating listings…
Bot:  📊 Progress: 5/50 (✅ 5, ❌ 0)
Bot:  📊 Progress: 10/50 (✅ 10, ❌ 0)
...
Bot:  📦 Job complete. Total: 50, Published: 50, Failed: 0
      🔍 QA sample (5 of 50):
      ✅ 1. Wireless Earbuds Pro
         AR: سماعات لاسلكية برو
         Tags: سماعات, لاسلكي, بلوتوث
      ...
```

### Bot commands & buttons

| Action | How |
|---|---|
| Start / check profile | `/start` |
| Help | `/help` or the 🆘 Help button |
| List your stores | 🗂 My stores |
| Add another store | 🔗 Add another store |
| Run a listing job | send a Google Sheet link |

---

## 🖥️ Using the web dashboard

1. Open <http://localhost:8000> → enter your name on the login screen
2. **Connect a store:** expand "+ Connect a store", pick Shopify/Salla, enter shop URL + token → it verifies and saves
3. **Start a job:** paste a Google Sheet link → "Start job"
4. **Watch progress:** the Recent jobs card shows status, counts, and the QA report

---

## ☁️ Deploying (so the bot runs 24/7)

The Telegram bot must be always-on to receive messages. Your laptop works for testing, but a server is better long-term.

### Easy option: Render / Railway

1. Push this repo to GitHub
2. Create a new web service from the repo on [Render](https://render.com) or [Railway](https://railway.app)
3. Build command: `pip install -r requirements.txt`
4. Start command: `python -m app.main`
5. Add all `.env` variables in the dashboard
6. Expose port `8000`

### VPS option (cheapest, ~$5/mo)

1. Rent a VPS (DigitalOcean, Hetzner, Contabo)
2. SSH in, clone the repo, install deps
3. Run with a process manager so it restarts on crash:
   ```bash
   # install uvicorn already done via requirements; use nohup for a quick test:
   nohup python -m app.main > app.log 2>&1 &
   ```
   For production, use `systemd` or `pm2` or `supervisor` (see `docs/deployment.md`).

---

## 💰 Cost

| Item | Cost |
|---|---|
| Hosting | $0 (laptop) to ~$5/mo (VPS) |
| LLM (OpenRouter free model) | $0 |
| Telegram bot | $0 |
| Shopify/Salla API | Free (included with your store) |

If you want higher-quality AI content, switch `OPENROUTER_MODEL` to a paid model (a few cents per 50 products).

---

## 🗂 Project structure

```
app/
├── main.py        # entry point: runs web + bot together
├── web.py         # FastAPI dashboard
├── bot.py         # Telegram bot (aiogram)
├── jobs.py        # job orchestrator (parse → enrich → push → QA)
├── sheets.py      # Google Sheet reader (CSV export)
├── llm.py         # OpenRouter LLM client (AR+EN content)
├── shopify.py     # Shopify Admin API client
├── salla.py       # Salla Admin API client
├── service.py     # business logic (customers, stores, jobs)
├── models.py      # SQLAlchemy models
├── db.py          # async DB setup
├── config.py      # settings + encryption
├── types.py       # dataclasses (RawProduct, EnrichedProduct)
└── templates/
    ├── index.html  # dashboard
    └── login.html
```

---

## 🛣️ Roadmap

- [ ] WhatsApp channel (needs WhatsApp Business API / Twilio)
- [ ] Multi-tenant: clients self-serve (log in, paste their own sheet + store key)
- [ ] Billing (Stripe / Tap)
- [ ] OpenHands Cloud as the automation backend (drop-in replacement for `enrich_product`)
- [ ] CSV bulk export as a fallback to direct API

---

## ❓ Troubleshooting

**"Could not read the sheet"** → Make sure the sheet is shared as *Anyone with the link → Viewer*. The bot can't read private sheets.

**"Could not verify the store credentials"** → Check the shop URL format and that the access token has `write_products` permission.

**Bot doesn't respond** → Confirm `TELEGRAM_BOT_TOKEN` is set and you messaged the *right* bot (the one BotFather gave you).

**AI content looks like the raw input** → `OPENROUTER_API_KEY` is empty, so it falls back to using raw data. Add your key.

**Port 8000 already in use** → Change the port in `app/main.py` (`port=8000`).

---

## 📄 License

MIT — use it, fork it, sell it. No warranty.
