import cloudinary
import cloudinary.uploader
import cloudinary.api
from app.config import settings

# Cáº¥u hÃ¬nh Cloudinary náº¿u cÃ³ thÃ´ng tin
if settings.CLOUDINARY_URL:
    cloudinary.config(
        cloudinary_url=settings.CLOUDINARY_URL
    )
    CLOUDINARY_ENABLED = True
elif settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET
    )
    CLOUDINARY_ENABLED = True
else:
    CLOUDINARY_ENABLED = False


def upload_image(file_path: str, folder: str = "comic_ai_uploads", public_id: str = None) -> dict:
    """
    Upload 1 file áº£nh lÃªn Cloudinary.
    Giá»¯ nguyÃªn format gốc cá»§a áº£nh vÃ  kÃ´ng cáº§n optimize máº¡nh Ä‘á»ƒ giá»¯ rÃµ nÃ©t truyá»‡n tranh.
    
    :param file_path: Ä‘Æ°á»ng dáº«n Ä‘áº¿n file áº£nh hiá»‡n táº¡i trÃªn disk
    :param folder: TÃªn thÆ° má»¥c chá»©a trÃªn Cloudinary (VD: session_id cá»§a users)
    :param public_id: TÃªn file dÆ°á»›i dÃ¡ng ID (tÃ¹y chá»n, máº·c Ä‘á»‹nh cloudinary sáº½ random)
    :return: dictionary chá»©a chuá»—i url vÃ  public_id
    """
    if not CLOUDINARY_ENABLED:
        raise Exception("Cloudinary chÆ°a Ä‘Æ°á»£c cáº¥u hÃ¬nh!")
    
    options = {
        "folder": folder,
        "resource_type": "image",
        "overwrite": True,
        "invalidate": True
    }
    if public_id:
        options["public_id"] = public_id

    response = cloudinary.uploader.upload(file_path, **options)
    
    return {
        "url": response.get("secure_url"),
        "public_id": response.get("public_id"),
        "format": response.get("format"),
        "size": response.get("bytes")
    }


def delete_image(public_id: str) -> bool:
    """
    XÃ³a áº£nh trÃªn Cloudinary dá»±a theo public_id.
    """
    if not CLOUDINARY_ENABLED:
        return False
        
    try:
        res = cloudinary.uploader.destroy(public_id)
        return res.get('result') == 'ok'
    except Exception:
        return False
