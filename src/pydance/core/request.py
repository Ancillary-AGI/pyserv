from typing import Dict, List, Any, AsyncGenerator, Optional
from urllib.parse import parse_qs
import json

from .application import Application

class Request:
    def __init__(self, scope, receive, send, app: Application):
        self.scope = scope
        self.receive = receive
        self.send = send
        self.app = app
        self.method = scope["method"]
        self.path = scope["path"]
        self.headers = self._parse_headers(scope["headers"])
        self.query_params = self._parse_query_params()
        self.path_params: Dict[str, Any] = {}
        self.state: Dict[str, Any] = {}
        self._body: Optional[bytes] = None
    
    def _parse_headers(self, headers: List[tuple]) -> Dict[str, str]:
        return {key.decode().lower(): value.decode() for key, value in headers}
    
    def _parse_query_params(self) -> Dict[str, List[str]]:
        query_string = self.scope.get("query_string", b"").decode()
        return parse_qs(query_string)
    
    async def body(self) -> bytes:
        if self._body is None:
            body = b""
            more_body = True
            while more_body:
                message = await self.receive()
                body += message.get("body", b"")
                more_body = message.get("more_body", False)
            self._body = body
        return self._body

    async def json(self) -> Any:
        body = await self.body()
        try:
            return json.loads(body.decode())
        except json.JSONDecodeError:
            from .exceptions import BadRequest
            from .i18n import _
            raise BadRequest(_('invalid_json'))
    
    async def form(self) -> Dict[str, str]:
        body = await self.body()
        parsed = parse_qs(body.decode())
        return {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
    
    async def stream(self) -> AsyncGenerator[bytes, None]:
        more_body = True
        while more_body:
            message = await self.receive()
            yield message.get("body", b"")
            more_body = message.get("more_body", False)

    @property
    def remote_addr(self) -> str:
        client = self.scope.get("client")
        if client:
            self.headers.get('x-forwarded-for', client[0])
        return "unknown"
