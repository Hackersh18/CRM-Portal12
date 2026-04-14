# Linux production server (PostgreSQL, Gunicorn, Nginx, TLS)

Deploy the CRM Portal on **Ubuntu 22.04 LTS** (or similar) as an always-on service: **PostgreSQL**, **Gunicorn** behind **Nginx**, **systemd** for process management, and **Let’s Encrypt** for HTTPS.

This guide uses **environment variables** only (via `.env` or systemd `EnvironmentFile`). Do **not** edit `college_management_system/settings.py` for hosts or secrets.

**Paths and user used in this guide**

| Symbol | Value |
|--------|--------|
| **Deploy user** | `avviare` (normal login user that owns the code and venv) |
| **Project root** | `/home/avviare/CRM Portal/CRM-Portal-main` |
| **Postgres role** | `avviare` (same name as deploy user; you may use a different DB user if you prefer — set `DATABASE_URL` to match) |

The parent folder **`CRM Portal`** contains a **space**. Quote paths in the **shell** and in **Nginx `alias`**. For **systemd**, many versions reject **quoted** `WorkingDirectory` with spaces **and** require an **absolute** `ExecStart` path — so this guide uses a **symlink without spaces** (`/home/avviare/crm-app`) for the unit file (see **§7**).

To use another user or path (e.g. `/srv/crm/CRM-Portal-main` and user `crmapp`), replace **`avviare`**, **`/home/avviare/CRM Portal/CRM-Portal-main`**, and Postgres **`CREATE USER`** / **`DATABASE_URL`** consistently.

**Assumptions:**

- Domain `crm.example.com` points to this server’s public IP (replace with yours).

### Easiest path (use this first)

Sections **1–5** stay the same. For **6–8**, use **Option A** below:

- Gunicorn listens on **`127.0.0.1:8000`** only (not reachable from the internet).
- **No** `gunicorn.conf.py`, **no** `/run/crm` folder, **no** `tmpfiles.d` — fewer steps and fewer things to break after reboot.
- Nginx proxies to that port.

**Option B** (Unix socket) is optional if you prefer it later.

---

## 1. Packages

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-dev build-essential libpq-dev \
  nginx postgresql postgresql-contrib git ufw certbot python3-certbot-nginx
```

---

## 2. PostgreSQL

```bash
sudo -u postgres psql
```

```sql
CREATE USER avviare WITH PASSWORD 'REPLACE_WITH_STRONG_PASSWORD';
CREATE DATABASE crm OWNER avviare;
ALTER ROLE avviare SET client_encoding TO 'utf8';
ALTER ROLE avviare SET default_transaction_isolation TO 'read committed';
GRANT ALL PRIVILEGES ON DATABASE crm TO avviare;
\c crm
GRANT ALL ON SCHEMA public TO avviare;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO avviare;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO avviare;
\q
```

**Local socket / same host:** use host `127.0.0.1` in `DATABASE_URL`. For a default Ubuntu Postgres install without SSL on localhost, use **`sslmode=disable`** in the URL so it does not conflict with the project’s Postgres defaults (see note in [LINUX_LOCAL_SETUP.md](./LINUX_LOCAL_SETUP.md)).

Example:

```text
postgresql://avviare:REPLACE_WITH_STRONG_PASSWORD@127.0.0.1:5432/crm?sslmode=disable
```

---

## 3. Application user and code

Use the **`avviare`** account (create it if this is a fresh server):

```bash
sudo adduser avviare
```

As **`avviare`**, create the parent folder (if needed), clone, and install dependencies:

```bash
sudo -u avviare -i
mkdir -p "/home/avviare/CRM Portal"
cd "/home/avviare/CRM Portal"
git clone <your-repository-url> CRM-Portal-main
cd CRM-Portal-main

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

If the project is **already** at `/home/avviare/CRM Portal/CRM-Portal-main`, skip `git clone` and only run the `venv` / `pip` steps inside that directory.

**Symlink for systemd (before §7):** avoids spaces and satisfies `ExecStart` absolute-path rules:

```bash
sudo ln -sf "/home/avviare/CRM Portal/CRM-Portal-main" /home/avviare/crm-app
```

Nginx may still use the real path with quoted `alias`, or you can use `/home/avviare/crm-app/staticfiles/` etc.

---

## 4. Environment variables

Store secrets outside the repo if you prefer; this example uses a file readable by root and the deploy user.

```bash
sudo mkdir -p /etc/crm
sudo nano /etc/crm/crm.env
```

Example contents (adjust every value):

