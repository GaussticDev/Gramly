from dataclasses import dataclass
from typing import Any

class Obj:
    __slots__ = ("_d",)

    def __init__(self, d: dict):
        self._d = d

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            v = self._d[name]
        except KeyError:
            raise AttributeError(name)
        if isinstance(v, dict):
            return Obj(v)
        if isinstance(v, list):
            return [Obj(i) if isinstance(i, dict) else i for i in v]
        return v

    def __setattr__(self, name, value):
        if name == "_d":
            super().__setattr__(name, value)
        else:
            self._d[name] = value

    def __getitem__(self, key):
        v = self._d[key]
        if isinstance(v, dict):
            return Obj(v)
        if isinstance(v, list):
            return [Obj(i) if isinstance(i, dict) else i for i in v]
        return v

    def __contains__(self, key):
        return key in self._d

    def get(self, key, default=None):
        if key in self._d:
            v = self._d[key]
            if isinstance(v, dict):
                return Obj(v)
            if isinstance(v, list):
                return [Obj(i) if isinstance(i, dict) else i for i in v]
            return v
        return default

    def keys(self):
        return self._d.keys()

    def values(self):
        return self._d.values()

    def items(self):
        return self._d.items()

    def __iter__(self):
        return iter(self._d)

    def __len__(self):
        return len(self._d)

    def __eq__(self, other):
        return self._d == (other._d if isinstance(other, Obj) else other)

    def __bool__(self):
        return bool(self._d)

    def __repr__(self):
        return repr(self._d)

def wrap(v):
    if isinstance(v, dict):
        return Obj({k: wrap(v2) for k, v2 in v.items()})
    if isinstance(v, list):
        return [wrap(i) for i in v]
    return v

def _to_raw(v):
    if isinstance(v, Obj):
        return {k: _to_raw(vv) for k, vv in v._d.items()}
    if isinstance(v, list):
        return [_to_raw(i) for i in v]
    return v

@dataclass
class User:
    id: int
    is_bot: bool = False
    first_name: str = ""
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    is_premium: bool | None = None
    added_to_attachment_menu: bool | None = None
    can_join_groups: bool | None = None
    can_read_all_group_messages: bool | None = None
    supports_inline_queries: bool | None = None
    supports_guest_queries: bool | None = None
    can_connect_to_business: bool | None = None
    has_main_web_app: bool | None = None
    can_manage_bots: bool | None = None

    @classmethod
    def fromDict(cls, d):
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d}) if d else None

@dataclass
class Chat:
    id: int
    type: str = "unknown"
    title: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_forum: bool | None = None
    is_direct_messages: bool | None = None

    @classmethod
    def fromDict(cls, d):
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d}) if d else None

@dataclass
class SuccessfulPayment:
    currency: str
    total_amount: int
    invoice_payload: str
    telegram_payment_charge_id: str
    provider_payment_charge_id: str | None = None
    is_recurring: bool | None = None
    is_first_recurring: bool | None = None
    subscription_expiration_date: int | None = None

    @classmethod
    def fromDict(cls, d):
        return cls(**{k: d[k] for k in cls.__dataclass_fields__ if k in d}) if d else None

class Widget:
    def __init__(self, id: str | None = None, type: str = "custom", url: str | None = None, title: str | None = None, data: Any = None, text: str | None = None, initial_data: Any = None, **kwargs):
        self.id = id
        self.type = type
        self.url = url
        self.title = title
        self.data = data if data is not None else initial_data
        self.text = text
        self.extra = kwargs

    def to_dict(self) -> dict:
        d = {"type": self.type}
        if self.id:
            d["id"] = self.id
        if self.url:
            d["url"] = self.url
        if self.title:
            d["title"] = self.title
        if self.data is not None:
            d["data"] = self.data
        if self.text:
            d["text"] = self.text
        d.update(self.extra)
        return d

    @classmethod
    def fromDict(cls, d):
        return cls(**d) if isinstance(d, dict) else d

class CallbackData:
    __slots__ = ("raw", "parts")

    def __init__(self, data: str):
        self.raw = data
        self.parts = data.split(":") if data else []

    action = property(lambda self: self.parts[0] if self.parts else "")
    args = property(lambda self: self.parts[1:] if len(self.parts) > 1 else [])

    def get(self, index: int, cast=str, default=None):
        try:
            return cast(self.args[index])
        except (IndexError, ValueError, TypeError):
            return default

    def __getitem__(self, index):
        return self.parts[index]

    def __len__(self):
        return len(self.parts)

    def __repr__(self):
        return f"CallbackData({self.raw!r})"

