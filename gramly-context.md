# Gramly AI Context (1.4.x)

Packed from the `ai-context` folder. Start with `README.md` and `AGENTS.md`; each section
below is marked `## File: <name>`.

# Directory Structure
````
01-overview.md
02-handlers.md
03-messaging.md
04-keyboards.md
05-chat-admin.md
06-business.md
07-payments.md
08-inline-settings.md
09-objects.md
10-patterns.md
11-api-index.md
AGENTS.md
llms.txt
README.md
````

# Files

## File: 01-overview.md
````markdown
# 01 — Overview and Runtime Model

**Gramly is an async-first Telegram Bot framework for Python.** It gives you decorators for
every update type, builders for messages and keyboards, and a single `Gramly` object that
owns the event loop and the Telegram API connection.

- **Target release:** `1.4.x`
- **Telegram Bot API:** `10.3`
- **Python:** `3.10+`
- **Install:** `pip install gramly`
- **Import:** `from gramly import Gramly`

This file covers only the framework-level model. Handlers, messages, and domains have
dedicated files.

## Mental model

```text
Telegram update
      |
      v
  bot.guard(...)            global guards, can drop the update
      |
      v
  bot.intercept(...)        raw update side effects (message-type routing)
      |
      v
  route by update type      message / callback / inline / join / payment / business
      |
      v
  handler-specific filters  filters=[...]
      |
      v
  your handler              sync (thread pool) or async (event loop)
      |
      v
  bot.* API call            send / edit / media / admin / payment
```

One `Gramly` instance owns one asyncio event loop. A handler may be a plain function or a
coroutine; Gramly normalizes both.

## Constructor

