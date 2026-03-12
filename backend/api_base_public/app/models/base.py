from pydantic import BaseModel


# Định nghĩa mô hình dữ liệu cho người dùng
class Base(BaseModel):
    id: int
