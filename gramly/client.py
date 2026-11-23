import asyncio
import json
import httpx
from gramly.errors import TelegramError
from gramly.types import wrap
from gramly.utils import _API_BASE, _MAX_RETRIES, mimeType

class AsyncAPIClient:
    def __init__(self, token: str, connectTimeout: int = 10, readTimeout: int = 30):
        self._token = token
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=connectTimeout, read=readTimeout, write=30, pool=5),
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
        )

    def _url(self, method: str) -> str:
        return _API_BASE.format(token=self._token, method=method)

    def _parse(self, raw: bytes):
        try:
            result = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            raise TelegramError("non-JSON response", 0)
        if not result.get("ok"):
            p = result.get("parameters") or {}
            raise TelegramError(
                result.get("description", "Unknown error"),
                result.get("error_code", 0),
                retryAfter=p.get("retry_after"),
            )
        return wrap(result.get("result"))

    def _safeParse(self, response) -> TelegramError:
        try:
            self._parse(response.content)
            return TelegramError("unknown error", response.status_code)
        except TelegramError as e:
            return e if e.errorCode else TelegramError(e.description, response.status_code)

    async def _with_retry(self, op):
        last_exc: Exception = RuntimeError("retry: no attempts made")
        for _ in range(_MAX_RETRIES):
            try:
                return await op()
            except TelegramError as e:
                last_exc = e
                if e.errorCode == 429 and e.retryAfter is not None:
                    await asyncio.sleep(e.retryAfter)
                    continue
                raise
            except httpx.HTTPStatusError as e:
                last_exc = self._safeParse(e.response)
                if last_exc.errorCode == 429 and last_exc.retryAfter is not None:
                    await asyncio.sleep(last_exc.retryAfter)
                    continue
                raise last_exc from e
        raise last_exc

    async def call(self, method: str, **params):
        params = {k: v for k, v in params.items() if v is not None}
        for k, v in list(params.items()):
            if isinstance(v, (dict, list)):
                params[k] = json.dumps(v)
        async def _do():
            resp = await self._client.post(self._url(method), data=params)
            resp.raise_for_status()
            return self._parse(resp.content)
        return await self._with_retry(_do)

    async def callFile(self, method: str, fileKey: str, fileObj, filename: str, contentType: str, **params):
        file_data = fileObj.read() if hasattr(fileObj, "read") else fileObj
        params = {k: v for k, v in params.items() if v is not None}
        data = {}
        for k, v in params.items():
            data[k] = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
        async def _do():
            resp = await self._client.post(self._url(method), data=data, files={fileKey: (filename, file_data, contentType)})
            resp.raise_for_status()
            return self._parse(resp.content)
        return await self._with_retry(_do)

    async def callMediaGroup(self, chatId: int, items: list, **params):
        has_bytes = any(isinstance(item.get("_bytes"), (bytes, bytearray)) for item in items)
        if not has_bytes:
            media_list = [{k: v for k, v in item.items() if not k.startswith("_")} for item in items]
            return await self.call("sendMediaGroup", chat_id=chatId, media=media_list, **params)
        fields = {"chat_id": str(chatId)}
        media_json = []
        for i, item in enumerate(items):
            raw_bytes = item.get("_bytes")
            entry = {k: v for k, v in item.items() if not k.startswith("_")}
            if raw_bytes is not None:
                attach_name = f"file{i}"
                filename = item.get("_filename", f"file{i}.jpg")
                ct = item.get("_content_type") or mimeType(filename.rsplit(".", 1)[-1] if "." in filename else "jpg")
                fields[attach_name] = (filename, bytes(raw_bytes) if not isinstance(raw_bytes, bytes) else raw_bytes, ct)
                entry["media"] = f"attach://{attach_name}"
            media_json.append(entry)
        fields["media"] = json.dumps(media_json)
        for k, v in params.items():
            if v is not None:
                fields[k] = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
        async def _do():
            resp = await self._client.post(self._url("sendMediaGroup"), files=fields)
            resp.raise_for_status()
            return self._parse(resp.content)
        return await self._with_retry(_do)

    async def callWithAttachments(self, method: str, jsonField: str, jsonValue, attachments: dict, **params):
        if not attachments:
            return await self.call(method, **{jsonField: jsonValue}, **params)
        fields = {jsonField: json.dumps(jsonValue)}
        for k, v in params.items():
            if v is not None:
                fields[k] = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
        async def _do():
            resp = await self._client.post(self._url(method), data=fields, files=dict(attachments))
            resp.raise_for_status()
            return self._parse(resp.content)
        return await self._with_retry(_do)

    async def close(self):
        try:
            await self._client.aclose()
        except Exception:
            pass