```text
Gramly(
    token: str,
    msgCooldown: float = 0.35,
    inlineCooldown: float = 0.5,
    connectTimeout: int = 10,
    readTimeout: int = 30,
    locksMaxsize: int = 10000,
    parseMode: str = "HTML",
    debug: bool = False,
)
```

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `token` | `str` | required | Bot token from [@BotFather](https://t.me/BotFather) |
| `msgCooldown` | `float` | `0.35` | Minimum seconds between message updates from one user |
| `inlineCooldown` | `float` | `0.5` | Minimum seconds between inline queries from one user |
| `connectTimeout` | `int` | `10` | Connection timeout, seconds |
| `readTimeout` | `int` | `30` | Response timeout, seconds |
| `locksMaxsize` | `int` | `10000` | Maximum users in the cooldown LRU cache |
| `parseMode` | `str` | `"HTML"` | Default parse mode: `"HTML"` or `"MarkdownV2"` |
| `debug` | `bool` | `False` | Verbose logging |

```python
from gramly import Gramly

bot = Gramly(
    token="YOUR_BOT_TOKEN",
    parseMode="HTML",
    debug=True,
)
```

Properties:

| Property | Type | Meaning |
| --- | --- | --- |
| `bot.parseMode` | `str` | Current default parse mode |
| `bot.debug` | `bool` | Debug logging flag |

Version introspection:

```python
from gramly import __version__, __bot_api_version__

print(__version__)          # installed 1.4.x version string
print(__bot_api_version__)  # "10.3"
```

If the installed version differs, prefer the installed package for signatures and report
the mismatch instead of guessing.

## Public imports

Common names exported by `gramly`:

```python
from gramly import (
    Gramly,
    btn, row, kbd,
    business,
    userRequest, chatRequest, managedBotRequest,
    Rich,
    chatId, userId,
    setupLogging,
    TelegramError,
    Message, CallbackQuery, CallbackData, InlineQuery, JoinRequest,
    BusinessMessage, BusinessConnection, GuestQuery, ManagedBot,
    User, Chat, Payment, PreCheckout, SuccessfulPayment,
    Obj, TimerHandle, CommandBlock,
    DEFAULT_PERMISSIONS,
)
```

Internal helpers such as `matchText`, `toList`, `isNotModified`, and `mimeType` live in
`gramly.gramly` and are not part of the top-level export contract.

## Async model

Gramly runs a single asyncio loop. You do **not** have to write `async`/`await`.

### Plain handler (recommended default)

```python
from gramly import Gramly

bot = Gramly("TOKEN")

@bot.onMessage(commands="start")
def start(msg):
    bot.send(msg, "Hello!")   # blocks this worker thread, not the event loop

bot.run()
```

Gramly wraps a plain function with `asyncio.to_thread`, so it runs in a worker thread and
cannot block the event loop. Every `bot.*` method detects the sync context and returns the
result directly.

### Async handler (when you need to await)

```python
import asyncio
from gramly import Gramly

bot = Gramly("TOKEN")

@bot.onMessage(commands="start")
async def start(msg):
    await asyncio.sleep(1)
    await bot.send(msg, "Hello!")

bot.run()
```

Inside an `async def` handler, `bot.*` methods return coroutines. `await` them.

### Rules

- Pick one style per handler. Once you `await`, keep awaiting every I/O call in that
  function.
- You may mix sync and async handlers in the same bot; each handler is independent.
- In an async handler, calling `bot.send(...)` without `await` schedules a background task.
  It works, but errors are only logged. Use `await` unless fire-and-forget is intentional.
- Never call blocking I/O (requests, `time.sleep`, heavy CPU) inside an `async def` handler.
  Use a plain handler or move the work to a thread/process.
- Sync handlers share the process; use locks or a database for mutable state.

## Starting and stopping

### Long polling (default)

```text
bot.run(
    skipPending: bool = False,
    pollTimeout: int = 20,
    allowedUpdates: list = None,
)
```

| Parameter | Default | Meaning |
| --- | --- | --- |
| `skipPending` | `False` | Drop updates queued before startup |
| `pollTimeout` | `20` | Long-poll timeout in seconds |
| `allowedUpdates` | `None` | Update types to receive; auto-detected when omitted |

`bot.run()` blocks the calling thread and runs until shutdown.

```python
bot.run(
    skipPending=True,
    pollTimeout=30,
    allowedUpdates=["message", "callback_query"],
)
```

### Non-blocking start

```python
bot.start()   # polling in a background thread/task
# ... other work ...
bot.close()
```

`bot.start()` accepts the same parameters as `bot.run()`.

### Webhook mode

Register the webhook once, then feed raw updates to `processUpdate`:

```python
bot.setWebhook(
    url="https://example.com/webhook",
    secretToken="a-long-random-secret",
    allowedUpdates=["message", "callback_query"],
    maxConnections=40,
    dropPending=False,
)
```

```python
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/webhook")
async def webhook(request: Request):
    update = await request.json()
    bot.processUpdate(update)
    return {"ok": True}
```

Remove it with:

```python
bot.deleteWebhook(dropPending=True)
```

`processUpdate(update: dict)` dispatches a raw Telegram update through guards,
interceptors, and handlers. It is the same entry point used by polling.

### Polling lifecycle

```text
bot.run()
  -> getMe(), verify token
  -> optional skipPending
  -> loop:
       getUpdates(offset, timeout, allowed_updates)
       for each update:
           processUpdate(update)
           offset = update_id + 1
  -> onStop handlers, shutdown
```

## Recommended project layout

```text
mybot/
  main.py            # Gramly instance, imports handlers, bot.run()
  config.py          # token and settings from environment
  handlers/
    start.py
    menu.py
    admin.py
  services/          # API clients, database, business logic
  keyboards.py       # reusable btn/row/kbd builders
  states.py          # explicit multi-step state store
  requirements.txt
```

Keep one `Gramly` instance. Import handler modules from `main.py` so the decorators run at
startup. Do not create a second instance for the same token.

```python
# main.py
import os
from gramly import Gramly

bot = Gramly(os.environ["BOT_TOKEN"])

import handlers.start   # noqa: E402,F401  (registers decorators)
import handlers.menu    # noqa: E402,F401

if __name__ == "__main__":
    bot.run()
```

## Configuration and secrets

- Read the token from an environment variable; never commit it.
- `parseMode="HTML"` is the default. Escape user-provided text before interpolating it into
  HTML (`html.escape`).
- `debug=True` is for development; it produces verbose logs.
- Built-in cooldowns are per-user, not per-chat or per-command. Add your own rate limiting
  for expensive operations.

## Minimal end-to-end bot

```python
import os
from gramly import Gramly, btn, row, kbd

bot = Gramly(os.environ["BOT_TOKEN"])

@bot.onMessage(commands="start")
def start(msg):
    bot.send(
        msg,
        f"Hello, {msg.from_user.first_name}!",
        inline=kbd(
            row(btn("Ping", action=f"ping:{msg.user_id}")),
        ),
    )

@bot.onCallback("ping:")
def ping(q):
    bot.alert(q, "Pong!", popup=True)

if __name__ == "__main__":
    bot.run()
```
````

## File: 02-handlers.md
````markdown
# 02 — Handlers, Routing, and Middleware

A handler is a function registered with a decorator. Gramly matches the incoming update,
builds a context object, runs global guards and interceptors, and calls the function.

- Decorators that are **factories** are written with parentheses: `@bot.onMessage(...)`,
  `@bot.onPost()`, `@bot.onAny()`, `@bot.onEdited()`.
- Decorators that are **bare** take the function directly: `@bot.onPayment`,
  `@bot.onCheckout`, `@bot.onWebApp`.
- All decorators return the original function, so they can be stacked.

## Handler map

| Decorator | Form | Trigger | Handler argument |
| --- | --- | --- | --- |
| `@bot.onMessage(...)` | factory | Incoming message | `Message` |
| `@bot.onCallback(...)` | factory | Inline button press | `CallbackQuery` |
| `@bot.onInline(...)` | factory | Inline query | `InlineQuery` |
| `@bot.onEdited()` | factory | Edited message or channel post | `Message` |
| `@bot.onPost()` | factory | Channel post | `Message` |
| `@bot.onMedia(...)` | factory | Message containing media | `Message` |
| `@bot.onAny()` | factory | Unhandled message fallback | `Message` |
| `@bot.onCheckout` | bare | Pre-checkout query | `PreCheckout` |
| `@bot.onPayment` | bare | Successful payment message | `Message` |
| `@bot.onWebApp` | bare | Web App data | `Message` |
| `@bot.onJoinRequest` | bare | Chat join request | `JoinRequest` |
| `@bot.onMyStatus` | bare | Bot's own member status change | `Obj` |
| `@bot.onChatMember` | bare | Any member status change | `Obj` |
| `@bot.onReaction` | bare | Reaction change | `Obj` |
| `@bot.onPoll` | bare | Poll answer (private chats) | `Obj` |
| `@bot.onBoost` | bare | Chat boost / unboost | `Obj` |
| `@bot.onPaidMedia` | bare | Paid media purchase | `Obj` |
| `@bot.onGuest` | bare | Guest query | `GuestQuery` |
| `@bot.onManaged` | bare | Managed bot created/connected | `ManagedBot` |
| `@bot.onGenerationStopped` | bare | User stops a draft | `Obj` |
| `@bot.onBusinessMessage(...)` | factory | Business message | `BusinessMessage` |
| `@bot.onBusinessEdited()` | factory | Edited business message | `BusinessMessage` |
| `@bot.onBusinessConnection` | bare | Business connection change | `BusinessConnection` |
| `@bot.onBusinessDeleted` | bare | Business messages deleted | `Obj` |
| `@bot.command(...)` | factory | Command block router | `CommandBlock` |
| `@bot.onStop` | bare | Bot shutdown | none |

> **Arity trap:** `@bot.onPayment()` raises a `TypeError` because `onPayment` expects the
> function directly. Use `@bot.onPayment`. The same applies to every bare decorator in the
> table: `onCheckout`, `onWebApp`, `onJoinRequest`, `onMyStatus`, `onChatMember`,
> `onReaction`, `onPoll`, `onBoost`, `onPaidMedia`, `onGuest`, `onManaged`,
> `onGenerationStopped`, `onBusinessConnection`, `onBusinessDeleted`, and `onStop`.
>
> Factories require parentheses: `onMessage`, `onCallback`, `onInline`, `onMedia`,
> `onPost`, `onAny`, `onEdited`, `onBusinessMessage`, `onBusinessEdited`, and `command`.
> In particular, `@bot.onPost` raises `TypeError`; `@bot.onAny` and `@bot.onEdited`
> without parentheses return a decorator without registering the handler. The official
> docs show the bare forms of `onPost` and `onAny`, but the installed API requires
> `@bot.onPost()` and `@bot.onAny()`.

## `@bot.onMessage`

The main text router. Every matcher is optional; at least one should be supplied.

```python
@bot.onMessage(
    commands=None,        # str or list: "start", ["help", "info"]
    exact=None,           # full text must equal this
    starts=None,          # text starts with this
    ends=None,            # text ends with this
    contains=None,        # text contains this
    regex=None,           # str or compiled pattern
    withSlash=True,       # accept "/start"
    withoutSlash=True,    # accept "start"
    filters=None,         # list of callables(Message) -> bool
)
def handler(msg: Message): ...
```

Examples:

```python
@bot.onMessage(commands="start")
def start(msg):
    bot.send(msg, f"Hello, {msg.from_user.first_name}!")

@bot.onMessage(commands=["help", "info"])
def help_cmd(msg):
    bot.send(msg, "Help text")

@bot.onMessage(exact="ping")
def ping(msg):
    bot.send(msg, "pong")

@bot.onMessage(starts="find ")
def find(msg):
    query = msg.argsFrom()
    bot.send(msg, f"Searching for: {query}")

@bot.onMessage(regex=r"order #(\d+)")
def order(msg):
    order_id = msg.args[0]        # first capture group
    bot.send(msg, f"Order {order_id}")

@bot.onMessage(contains="discount")
def discount(msg):
    bot.send(msg, "Current discount: 10%")
```

### Matcher semantics

- `commands` matches a command token at the start. With both slash forms enabled, `/start`
  and `start` both match. Remaining words become `msg.args`.
- `exact` requires the complete text to match.
- `starts` matches a prefix; the remainder becomes arguments.
- `ends` matches a suffix.
- `contains` matches anywhere; `msg.args` contains all words of the text.
- `regex` captures groups into `msg.args`; `msg.match` holds the `re.Match`.
- Filters run after the text matcher. Every filter must be truthy. A filter that raises is
  treated as a failed match and the error is logged.

### Argument validation

There is no built-in minimum-argument check:

```python
@bot.onMessage(commands="ban")
def ban_cmd(msg):
    if not msg.has(1):
        bot.send(msg, "Usage: /ban <user_id>")
        return
    user_id = msg.argInt(0)
    if user_id is None:
        bot.send(msg, "user_id must be a number")
        return
    bot.ban(msg.chat_id, user_id)
```

See [`09-objects.md`](09-objects.md) for `arg`, `argInt`, `argFloat`, `has`, and
`argsFrom`.

### Per-handler filters

```python
ADMIN_IDS = {12345, 67890}

def is_admin(msg) -> bool:
    return msg.user_id in ADMIN_IDS

@bot.onMessage(commands="admin", filters=[is_admin])
def admin_panel(msg):
    bot.send(msg, "Admin panel")
```

Filters may be sync or async callables. Use a filter for authorization that applies to a
single route; use a global guard for authorization that applies to everything.

## `@bot.onCallback`

Fires on inline keyboard presses.

```python
@bot.onCallback(
    *prefixes,      # optional; raw callback_data must start with one
    filters=None,   # list of callables(CallbackQuery) -> bool
)
def handler(q: CallbackQuery): ...
```

```python
@bot.onCallback("buy:")
def on_buy(q):
    item = q.cb.get(1)
    bot.edit(q, f"Buying {item}")

@bot.onCallback()          # every callback
def all_callbacks(q):
    print(q.data)
```

- With no prefix, the handler receives all callbacks.
- Prefix matching is on the raw `callback_data` string.
- If the handler returns without acknowledging, Gramly acknowledges automatically.
- Callbacks are serialized per user; a second press while a handler is running is dropped
  with a quick ack.
- Use `q.alert(...)`, `q.ack()`, `q.edit(...)`, or `q.editMarkup(...)` for responses.

## `@bot.onInline`

Fires for inline mode queries (`@botname query`).

```python
@bot.onInline(minLength=0)
def handler(q: InlineQuery): ...
```

```python
@bot.onInline(minLength=2)
def inline(q):
    results = [
        q.article("Result 1", "Message content 1", description="Subtitle"),
        q.article("Result 2", "Message content 2"),
    ]
    q.answer(results, cacheTime=10)
```

`minLength` drops queries shorter than the given length. See
[`08-inline-settings.md`](08-inline-settings.md) for result builders.

## Media handlers

### `@bot.onMedia(*contentTypes)`

Fires when the message contains one of the listed media types.

```python
@bot.onMedia("photo")
def photo(msg):
    bot.send(msg, "Nice photo!")

@bot.onMedia("photo", "video", "document")
def media(msg):
    bot.send(msg, "You sent media!")
```

Common content types include `photo`, `video`, `document`, `audio`, `voice`, `animation`,
`video_note`, `sticker`, `contact`, `location`, `venue`, `poll`, `dice`, `users_shared`,
`chat_shared`, and `web_app_data`. The exact string is the Telegram field name on the
message.

### `@bot.onAny()`

Fallback for messages not handled by `onMessage` or a `CommandBlock`. The parentheses are
required; `@bot.onAny` silently registers nothing.

```python
@bot.onAny()
def fallback(msg):
    bot.send(msg, "I don't understand that command.")

@bot.onAny(filters=[lambda m: m.isPrivate])
def private_fallback(msg):
    bot.send(msg, "Try /help.")
```

`onAny` skips messages already handled by another route. Use it for a single catch-all
fallback, not for business logic that belongs in `onMessage`.

## Other event handlers

### Edited messages

```python
@bot.onEdited()
def edited(msg):
    bot.send(msg, "You edited your message.")
```

Business-scoped edited messages use `@bot.onEdited(business())`; see
[`06-business.md`](06-business.md).

### Channel posts

```python
@bot.onPost()
def post(msg):
    print(msg.chat.title, msg.text)
```

### Web App data

```python
@bot.onWebApp
def webapp(msg):
    data = msg.webAppData
    bot.send(msg, f"Received: {data}")
```

### Join requests

```python
@bot.onJoinRequest
def join(rq):
    bot.approveJoin(rq)      # or bot.declineJoin(rq)
```

### Member and status events

```python
@bot.onMyStatus
def my_status(update):
    print("Bot status changed", update)

@bot.onChatMember
def member(update):
    print("Member changed", update)

@bot.onReaction
def reaction(update):
    print("Reaction changed", update)

@bot.onPoll
def poll_answer(update):
    print("Poll answered", update)

@bot.onBoost
def boost(update):
    print("Boost", update)

@bot.onPaidMedia
def paid_media(update):
    print("Paid media purchased", update)
```

These handlers receive a generic `Obj` (or a specific object where documented) with the raw
Telegram fields. Access fields as attributes or dict keys; see [`09-objects.md`](09-objects.md).

### Guest queries

```python
@bot.onGuest
def guest(q):
    q.answer(f"Hello {q.fromUser.first_name}!")
```

### Managed bots

```python
@bot.onManaged
def managed(mb):
    print(mb.creator.first_name, mb.bot.username)
    token = mb.token()
```

### Generation stopped

```python
@bot.onGenerationStopped
def stopped(data):
    print("Draft stopped", data)
```

Only fires for drafts sent with `canStop=True`.

## Payments

```python
@bot.onCheckout
def checkout(pco):
    if pco.totalAmount < 50:
        pco.reject("Minimum order is 50 Stars")
    else:
        pco.accept()

@bot.onPayment
def payment(msg):
    p = msg.payment
    bot.send(msg, f"Thanks! {p.stars} Stars received.")
```

Full flow in [`07-payments.md`](07-payments.md).

## `CommandBlock` — grouped commands and callbacks

`CommandBlock` keeps one command, its text sub-routes, and its callback actions together.

```python
@bot.command(
    *triggers,                 # "market", ["shop", "store"]
    withSlash=True,
    withoutSlash=True,
    filters=None,              # applies to every route in the block
    starts=None,               # prefix trigger instead of a word
    ends=None,                 # suffix trigger
)
def market(cmd: CommandBlock): ...
```

### `cmd.default`

Runs when the block trigger fires with no sub-route.

```python
@cmd.default(filters=None)
def fallback(msg): ...
```

### `cmd.on`

Text sub-route. Matches the remaining text after the block trigger.

```python
@cmd.on(
    *keys,                 # positional strings
    exact=None,
    starts=None,
    ends=None,
    contains=None,
    regex=None,
    filters=None,
)
def sub_handler(msg): ...
```

### `cmd.onCallback`

Callback sub-route. Matches the **first** segment of `callback_data` exactly.

```python
@cmd.onCallback(*actions, filters=None)
def cb_handler(q): ...
```

### Complete example

```python
from gramly import Gramly, CallbackQuery, btn, row, kbd

bot = Gramly("TOKEN")

def is_owner(q):
    return q.cb.get(0, int) == q.user_id

@bot.command("market")
def market(cmd):

    def show_menu(target):
        uid = target.user_id
        markup = kbd(
            row(btn("Food", action=f"category:{uid}:food")),
            row(btn("Cookies", action=f"category:{uid}:cookies")),
        )
        if isinstance(target, CallbackQuery):
            bot.edit(target, "<b>Market</b>", inline=markup)
        else:
            bot.send(target, "<b>Market</b>", inline=markup)

    @cmd.default
    def on_default(msg):
        show_menu(msg)

    @cmd.onCallback("category", filters=[is_owner])
    def on_category(q):
        category = q.cb.get(1)
        text = {
            "food": "Food: bread, apples",
            "cookies": "Cookies: magic, damage",
        }.get(category, "Empty section.")
        bot.edit(q, text, inline=kbd(
            row(btn("Back", action=f"back:{q.user_id}"))
        ))

    @cmd.onCallback("back", filters=[is_owner])
    def on_back(q):
        show_menu(q)

    @cmd.on("promo")
    def on_promo(msg):
        if not msg.has(1):
            bot.send(msg, "Usage: /market promo <code>")
            return
        if msg.arg(0) == "gramly":
            bot.send(msg, "Promo activated: 1000 coins")
        else:
            bot.send(msg, "Promo code not found.")

bot.run()
```

Notes:

- Block-level `filters` apply to every route inside the block, including callbacks. Use it
  for a shared owner check instead of repeating the filter.
- Callback actions are matched on the first `:`-separated part, so use
  `action:f"{user_id}:..."` style data consistently.
- A duplicate registration for the same command, route, or callback action raises
  `ValueError` at import time.
- `cmd.on` has no built-in argument count check; use `msg.has(n)`.

## Guards and interceptors

### Global guard

```python
@bot.guard
def only_private(ctx):
    return ctx.chat_type == "private"

# or
bot.guard(only_private)
```

A guard receives the parsed context (`Message`, `CallbackQuery`, `InlineQuery`,
`JoinRequest`, or `BusinessMessage`). Return `True` to allow the update; return `False` to
drop it silently. Multiple guards can be registered; all must pass. A guard that raises is
treated as a failed check.

### Global interceptor

```python
@bot.intercept
def log_message(raw: dict):
    uid = (raw.get("from") or {}).get("id")
    print(uid, raw.get("text", ""))

# or
bot.intercept(log_message)
```

An interceptor receives the raw update dict. It runs after guards, before handlers, for
message-type updates that go through routing. Use it for logging, analytics, and side
effects, not for authorization.

### Execution order

```text
raw update
  -> guard 1 (drop on False)
  -> guard 2 (drop on False)
  -> interceptor (raw dict)
  -> handler-specific filters
  -> handler
```

### Shutdown hook

```python
@bot.onStop
def cleanup():
    print("Bot is stopping")
```

Use it to close database connections, flush queues, and stop timers.

## Stacking decorators

Because decorators return the original function, one function can serve multiple routes:

```python
@bot.onMessage(commands="start")
@bot.onMessage(exact="hello")
def start_or_hello(msg):
    bot.send(msg, "Hello!")
```

## Choosing the right handler

- Use `onMessage(commands=...)` for `/start`, `/help`, and simple commands.
- Use `onMessage(exact=..., starts=..., regex=...)` for natural-language or pattern input.
- Use `onCallback` for stateless buttons and `CommandBlock` when a command owns a menu.
- Use `onMedia` for uploads and shared contacts/chats.
- Use `onAny` only as a fallback.
- Use a global `guard` for authorization that must apply to every update; use `filters` for
  a single route.
````

## File: 03-messaging.md
````markdown
# 03 — Messaging, Media, Rich Content, and Actions

Everything a handler sends or changes goes through the `bot` object. Targets are flexible:
a chat ID, a `Message`, a `CallbackQuery`, or a dict containing an `id`/`chat`.

```python
bot.send(chat_id, "Hello")
bot.send(msg, "Hello")          # replies into the same chat
bot.send(cb, "Hello")           # sends to the callback's chat
```

`bot.send` and `bot.reply` accept `target` as `int | Message | CallbackQuery | dict`.

## Send and reply

### `bot.send`

```python
bot.send(
    target,
    text,                       # str or Rich(...)
    inline=None,                # inline keyboard structure
    keyboard=None,              # reply keyboard structure
    photo=None,                 # URL or file_id; sends photo + caption
    forceReply=None,            # open the user's input field
    business_connection_id=None,# send as a business account
    **kwargs,                   # Telegram API parameters
)
```

```python
bot.send(msg, "Hello!")
bot.send(msg, "Caption", photo="https://example.com/image.jpg")
bot.send(msg, "Protected", protect_content=True)
bot.send(msg, "No preview", disable_web_page_preview=True)
bot.send(msg, "Choose:", inline=kbd(row(btn("OK", action=f"ok:{msg.user_id}"))))
bot.send(msg, "Pick:", keyboard=[["Option A", "Option B"], ["Cancel"]])
bot.send(msg, "Done.", keyboard=False)        # remove the reply keyboard
bot.send(msg, "Reply to this:", forceReply=True)
```

### `bot.reply`

Same parameters as `bot.send`, plus reply threading to the incoming message:

```python
@bot.onMessage(commands="hello")
def hello(msg):
    bot.reply(msg, f"Hello, {msg.from_user.first_name}!")
```

### `bot.ephemeral` (group-only)

Sends a message visible to one member of a group or supergroup.

```python
bot.ephemeral(
    target,                     # group/supergroup
    text,                       # str or Rich(...)
    to=None,                    # who sees it; defaults to target
    keyboard=None,
    inline=None,
    photo=None,
    replaceCallbackMessage=None,# replace the callback's original message
    **kwargs,
)
```

```python
@bot.onCallback("reveal:")
def reveal(cb):
    bot.ephemeral(cb, "Only you can see this", to=cb)

bot.ephemeral(group_chat_id, "Admin-only note", to=user_id)
```

Rules:

- Works only in groups and supergroups. It cannot be used in private chats or channels.
- A bot with admin rights may send at any time. Without admin rights, it may respond within
  15 seconds of an eligible action; pass the `CallbackQuery` or incoming `Message` as `to`.
- `bot.edit`, `bot.editMarkup`, and `bot.delete` auto-detect ephemeral messages and route to
  the ephemeral API. `bot.replace` does **not** support ephemeral messages.

### Parse mode

The bot-wide default is `"HTML"` (constructor `parseMode`). Override per call:

```python
bot.send(msg, "<b>bold</b> <i>italic</i>")                 # HTML
bot.send(msg, "*bold* _italic_", parseMode="MarkdownV2")   # MarkdownV2
```

All send and edit methods accept `parseMode`. Escape user input when building HTML:

```python
import html
bot.send(msg, f"<b>{html.escape(user_text)}</b>")
```

## Edit, replace, and delete

### `bot.edit`

```python
bot.edit(call, text, inline=None, photo=None, showCaption=None, **kwargs)
```

- `call` is a `Message` or a `CallbackQuery`.
- Edits text or caption automatically; for a photo message it uses the caption API.
- With `photo=...`, edits the media as well.
- `showCaption=True/False` moves a caption above/below the media.
- Accepts `parseMode` per call.
- Detects ephemeral messages automatically.
- When editing a `Rich(...)` message, media must be a URL or `file_id`; local bytes/paths are
  only supported on the initial send, not on edit.

```python
bot.edit(msg, "Updated text")
bot.edit(cb, "New menu", inline=kbd(row(btn("Back", action=f"back:{cb.user_id}"))))
bot.edit(msg, "New caption")                       # photo message
bot.edit(msg, "New photo", photo="https://example.com/new.jpg")
```

### `bot.editMarkup`

Edits only the inline keyboard:

```python
bot.editMarkup(cb, inline=None)   # inline=None or [] removes all buttons
```

### `bot.replace`

Replaces a message even when the media type changes:

```python
bot.replace(call, text, inline=None, photo=None, **kwargs)
```

Uses `editMessageText` when possible, otherwise deletes and re-sends. Useful for replacing
a photo message with text. Not supported for ephemeral messages.

### Live location

```python
bot.editLiveLocation(call, latitude, longitude, inline=None, **kwargs)
bot.stopLiveLocation(call, inline=None, **kwargs)
```

### Delete

```python
bot.delete(message)                       # single Message/BusinessMessage, returns bool
bot.delete(chat_id, message_id)           # single by ID
bot.delete(chat_id, [111, 222, 333])      # bulk by IDs
bot.delete(message, bcId="bc_1")          # business chat
bot.deleteMessage(chat_id, message_id)    # explicit single-message helper
bot.deleteMessages(chat_id, [111, 222])   # explicit bulk helper
bot.deleteLater(message, 60)              # delete after 60 seconds
bot.deleteLater(message, 60, messageId=..., bcId=...)
```

`deleteLater` takes the delay in seconds as the second positional argument (`delay`).

## Media

All media methods accept a file ID, an HTTPS URL, a local path, a file object, or raw bytes.
For albums, pass a list.

### Methods

```python
bot.photo(target, photo, caption=None, inline=None, keyboard=None, **kwargs)
bot.photo(target, ["file_id_1", "file_id_2"], caption="Album")

bot.media(target, items, caption=None, inline=None, keyboard=None, **kwargs)
# up to 10 mixed photos/videos/audio/documents in one album

bot.video(target, video, caption=None, inline=None, keyboard=None, **kwargs)
bot.document(target, doc, caption=None, inline=None, keyboard=None, **kwargs)
bot.audio(target, audio, caption=None, inline=None, keyboard=None, **kwargs)
bot.voice(target, voice, caption=None, inline=None, keyboard=None, **kwargs)
bot.animation(target, animation, caption=None, **kwargs)
bot.videoNote(target, videoNote, **kwargs)
bot.sticker(target, sticker, **kwargs)
bot.paidMedia(target, starCount, media, **kwargs)
```

Examples:

```python
bot.photo(msg, "https://example.com/image.jpg", caption="Nice view")
bot.photo(msg, photo="AgACAgIAAxk...", caption="Select",
          inline=[[btn("Yes", action="yes:1"), btn("No", action="no:1")]])
bot.media(msg, ["/tmp/a.jpg", "/tmp/b.png", "/tmp/clip.mp4"], caption="Album")
bot.document(msg, open("report.pdf", "rb"), caption="Report")
bot.videoNote(msg, "/tmp/note.mp4")
```

### Sources

| Source | Example |
| --- | --- |
| File ID | `"AgACAgIAAxkB..."` |
| HTTPS URL | `"https://example.com/image.jpg"` |
| Local path | `"/tmp/photo.jpg"` or `open("photo.jpg", "rb")` |
| Raw bytes | `b"..."` or `bytearray(...)` |

`bot.media()` does not accept dict items. Use a file ID, path, file object, or bytes.

## Rich messages

`Rich(...)` builds a formatted message from blocks. Pass it wherever `text` is accepted:
`bot.send`, `bot.reply`, `bot.edit`, `bot.replace`, and `bot.ephemeral`.

`Rich.Build(*blocks, forDraft=False)` is the low-level constructor. It always returns a
finished message and does not interpret `{name}` placeholders as templates.

```python
from gramly import Rich

bot.send(msg, Rich(
    Rich.Heading("Order confirmed"),
    Rich.Paragraph("Your order will arrive in 2-3 days."),
    Rich.Divider(),
    Rich.Footer("Thanks for shopping with us"),
))
```

### Text and structure blocks

| Builder | Produces |
| --- | --- |
| `Rich.Heading(*parts, size=1)` | Heading, size 1–6 |
| `Rich.Paragraph(*parts)` | Paragraph |
| `Rich.Footer(*parts)` | Small footer text |
| `Rich.Quote(*parts, credit=None)` | Blockquote; may contain nested blocks |
| `Rich.ExpandableQuote(*parts, credit=None, expanded=False)` | Collapsible quote |
| `Rich.PullQuote(*parts, credit=None)` | Pull quote (plain text only) |
| `Rich.BulletList(*items)` | List of `Rich.Item(...)` |
| `Rich.Item(*parts, checkbox=None, checked=None, children=None)` | List entry; optional checkbox and nesting |
| `Rich.CodeBlock(text, language=None)` | Code block with syntax highlighting |
| `Rich.MathBlock(expression)` | Math expression |
| `Rich.Divider()` | Horizontal rule |
| `Rich.Details(summary, *parts, open=False)` | Collapsible section |
| `Rich.Table(rows, headerRow=True, bordered=None, striped=None, compact=None, caption=None)` | Table; first row is the header when `headerRow=True` |
| `Rich.Map(latitude, longitude, zoom=15, width=400, height=300, caption=None, credit=None)` | Static map |

Examples:

```python
Rich.Table(rows=[
    ["Item", "Price"],
    ["Sneakers", "3200"],
    ["Hoodie", "1450"],
])

Rich.BulletList(
    Rich.Item("Buy milk", checkbox=True),
    Rich.Item("Buy bread", checkbox=True, checked=True),
)

Rich.Details("Shipping details", Rich.Paragraph("Ships in 2 days."))
```

### Inline styles and links

`Rich.Run(text, style=None, **kwargs)` wraps one piece of text:

- `style`: `"bold"`, `"italic"`, `"underline"`, `"strike"`, `"spoiler"`, `"mono"`,
  `"mark"`, `"sub"`, `"sup"`.
- Entity keywords: `link`, `mention`, `username`, `hashtag`, `cashtag`, `botCommand`,
  `email`, `phone`, `bankCard`, `date`, `math`.

Set exactly one style or entity option at a time.

```python
Rich.Paragraph(
    "Plain text, ",
    Rich.Run("bold text", "bold"),
    ", and a ",
    Rich.Run("link", link="https://example.com"),
    ".",
)
```

`Rich.EmojiRun(customEmojiId, alt="🙂")` inserts a custom emoji.

### Anchors, references, and buttons

```python
Rich.Anchor("section-1")
Rich.AnchorLink("Jump to section", "section-1")
Rich.Ref("note-1")
Rich.RefLink("See note", "note-1")

Rich.Paragraph("Tap: ", Rich.ButtonRun(btn("Open", url="https://example.com")))
Rich.Buttons(
    btn("Yes", action="poll:yes"),
    btn("No", action="poll:no"),
    align="center",           # "left" | "center" | "right"
)
```

### Media blocks

| Builder | Produces |
| --- | --- |
| `Rich.Photo(media, caption=None, credit=None, spoiler=False)` | Photo |
| `Rich.Video(media, caption=None, credit=None, spoiler=False, **kwargs)` | Video |
| `Rich.Animation(media, caption=None, credit=None, spoiler=False, **kwargs)` | GIF/animation |
| `Rich.Audio(media, caption=None, credit=None, title=None, performer=None)` | Audio |
| `Rich.Voice(media, caption=None, credit=None, duration=None)` | Voice note |
| `Rich.Document(media, caption=None, credit=None, fileName=None)` | Document |
| `Rich.Collage(items, caption=None, credit=None)` | Media group as a grid |
| `Rich.Slideshow(items, caption=None, credit=None)` | Media group as a slideshow |

### Markdown and HTML sources

```python
Rich.Markdown(text, media=None, rtl=None, skipEntityDetection=None)
Rich.Html(text, media=None, rtl=None, skipEntityDetection=None)
```

Both wrap existing markup into a rich message without using the block builders.

### Templates with `{slot}` placeholders

If any text contains `{name}`, `Rich(...)` returns a reusable template instead of a
finished message:

```python
product_card = Rich(
    Rich.Heading("{name}"),
    Rich.Paragraph("Price: {price}"),
)

bot.send(msg, product_card(name="Sneakers", price="3200"))
bot.send(msg, product_card("Hoodie", "1450"))   # positional order of first appearance
```

- Missing values raise `KeyError`; passing the same name positionally and by keyword raises
  `TypeError`.
- A repeated placeholder is filled once and reused in every location.
- Without placeholders, `Rich(...)` returns a finished message immediately.

### Draft-only thinking block

`Rich.Thinking(*parts)` is accepted only by `bot.messageDraft`, or by a `Rich(...)` built with
`forDraft=True`. Passing it to `send`, `reply`, or `edit` raises `TelegramError`.

```python
bot.messageDraft(msg, draft_id, text=Rich(
    Rich.Thinking("Working out the answer..."),
    Rich.Paragraph("Here is what I found."),
    forDraft=True,
))
```

## Special content

```python
bot.location(target, latitude, longitude, **kwargs)
bot.venue(target, latitude, longitude, title, address, **kwargs)
bot.contact(target, phone, firstName, lastName=None, **kwargs)
bot.dice(target, emoji="🎲", **kwargs)
bot.game(target, gameShortName, inline=None, keyboard=None, **kwargs)
bot.livePhoto(target, photo, animation, caption=None, inline=None, keyboard=None, **kwargs)
bot.checklist(target, title, tasks, **kwargs)
bot.editChecklist(target, messageId, title, tasks, **kwargs)
bot.messageDraft(target, draftId, text="", inline=None, keyboard=None,
                 canStop=None, keepOnStop=None, **kwargs)
```

### Polls

```python
bot.poll(
    target,
    question,
    options,                       # list of str or dict
    isAnonymous=True,
    pollType="regular",            # "regular" | "quiz"
    correctOptionIds=None,
    explanation=None,
    allowsMultipleAnswers=False,
    allowsRevoting=None,
    shuffleOptions=None,
    allowAddingOptions=None,
    hideResultsUntilCloses=None,
    description=None,
    openPeriod=None,
    closeDate=None,
    membersOnly=None,
    countryCodes=None,
    **kwargs,
)
bot.stopPoll(target, messageId, **kwargs)
```

```python
bot.poll(msg, "Favorite color?", ["Red", "Blue", "Green"])
bot.poll(msg, "What is 2+2?", ["3", "4", "5"],
         pollType="quiz", correctOptionIds=[1], explanation="Basic math!")
```

### Checklists

```python
bot.checklist(msg, "Shopping", [
    {"text": "Milk", "finished": False},
    {"text": "Bread", "finished": True},
])

bot.editChecklist(chat_id, message_id, "Updated", [
    {"text": "Milk", "finished": True},
])
```

### Message drafts

Drafts render as a "generating..." bubble. `draftId` is required.

```python
bot.messageDraft(msg, draft_id, "Working on it...")
bot.messageDraft(msg, draft_id, "Working on it...", canStop=True, keepOnStop=True)
```

Use `@bot.onGenerationStopped` to react when the user stops a draft.

## Message actions

```python
bot.action(target, action="typing")
```

Common actions: `typing`, `upload_photo`, `record_video`, `upload_video`, `record_voice`,
`upload_voice`, `upload_document`, `choose_sticker`, `find_location`, `record_video_note`,
`upload_video_note`.

### Forward and copy

```python
bot.forward(target, message)
bot.forwardMessages(target, fromChatId, messageIds)
bot.copy(target, message, **kwargs)
bot.copyMessages(target, fromChatId, messageIds, **kwargs)
```

### Pin, unpin, react

```python
bot.pin(message, notify=False)
bot.unpin(chat_id)                 # unpin all
bot.unpin(chat_id, msg_id)         # unpin one

bot.react(msg, "👍")               # one reaction
bot.react(msg, "🔥", "❤️")          # multiple
bot.react(msg, "5368324170671202286")  # custom emoji ID
bot.react(msg, "❤️", isBig=True)
bot.react(msg)                     # remove reactions
```

`bot.pin` and `bot.unpin` accept a `BusinessMessage` and pick up its connection ID
automatically.

### Leave a chat

```python
bot.leave(chat_id)
```

## Important restrictions

- Ephemeral messages: groups/supergroups only; no `replace()`.
- `bot.edit` with `Rich(...)` media: URL or `file_id` only, not local files.
- `bot.media()`: no dict items.
- HTML must be well-formed; escape untrusted text.
- Telegram caption limits apply (1024 characters); longer text must be a separate message.
- Reply keyboards are per-chat state. Send `keyboard=False` to remove one.
- A callback handler that returns without answering is acknowledged automatically.
````

## File: 04-keyboards.md
````markdown
# 04 — Keyboards and Buttons

Gramly uses one builder for every button type. `btn()` decides whether it creates an inline
button or a reply-keyboard button from the arguments you pass. `row()` and `kbd()` arrange
buttons into rows.

```python
from gramly import btn, row, kbd
```

## `btn()`

```text
btn(
    text: str,
    action=None,                 # callback data: "action:args"
    *,
    # inline only
    url: str = None,
    miniApp: str = None,
    loginUrl: dict = None,
    switchInline: str = None,
    switchInlineCurrent: str = None,
    switchInlineChosen: dict = None,
    copyText: str = None,
    pay: bool = False,
    # reply keyboard only
    requestPoll: str = None,     # "regular" | "quiz"
    requestContact: bool = False,
    requestLocation: bool = False,
    # appearance
    style: str = None,           # "primary" | "danger" | "success"
    emoji: str = None,
    disabled: bool = None,       # inline only
)
```

Exactly one action type should be supplied. `disabled=True` is the only case where no
action, URL, or other payload is required.

### Inline buttons

An inline button is attached to a message and sends a `callback_query` when pressed.

```python
btn("Confirm", action="confirm:1")
btn("Cancel", action="cancel:1")

btn("Save", action="save:1", style="primary")
btn("Delete", action="delete:1", style="danger")
btn("Done", action="done:1", style="success")

btn("Open site", url="https://example.com")
btn("Open app", miniApp="https://example.com/app")
btn("Copy token", copyText="abc-123")
btn("Share", switchInline="")
btn("Pay", pay=True)
btn("Sold out", disabled=True)
```

`callback_data` is limited to **64 bytes**. Use the `action:args` format:

```python
btn("Buy", action=f"buy:{user_id}:item_9")
```

Do not hand-write inline button dicts with `callback_data`; the builder expects the `data`
field produced by `btn()`. Use `btn()` for every inline button.

### Reply keyboard buttons

A reply keyboard button sits below the input field and sends a normal message when tapped.

```python
btn("Send phone", requestContact=True)
btn("Send location", requestLocation=True)
btn("Quiz", requestPoll="quiz")
btn("Poll", requestPoll="regular")
```

A reply keyboard can also contain plain strings:

```python
keyboard=[
    ["Option A", "Option B"],
    ["Cancel"],
]
```

### Appearance

- `style`: `"primary"` (blue), `"danger"` (red), `"success"` (green).
- `emoji`: custom emoji ID or supported emoji.
- `disabled=True`: greyed out and non-clickable, inline only.

## Layout: `row()` and `kbd()`

```python
row(*buttons)   # one row
kbd(*rows)      # collection of rows
```

```python
inline = kbd(
    row(btn("Yes", action=f"yes:{uid}"), btn("No", action=f"no:{uid}")),
    row(btn("Cancel", action=f"cancel:{uid}")),
)
bot.send(msg, "Are you sure?", inline=inline)
```

`kbd()` accepts several shapes:

| Shape | Example | Result |
| --- | --- | --- |
| Single button | `kbd(btn("OK", action="ok:1"))` | One row, one button |
| Flat buttons | `kbd(btn("1", action="a:1"), btn("2", action="a:2"))` | One row, several buttons |
| Rows | `kbd(row(...), row(...))` | One row per `row()` |
| Nested lists | `[[btn(...)], [btn(...)]]` | One row per inner list |

A flat list of strings or buttons is also accepted directly by `keyboard=` and `inline=`:

```python
bot.send(msg, "Pick:", inline=[
    [btn("A", action="a:1"), btn("B", action="b:1")],
    [btn("Cancel", action="cancel:1")],
])
```

`kbd()` structures are converted internally to Telegram's `reply_markup`. The converters
(`buildInlineKeyboard`, `buildReplyKeyboard`) are internal and are not exported from
`gramly`.

## Inline vs reply

| | Inline keyboard | Reply keyboard |
| --- | --- | --- |
| Parameter | `inline=` | `keyboard=` |
| Placement | Attached to the message | Bottom of the screen |
| Press result | `callback_query` | A normal message |
| Persistence | Lives with the message | Persists until replaced/removed |
| Button data | `action`, `url`, `miniApp`, ... | Text, contact, location, poll |
| Removal | `bot.editMarkup(call, [])` | `keyboard=False` |

```python
# Inline
bot.send(msg, "Menu:", inline=kbd(
    row(btn("Profile", action=f"profile:{msg.user_id}")),
))

# Reply
bot.send(msg, "Choose:", keyboard=[
    ["Profile", "Settings"],
    ["Cancel"],
])

# Remove reply keyboard
bot.send(msg, "Done.", keyboard=False)

# Force the input field open
bot.send(msg, "Type your answer:", forceReply=True)
```

## Request builders

These open Telegram's native pickers. Results arrive as messages with `users_shared` or
`chat_shared`; handle them with `@bot.onMedia("users_shared")` and
`@bot.onMedia("chat_shared")`. They are reply-keyboard buttons.

### `userRequest()`

```text
userRequest(
    requestId: int,
    *,
    isBot: bool = None,
    isPremium: bool = None,
    maxQuantity: int = None,       # 1–10, default 1
    requestName: bool = None,
    requestUsername: bool = None,
    requestPhoto: bool = None,
)
```

```python
btn("Pick user", userRequest(1, requestName=True, requestUsername=True))
btn("Pick 3 users", userRequest(2, maxQuantity=3, requestName=True))
btn("Bots only", userRequest(3, isBot=True))
```

```python
@bot.onMedia("users_shared")
def got_users(msg):
    rid = msg.userShared.request_id
    users = msg.userShared.users
    first = users[0]
    name = getattr(first, "first_name", "?")
    username = getattr(first, "username", None)
    bot.send(msg, f"{name} {username or ''} ({first.user_id})")
```

### `chatRequest()`

```text
chatRequest(
    requestId: int,
    *,
    isChannel: bool = None,
    isForum: bool = None,
    hasUsername: bool = None,
    isCreated: bool = None,
    botIsMember: bool = None,
    requestTitle: bool = None,
    requestUsername: bool = None,
    requestPhoto: bool = None,
    userAdminRights: dict = None,
    botAdminRights: dict = None,
)
```

```python
btn("Any chat", chatRequest(1))
btn("Channel", chatRequest(2, isChannel=True, requestTitle=True))
btn("Group", chatRequest(3, isChannel=False, requestTitle=True))
btn("My chat", chatRequest(4, isCreated=True, requestTitle=True))
```

```python
@bot.onMedia("chat_shared")
def got_chat(msg):
    shared = msg.chatShared
    title = getattr(shared, "title", "?")
    bot.send(msg, f"{title} ({shared.chat_id})")
```

### `managedBotRequest()`

Opens Telegram's Managed Bots flow. The result arrives on `@bot.onManaged`.

```text
managedBotRequest(
    requestId: int,
    *,
    suggestedName: str = None,
    suggestedUsername: str = None,
)
```

```python
btn("Connect a bot", managedBotRequest(1))
btn("Create a shop bot", managedBotRequest(
    2, suggestedName="My Shop", suggestedUsername="myshop_bot",
))

@bot.onManaged
def managed(mb):
    token = mb.token()
```

## Callback data contract

Use a stable, compact, action-first format:

```text
action:user_id:payload
```

Examples:

```python
btn("Buy", action=f"buy:{uid}:item_9")
btn("Page 2", action=f"page:{uid}:2")
btn("Cancel", action=f"cancel:{uid}")
```

Consumers:

```python
@bot.onCallback("buy:")
def buy(q):
    owner = q.cb.get(0, int)
    item = q.cb.get(1)
    if owner != q.user_id:
        q.alert("Not your button", popup=True)
        return
    bot.edit(q, f"Bought {item}")
```

- `q.cb.parts` includes the action; `q.cb.args` and `q.cb.get(i)` skip it.
- Keep under 64 bytes; IDs are cheaper than JSON.
- For `CommandBlock`, `cmd.onCallback("buy")` matches the exact first segment.
- Per-user serialization means a second tap while a handler runs is dropped with an ack.

## Full example

```python
from gramly import Gramly, btn, row, kbd

bot = Gramly("TOKEN")

@bot.onMessage(commands="start")
def start(msg):
    uid = msg.user_id
    bot.send(
        msg,
        "Choose an option:",
        inline=kbd(
            row(btn("Profile", action=f"profile:{uid}")),
            row(btn("Settings", action=f"settings:{uid}")),
            row(btn("Website", url="https://example.com")),
        ),
    )

@bot.onCallback("profile:")
def profile(q):
    if q.cb.get(0, int) != q.user_id:
        q.alert("Not your menu.", popup=True)
        return
    bot.edit(q, "Your profile", inline=kbd(
        row(btn("Back", action=f"back:{q.user_id}")),
    ))

@bot.onCallback("back:")
def back(q):
    uid = q.user_id
    bot.edit(q, "Choose an option:", inline=kbd(
        row(btn("Profile", action=f"profile:{uid}")),
        row(btn("Settings", action=f"settings:{uid}")),
    ))

bot.run()
```
````

## File: 05-chat-admin.md
````markdown
# 05 — Chat Management and Moderation

Most methods in this file accept a chat ID, a `Message`, a `Chat`, a `CallbackQuery`, or a
dict as `target`. The bot must be an administrator with the relevant right unless stated
otherwise.

```python
bot.ban(msg, user_id)                 # target from a Message
bot.ban(-1001234567890, user_id)      # target as an ID
```

## Membership and moderation

### Ban and unban

```python
bot.ban(target, userId, until=0, revokeMessages=False)
bot.unban(target, userId)
```

- `until` is a Unix timestamp; `0` means permanent.
- `revokeMessages=True` deletes the user's messages where Telegram supports it.

```python
bot.ban(chat_id, user_id)
bot.ban(chat_id, user_id, until=1700000000)
bot.ban(chat_id, user_id, revokeMessages=True)
bot.unban(chat_id, user_id)
```

### Kick

```python
bot.kick(target, userId)
```

Bans and immediately unbans, so the user can rejoin if the chat allows it.

### Mute and unmute

```python
bot.mute(target, userId, until=0)
bot.unmute(target, userId)
```

### Restrict

```python
bot.restrict(target, userId, permissions, until=0)
```

```python
bot.restrict(chat_id, user_id, {
    "can_send_messages": True,
    "can_send_media_messages": False,
    "can_send_polls": False,
})
```

### Promote

```python
bot.promote(target, userId, **permissions)
```

```python
bot.promote(chat_id, user_id,
    can_change_info=True,
    can_delete_messages=True,
    can_invite_users=True,
    can_pin_messages=True,
    can_restrict_members=True,
    can_promote_members=False,
    can_manage_chat=True,
    can_manage_video_chats=True,
    can_post_stories=True,
    can_edit_stories=True,
    can_delete_stories=True,
    can_post_messages=True,
    can_edit_messages=True,
    can_manage_topics=True,
)
```

Only grant rights the bot itself has. A bot cannot promote someone above its own level.

### Admin title and member tag

```python
bot.setAdminTitle(target, userId, title)
bot.setMemberTag(target, userId, tag)
```

### Default chat permissions

```python
bot.setChatPermissions(target, permissions)
```

### Sender bans

Ban or unban a channel that posts as a sender in a group:

```python
bot.banSender(target, senderChatId)
bot.unbanSender(target, senderChatId)
```

## Chat information

```python
bot.getChat(target)                        # full Chat object
bot.getChatMember(target, userId)          # member object
bot.getChatMemberCount(target)             # int
bot.isAdmin(target, userId)                # bool
bot.getAdmins(target, includeBots=False)   # list
bot.getUserBoosts(target, userId)          # boost info
```

```python
chat = bot.getChat(msg)
print(chat.title, chat.type, chat.username)

member = bot.getChatMember(chat_id, user_id)
print(member.status)   # member | administrator | creator | left | kicked

count = bot.getChatMemberCount(chat_id)

if bot.isAdmin(chat_id, user_id):
    bot.send(chat_id, "You are an admin.")

for admin in bot.getAdmins(chat_id):
    print(admin.user.id, admin.status)

boosts = bot.getUserBoosts(chat_id, user_id)
```

## Chat settings

```python
bot.setChatTitle(target, title)
bot.setChatDescription(target, description)
bot.setChatPhoto(target, photo)
bot.deleteChatPhoto(target)
bot.setChatStickerSet(target, stickerSetName)
bot.deleteChatStickerSet(target)
```

```python
bot.setChatTitle(chat_id, "New Group Name")
bot.setChatDescription(chat_id, "This is our group description")
bot.setChatPhoto(chat_id, "https://example.com/photo.jpg")
bot.deleteChatPhoto(chat_id)
bot.setChatStickerSet(chat_id, "my_sticker_set")
bot.deleteChatStickerSet(chat_id)
```

`setChatStickerSet` is for supergroups and requires the appropriate admin right.

## Invite links

### Regular links

```python
link = bot.exportInvite(target)                 # primary invite link (str)
bot.createInvite(target, **kwargs)              # create a new link
bot.editInvite(target, inviteLink, **kwargs)    # edit an existing link
bot.revokeInvite(target, inviteLink)            # revoke
```

```python
bot.createInvite(chat_id,
    name="Welcome link",
    expire_date=1700000000,
    member_limit=10,
    creates_join_request=True,
)
```

Common Telegram parameters: `name`, `expire_date`, `member_limit`,
`creates_join_request`.

### Subscription links

```python
bot.createSubscriptionInvite(
    target,
    subscriptionPeriod,   # seconds
    subscriptionPrice,    # Telegram Stars
    **kwargs,
)
bot.editSubscriptionInvite(target, inviteLink, **kwargs)
```

```python
link = bot.createSubscriptionInvite(chat_id,
    subscriptionPeriod=2592000,   # 30 days
    subscriptionPrice=100,        # 100 Stars
    name="Monthly subscription",
)
```

## Forum topics

### Topic management

```python
bot.createTopic(target, name, **kwargs)
bot.editTopic(target, messageThreadId, **kwargs)
bot.closeTopic(target, messageThreadId)
bot.reopenTopic(target, messageThreadId)
bot.deleteTopic(target, messageThreadId)
bot.unpinTopicMessages(target, messageThreadId)
```

```python
topic = bot.createTopic(chat_id, "General Discussion")
topic_id = topic.message_thread_id

bot.editTopic(chat_id, topic_id, name="New Name")
bot.closeTopic(chat_id, topic_id)
bot.reopenTopic(chat_id, topic_id)
bot.deleteTopic(chat_id, topic_id)
bot.unpinTopicMessages(chat_id, topic_id)
```

### General topic

```python
bot.editGeneralTopic(target, name)
bot.closeGeneralTopic(target)
bot.reopenGeneralTopic(target)
bot.hideGeneralTopic(target)
bot.unhideGeneralTopic(target)
bot.unpinGeneralTopicMessages(target)
```

The chat must be a forum supergroup. Topic methods require topic-management admin rights.

## Join requests

### Approve or decline

```python
bot.approveJoin(chatOrRequest, userId=None)
bot.declineJoin(chatOrRequest, userId=None)
```

```python
@bot.onJoinRequest
def on_join(rq):
    bot.approveJoin(rq)
    # or bot.declineJoin(rq)
```

With explicit IDs:

```python
bot.approveJoin(chat_id, user_id)
bot.declineJoin(chat_id, user_id)
```

### Answer a join request query

```python
bot.answerJoinRequestQuery(target, userId, queryId, result)
```

### Send a Web App to a join request

```python
bot.sendJoinRequestWebApp(target, userId, webAppUrl, **kwargs)
```

### `JoinRequest` object

| Property | Description |
| --- | --- |
| `rq.user` / `rq.fromUser` | Requesting user |
| `rq.user_id` | User ID |
| `rq.chat` | Target chat |
| `rq.chat_id` | Chat ID |
| `rq.userChatId` | User's private chat ID |
| `rq.inviteLink` | Invite link used, if any |
| `rq.date` | Unix timestamp |
| `rq.queryId` | Query ID for `answerJoinRequestQuery` |

## Admin guard pattern

Authorization should be explicit. Use a guard when every update in the bot is admin-only,
or a filter for a single route.

```python
ADMIN_IDS = {12345, 67890}

def admin_only(ctx):
    return getattr(ctx, "user_id", None) in ADMIN_IDS

@bot.guard
def global_guard(ctx):
    # Allow non-admin users to reach public routes; admin routes use their own filter.
    return True

@bot.onMessage(commands="ban", filters=[admin_only])
def ban_cmd(msg):
    if not msg.has(1):
        bot.send(msg, "Usage: /ban <user_id>")
        return
    bot.ban(msg.chat_id, msg.argInt(0))
    bot.send(msg, "Banned.")
```

Do not rely on the client or on callback text for authorization. Check `user_id` on the
server for every state-changing action.

## Common failures

| Symptom | Likely cause |
| --- | --- |
| `not enough rights` | Bot is not admin or lacks the specific right |
| `chat not found` | Wrong ID, bot not a member, or chat migrated to a supergroup |
| `user not found` | User has never interacted with the bot or ID is wrong |
| `message thread not found` | Wrong `messageThreadId` or chat is not a forum |
| Invite link fails | `member_limit`/`expire_date` combination invalid or bot lacks invite rights |
| Ban does not delete messages | `revokeMessages` not supported in that chat type |
````

## File: 06-business.md
````markdown
# 06 — Telegram Business Mode

Business Mode lets a bot act on behalf of a connected business account: read and reply to
customer chats, send media, manage the profile, gifts, Stars, and stories. Every business
update carries a **business connection ID** (`bc_id`).

Business support is first-class in Gramly: a marker scopes handlers, `BusinessMessage`
carries its own connection, and connection objects are cached.

## The `business()` marker

```python
from gramly import Gramly, business

bot = Gramly("TOKEN")
```

`business(...)` attaches a business scope to a handler. It is a **positional marker** and
must be passed first.

```python
business(bcId=None)
```

| Parameter | Type | Meaning |
| --- | --- | --- |
| `bcId` | `str \| list \| None` | Connection ID(s) to serve; omit for every connection |

```text
@bot.onMessage(business(), commands="start")           # any connection
@bot.onMessage(business(bcId="bc_1"), starts="/hi")    # one connection
@bot.onEdited(business(bcId="bc_1"))                   # edited business message
@bot.onAny(business())                                 # every business message
@bot.command(business(), "/shop")                      # business command block
```

Rules:

1. Pass the marker first, positionally.
2. `business=True` and the `business=` keyword **do not exist**. They raise `ValueError` at
   import time.
3. Passing the marker twice, or not first, raises at import time.
4. `@bot.onBusinessMessage(...)` and `@bot.onBusinessEdited()` are aliases for the common
   "any connection" case.

## Handlers

### `@bot.onBusinessMessage`

```python
@bot.onBusinessMessage(
    commands=None,
    exact=None,
    starts=None,
    ends=None,
    contains=None,
    regex=None,
    filters=None,
)
def handler(msg: BusinessMessage): ...
```

The text-matching surface is the same as `onMessage`, but the handler receives a
`BusinessMessage`.

```python
@bot.onBusinessMessage(commands="start")
def biz_start(msg):
    msg.reply("Hello! This is a business account reply.")

@bot.onBusinessMessage()
def biz_all(msg):
    conn = bot.businessConnection(msg.bc_id)   # sync handler
    if conn and conn.user and msg.user_id == conn.user.id:
        return                                  # ignore the owner's own messages
    msg.reply("Thanks for reaching out!")
```

### `@bot.onBusinessEdited`

```python
@bot.onBusinessEdited()
def handler(msg: BusinessMessage): ...
```

```python
@bot.onBusinessEdited()
def biz_edited(msg):
    print("Edited:", msg.text)
```

### `@bot.onBusinessConnection`

Fires when a connection is created, updated, enabled, or disabled.

```python
@bot.onBusinessConnection
def handler(conn: BusinessConnection): ...
```

```python
@bot.onBusinessConnection
def connected(conn):
    if conn.isEnabled:
        bot.send(conn.userChatId, "Bot connected. I will handle your business chats.")
```

The connection is cached automatically, so `bot.businessConnection(conn.id)` is cheap after
this handler runs.

### `@bot.onBusinessDeleted`

Fires when messages are deleted on the connected account's side.

```python
@bot.onBusinessDeleted
def handler(update: Obj): ...
```

```python
@bot.onBusinessDeleted
def deleted(update):
    print(f"Deleted in chat {update.chat.id}: {update.message_ids}")
```

## `BusinessMessage`

Same fields and argument helpers as `Message`, plus business-specific fields and methods.

| Property | Type | Meaning |
| --- | --- | --- |
| `msg.bc_id` / `msg.bcId` | `str \| None` | Business connection ID |
| `msg.businessConnectionId` | `str \| None` | Alias |
| `msg.text` | `str \| None` | Text or caption |
| `msg.chat_id` | `int` | Chat ID |
| `msg.message_id` | `int \| None` | Message ID |
| `msg.from_user` | `User` | Sender |
| `msg.chat` | `Chat` | Chat |
| `msg.args` | `list[str]` | Arguments / regex groups |
| `msg.match` | `re.Match \| None` | Regex match |

### Actions on the message

```python
msg.reply("Hello!")                         # threaded reply in this chat
msg.send(other_chat_id, "Hello there")      # any chat, same connection
msg.photo(other_chat_id, "photo.jpg", caption="Menu")
msg.media(other_chat_id, ["a.jpg", "b.jpg"], caption="Album")

msg.typing()                                # "typing..."
msg.typing("upload_photo")                  # any chat action
msg.read()                                  # mark up to this message as read

msg.delete()                                # delete this message
msg.delete([111, 222, 333])                 # delete specific IDs

msg.pin()                                   # pin without notification
msg.pin(notify=True)
msg.unpin()
```

Signatures:

```python
msg.reply(text, inline=None, keyboard=None, **kwargs)
msg.send(target, text, inline=None, keyboard=None, photo=None, forceReply=None, **kwargs)
msg.photo(target, photo, caption=None, inline=None, keyboard=None, **kwargs)
msg.media(target, items, caption=None, inline=None, keyboard=None, **kwargs)
msg.typing(action="typing")
msg.read()
msg.delete(messageIds=None)
msg.pin(notify=False)
msg.unpin()
```

`msg.reply()` threads properly; `msg.send()` does not thread and can target any chat.
`msg.typing()`, `msg.read()`, and `msg.delete()` call the low-level business methods for
you. `msg.reply()` and `msg.send()` go through `bot.reply()` / `bot.send()` with the
connection ID attached.

### Checking the owner

There is no `isOwner` flag. Compare the sender with the connection owner:

```python
@bot.onBusinessMessage()
def on_biz(msg):
    conn = bot.businessConnection(msg.bc_id)
    if conn and conn.user and msg.user_id == conn.user.id:
        return   # owner wrote this; do not auto-reply
```

In an async handler, `await bot.businessConnection(...)`; otherwise you get a coroutine
instead of the object.

## Low-level business methods

When you only have a connection ID and chat ID (for example, a stored order or a timer):

```python
bot.businessSend(target, text, bcId, inline=None, keyboard=None, **kwargs)
bot.businessAction(target, bcId, action="typing")
bot.businessRead(target, maxMessageId, bcId)
bot.businessDelete(target, messageIds, bcId)
```

```python
bot.businessSend(order.chat_id, "Your order shipped!", order.bc_id)
bot.businessAction(order.chat_id, order.bc_id, "upload_photo")
bot.businessRead(order.chat_id, order.message_id, order.bc_id)
bot.businessDelete(order.chat_id, [order.message_id], order.bc_id)
```

For any regular send method, pass the connection as a keyword instead of using a separate
business-specific method:

```python
bot.send(chat_id, "Hello", business_connection_id=bc_id)
bot.video(chat_id, "/tmp/demo.mp4", caption="Demo", business_connection_id=bc_id)
bot.poll(chat_id, "Coffee or tea?", ["Coffee", "Tea"], business_connection_id=bc_id)
bot.dice(chat_id, emoji="🎯", business_connection_id=bc_id)
```

`businessConnectionId=` is also accepted by `send()` / `reply()` as a camelCase alias.

There is no `businessPhoto`, `businessVideo`, `businessPoll`, or similar media wrapper
family. Use `business_connection_id` on the regular method.

## `BusinessConnection`

| Property | Type | Meaning |
| --- | --- | --- |
| `conn.id` | `str` | Connection ID |
| `conn.user` | `User` | Business account owner |
| `conn.userChatId` | `int \| None` | Owner's private chat ID |
| `conn.date` | `int` | Unix timestamp |
| `conn.isEnabled` | `bool` | Connection is active |
| `conn.canReply` | `bool` | Shorthand for `rights.can_reply` |
| `conn.rights` | `Obj \| None` | Telegram `BusinessBotRights` fields |

### `bot.businessConnection(bcId)`

```python
conn = bot.businessConnection(msg.bc_id)
if conn and conn.canReply:
    msg.reply("Hi!")
```

Results are cached; repeated calls with the same ID do not hit the API, and the cache is
refreshed by `business_connection` updates.

### Rights

`conn.rights` is an `Obj` (not a dedicated class) with fourteen optional booleans:

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

Check the relevant right before acting; a disabled or read-only connection rejects writes.

```python
r = conn.rights
if r and r.can_edit_name:
    bot.setBusinessName(conn.id, "New Name")
if r and r.can_manage_stories:
    bot.postStory(conn.id, {"type": "photo", "photo": "AgAC..."}, activePeriod=86400)
```

## Managing the connected account

These act on the owner's profile, gifts, Stars, and stories. Check the corresponding right
first.

| Method | Action |
| --- | --- |
| `bot.setBusinessName(bcId, firstName, lastName=None)` | Change the account name |
| `bot.setBusinessUsername(bcId, username=None)` | Change the username |
| `bot.setBusinessBio(bcId, bio=None)` | Change the bio |
| `bot.setBusinessPhoto(bcId, photo, isPublic=None)` | Set the profile photo |
| `bot.removeBusinessPhoto(bcId, isPublic=None)` | Remove the profile photo |
| `bot.setBusinessGiftSettings(bcId, showGiftButton, acceptedGiftTypes)` | Configure gifts |
| `bot.getBusinessStars(bcId)` | Star balance |
| `bot.transferBusinessStars(bcId, starCount)` | Transfer Stars to the bot |
| `bot.getBusinessGifts(bcId, **kwargs)` | List received gifts |
| `bot.convertBusinessGiftToStars(bcId, ownedGiftId)` | Convert a gift to Stars |
| `bot.upgradeBusinessGift(bcId, ownedGiftId, **kwargs)` | Upgrade a gift |
| `bot.transferBusinessGift(bcId, ownedGiftId, newOwnerChatId, starCount=None)` | Transfer a gift |
| `bot.postStory(bcId, content, activePeriod, **kwargs)` | Post a story |
| `bot.editStory(bcId, storyId, content, **kwargs)` | Edit a story |
| `bot.deleteStory(bcId, storyId)` | Delete a story |

```python
bot.setBusinessName(msg.bc_id, "Sunny Side Bakery")
bot.setBusinessBio(msg.bc_id, "Fresh bread, every morning.")
stars = bot.getBusinessStars(msg.bc_id)
bot.postStory(msg.bc_id, {"type": "photo", "photo": "AgAC..."}, activePeriod=86400)
```

## Full flow

```python
##  @bot.onBusinessConnection  -> account connects the bot
##            |
##  @bot.onBusinessMessage     -> customer writes to the connected account
##            |
##  msg.read() / msg.typing() / msg.reply()

@bot.onBusinessConnection
def connected(conn):
    print(f"{conn.user.first_name} connected, enabled={conn.isEnabled}")

@bot.onBusinessMessage()
def on_biz(msg):
    msg.read()
    msg.typing()

    conn = bot.businessConnection(msg.bc_id)
    if not conn or not conn.canReply:
        return
    if conn.user and msg.user_id == conn.user.id:
        return

    msg.reply(f"Hi {msg.from_user.first_name}, got your message!")
```

## Pitfalls

- Business handlers receive `BusinessMessage`, not `Message`. Do not pass it to methods that
  expect a plain message unless the method documents support for it.
- `business()` must be first; `business=True` is invalid.
- `bot.businessConnection()` returns a coroutine in async handlers; await it.
- The connection cache may be stale briefly after a rights change; handle `TelegramError`
  and re-fetch when a write is rejected.
- A connection can be connected but disabled or read-only. Check `isEnabled` and
  `canReply`/`rights`.
- Do not auto-reply to the owner's own messages; compare with `conn.user.id`.
- `BusinessMessage.delete()` without arguments deletes the current message; pass a list to
  delete specific IDs.
- Stories and profile changes require the matching right; a missing right is a Telegram
  error, not a silent no-op.
````

## File: 07-payments.md
````markdown
# 07 — Payments, Telegram Stars, and Gifts

Gramly supports Telegram Stars end to end: invoices, pre-checkout validation, successful
payments, refunds, subscriptions, gifts, Premium, and emoji status.

Currency for Stars is `"XTR"`. The minimum invoice price is **10 Stars**.

## Payment flow

```text
bot.invoice(...)            user receives the invoice
      |
      v
@bot.onCheckout             validate; pco.accept() or pco.reject("reason")
      |
      v
@bot.onPayment              payment confirmed; deliver the product
      |
      v
bot.refund(...)             optional, using msg.payment.chargeId
```

Never deliver a product in `onCheckout`; it only approves or rejects the charge. Deliver in
`onPayment`, after the charge is confirmed.

## Invoices

### `bot.invoice`

```text
bot.invoice(
    target,                     # chat ID, Message, CallbackQuery
    title: str,
    description: str,
    payload: str,               # your internal identifier, echoed back on payment
    stars: int,                 # price in Stars, minimum 10
    photoUrl: str = None,
    inline=None,
    protectContent: bool = False,
    **kwargs,
)
```

```python
bot.invoice(msg, "Digital Art", "Beautiful artwork", "order_123", stars=10)

bot.invoice(
    msg,
    "PapaCofe",
    "Arabica coffee",
    "coffee_arabica",
    stars=150,
    photoUrl="coffee-arabica.jpg",
)
```

### `bot.createInvoiceLink`

Creates a reusable invoice link without sending a message.

```text
bot.createInvoiceLink(
    title: str,
    description: str,
    payload: str,
    stars: int,
    photoUrl: str = None,
    subscriptionPeriod: int = None,   # seconds, for subscriptions
    **kwargs,
) -> str
```

```python
link = bot.createInvoiceLink(
    "Subscription",
    "Monthly subscription",
    "sub_1",
    stars=50,
    subscriptionPeriod=2592000,   # 30 days
)
bot.send(msg, f"Subscribe: {link}")
```

## Pre-checkout

### `@bot.onCheckout`

```python
@bot.onCheckout
def handler(pco: PreCheckout): ...
```

| Property | Type | Meaning |
| --- | --- | --- |
| `pco.id` | `str` | Pre-checkout query ID |
| `pco.fromUser` | `User` | Buyer |
| `pco.user_id` | `int \| None` | Buyer user ID |
| `pco.currency` | `str` | Currency code, `"XTR"` for Stars |
| `pco.totalAmount` | `int` | Amount in the smallest currency unit |
| `pco.payload` | `str` | Invoice payload |

Methods:

```python
pco.accept()              # approve; the charge proceeds
pco.reject("reason")      # reject; the reason is shown to the user
```

```python
@bot.onCheckout
def checkout(pco):
    if pco.totalAmount < 50:
        pco.reject("Minimum order is 50 Stars")
        return
    if is_banned(pco.user_id):
        pco.reject("You are banned")
        return
    pco.accept()
```

Always call exactly one of `accept()` or `reject()`. If neither is called, the payment does
not proceed.

## Successful payment

### `@bot.onPayment`

```python
@bot.onPayment
def handler(msg: Message): ...
```

`msg.payment` is a `Payment` object:

| Property | Type | Meaning |
| --- | --- | --- |
| `msg.from_user` | `User` | Buyer |
| `msg.user_id` | `int` | Buyer user ID |
| `payment.currency` | `str` | Currency code, `"XTR"` for Stars |
| `payment.totalAmount` | `int` | Amount in the smallest currency unit |
| `payment.stars` | `int \| None` | Stars amount |
| `payment.payload` | `str` | Invoice payload |
| `payment.chargeId` | `str` | Telegram charge ID; use for refunds |
| `payment.providerChargeId` | `str` | Provider charge ID |
| `payment.isRecurring` | `bool` | Recurring subscription payment |
| `payment.isFirstRecurring` | `bool` | First payment of a subscription |
| `payment.subscriptionExpiration` | `int \| None` | Expiry as a Unix timestamp |

```python
@bot.onPayment
def on_payment(msg):
    pay = msg.payment

    if pay.payload == "coffee_arabica":
        deliver_coffee(msg.user_id)
        bot.send(msg, "Arabica is on its way!")
    elif pay.payload == "vip_30d":
        grant_vip(msg.user_id, days=30)
        bot.send(msg, "VIP activated for 30 days!")
    else:
        bot.send(msg, "Payment received.")
```

### Subscriptions

```python
@bot.onPayment
def on_payment(msg):
    pay = msg.payment
    if pay.isFirstRecurring:
        bot.send(msg, "Subscription started.")
    elif pay.isRecurring:
        bot.send(msg, "Subscription renewed.")
```

Store `pay.chargeId` for later cancellation or refunds.

### Refunds

```python
refunded = bot.refund(user_id, charge_id)   # returns bool
```

```python
@bot.onPayment
def on_payment(msg):
    pay = msg.payment
    if not can_deliver(pay.payload):
        bot.refund(msg.user_id, pay.chargeId)
        bot.send(msg, "Out of stock. Refunded.")
        return
    deliver(msg.user_id, pay.payload)
```

Refund from `onPayment` only after verifying the charge. Keep a record of processed
`chargeId` values and make delivery idempotent; Telegram may retry updates.

## Gifts

### `bot.getGifts()`

Returns the gifts available for sending.

| Property | Type | Meaning |
| --- | --- | --- |
| `.id` | `str` | Gift ID for `bot.gift()` |
| `.star_count` | `int` | Cost in Stars |
| `.sticker` | `Obj` | Sticker object |
| `.total_count` | `int` | Available count |

```python
gifts = bot.getGifts()
cheapest = min(gifts, key=lambda g: g.star_count)
bot.gift(msg.user_id, cheapest.id)
```

### `bot.gift`

```python
bot.gift(userId, giftId, payForUpgrade=False, text=None)
```

```python
bot.gift(user_id, gift_id)
bot.gift(user_id, gift_id, text="Happy birthday!")
bot.gift(user_id, gift_id, payForUpgrade=True)
```

### Other gift methods

```python
bot.upgradeGift(giftId, keepOriginalDetails=False)
bot.convertGiftToStars(giftId)
bot.transferGift(giftId, userId)
```

- `upgradeGift` upgrades to a unique gift and costs Stars from the bot balance.
- `convertGiftToStars` converts a gift into Stars on the bot balance.
- `transferGift` sends a gift to another user.

## Stars

### Balance

```python
stars = bot.getStarBalance()   # int | None
```

Returns `None` on failure instead of raising.

```python
@bot.onMessage(commands="balance")
def balance(msg):
    stars = bot.getStarBalance()
    if stars is None:
        bot.send(msg, "Could not fetch the balance.")
    else:
        bot.send(msg, f"Bot balance: {stars} Stars")
```

### Transactions

```python
bot.getStarTransactions(offset=0, limit=100)
```

```python
tx = bot.getStarTransactions(limit=10)
for t in tx.transactions:
    print(t.id, t.amount, t.date)
```

### Subscriptions

```python
bot.editStarSubscription(
    userId,
    telegramPaymentChargeId,
    isCanceled,      # True to cancel, False to reactivate
)
```

```python
bot.editStarSubscription(user_id, charge_id, isCanceled=True)
```

### Premium and emoji status

```python
bot.giftPremium(userId, **kwargs)
bot.setEmojiStatus(userId, customEmojiId=None, **kwargs)
```

```python
bot.giftPremium(msg.user_id, month_count=3)

bot.setEmojiStatus(msg.user_id, "5361800828313167901")
bot.setEmojiStatus(msg.user_id)   # clear
```

`setEmojiStatus` requires the user to have granted the bot permission through Business Mode
or a Mini App.

## Payload design

Treat `payload` as your order key, not as JSON. Keep it short and stable:

```text
product:coffee_arabica
product:vip_30d
subscription:pro_monthly
```

Validate it against a server-side catalog in `onCheckout` and `onPayment`. Never trust the
client or the payload alone for price or entitlement; look up the expected price and grant
the entitlement idempotently.

## Payment checklist

- [ ] `stars >= 10`.
- [ ] `payload` identifies a server-side product.
- [ ] `onCheckout` calls exactly one of `accept()` / `reject()`.
- [ ] Delivery happens in `onPayment`, not `onCheckout`.
- [ ] `chargeId` is stored and delivery is idempotent.
- [ ] Refunds are issued with the original `chargeId`.
- [ ] Subscription cancellation stores the original charge ID.
- [ ] Errors are logged; users get a clear message.
````

## File: 08-inline-settings.md
````markdown
# 08 — Inline Queries, Bot Settings, Profile, and Stickers

## Inline queries

Inline mode lets users type `@yourbot query` in any chat and pick a result.

### Handler

```python
@bot.onInline(minLength=0)
def handler(q: InlineQuery): ...
```

`minLength` drops queries shorter than the given length.

```python
@bot.onInline(minLength=2)
def inline(q):
    results = [
        q.article("Result 1", "Message content 1", description="Subtitle"),
        q.article("Result 2", "Message content 2"),
    ]
    q.answer(results, cacheTime=10)
```

### `InlineQuery` object

| Property | Type | Meaning |
| --- | --- | --- |
| `q.id` | `str` | Inline query ID |
| `q.query` | `str` | Raw query text |
| `q.text` | `str` | Stripped query text |
| `q.from_user` | `User` | User who typed the query |
| `q.user_id` | `int \| None` | User ID |
| `q.offset` | `str` | Pagination offset |

### `q.article(...)`

Builds an article result. `**kwargs` are passed through to Telegram.

```text
q.article(
    title,                  # result title
    text,                   # message text to send
    description=None,       # subtitle
    thumbUrl=None,          # thumbnail URL
    resultId=None,          # defaults to title
    **kwargs,
) -> dict
```

### `q.answer(...)`

```python
q.answer(results, cacheTime=30, personal=True)
# equivalent to bot.answerInlineQuery(q, results, cacheTime=30, isPersonal=True)
```

### `bot.answerInlineQuery`

```text
bot.answerInlineQuery(
    query,                  # InlineQuery, dict with "id", or query ID string
    results: list,
    cacheTime: int = 30,
    isPersonal: bool = True,
    nextOffset: str = "",
)
```

```python
@bot.onInline()
def inline(q):
    bot.answerInlineQuery(q, [
        {
            "type": "article",
            "id": "1",
            "title": "Result",
            "input_message_content": {"message_text": "Hi!"},
        },
    ])
```

### Web App queries

```python
bot.answerWebAppQuery(webAppQueryId, result)
```

### Guest queries

```python
bot.answerGuestQuery(queryId, text, parseMode=None, **kwargs)
```

`@bot.onGuest` receives a `GuestQuery`; `q.answer(text, parseMode=None, **kwargs)` is a
shortcut.

```python
@bot.onGuest
def guest(q):
    q.answer(f"Hello {q.fromUser.first_name}!")
```

### Shipping queries

```python
bot.answerShippingQuery(shippingQueryId, ok, **kwargs)
```

```python
bot.answerShippingQuery(query_id, True, shipping_options=[...])
bot.answerShippingQuery(query_id, False, error_message="We do not ship there.")
```

### Prepared messages and buttons

```python
bot.savePreparedInlineMessage(
    userId,
    result,
    allowUserChats=None,
    allowBotChats=None,
    allowGroupChats=None,
    allowChannelChats=None,
)

bot.savePreparedKeyboardButton(
    text,
    requestUser=None,
    requestChat=None,
    requestManagedBot=None,
    webApp=None,
    loginUrl=None,
    switchInline=None,
    switchInlineCurrent=None,
    switchInlineChosen=None,
    copyText=None,
    pay=None,
)
```

```python
bot.savePreparedKeyboardButton("Open App", webApp={"url": "https://example.com"})
bot.savePreparedKeyboardButton("Search", switchInline="")
```

## Bot settings

### Basic information

```python
bot.getMe()
bot.getFile(fileId)
bot.getWebhookInfo()
```

```python
me = bot.getMe()
print(me.username, me.id)

f = bot.getFile(file_id)
print(f.file_path)

info = bot.getWebhookInfo()
print(info.url, info.pending_update_count)
```

### Commands

```python
bot.setMyCommands(commands, scope=None, languageCode=None)
bot.getMyCommands(scope=None, languageCode=None)
bot.deleteMyCommands(scope=None, languageCode=None)
```

```python
bot.setMyCommands([
    {"command": "start", "description": "Start the bot"},
    {"command": "help", "description": "Show help"},
])
```

### Name and descriptions

Each setter/getter accepts an optional `languageCode`.

```python
bot.setMyName(name, languageCode=None)
bot.getMyName(languageCode=None)

bot.setMyDescription(description, languageCode=None)
bot.getMyDescription(languageCode=None)

bot.setMyShortDescription(shortDescription, languageCode=None)
bot.getMyShortDescription(languageCode=None)
```

```python
bot.setMyName("My Bot")
bot.setMyDescription("Full description shown on the profile page.")
bot.setMyShortDescription("One-liner shown in chat lists and forwards.")
```

### Profile photo

```python
bot.setMyProfilePhoto(photo)
bot.removeMyProfilePhoto(photoId=None)
```

```python
bot.setMyProfilePhoto(open("logo.png", "rb"))
bot.removeMyProfilePhoto()
```

`photoId` is sent as `custom_emoji_id` under the hood; omit it for normal removal.

### Menu button

```python
bot.setMenuButton(target=None, menuButton=None)
bot.getMenuButton(target=None)
```

```python
bot.setMenuButton(menuButton={"type": "commands"})   # default for all private chats
bot.setMenuButton(chat_id, {
    "type": "web_app",
    "text": "Open",
    "web_app": {"url": "https://example.com"},
})
```

Omit `target` to set the default for all private chats.

### Default admin rights

```python
bot.setDefaultAdminRights(rights=None, forChannels=False)
bot.getDefaultAdminRights(forChannels=False)
```

```python
bot.setDefaultAdminRights({"can_manage_chat": True, "can_delete_messages": True})
bot.setDefaultAdminRights({"can_post_messages": True}, forChannels=True)
```

### Advanced

```python
bot.logOut()      # log out from the Bot API server
bot.closeBot()    # close the bot instance before moving servers
```

### Managed bot access

For Telegram's Managed Bots feature (Bot API 9.6+). A user connects or creates a bot with a
`managedBotRequest()` button; `@bot.onManaged` receives a `ManagedBot` whose `.token()`
wraps `getManagedToken`.

```python
bot.getAccessSettings()
bot.setAccessSettings(settings)       # settings: dict
bot.getManagedToken(userId)           # userId is the managed bot's own ID
bot.replaceManagedToken(userId)       # rotate the token
```

```python
current = bot.getAccessSettings()
bot.setAccessSettings({**current, "can_read_messages": True})

token = bot.getManagedToken(managed_bot_id)
```

`ManagedBot` properties: `.creator`, `.bot`, `.botId`, plus `.token()` and
`.replaceToken()`.

## User profile

```python
bot.getUserPhotos(userId, offset=0, limit=100)
bot.getUserAudios(userId, offset=0, limit=100)
bot.getPersonalMessages(userId, **kwargs)
bot.setEmojiStatus(userId, customEmojiId=None, **kwargs)
```

```python
photos = bot.getUserPhotos(msg.user_id, limit=10)
print(photos.total_count)
```

`getPersonalMessages` returns messages a user sent to the bot directly, outside a chat
context; it is used with Business Mode connections that expose personal history.

```python
bot.setEmojiStatus(msg.user_id, "5361800828313167901")
bot.setEmojiStatus(msg.user_id)   # clear
```

## Sticker sets

### Reading

```python
bot.getStickerSet(name)                  # by short name
bot.getCustomEmojiStickers(customEmojiIds)
```

```python
sset = bot.getStickerSet("animals_by_mybot")
print(sset.title, len(sset.stickers))
```

### Creating and extending

```python
uploaded = bot.uploadStickerFile(userId, sticker, stickerFormat)   # returns File
bot.createNewStickerSet(userId, name, title, stickers, **kwargs)
bot.addStickerToSet(userId, name, sticker)
```

`stickerFormat`: `"static"` (.WEBP/.PNG), `"animated"` (.TGS), or `"video"` (.WEBM).

A sticker item is a raw dict:

```python
{
    "sticker": file_id,          # from uploadStickerFile, or a file/bytes/path
    "format": "static",          # "static" | "animated" | "video"
    "emoji_list": ["🐱", "😺"],   # 1–20 emoji
    "keywords": ["cat"],         # optional
    "mask_position": {...},      # optional, mask sets only
}
```

```python
uploaded = bot.uploadStickerFile(user_id, open("cat.png", "rb"), "static")

bot.createNewStickerSet(user_id, "cats_by_mybot", "Cats", [
    {"sticker": uploaded.file_id, "format": "static", "emoji_list": ["🐱"]},
])

bot.addStickerToSet(user_id, "cats_by_mybot", {
    "sticker": file_id,
    "format": "static",
    "emoji_list": ["😸"],
})
```

Requirements:

- `name` must end in `_by_<bot_username>` and contain only letters, digits, and
  underscores.
- `title` is 1–64 characters.
- A new set accepts 1–50 items.
- The owner must have interacted with the bot before.

### Editing individual stickers

These target a sticker by `file_id`, not by set name.

```python
bot.setStickerPosition(sticker, position)
bot.deleteStickerFromSet(sticker)
bot.replaceStickerInSet(userId, name, oldSticker, sticker)
bot.setStickerEmojiList(sticker, emojiList)
bot.setStickerKeywords(sticker, keywords)
bot.setStickerMaskPosition(sticker, maskPosition)
```

```python
bot.setStickerPosition(file_id, 0)
bot.setStickerEmojiList(file_id, ["🐱", "😸", "😻"])
bot.deleteStickerFromSet(file_id)
```

### Editing the set

```python
bot.setStickerSetTitle(name, title)
bot.setStickerSetThumbnail(name, userId, thumbnail=None)
bot.setCustomEmojiStickerSetThumbnail(name, customEmojiId=None)
bot.deleteStickerSet(name)
```

```python
bot.setStickerSetTitle("cats_by_mybot", "Cats v2")
bot.setStickerSetThumbnail("cats_by_mybot", user_id, thumbnail=file_id)
```

### Chat sticker set

```python
bot.setChatStickerSet(target, stickerSetName)
bot.deleteChatStickerSet(target)
```

Sets the sticker set shown in a supergroup header. Requires the appropriate admin right.
````

## File: 09-objects.md
````markdown
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
````

## File: 10-patterns.md
````markdown
# 10 — Patterns, Anti-Patterns, and Operations

Canonical ways to assemble Gramly features. Each pattern is complete enough to adapt.

## 1. Start a bot safely

```python
import os
from gramly import Gramly, setupLogging

setupLogging(debug=os.getenv("DEBUG") == "1")

bot = Gramly(
    os.environ["BOT_TOKEN"],
    parseMode="HTML",
)

@bot.onMessage(commands="start")
def start(msg):
    bot.send(msg, f"Hello, {msg.from_user.first_name}!")

if __name__ == "__main__":
    bot.run(skipPending=True)
```

- Token from the environment, never a literal.
- `skipPending=True` avoids replying to messages queued while the bot was offline.
- `setupLogging` or `debug=True` for diagnostics.

## 2. Menu with owner-checked callbacks

```python
from gramly import Gramly, btn, row, kbd

bot = Gramly("TOKEN")

def is_owner(q):
    return q.cb.get(0, int) == q.user_id

def menu(uid):
    return kbd(
        row(btn("Profile", action=f"profile:{uid}")),
        row(btn("Settings", action=f"settings:{uid}")),
    )

@bot.onMessage(commands="menu")
def show_menu(msg):
    bot.send(msg, "Menu:", inline=menu(msg.user_id))

@bot.onCallback("profile:", filters=[is_owner])
def profile(q):
    bot.edit(q, "Your profile", inline=kbd(
        row(btn("Back", action=f"menu:{q.user_id}")),
    ))

@bot.onCallback("settings:", filters=[is_owner])
def settings(q):
    bot.edit(q, "Settings", inline=kbd(
        row(btn("Back", action=f"menu:{q.user_id}")),
    ))

@bot.onCallback("menu:", filters=[is_owner])
def back(q):
    bot.edit(q, "Menu:", inline=menu(q.user_id))

bot.run()
```

Why the owner check matters: callback data is visible to the client and can be replayed by
another user. Always compare the embedded user ID with `q.user_id` before acting.

## 3. Multi-step form with explicit state

Gramly has no FSM. Use a dict or a database and clear it on completion.

```python
import threading
from gramly import Gramly

bot = Gramly("TOKEN")

_lock = threading.Lock()
_state = {}   # (chat_id, user_id) -> {"step": str, "data": dict}

def key(msg):
    return (msg.chat_id, msg.user_id)

@bot.onMessage(commands="signup")
def signup(msg):
    with _lock:
        _state[key(msg)] = {"step": "name", "data": {}}
    bot.send(msg, "What is your name?")

@bot.onMessage()
def collect(msg):
    k = key(msg)
    with _lock:
        current = _state.get(k)
    if not current:
        return

    if current["step"] == "name":
        with _lock:
            current["data"]["name"] = msg.text
            current["step"] = "email"
        bot.send(msg, "What is your email?")

    elif current["step"] == "email":
        with _lock:
            current["data"]["email"] = msg.text
            _state.pop(k, None)
        bot.send(msg, f"Thanks, {current['data']['name']}! Signed up.")
```

For production, replace the dict with a database keyed by `(chat_id, user_id)`. If handlers
are async, use an async-safe store instead of `threading.Lock`.

## 4. `CommandBlock` for a command with sub-routes

```python
from gramly import Gramly, btn, row, kbd

bot = Gramly("TOKEN")

@bot.command("calc")
def calc(cmd):

    @cmd.default
    def usage(msg):
        bot.send(msg, "Usage: /calc add 5 3")

    @cmd.on(regex=r"(add|sub|mul|div) (\d+) (\d+)")
    def compute(msg):
        op, a, b = msg.args[0], int(msg.args[1]), int(msg.args[2])
        result = {
            "add": a + b,
            "sub": a - b,
            "mul": a * b,
            "div": a // b if b else 0,
        }[op]
        bot.send(msg, f"{a} {op} {b} = {result}")

bot.run()
```

Use `onMessage` for flat commands. Use `CommandBlock` when one command owns a menu, text
sub-routes, and callback actions.

## 5. Admin-only routes

```python
ADMIN_IDS = {12345, 67890}

def admin_only(ctx):
    return getattr(ctx, "user_id", None) in ADMIN_IDS

@bot.onMessage(commands="stats", filters=[admin_only])
def stats(msg):
    bot.send(msg, "Admin stats")
```

For a bot that is entirely private, register a global guard:

```python
@bot.guard
def private_only(ctx):
    return getattr(ctx, "user_id", None) in ADMIN_IDS
```

A guard that returns `False` drops the update silently. If the user needs feedback, use a
handler filter and send a denial message instead.

## 6. Pagination with callback data

```python
PAGE_SIZE = 10

def page_kb(uid, page, total_pages):
    buttons = []
    if page > 0:
        buttons.append(btn("Prev", action=f"page:{uid}:{page - 1}"))
    if page < total_pages - 1:
        buttons.append(btn("Next", action=f"page:{uid}:{page + 1}"))
    return kbd(row(*buttons)) if buttons else None

@bot.onMessage(commands="list")
def show_list(msg):
    items = get_items()
    page = 0
    chunk = items[:PAGE_SIZE]
    bot.send(msg, "\n".join(chunk), inline=page_kb(msg.user_id, page, 1))

@bot.onCallback("page:")
def change_page(q):
    uid = q.cb.get(0, int)
    page = q.cb.get(1, int)
    if uid != q.user_id:
        q.alert("Not your list.", popup=True)
        return

    items = get_items()
    total_pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    chunk = items[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    bot.edit(q, "\n".join(chunk), inline=page_kb(uid, page, total_pages))
```

Keep pagination state in the callback data (small integers) rather than in memory when
possible.

## 7. Timer

```python
def tick():
    bot.send(CHAT_ID, "Tick")

handle = bot.timer(60, tick)             # every 60 seconds
handle_now = bot.timer(300, backup, fireNow=True)
handle.stop()
```

Timers run in the background and integrate with the bot's event loop. `bot.*` calls are safe
inside a timer. Store the handle if you need to stop it later.

## 8. Webhook with FastAPI

```python
import os
from fastapi import FastAPI, Request
from gramly import Gramly

bot = Gramly(os.environ["BOT_TOKEN"])
app = FastAPI()

# Register once, for example during deployment:
# bot.setWebhook("https://example.com/webhook", secretToken=os.environ["WEBHOOK_SECRET"])

@app.post("/webhook")
async def webhook(request: Request):
    update = await request.json()
    bot.processUpdate(update)
    return {"ok": True}

@bot.onMessage(commands="start")
def start(msg):
    bot.send(msg, "Hello from a webhook bot")
```

Do not run `bot.run()` in webhook mode. Process updates through `processUpdate`. Verify the
secret token at the edge if your framework supports it.

## 9. Error handling and idempotency

```python
from gramly import TelegramError

@bot.onPayment
def payment(msg):
    pay = msg.payment
    if already_delivered(pay.chargeId):
        return
    try:
        deliver(msg.user_id, pay.payload)
        mark_delivered(pay.chargeId)
        bot.send(msg, "Delivered.")
    except TelegramError as e:
        log.error("delivery failed: %s (%s)", e.description, e.errorCode)
        bot.send(msg, "Delivery failed. Support has been notified.")
```

- Record the charge ID before or immediately after delivery; make the operation idempotent.
- Do not swallow exceptions silently. Log `description`, `errorCode`, and context.
- Gramly retries `retryAfter` up to three times. Do not add unbounded retries.

## 10. Sending files

```python
bot.photo(msg, "https://example.com/image.jpg", caption="URL")
bot.document(msg, open("report.pdf", "rb"), caption="Report")
bot.media(msg, ["/tmp/a.jpg", "/tmp/b.png", "/tmp/clip.mp4"], caption="Album")
```

Use file IDs for repeat sends. File IDs are stable per bot and avoid re-uploading. Close
file objects after the call if you opened them manually.

## 11. Testing and verification

Gramly has no bundled test harness. Verify in layers:

```bash
python -m py_compile bot.py
python -c "import gramly; print(gramly.__version__)"
python -c "from gramly import Gramly; help(Gramly.onMessage)"
```

- Unit-test pure business logic separately from handlers.
- Test handlers against a dedicated test bot token, not production.
- Use `skipPending=True` while developing to avoid replaying old updates.
- For webhook code, send a synthetic update with `bot.processUpdate({...})` in a local
  script once the bot loop is available.
- Add a smoke test: start the bot, send `/start`, press one callback, stop.

## 12. Deployment checklist

- [ ] Token and secrets come from the environment.
- [ ] One bot instance per token; no duplicate polling and webhook at the same time.
- [ ] `skipPending=True` on restart if old commands should not replay.
- [ ] Webhook URL uses HTTPS and a secret token.
- [ ] Logging is configured and does not print the token.
- [ ] Long tasks are outside the event loop or in a worker.
- [ ] State is in a database, not in module globals, if it must survive restarts.
- [ ] Timers are stopped on shutdown (`@bot.onStop`).
- [ ] Error paths send a user-facing message and log the exception.
- [ ] Rate limits and cooldowns are appropriate for the expected traffic.

## Anti-patterns

| Wrong | Right |
| --- | --- |
| `@bot.onMessage(business=True, ...)` | `@bot.onMessage(business(), ...)` |
| `@bot.command("start")` with `def start(msg)` | `@bot.onMessage(commands="start")` |
| `@bot.onPayment()` | `@bot.onPayment` |
| `bot.send(...)` then `await` in a sync handler | `bot.send(...)` only |
| `bot.send(...)` without `await` in async code | `await bot.send(...)` |
| `msg.args[0]` without a check | `msg.has(1)` then `msg.arg(0)` |
| `args_min=1` | `if not msg.has(1): ...` |
| `argsJoined()` | `argsFrom()` |
| Raw inline dict with `callback_data` | `btn("...", action="action:args")` |
| Callback data as JSON | Compact `action:args` under 64 bytes |
| Trusting `q.data` for authorization | Compare `q.user_id` with the owner ID |
| `businessPhoto(...)` | `bot.photo(..., business_connection_id=bc_id)` |
| Blocking `requests` inside `async def` | Plain handler or `asyncio.to_thread` |
| A global `bot` plus a second `Gramly(...)` per request | One instance per process |
| Catching every exception and ignoring it | Log and handle specific failures |

## When the API is unclear

1. Search [`11-api-index.md`](11-api-index.md).
2. Inspect the installed package:

```bash
python -c "import inspect; from gramly import Gramly; print(inspect.signature(Gramly.send))"
```

3. Read the official documentation: <https://gramly.gitbook.io/gramly-docs>.
4. If the method is still unclear, state the uncertainty and use the closest documented
   method. Never invent an API.
````

## File: 11-api-index.md
````markdown
# 11 — Complete API Index

Every public method on `Gramly`, plus module-level builders. Signatures are the current
1.4.x surface. `**kwargs` are passed through to Telegram and are not expanded here.

Use this page to confirm that a method exists before writing code. If a name is absent, it
is not part of the public API.

Decorator arity matters: signatures shown as `fn` are bare decorators (`@bot.onPayment`);
signatures with a parameter list are factories and must be called (`@bot.onMessage(...)`,
`@bot.onPost()`, `@bot.onAny()`, `@bot.onEdited()`). In particular, `onPost` has no
configuration parameters but still requires parentheses.

## Alphabetical methods

| Method | Signature | Purpose |
| --- | --- | --- |
| `ack` | `ack(call)` | Acknowledge a callback silently |
| `action` | `action(target, action="typing")` | Send a chat action |
| `addStickerToSet` | `addStickerToSet(userId, name, sticker)` | Add one sticker to a set |
| `alert` | `alert(call, text="", popup=False)` | Toast or popup for a callback |
| `animation` | `animation(target, animation, caption=None, **kwargs)` | Send a GIF/animation |
| `answerGuestQuery` | `answerGuestQuery(queryId, text, parseMode=None, **kwargs)` | Answer a guest query |
| `answerInlineQuery` | `answerInlineQuery(query, results, cacheTime=30, isPersonal=True, nextOffset="")` | Answer an inline query |
| `answerJoinRequestQuery` | `answerJoinRequestQuery(target, userId, queryId, result)` | Answer a join request query |
| `answerShippingQuery` | `answerShippingQuery(shippingQueryId, ok, **kwargs)` | Answer a shipping query |
| `answerWebAppQuery` | `answerWebAppQuery(webAppQueryId, result)` | Answer a Web App query |
| `approveJoin` | `approveJoin(target, userId=None)` | Approve a join request |
| `audio` | `audio(target, audio, caption=None, inline=None, keyboard=None, **kwargs)` | Send audio |
| `ban` | `ban(target, userId, until=0, revokeMessages=False)` | Ban a user |
| `banSender` | `banSender(target, senderChatId)` | Ban a sender channel |
| `businessAction` | `businessAction(target, bcId, action="typing")` | Chat action as a business account |
| `businessConnection` | `businessConnection(bcId)` | Fetch/cached business connection |
| `businessDelete` | `businessDelete(target, messageIds, bcId)` | Delete business messages |
| `businessRead` | `businessRead(target, maxMessageId, bcId)` | Mark business messages read |
| `businessSend` | `businessSend(target, text, bcId, inline=None, keyboard=None, **kwargs)` | Send as a business account |
| `checklist` | `checklist(target, title, tasks, **kwargs)` | Send a checklist |
| `close` | `close()` | Stop the running bot |
| `closeBot` | `closeBot()` | Close the bot instance |
| `closeGeneralTopic` | `closeGeneralTopic(target)` | Close the general topic |
| `closeTopic` | `closeTopic(target, messageThreadId)` | Close a forum topic |
| `command` | `command(*triggers, withSlash=True, withoutSlash=True, filters=None, starts=None, ends=None)` | Register a `CommandBlock` |
| `contact` | `contact(target, phone, firstName, lastName=None, **kwargs)` | Send a contact |
| `convertBusinessGiftToStars` | `convertBusinessGiftToStars(bcId, ownedGiftId)` | Convert a business gift |
| `convertGiftToStars` | `convertGiftToStars(giftId)` | Convert a gift to Stars |
| `copy` | `copy(target, message, **kwargs)` | Copy one message |
| `copyMessages` | `copyMessages(target, fromChatId, messageIds, **kwargs)` | Copy multiple messages |
| `createInvite` | `createInvite(target, **kwargs)` | Create an invite link |
| `createInvoiceLink` | `createInvoiceLink(title, description, payload, stars, photoUrl=None, subscriptionPeriod=None, **kwargs) -> str` | Create an invoice link |
| `createNewStickerSet` | `createNewStickerSet(userId, name, title, stickers, **kwargs)` | Create a sticker set |
| `createSubscriptionInvite` | `createSubscriptionInvite(target, subscriptionPeriod, subscriptionPrice, **kwargs)` | Create a subscription invite |
| `createTopic` | `createTopic(target, name, **kwargs)` | Create a forum topic |
| `declineJoin` | `declineJoin(target, userId=None)` | Decline a join request |
| `delete` | `delete(target, messageId=None, bcId=None) -> bool` | Delete one or more messages |
| `deleteChatPhoto` | `deleteChatPhoto(target)` | Remove a chat photo |
| `deleteChatStickerSet` | `deleteChatStickerSet(target)` | Remove a chat sticker set |
| `deleteLater` | `deleteLater(message, delay, messageId=None, bcId=None)` | Delete after a delay |
| `deleteMessage` | `deleteMessage(target, messageId, bcId=None) -> bool` | Delete one message |
| `deleteMessages` | `deleteMessages(target, messageIds, bcId=None) -> bool` | Delete multiple messages |
| `deleteMyCommands` | `deleteMyCommands(scope=None, languageCode=None)` | Delete bot commands |
| `deleteStickerFromSet` | `deleteStickerFromSet(sticker)` | Remove a sticker |
| `deleteStickerSet` | `deleteStickerSet(name)` | Delete a sticker set |
| `deleteStory` | `deleteStory(bcId, storyId)` | Delete a business story |
| `deleteTopic` | `deleteTopic(target, messageThreadId)` | Delete a topic |
| `deleteWebhook` | `deleteWebhook(dropPending=False)` | Remove the webhook |
| `dice` | `dice(target, emoji="🎲", **kwargs)` | Send a dice |
| `document` | `document(target, doc, caption=None, inline=None, keyboard=None, **kwargs)` | Send a document |
| `edit` | `edit(call, text, inline=None, photo=None, showCaption=None, **kwargs)` | Edit text/caption/media |
| `editChecklist` | `editChecklist(target, messageId, title, tasks, **kwargs)` | Edit a checklist |
| `editGeneralTopic` | `editGeneralTopic(target, name)` | Rename the general topic |
| `editInvite` | `editInvite(target, inviteLink, **kwargs)` | Edit an invite link |
| `editLiveLocation` | `editLiveLocation(call, latitude, longitude, inline=None, **kwargs)` | Update a live location |
| `editMarkup` | `editMarkup(call, inline=None)` | Edit only the inline keyboard |
| `editStarSubscription` | `editStarSubscription(userId, telegramPaymentChargeId, isCanceled)` | Cancel/reactivate a subscription |
| `editStory` | `editStory(bcId, storyId, content, **kwargs)` | Edit a business story |
| `editSubscriptionInvite` | `editSubscriptionInvite(target, inviteLink, **kwargs)` | Edit a subscription invite |
| `editTopic` | `editTopic(target, messageThreadId, **kwargs)` | Edit a topic |
| `ephemeral` | `ephemeral(target, text, to=None, keyboard=None, inline=None, photo=None, replaceCallbackMessage=None, **kwargs)` | Group-only ephemeral message |
| `exportInvite` | `exportInvite(target) -> str` | Get the primary invite link |
| `forward` | `forward(target, message)` | Forward one message |
| `forwardMessages` | `forwardMessages(target, fromChatId, messageIds, **kwargs)` | Forward multiple messages |
| `game` | `game(target, gameShortName, inline=None, keyboard=None, **kwargs)` | Send a game |
| `getAccessSettings` | `getAccessSettings()` | Get managed-bot access settings |
| `getAdmins` | `getAdmins(target, includeBots=False) -> list` | List chat admins |
| `getBusinessGifts` | `getBusinessGifts(bcId, **kwargs)` | List business gifts |
| `getBusinessStars` | `getBusinessStars(bcId)` | Business Star balance |
| `getChat` | `getChat(target)` | Get chat info |
| `getChatMember` | `getChatMember(target, userId)` | Get one member |
| `getChatMemberCount` | `getChatMemberCount(target) -> int` | Member count |
| `getCustomEmojiStickers` | `getCustomEmojiStickers(customEmojiIds)` | Stickers for custom emoji |
| `getDefaultAdminRights` | `getDefaultAdminRights(forChannels=False)` | Default admin rights |
| `getFile` | `getFile(fileId)` | Resolve a file |
| `getGifts` | `getGifts()` | List available gifts |
| `getManagedToken` | `getManagedToken(userId)` | Fetch a managed bot token |
| `getMe` | `getMe()` | Bot identity |
| `getMenuButton` | `getMenuButton(target=None)` | Get the menu button |
| `getMyCommands` | `getMyCommands(scope=None, languageCode=None)` | Get bot commands |
| `getMyDescription` | `getMyDescription(languageCode=None)` | Get the description |
| `getMyName` | `getMyName(languageCode=None)` | Get the bot name |
| `getMyShortDescription` | `getMyShortDescription(languageCode=None)` | Get the short description |
| `getPersonalMessages` | `getPersonalMessages(userId, **kwargs)` | Personal messages (Business) |
| `getStarBalance` | `getStarBalance()` | Star balance or `None` |
| `getStarTransactions` | `getStarTransactions(offset=0, limit=100)` | Star transactions |
| `getStickerSet` | `getStickerSet(name)` | Get a sticker set |
| `getUserAudios` | `getUserAudios(userId, offset=0, limit=100)` | User audio files |
| `getUserBoosts` | `getUserBoosts(target, userId)` | User boosts |
| `getUserPhotos` | `getUserPhotos(userId, offset=0, limit=100)` | User profile photos |
| `getWebhookInfo` | `getWebhookInfo()` | Webhook status |
| `gift` | `gift(userId, giftId, payForUpgrade=False, **kwargs)` | Send a gift |
| `giftPremium` | `giftPremium(userId, **kwargs)` | Gift Telegram Premium |
| `guard` | `guard(fn)` | Register a global guard |
| `hideGeneralTopic` | `hideGeneralTopic(target)` | Hide the general topic |
| `intercept` | `intercept(fn)` | Register a raw-update interceptor |
| `invoice` | `invoice(target, title, description, payload, stars, photoUrl=None, inline=None, protectContent=False, **kwargs)` | Send a Stars invoice |
| `isAdmin` | `isAdmin(target, userId) -> bool` | Check admin status |
| `kick` | `kick(target, userId)` | Kick a user |
| `leave` | `leave(target)` | Leave a chat |
| `livePhoto` | `livePhoto(target, photo, animation, caption=None, inline=None, keyboard=None, **kwargs)` | Send a live photo |
| `location` | `location(target, latitude, longitude, **kwargs)` | Send a location |
| `logOut` | `logOut()` | Log out from the API server |
| `media` | `media(target, items, caption=None, inline=None, keyboard=None, **kwargs)` | Send a mixed album |
| `messageDraft` | `messageDraft(target, draftId, text="", inline=None, keyboard=None, canStop=None, keepOnStop=None, **kwargs)` | Send a draft |
| `mute` | `mute(target, userId, until=0)` | Mute a user |
| `onAny` | `onAny(*businessMarker, filters=None)` | Catch-all message handler |
| `onBoost` | `onBoost(fn)` | Chat boost handler |
| `onBusinessConnection` | `onBusinessConnection(fn)` | Business connection handler |
| `onBusinessDeleted` | `onBusinessDeleted(fn, *businessMarker)` | Business deletion handler |
| `onBusinessEdited` | `onBusinessEdited()` | Business edit handler |
| `onBusinessMessage` | `onBusinessMessage(commands=None, **kw)` | Business message handler |
| `onCallback` | `onCallback(*prefixes, filters=None)` | Callback handler |
| `onChatMember` | `onChatMember(fn)` | Member change handler |
| `onCheckout` | `onCheckout(fn)` | Pre-checkout handler |
| `onEdited` | `onEdited(*businessMarker)` | Edited message handler |
| `onGenerationStopped` | `onGenerationStopped(fn)` | Draft stopped handler |
| `onGuest` | `onGuest(fn)` | Guest query handler |
| `onInline` | `onInline(minLength=0)` | Inline query handler |
| `onJoinRequest` | `onJoinRequest(fn)` | Join request handler |
| `onManaged` | `onManaged(fn)` | Managed bot handler |
| `onMedia` | `onMedia(*contentTypes)` | Media handler |
| `onMessage` | `onMessage(commands=None, exact=None, starts=None, ends=None, contains=None, regex=None, withSlash=True, withoutSlash=True, filters=None)` | Text/command handler |
| `onMyStatus` | `onMyStatus(fn)` | Bot status handler |
| `onPaidMedia` | `onPaidMedia(fn)` | Paid media handler |
| `onPayment` | `onPayment(fn)` | Successful payment handler |
| `onPoll` | `onPoll(fn)` | Poll answer handler |
| `onPost` | `onPost()` | Channel post handler |
| `onReaction` | `onReaction(fn)` | Reaction handler |
| `onStop` | `onStop(fn)` | Shutdown handler |
| `onWebApp` | `onWebApp(fn)` | Web App data handler |
| `paidMedia` | `paidMedia(target, starCount, media, **kwargs)` | Send paid media |
| `photo` | `photo(target, photo, caption=None, inline=None, keyboard=None, **kwargs)` | Send photos |
| `pin` | `pin(message, notify=False)` | Pin a message |
| `poll` | `poll(target, question, options, isAnonymous=True, pollType="regular", correctOptionIds=None, explanation=None, allowsMultipleAnswers=False, allowsRevoting=None, shuffleOptions=None, allowAddingOptions=None, hideResultsUntilCloses=None, description=None, openPeriod=None, closeDate=None, membersOnly=None, countryCodes=None, **kwargs)` | Send a poll |
| `postStory` | `postStory(bcId, content, activePeriod, **kwargs)` | Post a business story |
| `processUpdate` | `processUpdate(update)` | Dispatch a raw update |
| `promote` | `promote(target, userId, **permissions)` | Promote an admin |
| `react` | `react(msg, *emojis, isBig=False)` | Set/remove reactions |
| `refund` | `refund(userId, chargeId) -> bool` | Refund a Stars payment |
| `removeBusinessPhoto` | `removeBusinessPhoto(bcId, isPublic=None)` | Remove business photo |
| `removeMyProfilePhoto` | `removeMyProfilePhoto(photoId=None)` | Remove bot photo |
| `reopenGeneralTopic` | `reopenGeneralTopic(target)` | Reopen the general topic |
| `reopenTopic` | `reopenTopic(target, messageThreadId)` | Reopen a topic |
| `replace` | `replace(call, text, inline=None, photo=None, **kwargs)` | Replace a message |
| `replaceManagedToken` | `replaceManagedToken(userId)` | Rotate a managed bot token |
| `replaceStickerInSet` | `replaceStickerInSet(userId, name, oldSticker, sticker)` | Replace a sticker |
| `reply` | `reply(message, text, keyboard=None, inline=None, photo=None, forceReply=None, businessConnectionId=None, **kwargs)` | Threaded reply |
| `restrict` | `restrict(target, userId, permissions, until=0)` | Apply permissions |
| `revokeInvite` | `revokeInvite(target, inviteLink)` | Revoke an invite |
| `run` | `run(skipPending=False, pollTimeout=20, allowedUpdates=None)` | Start long polling |
| `savePreparedInlineMessage` | `savePreparedInlineMessage(userId, result, allowUserChats=None, allowBotChats=None, allowGroupChats=None, allowChannelChats=None)` | Save a prepared result |
| `savePreparedKeyboardButton` | `savePreparedKeyboardButton(text, requestUser=None, requestChat=None, requestManagedBot=None, webApp=None, loginUrl=None, switchInline=None, switchInlineCurrent=None, switchInlineChosen=None, copyText=None, pay=None)` | Save a prepared button |
| `send` | `send(target, text, inline=None, keyboard=None, photo=None, forceReply=None, businessConnectionId=None, **kwargs)` | Send a message |
| `sendJoinRequestWebApp` | `sendJoinRequestWebApp(target, userId, webAppUrl, **kwargs)` | Web App for a join request |
| `setAccessSettings` | `setAccessSettings(settings)` | Set managed-bot access |
| `setAdminTitle` | `setAdminTitle(target, userId, title)` | Set an admin title |
| `setBusinessBio` | `setBusinessBio(bcId, bio=None)` | Set business bio |
| `setBusinessGiftSettings` | `setBusinessGiftSettings(bcId, showGiftButton, acceptedGiftTypes)` | Gift settings |
| `setBusinessName` | `setBusinessName(bcId, firstName, lastName=None)` | Set business name |
| `setBusinessPhoto` | `setBusinessPhoto(bcId, photo, isPublic=None)` | Set business photo |
| `setBusinessUsername` | `setBusinessUsername(bcId, username=None)` | Set business username |
| `setChatDescription` | `setChatDescription(target, description)` | Set chat description |
| `setChatPermissions` | `setChatPermissions(target, permissions)` | Default permissions |
| `setChatPhoto` | `setChatPhoto(target, photo)` | Set chat photo |
| `setChatStickerSet` | `setChatStickerSet(target, stickerSetName)` | Set chat sticker set |
| `setChatTitle` | `setChatTitle(target, title)` | Set chat title |
| `setCustomEmojiStickerSetThumbnail` | `setCustomEmojiStickerSetThumbnail(name, customEmojiId=None)` | Custom emoji thumbnail |
| `setDefaultAdminRights` | `setDefaultAdminRights(rights=None, forChannels=False)` | Default admin rights |
| `setEmojiStatus` | `setEmojiStatus(userId, customEmojiId=None, **kwargs) -> bool` | Set/clear emoji status |
| `setMemberTag` | `setMemberTag(target, userId, tag)` | Set a member tag |
| `setMenuButton` | `setMenuButton(target=None, menuButton=None)` | Set the menu button |
| `setMyCommands` | `setMyCommands(commands, scope=None, languageCode=None)` | Set bot commands |
| `setMyDescription` | `setMyDescription(description, languageCode=None)` | Set the description |
| `setMyName` | `setMyName(name, languageCode=None)` | Set the bot name |
| `setMyProfilePhoto` | `setMyProfilePhoto(photo)` | Set the bot photo |
| `setMyShortDescription` | `setMyShortDescription(shortDescription, languageCode=None)` | Set the short description |
| `setStickerEmojiList` | `setStickerEmojiList(sticker, emojiList)` | Set sticker emoji |
| `setStickerKeywords` | `setStickerKeywords(sticker, keywords)` | Set sticker keywords |
| `setStickerMaskPosition` | `setStickerMaskPosition(sticker, maskPosition)` | Set mask position |
| `setStickerPosition` | `setStickerPosition(sticker, position)` | Move a sticker |
| `setStickerSetThumbnail` | `setStickerSetThumbnail(name, userId, thumbnail=None)` | Set set thumbnail |
| `setStickerSetTitle` | `setStickerSetTitle(name, title)` | Rename a set |
| `setWebhook` | `setWebhook(url, secretToken=None, allowedUpdates=None, maxConnections=None, ipAddress=None, certificate=None, dropPending=False)` | Register a webhook |
| `start` | `start(skipPending=False, pollTimeout=20, allowedUpdates=None)` | Start polling in background |
| `sticker` | `sticker(target, sticker, **kwargs)` | Send a sticker |
| `stopLiveLocation` | `stopLiveLocation(call, inline=None, **kwargs)` | Stop live location |
| `stopPoll` | `stopPoll(target, messageId, **kwargs)` | Stop a poll |
| `timer` | `timer(seconds, fn, fireNow=False) -> TimerHandle` | Repeating background task |
| `transferBusinessGift` | `transferBusinessGift(bcId, ownedGiftId, newOwnerChatId, starCount=None)` | Transfer business gift |
| `transferBusinessStars` | `transferBusinessStars(bcId, starCount)` | Transfer business Stars |
| `transferGift` | `transferGift(giftId, userId)` | Transfer a gift |
| `unban` | `unban(target, userId)` | Unban a user |
| `unbanSender` | `unbanSender(target, senderChatId)` | Unban a sender channel |
| `unhideGeneralTopic` | `unhideGeneralTopic(target)` | Unhide the general topic |
| `unmute` | `unmute(target, userId)` | Unmute a user |
| `unpin` | `unpin(target, msgId=None, bcId=None)` | Unpin messages |
| `unpinGeneralTopicMessages` | `unpinGeneralTopicMessages(target)` | Unpin general topic messages |
| `unpinTopicMessages` | `unpinTopicMessages(target, messageThreadId)` | Unpin topic messages |
| `upgradeBusinessGift` | `upgradeBusinessGift(bcId, ownedGiftId, **kwargs)` | Upgrade a business gift |
| `upgradeGift` | `upgradeGift(giftId, **kwargs)` | Upgrade a gift |
| `uploadStickerFile` | `uploadStickerFile(userId, sticker, stickerFormat)` | Upload a sticker file |
| `venue` | `venue(target, latitude, longitude, title, address, **kwargs)` | Send a venue |
| `video` | `video(target, video, caption=None, inline=None, keyboard=None, **kwargs)` | Send a video |
| `videoNote` | `videoNote(target, videoNote, **kwargs)` | Send a video note |
| `voice` | `voice(target, voice, caption=None, inline=None, keyboard=None, **kwargs)` | Send a voice note |

## Module-level builders and exports

| Name | Signature | Purpose |
| --- | --- | --- |
| `Gramly` | `Gramly(token, msgCooldown=0.35, inlineCooldown=0.5, connectTimeout=10, readTimeout=30, locksMaxsize=10000, parseMode="HTML", debug=False)` | Bot instance |
| `btn` | `btn(text, action=None, *, url=None, miniApp=None, loginUrl=None, switchInline=None, switchInlineCurrent=None, switchInlineChosen=None, copyText=None, pay=False, requestPoll=None, requestContact=False, requestLocation=False, style=None, emoji=None, disabled=None)` | Button builder |
| `row` | `row(*buttons) -> list` | One keyboard row |
| `kbd` | `kbd(*rows) -> list` | Keyboard structure |
| `business` | `business(bcId=None)` | Business scope marker |
| `userRequest` | `userRequest(requestId, *, isBot=None, isPremium=None, maxQuantity=None, requestName=None, requestUsername=None, requestPhoto=None)` | User picker button |
| `chatRequest` | `chatRequest(requestId, *, isChannel=None, isForum=None, hasUsername=None, isCreated=None, botIsMember=None, requestTitle=None, requestUsername=None, requestPhoto=None, userAdminRights=None, botAdminRights=None)` | Chat picker button |
| `managedBotRequest` | `managedBotRequest(requestId, *, suggestedName=None, suggestedUsername=None)` | Managed bot button |
| `chatId` | `chatId(target) -> int` | Extract a chat ID |
| `userId` | `userId(target) -> int \| None` | Extract a user ID |
| `setupLogging` | `setupLogging(debug=False)` | Configure logging |
| `Rich` | `Rich(*blocks, forDraft=False)` | Rich message builder |
| `TelegramError` | `TelegramError(description, errorCode=0, retryAfter=None)` | API error |
| `CallbackData` | `CallbackData(data)` | Parse callback data |
| `Obj` | `Obj(dict)` | Dynamic object wrapper |
| `TimerHandle` | returned by `bot.timer` | Timer control |
| `CommandBlock` | returned by `bot.command` | Grouped router |

## `Rich` builders

| Builder | Signature |
| --- | --- |
| `Rich.Build` | `Build(*blocks, forDraft=False)` |
| `Rich.Anchor` | `Anchor(name)` |
| `Rich.AnchorLink` | `AnchorLink(text, name)` |
| `Rich.Animation` | `Animation(media, caption=None, credit=None, spoiler=False, **kwargs)` |
| `Rich.Audio` | `Audio(media, caption=None, credit=None, title=None, performer=None)` |
| `Rich.BulletList` | `BulletList(*items)` |
| `Rich.ButtonRun` | `ButtonRun(button)` |
| `Rich.Buttons` | `Buttons(*buttons, align=None)` |
| `Rich.CodeBlock` | `CodeBlock(text, language=None)` |
| `Rich.Collage` | `Collage(items, caption=None, credit=None)` |
| `Rich.Details` | `Details(summary, *parts, open=False)` |
| `Rich.Divider` | `Divider()` |
| `Rich.Document` | `Document(media, caption=None, credit=None, fileName=None)` |
| `Rich.EmojiRun` | `EmojiRun(customEmojiId, alt="🙂")` |
| `Rich.ExpandableQuote` | `ExpandableQuote(*parts, credit=None, expanded=False)` |
| `Rich.Footer` | `Footer(*parts)` |
| `Rich.Heading` | `Heading(*parts, size=1)` |
| `Rich.Html` | `Html(text, media=None, rtl=None, skipEntityDetection=None)` |
| `Rich.Item` | `Item(*parts, checkbox=None, checked=None, value=None, labelType=None, children=None)` |
| `Rich.Map` | `Map(latitude, longitude, zoom=15, width=400, height=300, caption=None, credit=None)` |
| `Rich.Markdown` | `Markdown(text, media=None, rtl=None, skipEntityDetection=None)` |
| `Rich.MathBlock` | `MathBlock(expression)` |
| `Rich.Paragraph` | `Paragraph(*parts)` |
| `Rich.Photo` | `Photo(media, caption=None, credit=None, spoiler=False)` |
| `Rich.PullQuote` | `PullQuote(*parts, credit=None)` |
| `Rich.Quote` | `Quote(*parts, credit=None)` |
| `Rich.Ref` | `Ref(name)` |
| `Rich.RefLink` | `RefLink(text, name)` |
| `Rich.Run` | `Run(text, style=None, *, link=None, mention=None, username=None, hashtag=None, cashtag=None, botCommand=None, email=None, phone=None, bankCard=None, date=None, dateFormat=None, math=False)` |
| `Rich.Slideshow` | `Slideshow(items, caption=None, credit=None)` |
| `Rich.Table` | `Table(rows, headerRow=True, bordered=None, striped=None, compact=None, caption=None)` |
| `Rich.Thinking` | `Thinking(*parts)` — drafts only |
| `Rich.Video` | `Video(media, caption=None, credit=None, spoiler=False, **kwargs)` |
| `Rich.Voice` | `Voice(media, caption=None, credit=None, duration=None)` |
````

## File: AGENTS.md
````markdown
# AGENTS.md — Working with Gramly

You are a senior Python engineer building Telegram bots with **Gramly 1.4.x**
(Telegram Bot API 10.3, Python 3.10+). Your job is to produce complete, runnable, idiomatic
Gramly code — not pseudo-code and not python-telegram-bot or aiogram code.

This file is the contract. Domain details live in the linked files; read only what the task
needs.

## Non-negotiable API rules

- Use `from gramly import Gramly` and construct one instance: `bot = Gramly("TOKEN")`.
- Simple commands use `@bot.onMessage(commands="...")`. Use `@bot.command("...")` only for a
  `CommandBlock` router whose handler receives `cmd: CommandBlock`.
- `onPost`, `onAny`, and `onEdited` are factories: write `@bot.onPost()`, `@bot.onAny()`,
  and `@bot.onEdited()`. `@bot.onPost` raises `TypeError`; `@bot.onAny` and `@bot.onEdited`
  without parentheses silently register nothing.
- A plain `def` handler runs in a worker thread. Do not use `await` inside it.
- An `async def` handler runs on the event loop. `await` every `bot.*` I/O call inside it.
  Do not mix awaited and non-awaited calls in the same function.
- Inline keyboards receive `inline=`; reply keyboards receive `keyboard=`.
  `keyboard=False` removes the reply keyboard; `forceReply=True` opens the input field.
- Build inline buttons with `btn(..., action="action:args")`. The callback format is
  `action:arg1:arg2`, maximum 64 bytes. Put the action first.
- `@bot.onCallback` prefixes match the raw callback data from the start. Use
  `@bot.onCallback("buy:")` for data `buy:123:item_9`.
- `CommandBlock.onCallback` matches the **first** segment exactly; use it with the same
  `action:args` convention.
- Scope business handlers with the positional marker: `@bot.onMessage(business(), ...)`.
  `business=True` does not exist and raises at import time.
- There is no `args_min` / `args_error`. Validate with `msg.has(n)` and send usage yourself.
- Use `argsFrom()` to join arguments. `argsJoined()` does not exist.
- Access errors as `e.description`, `e.errorCode`, `e.retryAfter`.
- Do not use business media wrappers (`businessPhoto`, `businessVideo`, `businessPoll`, ...).
  They are not part of the 1.4.x API. Pass `business_connection_id=bc_id` to the regular
  method.
- Do not use `CallbackData.extra()`; use `.get(index, cast, default)`.
- Do not assume a state machine exists. Gramly has no built-in FSM or session store.

If a call is not listed in [`11-api-index.md`](11-api-index.md), verify it before use:

```bash
python -c "from gramly import Gramly; print([m for m in dir(Gramly) if not m.startswith('_')])"
python -c "from gramly import Gramly; help(Gramly.send)"
```

## Decision procedure

Before writing code, answer these five questions:

1. **What triggers the handler?** Message text/command, callback, inline query, join
   request, payment, business message, or a background timer. See
   [`02-handlers.md`](02-handlers.md).
2. **What object does the handler receive?** `Message`, `CallbackQuery`, `InlineQuery`,
   `JoinRequest`, `BusinessMessage`, `BusinessConnection`, `PreCheckout`, `GuestQuery`.
   Only use attributes documented for that object in [`09-objects.md`](09-objects.md).
3. **Sync or async?** Default to a plain `def` handler. Switch to `async def` only when the
   handler must await an async library (database, HTTP client). Keep the style consistent
   inside the function.
4. **What is the response?** New message, reply, edit, media, keyboard-only edit, or no
   response. See the response matrix below and [`03-messaging.md`](03-messaging.md).
5. **Where does state live?** In-memory dict for a single-process demo; a real database for
   anything that must survive a restart. Never rely on module globals in production.

## Canonical skeleton (sync, preferred)

```python
from gramly import Gramly, btn, row, kbd

bot = Gramly("YOUR_BOT_TOKEN")

@bot.onMessage(commands="start")
def start(msg):
    bot.send(
        msg,
        f"Hello, {msg.from_user.first_name}!",
        inline=kbd(
            row(btn("Profile", action=f"profile:{msg.user_id}")),
            row(btn("Help", action=f"help:{msg.user_id}")),
        ),
    )

@bot.onCallback("profile:")
def profile(q):
    if q.cb.get(0, int) != q.user_id:
        q.alert("This button is not yours.", popup=True)
        return
    bot.edit(q, "Your profile")

bot.run()
```

## Canonical skeleton (async, only when needed)

```python
import asyncio

from gramly import Gramly

bot = Gramly("YOUR_BOT_TOKEN")

@bot.onMessage(commands="start")
async def start(msg):
    await asyncio.sleep(0.1)
    await bot.send(msg, "Hello from an async handler")

bot.run()
```

Inside `async def`, `bot.send(...)` without `await` schedules a background task. That is
allowed by the runtime but hides failures; always `await` unless you deliberately want
fire-and-forget behavior.

## Handler selection matrix

| Need | Use | Handler receives |
| --- | --- | --- |
| `/start`, text commands, exact/starts/ends/contains/regex | `@bot.onMessage(...)` | `Message` |
| Inline button press | `@bot.onCallback(...)` | `CallbackQuery` |
| Inline mode `@bot query` | `@bot.onInline(...)` | `InlineQuery` |
| Any unhandled message | `@bot.onAny()` | `Message` |
| Photo, video, document, sticker, shared user/chat | `@bot.onMedia(...)` | `Message` |
| Edited message/post | `@bot.onEdited()` | `Message` |
| Channel post | `@bot.onPost()` | `Message` |
| Pre-checkout / successful payment | `@bot.onCheckout` / `@bot.onPayment` | `PreCheckout` / `Message` |
| Join request | `@bot.onJoinRequest` | `JoinRequest` |
| Web App data | `@bot.onWebApp` | `Message` |
| Reactions, polls, boosts, paid media, member changes | dedicated `on*` | varies |
| Business message / edit / connection / deletion | `@bot.onBusiness*` | `BusinessMessage` / `BusinessConnection` / `Obj` |
| Grouped command with sub-routes and callbacks | `@bot.command(...)` | `CommandBlock` |

## Response selection matrix

| Goal | Call |
| --- | --- |
| Send to a chat, user, message, or callback | `bot.send(target, text, ...)` |
| Threaded reply to the incoming message | `bot.reply(msg, text, ...)` |
| Edit the message a button belongs to | `bot.edit(cb, text, inline=...)` |
| Change only the inline keyboard | `bot.editMarkup(cb, inline=...)` |
| Replace text/photo messages uniformly | `bot.replace(call, text, ...)` |
| Show a toast or popup on a callback | `bot.alert(cb, text, popup=True)` |
| Acknowledge silently | `bot.ack(cb)` |
| Ephemeral message in a group | `bot.ephemeral(target, text, to=...)` |
| Photo, album, video, document, voice | `bot.photo`, `bot.media`, `bot.video`, ... |
| Rich layout (headings, tables, lists) | `bot.send(target, Rich(...))` |
| Remove reply keyboard | `bot.send(target, text, keyboard=False)` |

## Callback contract

```python
# Producer
btn("Buy", action=f"buy:{user_id}:item_9")

# Consumer
@bot.onCallback("buy:")
def on_buy(q):
    owner_id = q.cb.get(0, int)   # args excludes the action
    item = q.cb.get(1)
    if owner_id != q.user_id:
        q.alert("Not your button.", popup=True)
        return
    bot.edit(q, f"Bought {item}")
```

- `q.cb.raw` is the full string; `q.cb.parts` includes the action.
- `q.cb.action` is the first part; `q.cb.args` and `q.cb.get(i)` skip it.
- Callback data is limited to **64 bytes**. Keep IDs compact; do not embed JSON.
- Gramly auto-acknowledges a callback if the handler returns without answering. Call
  `q.alert(...)` / `bot.alert(q, ...)` when the user needs feedback.
- Callbacks from the same user are serialized; a second press while the first handler runs
  is dropped with a quick ack.

## State and concurrency

- Gramly has **no FSM**. Implement multi-step flows with a dict keyed by `(chat_id, user_id)`
  or a database row, and clear the state on completion/cancel.
- Sync handlers run in a thread pool, so shared dict mutation is not automatically safe.
  Use a `threading.Lock` for multi-step in-memory state, or keep all state in an async-safe
  store and use async handlers.
- Timers run in the background and integrate with the event loop; `bot.*` calls are safe
  inside them. Stop them with `handle.stop()`.
- A handler exception is logged and does not crash the bot. Catch `TelegramError` only when
  you can recover; otherwise let it log and return a user-facing fallback.

## Error handling

```python
from gramly import TelegramError

try:
    bot.send(msg, "Hello")
except TelegramError as e:
    print(e.description, e.errorCode, e.retryAfter)
```

- `retryAfter` is set on HTTP 429. Gramly already retries those up to three times.
- `isNotModified(e)` (internal helper) detects the harmless "message is not modified" edit
  error; avoid treating it as a failure.
- `getStarBalance()` returns `None` on failure instead of raising.

## Hard "do not" list

| Do not | Do instead |
| --- | --- |
| `@bot.onMessage(business=True, ...)` | `@bot.onMessage(business(), ...)` |
| `@bot.command("start")` with a `Message` handler | `@bot.onMessage(commands="start")` |
| `args_min=`, `args_error=` | `if not msg.has(n): ...` |
| `argsJoined()` | `argsFrom()` |
| `bot.businessPhoto(...)` | `bot.photo(..., business_connection_id=bc_id)` |
| `q.cb.extra()` | `q.cb.get(i, cast, default)` |
| Raw inline `{"text": ..., "callback_data": ...}` | `btn("...", action="action:args")` |
| `bot.send(...)` + `await` in a sync handler | plain `bot.send(...)` |
| `bot.send(...)` without `await` in an async handler | `await bot.send(...)` |
| Assuming `msg.args[0]` exists | `msg.has(1)` / `msg.arg(0)` |
| Storing secrets in code | environment variables / a secret store |

## Review checklist

Before returning code, verify:

- [ ] Every imported name is exported by `gramly` (or imported from `gramly.gramly` for
      internal helpers).
- [ ] Every handler has the right arity: bare decorators such as `@bot.onPayment`,
      `@bot.onCheckout`, `@bot.onBusinessDeleted` take a function directly; factories such
      as `@bot.onMessage(...)`, `@bot.onPost()`, `@bot.onAny()`, `@bot.onEdited()`,
      `@bot.onCallback(...)`, and `@bot.command(...)` are called.
- [ ] Sync/async style is consistent inside each handler.
- [ ] Callback data starts with the action and is under 64 bytes.
- [ ] Owner/admin checks are present on state-changing callbacks.
- [ ] User input is validated (`msg.has`, `argInt`, bounds checks).
- [ ] HTML is well-formed when `parseMode="HTML"` is in effect.
- [ ] Media paths/URLs/file IDs are valid for the chosen method.
- [ ] Long-running work does not block the event loop.
- [ ] The file runs as a script (`if __name__ == "__main__": bot.run()` optional, direct
      `bot.run()` is fine).

## When information is missing

1. Check the domain file and [`11-api-index.md`](11-api-index.md).
2. Check the installed package with `help()` or `inspect.signature`.
3. Check the official docs: <https://gramly.gitbook.io/gramly-docs>.
4. If still unknown, say so and propose the closest documented approach. Never invent a
   method, parameter, or event.
````

## File: llms.txt
````
# Gramly AI Context

> Compact, version-pinned operating context for AI agents building Telegram bots with Gramly 1.4.x (Telegram Bot API 10.3, Python 3.10+).

This folder is a distilled reference, not the full documentation. Read `AGENTS.md` first, then load only the domain file needed for the task. The complete official documentation is at <https://gramly.gitbook.io/gramly-docs>.

Key facts:

- Package: `gramly`, installed with `pip install gramly`.
- Current release line: `1.4.x`.
- Bot API: `10.3`.
- Runtime: one asyncio event loop; plain handlers run in a thread pool.
- Entry point: `Gramly("TOKEN")`, then `bot.run()` for long polling.
- Callback data convention: `action:arg1:arg2`, max 64 bytes.
- Business handlers use the positional `business()` marker; `business=True` does not exist.

## Start here

- [AGENTS.md](AGENTS.md): Non-negotiable API rules, decision procedure, review checklist.
- [README.md](README.md): Purpose, context map, and the ten rules that prevent most bugs.
- [01-overview.md](01-overview.md): Mental model, constructor, async model, run modes, layout.

## Core API

- [02-handlers.md](02-handlers.md): Every handler decorator, CommandBlock, guards, interceptors.
- [03-messaging.md](03-messaging.md): Send, reply, edit, media, Rich messages, special content, actions.
- [04-keyboards.md](04-keyboards.md): btn, row, kbd, request buttons, keyboard shapes.
- [05-chat-admin.md](05-chat-admin.md): Moderation, chat info/settings, invites, topics, join requests.
- [06-business.md](06-business.md): Business connections, handlers, actions, account management.
- [07-payments.md](07-payments.md): Invoices, pre-checkout, payments, Stars, gifts.
- [08-inline-settings.md](08-inline-settings.md): Inline and guest queries, bot settings, profile, stickers.
- [09-objects.md](09-objects.md): Objects, data classes, errors, helpers, timers.
- [11-api-index.md](11-api-index.md): Alphabetical index of every public Gramly method.

## Implementation guidance

- [10-patterns.md](10-patterns.md): Canonical recipes, anti-patterns, state, deployment, testing.

## Optional

- [Official Gramly documentation](https://gramly.gitbook.io/gramly-docs): Full prose documentation and examples.
- [Official llms-full.txt](https://gramly.gitbook.io/gramly-docs/llms-full.txt): Entire documentation in one file.
- [Telegram Bot API](https://core.telegram.org/bots/api): Underlying platform reference.
- [gramly-context.md](../gramly-context.md): All files in this folder packed into a single Markdown bundle.
````

## File: README.md
````markdown
# Gramly AI Context

A compact, version-pinned knowledge base for AI agents that write, review, or debug
Telegram bots built with **Gramly**. This is not a copy of the full documentation. It is
the operating context an agent needs to get the API right on the first attempt.

**Target release:** Gramly `1.4.x` · **Telegram Bot API:** `10.3` · **Python:** `3.10+`

```bash
pip install gramly
```

## Start here

1. Read [`AGENTS.md`](AGENTS.md) — the operating rules and workflow.
2. Read [`01-overview.md`](01-overview.md) — the mental model, lifecycle, and configuration.
3. Load only the domain file you need from the map below.
4. Use [`11-api-index.md`](11-api-index.md) when you need to confirm that a method exists
   and what its current signature is.

`llms.txt` is the machine-readable index for tools that understand the
[llms.txt convention](https://llmstxt.org/). `../gramly-context.md` (generated with
Repomix) is the same content packed into one file for chat interfaces.

## Context map

| File | Contains | Load when |
| --- | --- | --- |
| [`AGENTS.md`](AGENTS.md) | Non-negotiable rules, decision procedure, review checklist | Always, before writing code |
| [`01-overview.md`](01-overview.md) | Identity, install, constructor, async model, run modes, project layout | Starting a bot or changing configuration |
| [`02-handlers.md`](02-handlers.md) | Every handler decorator, `CommandBlock`, guards, interceptors | Routing an update |
| [`03-messaging.md`](03-messaging.md) | Send, reply, edit, media, `Rich`, special content, message actions | Producing any output |
| [`04-keyboards.md`](04-keyboards.md) | `btn`, `row`, `kbd`, request buttons, layout rules | Adding buttons or menus |
| [`05-chat-admin.md`](05-chat-admin.md) | Moderation, chat info/settings, invites, topics, join requests | Administering chats |
| [`06-business.md`](06-business.md) | Business connections, handlers, actions, account management | Telegram Business Mode |
| [`07-payments.md`](07-payments.md) | Invoices, pre-checkout, payments, Stars, gifts | Monetization |
| [`08-inline-settings.md`](08-inline-settings.md) | Inline/guest queries, bot settings, profile, sticker sets | Inline mode or bot profile |
| [`09-objects.md`](09-objects.md) | Objects, data classes, errors, helpers, `Obj`, timers | Reading handler payloads |
| [`10-patterns.md`](10-patterns.md) | Canonical recipes, anti-patterns, deployment and testing | Implementing a feature end-to-end |
| [`11-api-index.md`](11-api-index.md) | Alphabetical index of every public `Gramly` method | Verifying an API call |

## The ten rules that prevent most bugs

1. **One event loop.** Gramly owns an asyncio loop. Plain functions are automatically run
   in a thread pool; coroutine functions are awaited directly.
2. **Never mix `await` styles inside one handler.** In an `async def` handler, `await`
   every `bot.*` call that performs I/O. In a plain `def` handler, never use `await`.
3. **Callback data is `action:args`.** Use `action` first, for example
   `action=f"buy:{user_id}:item_9"`. `onCallback` prefixes and `CommandBlock` both match
   the first segment.
4. **Buttons come from `btn()`.** Do not hand-write Telegram `callback_data` dicts; use
   `btn(..., action=...)`, which produces the `data` field the keyboard builder expects.
5. **`business()` is a positional marker.** There is no `business=True` keyword. Pass
   `business()` first: `@bot.onMessage(business(), commands="start")`.
6. **No built-in argument validation.** Check `msg.has(n)` yourself and reply with usage.
7. **`parseMode` defaults to `"HTML"`.** Override it per call when needed; never assume
   Markdown.
8. **Ephemeral messages are group-only.** They cannot be sent in private chats or
   channels, and `replace()` does not support them.
9. **Errors are `TelegramError`.** Read `description`, `errorCode`, and `retryAfter`;
   Gramly retries `retryAfter` responses up to three times.
10. **Do not invent methods.** If a method is not in [`11-api-index.md`](11-api-index.md),
    it is probably not part of the public API. Check the installed package before use.

## Smallest correct bot

```python
from gramly import Gramly

bot = Gramly("YOUR_BOT_TOKEN")

@bot.onMessage(commands="start")
def start(msg):
    bot.send(msg, f"Hello, {msg.from_user.first_name}!")

bot.run()
```

## Source of truth

The official documentation is <https://gramly.gitbook.io/gramly-docs>. This folder is a
distilled snapshot pinned to `1.4.x`; it intentionally omits release history. When the
context and the installed package disagree, the installed package wins:

```bash
python -c "import gramly; print(gramly.__version__)"
python -c "from gramly import Gramly; help(Gramly.send)"
```

Do not silently upgrade APIs in generated code. Preserve the style already used by the
project and target the version reported by the environment.
````
