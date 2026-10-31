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