class ArgsMixin:
    def arg(self, index: int, cast=str, default=None):
        try:
            return cast(self.args[index])
        except (IndexError, ValueError, TypeError):
            return default

    def has(self, n: int = 1) -> bool:
        return len(self.args) >= n

    def argInt(self, index: int, default: int = None) -> int | None:
        return self.arg(index, cast=int, default=default)

    def argFloat(self, index: int, default: float = None) -> float | None:
        return self.arg(index, cast=float, default=default)

    def argsFrom(self, index: int = 0, sep: str = " ") -> str:
        return sep.join(self.args[index:])

class RawAttrMixin:
    __slots__ = ()

    def __getattr__(self, name):
        if name.startswith("_") or name not in self._raw:
            raise AttributeError(name)
        v = self._raw[name]
        return wrap(v) if isinstance(v, (dict, list)) else v

class Message(ArgsMixin, RawAttrMixin):
    __slots__ = ("_raw", "args", "match", "from_user", "chat", "text", "message_id", "_gramly")

    def __init__(self, raw: dict, args: list, match=None, gramly=None):
        self._raw = raw
        self.args = args
        self.match = match
        self._gramly = gramly
        self.from_user = User.fromDict(raw.get("from"))
        self.chat = Chat.fromDict(raw.get("chat")) or Chat(id=0, type="unknown")
        self.text = raw.get("text") or raw.get("caption")
        self.message_id = raw.get("message_id")

    userId = property(lambda self: self.from_user.id if self.from_user else None)
    user_id = userId
    chatId = property(lambda self: self.chat.id)
    chat_id = chatId
    chatType = property(lambda self: self.chat.type)
    chat_type = chatType
    messageId = property(lambda self: self.message_id)
    ephemeralId = property(lambda self: self._raw.get("ephemeral_message_id"))
    isEphemeral = property(lambda self: self.ephemeralId is not None)
    receiverUser = property(lambda self: User.fromDict(self._raw.get("receiver_user")))
    isPrivate = property(lambda self: self.chat_type == "private")
    isGroup = property(lambda self: self.chat_type in ("group", "supergroup"))
    isChannel = property(lambda self: self.chat_type == "channel")
    forwardFrom = property(lambda self: User.fromDict(self._raw.get("forward_from")))
    replyTo = property(lambda self: Message(self._raw["reply_to_message"], [], gramly=self._gramly) if self._raw.get("reply_to_message") else None)
    payment = property(lambda self: Payment(SuccessfulPayment.fromDict(self._raw["successful_payment"])) if self._raw.get("successful_payment") else None)
    widget = property(lambda self: Widget.fromDict(self._raw["widget"]) if self._raw.get("widget") else None)
    webAppData = property(lambda self: wrap(self._raw.get("web_app_data")))
    userShared = property(lambda self: wrap(self._raw.get("users_shared") or self._raw.get("user_shared")))
    chatShared = property(lambda self: wrap(self._raw.get("chat_shared")))
    checklist = property(lambda self: wrap(self._raw.get("checklist")))
    checklistTasksAdded = property(lambda self: wrap(self._raw.get("checklist_tasks_added")))
    livePhoto = property(lambda self: wrap(self._raw.get("live_photo")))
    communityChatAdded = property(lambda self: wrap(self._raw.get("community_chat_added")))
    communityChatJoined = property(lambda self: wrap(self._raw.get("community_chat_joined")))
    communityChatRemoved = property(lambda self: wrap(self._raw.get("community_chat_removed")))
    isGuest = property(lambda self: self._raw.get("guest_query_id") is not None)
    guestQueryId = property(lambda self: self._raw.get("guest_query_id"))
    guestCallerUser = property(lambda self: User.fromDict(self._raw.get("guest_bot_caller_user")))
    guestCallerChat = property(lambda self: Chat.fromDict(self._raw.get("guest_bot_caller_chat")))

    def reply(self, text, **kwargs):
        if self._gramly:
            return self._gramly.reply(self, text, **kwargs)
        raise RuntimeError("No Gramly instance attached to Message")

    def delete(self):
        if self._gramly:
            return self._gramly.delete(self.chat_id, self.message_id)
        raise RuntimeError("No Gramly instance attached to Message")

    def __repr__(self) -> str:
        return f"Message({self.message_id}, {self.text!r})"

