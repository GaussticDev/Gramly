import os
import re
from gramly.errors import TelegramError
from gramly.keyboards import _wireInlineButton
from gramly.utils import _typeFromBytes, _typeFromPath, _log

_MEDIA_META: dict = {
    "photo": ("image/jpeg", "jpg"),
    "video": ("video/mp4", "mp4"),
    "audio": ("audio/mpeg", "mp3"),
    "document": ("application/octet-stream", "bin"),
}

def _compileRuns(parts) -> list:
    if parts is None:
        return []
    if isinstance(parts, str) or (isinstance(parts, dict) and "type" in parts):
        parts = (parts,)
    out = []
    for p in parts:
        if isinstance(p, str):
            out.append(p)
        elif isinstance(p, dict):
            out.append(p)
        elif p is not None:
            out.append(str(p))
    return out

def _asBlocks(parts) -> list:
    if isinstance(parts, dict) and "blocks" in parts:
        return parts["blocks"]
    items = parts if isinstance(parts, (list, tuple)) else (parts,)
    out = []
    for it in items:
        if isinstance(it, dict) and "type" in it:
            out.append(it)
        else:
            out.append({"type": "paragraph", "text": _compileRuns(it)})
    return out

def _resolveMediaSource(item, index: int = 0) -> dict:
    if hasattr(item, "read"):
        item = (item.read(), getattr(item, "name", None))
    if isinstance(item, tuple) and len(item) == 2:
        data, hint = item
        if isinstance(data, (bytes, bytearray)):
            mtype = _typeFromPath(hint) if isinstance(hint, str) and hint else _typeFromBytes(bytes(data))
            ct, ext = _MEDIA_META.get(mtype, _MEDIA_META["document"])
            fname = hint if (isinstance(hint, str) and "." in hint) else f"file{index}.{ext}"
            return {"media": "", "_bytes": bytes(data), "_filename": fname, "_content_type": ct}
        item = data
    if isinstance(item, (bytes, bytearray)):
        mtype = _typeFromBytes(bytes(item))
        ct, ext = _MEDIA_META.get(mtype, _MEDIA_META["document"])
        return {"media": "", "_bytes": bytes(item), "_filename": f"file{index}.{ext}", "_content_type": ct}
    s = str(item)
    if ("/" in s or "\\" in s or s.startswith(".")) and os.path.isfile(s):
        try:
            with open(s, "rb") as f:
                data = f.read()
            fname = os.path.basename(s)
            mtype = _typeFromPath(fname)
            ct, _ = _MEDIA_META.get(mtype, _MEDIA_META["document"])
            return {"media": "", "_bytes": data, "_filename": fname, "_content_type": ct}
        except Exception as e:
            _log.warning("richMedia", file=s, err=e)
    return {"media": s}

def _resolveInputMedia(item, mediaType: str = None, index: int = 0, documentFallback: str = "photo", extensionlessOnly: bool = False, **fields) -> dict:
    resolved = _resolveMediaSource(item, index)
    if mediaType is None:
        if "_bytes" in resolved:
            mediaType = _typeFromBytes(resolved["_bytes"]) if not resolved.get("_filename") else _typeFromPath(resolved["_filename"])
        else:
            hasExtension = "." in str(item).rsplit("/", 1)[-1]
            mediaType = _typeFromPath(str(item))
            if mediaType == "document" and documentFallback and not (extensionlessOnly and hasExtension):
                mediaType = documentFallback
    entry = {"type": mediaType, "media": resolved["media"]}
    if "_bytes" in resolved:
        entry["_bytes"], entry["_filename"], entry["_content_type"] = (
            resolved["_bytes"], resolved["_filename"], resolved["_content_type"]
        )
    entry.update({k: v for k, v in fields.items() if v is not None})
    return entry

def _compileMediaMap(media: dict) -> list:
    if not media:
        return []
    out = []
    for name, item in media.items():
        wrapped = item if isinstance(item, dict) and "type" in item else _resolveInputMedia(item)
        out.append({"id": name, "media": wrapped})
    return out

