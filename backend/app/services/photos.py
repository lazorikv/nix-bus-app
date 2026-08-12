"""Bus photo processing: validation, thumbnailing, and MinIO/S3 upload."""

import io
import uuid

from PIL import Image, UnidentifiedImageError

from app.storage import presigned_get_url, upload_bytes

ALLOWED_CONTENT_TYPES = {"image/jpeg": "jpg", "image/png": "png"}
THUMBNAIL_SIZE = (320, 240)


class InvalidImageError(Exception):
    pass


def _pillow_format(content_type: str) -> str:
    return "JPEG" if content_type == "image/jpeg" else "PNG"


def process_and_upload(content_type: str, data: bytes) -> tuple[str, str]:
    """Validate the image, build a thumbnail, upload both. Returns (photo_key, thumb_key)."""
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise InvalidImageError("Only JPEG and PNG images are allowed")

    try:
        image = Image.open(io.BytesIO(data))
        image.verify()  # detects truncated / non-image payloads
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidImageError("Uploaded file is not a valid image") from exc

    ext = ALLOWED_CONTENT_TYPES[content_type]
    base = f"buses/{uuid.uuid4().hex}"
    photo_key = f"{base}.{ext}"
    thumb_key = f"{base}_thumb.{ext}"

    upload_bytes(photo_key, data, content_type)

    # Re-open (verify() leaves the image unusable) to build the thumbnail.
    thumb: Image.Image = Image.open(io.BytesIO(data))
    if thumb.mode in ("RGBA", "P") and content_type == "image/jpeg":
        thumb = thumb.convert("RGB")
    thumb.thumbnail(THUMBNAIL_SIZE)
    thumb_buffer = io.BytesIO()
    thumb.save(thumb_buffer, format=_pillow_format(content_type))
    upload_bytes(thumb_key, thumb_buffer.getvalue(), content_type)

    return photo_key, thumb_key


def photo_urls(photo_key: str | None, thumb_key: str | None) -> tuple[str | None, str | None]:
    photo_url = presigned_get_url(photo_key) if photo_key else None
    thumb_url = presigned_get_url(thumb_key) if thumb_key else None
    return photo_url, thumb_url
