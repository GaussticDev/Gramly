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
