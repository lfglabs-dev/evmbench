from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast


if TYPE_CHECKING:
    from collections.abc import Iterable


class ResponsesTranslationError(ValueError):
    """Raised when a Responses request cannot be represented by Chat Completions."""


def _content_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ''

    parts: list[str] = []
    for part in content:
        if isinstance(part, str):
            parts.append(part)
            continue
        if not isinstance(part, dict):
            continue
        part = cast('dict[str, Any]', part)
        part_type = part.get('type')
        if part_type in {'input_text', 'output_text', 'text'}:
            text = part.get('text')
            if isinstance(text, str):
                parts.append(text)
        elif part_type in {'input_image', 'image_url'}:
            msg = 'Responses image inputs are not supported by the Chat Completions adapter'
            raise ResponsesTranslationError(msg)
    return ''.join(parts)


def _tool_output_text(output: object) -> str:
    if isinstance(output, str):
        return output
    if isinstance(output, list):
        return _content_text(output)
    return json.dumps(output, separators=(',', ':'), ensure_ascii=False)


def _append_assistant_tool_call(messages: list[dict[str, Any]], tool_call: dict[str, Any]) -> None:
    if messages and messages[-1].get('role') == 'assistant' and 'tool_calls' in messages[-1]:
        messages[-1]['tool_calls'].append(tool_call)
        return
    messages.append({'role': 'assistant', 'content': None, 'tool_calls': [tool_call]})


