# 11 — Complete API Index

Every public method on `Gramly`, plus module-level builders. Signatures are the current
1.4.x surface. `**kwargs` are passed through to Telegram and are not expanded here.

Use this page to confirm that a method exists before writing code. If a name is absent, it
is not part of the public API.

Decorator arity matters: signatures shown as `fn` are bare decorators (`@bot.onPayment`);
signatures with a parameter list are factories and must be called (`@bot.onMessage(...)`,
`@bot.onPost()`, `@bot.onAny()`, `@bot.onEdited()`). In particular, `onPost` has no
configuration parameters but still requires parentheses.

## Alphabetical methods

| Method | Signature | Purpose |
| --- | --- | --- |
| `ack` | `ack(call)` | Acknowledge a callback silently |
| `action` | `action(target, action="typing")` | Send a chat action |
| `addStickerToSet` | `addStickerToSet(userId, name, sticker)` | Add one sticker to a set |
| `alert` | `alert(call, text="", popup=False)` | Toast or popup for a callback |
| `animation` | `animation(target, animation, caption=None, **kwargs)` | Send a GIF/animation |
| `answerGuestQuery` | `answerGuestQuery(queryId, text, parseMode=None, **kwargs)` | Answer a guest query |
| `answerInlineQuery` | `answerInlineQuery(query, results, cacheTime=30, isPersonal=True, nextOffset="")` | Answer an inline query |
| `answerJoinRequestQuery` | `answerJoinRequestQuery(target, userId, queryId, result)` | Answer a join request query |
| `answerShippingQuery` | `answerShippingQuery(shippingQueryId, ok, **kwargs)` | Answer a shipping query |
| `answerWebAppQuery` | `answerWebAppQuery(webAppQueryId, result)` | Answer a Web App query |
| `approveJoin` | `approveJoin(target, userId=None)` | Approve a join request |
| `audio` | `audio(target, audio, caption=None, inline=None, keyboard=None, **kwargs)` | Send audio |
| `ban` | `ban(target, userId, until=0, revokeMessages=False)` | Ban a user |
| `banSender` | `banSender(target, senderChatId)` | Ban a sender channel |
| `businessAction` | `businessAction(target, bcId, action="typing")` | Chat action as a business account |
| `businessConnection` | `businessConnection(bcId)` | Fetch/cached business connection |
| `businessDelete` | `businessDelete(target, messageIds, bcId)` | Delete business messages |
| `businessRead` | `businessRead(target, maxMessageId, bcId)` | Mark business messages read |
| `businessSend` | `businessSend(target, text, bcId, inline=None, keyboard=None, **kwargs)` | Send as a business account |
| `checklist` | `checklist(target, title, tasks, **kwargs)` | Send a checklist |
| `close` | `close()` | Stop the running bot |
| `closeBot` | `closeBot()` | Close the bot instance |
| `closeGeneralTopic` | `closeGeneralTopic(target)` | Close the general topic |
| `closeTopic` | `closeTopic(target, messageThreadId)` | Close a forum topic |
| `command` | `command(*triggers, withSlash=True, withoutSlash=True, filters=None, starts=None, ends=None)` | Register a `CommandBlock` |
| `contact` | `contact(target, phone, firstName, lastName=None, **kwargs)` | Send a contact |
| `convertBusinessGiftToStars` | `convertBusinessGiftToStars(bcId, ownedGiftId)` | Convert a business gift |
| `convertGiftToStars` | `convertGiftToStars(giftId)` | Convert a gift to Stars |
| `copy` | `copy(target, message, **kwargs)` | Copy one message |
| `copyMessages` | `copyMessages(target, fromChatId, messageIds, **kwargs)` | Copy multiple messages |
| `createInvite` | `createInvite(target, **kwargs)` | Create an invite link |
| `createInvoiceLink` | `createInvoiceLink(title, description, payload, stars, photoUrl=None, subscriptionPeriod=None, **kwargs) -> str` | Create an invoice link |
| `createNewStickerSet` | `createNewStickerSet(userId, name, title, stickers, **kwargs)` | Create a sticker set |
| `createSubscriptionInvite` | `createSubscriptionInvite(target, subscriptionPeriod, subscriptionPrice, **kwargs)` | Create a subscription invite |
| `createTopic` | `createTopic(target, name, **kwargs)` | Create a forum topic |
| `declineJoin` | `declineJoin(target, userId=None)` | Decline a join request |
| `delete` | `delete(target, messageId=None, bcId=None) -> bool` | Delete one or more messages |
| `deleteChatPhoto` | `deleteChatPhoto(target)` | Remove a chat photo |
| `deleteChatStickerSet` | `deleteChatStickerSet(target)` | Remove a chat sticker set |
| `deleteLater` | `deleteLater(message, delay, messageId=None, bcId=None)` | Delete after a delay |
| `deleteMessage` | `deleteMessage(target, messageId, bcId=None) -> bool` | Delete one message |
| `deleteMessages` | `deleteMessages(target, messageIds, bcId=None) -> bool` | Delete multiple messages |
| `deleteMyCommands` | `deleteMyCommands(scope=None, languageCode=None)` | Delete bot commands |
| `deleteStickerFromSet` | `deleteStickerFromSet(sticker)` | Remove a sticker |
| `deleteStickerSet` | `deleteStickerSet(name)` | Delete a sticker set |
| `deleteStory` | `deleteStory(bcId, storyId)` | Delete a business story |
| `deleteTopic` | `deleteTopic(target, messageThreadId)` | Delete a topic |
| `deleteWebhook` | `deleteWebhook(dropPending=False)` | Remove the webhook |
| `dice` | `dice(target, emoji="🎲", **kwargs)` | Send a dice |
| `document` | `document(target, doc, caption=None, inline=None, keyboard=None, **kwargs)` | Send a document |
| `edit` | `edit(call, text, inline=None, photo=None, showCaption=None, **kwargs)` | Edit text/caption/media |
| `editChecklist` | `editChecklist(target, messageId, title, tasks, **kwargs)` | Edit a checklist |
| `editGeneralTopic` | `editGeneralTopic(target, name)` | Rename the general topic |
| `editInvite` | `editInvite(target, inviteLink, **kwargs)` | Edit an invite link |
| `editLiveLocation` | `editLiveLocation(call, latitude, longitude, inline=None, **kwargs)` | Update a live location |
| `editMarkup` | `editMarkup(call, inline=None)` | Edit only the inline keyboard |
| `editStarSubscription` | `editStarSubscription(userId, telegramPaymentChargeId, isCanceled)` | Cancel/reactivate a subscription |
| `editStory` | `editStory(bcId, storyId, content, **kwargs)` | Edit a business story |
| `editSubscriptionInvite` | `editSubscriptionInvite(target, inviteLink, **kwargs)` | Edit a subscription invite |
| `editTopic` | `editTopic(target, messageThreadId, **kwargs)` | Edit a topic |
| `ephemeral` | `ephemeral(target, text, to=None, keyboard=None, inline=None, photo=None, replaceCallbackMessage=None, **kwargs)` | Group-only ephemeral message |
| `exportInvite` | `exportInvite(target) -> str` | Get the primary invite link |
| `forward` | `forward(target, message)` | Forward one message |
| `forwardMessages` | `forwardMessages(target, fromChatId, messageIds, **kwargs)` | Forward multiple messages |
| `game` | `game(target, gameShortName, inline=None, keyboard=None, **kwargs)` | Send a game |
| `getAccessSettings` | `getAccessSettings()` | Get managed-bot access settings |
| `getAdmins` | `getAdmins(target, includeBots=False) -> list` | List chat admins |
| `getBusinessGifts` | `getBusinessGifts(bcId, **kwargs)` | List business gifts |
| `getBusinessStars` | `getBusinessStars(bcId)` | Business Star balance |
| `getChat` | `getChat(target)` | Get chat info |
| `getChatMember` | `getChatMember(target, userId)` | Get one member |
| `getChatMemberCount` | `getChatMemberCount(target) -> int` | Member count |
| `getCustomEmojiStickers` | `getCustomEmojiStickers(customEmojiIds)` | Stickers for custom emoji |
| `getDefaultAdminRights` | `getDefaultAdminRights(forChannels=False)` | Default admin rights |
| `getFile` | `getFile(fileId)` | Resolve a file |
| `getGifts` | `getGifts()` | List available gifts |
| `getManagedToken` | `getManagedToken(userId)` | Fetch a managed bot token |
| `getMe` | `getMe()` | Bot identity |
| `getMenuButton` | `getMenuButton(target=None)` | Get the menu button |
| `getMyCommands` | `getMyCommands(scope=None, languageCode=None)` | Get bot commands |
| `getMyDescription` | `getMyDescription(languageCode=None)` | Get the description |
| `getMyName` | `getMyName(languageCode=None)` | Get the bot name |
| `getMyShortDescription` | `getMyShortDescription(languageCode=None)` | Get the short description |
| `getPersonalMessages` | `getPersonalMessages(userId, **kwargs)` | Personal messages (Business) |
| `getStarBalance` | `getStarBalance()` | Star balance or `None` |
| `getStarTransactions` | `getStarTransactions(offset=0, limit=100)` | Star transactions |
| `getStickerSet` | `getStickerSet(name)` | Get a sticker set |
| `getUserAudios` | `getUserAudios(userId, offset=0, limit=100)` | User audio files |
| `getUserBoosts` | `getUserBoosts(target, userId)` | User boosts |
| `getUserPhotos` | `getUserPhotos(userId, offset=0, limit=100)` | User profile photos |
| `getWebhookInfo` | `getWebhookInfo()` | Webhook status |
| `gift` | `gift(userId, giftId, payForUpgrade=False, **kwargs)` | Send a gift |
| `giftPremium` | `giftPremium(userId, **kwargs)` | Gift Telegram Premium |
| `guard` | `guard(fn)` | Register a global guard |
| `hideGeneralTopic` | `hideGeneralTopic(target)` | Hide the general topic |
| `intercept` | `intercept(fn)` | Register a raw-update interceptor |
| `invoice` | `invoice(target, title, description, payload, stars, photoUrl=None, inline=None, protectContent=False, **kwargs)` | Send a Stars invoice |
| `isAdmin` | `isAdmin(target, userId) -> bool` | Check admin status |
| `kick` | `kick(target, userId)` | Kick a user |
| `leave` | `leave(target)` | Leave a chat |
| `livePhoto` | `livePhoto(target, photo, animation, caption=None, inline=None, keyboard=None, **kwargs)` | Send a live photo |
| `location` | `location(target, latitude, longitude, **kwargs)` | Send a location |
| `logOut` | `logOut()` | Log out from the API server |
| `media` | `media(target, items, caption=None, inline=None, keyboard=None, **kwargs)` | Send a mixed album |
| `messageDraft` | `messageDraft(target, draftId, text="", inline=None, keyboard=None, canStop=None, keepOnStop=None, **kwargs)` | Send a draft |
| `mute` | `mute(target, userId, until=0)` | Mute a user |
| `onAny` | `onAny(*businessMarker, filters=None)` | Catch-all message handler |
| `onBoost` | `onBoost(fn)` | Chat boost handler |
| `onBusinessConnection` | `onBusinessConnection(fn)` | Business connection handler |
| `onBusinessDeleted` | `onBusinessDeleted(fn, *businessMarker)` | Business deletion handler |
| `onBusinessEdited` | `onBusinessEdited()` | Business edit handler |
| `onBusinessMessage` | `onBusinessMessage(commands=None, **kw)` | Business message handler |
| `onCallback` | `onCallback(*prefixes, filters=None)` | Callback handler |
| `onChatMember` | `onChatMember(fn)` | Member change handler |
| `onCheckout` | `onCheckout(fn)` | Pre-checkout handler |
| `onEdited` | `onEdited(*businessMarker)` | Edited message handler |
| `onGenerationStopped` | `onGenerationStopped(fn)` | Draft stopped handler |
| `onGuest` | `onGuest(fn)` | Guest query handler |
| `onInline` | `onInline(minLength=0)` | Inline query handler |
| `onJoinRequest` | `onJoinRequest(fn)` | Join request handler |
| `onManaged` | `onManaged(fn)` | Managed bot handler |
| `onMedia` | `onMedia(*contentTypes)` | Media handler |
| `onMessage` | `onMessage(commands=None, exact=None, starts=None, ends=None, contains=None, regex=None, withSlash=True, withoutSlash=True, filters=None)` | Text/command handler |
| `onMyStatus` | `onMyStatus(fn)` | Bot status handler |
| `onPaidMedia` | `onPaidMedia(fn)` | Paid media handler |
| `onPayment` | `onPayment(fn)` | Successful payment handler |
| `onPoll` | `onPoll(fn)` | Poll answer handler |
| `onPost` | `onPost()` | Channel post handler |
| `onReaction` | `onReaction(fn)` | Reaction handler |
| `onStop` | `onStop(fn)` | Shutdown handler |
| `onWebApp` | `onWebApp(fn)` | Web App data handler |
| `paidMedia` | `paidMedia(target, starCount, media, **kwargs)` | Send paid media |
| `photo` | `photo(target, photo, caption=None, inline=None, keyboard=None, **kwargs)` | Send photos |
| `pin` | `pin(message, notify=False)` | Pin a message |
| `poll` | `poll(target, question, options, isAnonymous=True, pollType="regular", correctOptionIds=None, explanation=None, allowsMultipleAnswers=False, allowsRevoting=None, shuffleOptions=None, allowAddingOptions=None, hideResultsUntilCloses=None, description=None, openPeriod=None, closeDate=None, membersOnly=None, countryCodes=None, **kwargs)` | Send a poll |
| `postStory` | `postStory(bcId, content, activePeriod, **kwargs)` | Post a business story |
| `processUpdate` | `processUpdate(update)` | Dispatch a raw update |
| `promote` | `promote(target, userId, **permissions)` | Promote an admin |
| `react` | `react(msg, *emojis, isBig=False)` | Set/remove reactions |
| `refund` | `refund(userId, chargeId) -> bool` | Refund a Stars payment |
| `removeBusinessPhoto` | `removeBusinessPhoto(bcId, isPublic=None)` | Remove business photo |
| `removeMyProfilePhoto` | `removeMyProfilePhoto(photoId=None)` | Remove bot photo |
| `reopenGeneralTopic` | `reopenGeneralTopic(target)` | Reopen the general topic |
| `reopenTopic` | `reopenTopic(target, messageThreadId)` | Reopen a topic |
| `replace` | `replace(call, text, inline=None, photo=None, **kwargs)` | Replace a message |
| `replaceManagedToken` | `replaceManagedToken(userId)` | Rotate a managed bot token |
| `replaceStickerInSet` | `replaceStickerInSet(userId, name, oldSticker, sticker)` | Replace a sticker |
| `reply` | `reply(message, text, keyboard=None, inline=None, photo=None, forceReply=None, businessConnectionId=None, **kwargs)` | Threaded reply |
| `restrict` | `restrict(target, userId, permissions, until=0)` | Apply permissions |
| `revokeInvite` | `revokeInvite(target, inviteLink)` | Revoke an invite |
| `run` | `run(skipPending=False, pollTimeout=20, allowedUpdates=None)` | Start long polling |
| `savePreparedInlineMessage` | `savePreparedInlineMessage(userId, result, allowUserChats=None, allowBotChats=None, allowGroupChats=None, allowChannelChats=None)` | Save a prepared result |
| `savePreparedKeyboardButton` | `savePreparedKeyboardButton(text, requestUser=None, requestChat=None, requestManagedBot=None, webApp=None, loginUrl=None, switchInline=None, switchInlineCurrent=None, switchInlineChosen=None, copyText=None, pay=None)` | Save a prepared button |
| `send` | `send(target, text, inline=None, keyboard=None, photo=None, forceReply=None, businessConnectionId=None, **kwargs)` | Send a message |
| `sendJoinRequestWebApp` | `sendJoinRequestWebApp(target, userId, webAppUrl, **kwargs)` | Web App for a join request |
| `setAccessSettings` | `setAccessSettings(settings)` | Set managed-bot access |
| `setAdminTitle` | `setAdminTitle(target, userId, title)` | Set an admin title |
| `setBusinessBio` | `setBusinessBio(bcId, bio=None)` | Set business bio |
| `setBusinessGiftSettings` | `setBusinessGiftSettings(bcId, showGiftButton, acceptedGiftTypes)` | Gift settings |
| `setBusinessName` | `setBusinessName(bcId, firstName, lastName=None)` | Set business name |
| `setBusinessPhoto` | `setBusinessPhoto(bcId, photo, isPublic=None)` | Set business photo |
| `setBusinessUsername` | `setBusinessUsername(bcId, username=None)` | Set business username |
| `setChatDescription` | `setChatDescription(target, description)` | Set chat description |
| `setChatPermissions` | `setChatPermissions(target, permissions)` | Default permissions |
| `setChatPhoto` | `setChatPhoto(target, photo)` | Set chat photo |
| `setChatStickerSet` | `setChatStickerSet(target, stickerSetName)` | Set chat sticker set |
| `setChatTitle` | `setChatTitle(target, title)` | Set chat title |
| `setCustomEmojiStickerSetThumbnail` | `setCustomEmojiStickerSetThumbnail(name, customEmojiId=None)` | Custom emoji thumbnail |
| `setDefaultAdminRights` | `setDefaultAdminRights(rights=None, forChannels=False)` | Default admin rights |
| `setEmojiStatus` | `setEmojiStatus(userId, customEmojiId=None, **kwargs) -> bool` | Set/clear emoji status |
| `setMemberTag` | `setMemberTag(target, userId, tag)` | Set a member tag |
| `setMenuButton` | `setMenuButton(target=None, menuButton=None)` | Set the menu button |
| `setMyCommands` | `setMyCommands(commands, scope=None, languageCode=None)` | Set bot commands |
| `setMyDescription` | `setMyDescription(description, languageCode=None)` | Set the description |
| `setMyName` | `setMyName(name, languageCode=None)` | Set the bot name |
| `setMyProfilePhoto` | `setMyProfilePhoto(photo)` | Set the bot photo |
| `setMyShortDescription` | `setMyShortDescription(shortDescription, languageCode=None)` | Set the short description |
| `setStickerEmojiList` | `setStickerEmojiList(sticker, emojiList)` | Set sticker emoji |
| `setStickerKeywords` | `setStickerKeywords(sticker, keywords)` | Set sticker keywords |
| `setStickerMaskPosition` | `setStickerMaskPosition(sticker, maskPosition)` | Set mask position |
| `setStickerPosition` | `setStickerPosition(sticker, position)` | Move a sticker |
| `setStickerSetThumbnail` | `setStickerSetThumbnail(name, userId, thumbnail=None)` | Set set thumbnail |
| `setStickerSetTitle` | `setStickerSetTitle(name, title)` | Rename a set |
| `setWebhook` | `setWebhook(url, secretToken=None, allowedUpdates=None, maxConnections=None, ipAddress=None, certificate=None, dropPending=False)` | Register a webhook |
| `start` | `start(skipPending=False, pollTimeout=20, allowedUpdates=None)` | Start polling in background |
| `sticker` | `sticker(target, sticker, **kwargs)` | Send a sticker |
| `stopLiveLocation` | `stopLiveLocation(call, inline=None, **kwargs)` | Stop live location |
| `stopPoll` | `stopPoll(target, messageId, **kwargs)` | Stop a poll |
| `timer` | `timer(seconds, fn, fireNow=False) -> TimerHandle` | Repeating background task |
| `transferBusinessGift` | `transferBusinessGift(bcId, ownedGiftId, newOwnerChatId, starCount=None)` | Transfer business gift |
| `transferBusinessStars` | `transferBusinessStars(bcId, starCount)` | Transfer business Stars |
| `transferGift` | `transferGift(giftId, userId)` | Transfer a gift |
| `unban` | `unban(target, userId)` | Unban a user |
| `unbanSender` | `unbanSender(target, senderChatId)` | Unban a sender channel |
| `unhideGeneralTopic` | `unhideGeneralTopic(target)` | Unhide the general topic |
| `unmute` | `unmute(target, userId)` | Unmute a user |
| `unpin` | `unpin(target, msgId=None, bcId=None)` | Unpin messages |
| `unpinGeneralTopicMessages` | `unpinGeneralTopicMessages(target)` | Unpin general topic messages |
| `unpinTopicMessages` | `unpinTopicMessages(target, messageThreadId)` | Unpin topic messages |
| `upgradeBusinessGift` | `upgradeBusinessGift(bcId, ownedGiftId, **kwargs)` | Upgrade a business gift |
| `upgradeGift` | `upgradeGift(giftId, **kwargs)` | Upgrade a gift |
| `uploadStickerFile` | `uploadStickerFile(userId, sticker, stickerFormat)` | Upload a sticker file |
| `venue` | `venue(target, latitude, longitude, title, address, **kwargs)` | Send a venue |
| `video` | `video(target, video, caption=None, inline=None, keyboard=None, **kwargs)` | Send a video |
| `videoNote` | `videoNote(target, videoNote, **kwargs)` | Send a video note |
| `voice` | `voice(target, voice, caption=None, inline=None, keyboard=None, **kwargs)` | Send a voice note |

