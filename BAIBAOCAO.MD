TRƯỜNG ĐẠI HỌC NAM CẦN THƠ
TRƯỜNG CÔNG NGHỆ SỐ VÀ TRÍ TUỆ NHÂN TẠO


 



BÁO CÁO THỰC TẬP

XÂY DỰNG HỆ THỐNG TỰ ĐỘNG TẠO LAYOUT TRUYỆN TRANH BẰNG TRÍ TUỆ NHÂN TẠO 










Họ và tên sinh viên: Huỳnh Chí Phúc	Mã số SV: 220359
Lớp: DH22TIN04	Ngành: Công nghệ thông tin
Họ và tên giảng viên hướng dẫn: ThS. Nguyễn Mỹ Phụng 
Họ và tên cán bộ hướng dẫn tại nơi thực tập: KS. Võ Khương Duy




Cần Thơ, tháng 06 năm 2026
TRƯỜNG ĐẠI HỌC NAM CẦN THƠ
TRƯỜNG CÔNG NGHỆ SỐ VÀ TRÍ TUỆ NHÂN TẠO


 



BÁO CÁO THỰC TẬP

XÂY DỰNG HỆ THỐNG TỰ ĐỘNG TẠO LAYOUT TRUYỆN TRANH BẰNG TRÍ TUỆ NHÂN TẠO 










Họ và tên sinh viên: Huỳnh Chí Phúc	Mã số SV: 220359
Lớp: DH22TIN04	Ngành: Công nghệ thông tin
Họ và tên giảng viên hướng dẫn: ThS. Nguyễn Mỹ Phụng 
Họ và tên cán bộ hướng dẫn tại nơi thực tập: KS. Võ Khương Duy




Cần Thơ, tháng 06 năm 2026
LỜI CẢM ƠN
Với lòng biết ơn sâu sắc và tình cảm chân thành em xin gửi lời cảm ơn tới:
Trường Đại học Nam Cần Thơ, Trường Công nghệ Số và Trí tuệ Nhân tạo, cùng các giảng viên đã tận tình chỉ dạy và tạo điều kiện giúp đỡ em trong quá trình học tập, nghiên cứu đề tài.
Đặc biệt, em xin gửi lời cảm ơn chân thành đến Cô Nguyễn Mỹ Phụng đã tận tình theo dõi, chỉ bảo và động viên em trong suốt quá trình thực tập tốt nghiệp. Những nhận xét và góp ý sâu sắc của Thầy đã giúp em định hướng đúng và hoàn thiện đề tài một cách tốt nhất.
Xin gửi lời cảm ơn đến Anh/Chị cán bộ hướng dẫn tại cơ sở thực tập – Công ty TNHH MTV Công Nghệ Kỹ Thuật Tiên Phong đã tạo điều kiện cho em được trực tiếp tham gia vào dự án thực tế, chia sẻ kinh nghiệm chuyên môn và hỗ trợ em trong từng bước thực hiện dự án ComicCraft AI.
Đồng thời, em cũng xin cảm ơn các bạn bè đã hỗ trợ, góp ý về nội dung và hình thức trong quá trình thực hiện đề tài.
Mặc dù đã cố gắng rất nhiều nhưng do kiến thức còn hạn chế nên không tránh khỏi những thiếu sót trong quá trình thực hiện đề tài. Vì thế, rất mong nhận được những ý kiến đóng góp của quý Thầy Cô, để em có thêm những kinh nghiệm và rút ra bài học quý báu cho công việc chuyên môn về sau.
Em xin chân thành cảm ơn! Trân trọng.

Cần Thơ, ngày 08 tháng 06 năm 2026.

Sinh viên thực hiện


Huỳnh Chí Phúc
 