def _collectRichAttachments(obj):
    files = {}

    def walk(node):
        if isinstance(node, dict):
            if "_bytes" in node:
                key = f"file{len(files)}"
                files[key] = (
                    node.get("_filename", f"{key}.bin"),
                    node["_bytes"],
                    node.get("_content_type", "application/octet-stream"),
                )
                cleaned = {k: v for k, v in node.items() if not k.startswith("_")}
                cleaned["media"] = f"attach://{key}"
                return cleaned
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(obj), files

_RUN_STYLES = ("bold", "italic", "underline", "strike", "spoiler", "mono", "mark", "sub", "sup")
_RUN_STYLE_WIRE = {
    "bold": "bold", "italic": "italic", "underline": "underline", "strike": "strikethrough",
    "spoiler": "spoiler", "mono": "code", "mark": "marked", "sub": "subscript", "sup": "superscript",
}

def run(text: str, style: str = None, *,
    link: str = None,
    mention: int = None,
    username: str = None,
    hashtag: str = None,
    cashtag: str = None,
    botCommand: str = None,
    email: str = None,
    phone: str = None,
    bankCard: str = None,
    date: int = None,
    dateFormat: str = None,
    math: bool = False,
) -> dict:
    kwarg_choices = (link, mention, username, hashtag, cashtag, botCommand, email, phone, bankCard, date, math or None)
    total = (1 if style is not None else 0) + sum(x is not None for x in kwarg_choices)

    if total == 0:
        return text
    if total > 1:
        raise ValueError(
            f"run({text!r}): exactly one of style/link/mention/username/hashtag/"
            f"cashtag/botCommand/email/phone/bankCard/date/math allowed, got {total}"
        )
    if style is not None:
        if style not in _RUN_STYLES:
            raise ValueError(f"run({text!r}): style must be one of {_RUN_STYLES}, got {style!r}")
        return {"type": _RUN_STYLE_WIRE[style], "text": [text]}
    if link is not None:
        return {"type": "url", "text": [text], "url": link}
    if mention is not None:
        return {"type": "text_mention", "text": [text], "user": {"id": mention}}
    if username is not None:
        return {"type": "mention", "text": [text], "username": username.lstrip("@")}
    if hashtag is not None:
        return {"type": "hashtag", "text": [text], "hashtag": hashtag if hashtag.startswith("#") else f"#{hashtag}"}
    if cashtag is not None:
        return {"type": "cashtag", "text": [text], "cashtag": cashtag if cashtag.startswith("$") else f"${cashtag}"}
    if botCommand is not None:
        return {"type": "bot_command", "text": [text], "bot_command": botCommand if botCommand.startswith("/") else f"/{botCommand}"}
    if email is not None:
        return {"type": "email_address", "text": [text], "email_address": email}
    if phone is not None:
        return {"type": "phone_number", "text": [text], "phone_number": phone}
    if bankCard is not None:
        return {"type": "bank_card_number", "text": [text], "bank_card_number": bankCard}
    if date is not None:
        return {"type": "date_time", "unix_time": date, "date_time_format": dateFormat}
    if math:
        return {"type": "mathematical_expression", "text": [text]}

def emojiRun(customEmojiId: str, alt: str = "🙂") -> dict:
    return {"type": "custom_emoji", "custom_emoji_id": customEmojiId, "alternative_text": alt}

def buttonRun(button: dict) -> dict:
    wired = _wireInlineButton(button)
    if wired is None:
        raise ValueError(f"buttonRun(): expected a btn(...) object, got {type(button).__name__!r}")
    return {"type": "button", "button": wired}

def anchor(name: str) -> dict:
    return {"type": "anchor", "name": name}

def anchorLink(text: str, name: str) -> dict:
    return {"type": "anchor_link", "text": [text], "anchor_name": name}

def ref(name: str) -> dict:
    return {"type": "reference", "name": name}

def refLink(text: str, name: str) -> dict:
    return {"type": "reference_link", "text": [text], "reference_name": name}

def heading(*parts, size: int = 1) -> dict:
    return {"type": "heading", "text": _compileRuns(parts), "size": max(1, min(size, 6))}

