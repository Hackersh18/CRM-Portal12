# Linux — local setup (development / lab server)

Run the CRM Portal on a Linux machine for **development**, **testing**, or a **small LAN server** using Django’s built-in HTTP server. For Gunicorn + Nginx + TLS, use **[LINUX_SERVER_SETUP.md](./LINUX_SERVER_SETUP.md)** instead.

**Prerequisites:** Python **3.11+** (3.10 often works), `git`, and build tools for some wheels.

---

## 1. System packages (Debian / Ubuntu)

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip build-essential libpq-dev
```

Install PostgreSQL **only** if you are not using SQLite:

```bash
sudo apt install -y postgresql postgresql-contrib
```

---

## 2. Get the code and virtualenv

```bash
cd ~
git clone <your-repository-url> CRM-Portal-main
cd CRM-Portal-main

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Environment file

```bash
cp .env.example .env
```

Edit **`.env`**. Replace every placeholder and **remove** any example cloud credentials from the template.

**Always set:**

- `SECRET_KEY` or `DJANGO_SECRET_KEY` — long random string (e.g. `python -c "import secrets; print(secrets.token_urlsafe(50))"`)
- `DJANGO_DEBUG=True` for local work
- `DJANGO_ALLOWED_HOSTS` or `ALLOWED_HOSTS` — comma-separated hostnames only, e.g. `127.0.0.1,localhost,192.168.1.50` (add your machine’s LAN IP if phones or other PCs will connect)

**Firebase variables** in `.env.example` are required for **firebase-messaging** features; use real values from the Firebase console or leave placeholders if you are not using push notifications yet.

---

## 4. Database options

### Option A — SQLite (simplest)

In `.env`:

```env
DJANGO_DEBUG=True
USE_SQLITE_LOCAL=true
```

When `USE_SQLITE_LOCAL` is true and `DEBUG` is on, the app uses **`db.sqlite3`** in the project root regardless of a leftover `DATABASE_URL`.

### Option B — PostgreSQL on the same machine

Create a database user and database:

```bash
sudo -u postgres psql
```

In `psql`:

```sql
CREATE USER crm_local WITH PASSWORD 'choose-a-strong-password';
CREATE DATABASE crm_local OWNER crm_local;
GRANT ALL PRIVILEGES ON DATABASE crm_local TO crm_local;
\q
```

For **local Postgres without SSL**, append **`sslmode=disable`** to the URL (the app defaults `sslmode=require` for Postgres unless the URL already sets it):

```env
DJANGO_DEBUG=True
USE_SQLITE_LOCAL=false
DATABASE_URL=postgresql://crm_local:choose-a-strong-password@127.0.0.1:5432/crm_local?sslmode=disable
```

If your server uses SSL for local connections, use `sslmode=require` (or `prefer`) instead.

---

## 5. Migrate and optional seed

```bash
source .venv/bin/activate
cd ~/CRM-Portal-main

python manage.py migrate
```

Optional:

```bash
python manage.py seed_crm_reference
```

---

## 6. Create an admin user

```bash
python manage.py createsuperuser
```

Use an email and password you will use to log in. The project uses **`main_app.CustomUser`**; you may still need an **`Admin`** or **`Counsellor`** profile in the app depending on your workflow — see **DOCUMENTATION.md** and **USER_MANUAL.md**.

---

## 7. Run the development server

**Localhost only:**

```bash
python manage.py runserver
```

**Listen on all interfaces** (other devices on the LAN can connect):

```bash
python manage.py runserver 0.0.0.0:8000
```

Open `http://127.0.0.1:8000/` or `http://YOUR_LAN_IP:8000/`.

**Firewall:** allow TCP `8000` if you use a firewall (`ufw allow 8000/tcp`).

---

## 8. Static files in local DEBUG mode

With **`DJANGO_DEBUG=True`**, Django serves static files from app directories; you do **not** need `collectstatic` for normal local development.

If you want to test **WhiteNoise** behaviour locally, set `DJANGO_DEBUG=False` briefly, run `collectstatic`, and use a proper WSGI server — see **LINUX_SERVER_SETUP.md**.

---

## 9. Email (password reset, notifications)

SMTP is configured from **`EMAIL_ADDRESS`** and **`EMAIL_PASSWORD`** in `.env` (Gmail-style app passwords work). Without valid SMTP, some flows may fail silently or error; that is expected until email is configured.

---

## 10. Common problems

| Symptom | What to check |
|--------|----------------|
| `DisallowedHost` | Add the hostname or IP to `DJANGO_ALLOWED_HOSTS` / `ALLOWED_HOSTS` |
| Postgres connection / SSL errors | Use `?sslmode=disable` for local non-TLS Postgres, or enable SSL on the server |
| `ImproperlyConfigured` for `SECRET_KEY` | Set `SECRET_KEY` or `DJANGO_SECRET_KEY` in `.env` |
| CSRF errors on HTTPS | You need `CSRF_TRUSTED_ORIGINS` — mainly for production behind HTTPS; see LINUX_SERVER_SETUP |

---

## Next steps

- **Production-style Linux server:** [LINUX_SERVER_SETUP.md](./LINUX_SERVER_SETUP.md)
- **Full technical reference:** [DOCUMENTATION.md](./DOCUMENTATION.md)
