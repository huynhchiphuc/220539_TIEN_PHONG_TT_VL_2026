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
- Ảnh trong folder được sắp xếp theo **số trong tên file** (`1.jpg`, `2.png`, `10.webp`, ...)
- Ảnh thứ `n` → khung có `global_order = n`
- Nếu ảnh ít hơn số khung → các khung cuối để trống (tối màu)
- Nếu ảnh nhiều hơn → bỏ qua ảnh thừa

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
| `--bg-color` | `30,30,30` | Màu nền trang (R,G,B) |

**Cấu trúc tên file ảnh được hỗ trợ:**
```
images/
├── 1.jpg       ← khung #1
├── 2.png       ← khung #2
├── 3.webp      ← khung #3
├── ...
└── 30.jpg      ← khung #30
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
