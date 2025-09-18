"""
Main NeuralForge Framework

Brings together all components: LLM Engine, Agent System, MCP Integration,
Agent Communication, and Economy System.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .llm_engine import LLMEngine, LLMConfig, LLMProvider
from .agent_system import NeuralAgent, AgentState, AgentCapability
from .mcp_integration import MCPServer
from .communication import AgentCommunicator
from .economy import EconomySystem

logger = logging.getLogger(__name__)


class TaskQueue:
    """
    Asynchronous task queue for agent task management
    """

    def __init__(self):
        self.queue = asyncio.Queue()
        self.active_tasks: Dict[str, Dict] = {}  # task_id -> task_info

    async def add_task(self, task_id: str, agent_id: str, task: str, context: Dict = None) -> str:
        """
        Add a task to the queue

        Args:
            task_id: Unique task identifier
            agent_id: Target agent ID
            task: Task description
            context: Additional context

        Returns:
            Task ID
        """
        task_data = {
            "task_id": task_id,
            "agent_id": agent_id,
            "task": task,
            "context": context or {},
            "timestamp": datetime.now().isoformat(),
            "status": "queued"
        }

        await self.queue.put(task_data)
        self.active_tasks[task_id] = task_data

        logger.info(f"Added task {task_id} for agent {agent_id}")
        return task_id

    async def get_task(self) -> Optional[Dict]:
        """
        Get a task from the queue

        Returns:
            Task data or None if queue is empty
        """
        try:
            task = await self.queue.get()
            task["status"] = "processing"
            self.active_tasks[task["task_id"]] = task
            return task
        except asyncio.QueueEmpty:
            return None

    def complete_task(self, task_id: str, result: Dict):
        """
        Mark a task as completed

        Args:
            task_id: Task identifier
            result: Task result
        """
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["status"] = "completed"
            self.active_tasks[task_id]["result"] = result
            self.active_tasks[task_id]["completed_at"] = datetime.now().isoformat()
            logger.info(f"Completed task {task_id}")

    def fail_task(self, task_id: str, error: str):
        """
        Mark a task as failed

        Args:
            task_id: Task identifier
            error: Error message
        """
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["status"] = "failed"
            self.active_tasks[task_id]["error"] = error
            self.active_tasks[task_id]["failed_at"] = datetime.now().isoformat()
            logger.error(f"Failed task {task_id}: {error}")

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        Get status of a task

        Args:
            task_id: Task identifier

        Returns:
            Task status information
        """
        return self.active_tasks.get(task_id)


