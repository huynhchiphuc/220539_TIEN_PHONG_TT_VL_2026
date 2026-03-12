from fastapi import FastAPI
from app.routers import auth
from app.routers import base
from app.routers import file_upload
from app.routers import comic
from app.routers import admin
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

# Prefix API theo version
api_prefix = f"/api/{settings.VERSION_APP}"

# Tạo instance của FastAPI
app = FastAPI(
    title=settings.TITLE_APP,
    docs_url=f"{api_prefix}/docs",
    redoc_url=f"{api_prefix}/redoc",
    openapi_url=f"{api_prefix}/openapi.json",
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_ORIGINS,
    allow_credentials=("*" not in settings.ALLOW_ORIGINS),
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)


# Include các router vào ứng dụng chính
app.include_router(auth.router, prefix=api_prefix)
app.include_router(base.router, prefix=api_prefix)
app.include_router(file_upload.router, prefix=api_prefix)
app.include_router(comic.router, prefix=api_prefix)
app.include_router(admin.router, prefix=api_prefix)


@app.get(f"{api_prefix}/")
def read_root():
    return {"message": f"Welcome to {settings.TITLE_APP}"}
