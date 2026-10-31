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
