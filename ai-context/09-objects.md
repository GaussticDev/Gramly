# 09 — Objects, Data Classes, Errors, and Helpers

Handlers receive typed wrappers around Telegram objects. Fields not wrapped in a dedicated
class are exposed dynamically through `Obj`.

## `Message`

Passed to message-level handlers (`onMessage`, `onMedia`, `onPost`, `onEdited`, `onAny`,
`onPayment`, `onWebApp`, and others).

### Properties

| Property | Type | Meaning |
| --- | --- | --- |
| `msg.message_id` / `msg.messageId` | `int` | Message ID |
| `msg.text` | `str \| None` | Text or caption |
| `msg.chat_id` / `msg.chatId` | `int` | Chat ID |
| `msg.chat_type` / `msg.chatType` | `str` | `private`, `group`, `supergroup`, `channel` |
| `msg.user_id` / `msg.userId` | `int \| None` | Sender user ID |
| `msg.from_user` | `User` | Sender |
| `msg.chat` | `Chat` | Chat |
| `msg.isPrivate` | `bool` | Private chat |
| `msg.isGroup` | `bool` | Group or supergroup |
| `msg.isChannel` | `bool` | Channel |
| `msg.args` | `list[str]` | Words after a command / regex capture groups |
| `msg.match` | `re.Match \| None` | Regex match object |
| `msg.replyTo` | `Message \| None` | Message being replied to |
| `msg.forwardFrom` | `User \| None` | Original sender of a forwarded message |
| `msg.payment` | `Payment \| None` | Payment data on a successful payment |
| `msg.webAppData` | `Obj \| None` | Web App payload |
| `msg.userShared` | `Obj \| None` | User shared via a keyboard button |
| `msg.chatShared` | `Obj \| None` | Chat shared via a keyboard button |
| `msg.checklist` | `Obj \| None` | Checklist data |
| `msg.checklistTasksAdded` | `Obj \| None` | Tasks added to a checklist |
| `msg.livePhoto` | `Obj \| None` | Live photo data |
| `msg.communityChatAdded` | `Obj \| None` | Community chat added |
| `msg.communityChatJoined` | `Obj \| None` | Community chat joined |
| `msg.communityChatRemoved` | `Obj \| None` | Community chat removed |
| `msg.isGuest` | `bool` | Guest query message |
| `msg.guestQueryId` | `str \| None` | Guest query ID |
| `msg.guestCallerUser` | `User \| None` | Guest query caller |
| `msg.guestCallerChat` | `Chat \| None` | Guest query chat |
| `msg.ephemeralId` | `int \| None` | Ephemeral message ID |
| `msg.isEphemeral` | `bool` | Ephemeral message |

Any other Telegram field is accessible dynamically: `msg.photo`, `msg.document`,
`msg.voice`, `msg.entities`, `msg.caption_entities`, and so on. Nested dicts come back as
`Obj`.

### Argument helpers (`ArgsMixin`)

```python
msg.arg(0)                        # str or None
msg.arg(0, cast=int, default=0)   # typed with fallback
msg.argInt(0, default=None)       # int shorthand
msg.argFloat(0, default=None)     # float shorthand
msg.has(2)                        # bool: at least 2 args
msg.argsFrom()                    # all args joined with spaces
msg.argsFrom(1)                   # skip the first arg
msg.argsFrom(1, sep=", ")         # custom separator
```

Rules:

- `msg.args` is matcher-dependent: words after a command, the remainder after a prefix, all
  words for `contains`, or regex capture groups for `regex`.
- `msg.has(n)` is the argument-count check. There is no `args_min`.
- `msg.arg(...)` never raises on a missing index; it returns `default`.
- `msg.argInt(...)` returns `None` (or the default) if the value cannot be cast.

## `CallbackQuery`

Passed to `@bot.onCallback`.

| Property | Type | Meaning |
| --- | --- | --- |
| `q.id` | `str` | Callback query ID |
| `q.data` | `str` | Raw callback data |
| `q.cb` | `CallbackData` | Parsed callback data |
| `q.from_user` | `User` | User who pressed |
| `q.user_id` / `q.userId` | `int \| None` | Pressing user ID |
| `q.chat_id` / `q.chatId` | `int \| None` | Chat ID (`None` for inline messages) |
| `q.message_id` / `q.messageId` | `int \| None` | Message ID |
| `q.message` | `Obj` | Full message object |
| `q.isInline` | `bool` | Inline message button |
| `q.inlineMessageId` | `str \| None` | Inline message ID |
| `q.args` | `list[str]` | Parts after the action |
| `q.ephemeralId` | `int \| None` | Ephemeral message ID |
| `q.isEphemeral` | `bool` | Ephemeral message |
| `q.bc_id` / `q.bcId` | `str \| None` | Business connection ID |
| `q.businessConnectionId` | `str \| None` | Alias |

Argument helpers are available: `q.arg()`, `q.argInt()`, `q.argFloat()`, `q.has()`,
`q.argsFrom()`.

### Methods