MỤC LỤC
CHƯƠNG 1  GIỚI THIỆU	5
1.1 Giới thiệu công ty	5
1.2 Thông tin về công ty	5
1.3 Trụ sở chính	5
1.4 Người đại diện theo pháp luật	6
1.5 Thông tin liên hệ	6
1.6 Các công việc được giao	6
CHƯƠNG 2 CƠ SỞ LÝ THUYẾT – PHƯƠNG PHÁP NGHIÊN CỨU	7
2.1 Lịch sử đề tài	7
2.2 Công cụ và mã nguồn	8
2.2.1 Công cụ soạn thảo văn bản	8
2.2.2 Công cụ sử dụng lập trình	8
2.2.3 Ngôn ngữ dùng trong đề tài	8
2.2.4 Framework	9
2.2.5 Thư viện (Library)	9
CHƯƠNG 3   NGHIÊN CỨU YÊU CẦU ĐỀ TÀI	11
3.1 Mô tả các yêu cầu đề tài	11
3.2 Mô tả các thành phần và thuật toán lõi	11
CHƯƠNG 4   SẢN PHẨM CỦA ĐỀ TÀI	13
4.1 Mô tả sản phẩm	13
CHƯƠNG 5  KẾT QUẢ ĐẠT ĐƯỢC QUA ĐỢT THỰC TẬP	18

  
DANH MỤC HÌNH
[Hình 4.1: Giao diện trang chủ – Upload ảnh]	10
[Hình 4.2: Bảng cấu hình Layout – Mode, Aspect Ratio, số Panel]	11
[Hình 4.3: Kết quả tạo layout – Chế độ Advanced (khung nghiêng)]	11
[Hình 4.4: Kết quả tạo layout – Chế độ Grid đơn giản]	12
[Hình 4.5: Giao diện Tự động tạo khung – Auto Frame Generator]	13
[Hình 4.6: Giao diện Đăng nhập / Đăng ký]	14
[Hình 4.7: Tính năng xuất file PDF/ZIP]	13
[Hình 4.8: Kiến trúc tổng thể hệ thống (Backend + Frontend)]	15
[Hình 4.9: Giao diện Quản lý Dự án]	16
 
