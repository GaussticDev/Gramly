import asyncio
import re
from collections.abc import Callable
from dataclasses import dataclass
from gramly.types import CallbackData, Message, CallbackQuery, BusinessMessage, Obj
from gramly.utils import toList

class business:
    __slots__ = ("bcIds",)

    def __init__(self, bcId=None):
        ids = toList(bcId)
        if ids and not any(ids):
            raise ValueError("business(bcId=...): business_connection_id must not be empty")
        self.bcIds = frozenset(str(i) for i in ids if i)

    def __bool__(self) -> bool:
        return True

    def match(self, target) -> bool:
        bc_id = getattr(target, "bc_id", None)
        if bc_id is None and isinstance(target, (dict, Obj)):
            raw = target._d if isinstance(target, Obj) else target
            bc_id = raw.get("business_connection_id")
        if not bc_id:
            return False
        return not self.bcIds or bc_id in self.bcIds

    def __repr__(self) -> str:
        return f"business(bcId={sorted(self.bcIds)!r})"

def _businessSpec(value) -> business | None:
    if value is None or value is False:
        return None
    if value is True or value is business:
        return business()
    if isinstance(value, business):
        return value
    raise ValueError(f"business expects True/False or business(...), got {type(value).__name__!r}")

def _businessArg(values: tuple) -> tuple:
    found = [v for v in values if isinstance(v, business)]
    if len(found) > 1:
        raise ValueError("business marker passed twice")
    if found:
        values = tuple(v for v in values if v is not found[0])
    return values, (found[0] if found else None)

def _businessParams(params: dict) -> dict:
    params = dict(params)
    businessConnectionId = params.pop("businessConnectionId", None)
    rawBusinessConnectionId = params.get("business_connection_id")
    if businessConnectionId is not None and rawBusinessConnectionId is not None:
        if businessConnectionId != rawBusinessConnectionId:
            raise ValueError("businessConnectionId conflicts with business_connection_id")
    connectionId = businessConnectionId if businessConnectionId is not None else rawBusinessConnectionId
    if connectionId is not None:
        if not isinstance(connectionId, str) or not connectionId:
            raise ValueError("businessConnectionId must be a non-empty string")
        params["business_connection_id"] = connectionId
    return params

def matchText(
    text, commands=None, exact=None, starts=None, ends=None, contains=None, regex=None,
    withSlash: bool = True, withoutSlash: bool = True,
):
    if not text:
        return None, None
    t = text.strip()
    tl = t.lower()
    parts = t.split()
    fw = parts[0] if parts else ""

    if commands:
        cmds = [c.lstrip("/").lower() for c in toList(commands)]
        clean = fw.lstrip("/").split("@")[0].lower()
        has_slash = fw.startswith("/")
        if clean in cmds and ((has_slash and withSlash) or (not has_slash and withoutSlash)):
            return parts[1:], None

    if exact is not None:
        for e in toList(exact):
            if tl == e.lower():
                return [], None

    if starts is not None:
        for s in toList(starts):
            if tl.startswith(s.lower()):
                return t[len(s):].strip().split(), None

    if ends is not None:
        for e in toList(ends):
            if tl.endswith(e.lower()):
                return t[:-len(e)].strip().split(), None

    if contains is not None:
        if any(c.lower() in tl for c in toList(contains)):
            return t.split(), None

    if regex is not None:
        m = re.search(regex, t, re.IGNORECASE)
        if m:
            return list(m.groups()), m

    return None, None

class TextRoute:
    __slots__ = ("fn", "filters", "exact", "starts", "ends", "contains", "regex")

    def __init__(self, fn, filters=None, exact=None, starts=None, ends=None, contains=None, regex=None):
        self.fn = fn
        self.filters = list(filters or [])
        self.exact = exact
        self.starts = starts
        self.ends = ends
        self.contains = contains
        self.regex = regex

    @property
    def isPlainExact(self) -> bool:
        return self.exact is not None and self.starts is None and self.ends is None and self.contains is None and self.regex is None

    def match(self, text: str):
        tl = text.lower()
        if self.exact is not None:
            el = self.exact.lower()
            if tl == el:
                return [], None
            if tl.startswith(el + " "):
                return text[len(self.exact):].strip().split(), None
            return None, None
        if self.starts is not None:
            if tl.startswith(self.starts.lower()):
                return text[len(self.starts):].strip().split(), None
            return None, None
        if self.ends is not None:
            el = self.ends.lower()
            if tl.endswith(el):
                return text[:-len(self.ends)].strip().split(), None
            return None, None
        if self.contains is not None:
            if self.contains.lower() in tl:
                return text.split(), None
            return None, None
        if self.regex is not None:
            m = re.search(self.regex, text, re.IGNORECASE)
            if m:
                return list(m.groups()), m
            return None, None
        return None, None

