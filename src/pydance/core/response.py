import asyncio
import inspect
import json
from typing import Any, Dict, List, Callable, Optional

class Response:
    def __init__(self, content: Any = None, status_code: int = 200, 
                 headers: Optional[Dict[str, str]] = None, 
                 media_type: Optional[str] = None,
                 background_tasks: Optional[List[Callable]] = None):
        self.status_code = status_code
        self.headers = headers or {}
        self.background_tasks = background_tasks or []
        self.content = content
        self._streaming = asyncio.Queue() if content is None else None
        
        if media_type:
            self.media_type = media_type
        elif isinstance(content, (dict, list)):
            self.media_type = "application/json"
        elif isinstance(content, str):
            self.media_type = "text/plain"
        else:
            self.media_type = "text/html"
    
    async def stream_data(self, data: bytes) -> None:
        if self._streaming is not None:
            await self._streaming.put(data)
        else:
            raise ValueError("Response is not configured for streaming")
    
    async def end_stream(self) -> None:
        if self._streaming is not None:
            await self._streaming.put(None)
    
    async def __call__(self, scope, receive, send) -> None:
        headers = [
            [b"content-type", self.media_type.encode()],
            *[(k.encode(), v.encode()) for k, v in self.headers.items()]
        ]
        
        await send({
            "type": "http.response.start",
            "status": self.status_code,
            "headers": headers,
        })
        
        if self._streaming is not None:
            while True:
                data = await self._streaming.get()
                if data is None:
                    break
                await send({
                    "type": "http.response.body",
                    "body": data,
                    "more_body": True,
                })
            await send({
                "type": "http.response.body",
                "body": b"",
                "more_body": False,
            })
        
        if self.content is not None:
            if isinstance(self.content, (dict, list)):
                content = json.dumps(self.content).encode()
            elif isinstance(self.content, str):
                content = self.content.encode()
            elif isinstance(self.content, bytes):
                content = self.content
            else:
                content = str(self.content).encode()
            
            await send({
                "type": "http.response.body",
                "body": content,
                "more_body": False,
            })
        
        for task in self.background_tasks:
            if inspect.iscoroutinefunction(task):
                asyncio.create_task(task())
            else:
                asyncio.get_event_loop().run_in_executor(None, task)