from django.apps import AppConfig
from django.conf import settings
from django.db.backends.signals import connection_created


def optimize_sqlite(sender, connection, **kwargs):
    """Optimize SQLite database connection for better performance"""
    if connection.vendor == 'sqlite':
        with connection.cursor() as cursor:
            # Enable WAL mode for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL;")
            # Reduce disk I/O
            cursor.execute("PRAGMA synchronous=NORMAL;")
            # Increase cache size (default is 2000 pages, ~2MB)
            cursor.execute("PRAGMA cache_size=-64000;")  # 64MB cache
            # Store temporary tables in memory
            cursor.execute("PRAGMA temp_store=MEMORY;")
            # Optimize for read-heavy workloads
            cursor.execute("PRAGMA mmap_size=268435456;")  # 256MB memory-mapped I/O


class MainAppConfig(AppConfig):
    name = 'main_app'
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        # Only optimize SQLite in development
        if settings.DEBUG:
            connection_created.connect(optimize_sqlite)
        from . import dashboard_cache_signals  # noqa: F401 — register signal receivers