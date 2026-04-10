import argparse
import os
import sys

# Đảm bảo có thể import được các module trong app/
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.comic.comic_layout_simple import process_comic_layout

def main():
    parser = argparse.ArgumentParser(description="Chương trình CLI tạo Comic (Chế độ SIMPLE GRID).")
    
    parser.add_argument("--folder", required=True, help="Đường dẫn thư mục chứa ảnh đầu vào")
    parser.add_argument("--output", required=True, help="Đường dẫn thư mục để xuất file hoàn thiện")
    parser.add_argument("--panels", type=int, default=5, help="Số khung tối đa mỗi trang (Mặc định: 5)")
    parser.add_argument("--aspect", type=str, default="9:16", help="Tỉ lệ trang (vd 9:16) (Mặc định: 9:16)")

    args = parser.parse_args()

    input_folder = os.path.abspath(args.folder)
    output_folder = os.path.abspath(args.output)
    
    # Tính toán kích thước trang tương phản với Aspect
    w_ratio, h_ratio = 9, 16
    try:
        if ":" in args.aspect:
            parts = args.aspect.split(":")
            w_ratio, h_ratio = int(parts[0]), int(parts[1])
    except:
        pass
        
    page_width = 1200
    page_height = int(page_width * h_ratio / w_ratio)

    if not os.path.exists(input_folder):
        print(f"❌ LỖI: Thư mục input '{input_folder}' không tồn tại!")
        sys.exit(1)
        
    # Tạo output nếu chưa có
    os.makedirs(output_folder, exist_ok=True)
    
    # Base suffix để render thành page_001.jpg
    output_filename = os.path.join(output_folder, "page.jpg")

    print("="*60)
    print("✨ TIẾN TRÌNH CREATE COMIC ĐANG KHỞI CHẠY (CHẾ ĐỘ SIMPLE)")
    print(f"📂 Nguồn ảnh (Folder)  : {input_folder}")
    print(f"💾 Nơi xuất (Output)   : {output_folder}")
    print(f"📄 Tối đa khung/trang  : {args.panels}")
    print(f"📐 Kích thước render   : {page_width}x{page_height}px (Tỉ lệ {args.aspect})")
    print("="*60)

    # Chạy Engine Simple Grid ngang/dọc
    process_comic_layout(
        input_folder=input_folder,
        output_filename=output_filename,
        page_width=page_width,
        margin=30,      # Viền trắng bao quanh trang
        gap=25,         # Khoảng cách giữa các phần tử
        page_height=page_height,
        panels_per_page=args.panels,
        use_smart_crop=True,        # Kích hoạt Crop giữ mặt chừa nội dung trọng tâm
        analyze_shot_type=True      # Kích hoạt phân tích AI góc nhìn
    )

    print("\n✅ HOÀN TẤT KỊCH BẢN SIMPLE! Các trang truyện tranh đã được dán vào:")
    print("👉", output_folder)

if __name__ == "__main__":
    main()
