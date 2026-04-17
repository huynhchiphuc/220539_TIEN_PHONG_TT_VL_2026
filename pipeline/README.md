# Pipeline Sinh Layout Truyện Tranh

Gồm **3 pipeline** chạy nối tiếp nhau:

```
Pipeline 1                    Pipeline 2                    Pipeline 3
──────────────────────        ──────────────────────────    ───────────────────────────
generate_layout.py     →      render_preview.py        →    compose_pages.py
  (sinh cấu trúc JSON)          (render preview layout)       (bỏ ảnh thật vào khung)
```

---

## Cài đặt

```bash
pip install -r requirements.txt
```

Dependencies: `numpy`, `Pillow`

---

## Pipeline 1 — Sinh JSON Layout

**File:** `generate_layout.py`

Nhận: số trang, số khung/trang, tỉ lệ trang  
Xuất: file JSON chứa cấu trúc khung của tất cả trang

```bash
python generate_layout.py --pages 5 --panels 6 --aspect 9:16
python generate_layout.py --pages 3 --panels 4 --aspect 2:3 --out my_layout.json --seed 42
python generate_layout.py --pages 1 --panels 3 --aspect 1:1 --pretty
```

| Tham số | Mặc định | Mô tả |
|---------|----------|-------|
| `-p`, `--pages` | 3 | Số trang |
| `-n`, `--panels` | 5 | Số khung/trang |
| `-a`, `--aspect` | `9:16` | Tỉ lệ trang (`9:16`, `2:3`, `3:4`, `4:5`, `1:1`, `16:9`) |
| `-o`, `--out` | tự động | Tên file JSON đầu ra |
| `--seed` | ngẫu nhiên | Seed để tái tạo kết quả |
| `--pretty` | false | In JSON đẹp (indent=2) |

---

## Pipeline 2 — Render Preview Layout

**File:** `render_preview.py`

Nhận: file JSON từ Pipeline 1  
Xuất: ảnh preview (màu pastel, số thứ tự, kích thước) cho từng trang

```bash
python render_preview.py layout.json
python render_preview.py layout.json --out-dir preview --scale 0.4
python render_preview.py layout.json --page 2 --format jpg
```

| Tham số | Mặc định | Mô tả |
|---------|----------|-------|
| `json_file` | (bắt buộc) | File JSON từ Pipeline 1 |
| `--out-dir` | `preview/` | Thư mục lưu ảnh |
| `--scale` | 0.5 | Tỉ lệ kích thước (1.0 = full res) |
| `--format` | `png` | Định dạng ảnh |
| `--page` | tất cả | Chỉ render một trang cụ thể |

---

## Pipeline 3 — Bỏ Ảnh Vào Khung

**File:** `compose_pages.py`

Nhận: file JSON layout + folder ảnh  
Xuất: trang truyện hoàn chỉnh với ảnh thật đặt trong từng khung

**Quy tắc sắp xếp ảnh:**
- Đọc file JSON và ánh xạ chính xác với ảnh trong folder thông qua cấu trúc tên (ví dụ: **`page_001_panel_01.jpg`**) tương ứng với trường `file_name` của tệp JSON.
- **Smart Fallback (Dự phòng thông minh):** 
  - Nếu định dạng ảnh sai lệch (ví dụ đuôi thật là `.png` nhưng JSON lưu là `.jpg`), thuật toán tự động nhận diện theo tên gốc (stem) `page_001_panel_01`.
  - Nếu data ảnh cũ chỉ đặt tên độc lập dạng (`1.png`, `2.jpg`), thuật toán tự động fallback sắp xếp số thứ tự để gán map bằng `global_order`.
- Nếu số ảnh ít hơn tổng số khung → các khung cuối thiếu ảnh được để trống.
- Nếu số ảnh nhiều hơn khung layout → hệ thống sẽ bỏ qua ảnh thừa ở cuối.

**Cách đặt ảnh vào khung:** Scale + center-crop (cover mode) – giữ tỉ lệ gốc, không kéo méo.

```bash
python compose_pages.py layout.json images/
python compose_pages.py layout.json images/ --out-dir output --scale 1.0
python compose_pages.py layout.json images/ --page 2 --format jpg
python compose_pages.py layout.json images/ --bg-color 255,255,255
```

| Tham số | Mặc định | Mô tả |
|---------|----------|-------|
| `json_file` | (bắt buộc) | File JSON layout |
| `image_dir` | (bắt buộc) | Folder chứa ảnh |
| `--out-dir` | `output/` | Thư mục lưu kết quả |
| `--scale` | 1.0 | Tỉ lệ kích thước (1.0 = full res) |
| `--format` | `png` | Định dạng ảnh (`png` hoặc `jpg`) |
| `--page` | tất cả | Chỉ render một trang cụ thể |
| `--bg-color` | `255,255,255` | Màu nền trang (R,G,B) mặc định là nền trắng đậm phong cách truyện tranh. |

**Cấu trúc tên file ảnh được hỗ trợ:**
```
images/
├── page_001_panel_01.jpg   ← trang 1, khung #1
├── page_001_panel_02.png   ← trang 1, khung #2
├── page_001_panel_03.webp  ← trang 1, khung #3
├── ...
└── page_005_panel_06.jpg   ← trang 5, khung cuối cùng (nếu có)
```

---

## Chạy Toàn Bộ Pipeline

```bash
# Bước 1: Sinh JSON layout
python generate_layout.py --pages 5 --panels 6 --aspect 9:16 --out layout.json

# Bước 2: Xem preview layout (tùy chọn)
python render_preview.py layout.json --out-dir preview --scale 0.5

# Bước 3: Bỏ ảnh vào khung → trang truyện hoàn chỉnh
python compose_pages.py layout.json images/ --out-dir output --scale 1.0
```

---

## Cấu Trúc File

```
pipeline/
├── generate_layout.py          # Pipeline 1: sinh JSON layout
├── render_preview.py           # Pipeline 2: render preview layout
├── compose_pages.py            # Pipeline 3: bỏ ảnh vào khung
├── comic_layout_algorithms.py  # Engine thuật toán (recursive subdivision)
├── comic_utils.py              # Tiện ích: phân loại aspect ratio
├── requirements.txt            # Dependencies: numpy, Pillow
└── README.md
```