CHƯƠNG 1  
GIỚI THIỆU
1.1 Giới thiệu công ty
Công ty TNHH MTV Công Nghệ Kỹ Thuật Tiên Phong đại diện cho một thực thể doanh nghiệp chuyên biệt trong lĩnh vực công nghệ và kỹ thuật tại Việt Nam. Đơn vị được thành lập dựa trên nguyên lý cốt lõi là phát triển và triển khai các giải pháp công nghệ tiên tiến có tính đột phá cao. Hoạt động của công ty được định hướng nghiên cứu một cách hệ thống, tập trung vào việc phát triển các sản phẩm và dịch vụ công nghệ cao với tính ứng dụng thực tiễn.
Nguồn lực nhân sự của đơn vị được cấu trúc theo mô hình chuyên nghiệp, bao gồm các chuyên gia có kinh nghiệm chuyên môn cao và định hướng phát triển bền vững. Phương pháp tiếp cận đa chiều này đã giúp Công ty TNHH MTV Công Nghệ Kỹ thuật Tiên Phong thiết lập vị thế đáng tin cậy trong hệ sinh thái đối tác cả trong và ngoài phạm vi quốc gia.
Thông qua việc áp dụng phương pháp phát triển dựa trên nguyên lý khoa học kỹ thuật, công ty đã xác lập được vị trí đáng kể trong lĩnh vực công nghệ. Các kết quả nghiên cứu và triển khai của đơn vị đã minh chứng khả năng đổi mới sáng tạo và tiềm năng phát triển bền vững trong bối cảnh chuyển đổi công nghệ hiện tại.
1.2 Thông tin về công ty
Tên công ty tiếng Việt: Công Ty TNHH Một Thành Viên Công Nghệ Kỹ Thuật Tiên Phong
Tên công ty tiếng Anh: ADVANCED HIGH TECHNOLOGY ONE MEMBER LIMITED LIABILITY COMPANY
Tên viết tắt: ADHIGHTECH
Mã số thuế: 1801526082
Lĩnh vực kinh doanh: Nghiên cứu và phát triển công nghệ; Sản xuất và cung cấp thiết bị kỹ thuật; Dịch vụ tư vấn và giải pháp công nghệ.
1.3 Trụ sở chính
Số B16, đường số 08, khu dân cư Công Ty 8, Phường Phú Thứ, Quận Cái Răng, Thành phố Cần Thơ.
1.4 Người đại diện theo pháp luật
Họ và tên: NGÔ HỒ ANH KHÔI
Chức vụ: Giám đốc / CEO
1.5 Thông tin liên hệ
Địa chỉ: Số B16, đường số 08, khu dân cư Công Ty 8, Phường Phú Thứ, Quận Cái Răng, TP. Cần Thơ.
Điện thoại: 0353220302
Email: nhakhoi@nctu.edu.vn
Website công ty: https://www.adhightechn.com/
1.6 Các công việc được giao
- Tích hợp Ultralytics YOLOv8 cho Person Detection - Tích hợp OpenCV (Canny Edge, MSER, Contour) để phân tích nội dung ảnh - Tích hợp Shapely cho kiểm tra tính hợp lệ đa giác
- Xây dựng Smart Crop module: Bounding Box Merge + IOU Weighting để tìm focal point - Phát triển tính năng OCR Aspect Boosting: "bơm phồng" aspect ratio cho panel chứa nhiều chữ - Chuẩn hoá code theo cấu trúc Service Repository Pattern
- Xây dựng Frontend ReactJS + Vite: Upload ảnh, cấu hình layout, xem trước trang truyện - Kết nối Frontend - Backend qua Axios và REST API
- Tích hợp tính năng xuất file: Download PNG từng trang, đóng gói ZIP, xuất PDF nguyên bộ - Tích hợp MySQL để lưu thông tin người dùng, quản lý dự án và đồng bộ hóa đám mây
- Kiểm tra toàn bộ sản phẩm, viết tài liệu kỹ thuật (README.md, README_BAO_CAO.md) - Đánh giá sản phẩm và demo trình bày với cán bộ hướng dẫn
CHƯƠNG 2
CƠ SỞ LÝ THUYẾT – PHƯƠNG PHÁP NGHIÊN CỨU
2.1 Lịch sử đề tài
Trong kỷ nguyên số hóa nội dung sáng tạo, nhu cầu tạo ra truyện tranh (comic/webtoon) ngày càng tăng cao không chỉ trong giới chuyên nghiệp mà còn lan rộng đến cộng đồng sáng tác nghiệp dư. Theo thống kê của các nền tảng đọc truyện châu Á, lượng tác phẩm webtoon tự xuất bản tăng hơn 300% trong giai đoạn 2020–2024, phản ánh nhu cầu bức thiết về các công cụ hỗ trợ tự động hóa quy trình sắp trang (Naver Webtoon Report, 2024).
Trước đây, việc sắp xếp bố cục trang truyện đòi hỏi họa sĩ phải thực hiện thủ công bằng các phần mềm như Adobe Photoshop hoặc Clip Studio Paint – một quy trình tốn nhiều thời gian và đòi hỏi kinh nghiệm thiết kế đồ họa chuyên sâu. Mỗi trang truyện có thể mất từ 2 đến 4 giờ chỉ để sắp xếp khung hình, chưa kể đến việc điều chỉnh tỷ lệ và crop ảnh phù hợp (Tran et al., 2023).
Sự xuất hiện của Computer Vision và các mô hình học sâu đã mở ra hướng tiếp cận mới: tự động phân tích nội dung ảnh để đưa ra quyết định bố cục thông minh. Các nghiên cứu về Saliency Detection (nơi mắt người nhìn vào trong ảnh) và Object Detection đã tạo nền tảng lý thuyết cho các ứng dụng layout tự động (Itti & Koch, 2000; Redmon et al., 2016). Mô hình YOLO (You Only Look Once) với khả năng nhận diện đối tượng thời gian thực đã trở thành công cụ phổ biến trong các bài toán phân tích ảnh tự động.
Tuy nhiên, các giải pháp tạo layout comic tự động vẫn còn rất hạn chế. Phần lớn các công cụ hiện tại chỉ hỗ trợ chia lưới đơn giản (Grid Layout) mà không tính đến tỷ lệ nội dung ảnh, dẫn đến tình trạng ảnh bị bóp méo hoặc crop mất nội dung quan trọng. Chưa có công cụ nào kết hợp được cả thuật toán hình học động, AI phân tích nội dung và cơ chế OCR để tối ưu hóa toàn diện bố cục trang truyện.
Đề tài ComicCraft AI được hình thành nhằm giải quyết khoảng trống này: xây dựng một hệ thống Web Full-stack có khả năng tự động tiếp nhận hàng chục đến hàng trăm ảnh đầu vào, phân tích nội dung từng ảnh bằng AI, sau đó phân bổ và sắp xếp các khung truyện một cách hợp lý và thẩm mỹ nhất. Đây là đề tài mang tính ứng dụng thực tiễn cao, kết hợp nhiều lĩnh vực kỹ thuật hiện đại từ Backend Python, Computer Vision, hình học đa giác đến Frontend ReactJS.
2.2 Công cụ và mã nguồn
2.2.1 Công cụ soạn thảo văn bản
Microsoft Word là công cụ soạn thảo văn bản chính được sử dụng trong quá trình viết báo cáo thực tập. Với khả năng định dạng phong phú, hỗ trợ font Unicode Times New Roman và công cụ kiểm tra chính tả tiếng Việt, Microsoft Word giúp em tạo ra tài liệu báo cáo đúng chuẩn định dạng của Khoa. Ngoài ra, em còn sử dụng Visual Studio Code cho việc viết code và ghi chú kỹ thuật nhờ tích hợp nhiều tiện ích hỗ trợ lập trình Python và JavaScript.
2.2.2 Công cụ sử dụng lập trình
Python 3.10 là ngôn ngữ lập trình nền tảng của toàn bộ hệ thống Backend. Phiên bản này mang lại nhiều cải tiến quan trọng đặc biệt phù hợp cho dự án: cú pháp match-case (Structural Pattern Matching) giúp xử lý các trường hợp phân nhánh trong thuật toán layout một cách rõ ràng hơn; cải tiến về asyncio cho phép xử lý bất đồng bộ nhiều request upload ảnh đồng thời với độ trễ thấp; và tối ưu hóa CPython interpreter giúp tăng tốc các phép tính NumPy trong engine hình học.
Visual Studio Code được chọn là môi trường phát triển tích hợp (IDE) chính nhờ hỗ trợ debugging Python nâng cao, tích hợp terminal Git, hỗ trợ Jupyter Notebook cho việc thử nghiệm thuật toán, và extension Pylance cho type checking. Ngoài ra, Git được sử dụng để quản lý phiên bản mã nguồn theo workflow feature branch trong suốt quá trình phát triển dự án.
2.2.3 Ngôn ngữ dùng trong đề tài
Python là ngôn ngữ lập trình chính phía Backend với cú pháp gần gũi, dễ đọc và hệ sinh thái thư viện khoa học/AI cực kỳ phong phú. Điểm mạnh của Python trong đề tài này nằm ở khả năng xử lý linh hoạt các cấu trúc dữ liệu phức tạp (list of polygons, coordinate matrices, bounding boxes) và tích hợp trơn tru với các thư viện Computer Vision như OpenCV và YOLO. (Ngô Hồ Anh Khôi, Trương Hùng Chen và Huỳnh Bá Lộc, 2021)
JavaScript (ES6+) được sử dụng phía Frontend thông qua React 19 và Vite 8. JavaScript cung cấp các tính năng hiện đại như destructuring, spread syntax, arrow functions và async/await giúp xây dựng giao diện người dùng tương tác cao. Đặc biệt, khả năng xử lý sự kiện drag-and-drop và preview file ảnh trong trình duyệt là yêu cầu thiết yếu của ứng dụng ComicCraft AI.
2.2.4 Framework
FastAPI là framework Python không đồng bộ hiệu suất cao được chọn cho Backend. FastAPI tận dụng type hints của Python kết hợp Pydantic để xác thực dữ liệu tự động, đồng thời tạo tài liệu OpenAPI (Swagger UI) tại /api/v1/docs mà không cần viết thêm code. Khả năng xử lý bất đồng bộ (async/await) của FastAPI đặc biệt quan trọng khi cần xử lý đồng thời nhiều ảnh lớn – mỗi ảnh cần qua pipeline: upload → AI analysis → layout calculation → render → export.
React 19 kết hợp Vite 8 tạo nên Frontend có tốc độ render và build cực nhanh. React's Virtual DOM cho phép cập nhật giao diện hiệu quả khi người dùng kéo thả ảnh vào các panel, trong khi Vite's HMR (Hot Module Replacement) rút ngắn đáng kể thời gian phát triển. React Router DOM quản lý điều hướng giữa các trang (Login, Dashboard, ComicGenerator) một cách mượt mà.
2.2.5 Thư viện (Library)
Pillow (PIL) là thư viện xử lý hình ảnh nền tảng của hệ thống, chịu trách nhiệm chính trong việc đọc/ghi file ảnh (JPEG, PNG, WebP), crop ảnh theo polygon mask, dán ảnh đã crop vào canvas, và bo góc panel với border. Pillow được chọn vì API trực quan, hỗ trợ đầy đủ định dạng ảnh phổ biến và tích hợp tốt với NumPy array.
NumPy cung cấp nền tảng tính toán số học hiệu suất cao cho toàn bộ engine hình học. Mọi tọa độ đa giác, ma trận transform và phép tính phân vùng diện tích đều được biểu diễn dưới dạng NumPy array để tận dụng vectorization – nhanh hơn vòng lặp Python thuần từ 10 đến 100 lần.
Shapely là thư viện hình học đa giác chuyên dụng, đóng vai trò kiểm tra viên (validator) trong pipeline tạo layout. Mỗi polygon được sinh ra bởi thuật toán Recursive Splitting đều phải qua kiểm tra Shapely: is_valid(), area > threshold, và convexity check. Nếu polygon không hợp lệ (self-intersecting, degenerate triangle), Shapely phát hiện và trigger fallback ngay lập tức.
OpenCV (cv2) là thư viện Computer Vision xử lý phân tích nội dung ảnh. Cụ thể: Canny Edge Detection xác định mật độ biên (edge density) để đánh giá độ phức tạp cảnh; Laplacian Blur Score đo độ sắc nét ảnh; MSER (Maximally Stable Extremal Regions) phát hiện vùng chữ; Contour Detection tìm bong bóng thoại; và HaarCascade phát hiện khuôn mặt làm fallback.
Ultralytics YOLOv8 là mô hình Deep Learning cốt lõi cho Person Detection. YOLOv8 được chọn vì cân bằng tốt giữa tốc độ inference (~30ms/ảnh trên CPU) và độ chính xác, đặc biệt với class 'person'. Kết quả bounding box từ YOLO được đưa vào Smart Crop module để tính focal point, đảm bảo nhân vật luôn nằm trong vùng hiển thị sau khi crop.
Axios là thư viện HTTP client phía Frontend, xử lý toàn bộ giao tiếp với Backend API: upload ảnh multipart/form-data, gửi cấu hình JSON, nhận và hiển thị preview trang truyện. Axios được chọn vì hỗ trợ interceptors tiện lợi cho xử lý lỗi toàn cục và progress tracking khi upload file lớn.
 
