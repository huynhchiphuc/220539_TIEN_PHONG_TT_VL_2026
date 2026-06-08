CHƯƠNG 4  
SẢN PHẨM CỦA ĐỀ TÀI
4.1 Mô tả sản phẩm
Giao diện trang chủ – Upload ảnh:
Giao diện chính của ComicCraft AI được thiết kế tối giản nhưng đầy đủ chức năng. Khu vực trung tâm là vùng upload ảnh hỗ trợ kéo thả (drag-and-drop) hoặc click để chọn từ máy tính – chấp nhận cùng lúc nhiều file JPEG/PNG/WebP. Ảnh sau khi upload được hiển thị dưới dạng thumbnail grid để người dùng xem lại và có thể xóa bỏ ảnh không mong muốn. Thanh trạng thái hiển thị số lượng ảnh đã chọn và ước tính số trang truyện sẽ tạo ra dựa trên số panel mỗi trang đã cấu hình.
 
[Hình 4.1: Giao diện trang chủ – Upload ảnh]
Bảng cấu hình Layout:
Bảng cấu hình bên tay phải cho phép người dùng tùy chỉnh toàn diện quá trình tạo layout. Các tùy chọn bao gồm: Mode (Simple Grid / Advanced Tilted), Aspect Ratio (16:9, 4:3, A4, 9:16, Auto), số Panel mỗi trang (3–8 panels), độ phân giải xuất (HD 1080p / 2K / 4K), độ dày viền khung (Border Width), và bật/tắt tính năng AI Smart Crop. Nút "GENERATE COMIC BOOK" ở cuối bảng kích hoạt toàn bộ pipeline xử lý.
 
[Hình 4.2: Bảng cấu hình Layout – Mode, Aspect Ratio, số Panel]
Kết quả tạo layout – Chế độ Advanced (khung nghiêng):
Ở chế độ Advanced, thuật toán Recursive Polygon Splitting tạo ra các trang truyện với khung hình nghiêng động – đặc trưng phong cách manga/comic chuyên nghiệp. Mỗi lần generate cho kết quả layout khác nhau do yếu tố Jitter ngẫu nhiên, nhưng luôn đảm bảo tính hợp lệ hình học nhờ Shapely Validation. Các đường cắt nghiêng tạo ra cảm giác chuyển động và năng lượng, phù hợp với các cảnh hành động hoặc cảnh có nhiều nhân vật.
 
[Hình 4.3: Kết quả tạo layout – Chế độ Advanced (khung nghiêng)]
Kết quả tạo layout – Chế độ Grid đơn giản:
Chế độ Simple Grid tạo ra layout lưới cổ điển với các khung hình chữ nhật vuông vắn – phù hợp với phong cách truyện tranh phương Tây hoặc slice-of-life. Ưu điểm của chế độ này là tính ổn định cao và tốc độ render nhanh hơn Advanced Mode khoảng 3–5 lần vì không cần tính toán hình học đa giác phức tạp. Thuật toán AR-Driven Area Allocation vẫn được áp dụng để đảm bảo ảnh ngang và dọc nhận được không gian phù hợp.
 
[Hình 4.4: Kết quả tạo layout – Chế độ Grid đơn giản]
Giao diện Tự động tạo khung (Auto Frame Generator):
Tính năng Tự động tạo khung cho phép người dùng nhanh chóng thiết lập và xem thử các bố cục trang truyện mà không cần tải lên hình ảnh trước. Người dùng có thể tùy biến các thông số đầu vào bao gồm: số khung mỗi trang (2–10 panels), độ ngẫu nhiên của bố cục (tỷ lệ phần trăm cắt chéo), tỉ lệ trang (1:1, 2:3, 3:4, 4:5, 9:16) và kích thước độ phân giải đầu ra (1K, 2K, 4K) cùng số lượng trang cần tạo. Sau khi click nút "Tạo khung", hệ thống sử dụng thuật toán chia đa giác ở backend để kết xuất trực tiếp các trang khung rỗng dưới dạng ảnh trực quan. Tại đây, người dùng có thể thực hiện lưu dự án lên Cloud, tải file PDF mẫu hoặc chuyển tiếp sang giao diện thiết kế chính (comic session hiện tại) để tiến hành ghép ảnh vào các ô khung vừa tạo.
 
