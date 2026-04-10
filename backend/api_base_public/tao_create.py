import argparse
import os
import sys

# Đảm bảo có thể import được các module trong app/ mà không bị lỗi ModuleNotFoundError
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.comic.comic_book_auto_fill import create_comic_book_from_images

def main():
    # 1. Khởi tạo ArgumentParser
    parser = argparse.ArgumentParser(description="Chương trình CLI tạo Comic từ danh sách ảnh.")
    
    # 2. Định nghĩa các tham số
    parser.add_argument("--folder", required=True, help="Đường dẫn thư mục chứa ảnh đầu vào")
    parser.add_argument("--output", required=True, help="Đường dẫn thư mục để xuất file hoàn thiện")
    parser.add_argument("--panels", type=int, default=5, help="Số khung dự kiến mỗi trang (Mặc định: 5)")
    parser.add_argument("--aspect", type=str, default="9:16", help="Tỉ lệ kích thước trang (Mặc định: 9:16)")

    # 3. Parse các tham số do người dùng nhập vào
    args = parser.parse_args()

    input_folder = os.path.abspath(args.folder)
    output_folder = os.path.abspath(args.output)

    # 4. Kiểm tra thư mục đầu vào có tồn tại thực sự hay không
    if not os.path.exists(input_folder):
        print(f"❌ LỖI TRẦM TRỌNG: Thư mục input '{input_folder}' không tồn tại!")
        print("Vui lòng kiểm tra lại đường dẫn nhập vào.")
        sys.exit(1)

    print("="*60)
    print("🚀 TIẾN TRÌNH CREATE COMIC ĐANG KHỞI CHẠY (CLI MODE)")
    print(f"📂 Nguồn ảnh (Folder) : {input_folder}")
    print(f"💾 Nơi xuất (Output)  : {output_folder}")
    print(f"📄 Khung/trang (Panels): {args.panels}")
    print(f"📐 Tỉ lệ (Aspect)     : {args.aspect}")
    print("="*60)

    # 5. Khởi động hàm lõi siêu mạnh (Có sẵn của Dự án Comic Generator)
    create_comic_book_from_images(
        image_folder=input_folder,
        output_folder=output_folder,
        panels_per_page=args.panels,
        aspect_ratio=args.aspect,
        diagonal_prob=0.3,
        adaptive_layout=True,
        analyze_shot_type=True,   # Ép bật tính năng boost Aspect / OCR
        use_smart_crop=True       # Ép bật tính năng Crop Face thông minh
    )

    print("\n✅ HOÀN TẤT KỊCH BẢN! Khung tranh hoàn chỉnh đã được đẩy vào:")
    print("👉", output_folder)

if __name__ == "__main__":
    main()