```env
DJANGO_DEBUG=False
SECRET_KEY=generate-a-long-random-string
DJANGO_ALLOWED_HOSTS=crm.example.com,www.crm.example.com,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://crm.example.com,https://www.crm.example.com
DATABASE_URL=postgresql://avviare:REPLACE_WITH_STRONG_PASSWORD@127.0.0.1:5432/crm?sslmode=disable
DATABASE_CONN_MAX_AGE=600
EMAIL_ADDRESS=your-smtp-user@gmail.com
EMAIL_PASSWORD=your-app-password
```

```bash
sudo chown root:avviare /etc/crm/crm.env
sudo chmod 640 /etc/crm/crm.env
```

**Notes:**

- With **`DJANGO_DEBUG=False`**, Django enables **HTTPS redirects** and secure cookies when configured in `settings.py`; you **must** set **`CSRF_TRUSTED_ORIGINS`** to your real `https://` origins or forms will fail with CSRF errors.
- **`DJANGO_ALLOWED_HOSTS`**: hostnames only, comma-separated, no scheme or path.
- For managed PostgreSQL (Supabase, Neon, etc.), use the provider’s URI and keep **`sslmode=require`** as in their dashboard; tune **`DATABASE_CONN_MAX_AGE`** per **DOCUMENTATION.md** (pooler vs direct).

Link `.env` for convenience (optional): the app loads `.env` via `python-dotenv` from the project directory. Either copy values into **`/home/avviare/CRM Portal/CRM-Portal-main/.env`** owned by `avviare`, or rely on systemd `EnvironmentFile` below and skip a project `.env`.

**`EnvironmentFile` path** can be changed (e.g. `/etc/default/crm-portal`); keep the same path in the systemd unit in §7.

---

## 5. Migrate, static files, superuser

```bash
sudo -u avviare -i
cd "/home/avviare/CRM Portal/CRM-Portal-main"
source .venv/bin/activate

set -a
source /etc/crm/crm.env
set +a

python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

`collectstatic` writes to **`staticfiles/`** under the project (`STATIC_ROOT` in `settings.py`). With `DEBUG=False`, **WhiteNoise** serves these files from the app; Nginx can also serve `/static/` directly (optional optimization below).

Create media upload directory if missing:

```bash
mkdir -p "/home/avviare/CRM Portal/CRM-Portal-main/media"
chown -R avviare:avviare "/home/avviare/CRM Portal/CRM-Portal-main/media"
```

---

## 6. Gunicorn

Workers: a common starting point is **`(2 × CPU cores) + 1`**, capped by RAM (each worker is a full Python process). For a 2 GB VPS, **3 workers** is often reasonable.

### Option A — TCP on `127.0.0.1` (easiest)

Nothing to create in this section. Gunicorn options go straight into the **systemd** unit in §7 (Option A).

### Option B — Unix socket (optional)

Create **`gunicorn.conf.py`** in the project root (e.g. **`/home/avviare/CRM Portal/CRM-Portal-main/gunicorn.conf.py`**, same as **`/home/avviare/crm-app/gunicorn.conf.py`** if the symlink exists) owned by `avviare`:

```python
bind = "unix:/run/crm/gunicorn.sock"
workers = 3
worker_class = "sync"
timeout = 120
umask = 0o007
```

Create the runtime directory for the socket:

```bash
sudo mkdir -p /run/crm
sudo chown avviare:avviare /run/crm
```

**systemd tmpfiles** (so `/run/crm` exists after reboot):

```bash
echo 'd /run/crm 0755 avviare avviare -' | sudo tee /etc/tmpfiles.d/crm.conf
sudo systemd-tmpfiles --create /etc/tmpfiles.d/crm.conf
```

---

## 7. systemd service

Create the symlink from **§3** if you have not already:

```bash
sudo ln -sf "/home/avviare/CRM Portal/CRM-Portal-main" /home/avviare/crm-app
```

Create `/etc/systemd/system/crm-portal.service` with **either** Option A or B (match your choice in §6 and §8).

Use **`/home/avviare/crm-app`** in the unit (no spaces). **`ExecStart`** must be the **full path** to `gunicorn` on your systemd (relative paths often fail with *Neither a valid executable name nor an absolute path*).

**Important:** Put **`ExecStart` on one line** (no trailing `\` line continuations). Multi-line `ExecStart` in unit files often passes a stray `\` to Gunicorn → `ModuleNotFoundError: No module named '\\'`.

### Option A — TCP on `127.0.0.1:8000` (easiest)

```ini
[Unit]
Description=CRM Portal (Gunicorn)
After=network.target postgresql.service

[Service]
User=avviare
Group=avviare
WorkingDirectory=/home/avviare/crm-app
EnvironmentFile=/etc/crm/crm.env
ExecStart=/home/avviare/crm-app/.venv/bin/gunicorn --bind 127.0.0.1:8000 --workers 3 --timeout 120 college_management_system.wsgi:application
Restart=on-failure
RestartSec=5

NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### Option B — Unix socket (uses `gunicorn.conf.py` from §6)