[Hình 4.5: Giao diện Tự động tạo khung – Auto Frame Generator]
Giao diện Đăng nhập và Đăng ký:
Trang đăng nhập và đăng ký được thiết kế theo phong cách hiện đại với hiệu ứng gradient làm nổi bật thương hiệu ComicCraft AI. Hệ thống hỗ trợ đăng nhập và đăng ký bằng tài khoản email/mật khẩu truyền thống hoặc đăng nhập nhanh thông qua cổng liên kết Google OAuth2. Khi đăng ký tài khoản mới, hệ thống áp dụng các quy chuẩn xác thực mật khẩu nghiêm ngặt (tối thiểu 8 ký tự, bao gồm ít nhất một chữ viết hoa, một chữ viết thường, một chữ số và một ký tự đặc biệt) nhằm đảm bảo an toàn thông tin cho người dùng. Khi đăng nhập thành công, token JWT (JSON Web Token) được lưu trữ ở client để duy trì trạng thái phiên làm việc.
 
[Hình 4.6: Giao diện Đăng nhập / Đăng ký]
Tính năng xuất file PDF/ZIP:
Sau khi người dùng hài lòng với bố cục trang truyện, hệ thống cung cấp ba tùy chọn xuất file: (1) Download từng trang dưới dạng ảnh PNG độ phân giải cao; (2) Download toàn bộ bộ truyện đóng gói trong file ZIP; (3) Xuất PDF nguyên bộ với tùy biến ảnh bìa trước/sau. File PDF được tạo bằng Pillow với cấu hình DPI phù hợp cho in ấn, đảm bảo chất lượng ảnh không bị giảm khi in ra giấy vật lý.
 
[Hình 4.7: Tính năng xuất file PDF/ZIP]
Kiến trúc tổng thể hệ thống:
Hệ thống được triển khai theo kiến trúc Client-Server hai tầng rõ ràng. Frontend React chạy tại port 5173 giao tiếp với Backend FastAPI tại port 60074 thông qua RESTful API (Axios HTTP). Backend được tổ chức theo Service Repository Pattern với ba tầng: Router (nhận request, validate data), Service (business logic – 4 thuật toán lõi), và Utility (hàm dùng chung). Toàn bộ file ảnh upload được lưu tại /uploads và kết quả render lưu tại /outputs trên server. Tích hợp MySQL (tùy chọn) cho phép lưu lịch sử phiên và metadata phục vụ tính năng quản lý project trong tương lai.
 
[Hình 4.8: Kiến trúc tổng thể hệ thống (Backend + Frontend)]
Giao diện Dashboard thống kê và quản lý cá nhân:
Dashboard cung cấp một cái nhìn tổng quan trực quan về tất cả tài nguyên và hoạt động của người dùng trên hệ thống. Giao diện bao gồm 5 khu vực chính: (1) Thẻ thống kê tổng hợp (Summary Cards) hiển thị tổng số dự án, số trang truyện, dung lượng lưu trữ đã dùng (MB) và tổng số lượt hoạt động; (2) Panel thông tin tài khoản hiển thị chi tiết tên đăng nhập, email, ngày tham gia và lịch sử đăng nhập cuối; (3) Nhật ký hoạt động gần đây (Recent Activities) ghi nhận thời gian thực các thao tác như upload ảnh, tạo layout hay export file; (4) Danh sách dự án gần đây hiển thị mã phiên làm việc (session ID), dung lượng và số lượng trang tương ứng; (5) Biểu đồ cột (Bar Chart) phân tích chi tiết tần suất các hành động thực hiện của tài khoản. Dữ liệu này giúp người dùng dễ dàng quản lý kho dự án đám mây và tối ưu tài nguyên lưu trữ cá nhân.
 
[Hình 4.9: Giao diện Dashboard thống kê và quản lý cá nhân]