def paragraph(*parts) -> dict:
    return {"type": "paragraph", "text": _compileRuns(parts)}

def footer(*parts) -> dict:
    return {"type": "footer", "text": _compileRuns(parts)}

def quote(*parts, credit=None) -> dict:
    d = {"type": "blockquote", "blocks": _asBlocks(parts)}
    if credit:
        d["credit"] = _compileRuns(credit)
    return d

def expandableQuote(*parts, credit=None, expanded: bool = False) -> dict:
    d = {"type": "expandable_blockquote", "text": _compileRuns(parts)}
    if credit:
        d["credit"] = _compileRuns(credit)
    if expanded:
        d["is_expanded"] = True
    return d

def pullQuote(*parts, credit=None) -> dict:
    d = {"type": "pullquote", "text": _compileRuns(parts)}
    if credit:
        d["credit"] = _compileRuns(credit)
    return d

def item(*parts, checkbox: bool = None, checked: bool = None,
         value: int = None, labelType: str = None, children: list = None) -> dict:
    blocks = list(_asBlocks(parts))
    if children:
        blocks.append({"type": "list", "items": [
            c if isinstance(c, dict) and "blocks" in c else item(c) for c in children
        ]})
    d = {"blocks": blocks}
    if checkbox or checked:
        d["has_checkbox"] = True
    if checked:
        d["is_checked"] = True
    if value is not None:
        d["value"] = value
    if labelType is not None:
        d["type"] = labelType
    return d

def bulletList(*items) -> dict:
    compiled = [it if isinstance(it, dict) and "blocks" in it else item(it) for it in items]
    return {"type": "list", "items": compiled}

def codeBlock(text: str, language: str = None) -> dict:
    d = {"type": "pre", "text": _compileRuns(text)}
    if language:
        d["language"] = language
    return d

def mathBlock(expression: str) -> dict:
    return {"type": "mathematical_expression", "expression": expression}

def divider() -> dict:
    return {"type": "divider"}

def buttonsBlock(*buttons, align: str = None) -> dict:
    flat = []
    def _collect(item):
        if isinstance(item, list):
            for sub in item:
                _collect(sub)
        elif item is not None:
            flat.append(item)
    for b in buttons:
        _collect(b)
    wired = [b for b in (_wireInlineButton(item) for item in flat) if b is not None]
    d = {"type": "buttons", "buttons": wired}
    if align is not None:
        if align not in ("left", "center", "right"):
            raise ValueError(f"buttonsBlock(): align must be left/center/right, got {align!r}")
        d["align"] = align
    return d

def thinking(*parts) -> dict:
    return {"type": "thinking", "text": _compileRuns(parts)}

def details(summary, *parts, open: bool = False) -> dict:
    summaryParts = summary if isinstance(summary, (list, tuple)) else (summary,)
    d = {"type": "details", "summary": _compileRuns(summaryParts), "blocks": _asBlocks(parts)}
    if open:
        d["is_open"] = True
    return d

def table(rows: list, headerRow: bool = True, bordered: bool = None,
          striped: bool = None, compact: bool = None, caption=None) -> dict:
    def cell(c, isHeaderRow: bool):
        if isinstance(c, dict):
            d = {"align": c.get("align", "left"), "valign": c.get("valign", "middle")}
            if "text" in c and c["text"] is not None:
                d["text"] = _compileRuns(c["text"])
            if c.get("header", isHeaderRow):
                d["is_header"] = True
            if c.get("colspan"):
                d["colspan"] = c["colspan"]
            if c.get("rowspan"):
                d["rowspan"] = c["rowspan"]
            return d
        parts = c if isinstance(c, (list, tuple)) else (c,)
        d = {"text": _compileRuns(parts), "align": "left", "valign": "middle"}
        if isHeaderRow:
            d["is_header"] = True
        return d

    cells = [[cell(c, headerRow and i == 0) for c in r] for i, r in enumerate(rows)]
    d = {"type": "table", "cells": cells}
    if bordered is not None:
        d["is_bordered"] = bordered
    if striped is not None:
        d["is_striped"] = striped
    if compact is not None:
        d["is_compact"] = compact
    if caption:
        d["caption"] = _compileRuns(caption)
    return d

