import os
import mysql.connector
from app.config import settings


def _build_ssl_kwargs() -> dict:
    ssl_mode = settings.DB_SSL_MODE.upper()
    ssl_ca = settings.DB_SSL_CA

    if ssl_mode in ("DISABLED", "OFF", "NONE"):
        return {"ssl_disabled": True}

    ssl_kwargs = {
        "ssl_disabled": False,
    }
    
    # Một số version mysql-connector yêu cầu ssl_mode trực tiếp
    if ssl_mode == "REQUIRED":
        ssl_kwargs["ssl_mode"] = "REQUIRED"
    elif ssl_mode == "VERIFY_CA":
        ssl_kwargs["ssl_mode"] = "VERIFY_CA"
    elif ssl_mode == "VERIFY_IDENTITY":
        ssl_kwargs["ssl_mode"] = "VERIFY_IDENTITY"

    if ssl_ca and os.path.exists(ssl_ca):
        ssl_kwargs["ssl_ca"] = ssl_ca
    
    return ssl_kwargs


def get_mysql_connection(**extra_kwargs):
    """Create MySQL connection with optional cloud SSL + custom port support."""
    config = {
        "host": settings.HOST,
        "port": settings.DB_PORT,
        "user": settings.USER,
        "password": settings.PASSWORD,
        "database": settings.DATABASE,
    }
    config.update(_build_ssl_kwargs())
    config.update(extra_kwargs)
    return mysql.connector.connect(**config)
