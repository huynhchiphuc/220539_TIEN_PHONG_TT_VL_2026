# app/utils/__init__.py
# Thêm thư mục utils vào sys.path để các module trong đây import nhau được
import sys
import os

_utils_dir = os.path.dirname(os.path.abspath(__file__))
if _utils_dir not in sys.path:
    sys.path.insert(0, _utils_dir)