def _caption(caption, credit=None) -> dict | None:
    if caption is None and credit is None:
        return None
    d = {"text": _compileRuns(caption) if caption else []}
    if credit is not None:
        d["credit"] = _compileRuns(credit)
    return d

def mapBlock(latitude: float, longitude: float, zoom: int = 15,
             width: int = 400, height: int = 300, caption=None, credit=None) -> dict:
    d = {
        "type": "map",
        "location": {"latitude": latitude, "longitude": longitude},
        "zoom": max(0, min(zoom, 24)), "width": width, "height": height,
    }
    cap = _caption(caption, credit)
    if cap:
        d["caption"] = cap
    return d

def _mediaBlockOf(wireType: str, blockKey: str, media, caption=None, credit=None,
                   index: int = 0, spoiler: bool = None, **mediaFields) -> dict:
    resolved = _resolveInputMedia(media, wireType, index, has_spoiler=spoiler or None, **mediaFields)
    d = {"type": wireType, blockKey: resolved}
    cap = _caption(caption, credit)
    if cap:
        d["caption"] = cap
    return d

def photo(media, caption=None, credit=None, spoiler: bool = False) -> dict:
    return _mediaBlockOf("photo", "photo", media, caption, credit, spoiler=spoiler)

def video(media, caption=None, credit=None, spoiler: bool = False, **kwargs) -> dict:
    return _mediaBlockOf("video", "video", media, caption, credit, spoiler=spoiler, **kwargs)

def animation(media, caption=None, credit=None, spoiler: bool = False, **kwargs) -> dict:
    return _mediaBlockOf("animation", "animation", media, caption, credit, spoiler=spoiler, **kwargs)

def audio(media, caption=None, credit=None, title: str = None, performer: str = None) -> dict:
    return _mediaBlockOf("audio", "audio", media, caption, credit, title=title, performer=performer)

def voiceNote(media, caption=None, credit=None, duration: int = None) -> dict:
    return _mediaBlockOf("voice_note", "voice_note", media, caption, credit, duration=duration)

def document(media, caption=None, credit=None, fileName: str = None) -> dict:
    return _mediaBlockOf("document", "document", media, caption, credit, file_name=fileName)

def _mediaGroup(kind: str, items: list, caption=None, credit=None) -> dict:
    blocks = []
    for i, it in enumerate(items):
        if isinstance(it, dict) and "type" in it:
            blocks.append(it)
        else:
            blocks.append(_mediaBlockOf("photo", "photo", it, index=i))
    d = {"type": kind, "blocks": blocks}
    cap = _caption(caption, credit)
    if cap:
        d["caption"] = cap
    return d

def collage(items: list, caption=None, credit=None) -> dict:
    return _mediaGroup("collage", items, caption, credit)

def slideshow(items: list, caption=None, credit=None) -> dict:
    return _mediaGroup("slideshow", items, caption, credit)

def _hasThinking(blocks: list) -> bool:
    return any(b.get("type") == "thinking" for b in blocks)

def rich(*blocks, forDraft: bool = False) -> dict:
    compiled = [dict(b) for b in blocks]
    if not forDraft and _hasThinking(compiled):
        raise TelegramError(
            "rich(): a thinking(...) block was found, but it's only accepted by "
            "bot.messageDraft(...) — pass rich(..., forDraft=True) if this is going "
            "to a draft, or drop thinking(...) to send it normally."
        )
    return {"blocks": compiled}

def richMarkdown(text: str, media: dict = None, rtl: bool = None, skipEntityDetection: bool = None) -> dict:
    out = {"markdown": text}
    if media:
        out["media"] = _compileMediaMap(media)
    if rtl is not None:
        out["is_rtl"] = rtl
    if skipEntityDetection is not None:
        out["skip_entity_detection"] = skipEntityDetection
    return out

