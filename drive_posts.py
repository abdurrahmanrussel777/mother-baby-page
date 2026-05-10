"""
Google Drive image poster for মা ও শিশুর যত্ন a to z page.
Scans Drive folder → picks random subfolder (topic) + random image → posts to Facebook.
"""
import time
import random
import logging
import requests
import gdown

from config import PAGE_ACCESS_TOKEN, PAGE_ID
from ai import generate_image_post

logger = logging.getLogger(__name__)

DRIVE_FOLDER_URL = "https://drive.google.com/drive/folders/1IKqxm5WAwR7-qAOxN-c2XAqkgMoTl7L0"
GRAPH = "https://graph.facebook.com/v25.0"

_cache: dict = {"folders": {}, "scanned_at": 0}
CACHE_TTL = 3600  # re-scan Drive every hour


def scan_drive() -> dict:
    """Returns {folder_name: [file_id, ...]} — cached for 1 hour."""
    now = time.time()
    if now - _cache["scanned_at"] < CACHE_TTL and _cache["folders"]:
        return _cache["folders"]

    try:
        files = gdown.download_folder(
            url=DRIVE_FOLDER_URL,
            skip_download=True,
            quiet=True,
        )
    except Exception as e:
        logger.error("Drive scan failed: %s", e)
        return _cache["folders"]

    folders: dict = {}
    for f in (files or []):
        parts = f.path.split("/")
        if len(parts) >= 2:
            folder_name = parts[0]
            folders.setdefault(folder_name, []).append(f.id)

    _cache["folders"] = folders
    _cache["scanned_at"] = now
    logger.info(
        "Drive scan: %d folders, %d total images",
        len(folders),
        sum(len(v) for v in folders.values()),
    )
    return folders


def _topic_from_folder(name: str) -> str:
    return name.replace("_", " ").strip()


def _download_image(file_id: str) -> bytes | None:
    url = f"https://drive.google.com/uc?id={file_id}&export=view"
    try:
        resp = requests.get(url, timeout=30, allow_redirects=True)
        content_type = resp.headers.get("content-type", "")
        if resp.ok and "image" in content_type:
            return resp.content
        logger.warning("Drive image fetch bad response: status=%s type=%s", resp.status_code, content_type)
    except Exception as e:
        logger.error("Image download failed (id=%s): %s", file_id, e)
    return None


def _post_image_to_facebook(image_bytes: bytes, caption: str) -> bool:
    try:
        resp = requests.post(
            f"{GRAPH}/{PAGE_ID}/photos",
            data={"message": caption, "access_token": PAGE_ACCESS_TOKEN},
            files={"source": ("image.jpg", image_bytes, "image/jpeg")},
            timeout=60,
        )
        if resp.ok:
            logger.info("Image post published: %s", resp.json().get("id"))
            return True
        logger.error("Image post failed: %s", resp.text)
    except Exception as e:
        logger.error("Facebook image post error: %s", e)
    return False


def do_drive_post() -> bool:
    """Pick random folder + image, generate health caption, post to Facebook."""
    folders = scan_drive()
    if not folders:
        logger.error("No Drive folders found — skipping")
        return False

    folder_name = random.choice(list(folders.keys()))
    file_ids = folders[folder_name]
    if not file_ids:
        logger.warning("Folder '%s' empty — skipping", folder_name)
        return False

    file_id = random.choice(file_ids)
    topic = _topic_from_folder(folder_name)
    logger.info("Drive post: folder='%s' file='%s'", folder_name, file_id)

    image_bytes = _download_image(file_id)
    if not image_bytes:
        return False

    caption = generate_image_post(topic)
    if not caption:
        logger.error("AI returned empty caption for topic '%s'", topic)
        return False

    return _post_image_to_facebook(image_bytes, caption)