## Module-level builders and exports

| Name | Signature | Purpose |
| --- | --- | --- |
| `Gramly` | `Gramly(token, msgCooldown=0.35, inlineCooldown=0.5, connectTimeout=10, readTimeout=30, locksMaxsize=10000, parseMode="HTML", debug=False)` | Bot instance |
| `btn` | `btn(text, action=None, *, url=None, miniApp=None, loginUrl=None, switchInline=None, switchInlineCurrent=None, switchInlineChosen=None, copyText=None, pay=False, requestPoll=None, requestContact=False, requestLocation=False, style=None, emoji=None, disabled=None)` | Button builder |
| `row` | `row(*buttons) -> list` | One keyboard row |
| `kbd` | `kbd(*rows) -> list` | Keyboard structure |
| `business` | `business(bcId=None)` | Business scope marker |
| `userRequest` | `userRequest(requestId, *, isBot=None, isPremium=None, maxQuantity=None, requestName=None, requestUsername=None, requestPhoto=None)` | User picker button |
| `chatRequest` | `chatRequest(requestId, *, isChannel=None, isForum=None, hasUsername=None, isCreated=None, botIsMember=None, requestTitle=None, requestUsername=None, requestPhoto=None, userAdminRights=None, botAdminRights=None)` | Chat picker button |
| `managedBotRequest` | `managedBotRequest(requestId, *, suggestedName=None, suggestedUsername=None)` | Managed bot button |
| `chatId` | `chatId(target) -> int` | Extract a chat ID |
| `userId` | `userId(target) -> int \| None` | Extract a user ID |
| `setupLogging` | `setupLogging(debug=False)` | Configure logging |
| `Rich` | `Rich(*blocks, forDraft=False)` | Rich message builder |
| `TelegramError` | `TelegramError(description, errorCode=0, retryAfter=None)` | API error |
| `CallbackData` | `CallbackData(data)` | Parse callback data |
| `Obj` | `Obj(dict)` | Dynamic object wrapper |
| `TimerHandle` | returned by `bot.timer` | Timer control |
| `CommandBlock` | returned by `bot.command` | Grouped router |

