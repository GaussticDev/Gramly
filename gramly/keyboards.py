from gramly.utils import _CB_LIMIT

class _UserRequest(dict):
    pass

class _ChatRequest(dict):
    pass

class _ManagedBotRequest(dict):
    pass

def userRequest(
    requestId: int, *,
    isBot: bool = None,
    isPremium: bool = None,
    maxQuantity: int = None,
    requestName: bool = None,
    requestUsername: bool = None,
    requestPhoto: bool = None,
) -> _UserRequest:
    fields = (("is_bot", isBot), ("is_premium", isPremium), ("max_quantity", maxQuantity), ("request_name", requestName), ("request_username", requestUsername), ("request_photo", requestPhoto))
    return _UserRequest({"request_id": requestId, **{k: v for k, v in fields if v is not None}})

def chatRequest(
    requestId: int,
    chatIsChannel: bool, *,
    chatIsForum: bool = None,
    chatHasUsername: bool = None,
    chatIsCreated: bool = None,
    userAdministratorRights: dict = None,
    botAdministratorRights: dict = None,
    botIsMember: bool = None,
    requestTitle: bool = None,
    requestUsername: bool = None,
    requestPhoto: bool = None,
) -> _ChatRequest:
    fields = (("chat_is_forum", chatIsForum), ("chat_has_username", chatHasUsername), ("chat_is_created", chatIsCreated), ("user_administrator_rights", userAdministratorRights), ("bot_administrator_rights", botAdministratorRights), ("bot_is_member", botIsMember), ("request_title", requestTitle), ("request_username", requestUsername), ("request_photo", requestPhoto))
    return _ChatRequest({"request_id": requestId, "chat_is_channel": chatIsChannel, **{k: v for k, v in fields if v is not None}})

def managedBotRequest(
    requestId: int, *,
    suggestedName: str = None,
    suggestedUsername: str = None,
) -> _ManagedBotRequest:
    fields = (("suggested_name", suggestedName), ("suggested_username", suggestedUsername))
    return _ManagedBotRequest({"request_id": requestId, **{k: v for k, v in fields if v is not None}})

def btn(
    text: str, action=None, *,
    url: str = None,
    miniApp: str = None,
    loginUrl: dict = None,
    switchInline: str = None,
    switchInlineCurrent: str = None,
    switchInlineChosen: dict = None,
    copyText: str = None,
    pay: bool = False,
    requestPoll: str = None,
    requestContact: bool = False,
    requestLocation: bool = False,
    requestUsers=None,
    requestChat=None,
    requestManagedBot=None,
    style: str = None,
    emoji: str = None,
    disabled: bool = None,
) -> dict:
    kwarg_choices = (
        url, miniApp, loginUrl, switchInline,
        switchInlineCurrent, switchInlineChosen, copyText, pay or None,
        requestPoll, requestContact or None, requestLocation or None,
        requestUsers, requestChat, requestManagedBot,
    )
    total = (1 if action is not None else 0) + sum(x is not None for x in kwarg_choices)

    if total == 0 and not disabled:
        raise ValueError(
            f"btn('{text}'): no action - pass callback_data string, "
            "userRequest(...), chatRequest(...), managedBotRequest(...), "
            "or a keyword action"
        )
    if total > 1:
        raise ValueError(f"btn('{text}'): exactly one action allowed, got {total}")
    if action is not None and not isinstance(action, (str, _UserRequest, _ChatRequest, _ManagedBotRequest)):
        raise ValueError(f"btn('{text}'): action must be str, userRequest, chatRequest, or managedBotRequest")
    if isinstance(action, str) and len(action.encode()) > _CB_LIMIT:
        raise ValueError(f"callback_data too long: {len(action.encode())} bytes (max {_CB_LIMIT})")

    d = {"text": text}
    if action is not None:
        key = "data" if isinstance(action, str) else ("request_user" if isinstance(action, _UserRequest) else ("request_chat" if isinstance(action, _ChatRequest) else "request_managed_bot"))
        d[key] = action if isinstance(action, str) else dict(action)
    kw_map = (
        ("url", url), ("mini_app", miniApp), ("login_url", loginUrl),
        ("switch_inline", switchInline), ("switch_inline_current", switchInlineCurrent),
        ("switch_inline_chosen", switchInlineChosen), ("copy_text", copyText),
        ("pay", True if pay else None), ("request_poll", requestPoll),
        ("request_contact", True if requestContact else None),
        ("request_location", True if requestLocation else None),
        ("request_user", dict(requestUsers) if isinstance(requestUsers, dict) else requestUsers),
        ("request_chat", dict(requestChat) if isinstance(requestChat, dict) else requestChat),
        ("request_managed_bot", dict(requestManagedBot) if isinstance(requestManagedBot, dict) else requestManagedBot),
        ("style", style), ("emoji", emoji), ("disabled", True if disabled else None),
    )
    d.update((k, v) for k, v in kw_map if v is not None)
    return d

