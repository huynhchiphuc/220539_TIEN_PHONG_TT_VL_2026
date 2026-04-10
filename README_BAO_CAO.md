# BÁO CÁO KỸ THUẬT: HỆ THỐNG TỰ ĐỘNG TẠO LAYOUT TRUYỆN TRANH BẰNG TRÍ TUỆ NHÂN TẠO

## 1. TỔNG QUAN DỰ ÁN
Dự án là một hệ thống ứng dụng Web (Backend Python FastAPI & Frontend ReactJS) cho phép tự động phân tích và tạo bố cục trang truyện tranh (Comic/Webtoon) từ một danh sách các hình ảnh đầu vào. 
Hệ thống sử dụng các thuật toán hình học động (Dynamic Geometry) kết hợp Trí tuệ nhân tạo (Computer Vision) để tự động nhận dạng ngữ cảnh hình ảnh, từ đó phân bổ diện tích khung truyện hợp lý và chuyên nghiệp nhất.

---

## 2. CÁC THƯ VIỆN CHÍNH (LIBRARIES)
Backend Python sử dụng các thư viện tính toán và xử lý tiên tiến nhất:
- **FastAPI / Uvicorn**: Xây dựng API tốc độ cao, hỗ trợ bất đồng bộ (Asynchronous) để xử lý lượng lớn ảnh đồng thời.
- **Pillow (PIL)**: Đọc, ghi và xử lý đồ họa vector/raster cơ bản, chịu trách nhiệm chính trong việc crop và dán ảnh vào panel.
- **NumPy**: Xử lý mảng ma trận số học. Tính toán phân vùng không gian (Coordinate system), tỷ lệ % diện tích và tính toán ma trận điểm cho các đa giác.
- **Shapely**: Thư viện xử lý hình học đa giác (Polygon). Dùng để kiểm tra tính hợp lệ của các khung truyện, đảm bảo đa giác không tự cắt rỗng (Self-intersecting polygons) hay bị biến dạng tam giác.
- **OpenCV (cv2)**: Thư viện Thị giác máy tính xử lý mảng nội dung. Dùng để Canny Edge, tìm Contour, Laplacian Blur, và MSER detecting cho các vùng Text.
- **Ultralytics (YOLO8)**: Mô hình AI Deep Learning dò tìm vùng có con người (Person Detection).
- **EasyOCR / HAAR Cascades**: Dùng làm Fallback detect chữ và khuôn mặt nếu model lớn gặp sự cố.

---

## 3. CÁC THUẬT TOÁN VÀ GIẢI THUẬT CHÍNH
Hệ thống kết hợp 4 thuật toán lõi để giải quyết bài toán chia trang phức tạp của họa sĩ truyện tranh:

### 3.1. Phân bổ diện tích theo tỷ lệ thuận (AR-Driven Area Allocation)
* **Mục tiêu:** Không chia đôi khung ảnh một cách mù quáng (50/50). Ảnh ngang cần khung dài, ảnh dọc cần khung đứng.
* **Quy trình:**
  - Quy đổi tỷ lệ ảnh đầu vào thành Aspect Ratio (AR) `AR = Width / Height`. Phân nhóm thành: Hình chữ nhật Ngang (`AR > 1.25`), Dọc (`AR < 0.8`) hoặc Vuông.
  - Khi ghép nhóm trên 1 hàng, trọng số chiều rộng của mỗi ảnh sẽ bằng chính tỷ lệ AR của nó: `width_weight = aspect_ratio / total_aspect_ratio`.
  - Từ đó, các mảnh lưới sẽ được đẩy lệch sang hai bên thay vì nằm ở giữa trang, bảo toàn triệt để nội dung ngang mà không bị bóp nghẹt.

### 3.2. Thuật toán bù đắp đệm dọc (Vertical Dynamic Padding)
* **Mục tiêu:** Chống hiện tượng kéo giãn dọc ảnh ngang (Stretch Deforming) khi có quá ít ảnh trên một khung giấy dài (VD: 9:16).
* **Quy trình giải thuật:**
  - Tính toán **Lý thuyết Chiều cao Tối ưu** (Ideal Usable Height) của khối ảnh dựa trên tổng trọng số Tỷ lệ nghịch `1.0 / (Cols * Avg_AR)`.
  - Giới hạn phép giãn căng tối đa là **15%** (`ideal_h * 1.15`) để bao phủ lề.
  - Nếu kích thước giấy tĩnh vượt quá ngưỡng này (do quá ít khung trong trang cuối), hệ thống sẽ **DỪNG** kéo dãn, bảo lưu chiều cao chuẩn Toán học và tự động tính `vertical_padding = (height - max_height) / 2` để đẩy cụm hình ra chính giữa giấy.

