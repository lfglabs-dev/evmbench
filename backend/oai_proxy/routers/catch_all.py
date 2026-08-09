import json
from collections.abc import AsyncIterator, Iterable
from functools import lru_cache
from urllib.parse import quote

import httpx
from fastapi import APIRouter, HTTPException, Request
from starlette.background import BackgroundTask
from starlette.responses import Response, StreamingResponse

from api.util.aes_gcm import decrypt_token, derive_key
from oai_proxy.core.config import settings
from oai_proxy.responses_chat_adapter import (
    ChatStreamAccumulator,
    ResponsesTranslationError,
    responses_to_chat,
)


# Marker token that triggers use of the static key
STATIC_KEY_MARKER = 'STATIC'
HOP_BY_HOP_HEADERS = {
    'connection',
    'host',
    'keep-alive',
    'proxy-authenticate',
    'proxy-authorization',
    'te',
    'trailers',
    'transfer-encoding',
    'upgrade',
}

router = APIRouter()


@lru_cache(maxsize=1)
def _aesgcm_key() -> bytes:
    return derive_key(settings.OAI_PROXY_AES_KEY.get_secret_value())


@lru_cache(maxsize=1)
def _get_static_key() -> str | None:
    if settings.OAI_PROXY_STATIC_KEY:
        return settings.OAI_PROXY_STATIC_KEY.get_secret_value()
    return None


def _decrypt_token(token: str) -> str:
    try:
        return decrypt_token(token, key=_aesgcm_key())
    except ValueError as err:
        raise HTTPException(status_code=401, detail='Invalid token') from err


def _resolve_openai_key(token: str) -> str:
    """Resolve the actual OpenAI key from the provided token.

    If token is STATIC_KEY_MARKER, use the static key (if configured).
    Otherwise, decrypt the encrypted token.
    """
    if token == STATIC_KEY_MARKER:
        static_key = _get_static_key()
        if not static_key:
            raise HTTPException(
                status_code=501,
                detail='Static key not configured on proxy',
            )
        return static_key
    return _decrypt_token(token)


def _get_authorization_token(request: Request) -> str:
    auth_header = request.headers.get('authorization')
    if not auth_header:
        raise HTTPException(status_code=401, detail='Missing Authorization header')
    scheme, _, token = auth_header.partition(' ')
    if scheme.lower() != 'bearer' or not token:
        raise HTTPException(status_code=401, detail='Invalid Authorization header')
    return token


def _filter_headers(items: Iterable[tuple[str, str]]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key, value in items:
        key_lower = key.lower()
        if key_lower in HOP_BY_HOP_HEADERS:
            continue
        if key_lower == 'content-length':
            continue
        headers[key_lower] = value
    return headers


async def _proxy_request(request: Request, path: str) -> StreamingResponse:
    token = _get_authorization_token(request)
    openai_key = _resolve_openai_key(token)
    forward_headers = _filter_headers(request.headers.items())
    forward_headers['authorization'] = f'Bearer {openai_key}'

    target_path = path.lstrip('/')
    encoded_path = quote(target_path, safe='/')
    upstream_base_url = settings.OAI_PROXY_UPSTREAM_BASE_URL.rstrip('/')
    if upstream_base_url.endswith('/v1') and encoded_path.startswith('v1/'):
        encoded_path = encoded_path[3:]
    target_url = f'{upstream_base_url}/{encoded_path}' if encoded_path else upstream_base_url

    body = request.stream()
    params = request.query_params

    client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=None))
    upstream = await client.send(
        client.build_request(
            request.method,
            target_url,
            params=params,
            headers=forward_headers,
            content=body,
        ),
        stream=True,
    )

    response_headers = _filter_headers(upstream.headers.items())

    async def _cleanup() -> None:
        await upstream.aclose()
        await client.aclose()

    return StreamingResponse(
        upstream.aiter_raw(),
        status_code=upstream.status_code,
        headers=response_headers,
        background=BackgroundTask(_cleanup),
    )


async def _adapt_responses_to_chat(request: Request) -> Response:  # noqa: C901, PLR0915
    """Serve Codex's Responses wire API through a Chat Completions upstream."""
    token = _get_authorization_token(request)
    openai_key = _resolve_openai_key(token)
    try:
        payload = await request.json()
    except ValueError as err:
        raise HTTPException(status_code=400, detail='Request body must be valid JSON') from err
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail='Request body must be a JSON object')

    try:
        chat_payload, tool_kinds = responses_to_chat(payload)
    except ResponsesTranslationError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    forward_headers = _filter_headers(request.headers.items())
    forward_headers['authorization'] = f'Bearer {openai_key}'
    forward_headers['content-type'] = 'application/json'
    upstream_base_url = settings.OAI_PROXY_UPSTREAM_BASE_URL.rstrip('/')
    if not upstream_base_url.endswith('/v1'):
        upstream_base_url = f'{upstream_base_url}/v1'
    target_url = f'{upstream_base_url}/chat/completions'

    client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=None))
    upstream_request = client.build_request('POST', target_url, headers=forward_headers, json=chat_payload)
    try:
        upstream = await client.send(upstream_request, stream=True)
    except httpx.HTTPError as err:
        await client.aclose()
        raise HTTPException(status_code=502, detail=f'Chat Completions upstream failed: {err}') from err

    if upstream.is_error:
        content = await upstream.aread()
        await upstream.aclose()
        await client.aclose()
        return Response(
            content,
            status_code=upstream.status_code,
            headers=_filter_headers(upstream.headers.items()),
            media_type=upstream.headers.get('content-type'),
        )

    accumulator = ChatStreamAccumulator(model=chat_payload['model'], tool_kinds=tool_kinds)

    async def stream_responses() -> AsyncIterator[bytes]:
        yield accumulator.created_sse()
        done_marker = False
        try:
            async for line in upstream.aiter_lines():
                if not line.startswith('data:'):
                    continue
                data = line.removeprefix('data:').strip()
                if data == '[DONE]':
                    done_marker = True
                    break
                chunk = json.loads(data)
                if not isinstance(chunk, dict):
                    msg = 'Chat Completions stream chunk must be a JSON object'
                    raise ResponsesTranslationError(msg)  # noqa: TRY301
                translated = accumulator.add_chunk(chunk)
                # A comment still advances the downstream connection when a
                # chunk contains only tool arguments or usage.
                yield translated or b': chat-completions-chunk\n\n'
            if not done_marker and not accumulator.finished:
                msg = 'Chat Completions stream ended before a completion marker'
                raise ResponsesTranslationError(msg)  # noqa: TRY301
            yield accumulator.completed_sse()
        except (httpx.HTTPError, ValueError, ResponsesTranslationError) as err:
            yield accumulator.failed_sse(err)
        finally:
            await upstream.aclose()
            await client.aclose()

    return StreamingResponse(stream_responses(), media_type='text/event-stream')


@router.api_route('/', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'])
@router.api_route('/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'])
async def proxy_all(request: Request, path: str = '') -> Response:
    normalized_path = path.strip('/')
    if (
        settings.OAI_PROXY_RESPONSES_MODE == 'chat_completions'
        and request.method == 'POST'
        and normalized_path in {'responses', 'v1/responses'}
    ):
        return await _adapt_responses_to_chat(request)
    return await _proxy_request(request, path)