```python
q.ack()                              # dismiss the spinner, no feedback
q.answer(text="", popup=False)       # alias of alert()
q.alert(text="", popup=False)        # toast or popup
q.edit(text, inline=None, **kwargs)  # edit this message
q.editMarkup(inline=None)            # edit only the keyboard
```

`answer()` and `alert()` are the same call. Gramly auto-acknowledges if the handler returns
without answering.

## `CallbackData`

Parses `callback_data` as `"{action}:{extra1}:{extra2}:..."`.

```python
cb = CallbackData("buy:12345:99:usd")

cb.raw          # "buy:12345:99:usd"
cb.parts        # ["buy", "12345", "99", "usd"]
cb.action       # "buy" (first part)
cb.args         # ("12345", "99", "usd") (everything after action)
cb.get(0)       # "12345"
cb.get(2)       # "99"
cb.get(2, int)  # 99
cb.get(2, int, default=0)
cb[0]           # "buy" (raw parts)
len(cb)         # 4
```

Asymmetry to remember:

- `cb.action`, `cb[0]`, and `len(cb)` operate on raw parts.
- `cb.args` and `cb.get(i)` skip the action.

Recommended convention: `"{action}:{user_id}:{extra...}"`, so `cb.get(0, int)` is the
owner's user ID and `cb.get(1)` is the payload.

## `InlineQuery`

Passed to `@bot.onInline`.

| Property | Type | Meaning |
| --- | --- | --- |
| `q.id` | `str` | Query ID |
| `q.query` | `str` | Raw query |
| `q.text` | `str` | Stripped query |
| `q.from_user` | `User` | Caller |
| `q.user_id` | `int \| None` | Caller ID |
| `q.offset` | `str` | Pagination offset |

Methods: `q.article(...)` and `q.answer(...)`; see
[`08-inline-settings.md`](08-inline-settings.md).

## `JoinRequest`

Passed to `@bot.onJoinRequest`.

| Property | Type | Meaning |
| --- | --- | --- |
| `.user` / `.fromUser` | `User` | Requesting user |
| `.user_id` / `.userId` | `int \| None` | User ID |
| `.chat` | `Chat` | Chat being joined |
| `.chat_id` / `.chatId` | `int` | Chat ID |
| `.userChatId` | `int \| None` | User's private chat ID |
| `.inviteLink` | `Obj \| None` | Invite link used |
| `.date` | `int \| None` | Unix timestamp |
| `.queryId` | `str \| None` | Query ID |

## `BusinessMessage`

Passed to `@bot.onBusinessMessage` and `@bot.onBusinessEdited`. Same text API as `Message`,
plus business fields and methods.

| Property | Type | Meaning |
| --- | --- | --- |
| `msg.bc_id` / `msg.bcId` | `str \| None` | Connection ID |
| `msg.businessConnectionId` | `str \| None` | Alias |
| `msg.text` | `str \| None` | Text or caption |
| `msg.chat_id` / `msg.chatId` | `int` | Chat ID |
| `msg.message_id` / `msg.messageId` | `int \| None` | Message ID |
| `msg.from_user` | `User` | Sender |
| `msg.chat` | `Chat` | Chat |
| `msg.args` | `list[str]` | Arguments / regex groups |
| `msg.match` | `re.Match \| None` | Regex match |

Methods: `reply`, `send`, `photo`, `media`, `typing`, `read`, `delete`, `pin`, `unpin`. See
[`06-business.md`](06-business.md).

## `BusinessConnection`

Passed to `@bot.onBusinessConnection`.

| Property | Type | Meaning |
| --- | --- | --- |
| `.id` | `str` | Connection ID |
| `.user` | `User` | Business account owner |
| `.userChatId` | `int \| None` | Owner's private chat ID |
| `.date` | `int` | Unix timestamp |
| `.isEnabled` | `bool` | Connection active |
| `.canReply` | `bool` | Shorthand for `rights.can_reply` |
| `.rights` | `Obj \| None` | Telegram `BusinessBotRights` fields |

## `GuestQuery`

Passed to `@bot.onGuest`.

| Property | Type | Meaning |
| --- | --- | --- |
| `.id` | `str` | Guest query ID |
| `.fromUser` | `User` | Caller |
| `.fromChat` | `Chat` | Caller chat |
| `.user_id` / `.userId` | `int \| None` | Caller ID |
| `.text` | `str \| None` | Query text |

Method: `q.answer(text, parseMode=None, **kwargs)`.

## Data classes

### `User`

```python
@dataclass
class User:
    id: int
    is_bot: bool
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    is_premium: Optional[bool] = None
    added_to_attachment_menu: Optional[bool] = None
    can_join_groups: Optional[bool] = None
    can_read_all_group_messages: Optional[bool] = None
    supports_inline_queries: Optional[bool] = None
    supports_guest_queries: Optional[bool] = None
    can_connect_to_business: Optional[bool] = None
    has_main_web_app: Optional[bool] = None
    can_manage_bots: Optional[bool] = None
```

### `Chat`