class NeuralForge:
    """
    Main NeuralForge framework class that orchestrates all components
    """

    def __init__(self):
        # Core components
        self.llm_engine = LLMEngine()
        self.agents: Dict[str, NeuralAgent] = {}
        self.mcp_server = MCPServer(self.llm_engine)
        self.communicator = AgentCommunicator()
        self.economy = EconomySystem()

        # Task management
        self.task_queue = TaskQueue()
        self.agent_tasks: Dict[str, asyncio.Task] = {}  # agent_id -> task

        # Framework state
        self.running = False
        self.cleanup_task: Optional[asyncio.Task] = None

        logger.info("NeuralForge framework initialized")

    def register_agent(self, agent: NeuralAgent):
        """
        Register an agent with the framework

        Args:
            agent: NeuralAgent instance to register
        """
        self.agents[agent.agent_id] = agent
        self.economy.register_agent(agent.agent_id, agent.balance)
        self.communicator.register_agent(agent.agent_id)

        logger.info(f"Registered agent: {agent.agent_id} ({agent.name})")

    def unregister_agent(self, agent_id: str):
        """
        Unregister an agent from the framework

        Args:
            agent_id: Agent identifier to unregister
        """
        if agent_id in self.agents:
            # Stop agent's task if running
            if agent_id in self.agent_tasks:
                self.agent_tasks[agent_id].cancel()
                del self.agent_tasks[agent_id]

            # Clean up from all systems
            del self.agents[agent_id]
            self.economy.unregister_agent(agent_id)
            self.communicator.unregister_agent(agent_id)

            logger.info(f"Unregistered agent: {agent_id}")

    async def process_agent_task(self, agent_id: str, task: str, context: Dict = None) -> Dict:
        """
        Process a task through a specific agent

        Args:
            agent_id: Target agent ID
            task: Task description
            context: Additional context

        Returns:
            Task result
        """
        if agent_id not in self.agents:
            return {"error": f"Agent {agent_id} not found"}

        agent = self.agents[agent_id]

        try:
            # Check if agent has sufficient balance
            if agent.balance <= 0:
                return {"error": f"Agent {agent_id} has insufficient balance"}

            # Process the task
            result = await agent.process_task(task, context)

            # Update economy (cost already deducted in agent.process_task)
            logger.info(f"Agent {agent_id} processed task successfully")
            return result

        except Exception as e:
            logger.error(f"Error processing task for agent {agent_id}: {str(e)}")
            return {"error": f"Task processing failed: {str(e)}"}

    async def orchestrate_agents(self, task: str, required_capabilities: List[str],
                               budget: float = 50.0) -> Dict:
        """
        Orchestrate multiple agents to complete a complex task

        Args:
            task: Complex task description
            required_capabilities: List of required capabilities
            budget: Maximum budget for the task

        Returns:
            Orchestrated result
        """
        # Find suitable agents
        suitable_agents = [
            agent for agent in self.agents.values()
            if any(cap in agent.capabilities for cap in required_capabilities)
            and agent.balance > budget / len(required_capabilities)
        ]

        if not suitable_agents:
            return {"error": "No suitable agents found with required capabilities"}

        logger.info(f"Found {len(suitable_agents)} suitable agents for orchestration")

        # Distribute task among agents
        results = []
        for agent in suitable_agents:
            subtask = f"{task} - Focus on your capabilities: {list(agent.capabilities.keys())}"
            result = await agent.process_task(subtask)
            results.append({
                "agent_id": agent.agent_id,
                "result": result
            })

        # Combine results using LLM
        combined_result = await self._combine_agent_results(results, task)

        return {
            "task": task,
            "participating_agents": [agent.agent_id for agent in suitable_agents],
            "combined_result": combined_result,
            "individual_results": results,
            "total_cost": sum(r["result"]["cost"] for r in results)
        }

    async def _combine_agent_results(self, results: List[Dict], original_task: str) -> str:
        """
        Use LLM to combine results from multiple agents

        Args:
            results: Individual agent results
            original_task: Original task description

        Returns:
            Combined result
        """
        results_summary = "\n\n".join([
            f"Agent {r['agent_id']}:\n{r['result']['response']}"
            for r in results
        ])

        combine_prompt = f"""
        Original task: {original_task}

        Multiple agents have provided their contributions:

        {results_summary}

        Please synthesize these contributions into a coherent, comprehensive response.
        Identify areas of agreement, disagreement, and complementarity.
        Provide a final integrated answer.
        """

        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4",
            temperature=0.3
        )

        response = await self.llm_engine.generate(config, combine_prompt)
        return response.content

    async def send_agent_message(self, from_agent: str, to_agent: str, message: str,
                               context: Dict = None) -> bool:
        """
        Send a message between agents

        Args:
            from_agent: Sender agent ID
            to_agent: Receiver agent ID
            message: Message content
            context: Additional context

        Returns:
            True if message sent successfully
        """
        # Check if agents are registered
        if from_agent not in self.agents or to_agent not in self.agents:
            logger.warning(f"One or both agents not registered: {from_agent}, {to_agent}")
            return False

        # Charge for communication
        success = await self.economy.charge_service(from_agent, "agent_communication", messages=1)
        if not success:
            logger.warning(f"Failed to charge {from_agent} for communication")
            return False

        # Send message
        return await self.communicator.send_message(from_agent, to_agent, message, context)

    async def broadcast_message(self, from_agent: str, message: str,
                              context: Dict = None) -> int:
        """
        Broadcast a message to all agents

        Args:
            from_agent: Sender agent ID
            message: Message content
            context: Additional context

        Returns:
            Number of agents message was sent to
        """
        if from_agent not in self.agents:
            logger.warning(f"Sender agent not registered: {from_agent}")
            return 0

        # Charge for broadcast (simplified)
        success = await self.economy.charge_service(from_agent, "agent_communication", messages=len(self.agents))
        if not success:
            logger.warning(f"Failed to charge {from_agent} for broadcast")
            return 0

        return await self.communicator.broadcast_message(from_agent, message, context)

    async def process_mcp_request(self, agent_id: str, request: Dict) -> Dict:
        """
        Process an MCP request from an agent

        Args:
            agent_id: Agent making the request
            request: MCP request

        Returns:
            MCP response
        """
        if agent_id not in self.agents:
            return {"error": "Agent not registered"}

        # Process MCP request
        response = await self.mcp_server.process_mcp_request(self.agents[agent_id], request)

        # Handle costs if successful
        if "cost" in response and response.get("success"):
            agent = self.agents[agent_id]
            if agent.balance >= response["cost"]:
                agent.balance -= response["cost"]
            else:
                return {"error": "Insufficient balance for MCP operation"}

        return response

    def get_agent_status(self, agent_id: str) -> Optional[Dict]:
        """
        Get status of a specific agent

        Args:
            agent_id: Agent identifier

        Returns:
            Agent status information
        """
        if agent_id not in self.agents:
            return None

        agent = self.agents[agent_id]
        return {
            "agent_id": agent_id,
            "name": agent.name,
            "state": agent.state.value,
            "balance": agent.balance,
            "capabilities": list(agent.capabilities.keys()),
            "memory_size": len(agent.memory.long_term),
            "economy_stats": self.economy.get_agent_stats(agent_id),
            "communication_stats": self.communicator.get_agent_stats(agent_id)
        }

    def get_system_status(self) -> Dict:
        """
        Get overall system status

        Returns:
            System status information
        """
        return {
            "framework_status": "running" if self.running else "stopped",
            "total_agents": len(self.agents),
            "active_agent_tasks": len([t for t in self.agent_tasks.values() if not t.done()]),
            "economy_stats": self.economy.get_system_stats(),
            "communication_stats": self.communicator.get_system_stats(),
            "mcp_stats": self.mcp_server.get_stats(),
            "queued_tasks": len(self.task_queue.active_tasks)
        }

    async def start_agent_loops(self):
        """
        Start autonomous agent loops for all registered agents
        """
        for agent_id, agent in self.agents.items():
            if agent_id not in self.agent_tasks:
                self.agent_tasks[agent_id] = asyncio.create_task(
                    self._run_agent_loop(agent_id)
                )
                logger.info(f"Started agent loop for {agent_id}")

    async def stop_agent_loops(self):
        """
        Stop all agent loops
        """
        for agent_id, task in self.agent_tasks.items():
            if not task.done():
                task.cancel()
                logger.info(f"Stopped agent loop for {agent_id}")

        # Wait for all tasks to complete
        await asyncio.gather(*self.agent_tasks.values(), return_exceptions=True)
        self.agent_tasks.clear()

    async def _run_agent_loop(self, agent_id: str):
        """
        Main loop for autonomous agent operation

        Args:
            agent_id: Agent identifier
        """
        agent = self.agents[agent_id]

        try:
            while self.running:
                # Check for messages from other agents
                messages = await self.communicator.receive_messages(agent_id, timeout=1.0)

                for message in messages:
                    # Process incoming message as a task
                    response_task = f"Respond to message from {message['from_agent']}: {message['message']}"
                    response = await agent.process_task(response_task, message['context'])

                    # Send response back
                    await self.send_agent_message(
                        agent_id, message['from_agent'],
                        response['response'],
                        {"in_response_to": message['message_id']}
                    )

                # Check for tasks in queue (if any)
                # This could be extended for more complex task management

                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            logger.info(f"Agent loop cancelled for {agent_id}")
        except Exception as e:
            logger.error(f"Error in agent loop for {agent_id}: {str(e)}")

    async def start(self):
        """
        Start the NeuralForge framework
        """
        if self.running:
            logger.warning("Framework is already running")
            return

        self.running = True

        # Start communication cleanup task
        await self.communicator.start_cleanup_task()

        # Start agent loops
        await self.start_agent_loops()

        logger.info("NeuralForge framework started")

    async def stop(self):
        """
        Stop the NeuralForge framework
        """
        if not self.running:
            logger.info("Framework is not running")
            return

        self.running = False

        # Stop agent loops
        await self.stop_agent_loops()

        # Stop communication cleanup
        await self.communicator.stop_cleanup_task()

        # Close LLM engine
        await self.llm_engine.close()

        logger.info("NeuralForge framework stopped")

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()
