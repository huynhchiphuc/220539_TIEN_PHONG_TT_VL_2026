import codecs
import re

content = codecs.open('backend/api_base_public/app/routers/comic.py', 'r', 'utf-8').read().replace('\r\n', '\n')

start_str = "    try:\n        if data.layout_mode == 'simple':"
end_str = "Lỗi khi tạo comic: {str(gen_error)}\")"

start_idx = content.find(start_str)
end_idx = content.find(end_str)

if start_idx != -1 and end_idx != -1:
    end_idx += len(end_str)
    
    new_block = """    try:
        from app.services.comic_service import ComicService
        
        # Gọi Service để xử lý pipeline thay vì viết code logic trong file router
        # Inject json payload từ data model cho service
        service_result = ComicService.generate_comic_pipeline(
            input_folder=input_folder,
            output_folder=output_folder,
            file_json_data=data.model_dump(),
            user_id=user.get('id'),
            session_id=data.session_id
        )
        
        pages = [Path(p) for p in service_result["pages"]]
        
    except MemoryError:
        raise HTTPException(status_code=500, detail="Không đủ bộ nhớ. Thử giảm số ảnh hoặc DPI")
    except Exception as gen_error:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo comic: {str(gen_error)}")"""
        
    new_content = content[:start_idx] + new_block + content[end_idx:]
    with codecs.open('backend/api_base_public/app/routers/comic.py', 'w', 'utf-8') as f:
        f.write(new_content)
    print("Refactored router successfully")
else:
    print("Could not find block", start_idx, end_idx)