```python
@dataclass
class Chat:
    id: int
    type: str                   # private | group | supergroup | channel
    title: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_forum: Optional[bool] = None
    is_direct_messages: Optional[bool] = None
```

### `SuccessfulPayment`

```python
@dataclass
class SuccessfulPayment:
    currency: str
    total_amount: int
    invoice_payload: str
    telegram_payment_charge_id: str
    provider_payment_charge_id: Optional[str] = None
    is_recurring: Optional[bool] = None
    is_first_recurring: Optional[bool] = None
    subscription_expiration_date: Optional[int] = None
```

### Business rights

`BusinessConnection.rights` returns an `Obj`, not a dedicated class. Its fields mirror
Telegram's `BusinessBotRights` object:

```text
can_reply
can_read_messages
can_delete_sent_messages
can_delete_all_messages
can_edit_name
can_edit_bio
can_edit_profile_photo
can_edit_username
can_change_gift_settings
can_view_gifts_and_stars
can_convert_gifts_to_stars
can_transfer_and_upgrade_gifts
can_transfer_stars
can_manage_stories
```

All are optional booleans. Read them as attributes (`conn.rights.can_reply`) or as keys
(`conn.rights["can_reply"]`). There is no importable `BusinessBotRights` class.

All three data classes (`User`, `Chat`, `SuccessfulPayment`) provide `fromDict(d)`, which
ignores unknown keys:

```python
user = User.fromDict(raw_dict)
```

## `TelegramError`

Raised by API calls on failure.

```python
from gramly import TelegramError

try:
    bot.send(msg, "test")
except TelegramError as e:
    print(e.description)   # human-readable message
    print(e.errorCode)     # Telegram error code (int)
    print(e.retryAfter)    # seconds to wait on HTTP 429, else None
```

Gramly automatically retries requests with `retryAfter` up to three times before raising.
Do not add your own blind retry loop around every call.

## `Obj`

Generic wrapper for Telegram objects that do not have a dedicated class. Supports attribute
access, dict-style access, iteration, and nested wrapping.

```python
msg = Obj({"id": 1, "text": "hi", "from": {"id": 42, "first_name": "Alice"}})

msg.id                 # 1
msg.text               # "hi"
msg["from"]            # Obj({"id": 42, ...})
getattr(msg, "from")   # same
msg["id"]              # 1
"text" in msg          # True
list(msg.keys())       # ["id", "text", "from"]
list(msg.items())      # [("id", 1), ...]
list(msg.values())
len(msg)               # 3
```

Nested dicts become nested `Obj` instances; lists of dicts become lists of `Obj`.

## `TimerHandle`

Returned by `bot.timer(...)`.

```python
handle = bot.timer(60, my_fn)
handle.stop()      # stop the repeating timer
handle.stopped     # bool, True once stopped
```

## Helpers

### `chatId(target) -> int`

Extracts a chat ID from an int, dict, `Message`, `CallbackQuery`, `JoinRequest`, or any
object with `.chat_id` or `.chat.id`.

```python
chatId(12345)
chatId({"id": 12345})
chatId(msg)
```

### `userId(target) -> int | None`

Extracts a user ID from an int, `Message`, `CallbackQuery`, or a dict with `from`, `user`,
or `id`.

```python
userId(msg)
userId(q)
```

### Internal helpers

These are documented for reference but are **not exported from `gramly`**. Import them from
`gramly.gramly` only if you truly need them:

```python
from gramly.gramly import toList, isNotModified, mimeType, matchText, TextRoute
```

```python
toList(None)         # []
toList("start")      # ["start"]
toList(["a", "b"])   # ["a", "b"]

mimeType("jpg")      # "image/jpeg"
mimeType("pdf")      # "application/pdf"
mimeType("xyz")      # "application/octet-stream"
```

`isNotModified(e)` returns `True` for the harmless "message is not modified" edit error:

```python
try:
    bot.edit(q, new_text)
except TelegramError as e:
    if not isNotModified(e):
        raise
```

### `matchText`

Low-level matcher used internally by `onMessage`. Returns `(args, match)` or
`(None, None)`.

```python
matchText(text, commands=None, exact=None, starts=None, ends=None,
          contains=None, regex=None, withSlash=True, withoutSlash=True)

matchText("/start", commands="start")        # ([], None)
matchText("help me", commands="help")        # (["me"], None)
matchText("hello", exact="hello")            # ([], None)
matchText("find something", starts="find")   # (["something"], None)
matchText("50% discount!", contains="discount")  # (["50%", "discount!"], None)
matchText("order #123", regex=r"order #(\d+)")   # (["123"], <re.Match>)
```

### `TextRoute`

Wraps a matching rule and a handler; used by `CommandBlock.textRoutes`.

```python
route = TextRoute(fn, exact="hello")
args, match = route.match("hello world")
```

### Logging

```python
from gramly import setupLogging

setupLogging(debug=True)    # DEBUG level on the "gramly" logger
setupLogging(debug=False)   # INFO level
```

The constructor's `debug=True` is the usual shortcut; `setupLogging` is for explicit control.