CHƯƠNG 3  
NGHIÊN CỨU YÊU CẦU ĐỀ TÀI
3.1 Mô tả các yêu cầu đề tài
Hệ thống ComicCraft AI được xây dựng để giải quyết bài toán tự động hóa quy trình sắp trang truyện tranh – một công việc đòi hỏi cả kỹ năng thiết kế đồ họa lẫn kiến thức về ngôn ngữ hình ảnh truyện tranh. Hệ thống cần đáp ứng bốn nhóm yêu cầu chức năng chính.
Nhóm yêu cầu thứ nhất là tiếp nhận và xử lý ảnh đầu vào: hệ thống phải chấp nhận upload hàng chục đến hàng trăm ảnh cùng lúc (JPEG, PNG, WebP) với kích thước đa dạng; tự động nhận diện orientation (dọc/ngang/vuông) của từng ảnh; và phân tích nội dung từng ảnh bằng AI để trích xuất các đặc trưng layout quan trọng (bounding boxes nhân vật, vùng chữ, bong bóng thoại, độ sắc nét).
Nhóm yêu cầu thứ hai là tạo layout tự động thông minh: hệ thống cần hỗ trợ hai chế độ layout – Simple Mode (lưới cổ điển, ổn định) và Advanced Mode (khung nghiêng ngẫu nhiên, sáng tạo). Layout phải tôn trọng Aspect Ratio của ảnh gốc thay vì chia đều 50/50; cần xử lý được hiện tượng Orphan Panel (ảnh lẻ loi cuối bộ); và không bao giờ trả về lỗi 500 với người dùng nhờ cơ chế Fallback.
Nhóm yêu cầu thứ ba là Smart Crop: khi ảnh gốc có tỷ lệ khác với khung được cấp, hệ thống phải crop thông minh để giữ lại phần quan trọng nhất (mặt nhân vật, vùng chữ, điểm tập trung của cảnh) thay vì crop mù quáng từ giữa hay góc trái. Độ chính xác của Smart Crop ảnh hưởng trực tiếp đến chất lượng cảm quan của trang truyện cuối cùng.
Nhóm yêu cầu thứ tư là xuất sản phẩm: người dùng cần có khả năng xem trước từng trang truyện đã tạo; tải xuống từng trang (PNG), toàn bộ bộ truyện (ZIP), hoặc xuất dưới dạng PDF nguyên bộ có thể tùy biến ảnh bìa. Toàn bộ quy trình từ upload đến xuất file phải hoàn thành trong thời gian hợp lý, không gây ra trải nghiệm chờ đợi khó chịu cho người dùng.
3.2 Mô tả các thành phần và thuật toán lõi
Hệ thống được xây dựng theo kiến trúc phân tầng với bốn thuật toán lõi độc lập nhưng phối hợp chặt chẽ với nhau trong pipeline xử lý.
a) AR-Driven Area Allocation (Phân bổ diện tích theo tỷ lệ):
Đây là thuật toán giải quyết bài toán cơ bản nhất: phân bổ không gian hợp lý cho từng ảnh trong một hàng. Thay vì chia đều (50/50, 33/33/33), mỗi ảnh nhận được không gian tỷ lệ thuận với Aspect Ratio của nó: width_weight = AR_i / Σ(AR_j). Kết quả là ảnh ngang (AR > 1.25) được cấp khung rộng và ảnh dọc (AR < 0.8) được cấp khung hẹp đứng – bảo toàn ngữ nghĩa trực quan. Thuật toán còn phân nhóm ảnh thành ba loại (Landscape/Portrait/Square) và áp dụng trọng số AR động để tránh hiện tượng bóp méo ảnh khi ghép chung một hàng.
b) Vertical Dynamic Padding (Đệm dọc động):
Thuật toán này giải quyết vấn đề kéo giãn dọc (Stretch Deforming) – hiện tượng xảy ra khi số lượng ảnh quá ít so với chiều cao khổ giấy. Hệ thống tính Ideal Usable Height dựa trên nghịch đảo tổng AR: H_ideal = k × (1.0 / (cols × avg_AR)). Nếu chiều cao giấy lớn hơn 115% H_ideal, thuật toán DỪNG giãn căng và thêm vertical_padding = (H_giấy - H_ideal) / 2 để canh giữa khối ảnh, tạo ra trang truyện đẹp ngay cả khi số lượng ảnh không đủ lấp đầy trang.
c) AI Context & OCR Aspect Boosting:
Đây là thành phần AI can thiệp bố cục thông minh nhất của hệ thống. YOLOv8 và OpenCV quét từng ảnh đầu vào, đếm text_count (số vùng chữ) và bubble_count (số bong bóng thoại), từ đó tính importance_score theo công thức: score = text_count × 3.0 + bubble_count × 2.5 + person_count × 2.0. Quan trọng hơn, tính năng OCR Aspect Boosting "bơm phồng" AR nguyên bản của ảnh chứa nhiều chữ thêm từ +10% đến +40%. Điều này "đánh lừa" engine phân bổ diện tích để tự động cấp thêm không gian rộng cho panel đó, đảm bảo chữ thoại không bị crop khi fit vào khung truyện.
d) Recursive Polygon Splitting (Cắt đa giác đệ quy – Advanced Mode):
Thuật toán này tạo ra các khung truyện nghiêng đặc trưng của phong cách comic chuyên nghiệp. Toàn bộ trang giấy được coi là một tứ giác lồi ban đầu (tọa độ 4 góc). Hàm split() đệ quy phân tách tứ giác bằng các đường cắt nghiêng: y_left ≠ y_right với độ Jitter ngẫu nhiên trong khoảng [-jitter, +jitter]. Shapely Validation kiểm tra mỗi polygon con sau khi cắt: nếu is_valid() = False hoặc area < min_threshold, thuật toán rollback nhánh đó và thực hiện đường cắt thẳng thay thế. Cơ chế Fallback Layout (comic_layout_simple.py) đảm bảo khi toàn bộ Advanced Mode thất bại, hệ thống vẫn trả về Grid Layout hợp lệ thay vì lỗi 500.
 
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
Hệ thống được triển khai theo kiến trúc Client-Server hai tầng rõ ràng. Frontend React chạy tại port 5173 giao tiếp với Backend FastAPI tại port 60074 thông qua RESTful API (Axios HTTP). Backend được tổ chức theo Service Repository Pattern với ba tầng: Router (nhận request, validate data), Service (business logic – 4 thuật toán lõi), và Utility (hàm dùng chung). Toàn bộ file ảnh upload được lưu tại /uploads và kết quả render lưu tại /outputs trên server. Tích hợp MySQL giúp lưu trữ thông tin tài khoản người dùng, lịch sử phiên tạo truyện và metadata phục vụ tính năng quản lý dự án (My Projects).
 
