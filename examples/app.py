#!/usr/bin/env python3
"""
Example Pyserv Application with Enhanced Features

This example demonstrates the refactored Pyserv framework with:
- Enhanced Application Architecture
- Advanced Middleware System
- Event System
- Security Features
- Monitoring and Observability
"""
from typing import Dict, Any
from pyserv import Application
from pyserv.middleware import (
    PerformanceMonitoringMiddleware,
    RequestLoggingMiddleware,
    CORSMiddleware,
    SecurityHeadersMiddleware
)

# Create application instance with enhanced features
app: Application = Application()

# Add middleware for enhanced functionality
app.add_middleware(PerformanceMonitoringMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CORSMiddleware, origins=["*"])
app.add_middleware(SecurityHeadersMiddleware)

# Basic routes
@app.route('/')
async def home(request) -> Dict[str, str]:
    return {'message': 'Welcome to Pyserv!', 'status': 'running', 'features': 'enhanced'}

@app.route('/hello/{name}')
async def hello(request, name: str) -> Dict[str, str]:
    return {'message': f'Hello, {name}!', 'framework': 'Pyserv Enhanced'}

@app.route('/health')
async def health(request) -> Dict[str, Any]:
    return {
        'status': 'healthy',
        'timestamp': request.headers.get('date', ''),
        'middleware_count': len(app.middleware_manager.http_middlewares),
        'active_requests': len(app.middleware_manager.request_contexts)
    }

# API routes with enhanced features
@app.route('/api/users', methods=['GET'])
async def get_users(request) -> Dict[str, Any]:
    """Get users with enhanced response"""
    return {
        'users': [
            {'id': 1, 'name': 'John Doe', 'role': 'user'},
            {'id': 2, 'name': 'Jane Smith', 'role': 'admin'}
        ],
        'total': 2,
        'middleware_enabled': True
    }

@app.route('/api/metrics')
async def get_metrics(request) -> Dict[str, Any]:
    """Get application metrics"""
    stats = app.middleware_manager.get_stats()
    return {
        'middleware_stats': stats,
        'framework_version': '1.0.0-enhanced',
        'features': [
            'Advanced Middleware System',
            'Event System',
            'Plugin Architecture',
            'Security Middleware',
            'Performance Monitoring',
            'GraphQL Support',
            'gRPC Services'
        ]
    }

# WebSocket route example with enhanced features
@app.websocket_route('/ws')
async def websocket_handler(websocket) -> None:
    await websocket.accept()
    await websocket.send_json({
        'message': 'WebSocket connected!',
        'features': 'Enhanced Pyserv Framework'
    })

    try:
        while True:
            data: Dict[str, Any] = await websocket.receive_json()
            response = {
                'echo': data,
                'server_info': {
                    'framework': 'Pyserv Enhanced',
                    'middleware_active': True,
                    'websocket_support': True
                }
            }
            await websocket.send_json(response)
    except Exception:
        pass

# SSE (Server-Sent Events) route example
@app.route('/sse')
async def sse_handler(request):
    """Server-Sent Events endpoint"""
    if not app.sse_manager:
        return {'error': 'SSE not available'}, 503

    # Get query parameters
    channels = request.query_params.get('channels', '').split(',')
    client_id = request.query_params.get('client_id')

    # Connect to SSE
    connection = await app.sse_manager.connect(
        client_id=client_id,
        channels=[ch.strip() for ch in channels if ch.strip()]
    )

    # Return connection info
    return {
        'connection_id': connection.connection_id,
        'channels': list(connection.channels),
        'status': 'connected',
        'sse_enabled': True
    }

# Send SSE event endpoint
@app.route('/sse/send', methods=['POST'])
async def send_sse_event(request):
    """Send SSE event to channels"""
    if not app.sse_manager:
        return {'error': 'SSE not available'}, 503

    try:
        data = await request.json()
        channel = data.get('channel', 'default')
        event_type = data.get('event_type', 'message')
        message = data.get('message', 'Hello from Pyserv SSE!')

        from pyserv.server.sse import create_sse_event
        event = create_sse_event(event_type, message)

        sent_count = await app.sse_manager.send_to_channel(channel, event)

        return {
            'status': 'sent',
            'channel': channel,
            'event_type': event_type,
            'sent_to_connections': sent_count
        }

    except Exception as e:
        return {'error': str(e)}, 400

# Session handling routes
@app.route('/session')
async def session_info(request):
    """Get session information"""
    if not app.session_manager:
        return {'error': 'Session not available'}, 503

    session_id = request.session.session_id
    user_id = request.session.user_id

    return {
        'session_id': session_id,
        'user_id': user_id,
        'session_enabled': True,
        'data': dict(request.session.items()) if request.session else {}
    }

@app.route('/session/set', methods=['POST'])
async def set_session_data(request):
    """Set session data"""
    if not app.session_manager:
        return {'error': 'Session not available'}, 503

    try:
        data = await request.json()
        key = data.get('key')
        value = data.get('value')

        if key:
            request.session[key] = value
            return {'status': 'success', 'key': key, 'value': value}

        return {'error': 'Key is required'}, 400

    except Exception as e:
        return {'error': str(e)}, 400

@app.route('/session/login/{user_id}')
async def login_session(request, user_id: str):
    """Login and create session"""
    if not app.session_manager:
        return {'error': 'Session not available'}, 503

    # Create new session for user
    session = await app.session_manager.create_session(
        user_id=user_id,
        data={'logged_in': True, 'login_time': time.time()},
        ip_address=request.client_ip,
        user_agent=request.headers.get('User-Agent')
    )

    # Set session cookie
    response = {'status': 'logged_in', 'user_id': user_id, 'session_id': session.session_id}
    return response

@app.route('/session/logout')
async def logout_session(request):
    """Logout and invalidate session"""
    if not app.session_manager:
        return {'error': 'Session not available'}, 503

    if request.session:
        request.session.flush()  # Mark session for deletion
        return {'status': 'logged_out'}

    return {'error': 'No active session'}, 400

# Exception handling example
@app.exception_handler(ValueError)
async def handle_value_error(exc: ValueError):
    return {'error': 'Invalid value', 'message': str(exc), 'handled_by': 'enhanced_framework'}

if __name__ == '__main__':
    print("🚀 Starting Pyserv Enhanced Application...")
    print("✅ Features enabled:")
    print("  - Advanced Middleware System")
    print("  - Event System")
    print("  - Security Features")
    print("  - Performance Monitoring")
    print("  - Enhanced Routing")
    print("  - Server-Sent Events (SSE)")
    print("  - Session Management")
    print("  - GraphQL Support")
    print("  - gRPC Services")

    # Run directly with enhanced features
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)
