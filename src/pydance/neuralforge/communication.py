"""
Communication Module for NeuralForge

Provides agent-to-agent communication capabilities with message queuing and conversation management.
"""

import asyncio
import hashlib
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class MessageQueue:
    """
    Asynchronous message queue for agent communication
    """

    def __init__(self, max_size: int = 1000):
        self.queue = asyncio.Queue(maxsize=max_size)
        self.message_history: List[Dict] = []
        self.max_history = 1000

    async def put(self, message: Dict):
        """
        Put a message in the queue

        Args:
            message: Message dictionary
        """
        try:
            await self.queue.put(message)
            self._add_to_history(message)
        except asyncio.QueueFull:
            logger.warning("Message queue is full, dropping oldest message")
            # Remove oldest message and try again
            await self.queue.get()
            await self.queue.put(message)
            self._add_to_history(message)

    async def get(self) -> Dict:
        """
        Get a message from the queue

        Returns:
            Message dictionary
        """
        return await self.queue.get()

    def get_nowait(self) -> Optional[Dict]:
        """
        Get a message from the queue without waiting

        Returns:
            Message dictionary or None if queue is empty
        """
        try:
            return self.queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def empty(self) -> bool:
        """
        Check if queue is empty

        Returns:
            True if queue is empty
        """
        return self.queue.empty()

    def qsize(self) -> int:
        """
        Get queue size

        Returns:
            Number of messages in queue
        """
        return self.queue.qsize()

    def _add_to_history(self, message: Dict):
        """
        Add message to history

        Args:
            message: Message dictionary
        """
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history = self.message_history[-self.max_history:]

    def get_history(self, limit: int = 50) -> List[Dict]:
        """
        Get message history

        Args:
            limit: Maximum number of messages to return

        Returns:
            List of recent messages
        """
        return self.message_history[-limit:]


class ConversationManager:
    """
    Manages conversations between agents
    """

    def __init__(self):
        self.conversations: Dict[str, List[Dict]] = {}
        self.active_conversations: Dict[str, datetime] = {}
        self.max_conversation_age = 3600  # 1 hour in seconds

    def add_message(self, conversation_id: str, message: Dict):
        """
        Add a message to a conversation

        Args:
            conversation_id: Conversation identifier
            message: Message dictionary
        """
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []

        self.conversations[conversation_id].append(message)
        self.active_conversations[conversation_id] = datetime.now()

        # Keep only recent messages (last 100 per conversation)
        if len(self.conversations[conversation_id]) > 100:
            self.conversations[conversation_id] = self.conversations[conversation_id][-100:]

    def get_conversation(self, conversation_id: str) -> List[Dict]:
        """
        Get all messages in a conversation

        Args:
            conversation_id: Conversation identifier

        Returns:
            List of messages in the conversation
        """
        return self.conversations.get(conversation_id, [])

    def get_recent_messages(self, conversation_id: str, limit: int = 10) -> List[Dict]:
        """
        Get recent messages from a conversation

        Args:
            conversation_id: Conversation identifier
            limit: Maximum number of messages to return

        Returns:
            List of recent messages
        """
        conversation = self.conversations.get(conversation_id, [])
        return conversation[-limit:]

    def cleanup_old_conversations(self):
        """
        Remove conversations that haven't been active for too long
        """
        current_time = datetime.now()
        to_remove = []

        for conv_id, last_activity in self.active_conversations.items():
            age = (current_time - last_activity).total_seconds()
            if age > self.max_conversation_age:
                to_remove.append(conv_id)

        for conv_id in to_remove:
            del self.conversations[conv_id]
            del self.active_conversations[conv_id]
            logger.info(f"Cleaned up old conversation: {conv_id}")

    def get_active_conversations(self) -> List[str]:
        """
        Get list of active conversation IDs

        Returns:
            List of active conversation IDs
        """
        return list(self.active_conversations.keys())

    def get_conversation_stats(self) -> Dict:
        """
        Get conversation statistics

        Returns:
            Statistics dictionary
        """
        total_messages = sum(len(msgs) for msgs in self.conversations.values())
        return {
            "total_conversations": len(self.conversations),
            "active_conversations": len(self.active_conversations),
            "total_messages": total_messages,
            "average_messages_per_conversation": total_messages / max(1, len(self.conversations))
        }


