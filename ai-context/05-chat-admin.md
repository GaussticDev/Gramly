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
