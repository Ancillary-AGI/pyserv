"""
Testing utilities for PyDance applications.
"""

from typing import Dict, Any, Optional, Union, List
from urllib.parse import urlencode, parse_qs
import json
import asyncio

from .core.server.application import Application
from .core.http import Response


class TestClient:
    """
    Test client for making HTTP requests to PyDance applications without starting a server.
    """

    def __init__(self, app: Application):
        self.app = app

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None,
                  headers: Optional[Dict[str, str]] = None) -> TestResponse:
        """Make a GET request."""
        return await self._make_request("GET", path, params=params, headers=headers)

    async def post(self, path: str, data: Optional[Dict[str, Any]] = None,
                   json_data: Optional[Dict[str, Any]] = None,
                   headers: Optional[Dict[str, str]] = None) -> TestResponse:
        """Make a POST request."""
        return await self._make_request("POST", path, data=data, json_data=json_data, headers=headers)

    async def put(self, path: str, data: Optional[Dict[str, Any]] = None,
                  json_data: Optional[Dict[str, Any]] = None,
                  headers: Optional[Dict[str, str]] = None) -> TestResponse:
        """Make a PUT request."""
        return await self._make_request("PUT", path, data=data, json_data=json_data, headers=headers)

    async def delete(self, path: str, headers: Optional[Dict[str, str]] = None) -> TestResponse:
        """Make a DELETE request."""
        return await self._make_request("DELETE", path, headers=headers)

    async def _make_request(self, method: str, path: str,
                           params: Optional[Dict[str, Any]] = None,
                           data: Optional[Dict[str, Any]] = None,
                           json_data: Optional[Dict[str, Any]] = None,
                           headers: Optional[Dict[str, str]] = None) -> 'TestResponse':
        """Make an HTTP request to the application."""
        # Build query string
        query_string = ""
        if params:
            query_string = "?" + urlencode(params)

        # Prepare headers
        request_headers = headers or {}
        request_headers.setdefault("host", "testserver")
        request_headers.setdefault("user-agent", "TestClient")

        # Prepare body
        body = b""
        if json_data is not None:
            body = json.dumps(json_data).encode('utf-8')
            request_headers.setdefault("content-type", "application/json")
        elif data is not None:
            body = urlencode(data).encode('utf-8')
            request_headers.setdefault("content-type", "application/x-www-form-urlencoded")

        # Create ASGI scope
        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": method,
            "path": path,
            "raw_path": path.encode(),
            "query_string": query_string.encode()[1:] if query_string else b"",  # Remove leading '?'
            "root_path": "",
            "headers": [[k.lower().encode(), v.encode()] for k, v in request_headers.items()],
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 0),
        }

        # Create mock receive and send functions
        messages = []
        body_sent = False

        async def receive():
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {
                    "type": "http.request",
                    "body": body,
                    "more_body": False,
                }
            else:
                # Keep alive for potential additional receives
                await asyncio.sleep(0)  # Allow other tasks to run
                return {"type": "http.disconnect"}

        async def send(message):
            messages.append(message)

        # Call the ASGI application
        await self.app(scope, receive, send)

        # Process the response messages
        return TestResponse.from_asgi_messages(messages)


class TestResponse:
    """
    Response object returned by TestClient requests.
    """

    def __init__(self, response: Response):
        self.response = response
        self.status_code = response.status_code
        self.headers = response.headers
        if isinstance(response.content, (dict, list)):
            self.content = json.dumps(response.content)
        elif isinstance(response.content, str):
            self.content = response.content
        elif isinstance(response.content, bytes):
            self.content = response.content.decode('utf-8')
        else:
            self.content = str(response.content)

    @classmethod
    def from_asgi_messages(cls, messages: List[Dict[str, Any]]) -> 'TestResponse':
        """Create TestResponse from ASGI messages."""
        status_code = 200
        headers = {}
        body_parts = []

        for message in messages:
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = {k.decode(): v.decode() for k, v in message.get("headers", [])}
            elif message["type"] == "http.response.body":
                body_parts.append(message.get("body", b""))

        body = b"".join(body_parts)
        content = body.decode('utf-8')

        # Create a mock Response object
        class MockResponse:
            def __init__(self, status_code, headers, content):
                self.status_code = status_code
                self.headers = headers
                self.content = content

        mock_response = MockResponse(status_code, headers, content)
        return cls(mock_response)

    @property
    def json(self) -> Dict[str, Any]:
        """Parse response content as JSON."""
        return json.loads(self.content)

    def __str__(self):
        return f"TestResponse(status={self.status_code}, content={self.content})"