def _responses_input_to_messages(  # noqa: C901, PLR0912
    instructions: object,
    response_input: object,
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    if isinstance(instructions, str) and instructions:
        messages.append({'role': 'developer', 'content': instructions})

    if isinstance(response_input, str):
        messages.append({'role': 'user', 'content': response_input})
        return messages
    if not isinstance(response_input, list):
        msg = 'Responses input must be a string or an array'
        raise ResponsesTranslationError(msg)

    for item in response_input:
        if not isinstance(item, dict):
            continue
        item = cast('dict[str, Any]', item)
        item_type = item.get('type')
        if item_type == 'message':
            role = item.get('role')
            if role not in {'system', 'developer', 'user', 'assistant'}:
                continue
            messages.append({'role': role, 'content': _content_text(item.get('content'))})
        elif item_type in {'function_call', 'custom_tool_call'}:
            name = item.get('name')
            call_id = item.get('call_id') or item.get('id')
            arguments = item.get('arguments') if item_type == 'function_call' else item.get('input')
            if not isinstance(name, str) or not isinstance(call_id, str):
                msg = f'Malformed {item_type} input item'
                raise ResponsesTranslationError(msg)
            if not isinstance(arguments, str):
                arguments = json.dumps(arguments or {}, separators=(',', ':'), ensure_ascii=False)
            _append_assistant_tool_call(
                messages,
                {
                    'id': call_id,
                    'type': 'function',
                    'function': {'name': name, 'arguments': arguments},
                },
            )
        elif item_type in {'function_call_output', 'custom_tool_call_output'}:
            call_id = item.get('call_id')
            if not isinstance(call_id, str):
                msg = f'Malformed {item_type} input item'
                raise ResponsesTranslationError(msg)
            messages.append(
                {
                    'role': 'tool',
                    'tool_call_id': call_id,
                    'content': _tool_output_text(item.get('output')),
                }
            )
        elif item_type == 'reasoning':
            # Chat Completions has no opaque reasoning-history item. Preserve only
            # provider-visible summary text when one is present.
            summary = _content_text(item.get('summary'))
            if summary:
                messages.append({'role': 'assistant', 'content': summary})

    return messages


def _responses_tools_to_chat(tools: object) -> tuple[list[dict[str, Any]], dict[str, str]]:
    if not isinstance(tools, list):
        return [], {}

    chat_tools: list[dict[str, Any]] = []
    tool_kinds: dict[str, str] = {}
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        tool = cast('dict[str, Any]', tool)
        tool_type = tool.get('type')
        name = tool.get('name')
        if tool_type == 'function' and isinstance(name, str):
            function = {
                key: tool[key]
                for key in ('name', 'description', 'parameters', 'strict')
                if key in tool
            }
            chat_tools.append({'type': 'function', 'function': function})
            tool_kinds[name] = 'function_call'
        elif tool_type == 'custom' and isinstance(name, str):
            # Chat Completions has no free-form tools. Expose the same tool as a
            # one-string function and translate the returned call back to a
            # Responses custom_tool_call event.
            description = tool.get('description')
            function: dict[str, Any] = {
                'name': name,
                'parameters': {
                    'type': 'object',
                    'properties': {'input': {'type': 'string'}},
                    'required': ['input'],
                    'additionalProperties': False,
                },
            }
            if isinstance(description, str):
                function['description'] = description
            chat_tools.append({'type': 'function', 'function': function})
            tool_kinds[name] = 'custom_tool_call'
        else:
            msg = f'Unsupported Responses tool type: {tool_type!r}'
            raise ResponsesTranslationError(msg)
    return chat_tools, tool_kinds


def responses_to_chat(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    """Convert a Codex Responses request into a streaming Chat request."""
    model = payload.get('model')
    if not isinstance(model, str) or not model:
        msg = 'Responses request is missing model'
        raise ResponsesTranslationError(msg)

    messages = _responses_input_to_messages(payload.get('instructions'), payload.get('input'))
    tools, tool_kinds = _responses_tools_to_chat(payload.get('tools'))
    request: dict[str, Any] = {
        'model': model,
        'messages': messages,
        'stream': True,
        'stream_options': {'include_usage': True},
    }
    if tools:
        request['tools'] = tools
    if isinstance(payload.get('parallel_tool_calls'), bool):
        request['parallel_tool_calls'] = payload['parallel_tool_calls']
    tool_choice = payload.get('tool_choice')
    if tool_choice in {'auto', 'none', 'required'}:
        request['tool_choice'] = tool_choice

    prompt_cache_key = payload.get('prompt_cache_key')
    if isinstance(prompt_cache_key, str) and prompt_cache_key:
        request['prompt_cache_key'] = prompt_cache_key

    reasoning = payload.get('reasoning')
    if isinstance(reasoning, dict) and isinstance(reasoning.get('effort'), str):
        request['reasoning_effort'] = reasoning['effort']

    max_tokens = payload.get('max_output_tokens')
    if isinstance(max_tokens, int) and max_tokens > 0:
        request['max_completion_tokens'] = max_tokens

    text = payload.get('text')
    text_format = text.get('format') if isinstance(text, dict) else None
    if isinstance(text_format, dict) and text_format.get('type') == 'json_schema':
        json_schema = {
            key: text_format[key]
            for key in ('name', 'schema', 'strict')
            if key in text_format
        }
        request['response_format'] = {'type': 'json_schema', 'json_schema': json_schema}

    return request, tool_kinds


def _usage_to_responses(usage: object) -> dict[str, Any]:
    usage_dict = cast('dict[str, Any]', usage) if isinstance(usage, dict) else {}
    prompt_details_value = usage_dict.get('prompt_tokens_details')
    prompt_details = cast('dict[str, Any]', prompt_details_value) if isinstance(prompt_details_value, dict) else {}
    completion_details_value = usage_dict.get('completion_tokens_details')
    completion_details = (
        cast('dict[str, Any]', completion_details_value) if isinstance(completion_details_value, dict) else {}
    )

    input_tokens = int(usage_dict.get('prompt_tokens') or usage_dict.get('input_tokens') or 0)
    output_tokens = int(usage_dict.get('completion_tokens') or usage_dict.get('output_tokens') or 0)
    cached_tokens = int(prompt_details.get('cached_tokens') or usage_dict.get('cached_input_tokens') or 0)
    reasoning_tokens = int(
        completion_details.get('reasoning_tokens') or usage_dict.get('reasoning_output_tokens') or 0
    )
    return {
        'input_tokens': input_tokens,
        'input_tokens_details': {'cached_tokens': cached_tokens},
        'output_tokens': output_tokens,
        'output_tokens_details': {'reasoning_tokens': reasoning_tokens},
        'total_tokens': int(usage_dict.get('total_tokens') or input_tokens + output_tokens),
    }


def _sse(events: Iterable[dict[str, Any]]) -> bytes:
    chunks: list[str] = []
    for event in events:
        event_type = event['type']
        chunks.append(f'event: {event_type}\ndata: {json.dumps(event, separators=(",", ":"))}\n\n')
    return ''.join(chunks).encode()


@dataclass
class ChatStreamAccumulator:
    """Aggregate Chat SSE deltas and emit the Responses subset Codex consumes."""

    model: str
    tool_kinds: dict[str, str]
    response_id: str = field(default_factory=lambda: f'resp_chat_{uuid.uuid4().hex}')
    created_at: int = field(default_factory=lambda: int(time.time()))
    content_parts: list[str] = field(default_factory=list)
    tool_calls: dict[int, dict[str, Any]] = field(default_factory=dict)
    usage: dict[str, Any] | None = None
    finished: bool = False

    def created_sse(self) -> bytes:
        return _sse([
            {
                'type': 'response.created',
                'response': {
                    'id': self.response_id,
                    'object': 'response',
                    'created_at': self.created_at,
                    'status': 'in_progress',
                    'model': self.model,
                },
            }
        ])

    def add_chunk(self, payload: dict[str, Any]) -> bytes:  # noqa: C901, PLR0912
        if isinstance(payload.get('model'), str):
            self.model = payload['model']
        if isinstance(payload.get('created'), int):
            self.created_at = payload['created']
        if isinstance(payload.get('usage'), dict):
            self.usage = payload['usage']

        choices = payload.get('choices')
        if choices in (None, []):
            return b''
        if not isinstance(choices, list) or not isinstance(choices[0], dict):
            msg = 'Malformed Chat Completions stream choices'
            raise ResponsesTranslationError(msg)
        if choices[0].get('finish_reason') is not None:
            self.finished = True
        delta = choices[0].get('delta')
        if not isinstance(delta, dict):
            return b''

        events: list[dict[str, Any]] = []
        content = delta.get('content')
        if isinstance(content, str) and content:
            self.content_parts.append(content)
            events.append({'type': 'response.output_text.delta', 'delta': content})

        tool_deltas = delta.get('tool_calls')
        if isinstance(tool_deltas, list):
            for position, raw_tool_delta in enumerate(tool_deltas):
                if not isinstance(raw_tool_delta, dict):
                    continue
                index = raw_tool_delta.get('index')
                if not isinstance(index, int):
                    index = position
                accumulated = self.tool_calls.setdefault(
                    index,
                    {'id': '', 'type': 'function', 'function': {'name': '', 'arguments': ''}},
                )
                call_id = raw_tool_delta.get('id')
                if isinstance(call_id, str) and call_id:
                    accumulated['id'] = call_id
                function_delta = raw_tool_delta.get('function')
                if not isinstance(function_delta, dict):
                    continue
                for key in ('name', 'arguments'):
                    fragment = function_delta.get(key)
                    if isinstance(fragment, str):
                        accumulated['function'][key] += fragment
        return _sse(events)

    def completed_sse(self) -> bytes:
        message: dict[str, Any] = {
            'role': 'assistant',
            'content': ''.join(self.content_parts) or None,
        }
        if self.tool_calls:
            message['tool_calls'] = [self.tool_calls[index] for index in sorted(self.tool_calls)]
        payload: dict[str, Any] = {
            'id': self.response_id,
            'created': self.created_at,
            'model': self.model,
            'choices': [{'message': message}],
        }
        if self.usage is not None:
            payload['usage'] = self.usage
        return chat_to_responses_sse(
            payload,
            self.tool_kinds,
            include_created=False,
            response_id_override=self.response_id,
        )

    def failed_sse(self, error: Exception) -> bytes:
        return _sse([
            {
                'type': 'response.failed',
                'response': {
                    'id': self.response_id,
                    'object': 'response',
                    'status': 'failed',
                    'error': {'code': 'chat_stream_error', 'message': str(error)},
                },
            }
        ])


def chat_to_responses_sse(  # noqa: C901, PLR0912
    payload: dict[str, Any],
    tool_kinds: dict[str, str],
    *,
    include_created: bool = True,
    response_id_override: str | None = None,
) -> bytes:
    """Convert one non-streaming Chat response into the SSE subset Codex consumes."""
    choices = payload.get('choices')
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        msg = 'Chat Completions response has no choices'
        raise ResponsesTranslationError(msg)
    message = choices[0].get('message')
    if not isinstance(message, dict):
        msg = 'Chat Completions response has no assistant message'
        raise ResponsesTranslationError(msg)

    response_id = response_id_override or payload.get('id')
    if not isinstance(response_id, str) or not response_id:
        response_id = f'resp_chat_{uuid.uuid4().hex}'
    events: list[dict[str, Any]] = []
    if include_created:
        events.append({
            'type': 'response.created',
            'response': {
                'id': response_id,
                'object': 'response',
                'created_at': int(payload.get('created') or time.time()),
                'status': 'in_progress',
                'model': payload.get('model'),
            },
        })

    content = message.get('content')
    if isinstance(content, str) and content:
        events.append(
            {
                'type': 'response.output_item.done',
                'item': {
                    'id': f'msg_{uuid.uuid4().hex}',
                    'type': 'message',
                    'role': 'assistant',
                    'status': 'completed',
                    'content': [{'type': 'output_text', 'text': content, 'annotations': []}],
                },
            }
        )

    tool_calls = message.get('tool_calls')
    if isinstance(tool_calls, list):
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue
            function = tool_call.get('function')
            if not isinstance(function, dict) or not isinstance(function.get('name'), str):
                continue
            name = function['name']
            arguments = function.get('arguments')
            if not isinstance(arguments, str):
                arguments = json.dumps(arguments or {}, separators=(',', ':'))
            call_id = tool_call.get('id')
            if not isinstance(call_id, str) or not call_id:
                call_id = f'call_{uuid.uuid4().hex}'
            kind = tool_kinds.get(name, 'function_call')
            if kind == 'custom_tool_call':
                try:
                    parsed = json.loads(arguments)
                except json.JSONDecodeError:
                    parsed = None
                custom_input = parsed.get('input') if isinstance(parsed, dict) else arguments
                if not isinstance(custom_input, str):
                    custom_input = json.dumps(custom_input, separators=(',', ':'), ensure_ascii=False)
                item = {
                    'type': 'custom_tool_call',
                    'call_id': call_id,
                    'name': name,
                    'input': custom_input,
                }
            else:
                item = {
                    'type': 'function_call',
                    'call_id': call_id,
                    'name': name,
                    'arguments': arguments,
                }
            events.append({'type': 'response.output_item.done', 'item': item})

    completed_response: dict[str, Any] = {
        'id': response_id,
        'object': 'response',
        'status': 'completed',
        'model': payload.get('model'),
        'output': [],
    }
    if isinstance(payload.get('usage'), dict):
        completed_response['usage'] = _usage_to_responses(payload['usage'])
    events.append(
        {
            'type': 'response.completed',
            'response': completed_response,
        }
    )
    return _sse(events)
