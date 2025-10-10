import os
import uuid
from pathlib import Path
from fastapi import HTTPException, UploadFile
from PIL import Image
from config import settings
import magic

UPLOAD_URL = Path(settings.UPLOAD_URL)
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = (1920, 1920)  # Max width/height in pixels

def upload_profile_image(file: UploadFile) -> str:
    """
    Securely upload and process profile image
    Returns: filename of uploaded image
    """
    
    # 1. Validate file exists
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # 2. Check file size
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB")
    
    # 3. Validate file extension
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    try:
        # 4. Read file content
        file_content = file.file.read()
        
        # 5. Validate MIME type using python-magic
        mime_type = magic.from_buffer(file_content, mime=True)
        if mime_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file format. Detected: {mime_type}"
            )
        
        # 6. Validate image using PIL
        try:
            image = Image.open(file.file)
            image.verify()  # Verify it's a valid image
            file.file.seek(0)  # Reset file pointer
            image = Image.open(file.file)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid or corrupted image file")
        
        # 7. Create secure filename
        secure_filename = f"{uuid.uuid4().hex}{file_extension}"
        
        # 8. Ensure upload directory exists
        UPLOAD_URL.mkdir(parents=True, exist_ok=True)
        
        # 9. Resize image if too large
        if image.size[0] > MAX_IMAGE_SIZE[0] or image.size[1] > MAX_IMAGE_SIZE[1]:
            image.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
        
        # 10. Convert to RGB if necessary (for JPEG compatibility)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        
        # 11. Save file
        file_path = UPLOAD_URL / "profile" /  secure_filename
        image.save(file_path, format="JPEG", quality=85, optimize=True)
        
        return secure_filename
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process image: {str(e)}")
    finally:
        file.file.close()


def upload_progress(file: UploadFile) -> str:
    """
    Securely upload and process profile image
    Returns: filename of uploaded image
    """
    
    # 1. Validate file exists
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # 2. Check file size
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB")
    
    # 3. Validate file extension
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    try:
        # 4. Read file content
        file_content = file.file.read()
        
        # 5. Validate MIME type using python-magic
        mime_type = magic.from_buffer(file_content, mime=True)
        if mime_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file format. Detected: {mime_type}"
            )
        
        # 6. Validate image using PIL
        try:
            image = Image.open(file.file)
            image.verify()  # Verify it's a valid image
            file.file.seek(0)  # Reset file pointer
            image = Image.open(file.file)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid or corrupted image file")
        
        # 7. Create secure filename
        secure_filename = f"{uuid.uuid4().hex}{file_extension}"
        
        # 8. Ensure upload directory exists
        UPLOAD_URL.mkdir(parents=True, exist_ok=True)
        
        # 9. Resize image if too large
        if image.size[0] > MAX_IMAGE_SIZE[0] or image.size[1] > MAX_IMAGE_SIZE[1]:
            image.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
        
        # 10. Convert to RGB if necessary (for JPEG compatibility)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        
        # 11. Save file
        file_path = UPLOAD_URL / "progress" /  secure_filename
        image.save(file_path, format="JPEG", quality=85, optimize=True)
        
        return secure_filename
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process image: {str(e)}")
    finally:
        file.file.close()