class CallbackQuery(ArgsMixin, RawAttrMixin):
    __slots__ = ("_raw", "_gramly", "cb", "args", "data", "message", "from_user", "chat", "id", "_answered", "bc_id")

    def __init__(self, raw: dict, cb: CallbackData, args: list = None, gramly=None):
        self._raw, self._gramly = raw, gramly
        self.cb = cb
        self.args = args if args is not None else list(cb.args)
        self.data = raw.get("data")
        self.message = wrap(raw.get("message", {}))
        self.from_user = User.fromDict(raw.get("from"))
        msg = raw.get("message") or {}
        self.chat = Chat.fromDict(msg.get("chat")) if msg.get("chat") else None
        self.id = raw.get("id")
        self.bc_id = msg.get("business_connection_id")
        self._answered = False

    businessConnectionId = property(lambda self: self.bc_id)
    bcId = businessConnectionId
    userId = property(lambda self: self.from_user.id if self.from_user else None)
    user_id = userId
    chatId = property(lambda self: self.chat.id if self.chat else None)
    chat_id = chatId
    messageId = property(lambda self: getattr(self.message, "message_id", None))
    message_id = messageId
    ephemeralId = property(lambda self: getattr(self.message, "ephemeral_message_id", None))
    isEphemeral = property(lambda self: self.ephemeralId is not None)
    isInline = property(lambda self: self._raw.get("inline_message_id") is not None)
    inlineMessageId = property(lambda self: self._raw.get("inline_message_id"))

    def ack(self):
        return self._gramly.ack(self)

    def answer(self, text: str = "", popup: bool = False):
        return self._gramly.alert(self, text=text, popup=popup)

    alert = answer

    def edit(self, text, inline=None, **kwargs):
        return self._gramly.edit(self, text, inline=inline, **kwargs)

    def editMarkup(self, inline=None):
        return self._gramly.editMarkup(self, inline)

    def __repr__(self) -> str:
        return f"CallbackQuery({self.data!r})"

class Payment:
    __slots__ = ("_raw",)

    def __init__(self, raw: SuccessfulPayment):
        self._raw = raw

    currency = property(lambda self: self._raw.currency)
    totalAmount = property(lambda self: self._raw.total_amount)
    stars = property(lambda self: self._raw.total_amount if self._raw.currency == "XTR" else None)
    payload = property(lambda self: self._raw.invoice_payload)
    chargeId = property(lambda self: self._raw.telegram_payment_charge_id)
    providerChargeId = property(lambda self: self._raw.provider_payment_charge_id)
    isRecurring = property(lambda self: bool(self._raw.is_recurring))
    isFirstRecurring = property(lambda self: bool(self._raw.is_first_recurring))
    subscriptionExpiration = property(lambda self: self._raw.subscription_expiration_date)

    def __repr__(self) -> str:
        return f"Payment({self.currency} {self.totalAmount} payload={self.payload!r})"

class PreCheckout:
    __slots__ = ("_raw", "_gramly")

    def __init__(self, raw: dict, gramly):
        self._raw, self._gramly = raw, gramly

    id = property(lambda self: self._raw.get("id"))
    fromUser = property(lambda self: User.fromDict(self._raw.get("from")))
    userId = property(lambda self: self.fromUser.id if self.fromUser else None)
    user_id = userId
    currency = property(lambda self: self._raw.get("currency"))
    totalAmount = property(lambda self: self._raw.get("total_amount"))
    payload = property(lambda self: self._raw.get("invoice_payload"))

    def accept(self):
        return self._gramly._api_call("answerPreCheckoutQuery", pre_checkout_query_id=self.id, ok=True)

    def reject(self, reason: str):
        return self._gramly._api_call("answerPreCheckoutQuery", pre_checkout_query_id=self.id, ok=False, error_message=reason)

    def __repr__(self) -> str:
        return f"PreCheckout({self.currency} {self.totalAmount} payload={self.payload!r})"

class JoinRequest(RawAttrMixin):
    __slots__ = ("_raw",)

    def __init__(self, raw: dict):
        self._raw = raw

    user = property(lambda self: User.fromDict(self._raw.get("from")))
    fromUser = user
    userId = property(lambda self: self.user.id if self.user else None)
    user_id = userId
    chat = property(lambda self: Chat.fromDict(self._raw.get("chat")))
    chatId = property(lambda self: self.chat.id if self.chat else None)
    chat_id = chatId
    userChatId = property(lambda self: int(self._raw.get("user_chat_id")) if self._raw.get("user_chat_id") else None)
    queryId = property(lambda self: self._raw.get("query_id"))
    inviteLink = property(lambda self: wrap(self._raw.get("invite_link")))
    date = property(lambda self: self._raw.get("date"))

    def __repr__(self) -> str:
        return f"JoinRequest(user={self.user_id}, chat={self.chat_id})"

