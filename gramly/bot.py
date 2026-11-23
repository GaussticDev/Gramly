import asyncio
import re
import threading
import time
from collections.abc import Callable
from contextlib import suppress
from typing import Optional, Any

from gramly.client import AsyncAPIClient
from gramly.errors import TelegramError
from gramly.keyboards import buildInlineKeyboard, buildReplyKeyboard
from gramly.rich import Rich, _collectRichAttachments, _resolveInputMedia
from gramly.routing import (
    CommandBlock, CallbackData, TextRoute, matchText, business,
    _businessArg, _businessParams
)
from gramly.types import (
    Obj, User, Chat, Widget, Message, CallbackQuery,
    InlineQuery, Payment, PreCheckout, JoinRequest, BusinessMessage,
    BusinessConnection, ManagedBot, GuestQuery, WidgetQuery, SharedWidgetQuery,
    wrap, _to_raw
)
from gramly.utils import (
    LRUCache, TimerHandle, chatId, userId, toList, isNotModified,
    _in_async_task, setupLogging, _log, DEFAULT_PERMISSIONS
)

__version__ = "1.5.0"
__bot_api_version__ = "10.4"

__all__ = ["Gramly", "__version__", "__bot_api_version__", "HANDLER_UPDATES"]

_MEDIA_METHODS: dict = {
    "video": ("sendVideo", "video"),
    "audio": ("sendAudio", "audio"),
    "document": ("sendDocument", "document"),
}

HANDLER_UPDATES: dict = {
    "_messageHandlers": ["message"],
    "_editedHandlers": ["edited_message", "edited_channel_post"],
    "_postHandlers": ["channel_post"],
    "_callbackHandlers": ["callback_query"],
    "_inlineHandlers": ["inline_query"],
    "_mediaHandlers": ["message"],
    "_anyHandlers": ["message"],
    "_myStatusHandlers": ["my_chat_member"],
    "_memberHandlers": ["chat_member"],
    "_joinHandlers": ["chat_join_request"],
    "_reactionHandlers": ["message_reaction"],
    "_pollHandlers": ["poll_answer"],
    "_boostHandlers": ["chat_boost", "removed_chat_boost"],
    "_checkoutHandlers": ["pre_checkout_query"],
    "_paymentHandlers": ["message"],
    "_webappHandlers": ["message"],
    "_paidMediaHandlers": ["purchased_paid_media"],
    "_guestHandlers": ["guest_message"],
    "_managedHandlers": ["managed_bot"],
    "_generationStoppedHandlers": ["stopped_message_generation"],
    "_bizMsgHandlers": ["business_message"],
    "_bizEditedHandlers": ["edited_business_message"],
    "_bizDeletedHandlers": ["deleted_business_messages"],
    "_bizConnectionHandlers": ["business_connection"],
    "_widgetQueryHandlers": ["widget_query"],
    "_sharedWidgetQueryHandlers": ["shared_widget_query"],
    "_commandBlocks": ["message", "callback_query", "business_message"],
}

