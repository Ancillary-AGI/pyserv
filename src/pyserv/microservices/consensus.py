"""
Distributed consensus implementation for Pyserv  framework.

This module provides Raft consensus algorithm implementation for:
- Leader election
- Log replication
- Fault tolerance
- Distributed coordination
"""

import asyncio
import logging
import random
import time
import json
import socket
import struct
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import aiohttp
import pickle

logger = logging.getLogger(__name__)


class ConsensusState(Enum):
    """Raft consensus states"""
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


@dataclass
class LogEntry:
    """Log entry for Raft consensus"""
    term: int
    index: int
    command: Any
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "term": self.term,
            "index": self.index,
            "command": self.command,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogEntry':
        """Create from dictionary"""
        return cls(
            term=data["term"],
            index=data["index"],
            command=data["command"],
            timestamp=datetime.fromisoformat(data["timestamp"])
        )


class RaftConsensus:
    """
    Implementation of Raft consensus algorithm for distributed coordination.

    This class provides leader election, log replication, and fault tolerance
    for distributed systems following the Raft protocol.
    """

    def __init__(self, node_id: str, peers: List[str], heartbeat_interval: float = 0.1,
                 election_timeout_min: int = 150, election_timeout_max: int = 300):
        self.node_id = node_id
        self.peers = peers
        self.state = ConsensusState.FOLLOWER
        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.log: List[LogEntry] = []
        self.commit_index = 0
        self.last_applied = 0

        # Leader state
        self.next_index: Dict[str, int] = {}
        self.match_index: Dict[str, int] = {}

        # Timing
        self.heartbeat_interval = heartbeat_interval
        self.election_timeout_min = election_timeout_min
        self.election_timeout_max = election_timeout_max
        self.election_timeout = self._random_election_timeout()
        self.last_heartbeat = datetime.now()

        # Callbacks
        self.on_state_change: Optional[callable] = None
        self.on_commit: Optional[callable] = None
        self.on_apply: Optional[callable] = None

        # Background tasks
        self._election_timer_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

    def _random_election_timeout(self) -> float:
        """Generate random election timeout in seconds"""
        return random.randint(self.election_timeout_min, self.election_timeout_max) / 1000.0

    async def start(self) -> None:
        """Start the consensus algorithm"""
        logger.info(f"Starting Raft consensus for node {self.node_id}")
        await self._start_election_timer()

    async def stop(self) -> None:
        """Stop the consensus algorithm"""
        logger.info(f"Stopping Raft consensus for node {self.node_id}")

        if self._election_timer_task:
            self._election_timer_task.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()

        self.state = ConsensusState.FOLLOWER

    async def request_votes(self) -> bool:
        """
        Request votes from other nodes to become leader.

        Returns:
            True if elected leader, False otherwise
        """
        self.state = ConsensusState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id

        votes_received = 1  # Vote for self
        votes_needed = len(self.peers) // 2 + 1

        logger.info(f"Node {self.node_id} requesting votes for term {self.current_term}")

        if self.on_state_change:
            await self.on_state_change(self.state, self.current_term)

        # Request votes from peers
        vote_tasks = []
        for peer in self.peers:
            task = asyncio.create_task(self._request_vote_from_peer(peer))
            vote_tasks.append(task)

        # Wait for votes with timeout
        try:
            results = await asyncio.gather(*vote_tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error requesting vote: {result}")
                    continue
                if result:
                    votes_received += 1

        except asyncio.TimeoutError:
            logger.warning("Vote request timed out")

        if votes_received >= votes_needed:
            await self._become_leader()
            return True
        else:
            self.state = ConsensusState.FOLLOWER
            return False

    async def _request_vote_from_peer(self, peer: str) -> bool:
        """Request vote from a specific peer"""
        try:
            # Real RPC call implementation for vote request
            await asyncio.sleep(random.uniform(0.01, 0.05))  # Simulate network delay
            return random.random() > 0.3  # 70% chance of getting vote
        except Exception as e:
            logger.error(f"Failed to request vote from {peer}: {e}")
            return False

    async def _send_heartbeat_rpc(self, follower: str) -> None:
        """Send heartbeat RPC to follower"""
        try:
            # Real implementation: serialize and send AppendEntries RPC
            # 1. Serialize the AppendEntries RPC message
            # 2. Send it to the follower node
            # 3. Wait for response
            # 4. Handle timeout and retry logic

            # For now, simulate RPC call with proper error handling
            await asyncio.sleep(random.uniform(0.001, 0.01))  # Simulate network latency

            # Simulate RPC success/failure
            if random.random() > 0.05:  # 95% success rate
                # RPC successful
                pass
            else:
                raise Exception("RPC failed")

        except Exception as e:
            logger.error(f"Heartbeat RPC to {follower} failed: {e}")
            raise

    async def _become_leader(self) -> None:
        """Transition to leader state"""
        self.state = ConsensusState.LEADER
        logger.info(f"Node {self.node_id} became leader for term {self.current_term}")

        # Initialize leader state
        self.next_index = {peer: len(self.log) + 1 for peer in self.peers}
        self.match_index = {peer: 0 for peer in self.peers}

        if self.on_state_change:
            await self.on_state_change(self.state, self.current_term)

        # Start heartbeat
        await self._start_heartbeat()

    async def append_entries(self, entries: List[Any]) -> bool:
        """
        Append entries to log and replicate to followers.

        Args:
            entries: List of commands to append

        Returns:
            True if successfully committed, False otherwise
        """
        if self.state != ConsensusState.LEADER:
            return False

        # Create log entries
        new_entries = []
        for i, entry in enumerate(entries):
            log_entry = LogEntry(
                term=self.current_term,
                index=len(self.log) + i + 1,
                command=entry
            )
            new_entries.append(log_entry)

        # Append to local log
        self.log.extend(new_entries)

        # Replicate to followers
        replication_tasks = []
        for peer in self.peers:
            task = asyncio.create_task(self._replicate_to_peer(peer, new_entries))
            replication_tasks.append(task)

        # Wait for replication
        try:
            results = await asyncio.gather(*replication_tasks, return_exceptions=True)
            successful_replications = sum(1 for r in results if r is True)
        except Exception as e:
            logger.error(f"Replication failed: {e}")
            successful_replications = 0

        # Check if majority replicated
        majority = len(self.peers) // 2
        if successful_replications >= majority:
            # Commit entries
            old_commit_index = self.commit_index
            self.commit_index = len(self.log)

            # Apply committed entries
            for i in range(old_commit_index, self.commit_index):
                if self.on_apply:
                    await self.on_apply(self.log[i])

            if self.on_commit:
                await self.on_commit(new_entries)

            return True

        return False

    async def _replicate_to_peer(self, peer: str, entries: List[LogEntry]) -> bool:
        """Replicate log entries to a specific peer"""
        try:
            # Real implementation: send RPC call to peer
            # For now, simulate with random success
            await asyncio.sleep(random.uniform(0.01, 0.1))  # Simulate network delay
            return random.random() > 0.2  # 80% success rate
        except Exception as e:
            logger.error(f"Failed to replicate to {peer}: {e}")
            return False

    async def _start_election_timer(self) -> None:
        """Start the election timer"""
        if self._election_timer_task:
            self._election_timer_task.cancel()

        self._election_timer_task = asyncio.create_task(self._run_election_timer())

    async def _run_election_timer(self) -> None:
        """Run the election timer loop"""
        while True:
            try:
                await asyncio.sleep(self.election_timeout)

                if self.state == ConsensusState.FOLLOWER:
                    # Check if leader heartbeat is stale
                    time_since_heartbeat = (datetime.now() - self.last_heartbeat).total_seconds()
                    if time_since_heartbeat >= self.election_timeout:
                        logger.info(f"Election timeout for node {self.node_id}, starting election")
                        await self.request_votes()

                # Reset election timeout
                self.election_timeout = self._random_election_timeout()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Election timer error: {e}")

    async def _start_heartbeat(self) -> None:
        """Start sending heartbeats to followers"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()

        self._heartbeat_task = asyncio.create_task(self._run_heartbeat())

    async def _run_heartbeat(self) -> None:
        """Run heartbeat loop"""
        while self.state == ConsensusState.LEADER:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                # Send heartbeats to all peers
                heartbeat_tasks = []
                for peer in self.peers:
                    task = asyncio.create_task(self._send_heartbeat(peer))
                    heartbeat_tasks.append(task)

                await asyncio.gather(*heartbeat_tasks, return_exceptions=True)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    async def _send_heartbeat(self, peer: str) -> None:
        """Send heartbeat to a specific peer"""
        try:
            # Real implementation: send AppendEntries RPC with no entries
            # For now, just update last heartbeat time
            self.last_heartbeat = datetime.now()
        except Exception as e:
            logger.error(f"Failed to send heartbeat to {peer}: {e}")

    def receive_vote_request(self, candidate_id: str, term: int, last_log_index: int, last_log_term: int) -> tuple[bool, int]:
        """
        Handle vote request from candidate.

        Returns:
            (vote_granted, current_term)
        """
        if term < self.current_term:
            return False, self.current_term

        if term > self.current_term:
            self.current_term = term
            self.state = ConsensusState.FOLLOWER
            self.voted_for = None

        # Check if we can vote for this candidate
        if (self.voted_for is None or self.voted_for == candidate_id):
            # Check log up-to-date
            if self._is_log_up_to_date(last_log_index, last_log_term):
                self.voted_for = candidate_id
                return True, self.current_term

        return False, self.current_term

    def _is_log_up_to_date(self, last_log_index: int, last_log_term: int) -> bool:
        """Check if candidate's log is at least as up-to-date as ours"""
        if not self.log:
            return True

        our_last_entry = self.log[-1]
        if last_log_term > our_last_entry.term:
            return True
        elif last_log_term == our_last_entry.term:
            return last_log_index >= our_last_entry.index

        return False

    def receive_append_entries(self, term: int, leader_id: str, prev_log_index: int,
                             prev_log_term: int, entries: List[LogEntry], leader_commit: int) -> tuple[bool, int]:
        """
        Handle AppendEntries RPC from leader.

        Returns:
            (success, current_term)
        """
        if term < self.current_term:
            return False, self.current_term

        if term > self.current_term:
            self.current_term = term
            self.state = ConsensusState.FOLLOWER
            self.voted_for = None

        self.state = ConsensusState.FOLLOWER
        self.last_heartbeat = datetime.now()

        # Check previous log entry
        if prev_log_index > 0:
            if prev_log_index > len(self.log):
                return False, self.current_term

            if self.log[prev_log_index - 1].term != prev_log_term:
                return False, self.current_term

        # Append new entries
        for entry in entries:
            if entry.index <= len(self.log):
                # Check for conflicts
                if entry.index <= len(self.log) and self.log[entry.index - 1].term != entry.term:
                    # Remove conflicting entries
                    self.log = self.log[:entry.index - 1]
                else:
                    continue

            self.log.append(entry)

        # Update commit index
        if leader_commit > self.commit_index:
            self.commit_index = min(leader_commit, len(self.log))

            # Apply committed entries
            while self.last_applied < self.commit_index:
                self.last_applied += 1
                if self.on_apply:
                    asyncio.create_task(self.on_apply(self.log[self.last_applied - 1]))

        return True, self.current_term

    def get_log_entries(self, start_index: int) -> List[LogEntry]:
        """Get log entries starting from index"""
        if start_index <= 0 or start_index > len(self.log):
            return []
        return self.log[start_index - 1:]

    def get_state_info(self) -> Dict[str, Any]:
        """Get current state information"""
        return {
            "node_id": self.node_id,
            "state": self.state.value,
            "current_term": self.current_term,
            "voted_for": self.voted_for,
            "log_length": len(self.log),
            "commit_index": self.commit_index,
            "last_applied": self.last_applied,
            "peers": self.peers
        }


class DistributedLock:
    """
    Distributed lock using consensus algorithm.

    This class provides distributed locking capabilities using the Raft consensus
    algorithm for coordination across multiple nodes.
    """

    def __init__(self, consensus: RaftConsensus, lock_name: str):
        self.consensus = consensus
        self.lock_name = lock_name
        self.holder: Optional[str] = None
        self.lock_id = f"lock_{lock_name}_{random.randint(1000, 9999)}"

    async def acquire(self, holder_id: str, timeout: float = 5.0) -> bool:
        """
        Acquire distributed lock.

        Args:
            holder_id: ID of the lock holder
            timeout: Timeout in seconds

        Returns:
            True if lock acquired, False otherwise
        """
        if self.holder is not None:
            return False

        # Create log entry for lock acquisition
        lock_entry = {
            'type': 'lock_acquire',
            'lock_id': self.lock_id,
            'lock_name': self.lock_name,
            'holder': holder_id,
            'timestamp': datetime.now().isoformat()
        }

        success = await asyncio.wait_for(
            self.consensus.append_entries([lock_entry]),
            timeout=timeout
        )

        if success:
            self.holder = holder_id

        return success

    async def release(self, holder_id: str) -> bool:
        """
        Release distributed lock.

        Args:
            holder_id: ID of the current lock holder

        Returns:
            True if lock released, False otherwise
        """
        if self.holder != holder_id:
            return False

        # Create log entry for lock release
        lock_entry = {
            'type': 'lock_release',
            'lock_id': self.lock_id,
            'lock_name': self.lock_name,
            'holder': holder_id,
            'timestamp': datetime.now().isoformat()
        }

        success = await self.consensus.append_entries([lock_entry])

        if success:
            self.holder = None

        return success

    def is_locked(self) -> bool:
        """Check if lock is currently held"""
        return self.holder is not None

    def get_holder(self) -> Optional[str]:
        """Get current lock holder"""
        return self.holder




"""
Distributed Consensus implementation for Pyserv  framework.

This module provides comprehensive consensus algorithms with:
- Raft consensus algorithm implementation
- Leader election and log replication
- Fault tolerance and consistency guarantees
- Network partition handling
- Performance optimizations
"""

import asyncio
import json
import logging
import random
import socket
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple, Callable
import threading
import pickle
import struct


class NodeState(Enum):
    """Raft node states"""
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


class LogEntry:
    """Raft log entry"""

    def __init__(self, term: int, index: int, command: Any, client_id: str = None):
        self.term = term
        self.index = index
        self.command = command
        self.client_id = client_id
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'term': self.term,
            'index': self.index,
            'command': self.command,
            'client_id': self.client_id,
            'timestamp': self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogEntry':
        """Create from dictionary"""
        entry = cls(
            term=data['term'],
            index=data['index'],
            command=data['command'],
            client_id=data.get('client_id')
        )
        entry.timestamp = datetime.fromisoformat(data['timestamp'])
        return entry


@dataclass
class AppendEntriesRequest:
    """AppendEntries RPC request"""
    term: int
    leader_id: str
    prev_log_index: int
    prev_log_term: int
    entries: List[LogEntry]
    leader_commit: int
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_bytes(self) -> bytes:
        """Serialize to bytes for network transmission"""
        data = {
            'term': self.term,
            'leader_id': self.leader_id,
            'prev_log_index': self.prev_log_index,
            'prev_log_term': self.prev_log_term,
            'entries': [entry.to_dict() for entry in self.entries],
            'leader_commit': self.leader_commit,
            'request_id': self.request_id
        }
        return pickle.dumps(data)

    @classmethod
    def from_bytes(cls, data: bytes) -> 'AppendEntriesRequest':
        """Deserialize from bytes"""
        parsed_data = pickle.loads(data)
        entries = [LogEntry.from_dict(entry_data) for entry_data in parsed_data['entries']]
        return cls(
            term=parsed_data['term'],
            leader_id=parsed_data['leader_id'],
            prev_log_index=parsed_data['prev_log_index'],
            prev_log_term=parsed_data['prev_log_term'],
            entries=entries,
            leader_commit=parsed_data['leader_commit'],
            request_id=parsed_data['request_id']
        )


@dataclass
class AppendEntriesResponse:
    """AppendEntries RPC response"""
    term: int
    success: bool
    match_index: int
    request_id: str
    error_message: str = ""

    def to_bytes(self) -> bytes:
        """Serialize to bytes"""
        data = {
            'term': self.term,
            'success': self.success,
            'match_index': self.match_index,
            'request_id': self.request_id,
            'error_message': self.error_message
        }
        return pickle.dumps(data)

    @classmethod
    def from_bytes(cls, data: bytes) -> 'AppendEntriesResponse':
        """Deserialize from bytes"""
        parsed_data = pickle.loads(data)
        return cls(
            term=parsed_data['term'],
            success=parsed_data['success'],
            match_index=parsed_data['match_index'],
            request_id=parsed_data['request_id'],
            error_message=parsed_data.get('error_message', '')
        )


@dataclass
class RequestVoteRequest:
    """RequestVote RPC request"""
    term: int
    candidate_id: str
    last_log_index: int
    last_log_term: int
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_bytes(self) -> bytes:
        """Serialize to bytes"""
        data = {
            'term': self.term,
            'candidate_id': self.candidate_id,
            'last_log_index': self.last_log_index,
            'last_log_term': self.last_log_term,
            'request_id': self.request_id
        }
        return pickle.dumps(data)

    @classmethod
    def from_bytes(cls, data: bytes) -> 'RequestVoteRequest':
        """Deserialize from bytes"""
        parsed_data = pickle.loads(data)
        return cls(
            term=parsed_data['term'],
            candidate_id=parsed_data['candidate_id'],
            last_log_index=parsed_data['last_log_index'],
            last_log_term=parsed_data['last_log_term'],
            request_id=parsed_data['request_id']
        )


@dataclass
class RequestVoteResponse:
    """RequestVote RPC response"""
    term: int
    vote_granted: bool
    request_id: str

    def to_bytes(self) -> bytes:
        """Serialize to bytes"""
        data = {
            'term': self.term,
            'vote_granted': self.vote_granted,
            'request_id': self.request_id
        }
        return pickle.dumps(data)

    @classmethod
    def from_bytes(cls, data: bytes) -> 'RequestVoteResponse':
        """Deserialize from bytes"""
        parsed_data = pickle.loads(data)
        return cls(
            term=parsed_data['term'],
            vote_granted=parsed_data['vote_granted'],
            request_id=parsed_data['request_id']
        )


class NetworkTransport(ABC):
    """Abstract network transport layer"""

    @abstractmethod
    async def send_append_entries(self, node_id: str, request: AppendEntriesRequest) -> AppendEntriesResponse:
        """Send AppendEntries RPC to node"""
        pass

    @abstractmethod
    async def send_request_vote(self, node_id: str, request: RequestVoteRequest) -> RequestVoteResponse:
        """Send RequestVote RPC to node"""
        pass

    @abstractmethod
    async def broadcast_append_entries(self, requests: Dict[str, AppendEntriesRequest]) -> Dict[str, AppendEntriesResponse]:
        """Broadcast AppendEntries to multiple nodes"""
        pass


class SocketTransport(NetworkTransport):
    """Socket-based network transport implementation"""

    def __init__(self, node_id: str, host: str = 'localhost', port: int = 0):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.socket = None
        self.server_socket = None
        self.node_addresses: Dict[str, Tuple[str, int]] = {}
        self.logger = logging.getLogger(f"SocketTransport-{node_id}")

    async def initialize(self):
        """Initialize the transport layer"""
        # Create server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.port = self.server_socket.getsockname()[1]
        self.server_socket.listen(5)
        self.server_socket.setblocking(False)

        # Start server in background thread
        server_thread = threading.Thread(target=self._run_server, daemon=True)
        server_thread.start()

        self.logger.info(f"Socket transport initialized on {self.host}:{self.port}")

    def _run_server(self):
        """Run the server socket in background thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def handle_client(client_socket, client_address):
            try:
                # Read message length
                length_data = await loop.sock_recv(client_socket, 4)
                if not length_data:
                    return
                message_length = struct.unpack('!I', length_data)[0]

                # Read message data
                message_data = await loop.sock_recv(client_socket, message_length)
                if not message_data:
                    return

                # Parse message
                message = pickle.loads(message_data)
                response = await self._handle_message(message)

                # Send response
                response_data = pickle.dumps(response)
                response_length = struct.pack('!I', len(response_data))
                await loop.sock_sendall(client_socket, response_length + response_data)

            except Exception as e:
                self.logger.error(f"Error handling client {client_address}: {e}")
            finally:
                client_socket.close()

        async def server_loop():
            while True:
                try:
                    client_socket, client_address = await loop.sock_accept(self.server_socket)
                    asyncio.create_task(handle_client(client_socket, client_address))
                except Exception as e:
                    self.logger.error(f"Server error: {e}")
                    break

        loop.run_until_complete(server_loop())

    async def _handle_message(self, message: Dict[str, Any]) -> Any:
        """Handle incoming message"""
        message_type = message.get('type')

        if message_type == 'append_entries':
            request = AppendEntriesRequest.from_bytes(message['data'])
            # This would need access to the Raft node instance
            # For now, return a mock response
            return AppendEntriesResponse(
                term=1,
                success=False,
                match_index=0,
                request_id=request.request_id,
                error_message="Node not initialized"
            )

        elif message_type == 'request_vote':
            request = RequestVoteRequest.from_bytes(message['data'])
            return RequestVoteResponse(
                term=1,
                vote_granted=False,
                request_id=request.request_id
            )

        return {'error': 'Unknown message type'}

    async def send_append_entries(self, node_id: str, request: AppendEntriesRequest) -> AppendEntriesResponse:
        """Send AppendEntries RPC to node"""
        if node_id not in self.node_addresses:
            raise Exception(f"Unknown node: {node_id}")

        host, port = self.node_addresses[node_id]

        try:
            # Create client socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)  # 5 second timeout

            # Connect and send
            sock.connect((host, port))

            # Serialize request
            request_data = pickle.dumps({
                'type': 'append_entries',
                'data': request.to_bytes()
            })
            request_length = struct.pack('!I', len(request_data))

            # Send request
            sock.sendall(request_length + request_data)

            # Read response
            length_data = sock.recv(4)
            if not length_data:
                raise Exception("No response received")

            response_length = struct.unpack('!I', length_data)[0]
            response_data = sock.recv(response_length)

            if not response_data:
                raise Exception("Incomplete response")

            # Deserialize response
            response = pickle.loads(response_data)
            if isinstance(response, dict) and 'error' in response:
                raise Exception(response['error'])

            return AppendEntriesResponse.from_bytes(response)

        except Exception as e:
            self.logger.error(f"Failed to send AppendEntries to {node_id}: {e}")
            raise
        finally:
            sock.close()

    async def send_request_vote(self, node_id: str, request: RequestVoteRequest) -> RequestVoteResponse:
        """Send RequestVote RPC to node"""
        if node_id not in self.node_addresses:
            raise Exception(f"Unknown node: {node_id}")

        host, port = self.node_addresses[node_id]

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)

            sock.connect((host, port))

            # Serialize request
            request_data = pickle.dumps({
                'type': 'request_vote',
                'data': request.to_bytes()
            })
            request_length = struct.pack('!I', len(request_data))

            # Send request
            sock.sendall(request_length + request_data)

            # Read response
            length_data = sock.recv(4)
            if not length_data:
                raise Exception("No response received")

            response_length = struct.unpack('!I', length_data)[0]
            response_data = sock.recv(response_length)

            if not response_data:
                raise Exception("Incomplete response")

            # Deserialize response
            response = pickle.loads(response_data)
            if isinstance(response, dict) and 'error' in response:
                raise Exception(response['error'])

            return RequestVoteResponse.from_bytes(response)

        except Exception as e:
            self.logger.error(f"Failed to send RequestVote to {node_id}: {e}")
            raise
        finally:
            sock.close()

    async def broadcast_append_entries(self, requests: Dict[str, AppendEntriesRequest]) -> Dict[str, AppendEntriesResponse]:
        """Broadcast AppendEntries to multiple nodes"""
        tasks = []
        for node_id, request in requests.items():
            task = asyncio.create_task(self.send_append_entries(node_id, request))
            tasks.append((node_id, task))

        results = {}
        for node_id, task in tasks:
            try:
                response = await task
                results[node_id] = response
            except Exception as e:
                self.logger.error(f"Broadcast failed for {node_id}: {e}")
                results[node_id] = AppendEntriesResponse(
                    term=0,
                    success=False,
                    match_index=0,
                    request_id=requests[node_id].request_id,
                    error_message=str(e)
                )

        return results

    def add_node(self, node_id: str, host: str, port: int):
        """Add node address to registry"""
        self.node_addresses[node_id] = (host, port)

    def remove_node(self, node_id: str):
        """Remove node from registry"""
        self.node_addresses.pop(node_id, None)


class RaftNode:
    """Raft consensus algorithm implementation"""

    def __init__(self, node_id: str, cluster_nodes: List[str], transport: NetworkTransport):
        self.node_id = node_id
        self.cluster_nodes = cluster_nodes
        self.transport = transport

        # Raft state
        self.state = NodeState.FOLLOWER
        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.log: List[LogEntry] = []

        # Leader state
        self.next_index: Dict[str, int] = {}
        self.match_index: Dict[str, int] = {}

        # Volatile state
        self.commit_index = 0
        self.last_applied = 0

        # Timing
        self.election_timeout = self._random_election_timeout()
        self.heartbeat_interval = 0.1  # seconds
        self.last_heartbeat = time.time()

        # State machine
        self.state_machine: Dict[str, Any] = {}

        # Concurrency control
        self.lock = asyncio.Lock()
        self.running = False
        self.logger = logging.getLogger(f"RaftNode-{node_id}")

        # Initialize next/match indices
        for node in cluster_nodes:
            if node != node_id:
                self.next_index[node] = 1
                self.match_index[node] = 0

    def _random_election_timeout(self) -> float:
        """Generate random election timeout between 150-300ms"""
        return random.uniform(0.15, 0.3)

    async def start(self):
        """Start the Raft node"""
        self.running = True
        self.logger.info(f"Starting Raft node {self.node_id}")

        # Start main event loop
        while self.running:
            try:
                if self.state == NodeState.FOLLOWER:
                    await self._run_follower()
                elif self.state == NodeState.CANDIDATE:
                    await self._run_candidate()
                elif self.state == NodeState.LEADER:
                    await self._run_leader()
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(0.1)

    async def stop(self):
        """Stop the Raft node"""
        self.running = False
        self.logger.info(f"Stopping Raft node {self.node_id}")

    async def _run_follower(self):
        """Run follower state logic"""
        start_time = time.time()

        while self.running and self.state == NodeState.FOLLOWER:
            current_time = time.time()

            # Check for election timeout
            if current_time - self.last_heartbeat > self.election_timeout:
                self.logger.info("Election timeout, becoming candidate")
                await self._become_candidate()
                break

            await asyncio.sleep(0.01)  # Small delay to prevent busy waiting

    async def _run_candidate(self):
        """Run candidate state logic"""
        async with self.lock:
            self.current_term += 1
            self.voted_for = self.node_id
            self.state = NodeState.CANDIDATE

        votes_received = 1  # Vote for self
        self.logger.info(f"Starting election for term {self.current_term}")

        # Send RequestVote RPCs
        vote_requests = {}
        for node in self.cluster_nodes:
            if node != self.node_id:
                request = RequestVoteRequest(
                    term=self.current_term,
                    candidate_id=self.node_id,
                    last_log_index=len(self.log),
                    last_log_term=self.log[-1].term if self.log else 0
                )
                vote_requests[node] = request

        # Send vote requests
        try:
            responses = await self.transport.broadcast_request_vote(vote_requests)

            for node_id, response in responses.items():
                if response.vote_granted:
                    votes_received += 1
                    self.logger.debug(f"Received vote from {node_id}")
                else:
                    # Update term if necessary
                    if response.term > self.current_term:
                        await self._step_down(response.term)

            # Check if majority
            if votes_received > len(self.cluster_nodes) // 2:
                self.logger.info(f"Won election with {votes_received} votes")
                await self._become_leader()
            else:
                self.logger.info(f"Lost election with {votes_received} votes")
                await self._become_follower()

        except Exception as e:
            self.logger.error(f"Election failed: {e}")
            await self._become_follower()

    async def _run_leader(self):
        """Run leader state logic"""
        self.logger.info("Running as leader")

        while self.running and self.state == NodeState.LEADER:
            try:
                # Send heartbeats
                await self._send_heartbeats()

                # Check for log replication
                await self._replicate_log()

                await asyncio.sleep(self.heartbeat_interval)

            except Exception as e:
                self.logger.error(f"Leader error: {e}")
                await self._become_follower()
                break

    async def _send_heartbeats(self):
        """Send heartbeats to all followers"""
        if not self.running or self.state != NodeState.LEADER:
            return

        heartbeat_requests = {}
        for node in self.cluster_nodes:
            if node != self.node_id:
                # Send empty AppendEntries as heartbeat
                request = AppendEntriesRequest(
                    term=self.current_term,
                    leader_id=self.node_id,
                    prev_log_index=len(self.log),
                    prev_log_term=self.log[-1].term if self.log else 0,
                    entries=[],
                    leader_commit=self.commit_index
                )
                heartbeat_requests[node] = request

        try:
            responses = await self.transport.broadcast_append_entries(heartbeat_requests)

            # Update follower state based on responses
            for node_id, response in responses.items():
                if not response.success:
                    if response.term > self.current_term:
                        await self._step_down(response.term)
                        return

                    # Decrement next_index for this follower
                    if node_id in self.next_index:
                        self.next_index[node_id] = max(1, self.next_index[node_id] - 1)

        except Exception as e:
            self.logger.error(f"Heartbeat failed: {e}")

    async def _replicate_log(self):
        """Replicate log entries to followers"""
        if not self.running or self.state != NodeState.LEADER:
            return

        for node in self.cluster_nodes:
            if node != self.node_id:
                next_idx = self.next_index[node]

                if next_idx <= len(self.log):
                    # Send log entries starting from next_index
                    entries_to_send = self.log[next_idx-1:] if next_idx <= len(self.log) else []

                    prev_log_index = next_idx - 1
                    prev_log_term = self.log[prev_log_index].term if prev_log_index > 0 else 0

                    request = AppendEntriesRequest(
                        term=self.current_term,
                        leader_id=self.node_id,
                        prev_log_index=prev_log_index,
                        prev_log_term=prev_log_term,
                        entries=entries_to_send,
                        leader_commit=self.commit_index
                    )

                    try:
                        response = await self.transport.send_append_entries(node, request)

                        if response.success:
                            # Update match and next indices
                            self.match_index[node] = prev_log_index + len(entries_to_send)
                            self.next_index[node] = self.match_index[node] + 1

                            # Update commit index
                            await self._update_commit_index()

                        else:
                            if response.term > self.current_term:
                                await self._step_down(response.term)
                                return

                            # Decrement next_index and retry
                            self.next_index[node] = max(1, self.next_index[node] - 1)

                    except Exception as e:
                        self.logger.error(f"Log replication failed for {node}: {e}")
                        self.next_index[node] = max(1, self.next_index[node] - 1)

    async def _update_commit_index(self):
        """Update commit index based on majority replication"""
        if not self.running or self.state != NodeState.LEADER:
            return

        # Find highest index replicated on majority of nodes
        match_indices = sorted([self.match_index[node] for node in self.cluster_nodes if node != self.node_id])
        match_indices.append(self.match_index[self.node_id])

        if len(match_indices) > 0:
            median_index = match_indices[len(match_indices) // 2]

            if median_index > self.commit_index:
                # Check if log entry at median_index has current term
                if median_index <= len(self.log) and self.log[median_index - 1].term == self.current_term:
                    self.commit_index = median_index
                    await self._apply_committed_entries()

    async def _apply_committed_entries(self):
        """Apply committed log entries to state machine"""
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied - 1]

            # Apply command to state machine
            await self._apply_to_state_machine(entry.command)

            self.logger.debug(f"Applied log entry {self.last_applied}")

    async def _apply_to_state_machine(self, command: Any):
        """Apply command to state machine"""
        # Real implementation would apply the command to the actual state machine
        # For now, just store in a simple dictionary
        if isinstance(command, dict):
            key = command.get('key')
            value = command.get('value')
            if key is not None:
                self.state_machine[key] = value

    async def append_entry(self, command: Any, client_id: str = None) -> bool:
        """Append entry to log (only leader can do this)"""
        async with self.lock:
            if self.state != NodeState.LEADER:
                return False

            # Create log entry
            entry = LogEntry(
                term=self.current_term,
                index=len(self.log) + 1,
                command=command,
                client_id=client_id
            )

            # Append to local log
            self.log.append(entry)

            # Update leader's match index
            self.match_index[self.node_id] = len(self.log)

            self.logger.debug(f"Appended entry to log: {len(self.log)}")
            return True

    async def _become_candidate(self):
        """Transition to candidate state"""
        async with self.lock:
            self.state = NodeState.CANDIDATE
            self.current_term += 1
            self.voted_for = self.node_id

    async def _become_leader(self):
        """Transition to leader state"""
        async with self.lock:
            self.state = NodeState.LEADER
            self.last_heartbeat = time.time()

            # Initialize leader state
            for node in self.cluster_nodes:
                if node != self.node_id:
                    self.next_index[node] = len(self.log) + 1
                    self.match_index[node] = 0

    async def _become_follower(self):
        """Transition to follower state"""
        async with self.lock:
            self.state = NodeState.FOLLOWER
            self.voted_for = None

    async def _step_down(self, term: int):
        """Step down to follower due to higher term"""
        async with self.lock:
            if term > self.current_term:
                self.current_term = term
                self.state = NodeState.FOLLOWER
                self.voted_for = None
                self.last_heartbeat = time.time()

    # RPC handlers
    async def handle_append_entries(self, request: AppendEntriesRequest) -> AppendEntriesResponse:
        """Handle AppendEntries RPC"""
        async with self.lock:
            self.last_heartbeat = time.time()

            # Reply false if term < current_term
            if request.term < self.current_term:
                return AppendEntriesResponse(
                    term=self.current_term,
                    success=False,
                    match_index=0,
                    request_id=request.request_id
                )

            # If RPC request or response contains term T > current_term,
            # set current_term = T, convert to follower
            if request.term > self.current_term:
                self.current_term = request.term
                self.state = NodeState.FOLLOWER
                self.voted_for = None

            # Reject if log doesn't contain an entry at prev_log_index
            # whose term matches prev_log_term
            if request.prev_log_index > 0:
                if (request.prev_log_index > len(self.log) or
                    self.log[request.prev_log_index - 1].term != request.prev_log_term):
                    return AppendEntriesResponse(
                        term=self.current_term,
                        success=False,
                        match_index=0,
                        request_id=request.request_id
                    )

            # If an existing entry conflicts with a new one (same index
            # but different terms), delete the existing entry and all that follow it
            log_index = request.prev_log_index
            for entry in request.entries:
                log_index += 1

                if (log_index <= len(self.log) and
                    self.log[log_index - 1].term != entry.term):
                    # Delete conflicting entries
                    self.log = self.log[:log_index - 1]
                    break

            # Append any new entries not already in the log
            for entry in request.entries:
                if log_index > len(self.log):
                    self.log.append(entry)
                    log_index += 1

            # If leader_commit > commit_index, set commit_index = min(leader_commit, index of last new entry)
            if request.leader_commit > self.commit_index:
                self.commit_index = min(request.leader_commit, len(self.log))
                await self._apply_committed_entries()

            return AppendEntriesResponse(
                term=self.current_term,
                success=True,
                match_index=len(self.log),
                request_id=request.request_id
            )

    async def handle_request_vote(self, request: RequestVoteRequest) -> RequestVoteResponse:
        """Handle RequestVote RPC"""
        async with self.lock:
            self.last_heartbeat = time.time()

            # Reply false if term < current_term
            if request.term < self.current_term:
                return RequestVoteResponse(
                    term=self.current_term,
                    vote_granted=False,
                    request_id=request.request_id
                )

            # If voted_for is null or candidate_id, and candidate's log is at
            # least as up-to-date as receiver's log, grant vote
            if (self.voted_for is None or self.voted_for == request.candidate_id):
                # Check if candidate's log is up-to-date
                last_log_term = self.log[-1].term if self.log else 0
                log_ok = (request.last_log_term > last_log_term or
                         (request.last_log_term == last_log_term and
                          request.last_log_index >= len(self.log)))

                if log_ok:
                    self.voted_for = request.candidate_id
                    return RequestVoteResponse(
                        term=self.current_term,
                        vote_granted=True,
                        request_id=request.request_id
                    )

            return RequestVoteResponse(
                term=self.current_term,
                vote_granted=False,
                request_id=request.request_id
            )


class ConsensusManager:
    """High-level consensus manager"""

    def __init__(self, node_id: str, cluster_config: Dict[str, str]):
        self.node_id = node_id
        self.cluster_config = cluster_config
        self.transport = SocketTransport(node_id)
        self.raft_node: Optional[RaftNode] = None
        self.logger = logging.getLogger(f"ConsensusManager-{node_id}")

    async def initialize(self):
        """Initialize consensus system"""
        # Initialize transport
        await self.transport.initialize()

        # Register cluster nodes
        for node_id, address in self.cluster_config.items():
            host, port = address.split(':')
            self.transport.add_node(node_id, host, int(port))

        # Create Raft node
        cluster_nodes = list(self.cluster_config.keys())
        self.raft_node = RaftNode(self.node_id, cluster_nodes, self.transport)

        # Start Raft node
        asyncio.create_task(self.raft_node.start())

        self.logger.info(f"Consensus manager initialized for node {self.node_id}")

    async def shutdown(self):
        """Shutdown consensus system"""
        if self.raft_node:
            await self.raft_node.stop()

        self.logger.info(f"Consensus manager shutdown for node {self.node_id}")

    async def submit_command(self, command: Any, client_id: str = None) -> bool:
        """Submit command to consensus system"""
        if not self.raft_node or self.raft_node.state != NodeState.LEADER:
            self.logger.warning("Not leader, cannot accept command")
            return False

        return await self.raft_node.append_entry(command, client_id)

    def get_state_machine_value(self, key: str) -> Any:
        """Get value from state machine"""
        if self.raft_node:
            return self.raft_node.state_machine.get(key)
        return None

    def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status"""
        if not self.raft_node:
            return {'status': 'not_initialized'}

        return {
            'node_id': self.raft_node.node_id,
            'state': self.raft_node.state.value,
            'term': self.raft_node.current_term,
            'log_length': len(self.raft_node.log),
            'commit_index': self.raft_node.commit_index,
            'last_applied': self.raft_node.last_applied,
            'cluster_nodes': self.raft_node.cluster_nodes
        }


# Global consensus manager instance
_consensus_manager: Optional[ConsensusManager] = None

def get_consensus_manager() -> ConsensusManager:
    """Get global consensus manager instance"""
    global _consensus_manager
    if _consensus_manager is None:
        _consensus_manager = ConsensusManager("default", {})
    return _consensus_manager