## `Rich` builders

| Builder | Signature |
| --- | --- |
| `Rich.Build` | `Build(*blocks, forDraft=False)` |
| `Rich.Anchor` | `Anchor(name)` |
| `Rich.AnchorLink` | `AnchorLink(text, name)` |
| `Rich.Animation` | `Animation(media, caption=None, credit=None, spoiler=False, **kwargs)` |
| `Rich.Audio` | `Audio(media, caption=None, credit=None, title=None, performer=None)` |
| `Rich.BulletList` | `BulletList(*items)` |
| `Rich.ButtonRun` | `ButtonRun(button)` |
| `Rich.Buttons` | `Buttons(*buttons, align=None)` |
| `Rich.CodeBlock` | `CodeBlock(text, language=None)` |
| `Rich.Collage` | `Collage(items, caption=None, credit=None)` |
| `Rich.Details` | `Details(summary, *parts, open=False)` |
| `Rich.Divider` | `Divider()` |
| `Rich.Document` | `Document(media, caption=None, credit=None, fileName=None)` |
| `Rich.EmojiRun` | `EmojiRun(customEmojiId, alt="🙂")` |
| `Rich.ExpandableQuote` | `ExpandableQuote(*parts, credit=None, expanded=False)` |
| `Rich.Footer` | `Footer(*parts)` |
| `Rich.Heading` | `Heading(*parts, size=1)` |
| `Rich.Html` | `Html(text, media=None, rtl=None, skipEntityDetection=None)` |
| `Rich.Item` | `Item(*parts, checkbox=None, checked=None, value=None, labelType=None, children=None)` |
| `Rich.Map` | `Map(latitude, longitude, zoom=15, width=400, height=300, caption=None, credit=None)` |
| `Rich.Markdown` | `Markdown(text, media=None, rtl=None, skipEntityDetection=None)` |
| `Rich.MathBlock` | `MathBlock(expression)` |
| `Rich.Paragraph` | `Paragraph(*parts)` |
| `Rich.Photo` | `Photo(media, caption=None, credit=None, spoiler=False)` |
| `Rich.PullQuote` | `PullQuote(*parts, credit=None)` |
| `Rich.Quote` | `Quote(*parts, credit=None)` |
| `Rich.Ref` | `Ref(name)` |
| `Rich.RefLink` | `RefLink(text, name)` |
| `Rich.Run` | `Run(text, style=None, *, link=None, mention=None, username=None, hashtag=None, cashtag=None, botCommand=None, email=None, phone=None, bankCard=None, date=None, dateFormat=None, math=False)` |
| `Rich.Slideshow` | `Slideshow(items, caption=None, credit=None)` |
| `Rich.Table` | `Table(rows, headerRow=True, bordered=None, striped=None, compact=None, caption=None)` |
| `Rich.Thinking` | `Thinking(*parts)` — drafts only |
| `Rich.Video` | `Video(media, caption=None, credit=None, spoiler=False, **kwargs)` |
| `Rich.Voice` | `Voice(media, caption=None, credit=None, duration=None)` |
