# File cấu hình chung cho ứng dụng

import os
import json
from dotenv import load_dotenv

# Load các biến môi trường từ file .env
load_dotenv()


class Settings:
    # SETTING
    DIR_ROOT = os.path.dirname(os.path.abspath(".env"))
    
    # API KEY
    API_KEY = os.environ["API_KEY"]
    SECRET_KEY = os.environ["SECRET_KEY"]
    
    # SECURITY - Parse JSON string to list
    ALLOW_ORIGINS = json.loads(os.environ.get("ALLOW_ORIGINS", '["http://localhost:5173"]'))
    
    # Tự động thêm frontend Vercel nếu đang trên Render
    if os.environ.get("RENDER"):
        if "https://comic-ai-teal.vercel.app" not in ALLOW_ORIGINS:
            ALLOW_ORIGINS.append("https://comic-ai-teal.vercel.app")

    # TITLE
    TITLE_APP = os.environ["TITLE_APP"]
    VERSION_APP = os.environ["VERSION_APP"]
    

    # DB
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if DATABASE_URL and DATABASE_URL.startswith("mysql"):
        from urllib.parse import urlparse
        parsed = urlparse(DATABASE_URL)
        HOST = parsed.hostname
        DB_PORT = parsed.port or 3306
        USER = parsed.username
        PASSWORD = parsed.password
        DATABASE = parsed.path.lstrip('/')
    else:
        HOST = os.environ.get("DB_HOST", os.environ.get("HOST", "127.0.0.1"))
        DB_PORT = int(os.environ.get("DB_PORT", os.environ.get("PORT_DB", "3306")))
        USER = os.environ.get("DB_USER", os.environ.get("USER", "root"))
        PASSWORD = os.environ.get("DB_PASSWORD", os.environ.get("PASSWORD", ""))
        DATABASE = os.environ.get("DB_NAME", os.environ.get("DATABASE", "testdb"))
    
    DB_SSL_MODE = os.environ.get("DB_SSL_MODE", "REQUIRED")
    DB_SSL_CA = os.environ.get("DB_SSL_CA", "")


settings = Settings()
