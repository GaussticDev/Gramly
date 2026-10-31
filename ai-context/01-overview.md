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
