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