class Gramly:
    def __init__(
        self,
        token: str,
        msgCooldown: float = 0.35,
        inlineCooldown: float = 0.5,
        connectTimeout: int = 10,
        readTimeout: int = 30,
        locksMaxsize: int = 10000,
        parseMode: str = "HTML",
        debug: bool = False,
    ):
        if not token or not token.strip():
            raise ValueError("Token must be a non-empty string")
        self.debug = debug
        self.parseMode = parseMode
        setupLogging(debug)

        self._loop = None
        self._loop_owned = False
        self._api = AsyncAPIClient(token, connectTimeout=connectTimeout, readTimeout=readTimeout)
        self._msgCooldown = msgCooldown
        self._inlineCooldown = inlineCooldown

        self._guards = []
        self._interceptors = []
        self._stopEvent = threading.Event()
        self._pendingTimers: list = []

        self._userMsgTs = LRUCache(locksMaxsize)
        self._userMsgTsLock = threading.Lock()
        self._userInlineTs = LRUCache(locksMaxsize)
        self._userInlineTsLock = threading.Lock()
        self._handledMsgIds = LRUCache(locksMaxsize)
        self._handledMsgIdsLock = threading.Lock()
        self._userCbLocks = {}
        self._userCbLocksLock = asyncio.Lock()

        handler_attrs = (
            "_messageHandlers", "_callbackHandlers", "_inlineHandlers", "_editedHandlers",
            "_postHandlers", "_mediaHandlers", "_anyHandlers", "_myStatusHandlers",
            "_memberHandlers", "_joinHandlers", "_reactionHandlers", "_pollHandlers",
            "_boostHandlers", "_checkoutHandlers", "_paymentHandlers", "_webappHandlers",
            "_paidMediaHandlers", "_guestHandlers", "_managedHandlers", "_generationStoppedHandlers",
            "_bizMsgHandlers", "_bizEditedHandlers", "_bizDeletedHandlers", "_bizConnectionHandlers",
            "_widgetQueryHandlers", "_sharedWidgetQueryHandlers",
            "_commandBlocks", "_stopCallbacks",
        )
        for attr in handler_attrs:
            setattr(self, attr, [])

        self._bizConnCache = {}
        self._bizConnCacheLock = threading.Lock()

    def _ensure_loop(self):
        if self._loop is None or self._loop.is_closed():
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
                self._loop_owned = True

    def _run_coro(self, coro):
        self._ensure_loop()
        if self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
            return future.result()
        return self._loop.run_until_complete(coro)
    def _schedule(self, coro):
        if _in_async_task():
            return coro
        return self._run_coro(coro)
    def _api_call(self, method: str, **params):
        return self._schedule(self._api.call(method, **_businessParams(params)))
    def _safe(self, method: str, **params):
        async def _guarded():
            try:
                return await self._api.call(method, **_businessParams(params))
            except Exception as e:
                _log.warning(method, err=e)
                return None
        return self._schedule(_guarded())
    def _editSafe(self, action: str, method: str, kind: str = "text", **params):
        async def _guarded():
            try:
                return await self._api.call(method, **params)
            except TelegramError as e:
                if not isNotModified(e):
                    _log.warning(action, kind=kind, err=e)
                return None
        return self._schedule(_guarded())
    def _api_callFile(self, method, fileKey, fileObj, filename, contentType, **params):
        return self._schedule(self._api.callFile(method, fileKey=fileKey, fileObj=fileObj, filename=filename, contentType=contentType, **_businessParams(params)))
    def _api_callMediaGroup(self, chatId, items, **params):
        return self._schedule(self._api.callMediaGroup(chatId, items, **_businessParams(params)))
    def _api_callRich(self, method, jsonField, jsonValue, attachments, **params):
        return self._schedule(self._api.callWithAttachments(method, jsonField, jsonValue, attachments, **_businessParams(params)))
    def _debug(self, action: str, **ctx):
        if self.debug:
            _log.debug(action, **ctx)

    def _markHandled(self, msgId):
        if msgId is not None:
            with self._handledMsgIdsLock:
                self._handledMsgIds[msgId] = True

    def _popHandled(self, msgId) -> bool:
        if msgId is None:
            return False
        with self._handledMsgIdsLock:
            if msgId in self._handledMsgIds:
                del self._handledMsgIds[msgId]
                return True
        return False

    def _checkCooldown(self, uid: int, kind: str) -> bool:
        if kind == "msg":
            store, interval, lock = self._userMsgTs, self._msgCooldown, self._userMsgTsLock
        else:
            store, interval, lock = self._userInlineTs, self._inlineCooldown, self._userInlineTsLock
        now = time.time()
        with lock:
            last = store.get(uid, 0.0)
            if now - last < interval:
                return False
            store[uid] = now
        return True

    def _submit(self, fn, *args, **kwargs):
        coro = self._wrap(fn, *args, **kwargs)
        self._ensure_loop()
        if self._loop.is_running():
            try:
                asyncio.get_running_loop()
                asyncio.ensure_future(coro)
            except RuntimeError:
                asyncio.run_coroutine_threadsafe(coro, self._loop)
        else:
            self._loop.run_until_complete(coro)

    async def _submitForUser(self, uid: int, fn, *args, callId: str = None):
        async with self._userCbLocksLock:
            if uid not in self._userCbLocks:
                self._userCbLocks[uid] = asyncio.Lock()
        lock = self._userCbLocks[uid]
        if not lock.locked():
            async with lock:
                await self._wrap(fn, *args)
            async with self._userCbLocksLock:
                if not lock.locked():
                    self._userCbLocks.pop(uid, None)
        else:
            self._debug("drop callback", uid=uid, reason="busy")
            if callId:
                try:
                    await self._api.call("answerCallbackQuery", callback_query_id=callId, cache_time=1)
                except Exception:
                    pass

    def _queueUserTask(self, uid: int, fn, callId: str = None):
        self._submit(self._submitForUser, uid, fn, callId=callId)

    async def _invoke(self, fn, *args, **kwargs):
        if asyncio.iscoroutinefunction(fn):
            await fn(*args, **kwargs)
        else:
            await asyncio.to_thread(fn, *args, **kwargs)

    async def _wrap(self, fn, *args, **kwargs):
        try:
            await self._invoke(fn, *args, **kwargs)
        except Exception:
            _log.error("handler", fn=getattr(fn, "__name__", repr(fn)), exc_info=True)

    async def _runCallback(self, parsed: CallbackQuery, fn):
        try:
            await self._invoke(fn, parsed)
        except Exception:
            _log.error("callback", fn=getattr(fn, "__name__", repr(fn)), exc_info=True)
        finally:
            if not parsed._answered and not parsed.isInline:
                with suppress(Exception):
                    await self._api.call("answerCallbackQuery", callback_query_id=parsed.id)

    def _msgFrom(self, target) -> tuple:
        if isinstance(target, (Message, BusinessMessage)):
            return target.chat_id, target.message_id
        if isinstance(target, CallbackQuery):
            msg = target.message
            return (msg.chat.id, msg.message_id) if msg else (None, None)
        if isinstance(target, dict):
            c = target.get("chat") or {}
            return c.get("id"), target.get("message_id")
        return target, None

    def _msgTarget(self, target) -> tuple:
        if isinstance(target, CallbackQuery):
            msg = target.message
            if msg:
                has_photo = bool(getattr(msg, "photo", None))
                return msg.chat.id, msg.message_id, has_photo, target.bc_id, getattr(msg, "ephemeral_message_id", None)
            return None, None, False, target.bc_id, None
        if isinstance(target, BusinessMessage):
            return target.chat_id, target.message_id, bool(getattr(target, "photo", None)), target.bc_id, None
        if isinstance(target, Message):
            return target.chat_id, target.message_id, bool(getattr(target, "photo", None)), None, target.ephemeralId
        if isinstance(target, dict):
            cid = chatId(target)
            msg_id = target.get("message_id")
            has_photo = bool(target.get("photo"))
            bc_id = target.get("business_connection_id")
            eph_id = target.get("ephemeral_message_id")
            return cid, msg_id, has_photo, bc_id, eph_id
        return chatId(target), None, False, None, None

    def _ephemeralFrom(self, target) -> tuple:
        if isinstance(target, CallbackQuery):
            msg = target.message
            return target.user_id, target.id, getattr(msg, "ephemeral_message_id", None) if msg else None
        if isinstance(target, (Message, BusinessMessage)):
            return target.user_id, None, target.ephemeralId
        if isinstance(target, dict):
            u = target.get("from") or {}
            m = target.get("message") or target
            return u.get("id"), target.get("id") if "data" in target else None, m.get("ephemeral_message_id")
        return userId(target), None, None

    def _ephemeralParams(self, receiver: Optional[int], callId: Optional[str], replaceCallbackMessage: bool = None) -> Optional[dict]:
        params = {}
        if receiver is not None:
            params["receiver_user_id"] = receiver
        if callId is not None:
            params["callback_query_id"] = callId
        if replaceCallbackMessage is not None:
            params["replace_callback_query_message"] = replaceCallbackMessage
        return params if params else None

    def _resolveMarkup(self, inline, keyboard, forceReply: bool = None):
        if inline is not None and keyboard is not None:
            raise ValueError("Pass inline= or keyboard=, not both")
        if inline is not None:
            return buildInlineKeyboard(inline)
        if keyboard is not None:
            return buildReplyKeyboard(keyboard, forceReply=forceReply)
        if forceReply:
            return {"force_reply": True}
        return None

    async def _runGuards(self, ctx) -> bool:
        for fn in self._guards:
            try:
                result = fn(ctx)
                if asyncio.iscoroutine(result):
                    result = await result
                if not result:
                    return False
            except Exception:
                _log.error("guard", fn=getattr(fn, "__name__", repr(fn)), exc_info=True)
                return False
        return True

    async def _runFilterList(self, filters, ctx) -> bool:
        for filter_fn in filters or []:
            try:
                ok = filter_fn(ctx)
                if asyncio.iscoroutine(ok):
                    ok = await ok
                if not ok:
                    return False
            except Exception:
                _log.error("filter", fn=getattr(filter_fn, "__name__", repr(filter_fn)), exc_info=True)
                return False
        return True

    def _submitFiltered(self, fn, ctx, filters):
        if filters:
            async def _checked(c):
                if await self._runFilterList(filters, c):
                    self._submit(fn, c)
            self._submit(_checked, ctx)
            return
        self._submit(fn, ctx)

    def _runInterceptors(self, raw: dict):
        for fn in self._interceptors:
            try:
                fn(raw)
            except Exception:
                _log.error("interceptor", fn=getattr(fn, "__name__", repr(fn)), exc_info=True)

    def _registerCommandBlock(self, block: CommandBlock):
        self._commandBlocks.append(block)

    def guard(self, fn):
        if not callable(fn):
            raise ValueError(f"guard() expects a function; got {type(fn).__name__}")
        self._guards.append(fn)
        return self

    def intercept(self, fn):
        self._interceptors.append(fn)
        return self

    def onStop(self, fn):
        self._stopCallbacks.append(fn)
        return self

    def command(self, *triggers, withSlash: bool = True, withoutSlash: bool = True, filters=None, starts=None, ends=None):
        triggers, spec = _businessArg(triggers)
        def decorator(fn):
            block = CommandBlock(
                self,
                list(triggers),
                withSlash=withSlash,
                withoutSlash=withoutSlash,
                filters=filters,
                starts=starts,
                ends=ends,
                business=spec,
            )
            fn(block)
            block._register()
            return fn
        return decorator

    def onMessage(self, commands=None, exact=None, starts=None, ends=None, contains=None, regex=None, withSlash: bool = True, withoutSlash: bool = True, filters=None):
        as_list = isinstance(commands, (list, tuple))
        raw, spec = _businessArg(tuple(commands) if as_list else (commands,))
        for v in (exact, starts, ends, contains, regex):
            if isinstance(v, business):
                raise ValueError("business marker must be the first argument")
        commands = (list(raw) or None) if as_list else (raw[0] if raw else None)
        if spec is not None:
            def decorator(fn):
                def _handle(msg: BusinessMessage):
                    if not spec.match(msg):
                        return
                    if any(f is not None for f in (commands, exact, starts, ends, contains, regex)):
                        args, match = matchText(msg.text, commands=commands, exact=exact, starts=starts, ends=ends, contains=contains, regex=regex, withSlash=withSlash, withoutSlash=withoutSlash)
                        if args is None:
                            return
                        msg.args = args
                        msg.match = match
                    self._submitFiltered(fn, msg, filters)
                self._bizMsgHandlers.append(_handle)
                return fn
            return decorator

        def decorator(fn):
            self._messageHandlers.append((
                TextRoute(fn, filters=filters, exact=exact, starts=starts, ends=ends, contains=contains, regex=regex),
                commands, withSlash, withoutSlash
            ))
            return fn
        return decorator

    def onCallback(self, *prefixes, filters=None):
        prefixes, spec = _businessArg(prefixes)
        pref_list = [p.lower() for p in prefixes]
        route_filters = list(filters or [])

        def decorator(fn):
            def _handle(raw: dict):
                data = raw.get("data") or ""
                dl = data.lower()
                if pref_list and not any(dl.startswith(p) for p in pref_list):
                    return
                uid = (raw.get("from") or {}).get("id", 0)

                async def _run():
                    cb = CallbackData(data)
                    parsed = CallbackQuery(raw, cb, gramly=self)
                    if spec is not None and not spec.match(parsed):
                        await self.ack(parsed)
                        return
                    if route_filters and not await self._runFilterList(route_filters, parsed):
                        await self.ack(parsed)
                        return
                    await self._runCallback(parsed, fn)

                self._queueUserTask(uid, _run, callId=raw.get("id"))
            self._callbackHandlers.append(_handle)
            return fn
        return decorator

    def onInline(self, minLength: int = 0):
        def decorator(fn):
            def _handle(raw: dict):
                q = raw.get("query", "")
                if len(q.strip()) < minLength:
                    return
                uid = (raw.get("from") or {}).get("id", 0)
                if not self._checkCooldown(uid, "inline"):
                    return
                self._submit(fn, InlineQuery(raw, self))
            self._inlineHandlers.append(_handle)
            return fn
        return decorator

    def _reg(self, target_list, fn):
        target_list.append(fn)
        return fn

    def onCheckout(self, fn): return self._reg(self._checkoutHandlers, fn)
    def onPayment(self, fn): return self._reg(self._paymentHandlers, fn)
    def onPaidMedia(self, fn): return self._reg(self._paidMediaHandlers, fn)
    def onJoinRequest(self, fn): return self._reg(self._joinHandlers, fn)
    def onMyStatus(self, fn): return self._reg(self._myStatusHandlers, fn)
    def onChatMember(self, fn): return self._reg(self._memberHandlers, fn)
    def onBoost(self, fn): return self._reg(self._boostHandlers, fn)
    def onReaction(self, fn): return self._reg(self._reactionHandlers, fn)
    def onPoll(self, fn): return self._reg(self._pollHandlers, fn)
    def onWebApp(self, fn): return self._reg(self._webappHandlers, fn)
    def onGuest(self, fn): return self._reg(self._guestHandlers, fn)
    def onManaged(self, fn): return self._reg(self._managedHandlers, fn)
    def onGenerationStopped(self, fn): return self._reg(self._generationStoppedHandlers, fn)
    def onBusinessConnection(self, fn): return self._reg(self._bizConnectionHandlers, fn)

    def onBusinessDeleted(self, fn, *businessMarker):
        _, spec = _businessArg(businessMarker)
        if spec is None:
            return self._reg(self._bizDeletedHandlers, fn)
        def _handle(raw):
            if spec.match(raw):
                self._submit(fn, raw)
        return self._reg(self._bizDeletedHandlers, _handle)
    def onBusinessEdited(self):
        return self.onEdited(business())

    def onBusinessMessage(self, commands=None, **kw):
        marker = [business(), *toList(commands)] if commands is not None else business()
        return self.onMessage(marker, **kw)

    def onMedia(self, *contentTypes):
        def decorator(fn):
            self._mediaHandlers.append((contentTypes, fn))
            return fn
        return decorator

    def onWidgetQuery(self, fn=None):
        return self._reg(self._widgetQueryHandlers, fn) if fn else lambda f: self._reg(self._widgetQueryHandlers, f)

    onWidget = onWidgetQuery

    def onSharedWidgetQuery(self, fn=None):
        return self._reg(self._sharedWidgetQueryHandlers, fn) if fn else lambda f: self._reg(self._sharedWidgetQueryHandlers, f)
    def onPost(self, filters=None):
        def decorator(fn):
            def _handle(raw: dict):
                msg = Message(raw, [], gramly=self)
                self._submitFiltered(fn, msg, filters)
            self._postHandlers.append(_handle)
            return fn
        return decorator

    def onAny(self, *businessMarker, filters=None):
        _, spec = _businessArg(businessMarker)
        def decorator(fn):
            def _handle(msg: Message):
                if spec is not None and not spec.match(msg):
                    return
                self._submitFiltered(fn, msg, filters)
            self._anyHandlers.append(_handle)
            return fn
        return decorator

    def onEdited(self, *businessMarker, filters=None):
        _, spec = _businessArg(businessMarker)
        def decorator(fn):
            def _handle(raw: dict):
                msg = BusinessMessage(raw, self) if spec is not None else Message(raw, [], gramly=self)
                if spec is not None and not spec.match(msg):
                    return
                self._submitFiltered(fn, msg, filters)
            self._editedHandlers.append(_handle)
            return fn
        return decorator

    def businessConnection(self, bcId: str):
        return self._schedule(self._businessConnection(bcId))

    async def _businessConnection(self, bcId: str):
        with self._bizConnCacheLock:
            conn = self._bizConnCache.get(bcId)
        if conn is not None:
            return conn
        try:
            raw = await self._api.call("getBusinessConnection", business_connection_id=bcId)
            conn = BusinessConnection(_to_raw(raw) if isinstance(raw, Obj) else raw)
            with self._bizConnCacheLock:
                self._bizConnCache[bcId] = conn
            return conn
        except Exception as e:
            _log.warning("getBusinessConnection", bc_id=bcId, err=e)
            return None

    def send(self, target, text, keyboard=None, inline=None, photo=None, forceReply: bool = None, **kwargs):
        cid = chatId(target)
        markup = self._resolveMarkup(inline, keyboard, forceReply=forceReply)
        if isinstance(text, dict):
            cleaned, attachments = _collectRichAttachments(text)
            self._debug("send", chat=cid, rich=True, blocks=len(text.get("blocks", [])) or None)
            return self._api_callRich("sendRichMessage", "rich_message", cleaned, attachments, chat_id=cid, reply_markup=markup, **kwargs)
        self._debug("send", chat=cid, text=f"{text[:40]!r}" if isinstance(text, str) else str(text))
        if photo is not None:
            return self._api_call("sendPhoto", chat_id=cid, photo=photo, caption=text, parse_mode=kwargs.pop("parseMode", None) or self.parseMode, reply_markup=markup, **kwargs)
        return self._api_call("sendMessage", chat_id=cid, text=text, parse_mode=kwargs.pop("parseMode", None) or self.parseMode, reply_markup=markup, **kwargs)
    def reply(self, message, text, keyboard=None, inline=None, photo=None, forceReply: bool = None, businessConnectionId: str = None, **kwargs):
        cid, msg_id = self._msgFrom(message)
        _, _, _, source_bc_id, _ = self._msgTarget(message)
        if source_bc_id is not None and businessConnectionId is not None and businessConnectionId != source_bc_id:
            raise ValueError("reply businessConnectionId must match the source message")
        if businessConnectionId is None:
            businessConnectionId = source_bc_id
        kwargs["reply_to_message_id"] = msg_id
        return self.send(
            cid, text, keyboard=keyboard, inline=inline, photo=photo,
            forceReply=forceReply, businessConnectionId=businessConnectionId,
            **kwargs,
        )

    def ephemeral(self, target, text, to=None, keyboard=None, inline=None, photo=None, replaceCallbackMessage: bool = None, **kwargs):
        cid = chatId(target)
        markup = self._resolveMarkup(inline, keyboard)
        receiver, call_id, reply_eph_id = self._ephemeralFrom(to if to is not None else target)
        reply_params = {"ephemeral_message_id": reply_eph_id} if reply_eph_id is not None else None
        eph_params = self._ephemeralParams(receiver, call_id, replaceCallbackMessage)
        self._debug("ephemeral", chat=cid, to=receiver)
        if isinstance(text, dict):
            cleaned, attachments = _collectRichAttachments(text)
            self._debug("ephemeral", chat=cid, to=receiver, rich=True)
            return self._api_callRich(
                "sendRichMessage", "rich_message", cleaned, attachments,
                chat_id=cid, reply_markup=markup, ephemeral_message_parameters=eph_params,
                reply_parameters=reply_params, **kwargs
            )
        if photo is not None:
            return self._api_call(
                "sendPhoto", chat_id=cid, photo=photo, caption=text,
                parse_mode=kwargs.pop("parseMode", None) or self.parseMode,
                reply_markup=markup, ephemeral_message_parameters=eph_params,
                reply_parameters=reply_params, **kwargs
            )
        return self._api_call(
            "sendMessage", chat_id=cid, text=text,
            parse_mode=kwargs.pop("parseMode", None) or self.parseMode,
            reply_markup=markup, ephemeral_message_parameters=eph_params,
            reply_parameters=reply_params, **kwargs
        )

    def edit(self, call, text, inline=None, photo=None, showCaption: bool = None, **kwargs):
        cid, msg_id, has_photo, bc_id, eph_id = self._msgTarget(call)
        markup = buildInlineKeyboard(inline) if inline is not None else None
        if eph_id is not None:
            self._debug("edit", chat=cid, ephemeral=eph_id)
            if photo is not None:
                media = _resolveInputMedia(photo, "photo", caption=text, parse_mode=kwargs.pop("parseMode", None) or self.parseMode, show_caption_above_media=showCaption)
                cleaned_media, attachments = _collectRichAttachments(media)
                return self._api_callRich("editEphemeralMessageMedia", "media", cleaned_media, attachments, chat_id=cid, ephemeral_message_id=eph_id, reply_markup=markup, **kwargs)
            if has_photo:
                return self._editSafe("edit", "editEphemeralMessageCaption", kind="ephemeral_caption", caption=text, chat_id=cid, ephemeral_message_id=eph_id, parse_mode=kwargs.pop("parseMode", None) or self.parseMode, show_caption_above_media=showCaption, reply_markup=markup, **kwargs)
            if isinstance(text, dict):
                cleaned, attachments = _collectRichAttachments(text)
                if attachments:
                    raise ValueError("edit: rich message references local files; use a file_id or URL when editing an ephemeral message")
                return self._editSafe("edit", "editEphemeralMessageText", kind="ephemeral_rich", rich_message=cleaned, chat_id=cid, ephemeral_message_id=eph_id, reply_markup=markup, **kwargs)
            return self._editSafe("edit", "editEphemeralMessageText", kind="ephemeral_text", text=text, chat_id=cid, ephemeral_message_id=eph_id, parse_mode=kwargs.pop("parseMode", None) or self.parseMode, reply_markup=markup, **kwargs)
        if isinstance(text, dict):
            cleaned, attachments = _collectRichAttachments(text)
            if attachments:
                raise ValueError("edit: rich message references local files; use a file_id or URL when editing")
            self._debug("edit", chat=cid, msg=msg_id, bc=bc_id, rich=True)
            return self._editSafe("edit", "editMessageText", kind="rich", rich_message=cleaned, chat_id=cid, message_id=msg_id, business_connection_id=bc_id, reply_markup=markup, **kwargs)
        self._debug("edit", chat=cid, msg=msg_id, bc=bc_id)
        if photo is not None:
            media = {"type": "photo", "media": photo, "caption": text, "parse_mode": self.parseMode}
            return self._editSafe("edit", "editMessageMedia", kind="media", media=media, chat_id=cid, message_id=msg_id, business_connection_id=bc_id, reply_markup=markup, **kwargs)
        if has_photo:
            return self._editSafe("edit", "editMessageCaption", kind="caption", caption=text, chat_id=cid, message_id=msg_id, business_connection_id=bc_id, parse_mode=kwargs.pop("parseMode", None) or self.parseMode, reply_markup=markup, **kwargs)
        return self._editSafe("edit", "editMessageText", kind="text", text=text, chat_id=cid, message_id=msg_id, business_connection_id=bc_id, parse_mode=kwargs.pop("parseMode", None) or self.parseMode, reply_markup=markup, **kwargs)
    def editMarkup(self, call, inline=None):
        cid, msg_id, _, bc_id, eph_id = self._msgTarget(call)
        markup = buildInlineKeyboard(inline) if inline is not None else None
        if eph_id is not None:
            return self._editSafe("editMarkup", "editEphemeralMessageReplyMarkup", kind="ephemeral", chat_id=cid, ephemeral_message_id=eph_id, reply_markup=markup)
        return self._editSafe("editMarkup", "editMessageReplyMarkup", chat_id=cid, message_id=msg_id, business_connection_id=bc_id, reply_markup=markup)
    def replace(self, call, text: str, inline=None, photo=None, **kwargs):
        cid, msg_id, has_photo, bc_id, _ = self._msgTarget(call)
        markup = buildInlineKeyboard(inline) if inline is not None else None
        if photo is not None:
            media = {"type": "photo", "media": photo, "caption": text, "parse_mode": self.parseMode}
            return self._editSafe("replace", "editMessageMedia", kind="swap_photo", media=media, chat_id=cid, message_id=msg_id, business_connection_id=bc_id, reply_markup=markup)
        if has_photo:
            self._safe("deleteMessage", chat_id=cid, message_id=msg_id)
            return self._api_call("sendMessage", chat_id=cid, text=text, business_connection_id=bc_id, parse_mode=kwargs.pop("parseMode", None) or self.parseMode, reply_markup=markup, **kwargs)
        return self._editSafe("replace", "editMessageText", text=text, chat_id=cid, message_id=msg_id, business_connection_id=bc_id, parse_mode=kwargs.pop("parseMode", None) or self.parseMode, reply_markup=markup, **kwargs)
    def editLiveLocation(self, call, latitude: float, longitude: float, inline=None, **kwargs):
        cid, msg_id, _, bc_id, _ = self._msgTarget(call)
        markup = buildInlineKeyboard(inline) if inline is not None else None
        return self._api_call("editMessageLiveLocation", chat_id=cid, message_id=msg_id, business_connection_id=bc_id, latitude=latitude, longitude=longitude, reply_markup=markup, **kwargs)
    def stopLiveLocation(self, call, inline=None, **kwargs):
        cid, msg_id, _, bc_id, _ = self._msgTarget(call)
        markup = buildInlineKeyboard(inline) if inline is not None else None
        return self._api_call("stopMessageLiveLocation", chat_id=cid, message_id=msg_id, business_connection_id=bc_id, reply_markup=markup, **kwargs)
    def alert(self, call, text: str = "", popup: bool = False):
        if isinstance(call, CallbackQuery):
            if call._answered:
                return
            call._answered = True
            cid = call.id
        elif isinstance(call, dict):
            cid = call.get("id")
        else:
            cid = call.id if hasattr(call, "id") else call
        try:
            return self._api_call("answerCallbackQuery", callback_query_id=cid, text=text, show_alert=popup)
        except Exception as e:
            _log.warning("alert", err=e)

    def ack(self, call):
        return self.alert(call, text="", popup=False)

    def delete(self, target, messageId=None, bcId: str = None) -> bool:
        try:
            if messageId is None:
                cid, msg_id, _, bc, eph_id = self._msgTarget(target)
                if eph_id is not None:
                    self._api_call("deleteEphemeralMessage", chat_id=cid, ephemeral_message_id=eph_id)
                    return True
                bc = bcId if bcId is not None else bc
                if bc is not None:
                    return bool(self._safe("deleteBusinessMessages", business_connection_id=bc, chat_id=cid, message_ids=[msg_id]))
                self._api_call("deleteMessage", chat_id=cid, message_id=msg_id)
                return True
            ids = list(messageId) if isinstance(messageId, (list, tuple, set)) else [messageId]
            cid = chatId(target)
            if bcId is not None:
                return bool(self._safe("deleteBusinessMessages", business_connection_id=bcId, chat_id=cid, message_ids=ids))
            if len(ids) == 1:
                self._api_call("deleteMessage", chat_id=cid, message_id=ids[0])
                return True
            return bool(self._safe("deleteMessages", chat_id=cid, message_ids=ids))
        except Exception:
            return False

    def deleteMessage(self, target, messageId: int, bcId: str = None) -> bool:
        return self.delete(target, messageId, bcId=bcId)

    def deleteMessages(self, target, messageIds: list, bcId: str = None) -> bool:
        return self.delete(target, messageIds, bcId=bcId)

    def deleteLater(self, message, delay: float, messageId=None, bcId: str = None):
        timer = threading.Timer(delay, self.delete, args=[message, messageId], kwargs={"bcId": bcId})
        timer.daemon = True
        self._pendingTimers.append(timer)
        timer.start()
        return timer

    def forward(self, target, message):
        from_chat, msg_id = self._msgFrom(message)
        return self._api_call("forwardMessage", chat_id=chatId(target), from_chat_id=from_chat, message_id=msg_id)
    def forwardMessages(self, target, fromChatId: int, messageIds: list, **kwargs):
        return self._api_call("forwardMessages", chat_id=chatId(target), from_chat_id=fromChatId, message_ids=messageIds, **kwargs)
    def copy(self, target, message, **kwargs):
        from_chat, msg_id = self._msgFrom(message)
        return self._api_call("copyMessage", chat_id=chatId(target), from_chat_id=from_chat, message_id=msg_id, **kwargs)
    def copyMessages(self, target, fromChatId: int, messageIds: list, **kwargs):
        return self._api_call("copyMessages", chat_id=chatId(target), from_chat_id=fromChatId, message_ids=messageIds, **kwargs)
    def action(self, target, action: str = "typing"):
        return self._safe("sendChatAction", chat_id=chatId(target), action=action)
    def pin(self, message, notify: bool = False):
        try:
            cid, msg_id, _, bc_id, _ = self._msgTarget(message)
            self._api_call("pinChatMessage", chat_id=cid, message_id=msg_id, disable_notification=not notify, business_connection_id=bc_id)
        except Exception as e:
            _log.warning("pin", err=e)

    def unpin(self, target, msgId: int = None, bcId: str = None):
        cid = chatId(target)
        try:
            if msgId is not None:
                self._api_call("unpinChatMessage", chat_id=cid, message_id=msgId, business_connection_id=bcId)
            else:
                self._api_call("unpinAllChatMessages", chat_id=cid)
        except Exception as e:
            _log.warning("unpin", err=e)

    def timer(self, seconds: float, fn: Callable, fireNow: bool = False) -> TimerHandle:
        stop_evt = threading.Event()
        handle = TimerHandle(stop_evt)
        def run_timer():
            if fireNow:
                try:
                    self._submit(fn)
                except Exception:
                    _log.error("timer callback error", exc_info=True)
            while not stop_evt.wait(seconds):
                try:
                    self._submit(fn)
                except Exception:
                    _log.error("timer callback error", exc_info=True)
        t = threading.Thread(target=run_timer, daemon=True)
        self._pendingTimers.append(t)
        t.start()
        return handle

    def sendWidget(self, target, widget, **kwargs):
        cid = chatId(target)
        w = widget.to_dict() if hasattr(widget, "to_dict") else (widget.raw if hasattr(widget, "raw") else widget)
        return self._api_call("sendWidget", chat_id=cid, widget=w, **kwargs)

    widget = sendWidget

    def sendSharedWidget(self, target, widget, **kwargs):
        cid = chatId(target)
        w = widget.to_dict() if hasattr(widget, "to_dict") else (widget.raw if hasattr(widget, "raw") else widget)
        return self._api_call("sendSharedWidget", chat_id=cid, widget=w, **kwargs)

    sharedWidget = sendSharedWidget

    def answerWidgetQuery(self, widgetQueryId: str, data=None, **kwargs):
        params = {"widget_query_id": widgetQueryId}
        if data is not None:
            params["data"] = data
        params.update(kwargs)
        return self._api_call("answerWidgetQuery", **params)
    def editMessageWidgetData(self, target, messageId: int, data: dict, **kwargs):
        cid = chatId(target)
        return self._api_call("editMessageWidgetData", chat_id=cid, message_id=messageId, data=data, **kwargs)
    def editSharedWidgetData(self, sharedWidgetQueryId: str, data: dict, **kwargs):
        return self._api_call("editSharedWidgetData", shared_widget_query_id=sharedWidgetQueryId, data=data, **kwargs)
    def photo(self, target, photo, caption=None, inline=None, keyboard=None, **kwargs):
        cid = chatId(target)
        markup = self._resolveMarkup(inline, keyboard)
        if isinstance(photo, list):
            media = [{"type": "photo", "media": p.get("file") if isinstance(p, dict) else p} for p in photo]
            if caption:
                media[0].update(caption=caption, parse_mode=kwargs.pop("parseMode", None) or self.parseMode)
            return self._api_call("sendMediaGroup", chat_id=cid, media=media, **kwargs)
        if hasattr(photo, "read") or isinstance(photo, (bytes, bytearray)):
            return self._api_callFile("sendPhoto", "photo", photo, "photo.jpg", "image/jpeg", chat_id=cid, caption=caption, parse_mode=kwargs.pop("parseMode", None) or self.parseMode, reply_markup=markup, **kwargs)
        return self._api_call("sendPhoto", chat_id=cid, photo=photo, caption=caption, parse_mode=kwargs.pop("parseMode", None) or self.parseMode, reply_markup=markup, **kwargs)
    def animation(self, target, animation, caption: str = None, **kwargs):
        return self._api_call("sendAnimation", chat_id=chatId(target), animation=animation, caption=caption, parse_mode=kwargs.pop("parseMode", None) or self.parseMode, **kwargs)
    def videoNote(self, target, videoNote, **kwargs):
        return self._api_call("sendVideoNote", chat_id=chatId(target), video_note=videoNote, **kwargs)
    def paidMedia(self, target, starCount: int, media: list, **kwargs):
        return self._api_call("sendPaidMedia", chat_id=chatId(target), star_count=starCount, media=media, **kwargs)
    def react(self, msg, *emojis, isBig=False):
        cid, mid, _, _, _ = self._msgTarget(msg)
        reaction = []
        for e in emojis:
            if isinstance(e, str) and e.isdigit():
                reaction.append({"type": "custom_emoji", "custom_emoji_id": e})
            else:
                reaction.append({"type": "emoji", "emoji": e})
        try:
            self._api_call("setMessageReaction", chat_id=cid, message_id=mid, reaction=reaction, is_big=isBig)
        except Exception as e:
            _log.warning("react", chat=cid, msg=mid, err=e)

    def _normalizeMediaItem(self, index: int, item, caption: str = None, parseMode: str = None) -> dict:
        fields = {"caption": caption, "parse_mode": (parseMode or self.parseMode) if caption else None}
        return _resolveInputMedia(item, index=index, extensionlessOnly=True, **fields)

    def media(self, target, items, caption: str = None, inline=None, keyboard=None, **kwargs):
        cid = chatId(target)
        markup = self._resolveMarkup(inline, keyboard)
        parse_mode = kwargs.pop("parseMode", None) or self.parseMode
        if not isinstance(items, list):
            items = [items]
        if not items:
            _log.warning("media", reason="empty_list")
            return None
        if len(items) > 10:
            _log.warning("media", truncated_from=len(items), truncated_to=10)
            items = items[:10]

        normalized = [
            self._normalizeMediaItem(i, item, caption if i == 0 else None, parseMode=parse_mode)
            for i, item in enumerate(items)
        ]

        if len(normalized) > 1:
            self._debug("media", chat=cid, count=len(normalized))
            return self._api_callMediaGroup(cid, normalized, reply_markup=markup, **kwargs)

        m = normalized[0]
        mtype = m.get("type", "photo")
        cap = m.get("caption")
        method, key = _MEDIA_METHODS.get(mtype, ("sendPhoto", "photo"))
        if m.get("_bytes") is not None:
            return self._api_callFile(method, fileKey=key, fileObj=m["_bytes"], filename=m["_filename"], contentType=m["_content_type"], chat_id=cid, caption=cap, parse_mode=parse_mode, reply_markup=markup, **kwargs)
        return self._api_call(method, chat_id=cid, **{key: m["media"]}, caption=cap, parse_mode=parse_mode, reply_markup=markup, **kwargs)
    def video(self, target, video, caption: str = None, inline=None, keyboard=None, **kwargs):
        markup = self._resolveMarkup(inline, keyboard)
        return self._api_call("sendVideo", chat_id=chatId(target), video=video, caption=caption, parse_mode=kwargs.pop("parseMode", None) or self.parseMode, reply_markup=markup, **kwargs)
    def document(self, target, doc, caption: str = None, inline=None, keyboard=None, **kwargs):
        markup = self._resolveMarkup(inline, keyboard)
        return self._api_call("sendDocument", chat_id=chatId(target), document=doc, caption=caption, parse_mode=kwargs.pop("parseMode", None) or self.parseMode, reply_markup=markup, **kwargs)
    def audio(self, target, audio, caption: str = None, inline=None, keyboard=None, **kwargs):
        markup = self._resolveMarkup(inline, keyboard)
        return self._api_call("sendAudio", chat_id=chatId(target), audio=audio, caption=caption, parse_mode=kwargs.pop("parseMode", None) or self.parseMode, reply_markup=markup, **kwargs)
    def voice(self, target, voice, caption: str = None, inline=None, keyboard=None, **kwargs):
        markup = self._resolveMarkup(inline, keyboard)
        return self._api_call("sendVoice", chat_id=chatId(target), voice=voice, caption=caption, parse_mode=kwargs.pop("parseMode", None) or self.parseMode, reply_markup=markup, **kwargs)
    def sticker(self, target, sticker, **kwargs):
        return self._api_call("sendSticker", chat_id=chatId(target), sticker=sticker, **kwargs)
    def location(self, target, latitude: float, longitude: float, **kwargs):
        return self._api_call("sendLocation", chat_id=chatId(target), latitude=latitude, longitude=longitude, **kwargs)
    def venue(self, target, latitude: float, longitude: float, title: str, address: str, **kwargs):
        return self._api_call("sendVenue", chat_id=chatId(target), latitude=latitude, longitude=longitude, title=title, address=address, **kwargs)
    def contact(self, target, phone: str, firstName: str, lastName: str = None, **kwargs):
        return self._api_call("sendContact", chat_id=chatId(target), phone_number=phone, first_name=firstName, last_name=lastName, **kwargs)
    def poll(self, target, question: str, options: list, isAnonymous: bool = True, pollType: str = "regular", correctOptionIds: list = None, explanation: str = None, allowsMultipleAnswers: bool = False, allowsRevoting: bool = None, shuffleOptions: bool = None, allowAddingOptions: bool = None, hideResultsUntilCloses: bool = None, description: str = None, openPeriod: int = None, closeDate: int = None, membersOnly: bool = None, countryCodes: list = None, **kwargs):
        params = dict(chat_id=chatId(target), question=question, options=[{"text": o} if isinstance(o, str) else o for o in options], is_anonymous=isAnonymous, type=pollType, allows_multiple_answers=allowsMultipleAnswers, explanation=explanation)
        if correctOptionIds is not None:
            params["correct_option_ids"] = correctOptionIds
        if allowsRevoting is not None:
            params["allows_revoting"] = allowsRevoting
        if shuffleOptions is not None:
            params["shuffle_options"] = shuffleOptions
        if allowAddingOptions is not None:
            params["allow_adding_options"] = allowAddingOptions
        if hideResultsUntilCloses is not None:
            params["hide_results_until_closes"] = hideResultsUntilCloses
        if description is not None:
            params["description"] = description
        if openPeriod is not None:
            params["open_period"] = openPeriod
        if closeDate is not None:
            params["close_date"] = closeDate
        if membersOnly is not None:
            params["members_only"] = membersOnly
        if countryCodes is not None:
            params["country_codes"] = countryCodes
        params.update(kwargs)
        return self._api_call("sendPoll", **params)
    def stopPoll(self, target, messageId: int, **kwargs):
        return self._api_call("stopPoll", chat_id=chatId(target), message_id=messageId, **kwargs)
    def dice(self, target, emoji: str = "🎲", **kwargs):
        return self._api_call("sendDice", chat_id=chatId(target), emoji=emoji, **kwargs)
    def game(self, target, gameShortName: str, inline=None, keyboard=None, **kwargs):
        markup = self._resolveMarkup(inline, keyboard)
        return self._api_call("sendGame", chat_id=chatId(target), game_short_name=gameShortName, reply_markup=markup, **kwargs)
    def livePhoto(self, target, photo, animation, caption: str = None, inline=None, keyboard=None, **kwargs):
        markup = self._resolveMarkup(inline, keyboard)
        return self._api_call("sendLivePhoto", chat_id=chatId(target), photo=photo, animation=animation, caption=caption, parse_mode=kwargs.pop("parseMode", None) or self.parseMode, reply_markup=markup, **kwargs)
    def messageDraft(self, target, draftId: int, text="", inline=None, keyboard=None, canStop: bool = None, keepOnStop: bool = None, **kwargs):
        if isinstance(text, dict):
            markup = self._resolveMarkup(inline, keyboard)
            cleaned, attachments = _collectRichAttachments(text)
            return self._api_callRich("sendRichMessageDraft", "rich_message", cleaned, attachments, chat_id=chatId(target), draft_id=draftId, reply_markup=markup, can_stop=canStop, keep_on_stop=keepOnStop, **kwargs)
        return self._api_call("sendMessageDraft", chat_id=chatId(target), draft_id=draftId, text=text, can_stop=canStop, keep_on_stop=keepOnStop, **kwargs)
    def checklist(self, target, title: str, tasks: list, **kwargs):
        return self._api_call("sendChecklist", chat_id=chatId(target), title=title, tasks=tasks, **kwargs)
    def editChecklist(self, target, messageId: int, title: str, tasks: list, **kwargs):
        return self._api_call("editMessageChecklist", chat_id=chatId(target), message_id=messageId, title=title, tasks=tasks, **kwargs)
    def ban(self, target, userId: int, until: int = 0, revokeMessages: bool = False):
        return self._safe("banChatMember", chat_id=chatId(target), user_id=userId, until_date=until, revoke_messages=revokeMessages)
    def unban(self, target, userId: int):
        return self._safe("unbanChatMember", chat_id=chatId(target), user_id=userId, only_if_banned=True)
    def kick(self, target, userId: int):
        self.ban(target, userId)
        self.unban(target, userId)

    def mute(self, target, userId: int, until: int = 0):
        return self._safe("restrictChatMember", chat_id=chatId(target), user_id=userId, permissions={"can_send_messages": False}, until_date=until)
    def unmute(self, target, userId: int):
        return self._safe("restrictChatMember", chat_id=chatId(target), user_id=userId, permissions=dict(DEFAULT_PERMISSIONS))
    def restrict(self, target, userId: int, permissions: dict, until: int = 0):
        return self._safe("restrictChatMember", chat_id=chatId(target), user_id=userId, permissions=permissions, until_date=until)
    def promote(self, target, userId: int, **permissions):
        return self._safe("promoteChatMember", chat_id=chatId(target), user_id=userId, **permissions)
    def setAdminTitle(self, target, userId: int, title: str):
        return self._safe("setChatAdministratorCustomTitle", chat_id=chatId(target), user_id=userId, custom_title=title)
    def setMemberTag(self, target, userId: int, tag: str):
        return self._safe("setChatMemberTag", chat_id=chatId(target), user_id=userId, tag=tag)
    def setChatPermissions(self, target, permissions: dict):
        return self._safe("setChatPermissions", chat_id=chatId(target), permissions=permissions)
    def approveJoin(self, target, userId: int = None):
        if isinstance(target, JoinRequest):
            cid, uid = target.chat_id, target.user_id
        else:
            cid, uid = chatId(target), userId
        return self._safe("approveChatJoinRequest", chat_id=cid, user_id=uid)
    def declineJoin(self, target, userId: int = None):
        if isinstance(target, JoinRequest):
            cid, uid = target.chat_id, target.user_id
        else:
            cid, uid = chatId(target), userId
        return self._safe("declineChatJoinRequest", chat_id=cid, user_id=uid)
    def answerJoinRequestQuery(self, target, userId: int, queryId: str, result: dict):
        return self._safe("answerChatJoinRequestQuery", chat_id=chatId(target), user_id=userId, query_id=queryId, result=result)
    def sendJoinRequestWebApp(self, target, userId: int, webAppUrl: str, **kwargs):
        return self._api_call("sendChatJoinRequestWebApp", chat_id=chatId(target), user_id=userId, web_app_url=webAppUrl, **kwargs)
    def leave(self, target):
        return self._safe("leaveChat", chat_id=chatId(target))
    def setChatTitle(self, target, title: str):
        return self._safe("setChatTitle", chat_id=chatId(target), title=title)
    def setChatDescription(self, target, description: str):
        return self._safe("setChatDescription", chat_id=chatId(target), description=description)
    def setChatPhoto(self, target, photo):
        return self._safe("setChatPhoto", chat_id=chatId(target), photo=photo)
    def deleteChatPhoto(self, target):
        return self._safe("deleteChatPhoto", chat_id=chatId(target))
    def banSender(self, target, senderChatId: int):
        return self._safe("banChatSenderChat", chat_id=chatId(target), sender_chat_id=senderChatId)
    def unbanSender(self, target, senderChatId: int):
        return self._safe("unbanChatSenderChat", chat_id=chatId(target), sender_chat_id=senderChatId)
    def exportInvite(self, target) -> str:
        return self._api_call("exportChatInviteLink", chat_id=chatId(target))
    def createInvite(self, target, **kwargs):
        return self._api_call("createChatInviteLink", chat_id=chatId(target), **kwargs)
    def editInvite(self, target, inviteLink: str, **kwargs):
        return self._api_call("editChatInviteLink", chat_id=chatId(target), invite_link=inviteLink, **kwargs)
    def revokeInvite(self, target, inviteLink: str):
        return self._api_call("revokeChatInviteLink", chat_id=chatId(target), invite_link=inviteLink)
    def createSubscriptionInvite(self, target, subscriptionPeriod: int, subscriptionPrice: int, **kwargs):
        return self._api_call("createChatSubscriptionInviteLink", chat_id=chatId(target), subscription_period=subscriptionPeriod, subscription_price=subscriptionPrice, **kwargs)
    def editSubscriptionInvite(self, target, inviteLink: str, **kwargs):
        return self._api_call("editChatSubscriptionInviteLink", chat_id=chatId(target), invite_link=inviteLink, **kwargs)
    def createTopic(self, target, name: str, **kwargs):
        return self._api_call("createForumTopic", chat_id=chatId(target), name=name, **kwargs)
    def editTopic(self, target, messageThreadId: int, **kwargs):
        return self._api_call("editForumTopic", chat_id=chatId(target), message_thread_id=messageThreadId, **kwargs)
    def closeTopic(self, target, messageThreadId: int):
        return self._safe("closeForumTopic", chat_id=chatId(target), message_thread_id=messageThreadId)
    def reopenTopic(self, target, messageThreadId: int):
        return self._safe("reopenForumTopic", chat_id=chatId(target), message_thread_id=messageThreadId)
    def deleteTopic(self, target, messageThreadId: int):
        return self._safe("deleteForumTopic", chat_id=chatId(target), message_thread_id=messageThreadId)
    def unpinTopicMessages(self, target, messageThreadId: int):
        return self._safe("unpinAllForumTopicMessages", chat_id=chatId(target), message_thread_id=messageThreadId)
    def editGeneralTopic(self, target, name: str):
        return self._safe("editGeneralForumTopic", chat_id=chatId(target), name=name)
    def closeGeneralTopic(self, target):
        return self._safe("closeGeneralForumTopic", chat_id=chatId(target))
    def reopenGeneralTopic(self, target):
        return self._safe("reopenGeneralForumTopic", chat_id=chatId(target))
    def hideGeneralTopic(self, target):
        return self._safe("hideGeneralForumTopic", chat_id=chatId(target))
    def unhideGeneralTopic(self, target):
        return self._safe("unhideGeneralForumTopic", chat_id=chatId(target))
    def unpinGeneralTopicMessages(self, target):
        return self._safe("unpinAllGeneralForumTopicMessages", chat_id=chatId(target))
    def answerInlineQuery(self, query, results: list, cacheTime: int = 30, isPersonal: bool = True, nextOffset: str = ""):
        qid = query.id if isinstance(query, InlineQuery) else query.get("id") if isinstance(query, dict) else query.id
        return self._safe("answerInlineQuery", inline_query_id=qid, results=results, cache_time=cacheTime, is_personal=isPersonal, next_offset=nextOffset)
    def answerWebAppQuery(self, webAppQueryId: str, result: dict):
        return self._safe("answerWebAppQuery", web_app_query_id=webAppQueryId, result=result)
    def answerGuestQuery(self, queryId: str, text: str, parseMode: str = None, **kwargs):
        return self._api_call("answerGuestQuery", guest_query_id=queryId, message={"text": text, "parse_mode": parseMode or self.parseMode, **kwargs})
    def answerShippingQuery(self, shippingQueryId: str, ok: bool, **kwargs):
        return self._api_call("answerShippingQuery", shipping_query_id=shippingQueryId, ok=ok, **kwargs)
    def savePreparedInlineMessage(self, userId: int, result: dict, allowUserChats: bool = None, allowBotChats: bool = None, allowGroupChats: bool = None, allowChannelChats: bool = None):
        return self._api_call("savePreparedInlineMessage", user_id=userId, result=result, allow_user_chats=allowUserChats, allow_bot_chats=allowBotChats, allow_group_chats=allowGroupChats, allow_channel_chats=allowChannelChats)
    def savePreparedKeyboardButton(self, text: str, requestUser: dict = None, requestChat: dict = None, requestManagedBot: dict = None, webApp: dict = None, loginUrl: dict = None, switchInline: str = None, switchInlineCurrent: str = None, switchInlineChosen: dict = None, copyText: dict = None, pay: bool = None):
        button_dict = {"text": text}
        fields = (
            ("request_users", requestUser),
            ("request_chat", requestChat),
            ("request_managed_bot", requestManagedBot),
            ("web_app", webApp),
            ("login_url", loginUrl),
            ("switch_inline_query", switchInline),
            ("switch_inline_query_current_chat", switchInlineCurrent),
            ("switch_inline_query_chosen_chat", switchInlineChosen),
            ("copy_text", copyText),
            ("pay", pay),
        )
        button_dict.update((k, v) for k, v in fields if v)
        return self._api_call("savePreparedKeyboardButton", button=button_dict)
    def invoice(self, target, title: str, description: str, payload: str, stars: int, photoUrl: str = None, inline=None, protectContent: bool = False, **kwargs):
        prices = [{"label": title, "amount": stars}]
        markup = buildInlineKeyboard(inline) if inline is not None else None
        return self._api_call("sendInvoice", chat_id=chatId(target), title=title, description=description, payload=payload, provider_token="", currency="XTR", prices=prices, photo_url=photoUrl, reply_markup=markup, protect_content=protectContent, **kwargs)
    def createInvoiceLink(self, title: str, description: str, payload: str, stars: int, photoUrl: str = None, subscriptionPeriod: int = None, **kwargs) -> str:
        prices = [{"label": title, "amount": stars}]
        return self._api_call("createInvoiceLink", title=title, description=description, payload=payload, provider_token="", currency="XTR", prices=prices, photo_url=photoUrl, subscription_period=subscriptionPeriod, **kwargs)
    def gift(self, userId: int, giftId: str, payForUpgrade: bool = False, **kwargs):
        return self._api_call("sendGift", user_id=userId, gift_id=giftId, pay_for_upgrade=payForUpgrade, **kwargs)
    def giftPremium(self, userId: int, **kwargs):
        return self._api_call("giftPremiumSubscription", user_id=userId, **kwargs)
    def refund(self, userId: int, chargeId: str) -> bool:
        try:
            self._api_call("refundStarPayment", user_id=userId, telegram_payment_charge_id=chargeId)
            return True
        except Exception as e:
            _log.warning("refund", err=e)
            return False

    def getStarTransactions(self, offset: int = 0, limit: int = 100):
        return self._api_call("getStarTransactions", offset=offset, limit=limit)
    def getStarBalance(self):
        try:
            result = self._api_call("getMyStarBalance")
            return result.amount if result else None
        except Exception as e:
            _log.warning("getStarBalance", err=e)
            return None

    def editStarSubscription(self, userId: int, telegramPaymentChargeId: str, isCanceled: bool):
        return self._safe("editUserStarSubscription", user_id=userId, telegram_payment_charge_id=telegramPaymentChargeId, is_canceled=isCanceled)
    def setEmojiStatus(self, userId: int, customEmojiId: str = None, **kwargs) -> bool:
        try:
            self._api_call("setUserEmojiStatus", user_id=userId, emoji_status={"custom_emoji_id": customEmojiId} if customEmojiId else {}, **kwargs)
            return True
        except Exception as e:
            _log.warning("setEmojiStatus", err=e)
            return False

    def getUserPhotos(self, userId: int, offset: int = 0, limit: int = 100):
        return self._api_call("getUserProfilePhotos", user_id=userId, offset=offset, limit=limit)
    def getUserAudios(self, userId: int, offset: int = 0, limit: int = 100):
        return self._api_call("getUserProfileAudios", user_id=userId, offset=offset, limit=limit)
    def getPersonalMessages(self, userId: int, **kwargs):
        return self._api_call("getUserPersonalChatMessages", user_id=userId, **kwargs)
    def getChat(self, target):
        return self._api_call("getChat", chat_id=chatId(target))
    def getChatMember(self, target, userId: int):
        return self._api_call("getChatMember", chat_id=chatId(target), user_id=userId)
    def getChatMemberCount(self, target) -> int:
        return self._api_call("getChatMemberCount", chat_id=chatId(target))
    def isAdmin(self, target, userId: int) -> bool:
        try:
            member = self.getChatMember(target, userId)
            return member.status in ("administrator", "creator")
        except Exception:
            return False

    def getAdmins(self, target, includeBots: bool = False) -> list:
        admins = self._api_call("getChatAdministrators", chat_id=chatId(target))
        if not includeBots:
            admins = [a for a in admins if not getattr(a, "is_bot", False)]
        return admins

    def getUserBoosts(self, target, userId: int):
        return self._api_call("getUserChatBoosts", chat_id=chatId(target), user_id=userId)
    def getMe(self):
        return self._api_call("getMe")
    def getFile(self, fileId: str):
        return self._api_call("getFile", file_id=fileId)
    def getWebhookInfo(self):
        return self._api_call("getWebhookInfo")
    def setMyCommands(self, commands: list, scope: dict = None, languageCode: str = None):
        return self._api_call("setMyCommands", commands=commands, scope=scope, language_code=languageCode)
    def deleteMyCommands(self, scope: dict = None, languageCode: str = None):
        return self._api_call("deleteMyCommands", scope=scope, language_code=languageCode)
    def getMyCommands(self, scope: dict = None, languageCode: str = None):
        return self._api_call("getMyCommands", scope=scope, language_code=languageCode)
    def setMyName(self, name: str, languageCode: str = None):
        return self._api_call("setMyName", name=name, language_code=languageCode)
    def getMyName(self, languageCode: str = None):
        return self._api_call("getMyName", language_code=languageCode)
    def setMyDescription(self, description: str, languageCode: str = None):
        return self._api_call("setMyDescription", description=description, language_code=languageCode)
    def getMyDescription(self, languageCode: str = None):
        return self._api_call("getMyDescription", language_code=languageCode)
    def setMyShortDescription(self, shortDescription: str, languageCode: str = None):
        return self._api_call("setMyShortDescription", short_description=shortDescription, language_code=languageCode)
    def getMyShortDescription(self, languageCode: str = None):
        return self._api_call("getMyShortDescription", language_code=languageCode)
    def setMyProfilePhoto(self, photo):
        return self._api_call("setMyProfilePhoto", photo=photo)
    def removeMyProfilePhoto(self, photoId: str = None):
        return self._api_call("removeMyProfilePhoto", custom_emoji_id=photoId)
    def setMenuButton(self, target=None, menuButton: dict = None):
        return self._api_call("setChatMenuButton", chat_id=chatId(target) if target is not None else None, menu_button=menuButton)
    def getMenuButton(self, target=None):
        return self._api_call("getChatMenuButton", chat_id=chatId(target) if target is not None else None)
    def setDefaultAdminRights(self, rights: dict = None, forChannels: bool = False):
        return self._api_call("setMyDefaultAdministratorRights", rights=rights, for_channels=forChannels)
    def getDefaultAdminRights(self, forChannels: bool = False):
        return self._api_call("getMyDefaultAdministratorRights", for_channels=forChannels)
    def logOut(self):
        return self._api_call("logOut")
    def closeBot(self):
        return self._api_call("close")
    def getAccessSettings(self):
        return self._api_call("getManagedBotAccessSettings")
    def setAccessSettings(self, settings: dict):
        return self._api_call("setManagedBotAccessSettings", **settings)
    def getManagedToken(self, userId: int):
        return self._api_call("getManagedBotToken", user_id=userId)
    def replaceManagedToken(self, userId: int):
        return self._api_call("replaceManagedBotToken", user_id=userId)
    def getStickerSet(self, name: str):
        return self._api_call("getStickerSet", name=name)
    def getCustomEmojiStickers(self, customEmojiIds: list):
        return self._api_call("getCustomEmojiStickers", custom_emoji_ids=customEmojiIds)
    def uploadStickerFile(self, userId: int, sticker, stickerFormat: str):
        return self._api_call("uploadStickerFile", user_id=userId, sticker=sticker, sticker_format=stickerFormat)
    def createNewStickerSet(self, userId: int, name: str, title: str, stickers: list, **kwargs):
        return self._api_call("createNewStickerSet", user_id=userId, name=name, title=title, stickers=stickers, **kwargs)
    def addStickerToSet(self, userId: int, name: str, sticker: dict):
        return self._api_call("addStickerToSet", user_id=userId, name=name, sticker=sticker)
    def setStickerPosition(self, sticker: str, position: int):
        return self._api_call("setStickerPositionInSet", sticker=sticker, position=position)
    def deleteStickerFromSet(self, sticker: str):
        return self._api_call("deleteStickerFromSet", sticker=sticker)
    def replaceStickerInSet(self, userId: int, name: str, oldSticker: str, sticker: dict):
        self._api_call("replaceStickerInSet", user_id=userId, name=name, old_sticker=oldSticker, sticker=sticker)

    def setStickerEmojiList(self, sticker: str, emojiList: list):
        return self._api_call("setStickerEmojiList", sticker=sticker, emoji_list=emojiList)
    def setStickerKeywords(self, sticker: str, keywords: list):
        return self._api_call("setStickerKeywords", sticker=sticker, keywords=keywords)
    def setStickerMaskPosition(self, sticker: str, maskPosition: dict):
        return self._api_call("setStickerMaskPosition", sticker=sticker, mask_position=maskPosition)
    def setStickerSetTitle(self, name: str, title: str):
        return self._api_call("setStickerSetTitle", name=name, title=title)
    def setStickerSetThumbnail(self, name: str, userId: int, thumbnail: str = None):
        return self._api_call("setStickerSetThumbnail", name=name, user_id=userId, thumbnail=thumbnail)
    def setCustomEmojiStickerSetThumbnail(self, name: str, customEmojiId: str = None):
        return self._api_call("setCustomEmojiStickerSetThumbnail", name=name, custom_emoji_id=customEmojiId)
    def deleteStickerSet(self, name: str):
        return self._api_call("deleteStickerSet", name=name)
    def setChatStickerSet(self, target, stickerSetName: str):
        return self._api_call("setChatStickerSet", chat_id=chatId(target), sticker_set_name=stickerSetName)
    def deleteChatStickerSet(self, target):
        return self._api_call("deleteChatStickerSet", chat_id=chatId(target))
    def getGifts(self):
        return self._api_call("getAvailableGifts")
    def convertGiftToStars(self, giftId: str):
        return self._api_call("convertGiftToStars", gift_id=giftId)
    def upgradeGift(self, giftId: str, **kwargs):
        return self._api_call("upgradeGift", gift_id=giftId, **kwargs)
    def transferGift(self, giftId: str, userId: int):
        self._api_call("transferGift", gift_id=giftId, user_id=userId)

    def businessSend(self, target, text: str, bcId: str, inline=None, keyboard=None, **kwargs):
        return self.send(target, text, inline=inline, keyboard=keyboard, businessConnectionId=bcId, **kwargs)

    def businessAction(self, target, bcId: str, action: str = "typing"):
        return self._safe("sendChatAction", chat_id=chatId(target), action=action, business_connection_id=bcId)
    def businessRead(self, target, maxMessageId: int, bcId: str):
        return self._safe("readBusinessMessage", chat_id=chatId(target), message_id=maxMessageId, business_connection_id=bcId)
    def businessDelete(self, target, messageIds: list, bcId: str):
        return self._safe("deleteBusinessMessages", chat_id=chatId(target), message_ids=toList(messageIds), business_connection_id=bcId)
    def setBusinessName(self, bcId: str, firstName: str, lastName: str = None):
        return self._api_call("setBusinessName", business_connection_id=bcId, first_name=firstName, last_name=lastName)
    def setBusinessUsername(self, bcId: str, username: str = None):
        return self._api_call("setBusinessUsername", business_connection_id=bcId, username=username)
    def setBusinessBio(self, bcId: str, bio: str = None):
        return self._api_call("setBusinessBio", business_connection_id=bcId, bio=bio)
    def setBusinessPhoto(self, bcId: str, photo, isPublic: bool = None):
        return self._api_call("setBusinessProfilePhoto", business_connection_id=bcId, photo=photo, is_public=isPublic)
    def removeBusinessPhoto(self, bcId: str, isPublic: bool = None):
        return self._api_call("removeBusinessProfilePhoto", business_connection_id=bcId, is_public=isPublic)
    def setBusinessGiftSettings(self, bcId: str, showGiftButton: bool, acceptedGiftTypes: dict):
        return self._api_call("setBusinessAccountGiftSettings", business_connection_id=bcId, show_gift_button=showGiftButton, accepted_gift_types=acceptedGiftTypes)
    def getBusinessStars(self, bcId: str):
        try:
            res = self._api_call("getBusinessAccountStarBalance", business_connection_id=bcId)
            return res.amount if res else None
        except Exception as e:
            _log.warning("getBusinessStars", bc_id=bcId, err=e)
            return None

    def transferBusinessStars(self, bcId: str, starCount: int):
        return self._api_call("transferBusinessAccountStars", business_connection_id=bcId, star_count=starCount)
    def getBusinessGifts(self, bcId: str, **kwargs):
        return self._api_call("getBusinessAccountGifts", business_connection_id=bcId, **kwargs)
    def convertBusinessGiftToStars(self, bcId: str, ownedGiftId: str):
        return self._api_call("convertBusinessAccountGiftToStars", business_connection_id=bcId, owned_gift_id=ownedGiftId)
    def upgradeBusinessGift(self, bcId: str, ownedGiftId: str, **kwargs):
        return self._api_call("upgradeBusinessAccountGift", business_connection_id=bcId, owned_gift_id=ownedGiftId, **kwargs)
    def transferBusinessGift(self, bcId: str, ownedGiftId: str, newOwnerChatId: int, starCount: int = None):
        return self._api_call("transferBusinessAccountGift", business_connection_id=bcId, owned_gift_id=ownedGiftId, new_owner_chat_id=newOwnerChatId, star_count=starCount)
    def postStory(self, bcId: str, content: dict, activePeriod: int = 86400, **kwargs):
        return self._api_call("postBusinessStory", business_connection_id=bcId, content=content, active_period=activePeriod, **kwargs)
    def editStory(self, bcId: str, storyId: int, content: dict, **kwargs):
        return self._api_call("editBusinessStory", business_connection_id=bcId, story_id=storyId, content=content, **kwargs)
    def deleteStory(self, bcId: str, storyId: int):
        return self._api_call("deleteBusinessStory", business_connection_id=bcId, story_id=storyId)
    def every(self, interval: float, fn, *args, **kwargs) -> TimerHandle:
        handle = TimerHandle()
        def _loop():
            while not handle.stopped and not self._stopEvent.is_set():
                time.sleep(interval)
                if handle.stopped or self._stopEvent.is_set():
                    break
                self._submit(fn, *args, **kwargs)
        t = threading.Thread(target=_loop, daemon=True)
        t.start()
        return handle

    def after(self, delay: float, fn, *args, **kwargs) -> TimerHandle:
        handle = TimerHandle()
        def _timer():
            time.sleep(delay)
            if not handle.stopped and not self._stopEvent.is_set():
                self._submit(fn, *args, **kwargs)
        t = threading.Thread(target=_timer, daemon=True)
        t.start()
        return handle

    def setWebhook(self, url: str, secretToken: str = None, allowedUpdates: list = None, maxConnections: int = None, ipAddress: str = None, certificate=None, dropPending: bool = False):
        params = {"url": url, "drop_pending_updates": dropPending}
        if secretToken:
            params["secret_token"] = secretToken
        if allowedUpdates is not None:
            params["allowed_updates"] = allowedUpdates
        if maxConnections:
            params["max_connections"] = maxConnections
        if ipAddress:
            params["ip_address"] = ipAddress
        if certificate:
            params["certificate"] = certificate
        self._api_call("setWebhook", **params)

    def deleteWebhook(self, dropPending: bool = False):
        self._api_call("deleteWebhook", drop_pending_updates=dropPending)

    def processUpdate(self, update: dict):
        raw = dict(update) if isinstance(update, Obj) else update
        if _in_async_task():
            return asyncio.create_task(self._dispatch(raw))
        return self._run_coro(self._dispatch(raw))

    async def _dispatch(self, update: dict):
        for update_type in ("message", "edited_message", "channel_post", "edited_channel_post"):
            if update_type in update and not await self._runGuards(Message(update[update_type], [], gramly=self)):
                return

        if "business_message" in update and not await self._runGuards(BusinessMessage(update["business_message"], self)):
            return
        if "edited_business_message" in update and not await self._runGuards(BusinessMessage(update["edited_business_message"], self)):
            return

        if "callback_query" in update:
            cb_raw = update["callback_query"]
            cb_data = CallbackData(cb_raw.get("data") or "")
            if not await self._runGuards(CallbackQuery(cb_raw, cb_data, gramly=self)):
                return

        if "inline_query" in update and not await self._runGuards(InlineQuery(update["inline_query"], self)):
            return

        if "chat_join_request" in update and not await self._runGuards(JoinRequest(update["chat_join_request"])):
            return

        for key, handlers, wrapper in (
            ("widget_query", self._widgetQueryHandlers, lambda r: WidgetQuery(r, self)),
            ("shared_widget_query", self._sharedWidgetQueryHandlers, lambda r: SharedWidgetQuery(r, self)),
            ("deleted_business_messages", self._bizDeletedHandlers, wrap),
            ("guest_message", self._guestHandlers, lambda r: GuestQuery(r, self)),
            ("managed_bot", self._managedHandlers, lambda r: ManagedBot(r, self)),
            ("stopped_message_generation", self._generationStoppedHandlers, wrap),
        ):
            if key in update:
                obj = wrapper(update[key])
                for h in handlers:
                    self._submit(h, obj)
                return

        if "business_connection" in update:
            conn = BusinessConnection(update["business_connection"])
            with self._bizConnCacheLock:
                self._bizConnCache[conn.id] = conn
            for h in self._bizConnectionHandlers:
                self._submit(h, conn)
            return

        if "business_message" in update:
            raw = update["business_message"]
            msg = BusinessMessage(raw, self)
            for block in self._commandBlocks:
                if block._business is not None and block._matchTrigger(raw):
                    block.dispatchMessage(raw, spec=block._business)
                    return
            for h in self._bizMsgHandlers:
                h(msg)
            return

        if "edited_business_message" in update:
            msg = BusinessMessage(update["edited_business_message"], self)
            for h in self._bizEditedHandlers:
                self._submit(h, msg)
            return

        if "message" in update:
            raw = update["message"]
            if "successful_payment" in raw:
                msg = Message(raw, [], gramly=self)
                for h in self._paymentHandlers:
                    self._submit(h, msg)
                return

            if "web_app_data" in raw:
                msg = Message(raw, [], gramly=self)
                for h in self._webappHandlers:
                    self._submit(h, msg)
                return

            text = raw.get("text") or raw.get("caption") or ""
            uid = (raw.get("from") or {}).get("id")
            if uid and not self._checkCooldown(uid, "msg"):
                return

            for block in self._commandBlocks:
                if block._business is None and block._matchTrigger(raw):
                    block.dispatchMessage(raw)
                    return

            matched = False
            for route, commands, with_slash, without_slash in self._messageHandlers:
                args, match = matchText(
                    text,
                    commands=commands,
                    exact=route.exact,
                    starts=route.starts,
                    ends=route.ends,
                    contains=route.contains,
                    regex=route.regex,
                    withSlash=with_slash,
                    withoutSlash=without_slash,
                )
                if args is not None:
                    matched = True
                    self._runInterceptors(raw)
                    self._markHandled(raw.get("message_id"))
                    msg = Message(raw, args, match=match, gramly=self)
                    self._submitFiltered(route.fn, msg, route.filters)
                    break

            if not matched:
                has_media = any(k in raw for k in ("photo", "video", "audio", "document", "voice", "animation", "sticker", "contact", "location", "venue", "poll", "dice", "users_shared", "chat_shared", "web_app_data"))
                if has_media and self._mediaHandlers:
                    for cts, fn in self._mediaHandlers:
                        if not cts or any(raw.get(ct) is not None for ct in cts):
                            self._runInterceptors(raw)
                            self._markHandled(raw.get("message_id"))
                            msg = Message(raw, [], gramly=self)
                            self._submit(fn, msg)
                            return

                if self._anyHandlers:
                    self._runInterceptors(raw)
                    self._markHandled(raw.get("message_id"))
                    msg = Message(raw, text.split(), gramly=self)
                    for h in self._anyHandlers:
                        h(msg)
            return

        if "callback_query" in update:
            raw = update["callback_query"]
            data = raw.get("data") or ""
            action = CallbackData(data).action.lower() if data else ""
            block_match = any(block._business is None and action in block._callbackRoutes for block in self._commandBlocks)
            if block_match:
                for block in self._commandBlocks:
                    if block._business is None and action in block._callbackRoutes:
                        block.dispatchCallback(raw)
                        return

            for h in self._callbackHandlers:
                h(raw)
            return

        if "inline_query" in update:
            for h in self._inlineHandlers:
                h(update["inline_query"])
            return

        if "edited_message" in update or "edited_channel_post" in update:
            raw = update.get("edited_message") or update.get("edited_channel_post")
            for h in self._editedHandlers:
                h(raw)
            return

        if "channel_post" in update:
            for h in self._postHandlers:
                h(update["channel_post"])
            return

        for key, handlers, wrapper in (
            ("my_chat_member", self._myStatusHandlers, wrap),
            ("chat_member", self._memberHandlers, wrap),
            ("chat_join_request", self._joinHandlers, JoinRequest),
            ("message_reaction", self._reactionHandlers, wrap),
            ("poll_answer", self._pollHandlers, wrap),
            ("pre_checkout_query", self._checkoutHandlers, lambda r: PreCheckout(r, self)),
            ("purchased_paid_media", self._paidMediaHandlers, wrap),
        ):
            if key in update:
                obj = wrapper(update[key])
                for h in handlers:
                    self._submit(h, obj)
                return

        if "chat_boost" in update or "removed_chat_boost" in update:
            raw = wrap(update.get("chat_boost") or update.get("removed_chat_boost"))
            for h in self._boostHandlers:
                self._submit(h, raw)
            return

    def _collectAllowedUpdates(self) -> list:
        allowed = set()
        for attr, updates in HANDLER_UPDATES.items():
            if getattr(self, attr, None):
                allowed.update(updates)
        if not allowed:
            allowed = {
                "message", "edited_message", "channel_post", "edited_channel_post",
                "inline_query", "callback_query", "my_chat_member", "chat_member",
                "chat_join_request", "message_reaction", "poll_answer", "chat_boost",
                "removed_chat_boost", "pre_checkout_query", "purchased_paid_media",
                "business_connection", "business_message", "edited_business_message",
                "deleted_business_messages", "guest_message", "managed_bot",
                "stopped_message_generation", "widget_query", "shared_widget_query",
            }
        return list(allowed)

    def run(self, pollTimeout: int = 30, skipPending: bool = False, allowedUpdates: list = None):
        self._ensure_loop()
        try:
            self._loop.run_until_complete(self.start(pollTimeout=pollTimeout, skipPending=skipPending, allowedUpdates=allowedUpdates))
        except (KeyboardInterrupt, SystemExit):
            self._debug("stop", reason="signal")
        finally:
            self._run_coro(self._shutdown())

    async def start(self, pollTimeout: int = 30, skipPending: bool = False, allowedUpdates: list = None):
        if allowedUpdates is None:
            allowedUpdates = self._collectAllowedUpdates()
        self._stopEvent.clear()
        offset = 0

        if skipPending:
            try:
                await self._api.call("getUpdates", offset=-1, timeout=0)
            except TelegramError as e:
                _log.warning("skip_pending", err=e)

        self._debug("polling_start")
        while not self._stopEvent.is_set():
            try:
                updates = await self._api.call("getUpdates", offset=offset, timeout=pollTimeout, limit=100, allowed_updates=allowedUpdates)
                if not updates:
                    continue
                if not isinstance(updates, list):
                    updates = [updates]
                for u in updates:
                    uid = u.update_id if hasattr(u, "update_id") else u.get("update_id", 0)
                    offset = uid + 1
                    raw = _to_raw(u) if isinstance(u, Obj) else u
                    await self._dispatch(raw)
            except TelegramError as e:
                if "conflict" in str(e).lower():
                    _log.error("polling", reason="conflict", err=e)
                    break
                _log.warning("polling", op="getUpdates", err=e)
                await asyncio.sleep(1)
            except Exception as e:
                if not self._stopEvent.is_set():
                    _log.warning("polling", err=e)
                    await asyncio.sleep(1)

        await self._shutdown()

    async def _shutdown(self):
        self._stopEvent.set()
        for t in self._pendingTimers:
            with suppress(Exception):
                t.cancel()
        self._pendingTimers.clear()
        await self._api.close()
        for fn in self._stopCallbacks:
            try:
                fn()
            except Exception:
                _log.error("stop callback error", exc_info=True)
        if self._loop_owned and self._loop is not None:
            self._loop.close()
            self._loop = None

    def close(self):
        self._run_coro(self._shutdown())
