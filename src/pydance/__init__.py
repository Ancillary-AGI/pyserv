"""
Pydance - A comprehensive web framework with MVC architecture.

Pydance is a high-performance web framework built with Python that provides
a complete MVC (Model-View-Controller) architecture for building scalable
web applications. It includes features like:

- High-performance HTTP server with C extensions
- MVC architecture with controllers, models, and views
- Template engine with multiple language support
- Database ORM with migration support
- Security middleware and authentication
- WebSocket support
- Internationalization (i18n)
- NeuralForge AI integration
- Widget system for UI components
- Microservices support
- Monitoring and metrics
- Quantum security features

Example:
    >>> from pydance import Application
    >>>
    >>> app = Application()
    >>>
    >>> @app.route('/')
    ... def hello(request):
    ...     return 'Hello, World!'
    >>>
    >>> if __name__ == '__main__':
    ...     app.run()
"""

__version__ = "0.1.0"

# Core framework imports
from .core.server.application import Application
from .core.server.config import AppConfig
from .core.routing import Router, Route
from .core.middleware import HTTPMiddleware, WebSocketMiddleware
from .core.exceptions import HTTPException, BadRequest, NotFound, Forbidden
from .core.templating import TemplateEngineManager
from .core.security import Security, CryptoUtils

# NeuralForge AI Framework
from .neuralforge import (
    NeuralForge, NeuralAgent, AgentCapability, AgentState, AgentMemory,
    LLMEngine, LLMConfig, LLMResponse, LLMProvider,
    MCPServer, AgentCommunicator, EconomySystem
)

# Widgets system
from .widgets import (
    RichText, RichSelect, RichTitle, RichFile, RichDate,
    RichColor, RichRating, RichTags, RichSlider, RichCode
)

__all__ = [
    # Core framework
    'Application', 'AppConfig', 'Router', 'Route', 'HTTPMiddleware', 'WebSocketMiddleware',
    'HTTPException', 'BadRequest', 'NotFound', 'Forbidden',
    'TemplateEngineManager', 'Security', 'CryptoUtils',
    # NeuralForge AI
    'NeuralForge', 'NeuralAgent', 'AgentCapability', 'AgentState', 'AgentMemory',
    'LLMEngine', 'LLMConfig', 'LLMResponse', 'LLMProvider',
    'MCPServer', 'AgentCommunicator', 'EconomySystem',
    # Widgets
    'RichText', 'RichSelect', 'RichTitle', 'RichFile', 'RichDate',
    'RichColor', 'RichRating', 'RichTags', 'RichSlider', 'RichCode'
]