Create **`gunicorn.conf.py`** inside the project (it is also reachable as **`/home/avviare/crm-app/gunicorn.conf.py`** via the symlink).

```ini
[Unit]
Description=CRM Portal (Gunicorn)
After=network.target postgresql.service

[Service]
User=avviare
Group=avviare
WorkingDirectory=/home/avviare/crm-app
EnvironmentFile=/etc/crm/crm.env
ExecStart=/home/avviare/crm-app/.venv/bin/gunicorn --config /home/avviare/crm-app/gunicorn.conf.py college_management_system.wsgi:application
Restart=on-failure
RestartSec=5

NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now crm-portal
sudo systemctl status crm-portal
```

Logs:

```bash
sudo journalctl -u crm-portal -f
```

### 7.1 systemd still fails — wrapper script (no `WorkingDirectory`)

If you still see **`WorkingDirectory= path is not absolute`** or **`relative gunicorn`**, your parser may be strict. Use a small script: systemd only runs an **absolute** `ExecStart` to that script; the script **`cd`**s into the real folder (spaces OK in bash).

```bash
sudo tee /usr/local/bin/crm-portal-gunicorn.sh << 'EOF'
#!/bin/bash
set -euo pipefail
cd "/home/avviare/CRM Portal/CRM-Portal-main"
exec .venv/bin/gunicorn \
  --bind 127.0.0.1:8000 \
  --workers 3 \
  --timeout 120 \
  college_management_system.wsgi:application
EOF
sudo chmod 755 /usr/local/bin/crm-portal-gunicorn.sh
sudo chown root:root /usr/local/bin/crm-portal-gunicorn.sh
```

```bash
sudo tee /etc/systemd/system/crm-portal.service << 'EOF'
[Unit]
Description=CRM Portal (Gunicorn)
After=network.target postgresql.service

[Service]
Type=simple
User=avviare
Group=avviare
EnvironmentFile=/etc/crm/crm.env
ExecStart=/usr/local/bin/crm-portal-gunicorn.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl restart crm-portal
sudo systemctl status crm-portal
```

If the project is **not** at `/home/avviare/CRM Portal/CRM-Portal-main`, edit the `cd` line in `/usr/local/bin/crm-portal-gunicorn.sh` only.

---

## 8. Nginx

`/etc/nginx/sites-available/crm-portal` — use the block that matches **§7** (A or B). **Quote `alias` paths** because of the space in `CRM Portal`.

### Option A — proxy to `127.0.0.1:8000` (easiest)

Replace **`server_name`** with your real hostname(s), your **public IP**, or **`_`** (catch‑all). See **§8.1** for IP-only HTTP.

