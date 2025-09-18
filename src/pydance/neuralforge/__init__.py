"""
NeuralForge - A Custom LLM Backend Framework

Features:
- LLM Engine with multiple provider support
- Agent System with capabilities and memory
- MCP (Model Context Protocol) Integration
- Agent-to-Agent Communication
- Sandbox Economy System

Author: PyDance Framework
"""

from .llm_engine import LLMEngine, LLMConfig, LLMResponse, LLMProvider
from .agent_system import NeuralAgent, AgentState, AgentCapability, AgentMemory
from .mcp_integration import MCPServer
from .communication import AgentCommunicator
from .economy import EconomySystem
from .framework import NeuralForge

__version__ = "1.0.0"
__all__ = [
    "LLMEngine", "LLMConfig", "LLMResponse", "LLMProvider",
    "NeuralAgent", "AgentState", "AgentCapability", "AgentMemory",
    "MCPServer", "AgentCommunicator", "EconomySystem", "NeuralForge"
]