def richHtml(text: str, media: dict = None, rtl: bool = None, skipEntityDetection: bool = None) -> dict:
    out = {"html": text}
    if media:
        out["media"] = _compileMediaMap(media)
    if rtl is not None:
        out["is_rtl"] = rtl
    if skipEntityDetection is not None:
        out["skip_entity_detection"] = skipEntityDetection
    return out

_SLOT_PATTERN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

def _slotNames(node, order: list) -> None:
    if isinstance(node, str):
        for m in _SLOT_PATTERN.finditer(node):
            name = m.group(1)
            if name not in order:
                order.append(name)
    elif isinstance(node, dict):
        for v in node.values():
            _slotNames(v, order)
    elif isinstance(node, (list, tuple)):
        for v in node:
            _slotNames(v, order)

def _fillSlots(node, data: dict):
    if isinstance(node, str):
        def _sub(m: "re.Match") -> str:
            name = m.group(1)
            if name not in data:
                raise KeyError(f"missing value for slot '{{{name}}}'")
            return str(data[name])
        return _SLOT_PATTERN.sub(_sub, node)
    if isinstance(node, dict):
        return {k: _fillSlots(v, data) for k, v in node.items()}
    if isinstance(node, (list, tuple)):
        return [_fillSlots(v, data) for v in node]
    return node

class RichTemplate:
    __slots__ = ("_blocks", "_forDraft", "_slotOrder")

    def __init__(self, blocks: tuple, forDraft: bool):
        self._blocks = blocks
        self._forDraft = forDraft
        order: list = []
        for b in blocks:
            _slotNames(b, order)
        self._slotOrder = tuple(order)

    def __call__(self, *args, **kwargs) -> dict:
        if len(args) > len(self._slotOrder):
            raise ValueError(
                f"template takes {len(self._slotOrder)} positional slot(s) "
                f"{self._slotOrder}, got {len(args)}"
            )
        data = dict(zip(self._slotOrder, args))
        for name, value in kwargs.items():
            if name in data:
                raise ValueError(f"slot '{name}' passed both positionally and by name")
            data[name] = value
        filled = [_fillSlots(b, data) for b in self._blocks]
        return rich(*filled, forDraft=self._forDraft)

    @property
    def slots(self) -> tuple:
        return self._slotOrder

    def __repr__(self) -> str:
        return f"RichTemplate(slots={self._slotOrder!r})"

class Rich:
    __slots__ = ()

    def __new__(cls, *blocks, forDraft=False):
        order: list = []
        for b in blocks:
            _slotNames(b, order)
        if order:
            return RichTemplate(blocks, forDraft)
        return rich(*blocks, forDraft=forDraft)

    Build = staticmethod(rich)
    Heading = staticmethod(heading)
    Paragraph = staticmethod(paragraph)
    Footer = staticmethod(footer)
    Quote = staticmethod(quote)
    ExpandableQuote = staticmethod(expandableQuote)
    PullQuote = staticmethod(pullQuote)
    Item = staticmethod(item)
    BulletList = staticmethod(bulletList)
    CodeBlock = staticmethod(codeBlock)
    MathBlock = staticmethod(mathBlock)
    Anchor = staticmethod(anchor)
    Divider = staticmethod(divider)
    Thinking = staticmethod(thinking)
    Details = staticmethod(details)
    Table = staticmethod(table)
    Map = staticmethod(mapBlock)
    Run = staticmethod(run)
    EmojiRun = staticmethod(emojiRun)
    ButtonRun = staticmethod(buttonRun)
    Buttons = staticmethod(buttonsBlock)
    AnchorLink = staticmethod(anchorLink)
    Ref = staticmethod(ref)
    RefLink = staticmethod(refLink)
    Markdown = staticmethod(richMarkdown)
    Html = staticmethod(richHtml)
    Photo = staticmethod(photo)
    Video = staticmethod(video)
    Animation = staticmethod(animation)
    Audio = staticmethod(audio)
    Voice = staticmethod(voiceNote)
    Document = staticmethod(document)
    Collage = staticmethod(collage)
    Slideshow = staticmethod(slideshow)