class _RouteResult:
    __slots__ = ("route", "args", "match")

    def __init__(self, route, args, match):
        self.route = route
        self.args = args
        self.match = match

@dataclass
class CallbackRoute:
    fn: Callable
    filters: list | None = None

class CommandBlock:
    __slots__ = (
        "_gramly", "_triggersSingle", "_triggersMulti", "_triggerPrefixes", "_triggerSuffixes",
        "_withSlash", "_withoutSlash",
        "_filters", "_defaultFn", "_defaultFilters", "_exactRoutes", "_patternRoutes", "_callbackRoutes", "_registered",
        "_business",
    )

    def __init__(self, gramly, triggers: list, withSlash: bool = True, withoutSlash: bool = True, filters=None, starts=None, ends=None, business=None):
        self._gramly = gramly
        self._triggersSingle = set()
        self._triggersMulti = set()
        for t in triggers:
            tl = t.lstrip("/").lower()
            if " " in tl:
                self._triggersMulti.add(tl)
            else:
                self._triggersSingle.add(tl)
        self._triggerPrefixes = [p.lower() for p in toList(starts)]
        self._triggerSuffixes = [e.lower() for e in toList(ends)]
        if not (self._triggersSingle or self._triggersMulti or self._triggerPrefixes or self._triggerSuffixes):
            raise ValueError("CommandBlock: provide at least one of triggers, starts=, or ends=")
        self._withSlash = withSlash
        self._withoutSlash = withoutSlash
        self._filters = list(filters or [])
        self._defaultFn = None
        self._defaultFilters = []
        self._exactRoutes: dict = {}
        self._patternRoutes: list = []
        self._callbackRoutes: dict = {}
        self._registered = False
        self._business = _businessSpec(business)

    def _extractCommand(self, raw: dict):
        text = raw.get("text") or raw.get("caption") or ""
        t = text.strip()
        if not t:
            return None, None, None, None, None
        parts = t.split()
        fw = parts[0]
        has_slash = fw.startswith("/")
        tl = t.lower()
        return t, parts, fw, has_slash, tl

    def _resolveTrigger(self, raw: dict):
        extracted = self._extractCommand(raw)
        if extracted[0] is None:
            return None
        t, parts, fw, has_slash, tl = extracted
        if has_slash and not self._withSlash:
            return None
        if not has_slash and not self._withoutSlash:
            return None

        if fw.lstrip("/").split("@")[0].lower() in self._triggersSingle:
            return t, parts[1:]

        if self._triggersMulti:
            clean_tl = tl.lstrip("/")
            clean_t = t.lstrip("/")
            for mt in self._triggersMulti:
                if clean_tl == mt or clean_tl.startswith(mt + " "):
                    remainder = clean_t[len(mt):].strip()
                    return t, (remainder.split() if remainder else [])

        for p in self._triggerPrefixes:
            if tl.startswith(p):
                remainder = t[len(p):].strip()
                return t, (remainder.split() if remainder else [])

        for s in self._triggerSuffixes:
            if tl.endswith(s):
                remainder = t[:-len(s)].strip()
                return t, (remainder.split() if remainder else [])

        return None

    def default(self, fn=None, *, filters=None) -> Callable:
        def decorator(handler):
            self._defaultFn = handler
            self._defaultFilters = list(filters or [])
            return handler
        return decorator(fn) if fn is not None else decorator

    def on(self, *keys, exact=None, starts=None, ends=None, contains=None, regex=None, filters=None) -> Callable:
        def decorator(fn):
            route_filters = list(filters or [])
            if keys:
                for k in keys:
                    self._addRoute(k.lower(), TextRoute(fn, filters=route_filters, exact=k))
            else:
                route = TextRoute(fn, filters=route_filters, exact=exact, starts=starts, ends=ends, contains=contains, regex=regex)
                self._addRoute(exact.lower() if route.isPlainExact else None, route)
            return fn
        return decorator

    def _addRoute(self, exactKey: str | None, route: TextRoute) -> None:
        if exactKey is not None:
            if exactKey in self._exactRoutes:
                raise ValueError(f"CommandBlock.on: duplicate exact key {exactKey!r} already registered")
            self._exactRoutes[exactKey] = route
        else:
            self._patternRoutes.append(route)

    def onCallback(self, *actions, filters=None) -> Callable:
        def decorator(fn):
            route_filters = list(filters or [])
            for a in actions:
                key = a.lower()
                if key in self._callbackRoutes:
                    raise ValueError(f"CommandBlock.onCallback: duplicate action {key!r} already registered")
                self._callbackRoutes[key] = CallbackRoute(fn, route_filters)
            return fn
        return decorator

    def _register(self):
        if self._registered:
            return
        self._registered = True
        self._gramly._registerCommandBlock(self)

    def _matchTrigger(self, raw: dict) -> bool:
        return self._resolveTrigger(raw) is not None

    async def _runFilterList(self, filters, ctx):
        return await self._gramly._runFilterList(filters, ctx)

    def _findRoute(self, subtext: str) -> _RouteResult | None:
        first_word = subtext.split(" ", 1)[0].lower() if subtext else ""
        exact_route = self._exactRoutes.get(first_word) or self._exactRoutes.get(subtext.lower())
        if exact_route is not None:
            args, match = exact_route.match(subtext)
            if args is not None:
                return _RouteResult(exact_route, args, match)

        for route in self._patternRoutes:
            args, match = route.match(subtext)
            if args is not None:
                return _RouteResult(route, args, match)
        return None

    def _submitDefault(self, msg: Message, routeFilters=None, spec: business = None):
        if spec is not None and not spec.match(msg):
            return
        filters = self._filters + self._defaultFilters + list(routeFilters or [])
        self._gramly._submitFiltered(self._defaultFn, msg, filters)

    def dispatchMessage(self, raw: dict, spec: business = None):
        g = self._gramly
        uid = (raw.get("from") or {}).get("id")
        if uid and not g._checkCooldown(uid, "msg"):
            return
        resolved = self._resolveTrigger(raw)
        if resolved is None:
            return
        _, cmd_args = resolved

        g._runInterceptors(raw)
        g._markHandled(raw.get("message_id"))

        def _parsed(args, match=None):
            if spec is not None:
                return BusinessMessage(raw, g, args, match=match)
            return Message(raw, args, match=match, gramly=g)

        if not cmd_args:
            if self._defaultFn:
                self._submitDefault(_parsed([]), spec=spec)
            return

        subtext = " ".join(cmd_args)
        result = self._findRoute(subtext)
        if result is None:
            if self._defaultFn:
                self._submitDefault(_parsed(cmd_args), spec=spec)
            return

        msg = _parsed(result.args, result.match)
        if spec is not None and not spec.match(msg):
            return
        g._submitFiltered(result.route.fn, msg, self._filters + result.route.filters)

    def dispatchCallback(self, raw: dict):
        g = self._gramly
        uid = (raw.get("from") or {}).get("id", 0)
        data = raw.get("data") or ""
        if not data:
            return
        action = CallbackData(data).action.lower()
        route = self._callbackRoutes.get(action)
        if not route:
            return

        async def _run():
            cb = CallbackData(data)
            extra = list(cb.args)
            parsed = CallbackQuery(raw, cb, args=extra, gramly=g)

            async def _answer(text="", popup=False):
                res = g.alert(parsed, text=text, popup=popup)
                if asyncio.isfuture(res):
                    await res

            if not await self._runFilterList(self._filters, parsed):
                await _answer()
                return
            if not await self._runFilterList(route.filters, parsed):
                await _answer()
                return
            await g._runCallback(parsed, route.fn)

        g._queueUserTask(uid, _run, callId=raw.get("id"))
