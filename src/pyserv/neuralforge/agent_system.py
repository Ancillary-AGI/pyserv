"""
Agent System Module for NeuralForge

Provides intelligent agents with capabilities, memory, and task processing abilities.
"""

import json
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime

from .llm_engine import LLMEngine, LLMConfig, LLMProvider


class AgentState(Enum):
    """Agent operational states"""
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentCapability:
    """Represents a capability that an agent can perform"""
    name: str
    description: str
    cost: float  # Cost in economy tokens


@dataclass
class AgentMemory:
    """Agent's memory system"""
    short_term: Dict[str, Any] = field(default_factory=dict)
    long_term: List[Dict] = field(default_factory=list)


class NeuralAgent:
    """
    Intelligent agent with LLM capabilities, memory, and specialized skills
    """

    def __init__(self, agent_id: str, name: str, description: str,
                 llm_engine: LLMEngine, capabilities: List[AgentCapability],
                 initial_balance: float = 100.0):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.llm_engine = llm_engine
        self.capabilities = {cap.name: cap for cap in capabilities}
        self.state = AgentState.IDLE
        self.memory = AgentMemory()
        self.balance = initial_balance

        # Default LLM configuration
        self.llm_config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-3.5-turbo",
            temperature=0.7
        )

    async def process_task(self, task: str, context: Dict = None) -> Dict:
        """
        Process a task using LLM and agent capabilities

        Args:
            task: Task description
            context: Additional context for the task

        Returns:
            Dict containing response and metadata
        """
        self.state = AgentState.PROCESSING

        try:
            # Build context-aware prompt
            prompt = self._build_prompt(task, context)

            # Use LLM to generate response
            response = await self.llm_engine.generate(self.llm_config, prompt)

            # Update memory and state
            self._update_memory(task, response.content)
            self.state = AgentState.COMPLETED

            # Deduct cost from balance (simple cost model)
            cost = len(response.content) * 0.01
            self.balance -= cost

            return {
                "agent_id": self.agent_id,
                "response": response.content,
                "cost": cost,
                "tokens_used": response.tokens_used,
                "latency": response.latency
            }

        except Exception as e:
            self.state = AgentState.ERROR
            raise Exception(f"Agent task processing failed: {str(e)}")

    def _build_prompt(self, task: str, context: Dict = None) -> str:
        """
        Build context-aware prompt for the agent

        Args:
            task: Task description
            context: Additional context

        Returns:
            Formatted prompt string
        """
        context_str = json.dumps(context) if context else "No context provided"
        memory_str = json.dumps(self.memory.short_term) if self.memory.short_term else "No recent memory"

        capability_list = list(self.capabilities.keys())

        return f"""
        You are {self.name}, an AI agent with these capabilities: {capability_list}

        Your description: {self.description}

        Recent memory: {memory_str}
        Task context: {context_str}

        Current task: {task}

        Please provide a thoughtful response considering your capabilities and the context.
        """

    def _update_memory(self, task: str, response: str):
        """
        Update agent memory with recent interaction

        Args:
            task: Original task
            response: Agent's response
        """
        # Add to long-term memory
        self.memory.long_term.append({
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "response": response
        })

        # Keep only recent short-term memory (last 50 interactions)
        if len(self.memory.long_term) > 50:
            self.memory.long_term = self.memory.long_term[-50:]

        # Update short-term memory with recent context
        self.memory.short_term = {
            "last_task": task,
            "last_response": response[:200] + "..." if len(response) > 200 else response,
            "timestamp": datetime.now().isoformat()
        }

    def add_capability(self, capability: AgentCapability):
        """
        Add a new capability to the agent

        Args:
            capability: New capability to add
        """
        self.capabilities[capability.name] = capability

    def remove_capability(self, capability_name: str):
        """
        Remove a capability from the agent

        Args:
            capability_name: Name of capability to remove
        """
        if capability_name in self.capabilities:
            del self.capabilities[capability_name]

    def get_capability(self, capability_name: str) -> Optional[AgentCapability]:
        """
        Get a specific capability by name

        Args:
            capability_name: Name of capability to retrieve

        Returns:
            AgentCapability if found, None otherwise
        """
        return self.capabilities.get(capability_name)

    def list_capabilities(self) -> List[str]:
        """
        List all capability names

        Returns:
            List of capability names
        """
        return list(self.capabilities.keys())

    def update_balance(self, amount: float):
        """
        Update agent balance

        Args:
            amount: Amount to add (positive) or subtract (negative)
        """
        self.balance += amount

    def get_status(self) -> Dict:
        """
        Get current agent status

        Returns:
            Dict containing agent status information
        """
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "state": self.state.value,
            "balance": self.balance,
            "capabilities": self.list_capabilities(),
            "memory_size": len(self.memory.long_term)
        }




