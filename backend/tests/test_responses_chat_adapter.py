# ruff: noqa: PT009, PT027

import json
import os
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from unittest.mock import patch


os.environ.setdefault('OAI_PROXY_AES_KEY', 'unit-test-only')

import httpx

from oai_proxy import app
from oai_proxy.core.config import settings
from oai_proxy.responses_chat_adapter import (
    ChatStreamAccumulator,
    ResponsesTranslationError,
    chat_to_responses_sse,
    responses_to_chat,
)


class FakeChatHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get('content-length', '0'))
        request = json.loads(self.rfile.read(length))
        self.server.last_request = request  # type: ignore[attr-defined]
        chunks = [
            {
                'id': 'chatcmpl_integration',
                'model': request['model'],
                'choices': [{'delta': {'role': 'assistant', 'content': 'adapter '}}],
            },
            {'choices': [{'delta': {'content': 'ok'}, 'finish_reason': 'stop'}]},
            {
                'choices': [],
                'usage': {'prompt_tokens': 12, 'completion_tokens': 3, 'total_tokens': 15},
            },
        ]
        body = ''.join(
            [*(f'data: {json.dumps(chunk)}\n\n' for chunk in chunks), 'data: [DONE]\n\n']
        ).encode()
        self.send_response(200)
        self.send_header('content-type', 'text/event-stream')
        self.send_header('content-length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        del format, args


def parse_sse(body: bytes) -> list[dict]:
    events = []
    for block in body.decode().strip().split('\n\n'):
        data_line = next((line for line in block.splitlines() if line.startswith('data: ')), None)
        if data_line is None:
            continue
        events.append(json.loads(data_line.removeprefix('data: ')))
    return events


class ResponsesToChatTests(unittest.TestCase):
    def test_translates_messages_tools_reasoning_and_outputs(self) -> None:
        request, tool_kinds = responses_to_chat(
            {
                'model': 'gpt-5.6-sol',
                'instructions': 'Audit carefully.',
                'reasoning': {'effort': 'low'},
                'parallel_tool_calls': True,
                'tool_choice': 'auto',
                'prompt_cache_key': 'audit-1',
                'input': [
                    {
                        'type': 'message',
                        'role': 'user',
                        'content': [{'type': 'input_text', 'text': 'Inspect the repo.'}],
                    },
                    {
                        'type': 'function_call',
                        'call_id': 'call_1',
                        'name': 'shell_command',
                        'arguments': '{"command":"pwd"}',
                    },
                    {
                        'type': 'function_call_output',
                        'call_id': 'call_1',
                        'output': 'workspace',
                    },
                ],
                'tools': [
                    {
                        'type': 'function',
                        'name': 'shell_command',
                        'description': 'Run a command',
                        'parameters': {
                            'type': 'object',
                            'properties': {'command': {'type': 'string'}},
                            'required': ['command'],
                        },
                    }
                ],
            }
        )

        self.assertEqual(request['model'], 'gpt-5.6-sol')
        self.assertTrue(request['stream'])
        self.assertEqual(request['stream_options'], {'include_usage': True})
        self.assertEqual(request['reasoning_effort'], 'low')
        self.assertEqual(request['tool_choice'], 'auto')
        self.assertEqual(request['prompt_cache_key'], 'audit-1')
        self.assertEqual(request['messages'][0], {'role': 'developer', 'content': 'Audit carefully.'})
        self.assertEqual(request['messages'][2]['tool_calls'][0]['id'], 'call_1')
        self.assertEqual(request['messages'][3]['tool_call_id'], 'call_1')
        self.assertEqual(request['tools'][0]['function']['name'], 'shell_command')
        self.assertEqual(tool_kinds, {'shell_command': 'function_call'})

    def test_translates_custom_tool_to_string_function(self) -> None:
        request, tool_kinds = responses_to_chat(
            {
                'model': 'gpt-5.6-sol',
                'input': 'Patch the file.',
                'tools': [{'type': 'custom', 'name': 'apply_patch', 'description': 'Apply a patch'}],
            }
        )
        function = request['tools'][0]['function']
        self.assertEqual(function['parameters']['required'], ['input'])
        self.assertEqual(tool_kinds, {'apply_patch': 'custom_tool_call'})

    def test_rejects_images_instead_of_silently_dropping_them(self) -> None:
        with self.assertRaisesRegex(ResponsesTranslationError, 'image inputs'):
            responses_to_chat(
                {
                    'model': 'gpt-5.6-sol',
                    'input': [
                        {
                            'type': 'message',
                            'role': 'user',
                            'content': [{'type': 'input_image', 'image_url': 'data:image/png;base64,x'}],
                        }
                    ],
                }
            )


class ChatToResponsesTests(unittest.TestCase):
    def test_assembles_fragmented_parallel_tool_calls(self) -> None:
        accumulator = ChatStreamAccumulator(
            model='gpt-5.6-sol',
            tool_kinds={'exec_command': 'function_call', 'apply_patch': 'custom_tool_call'},
        )
        accumulator.add_chunk(
            {
                'choices': [
                    {
                        'delta': {
                            'tool_calls': [
                                {
                                    'index': 0,
                                    'id': 'call_exec',
                                    'function': {'name': 'exec_', 'arguments': '{"cmd":"'},
                                },
                                {
                                    'index': 1,
                                    'id': 'call_patch',
                                    'function': {'name': 'apply_patch', 'arguments': '{"input":"patch'},
                                },
                            ]
                        }
                    }
                ]
            }
        )
        accumulator.add_chunk(
            {
                'choices': [
                    {
                        'delta': {
                            'tool_calls': [
                                {'index': 0, 'function': {'name': 'command', 'arguments': 'pwd"}'}},
                                {'index': 1, 'function': {'arguments': ' text"}'}},
                            ]
                        }
                    }
                ],
                'usage': {'prompt_tokens': 20, 'completion_tokens': 8, 'total_tokens': 28},
            }
        )
        events = parse_sse(accumulator.completed_sse())
        items = [event['item'] for event in events if event['type'] == 'response.output_item.done']
        self.assertEqual(items[0]['name'], 'exec_command')
        self.assertEqual(items[0]['arguments'], '{"cmd":"pwd"}')
        self.assertEqual(items[1]['type'], 'custom_tool_call')
        self.assertEqual(items[1]['input'], 'patch text')
        self.assertEqual(events[-1]['response']['usage']['total_tokens'], 28)

    def test_translates_text_and_usage(self) -> None:
        events = parse_sse(
            chat_to_responses_sse(
                {
                    'id': 'chatcmpl_1',
                    'created': 123,
                    'model': 'gpt-5.6-sol',
                    'choices': [{'message': {'role': 'assistant', 'content': 'Done.'}}],
                    'usage': {
                        'prompt_tokens': 100,
                        'completion_tokens': 20,
                        'total_tokens': 120,
                        'prompt_tokens_details': {'cached_tokens': 40},
                        'completion_tokens_details': {'reasoning_tokens': 7},
                    },
                },
                {},
            )
        )
        self.assertEqual([event['type'] for event in events], [
            'response.created',
            'response.output_item.done',
            'response.completed',
        ])
        self.assertEqual(events[1]['item']['content'][0]['text'], 'Done.')
        usage = events[-1]['response']['usage']
        self.assertEqual(usage['input_tokens'], 100)
        self.assertEqual(usage['input_tokens_details']['cached_tokens'], 40)
        self.assertEqual(usage['output_tokens_details']['reasoning_tokens'], 7)

    def test_translates_function_and_custom_tool_calls(self) -> None:
        events = parse_sse(
            chat_to_responses_sse(
                {
                    'id': 'chatcmpl_tools',
                    'model': 'gpt-5.6-sol',
                    'choices': [
                        {
                            'message': {
                                'role': 'assistant',
                                'content': None,
                                'tool_calls': [
                                    {
                                        'id': 'call_shell',
                                        'type': 'function',
                                        'function': {
                                            'name': 'shell_command',
                                            'arguments': '{"command":"pwd"}',
                                        },
                                    },
                                    {
                                        'id': 'call_patch',
                                        'type': 'function',
                                        'function': {
                                            'name': 'apply_patch',
                                            'arguments': '{"input":"*** Begin Patch"}',
                                        },
                                    },
                                ],
                            }
                        }
                    ],
                    'usage': {},
                },
                {'shell_command': 'function_call', 'apply_patch': 'custom_tool_call'},
            )
        )
        output_items = [event['item'] for event in events if event['type'] == 'response.output_item.done']
        self.assertEqual(output_items[0]['type'], 'function_call')
        self.assertEqual(output_items[0]['arguments'], '{"command":"pwd"}')
        self.assertEqual(output_items[1]['type'], 'custom_tool_call')
        self.assertEqual(output_items[1]['input'], '*** Begin Patch')


class ProxyIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_responses_route_calls_chat_upstream_and_returns_sse(self) -> None:
        server = ThreadingHTTPServer(('127.0.0.1', 0), FakeChatHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        old_mode = settings.OAI_PROXY_RESPONSES_MODE
        old_url = settings.OAI_PROXY_UPSTREAM_BASE_URL
        settings.OAI_PROXY_RESPONSES_MODE = 'chat_completions'
        settings.OAI_PROXY_UPSTREAM_BASE_URL = f'http://127.0.0.1:{server.server_port}/v1'
        try:
            transport = httpx.ASGITransport(app=app)
            with patch('oai_proxy.routers.catch_all._resolve_openai_key', return_value='fake-upstream-key'):
                async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
                    response = await client.post(
                        '/v1/responses',
                        headers={'authorization': 'Bearer STATIC'},
                        json={
                            'model': 'gpt-5.6-sol',
                            'instructions': 'Be concise.',
                            'input': 'Say adapter ok.',
                            'reasoning': {'effort': 'low'},
                        },
                    )
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.headers['content-type'].startswith('text/event-stream'))
            events = parse_sse(response.content)
            self.assertEqual(events[-1]['response']['usage']['total_tokens'], 15)
            request = server.last_request  # type: ignore[attr-defined]
            self.assertEqual(request['model'], 'gpt-5.6-sol')
            self.assertEqual(request['reasoning_effort'], 'low')
            self.assertTrue(request['stream'])
            self.assertEqual(request['stream_options'], {'include_usage': True})
        finally:
            settings.OAI_PROXY_RESPONSES_MODE = old_mode
            settings.OAI_PROXY_UPSTREAM_BASE_URL = old_url
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == '__main__':
    unittest.main()