[Hình 4.8: Kiến trúc tổng thể hệ thống (Backend + Frontend)]
Giao diện Quản lý Dự án (Dự Án Của Tôi):
Giao diện Quản lý Dự án cho phép người dùng quản lý tập trung và chi tiết toàn bộ các bộ truyện tranh đã được thiết lập hoặc kết xuất trên hệ thống. Các tính năng và thông tin hiển thị bao gồm: (1) Lưới danh sách dự án (Projects Grid) hiển thị từng project dưới dạng thẻ (Card) trực quan chứa ảnh thumbnail đại diện (hoặc icon tài liệu nếu chưa ghép ảnh), mã định danh dự án (Session ID), số lượng trang (ví dụ: 6 trang, 2 trang), dung lượng lưu trữ (MB) và thời gian khởi tạo chi tiết; (2) Hệ thống tương tác cho phép người dùng thực hiện nhanh 3 hành động trực tiếp trên từng dự án: Xem (quay lại phiên làm việc để chỉnh sửa hoặc xem chi tiết), Tải (tải gói nén ZIP/PDF của dự án) và Xóa (gửi yêu cầu xóa dữ liệu trên hệ thống); (3) Bảng thống kê tóm tắt ở chân trang (Projects Stats) hiển thị tổng số dự án hiện có, tổng số trang truyện và tổng dung lượng lưu trữ tài nguyên trên Cloud, giúp người dùng dễ dàng kiểm soát dung lượng sử dụng.
 