class BusinessConnection(RawAttrMixin):
    __slots__ = ("_raw",)

    def __init__(self, raw: dict):
        self._raw = raw

    id = property(lambda self: self._raw.get("id"))
    user = property(lambda self: User.fromDict(self._raw.get("user")))
    userChatId = property(lambda self: self._raw.get("user_chat_id"))
    date = property(lambda self: self._raw.get("date"))
    isEnabled = property(lambda self: bool(self._raw.get("is_enabled")))
    rights = property(lambda self: wrap(self._raw.get("rights")))
    canReply = property(lambda self: bool(self.rights and self.rights.can_reply))

    def __repr__(self) -> str:
        return f"BusinessConnection(id={self.id!r}, enabled={self.isEnabled})"

class ManagedBot(RawAttrMixin):
    __slots__ = ("_raw", "_gramly")

    def __init__(self, raw: dict, gramly):
        self._raw, self._gramly = raw, gramly

    creator = property(lambda self: User.fromDict(self._raw.get("user")))
    bot = property(lambda self: User.fromDict(self._raw.get("bot")))
    botId = property(lambda self: self.bot.id if self.bot else None)

    def token(self):
        return self._gramly._api_call("getManagedBotToken", user_id=self.botId)

    def replaceToken(self):
        return self._gramly._api_call("replaceManagedBotToken", user_id=self.botId)

    def __repr__(self) -> str:
        return f"ManagedBot(bot=@{self.bot.username if self.bot else None}, id={self.botId})"

class BusinessMessage(ArgsMixin, RawAttrMixin):
    __slots__ = (
        "_raw", "_gramly", "args", "match",
        "bc_id", "chat_id", "message_id", "text", "from_user", "chat",
    )

    def __init__(self, raw: dict, gramly, args: list = None, match=None):
        self._raw, self._gramly = raw, gramly
        self.args = args or []
        self.match = match
        self.bc_id = raw.get("business_connection_id")
        self.text = raw.get("text") or raw.get("caption")
        self.chat = Chat.fromDict(raw.get("chat")) or Chat(id=0, type="unknown")
        self.chat_id = self.chat.id
        self.message_id = raw.get("message_id")
        self.from_user = User.fromDict(raw.get("from"))

    businessConnectionId = property(lambda self: self.bc_id)
    bcId = businessConnectionId
    messageId = property(lambda self: self.message_id)
    chatId = property(lambda self: self.chat_id)
    userId = property(lambda self: self.from_user.id if self.from_user else None)
    user_id = userId
    isPrivate = property(lambda self: self.chat.type == "private")
    isGroup = property(lambda self: self.chat.type in ("group", "supergroup"))
    isChannel = property(lambda self: self.chat.type == "channel")

    def send(self, target, text, inline=None, keyboard=None, photo=None, forceReply: bool = None, **kwargs):
        return self._gramly.send(target, text, inline=inline, keyboard=keyboard, photo=photo, forceReply=forceReply, businessConnectionId=self.bc_id, **kwargs)

    def reply(self, text, inline=None, keyboard=None, **kwargs):
        return self._gramly.reply(self, text, inline=inline, keyboard=keyboard, **kwargs)

    def photo(self, target, photo, caption=None, inline=None, keyboard=None, **kwargs):
        return self._gramly.photo(target, photo, caption=caption, inline=inline, keyboard=keyboard, business_connection_id=self.bc_id, **kwargs)

    def media(self, target, items, caption=None, inline=None, keyboard=None, **kwargs):
        return self._gramly.media(target, items, caption=caption, inline=inline, keyboard=keyboard, business_connection_id=self.bc_id, **kwargs)

    def typing(self, action: str = "typing"):
        return self._gramly.businessAction(self.chat_id, self.bc_id, action)

    def read(self):
        return self._gramly.businessRead(self.chat_id, self.message_id, self.bc_id)

    def delete(self, messageIds: list = None):
        ids = messageIds if messageIds is not None else [self.message_id]
        return self._gramly.delete(self.chat_id, ids, bcId=self.bc_id)

    def pin(self, notify: bool = False):
        return self._gramly.pin(self, notify=notify)

    def unpin(self):
        return self._gramly.unpin(self.chat_id, self.message_id, bcId=self.bc_id)

    def __repr__(self) -> str:
        return f"BusinessMessage(chat={self.chat_id}, bc_id={self.bc_id!r}, text={self.text!r})"

