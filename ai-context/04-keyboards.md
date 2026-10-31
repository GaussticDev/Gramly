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