[Hình 4.9: Giao diện Quản lý Dự án]
CHƯƠNG 5  
KẾT QUẢ ĐẠT ĐƯỢC QUA ĐỢT THỰC TẬP
Sau quá trình thực tập, em đã đạt được sự phát triển đáng kể về kiến thức chuyên môn và năng lực kỹ thuật trong nhiều lĩnh vực quan trọng.
Về kiến thức lý thuyết được củng cố và bổ sung: Việc làm chủ Python 3.10 với các tính năng tiên tiến như pattern matching, asyncio cải tiến và NumPy vectorization đã tạo nền tảng vững chắc cho việc triển khai các thuật toán tính toán phức tạp. Kiến thức về hình học giải tích máy tính – từ đa giác lồi, kiểm tra self-intersection đến thuật toán polygon clipping – là những kiến thức hoàn toàn mới mà em phải tự nghiên cứu trong quá trình thực hiện dự án. Ngoài ra, em đã hiểu sâu hơn về cơ chế hoạt động của mô hình YOLO: từ kiến trúc mạng, quá trình inference đến kỹ thuật Non-Maximum Suppression (NMS) và cách đọc bounding box output.
Về kỹ năng thực hành học hỏi được: Em đã rèn luyện được kỹ năng thiết kế và xây dựng hệ thống Web Full-stack hoàn chỉnh – từ việc thiết kế API contract, xử lý file upload đa luồng đến tối ưu response time cho các endpoint xử lý ảnh phức tạp. Kỹ năng Debug nâng cao được cải thiện đáng kể khi làm việc với các thư viện phức tạp như Shapely, OpenCV và YOLO đòi hỏi khả năng đọc stack trace, profiling code và viết unit test hiệu quả. Đặc biệt, kỹ năng tối ưu hóa thuật toán – áp dụng caching kết quả AI inference và NumPy vectorization thay vì vòng lặp Python thuần – giúp giảm thời gian xử lý mỗi trang truyện từ ~8 giây xuống còn ~2 giây.
Về kinh nghiệm thực tiễn tích lũy được: Em học được cách quản lý thời gian và ưu tiên công việc trong môi trường có nhiều task song song và yêu cầu thay đổi liên tục. Kinh nghiệm làm việc với Git theo workflow feature branch, viết commit message chuẩn và xử lý merge conflict trong nhóm là những kỹ năng mềm quan trọng mà chỉ có thể học được qua thực tế. Quan trọng hơn, em học được tư duy problem-solving kỹ sư: khi gặp vấn đề không có sẵn giải pháp trên internet (như Orphan Panel hay Stretch Deforming), em phải tự phân tích root cause, đề xuất và thử nghiệm nhiều phương án trước khi chọn giải pháp tối ưu.
Thành quả nổi bật nhất là việc phát triển thành công hệ thống ComicCraft AI với các đóng góp cụ thể: (1) Module comic_layout_algorithms.py – toàn bộ engine hình học đa giác cho Advanced Mode do em phát triển từ đầu; (2) Smart Crop module (smart_crop.py) với thuật toán Bounding Box Merge + IOU Weighting; (3) Tính năng OCR Aspect Boosting do em đề xuất và cài đặt sau khi nhận thấy vấn đề panel text bị crop; (4) Cơ chế Fallback Layout đảm bảo hệ thống không bao giờ trả lỗi 500 cho người dùng; (5) Hai file tài liệu kỹ thuật chi tiết (README.md và README_BAO_CAO.md) ghi lại đầy đủ kiến trúc và thuật toán hệ thống.
Đánh giá tổng thể, quá trình thực tập đã củng cố các phương pháp làm việc chuyên nghiệp bao gồm quản lý phiên bản mã nguồn, tuân thủ quy trình phát triển phần mềm chuẩn (Agile/Scrum), tài liệu hóa đầy đủ và tối ưu hóa hiệu suất hệ thống. Những kiến thức và kinh nghiệm tích lũy được trong đợt thực tập này là hành trang vô cùng quý giá cho sự nghiệp kỹ sư phần mềm của em sau này.
 
