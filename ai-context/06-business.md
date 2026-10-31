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