### 3.3. Trí tuệ Nhân tạo Can thiệp Bố cục (AI Context & OCR Boost)
* **Mục tiêu:** Phát hiện vùng quan trọng chứa Nội dung tĩnh, Bong bóng thoại hoặc Chữ cái để can thiệp chia diện tích.
* **Thuật toán:**
  - YOLO & Contour check quét toàn bộ ảnh đếm `text_count` và `bubble_count`.
  - Phân vùng trọng số: Chữ viết (Trọng số `x3.0`) > Bong bóng thoại (`x2.5`) > Nhân vật (`x2.0`).
  - **OCR Aspect Booting**: Khảo sát mật độ chữ và "bơm phồng" Aspect nguyên bản của khung tranh chứa chữ thêm **+10% đến +40%** chiều ngang. Thuật toán layout bị lừa và sẽ tự động cấp mảnh giấy cực rộng cho panel đó hiển thị số lượng lớn chữ thoại mà không bị Crop xén.

### 3.4. Cắt đa giác đệ quy và Kiểm tra Hình học (Recursive Polygon Splitting)
* **Mục tiêu:** Tạo các khung truyện nghiêng (tilted/diagonal) một cách ngẫu nhiên nhưng phải hợp lệ.
* **Quy trình:**
  - Coi trang giấy là 1 tứ giác lồi khổng lồ tọa độ (X, Y).
  - Thuật toán `Split` sẽ băm khối tứ giác bằng các đường chẻ nghiêng `y_left != y_right` với độ tự do Jitter.
  - **Shapely Validation**: Kiểm tra tính lồi của đa giác sinh ra (`convex`) hoặc diện tích nhỏ quá mức. Nếu đường cắt đi chéo nhau tạo thành hình tam giác hỏng 2 đáy, thuật toán lập tức xoá nhánh đệ quy đó và tạo đường cắt thẳng thay thế.

---

## 4. CẤU TRÚC PROJECT (BACKEND PYTHON)
Kiến trúc bám sát triết lý chia tầng trách nhiệm **Single Responsibility Principle** và **Service Repository Pattern**.

```
backend/api_base_public/
│
├── app/
│   ├── api/
│   │   └── routers/            # Nhận Request, validate data trả về cho Frontend (comic.py, auth.py)
│   │
│   ├── services/
│   │   ├── comic/              # CORE: Xử lý logic nghiệp vụ tạo Layout
│   │   │   ├── comic_book_auto_fill.py   # Lõi điều phối (Orchestrator): Gom nhóm ảnh, chia số lượng frame cho các trang, Look-ahead ngắt trang.
│   │   │   ├── comic_layout_algorithms.py# Engine phép tính Hình học đệ quy, tạo các điểm cắt đa giác Tilted Grid & Advanced Layout.
│   │   │   ├── comic_layout_simple.py    # Engine dự phòng (Fallback): Layout lưới cổ điển với dynamic gap.
│   │   │   ├── comic_layout_generator.py # Render engine: Điền ảnh, xử lý bo góc, viền border vào panel trống.
│   │   │   └── comic_utils.py            # Utility đệm: Xác định các siêu tham số, boost OCR và xử lý tỷ lệ.
│   │   │
│   │   └── ai/                 # CORE: Xử lý trí tuệ nhân tạo 
│   │       ├── smart_crop.py             # Crop Focus: Phân mảnh Bounding Box, Merge IOU với trọng số để lấy tâm nhìn (Focal point).
│   │       ├── character_classifier.py   # Phân loại độ tuổi, gương mặt.
│   │       └── image_analyzer.py         # Thống kê Motion Score, Mật độ biên (Density edge).
│   │
│   ├── models/                 # Database Schema/Pydantic Model.
│   └── core/                   # Cấu hình base, JWT, DB Config.
│
├── run_api.py                  # Điểm khởi chạy ASGI Uvicorn Server.
└── requirements.txt            # Tập hợp các thư viện Python cần thiết.
```

## 5. CÁC TÍNH NĂNG VÀ CHỨC NĂNG CHÍNH (FEATURE HIGHLIGHTS)
- **Automatic Page & Panel Allocation**: Tiếp nhận hàng trăm ảnh và tự chia gọn gàng vào các trang giới hạn Frame. Cô lập ảnh lẻ loi (Orphan Panel) lùi sang trang tiếp theo bằng thuật toán nhìn trước (Look-ahead).
- **Adaptive Canvas Dimensioning**: Background kích thước tự động co giãn ôm theo loại ảnh đầu vào đa số hay thiểu số.
- **Context-Aware Smart Cropping**: Giữ lại mọi nội dung có giá trị (Text/Mặt/Cảnh) ngay cả khi khung tỷ lệ bị bép nhỏ.
- **Fallback Layout Mechanism**: Khi thuật toán đa giác ngẫu nhiên sụp đổ (Vẽ sai hình), nó có màng lưới an toàn (Grid lưới) hứng lại để bảo đảm hệ thống web không bao giờ văng Exception `500 Server Error`.
- **Dynamic Orientation Mixing**: Trộn nhiều dạng ảnh trong cùng dòng nhưng không bị lỗi kích thước xô lệch do hệ số nhân AR động.