TÀI LIỆU THAM KHẢO
Tiếng Việt:
1. Ngô Hồ Anh Khôi, Trương Hùng Chen và Huỳnh Bá Lộc. (2021). Giáo trình Lập trình Python. NXB Đại học Nam Cần Thơ. 177 trang.
2. Huỳnh Trung Tín. (2023). Xây dựng ứng dụng web với ReactJS và Python FastAPI. NXB Đại học Nam Cần Thơ. 185 trang.
3. Trần Văn Hùng. (2023). Ứng dụng trí tuệ nhân tạo trong nhận dạng và phân tích hình ảnh. NXB Đại học Nam Cần Thơ. 203 trang.
4. Nguyễn Văn Minh. (2022). Python 3.10: Tính năng mới và ứng dụng trong xử lý dữ liệu. Tạp chí Công nghệ thông tin Việt Nam, 15(3), 78–91.
5. Phạm Minh Tuấn và Lê Hoàng Phương. (2024). Hệ thống phát hiện và phân tích nội dung ảnh sử dụng YOLO. Kỷ yếu Hội thảo Công nghệ và Ứng dụng AI, Đại học Nam Cần Thơ, 67–82.
6. MDN Web Docs. (2024). CSS Grid Layout và CSS Flexible Box Layout. Mozilla Developer Network.
Tiếng Anh:
7. Redmon, J., Divvala, S., Girshick, R., & Farhadi, A. (2016). You Only Look Once: Unified, Real-Time Object Detection. Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR), 779–788.
8. Bradski, G., & Kaehler, A. (2008). Learning OpenCV: Computer Vision with the OpenCV Library. O'Reilly Media. 555 pages.
9. Shapely Development Team. (2023). Shapely User Manual – Manipulation and Analysis of Geometric Objects. Retrieved from https://shapely.readthedocs.io
10. Jocher, G. et al. (2023). Ultralytics YOLOv8. GitHub Repository. Retrieved from https://github.com/ultralytics/ultralytics
11. Itti, L., & Koch, C. (2000). A saliency-based search mechanism for overt and covert shifts of visual attention. Vision Research, 40(10–12), 1489–1506.
