#!/usr/bin/env python3
"""
Example Pydance Application
"""
from pydance import Application

# Create application instance
app = Application()

# Basic routes
@app.route('/')
async def home(request):
    return {'message': 'Welcome to Pydance!', 'status': 'running'}

@app.route('/hello/{name}')
async def hello(request, name: str):
    return {'message': f'Hello, {name}!'}

@app.route('/health')
async def health(request):
    return {'status': 'healthy', 'timestamp': request.headers.get('date', '')}

# WebSocket route example
@app.websocket_route('/ws')
async def websocket_handler(websocket):
    await websocket.accept()
    await websocket.send_json({'message': 'WebSocket connected!'})

    try:
        while True:
            data = await websocket.receive_json()
            await websocket.send_json({'echo': data})
    except Exception:
        pass

if __name__ == '__main__':
    # Run directly
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)
