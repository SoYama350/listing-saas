# Deployment guide

This guide covers running Listing SaaS permanently so the Telegram bot is always online.

## Option 1 — Render / Railway (easiest, free tier available)

1. Push this repo to GitHub.
2. Go to [Render](https://render.com) → New → Web Service → connect the GitHub repo.
3. Settings:
   - **Environment:** Python 3
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `python -m app.main`
   - **Plan:** Free or Starter ($7/mo) — free tier sleeps after inactivity, which kills the bot. Use Starter for 24/7.
4. Environment variables: add every variable from `.env.example` (the real values, not the placeholders).
5. Health check path: `/healthz`
6. Deploy. Render gives you a public URL; set `BASE_URL` to it.

Railway is nearly identical: New Project → Deploy from GitHub repo → add Variables → it auto-detects Python.

## Option 2 — VPS (cheapest 24/7, ~$5/mo)

Works on DigitalOcean, Hetzner, Contabo, or any Ubuntu box.

### 1. SSH in and install Python

```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git
```

### 2. Clone and set up

```bash
git clone https://github.com/SoYama350/listing-saas.git
cd listing-saas
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env   # fill in your real values
```

### 3. Quick smoke test

```bash
python -m app.main
# Ctrl-C once you see it running
```

### 4. Run forever with systemd

Create `/etc/systemd/system/listing-saas.service` (replace `YOUR_USERNAME`):

```ini
[Unit]
Description=Listing SaaS
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/listing-saas
EnvironmentFile=/home/YOUR_USERNAME/listing-saas/.env
ExecStart=/home/YOUR_USERNAME/listing-saas/.venv/bin/python -m app.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable listing-saas
sudo systemctl start listing-saas
sudo systemctl status listing-saas   # check it's active
journalctl -u listing-saas -f        # tail logs
```

### 5. (Optional) Put it behind HTTPS with nginx + Let's Encrypt

The web dashboard works on plain HTTP for local use, but for public access you'll want HTTPS.

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

Create `/etc/nginx/sites-available/listing-saas`:

```nginx
server {
    server_name your-domain.com;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/listing-saas /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d your-domain.com
```

Then set `BASE_URL=https://your-domain.com` in `.env` and restart the service.

## Option 3 — Laptop (for testing only)

```bash
git clone https://github.com/SoYama350/listing-saas.git
cd listing-saas
pip install -r requirements.txt
cp .env.example .env   # fill it in
python -m app.main
```

The bot only works while your laptop is on and the terminal is running. Fine for trying it out, not for production.

## Updating

```bash
cd listing-saas
git pull
pip install -r requirements.txt   # if deps changed
sudo systemctl restart listing-saas   # on VPS
```

## Backups

The only stateful data is the SQLite DB (`listingsaas.db`), which holds encrypted store tokens. Back it up regularly:

```bash
cp listingsaas.db listingsaas.db.$(date +%F).bak
```

Keep `CREDENTIAL_ENCRYPTION_KEY` safe — without it, the backed-up tokens can't be decrypted.