class GuestQuery:
    __slots__ = ("_raw", "_gramly")

    def __init__(self, raw: dict, gramly):
        self._raw, self._gramly = raw, gramly

    id = property(lambda self: self._raw.get("guest_query_id"))
    fromUser = property(lambda self: User.fromDict(self._raw.get("guest_bot_caller_user")))
    fromChat = property(lambda self: Chat.fromDict(self._raw.get("guest_bot_caller_chat")))
    userId = property(lambda self: self.fromUser.id if self.fromUser else None)
    user_id = userId
    text = property(lambda self: self._raw.get("text"))

    def answer(self, text: str, parseMode: str = None, **kwargs):
        return self._gramly._api_call(
            "answerGuestQuery",
            guest_query_id=self.id,
            message={"text": text, "parse_mode": parseMode or self._gramly.parseMode, **kwargs}
        )

    def __repr__(self) -> str:
        return f"GuestQuery(id={self.id!r})"

class InlineQuery:
    __slots__ = ("_raw", "_gramly", "id", "text", "from_user", "offset", "query")

    def __init__(self, raw: dict, gramly):
        self._raw = raw
        self._gramly = gramly
        self.id = raw.get("id")
        self.query = raw.get("query", "")
        self.text = self.query.strip()
        self.from_user = User.fromDict(raw.get("from"))
        self.offset = raw.get("offset", "")

    userId = property(lambda self: self.from_user.id if self.from_user else None)
    user_id = userId

    def article(self, title: str, text: str, description: str = None, thumbUrl: str = None, resultId: str = None, **kwargs) -> dict:
        return {
            "type": "article",
            "id": resultId or title,
            "title": title,
            "description": description,
            "thumbnail_url": thumbUrl,
            "input_message_content": {
                "message_text": text,
                "parse_mode": kwargs.pop("parseMode", None) or self._gramly.parseMode
            },
            **kwargs,
        }

    def answer(self, results: list, cacheTime: int = 30, personal: bool = True):
        return self._gramly.answerInlineQuery(self, results, cacheTime=cacheTime, isPersonal=personal)

    def __repr__(self) -> str:
        return f"InlineQuery({self.id!r}, {self.text!r})"

class WidgetQuery(RawAttrMixin):
    __slots__ = ("_raw", "_gramly")

    def __init__(self, raw: dict, gramly):
        self._raw, self._gramly = raw, gramly

    id = property(lambda self: self._raw.get("id"))
    fromUser = property(lambda self: User.fromDict(self._raw.get("from")))
    userId = property(lambda self: self.fromUser.id if self.fromUser else None)
    user_id = userId
    message = property(lambda self: Message(self._raw["message"], [], gramly=self._gramly) if self._raw.get("message") else None)
    chat = property(lambda self: Chat.fromDict((self._raw.get("message") or {}).get("chat") or self._raw.get("chat")))
    chatId = property(lambda self: self.chat.id if self.chat else None)
    chat_id = chatId
    widgetId = property(lambda self: self._raw.get("widget_id"))
    queryType = property(lambda self: self._raw.get("query_type"))
    data = property(lambda self: wrap(self._raw.get("data")))

    def answer(self, data: Any = None, **kwargs):
        params = {"widget_query_id": self.id}
        if data is not None:
            params["data"] = data
        params.update(kwargs)
        return self._gramly._api_call("answerWidgetQuery", **params)

    def __repr__(self) -> str:
        return f"WidgetQuery(id={self.id!r}, user={self.user_id})"

class SharedWidgetQuery(RawAttrMixin):
    __slots__ = ("_raw", "_gramly")

    def __init__(self, raw: dict, gramly):
        self._raw, self._gramly = raw, gramly

    id = property(lambda self: self._raw.get("id"))
    fromUser = property(lambda self: User.fromDict(self._raw.get("from")))
    userId = property(lambda self: self.fromUser.id if self.fromUser else None)
    user_id = userId
    widgetId = property(lambda self: self._raw.get("widget_id"))
    queryType = property(lambda self: self._raw.get("query_type"))
    data = property(lambda self: wrap(self._raw.get("data")))

    def answer(self, data: Any = None, **kwargs):
        params = {"shared_widget_query_id": self.id}
        if data is not None:
            params["data"] = data
        params.update(kwargs)
        return self._gramly._api_call("answerWidgetQuery", **params)

    def __repr__(self) -> str:
        return f"SharedWidgetQuery(id={self.id!r}, user={self.user_id})"
