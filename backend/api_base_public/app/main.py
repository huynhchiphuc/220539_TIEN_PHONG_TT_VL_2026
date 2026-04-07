"""
Điểm khởi đầu ứng dụng FastAPI.

Khởi tạo instance FastAPI, cấu hình CORS middleware,
và đăng ký tất cả các router theo prefix API version.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.config import settings
from app.routers import auth, base, file_upload, comic, comic_media, comic_projects, admin

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
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=("*" not in settings.ALLOW_ORIGINS),
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Include các router vào ứng dụng chính
app.include_router(auth.router, prefix=api_prefix)
app.include_router(base.router, prefix=api_prefix)
app.include_router(file_upload.router, prefix=api_prefix)
app.include_router(comic.router, prefix=api_prefix)
app.include_router(comic_media.router, prefix=api_prefix)
app.include_router(comic_projects.router, prefix=api_prefix)
app.include_router(admin.router, prefix=api_prefix)


@app.get("/")
def redirect_to_docs() -> RedirectResponse:
    """Chuyển hướng root URL đến trang tài liệu API Swagger."""
    return RedirectResponse(url=f"{api_prefix}/docs")


@app.get(f"{api_prefix}/")
def read_root() -> dict:
    """Health check — trả về tên và version ứng dụng."""
    return {"message": f"Welcome to {settings.TITLE_APP}", "version": settings.VERSION_APP}