```nginx
server {
    listen 80;
    server_name crm.example.com www.crm.example.com;

    client_max_body_size 100M;

    location /static/ {
        alias "/home/avviare/CRM Portal/CRM-Portal-main/staticfiles/";
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias "/home/avviare/CRM Portal/CRM-Portal-main/media/";
        expires 7d;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

### Option B — Unix socket

```nginx
upstream crm_app {
    server unix:/run/crm/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name crm.example.com www.crm.example.com;

    client_max_body_size 100M;

    location /static/ {
        alias "/home/avviare/CRM Portal/CRM-Portal-main/staticfiles/";
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias "/home/avviare/CRM Portal/CRM-Portal-main/media/";
        expires 7d;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass http://crm_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

Enable and test:

```bash
sudo ln -sf /etc/nginx/sites-available/crm-portal /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**Ubuntu default site:** `sites-enabled/default` also listens on port **80**. If your CRM config uses **`server_name _;`**, Nginx may warn **conflicting server name "_"** (two defaults). Prefer **`server_name YOUR_PUBLIC_IP;`** instead of **`_`**, **or** disable the default site so only the CRM `server` block handles port 80:

```bash
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

---

## 8.1 No domain — access by **public IP** over HTTP

You do **not** need to buy a domain. Use your VPS **public IPv4** (from your provider’s panel, e.g. `203.0.113.50`).

**1. Nginx** — **prefer your real IP** (avoids clashes with Ubuntu’s `default` site):

```nginx
server_name 203.0.113.50;
```

Only use **`server_name _;`** if you have **removed** `sites-enabled/default` (or you will get **conflicting server name "_"** and Nginx may not start).

Keep **`proxy_pass http://127.0.0.1:8000;`** (Option A) and the same **`alias`** paths to your project.

**2. Firewall** — allow HTTP: `sudo ufw allow 'Nginx HTTP'` (or `80/tcp`).

**3. Django env** (`/etc/crm/crm.env`) — replace `203.0.113.50` with your real IP:

```env
DJANGO_DEBUG=False
DJANGO_USE_HTTPS=0
SECRET_KEY=your-long-random-secret
DJANGO_ALLOWED_HOSTS=203.0.113.50,127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=http://203.0.113.50
```

Use **`DJANGO_USE_HTTPS=0`** (or `false`, `no`, `off`). Without it, the project defaults to **forcing HTTPS** when `DEBUG` is off, which breaks plain **`http://IP`** until you have TLS. After changing **`settings.py`**, redeploy the app code on the server (`git pull`) and restart **`crm-portal`**.

**4. Restart Gunicorn** after editing env:

```bash
sudo systemctl restart crm-portal
```

**5. Open in a browser:** `http://203.0.113.50/`

Traffic is **not encrypted** on the internet. Add a domain and **§9 Certbot** when you can.

---

## 9. TLS (Let’s Encrypt)

```bash
sudo certbot --nginx -d crm.example.com -d www.crm.example.com
```

Certbot will adjust the server block for HTTPS. After HTTPS works, confirm **`CSRF_TRUSTED_ORIGINS`** includes the same `https://` hostnames.

---

## 10. Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

---

## 11. File permissions

```bash
sudo chown -R avviare:avviare "/home/avviare/CRM Portal/CRM-Portal-main"
# Nginx only needs read for static/media if served by Nginx:
sudo chmod -R u=rwX,g=rX,o= "/home/avviare/CRM Portal/CRM-Portal-main"
```

If you use **Option B** (Unix socket), ensure `/run/crm` exists and is writable by `avviare` (see §6).

---

## 12. Optional: Redis and Celery

If you use **`REDIS_URL`**, install Redis and point the env var at it; run a **Celery** worker and (if needed) beat scheduler as separate systemd units. See **DOCUMENTATION.md** for cache and task behaviour. The app can run without Redis using in-memory fallbacks where implemented.

---

## 13. Deploy updates

```bash
sudo -u avviare -i
cd "/home/avviare/CRM Portal/CRM-Portal-main"
source .venv/bin/activate
git pull
pip install -r requirements.txt
set -a; source /etc/crm/crm.env; set +a
python manage.py migrate
python manage.py collectstatic --noinput
exit
sudo systemctl restart crm-portal
```

---

## 14. Troubleshooting

| Issue | Checks |
|--------|--------|
| **502 Bad Gateway** | `systemctl status crm-portal`; **Option A:** is Gunicorn on `127.0.0.1:8000`? `curl -sI http://127.0.0.1:8000/` from the server. **Option B:** socket path matches Nginx; `/run/crm` ownership |
| **Address already in use** | Port `8000` taken by another app; change `--bind` port in systemd and `proxy_pass` in Nginx to match |
| **Static 404** | Run `collectstatic`; check `alias` paths (quotes, exact path); `DJANGO_DEBUG=False` uses WhiteNoise — Nginx `/static/` is optional but must match `STATIC_ROOT` |
| **CSRF / login redirect loops** | `CSRF_TRUSTED_ORIGINS`, `SECURE_PROXY_SSL_HEADER` (Nginx sets `X-Forwarded-Proto`), correct HTTPS |
| **Database errors** | `postgresql` service; `DATABASE_URL`; `sslmode` for local vs cloud |
| **Permission denied on media** | `chown avviare` on `media/` |
| **systemd fails to start** | Use symlink **`/home/avviare/crm-app`** + absolute **`ExecStart=/home/avviare/crm-app/.venv/bin/gunicorn`**; see **§7** |
| **WorkingDirectory not absolute** / **relative gunicorn** | Some systemd builds reject quoted paths with spaces and reject relative **`ExecStart`** — use **§3** symlink and **§7** unit as written |
| **`ModuleNotFoundError: No module named '\\'`** | **`ExecStart`** used line-ending `\` — systemd passes `\` as an argument; use **one line** for **`ExecStart`** (see **§7**) |
| **conflicting server name "_"** | Two `server` blocks use **`_`** on port 80 — use **`server_name YOUR_IP;`** or run **`sudo rm /etc/nginx/sites-enabled/default`** then **`sudo nginx -t`** |
| **nginx.service not active / failed to start** | **`sudo nginx -t`** (fix errors); **`sudo journalctl -u nginx -n 40 --no-pager`**; port **80** in use: **`sudo ss -tlnp \| grep :80`** |

---

## Related docs

- [LINUX_DEPLOY.md](./LINUX_DEPLOY.md) — overview and checklists  
- [LINUX_LOCAL_SETUP.md](./LINUX_LOCAL_SETUP.md) — SQLite / dev server  
- [DOCUMENTATION.md](./DOCUMENTATION.md) — env vars, RLS, platforms  
- [HOSTINGER_DEPLOYMENT.md](./HOSTINGER_DEPLOYMENT.md) — VPS walkthrough (verify env-driven settings; avoid editing `settings.py` for hosts)
