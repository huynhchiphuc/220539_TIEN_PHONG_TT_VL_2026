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

    # TITLE
    TITLE_APP = os.environ["TITLE_APP"]
    VERSION_APP = os.environ["VERSION_APP"]
    

    # DB
    DATABASE_URL = os.environ.get("DATABASE_URL")
    HOST = os.environ["HOST"]
    DB_PORT = int(os.environ.get("DB_PORT", os.environ.get("PORT_DB", "3306")))
    USER = os.environ["USER"]
    PASSWORD = os.environ["PASSWORD"]
    DATABASE = os.environ["DATABASE"]
    DB_SSL_MODE = os.environ.get("DB_SSL_MODE", "DISABLED")
    DB_SSL_CA = os.environ.get("DB_SSL_CA", "")


settings = Settings()
