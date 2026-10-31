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
