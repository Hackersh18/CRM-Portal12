# Hostinger Deployment Guide for CRM Portal

**Configuration:** This project uses **environment variables** for `DEBUG`, `ALLOWED_HOSTS`, `SECRET_KEY`, and the database URL (see `.env.example` and `college_management_system/settings.py`). Prefer **`.env`** or **systemd `EnvironmentFile`** instead of editing `settings.py`. For a generic Ubuntu layout (paths, Unix socket, `/etc/crm/crm.env`), see **[LINUX_SERVER_SETUP.md](./LINUX_SERVER_SETUP.md)**.

## 📋 Table of Contents
1. [System Requirements](#system-requirements)
2. [Cost Breakdown](#cost-breakdown)
3. [Pre-Deployment Checklist](#pre-deployment-checklist)
4. [Step-by-Step Deployment](#step-by-step-deployment)
5. [Configuration Files](#configuration-files)
6. [Database Setup](#database-setup)
7. [Static Files Configuration](#static-files-configuration)
8. [Domain & SSL Setup](#domain--ssl-setup)
9. [Post-Deployment](#post-deployment)
10. [Troubleshooting](#troubleshooting)

---

## 🖥️ System Requirements

### Minimum Requirements (Cost-Effective Option)
- **Hosting Type**: VPS (Virtual Private Server)
- **CPU**: 2 vCPU cores
- **RAM**: 2 GB
- **Storage**: 40 GB SSD
- **Bandwidth**: 1 TB/month
- **OS**: Ubuntu 22.04 LTS (recommended)
- **Python**: 3.11 or higher
- **Database**: PostgreSQL 14+ (recommended) or MySQL 8.0+
- **Web Server**: Nginx
- **Application Server**: Gunicorn

### Recommended Requirements (Better Performance)
- **CPU**: 4 vCPU cores
- **RAM**: 4 GB
- **Storage**: 80 GB SSD
- **Bandwidth**: 2 TB/month

---

## 💰 Cost Breakdown

### Hostinger VPS Pricing (Cost-Effective)

#### Option 1: VPS 1 (Budget-Friendly) - **$3.99/month**
- 1 vCPU Core
- 1 GB RAM
- 20 GB SSD
- 1 TB Bandwidth
- ⚠️ **Note**: May need upgrade for production

#### Option 2: VPS 2 (Recommended) - **$4.99/month**
- 2 vCPU Cores
- 2 GB RAM
- 40 GB SSD
- 2 TB Bandwidth
- ✅ **Best for small to medium CRM**

#### Option 3: VPS 3 (High Performance) - **$7.99/month**
- 4 vCPU Cores
- 4 GB RAM
- 80 GB SSD
- 4 TB Bandwidth
- ✅ **Best for larger teams**

### Additional Costs (Optional)
- **Domain Name**: $0.99 - $15/year (free with some Hostinger plans)
- **SSL Certificate**: **FREE** (Let's Encrypt via Hostinger)
- **Email Hosting**: Included in most plans
- **Backup Service**: Included (daily backups)

### Total Monthly Cost Estimate
- **Minimum**: $4.99/month (VPS 2)
- **Recommended**: $7.99/month (VPS 3)
- **Domain**: $0.99 - $15/year (one-time or annual)

---

## ✅ Pre-Deployment Checklist

### 1. Prepare Your Code
- [ ] All code is committed to Git
- [ ] `.env` file is prepared (without sensitive data in repo)
- [ ] Database migrations are ready
- [ ] Static files are collected locally (test)
- [ ] All dependencies are in `requirements.txt`

### 2. Environment Variables Needed
Create a `.env` file with:
```env
SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:password@localhost:5432/crm_db
TIME_ZONE=Asia/Kolkata
USE_TZ=True

# Firebase (if using)
FIREBASE_API_KEY=your-api-key
FIREBASE_AUTH_DOMAIN=your-auth-domain
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-storage-bucket
FIREBASE_MESSAGING_SENDER_ID=your-sender-id
FIREBASE_APP_ID=your-app-id
FIREBASE_MEASUREMENT_ID=your-measurement-id

# Email Configuration (optional)
EMAIL_HOST=smtp.hostinger.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@yourdomain.com
EMAIL_HOST_PASSWORD=your-email-password
```

---

## 🚀 Step-by-Step Deployment

### Step 1: Purchase Hostinger VPS

1. Go to [Hostinger.com](https://www.hostinger.com)
2. Select **VPS Hosting**
3. Choose **VPS 2** (recommended) or **VPS 3**
4. Complete purchase
5. Wait for VPS setup email (usually 5-15 minutes)

### Step 2: Access Your VPS

1. **Via SSH** (Recommended):
   ```bash
   ssh root@your-vps-ip
   ```
   Password will be provided in email

2. **Via Hostinger Control Panel**:
   - Log in to hPanel
   - Go to VPS section
   - Use Web Terminal

### Step 3: Initial Server Setup

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y python3 python3-pip python3-venv nginx postgresql postgresql-contrib git curl

# Install Node.js (if needed for any build tools)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Create a non-root user for security
sudo adduser crmuser
sudo usermod -aG sudo crmuser
su - crmuser
```

### Step 4: Setup PostgreSQL Database

```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL prompt:
CREATE DATABASE crm_db;
CREATE USER crm_user WITH PASSWORD 'your_secure_password_here';
ALTER ROLE crm_user SET client_encoding TO 'utf8';
ALTER ROLE crm_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE crm_user SET timezone TO 'Asia/Kolkata';
GRANT ALL PRIVILEGES ON DATABASE crm_db TO crm_user;
\q
```

### Step 5: Clone Your Repository

```bash
# Navigate to home directory
cd ~

# Clone your repository (replace with your repo URL)
git clone https://github.com/yourusername/CRM-Portal-main.git
cd CRM-Portal-main

# Or upload files via SFTP/FTP
```

### Step 6: Setup Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### Step 7: Configure Environment Variables

```bash
# Create .env file
nano .env

# Add all environment variables (see Pre-Deployment Checklist)
# Save and exit: Ctrl+X, then Y, then Enter
```

### Step 8: Production flags (environment only)

Do **not** change `settings.py` for hosts or `DEBUG`. In your **`.env`** (or systemd environment file), set at minimum:

```env
DJANGO_DEBUG=False
SECRET_KEY=your-long-random-secret
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,YOUR_VPS_IP
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
DATABASE_URL=postgresql://crm_user:your_password@localhost:5432/crm_db
```

`STATIC_ROOT`, `MEDIA_ROOT`, and WhiteNoise are already defined in `settings.py` for production.

### Step 9: Run Migrations

```bash
# Activate virtual environment
source venv/bin/activate

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

### Step 10: Configure Gunicorn

Create `gunicorn_config.py`:

```python
# gunicorn_config.py
bind = "127.0.0.1:8000"
workers = 3
worker_class = "sync"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
```

### Step 11: Create Systemd Service

Create `/etc/systemd/system/crm-portal.service`:

```bash
sudo nano /etc/systemd/system/crm-portal.service
```

Add this content:

```ini
[Unit]
Description=CRM Portal Gunicorn daemon
After=network.target

[Service]
User=crmuser
Group=www-data
WorkingDirectory=/home/crmuser/CRM-Portal-main
Environment="PATH=/home/crmuser/CRM-Portal-main/venv/bin"
ExecStart=/home/crmuser/CRM-Portal-main/venv/bin/gunicorn \
    --config /home/crmuser/CRM-Portal-main/gunicorn_config.py \
    college_management_system.wsgi:application

Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable crm-portal
sudo systemctl start crm-portal
sudo systemctl status crm-portal
```

### Step 12: Configure Nginx

Create `/etc/nginx/sites-available/crm-portal`:

```bash
sudo nano /etc/nginx/sites-available/crm-portal
```

Add this configuration:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect HTTP to HTTPS (after SSL setup)
    # return 301 https://$server_name$request_uri;

    # For initial setup, use HTTP (remove redirect above)
    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    location /static/ {
        alias /home/crmuser/CRM-Portal-main/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /home/crmuser/CRM-Portal-main/media/;
        expires 30d;
        add_header Cache-Control "public";
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/crm-portal /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 13: Setup SSL Certificate (Free)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Certbot will automatically configure Nginx for HTTPS
# Certificates auto-renew every 90 days
```

After SSL setup, update Nginx config to redirect HTTP to HTTPS (uncomment the redirect line).

---

## 📁 Configuration Files

### Create `.htaccess` for Hostinger (if using shared hosting)

If using Hostinger shared hosting instead of VPS, create `.htaccess`:

```apache
RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.*)$ /index.php/$1 [L]
```

### Create `passenger_wsgi.py` (for shared hosting with Passenger)

```python
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'college_management_system.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

---

## 🗄️ Database Setup

### Option 1: PostgreSQL (Recommended)

Already configured in Step 4. Update `.env`:

```env
DATABASE_URL=postgresql://crm_user:your_password@localhost:5432/crm_db
```

### Option 2: MySQL (Alternative)

```bash
# Install MySQL
sudo apt install -y mysql-server

# Secure MySQL
sudo mysql_secure_installation

# Create database
sudo mysql -u root -p
```

```sql
CREATE DATABASE crm_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'crm_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON crm_db.* TO 'crm_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

Update `.env`:
```env
DATABASE_URL=mysql://crm_user:your_password@localhost:3306/crm_db
```

Install MySQL client:
```bash
pip install mysqlclient
```

---

## 📦 Static Files Configuration

Static files are already configured with WhiteNoise. Ensure:

1. **Collect static files**:
   ```bash
   python manage.py collectstatic --noinput
   ```

2. **Verify static files**:
   ```bash
   ls -la staticfiles/
   ```

3. **Nginx serves static files** (already configured in Step 12)

---

## 🌐 Domain & SSL Setup

### 1. Point Domain to Hostinger

1. Log in to your domain registrar
2. Update DNS records:
   - **A Record**: `@` → Your VPS IP
   - **A Record**: `www` → Your VPS IP
3. Wait for DNS propagation (up to 48 hours, usually 1-2 hours)

### 2. SSL Certificate (Free with Let's Encrypt)

Already configured in Step 13. Certbot handles:
- Automatic certificate generation
- Nginx configuration
- Auto-renewal (every 90 days)

---

## 🔧 Post-Deployment

### 1. Verify Application

```bash
# Check Gunicorn status
sudo systemctl status crm-portal

# Check Nginx status
sudo systemctl status nginx

# Check application logs
sudo journalctl -u crm-portal -f
```

### 2. Setup Automatic Backups

Create backup script `/home/crmuser/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/home/crmuser/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup database
pg_dump -U crm_user crm_db > $BACKUP_DIR/db_backup_$DATE.sql

# Backup media files
tar -czf $BACKUP_DIR/media_backup_$DATE.tar.gz /home/crmuser/CRM-Portal-main/media/

# Keep only last 7 days of backups
find $BACKUP_DIR -type f -mtime +7 -delete
```

Make it executable:
```bash
chmod +x /home/crmuser/backup.sh
```

Add to crontab (daily at 2 AM):
```bash
crontab -e
# Add this line:
0 2 * * * /home/crmuser/backup.sh
```

### 3. Setup Log Rotation

Create `/etc/logrotate.d/crm-portal`:

```
/home/crmuser/CRM-Portal-main/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 crmuser www-data
    sharedscripts
}
```

### 4. Monitor Application

```bash
# View real-time logs
sudo journalctl -u crm-portal -f

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Check application access logs
sudo tail -f /var/log/nginx/access.log
```

---

## 🔍 Troubleshooting

### Issue: 502 Bad Gateway

**Solution**:
```bash
# Check if Gunicorn is running
sudo systemctl status crm-portal

# Restart Gunicorn
sudo systemctl restart crm-portal

# Check Gunicorn logs
sudo journalctl -u crm-portal -n 50
```

### Issue: Static files not loading

**Solution**:
```bash
# Recollect static files
python manage.py collectstatic --noinput

# Check Nginx configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### Issue: Database connection error

**Solution**:
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test database connection
psql -U crm_user -d crm_db -h localhost

# Check .env file has correct DATABASE_URL
cat .env | grep DATABASE_URL
```

### Issue: Permission errors

**Solution**:
```bash
# Fix ownership
sudo chown -R crmuser:www-data /home/crmuser/CRM-Portal-main
sudo chmod -R 755 /home/crmuser/CRM-Portal-main

# Fix static files permissions
sudo chown -R crmuser:www-data /home/crmuser/CRM-Portal-main/staticfiles
sudo chmod -R 755 /home/crmuser/CRM-Portal-main/staticfiles
```

### Issue: Port 8000 already in use

**Solution**:
```bash
# Find process using port 8000
sudo lsof -i :8000

# Kill the process or change port in gunicorn_config.py
```

---

## 📊 Performance Optimization

### 1. Enable Gzip Compression in Nginx

Add to Nginx config:

```nginx
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/json;
```

### 2. Database Optimization

```python
# In settings.py, add connection pooling
DATABASES['default']['CONN_MAX_AGE'] = 600
```

### 3. Caching (Optional)

Install Redis for caching:
```bash
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

---

## 🔐 Security Checklist

- [ ] `DEBUG = False` in production
- [ ] Strong `SECRET_KEY` in `.env`
- [ ] `ALLOWED_HOSTS` configured correctly
- [ ] SSL certificate installed
- [ ] Firewall configured (UFW)
- [ ] Database user has limited privileges
- [ ] Regular backups configured
- [ ] Strong passwords for all accounts
- [ ] SSH key authentication (disable password auth)

### Setup Firewall

```bash
# Install UFW
sudo apt install -y ufw

# Allow SSH, HTTP, HTTPS
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
sudo ufw status
```

---

## 📞 Support & Resources

- **Hostinger Support**: [support.hostinger.com](https://support.hostinger.com)
- **Django Deployment**: [docs.djangoproject.com/en/stable/howto/deployment/](https://docs.djangoproject.com/en/stable/howto/deployment/)
- **Nginx Documentation**: [nginx.org/en/docs/](https://nginx.org/en/docs/)
- **Gunicorn Documentation**: [docs.gunicorn.org](https://docs.gunicorn.org)

---

## 💡 Quick Reference Commands

```bash
# Restart application
sudo systemctl restart crm-portal

# Restart Nginx
sudo systemctl restart nginx

# View application logs
sudo journalctl -u crm-portal -f

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Create superuser
python manage.py createsuperuser

# Check service status
sudo systemctl status crm-portal
sudo systemctl status nginx
sudo systemctl status postgresql
```

---

## ✅ Deployment Checklist

- [ ] VPS purchased and accessible
- [ ] Server updated and packages installed
- [ ] Database created and configured
- [ ] Code cloned/uploaded
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] Environment variables configured
- [ ] Migrations run
- [ ] Superuser created
- [ ] Static files collected
- [ ] Gunicorn service configured and running
- [ ] Nginx configured and running
- [ ] SSL certificate installed
- [ ] Domain pointed to server
- [ ] Firewall configured
- [ ] Backups configured
- [ ] Application tested and working

---

**Total Estimated Setup Time**: 2-3 hours  
**Monthly Cost**: $4.99 - $7.99 (VPS) + Domain ($0.99-$15/year)

Good luck with your deployment! 🚀