def row(*buttons) -> list:
    return list(buttons)

def kbd(*rows) -> list:
    return list(rows)

def _wireInlineButton(b: dict) -> dict:
    out = {"text": b["text"]}
    if b.get("style"):
        out["style"] = b["style"]
    if b.get("emoji"):
        out["icon_custom_emoji_id"] = b["emoji"]
    if b.get("disabled"):
        out["disabled"] = True

    if "data" in b:
        out["callback_data"] = b["data"]
    elif "url" in b:
        out["url"] = b["url"]
    elif "mini_app" in b:
        out["web_app"] = {"url": b["mini_app"]}
    elif "login_url" in b:
        out["login_url"] = b["login_url"]
    elif "switch_inline" in b:
        out["switch_inline_query"] = b["switch_inline"]
    elif "switch_inline_current" in b:
        out["switch_inline_query_current_chat"] = b["switch_inline_current"]
    elif "switch_inline_chosen" in b:
        out["switch_inline_query_chosen_chat"] = b["switch_inline_chosen"]
    elif "copy_text" in b:
        out["copy_text"] = {"text": b["copy_text"]}
    elif b.get("pay"):
        out["pay"] = True
    elif b.get("disabled"):
        pass
    else:
        raise ValueError(f"Button {b['text']!r} has no valid inline action")
    return out

def buildInlineKeyboard(rows) -> dict:
    if rows is False or rows is None:
        return {}
    if isinstance(rows, dict):
        if "inline_keyboard" in rows:
            return rows
        rows = [[rows]]
    elif isinstance(rows, list):
        if rows and all(isinstance(x, (str, dict)) for x in rows):
            rows = [rows]
    else:
        rows = [list(rows)]

    keyboard = []
    for r in rows:
        if isinstance(r, dict):
            r = [r]
        row_btns = []
        for b in r:
            if isinstance(b, str):
                row_btns.append({"text": b, "callback_data": b})
            elif isinstance(b, dict):
                row_btns.append(_wireInlineButton(b))
        if row_btns:
            keyboard.append(row_btns)
    return {"inline_keyboard": keyboard}

def buildReplyKeyboard(rows, forceReply: bool = None) -> dict:
    if rows is False:
        return {"remove_keyboard": True}
    if isinstance(rows, (str, dict)):
        rows = [[rows]]
    elif isinstance(rows, list) and rows and all(isinstance(x, (str, dict)) for x in rows):
        rows = [rows]

    keyboard = []
    for r in rows:
        if isinstance(r, (str, dict)):
            r = [r]
        row_btns = []
        for b in r:
            if isinstance(b, str):
                row_btns.append({"text": b})
            elif isinstance(b, dict):
                btn_obj = {"text": b["text"]}
                for bk, rk, transform in (
                    ("style", "style", None), ("emoji", "icon_custom_emoji_id", None),
                    ("request_contact", "request_contact", lambda v: True),
                    ("request_location", "request_location", lambda v: True),
                    ("request_poll", "request_poll", lambda v: {"type": v}),
                    ("request_user", "request_users", None),
                    ("request_chat", "request_chat", None),
                    ("request_managed_bot", "request_managed_bot", None),
                    ("mini_app", "web_app", lambda v: {"url": v}),
                ):
                    val = b.get(bk)
                    if val:
                        btn_obj[rk] = transform(val) if transform else val
                row_btns.append(btn_obj)
        if row_btns:
            keyboard.append(row_btns)
    markup = {"keyboard": keyboard, "resize_keyboard": True}
    if forceReply:
        markup["force_reply"] = True
    return markup
