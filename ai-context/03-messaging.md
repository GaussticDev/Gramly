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
