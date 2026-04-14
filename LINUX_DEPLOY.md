# Linux deployment — overview

This document is the **entry point** for running the CRM Portal on Linux. It explains which guide to follow and how the pieces fit together.

| Guide | Use when |
|--------|-----------|
| **[LINUX_LOCAL_SETUP.md](./LINUX_LOCAL_SETUP.md)** | You want the app running quickly on one machine: venv, `.env`, SQLite or local Postgres, `runserver` (LAN or localhost). |
| **[LINUX_SERVER_SETUP.md](./LINUX_SERVER_SETUP.md)** | You want a **production-style** stack: PostgreSQL, Gunicorn, Nginx, systemd, TLS, firewall. |
| **[HOSTINGER_DEPLOYMENT.md](./HOSTINGER_DEPLOYMENT.md)** | Step-by-step for a **Hostinger VPS** (similar to LINUX_SERVER_SETUP; adjust paths and domain). |
| **[DOCUMENTATION.md](./DOCUMENTATION.md)** | Architecture, env vars, security, RLS, cloud platforms (Render, Vercel, Supabase), troubleshooting. |

---

## What you are deploying

- **Django 4.2** application package: `college_management_system`
- **Main app**: `main_app`
- **WSGI entry** (Gunicorn): `college_management_system.wsgi:application`
- **Database**: PostgreSQL in production; SQLite optional for local dev (`USE_SQLITE_LOCAL=true` when `DEBUG` is on)
- **Static files**: `collectstatic` → `staticfiles/`; **WhiteNoise** when `DJANGO_DEBUG=False`
- **Configuration**: almost everything is **environment variables** (see `.env.example` and `college_management_system/settings.py`) — do **not** hard-code secrets or hosts in `settings.py`

---

## Choose a path

### A. Local / lab / demo (single machine)

1. Follow **[LINUX_LOCAL_SETUP.md](./LINUX_LOCAL_SETUP.md)**.
2. Prefer **SQLite** for the fastest start; use **PostgreSQL** if you need production parity.

### B. Office server or VPS (always-on, HTTPS, multiple users)

1. Follow **[LINUX_SERVER_SETUP.md](./LINUX_SERVER_SETUP.md)**.
2. Use **PostgreSQL** on the same host or a managed DB; set `DATABASE_URL` accordingly.
3. Set `DJANGO_DEBUG=False`, strong `SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, and `CSRF_TRUSTED_ORIGINS` for your HTTPS URL.

### C. Managed cloud (no full Linux admin)

- **App**: Render, Railway, Vercel, etc. (see **DOCUMENTATION.md** § deployment).
- **Database**: Supabase, Render Postgres, Neon, RDS — any PostgreSQL with a `DATABASE_URL`.

The app reads `RENDER_EXTERNAL_URL`, `RAILWAY_PUBLIC_DOMAIN`, `VERCEL_URL` when present to extend hosts and CSRF origins.

---

## Minimum production checklist

- [ ] `SECRET_KEY` (or `DJANGO_SECRET_KEY`) is long and random; not committed to git
- [ ] `DJANGO_DEBUG=False`
- [ ] `DJANGO_ALLOWED_HOSTS` lists every hostname users use (no `https://`, no paths)
- [ ] `CSRF_TRUSTED_ORIGINS` lists full origins, e.g. `https://crm.example.com`
- [ ] `DATABASE_URL` points at PostgreSQL (with correct `sslmode` for your host — see LINUX_SERVER_SETUP)
- [ ] `python manage.py migrate` has been run at least once on that database
- [ ] `python manage.py collectstatic --noinput` after code or static changes
- [ ] HTTPS terminated at Nginx (or load balancer) with `X-Forwarded-Proto` so Django security headers behave correctly

---

## PostgreSQL and Row Level Security

Migration **`0027_enable_postgres_row_level_security`** enables **RLS** on Django-managed tables when using PostgreSQL. Django normally connects as a role that can still use the app; if you use a **custom restricted** database user, read **DOCUMENTATION.md** § database / RLS.

---

## After deployment

- Create an app admin: `python manage.py createsuperuser` (and ensure `CustomUser` / `Admin` profile match your onboarding — see **DOCUMENTATION.md**).
- Optional reference data: `python manage.py seed_crm_reference` (if the command exists in your tree).
- **USER_MANUAL.md** — for end users (admins and counsellors).

---

## Updating the app (typical VPS)

```bash
cd /path/to/CRM-Portal-main
git pull
source .venv/bin/activate   # or your venv path
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart crm-portal   # or your unit name
```

Always test in staging or maintenance window for major upgrades.