class AgentCommunicator:
    """
    Main communication system for agent-to-agent messaging
    """

    def __init__(self):
        self.message_queues: Dict[str, MessageQueue] = {}
        self.conversation_manager = ConversationManager()
        self.message_counter = 0
        self.cleanup_task: Optional[asyncio.Task] = None

    def register_agent(self, agent_id: str):
        """
        Register an agent for communication

        Args:
            agent_id: Unique agent identifier
        """
        if agent_id not in self.message_queues:
            self.message_queues[agent_id] = MessageQueue()
            logger.info(f"Registered agent for communication: {agent_id}")

    def unregister_agent(self, agent_id: str):
        """
        Unregister an agent from communication

        Args:
            agent_id: Agent identifier to unregister
        """
        if agent_id in self.message_queues:
            del self.message_queues[agent_id]
            logger.info(f"Unregistered agent from communication: {agent_id}")

    async def send_message(self, from_agent: str, to_agent: str, message: str,
                          context: Dict = None, message_type: str = "direct") -> bool:
        """
        Send a message from one agent to another

        Args:
            from_agent: Sender agent ID
            to_agent: Receiver agent ID
            message: Message content
            context: Additional context
            message_type: Type of message

        Returns:
            True if message was sent successfully
        """
        if to_agent not in self.message_queues:
            logger.warning(f"Agent {to_agent} not registered for communication")
            return False

        self.message_counter += 1
        message_id = f"msg_{self.message_counter}_{hashlib.md5(f'{from_agent}_{to_agent}_{datetime.now().isoformat()}'.encode()).hexdigest()[:8]}"

        message_data = {
            "message_id": message_id,
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "context": context or {},
            "message_type": message_type
        }

        # Add to recipient's queue
        await self.message_queues[to_agent].put(message_data)

        # Store in conversation history
        conversation_id = self._get_conversation_id(from_agent, to_agent)
        self.conversation_manager.add_message(conversation_id, message_data)

        logger.info(f"Message sent from {from_agent} to {to_agent}: {message_id}")
        return True

    async def broadcast_message(self, from_agent: str, message: str,
                               context: Dict = None, exclude_agents: List[str] = None) -> int:
        """
        Broadcast a message to all registered agents

        Args:
            from_agent: Sender agent ID
            message: Message content
            context: Additional context
            exclude_agents: List of agents to exclude from broadcast

        Returns:
            Number of agents the message was sent to
        """
        exclude_agents = exclude_agents or []
        exclude_agents.append(from_agent)  # Don't send to self

        sent_count = 0
        for agent_id in self.message_queues.keys():
            if agent_id not in exclude_agents:
                success = await self.send_message(
                    from_agent, agent_id, message, context, "broadcast"
                )
                if success:
                    sent_count += 1

        logger.info(f"Broadcast message sent to {sent_count} agents")
        return sent_count

    async def receive_messages(self, agent_id: str, timeout: float = 5.0,
                              max_messages: int = 10) -> List[Dict]:
        """
        Receive messages for a specific agent

        Args:
            agent_id: Agent ID to receive messages for
            timeout: Timeout in seconds to wait for messages
            max_messages: Maximum number of messages to receive

        Returns:
            List of received messages
        """
        if agent_id not in self.message_queues:
            logger.warning(f"Agent {agent_id} not registered for communication")
            return []

        messages = []
        queue = self.message_queues[agent_id]

        try:
            # Try to get messages without waiting first
            while len(messages) < max_messages and not queue.empty():
                message = queue.get_nowait()
                messages.append(message)

            # If we haven't reached max_messages and timeout > 0, wait for more
            if len(messages) < max_messages and timeout > 0:
                remaining_timeout = timeout
                while len(messages) < max_messages and remaining_timeout > 0:
                    start_time = asyncio.get_event_loop().time()
                    try:
                        message = await asyncio.wait_for(
                            queue.get(), timeout=remaining_timeout
                        )
                        messages.append(message)
                        elapsed = asyncio.get_event_loop().time() - start_time
                        remaining_timeout -= elapsed
                    except asyncio.TimeoutError:
                        break

        except Exception as e:
            logger.error(f"Error receiving messages for agent {agent_id}: {str(e)}")

        if messages:
            logger.info(f"Agent {agent_id} received {len(messages)} messages")

        return messages

    async def peek_messages(self, agent_id: str, count: int = 5) -> List[Dict]:
        """
        Peek at messages without removing them from the queue

        Args:
            agent_id: Agent ID
            count: Number of messages to peek at

        Returns:
            List of messages (copies, not removed from queue)
        """
        if agent_id not in self.message_queues:
            return []

        # Get messages from history since we can't peek the queue directly
        conversation_ids = [
            self._get_conversation_id(agent_id, other_agent)
            for other_agent in self.message_queues.keys()
            if other_agent != agent_id
        ]

        all_messages = []
        for conv_id in conversation_ids:
            messages = self.conversation_manager.get_recent_messages(conv_id, count)
            # Filter messages addressed to this agent
            agent_messages = [msg for msg in messages if msg["to_agent"] == agent_id]
            all_messages.extend(agent_messages)

        # Sort by timestamp and return most recent
        all_messages.sort(key=lambda x: x["timestamp"], reverse=True)
        return all_messages[:count]

    def get_conversation_history(self, agent1: str, agent2: str, limit: int = 50) -> List[Dict]:
        """
        Get conversation history between two agents

        Args:
            agent1: First agent ID
            agent2: Second agent ID
            limit: Maximum number of messages to return

        Returns:
            List of messages in the conversation
        """
        conversation_id = self._get_conversation_id(agent1, agent2)
        return self.conversation_manager.get_recent_messages(conversation_id, limit)

    def get_agent_stats(self, agent_id: str) -> Dict:
        """
        Get communication statistics for an agent

        Args:
            agent_id: Agent ID

        Returns:
            Statistics dictionary
        """
        if agent_id not in self.message_queues:
            return {"error": "Agent not registered"}

        queue = self.message_queues[agent_id]

        # Count conversations involving this agent
        conversation_count = 0
        total_messages = 0
        for other_agent in self.message_queues.keys():
            if other_agent != agent_id:
                conv_id = self._get_conversation_id(agent_id, other_agent)
                messages = self.conversation_manager.get_conversation(conv_id)
                if messages:
                    conversation_count += 1
                    total_messages += len(messages)

        return {
            "agent_id": agent_id,
            "queue_size": queue.qsize(),
            "messages_in_history": len(queue.get_history()),
            "active_conversations": conversation_count,
            "total_messages": total_messages
        }

    def get_system_stats(self) -> Dict:
        """
        Get system-wide communication statistics

        Returns:
            Statistics dictionary
        """
        total_queues = len(self.message_queues)
        total_messages_queued = sum(queue.qsize() for queue in self.message_queues.values())

        conv_stats = self.conversation_manager.get_conversation_stats()

        return {
            "registered_agents": total_queues,
            "total_messages_queued": total_messages_queued,
            "total_messages_sent": self.message_counter,
            **conv_stats
        }

    def _get_conversation_id(self, agent1: str, agent2: str) -> str:
        """
        Generate a consistent conversation ID for two agents

        Args:
            agent1: First agent ID
            agent2: Second agent ID

        Returns:
            Conversation ID
        """
        sorted_ids = sorted([agent1, agent2])
        return hashlib.md5(f"{sorted_ids[0]}_{sorted_ids[1]}".encode()).hexdigest()

    async def start_cleanup_task(self):
        """
        Start the periodic cleanup task
        """
        if self.cleanup_task is None or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self._periodic_cleanup())

    async def stop_cleanup_task(self):
        """
        Stop the periodic cleanup task
        """
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

    async def _periodic_cleanup(self):
        """
        Periodic cleanup of old conversations
        """
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                self.conversation_manager.cleanup_old_conversations()
                logger.debug("Performed periodic cleanup of old conversations")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {str(e)}")
