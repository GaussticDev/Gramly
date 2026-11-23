import asyncio
import logging
import mimetypes
import threading
from collections import OrderedDict

_CB_LIMIT = 64
_API_BASE = "https://api.telegram.org/bot{token}/{method}"
_MAX_RETRIES = 3
_LEVEL_TAG = {
    logging.DEBUG: "Debug",
    logging.INFO: "Info",
    logging.WARNING: "Warning",
    logging.ERROR: "Error",
}

class _Log:
    def __init__(self):
        self._logger = logging.getLogger("gramly")

    def setup(self, debug: bool) -> None:
        self._logger.setLevel(logging.DEBUG if debug else logging.INFO)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S"))
            self._logger.addHandler(handler)
        self._logger.propagate = False

    def _emit(self, level: int, action: str, exc_info=None, **ctx):
        tag = _LEVEL_TAG.get(level, "?")
        parts = " ".join(f"{k}={v}" for k, v in ctx.items() if v is not None)
        line = f"{tag} {action}  {parts}".rstrip() if parts else f"{tag} {action}"
        self._logger.log(level, line, exc_info=exc_info)

    def debug(self, action: str, **ctx):
        self._emit(logging.DEBUG, action, **ctx)

    def info(self, action: str, **ctx):
        self._emit(logging.INFO, action, **ctx)

    def warning(self, action: str, **ctx):
        self._emit(logging.WARNING, action, **ctx)

    def error(self, action: str, exc_info=None, **ctx):
        self._emit(logging.ERROR, action, exc_info=exc_info, **ctx)

_log = _Log()

def setupLogging(debug: bool) -> None:
    _log.setup(debug)

DEFAULT_PERMISSIONS: dict = {
    "can_send_messages": True, "can_send_audios": True, "can_send_documents": True,
    "can_send_photos": True, "can_send_videos": True, "can_send_video_notes": True,
    "can_send_voice_notes": True, "can_send_polls": True, "can_send_other_messages": True,
    "can_add_web_page_previews": True, "can_change_info": True, "can_invite_users": True,
    "can_pin_messages": True, "can_manage_topics": True,
}

def chatId(target) -> int:
    if isinstance(target, bool):
        raise ValueError(f"chat_id must be int, got bool: {target!r}")
    if isinstance(target, int):
        return target
    if isinstance(target, dict):
        if "chat" in target:
            return chatId(target["chat"])
        if "message" in target:
            return chatId(target["message"])
        if "id" not in target or not isinstance(target["id"], int):
            raise ValueError(f"invalid dict id: {target.get('id')!r}")
        return target["id"]
    for attr in ("user_chat_id", "chat_id", "id"):
        val = getattr(target, attr, None)
        if val is not None:
            if isinstance(val, dict):
                return int(val["id"])
            try:
                return int(val)
            except (TypeError, ValueError) as err:
                raise ValueError(f"chat_id is not int-like: {val!r}") from err
    if hasattr(target, "chat"):
        c = target.chat
        return c["id"] if isinstance(c, dict) else c.id
    raise ValueError(f"Cannot extract chat_id from {type(target).__name__}")

def userId(target) -> int | None:
    if isinstance(target, int):
        return target
    if isinstance(target, dict):
        for k in ("from", "user"):
            if target.get(k):
                u = target[k]
                return u.get("id") if isinstance(u, dict) else getattr(u, "id", None)
        value = target.get("id")
        return value if isinstance(value, int) else None
    if hasattr(target, "user_id"):
        return target.user_id
    if hasattr(target, "from_user") and target.from_user:
        fu = target.from_user
        return fu["id"] if isinstance(fu, dict) else fu.id
    if hasattr(target, "id"):
        return target.id
    return None

def toList(value) -> list:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set, frozenset)):
        return list(value)
    return [value]

def isNotModified(error: Exception) -> bool:
    return "message is not modified" in str(error).lower()

_EXT_MIME = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp", "bmp": "image/bmp",
    "mp4": "video/mp4", "mov": "video/quicktime", "avi": "video/x-msvideo", "mkv": "video/x-matroska", "webm": "video/webm",
    "mp3": "audio/mpeg", "ogg": "audio/ogg", "m4a": "audio/mp4", "flac": "audio/flac", "wav": "audio/wav", "opus": "audio/ogg",
    "pdf": "application/pdf", "zip": "application/zip",
}

_EXT_TYPE = {
    "jpg": "photo", "jpeg": "photo", "png": "photo", "gif": "photo", "webp": "photo", "bmp": "photo",
    "mp4": "video", "mov": "video", "avi": "video", "mkv": "video", "webm": "video",
    "mp3": "audio", "ogg": "audio", "m4a": "audio", "flac": "audio", "wav": "audio", "opus": "audio",
}

def mimeType(ext: str) -> str:
    clean = (ext or "").lower().lstrip(".")
    if clean in _EXT_MIME:
        return _EXT_MIME[clean]
    guessed, _ = mimetypes.guess_type(f"file.{clean}" if clean else "")
    return guessed or "application/octet-stream"

def _typeFromPath(path: str) -> str:
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return _EXT_TYPE.get(ext, "document")

def _typeFromBytes(data: bytes) -> str:
    if len(data) < 4:
        return "document"
    header = data[:12]
    if header[:3] == b"\xff\xd8\xff" or header[:4] in (b"\x89PNG", b"GIF8") or (header[:4] == b"RIFF" and data[8:12] == b"WEBP"):
        return "photo"
    if header[:4] in (b"ftyp", b"\x00\x00\x00\x18", b"\x00\x00\x00\x1c", b"\x1a\x45\xdf\xa3") or data[4:8] == b"ftyp":
        return "video"
    if header[:3] == b"ID3" or header[:2] == b"\xff\xfb" or header[:4] in (b"OggS", b"fLaC"):
        return "audio"
    return "document"

class LRUCache(OrderedDict):
    def __init__(self, maxsize: int):
        super().__init__()
        self._maxsize = maxsize

    def __getitem__(self, key):
        self.move_to_end(key)
        return super().__getitem__(key)

    def __setitem__(self, key, value):
        if key in self:
            self.move_to_end(key)
        super().__setitem__(key, value)
        if len(self) > self._maxsize:
            self.popitem(last=False)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

class TimerHandle:
    def __init__(self, stop_evt=None):
        self._stop = stop_evt if stop_evt is not None else threading.Event()

    def stop(self):
        self._stop.set()

    @property
    def stopped(self) -> bool:
        return self._stop.is_set()

def _in_async_task() -> bool:
    try:
        return asyncio.current_task() is not None
    except RuntimeError:
        return False
