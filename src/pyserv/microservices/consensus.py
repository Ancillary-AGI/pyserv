"""
Distributed consensus implementation for Pyserv framework.

This module provides a complete Raft consensus algorithm implementation with:
- Real network transport layer with TCP sockets
- Database-agnostic persistent storage
- Comprehensive leader election and log replication
- Fault tolerance and partition recovery
"""

import asyncio
import logging
import random
import time
import json
import socket
import struct
import threading
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import pickle
import uuid

from pyserv.database import DatabaseConnection
from pyserv.database.config import db_config

logger = logging.getLogger(__name__)


class NodeRole(Enum):
    """Raft node roles"""
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


class LogEntryType(Enum):
    """Types of log entries"""
    COMMAND = "command"
    NO_OP = "no_op"
    CONFIG_CHANGE = "config_change"
    MEMBERSHIP_CHANGE = "membership_change"


@dataclass
class LogEntry:
    """Log entry for Raft consensus"""
    term: int
    index: int
    entry_type: LogEntryType
    command: Any
    client_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "term": self.term,
            "index": self.index,
            "entry_type": self.entry_type.value,
            "command": self.command,
            "client_id": self.client_id,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogEntry':
        """Create from dictionary"""
        return cls(
            term=data["term"],
            index=data["index"],
            entry_type=LogEntryType(data["entry_type"]),
            command=data["command"],
            client_id=data.get("client_id"),
            timestamp=datetime.fromisoformat(data["timestamp"])
        )

    def is_no_op(self) -> bool:
        """Check if this is a no-op entry"""
        return self.entry_type == LogEntryType.NO_OP


@dataclass
class RPCRequest:
    """Base RPC request"""
    term: int
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_bytes(self) -> bytes:
        """Serialize to bytes"""
        return pickle.dumps(self.__dict__, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def from_bytes(cls, data: bytes):
        """Deserialize from bytes"""
        parsed_data = pickle.loads(data)
        return cls(**parsed_data)


@dataclass
class RPCResponse:
    """Base RPC response"""
    term: int
    request_id: str
    success: bool = True
    error_message: str = ""

    def to_bytes(self) -> bytes:
        """Serialize to bytes"""
        return pickle.dumps(self.__dict__, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def from_bytes(cls, data: bytes):
        """Deserialize from bytes"""
        parsed_data = pickle.loads(data)
        return cls(**parsed_data)


@dataclass
class AppendEntriesRequest(RPCRequest):
    """AppendEntries RPC request"""
    leader_id: str = ""
    prev_log_index: int = 0
    prev_log_term: int = 0
    entries: List[LogEntry] = field(default_factory=list)
    leader_commit: int = 0

    def to_bytes(self) -> bytes:
        """Serialize to bytes with entry conversion"""
        data = self.__dict__.copy()
        data['entries'] = [entry.to_dict() for entry in self.entries]
        return pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def from_bytes(cls, data: bytes):
        """Deserialize from bytes with entry conversion"""
        parsed_data = pickle.loads(data)
        entries = [LogEntry.from_dict(entry_data) for entry_data in parsed_data.get('entries', [])]
        parsed_data['entries'] = entries
        return cls(**parsed_data)


@dataclass
class AppendEntriesResponse(RPCResponse):
    """AppendEntries RPC response"""
    match_index: int = 0


@dataclass
class RequestVoteRequest(RPCRequest):
    """RequestVote RPC request"""
    candidate_id: str = ""
    last_log_index: int = 0
    last_log_term: int = 0


@dataclass
class RequestVoteResponse(RPCResponse):
    """RequestVote RPC response"""
    vote_granted: bool = False

    @property
    def success(self) -> bool:
        """Success is determined by vote_granted"""
        return self.vote_granted


class PersistentStorage:
    """Database-agnostic persistent storage for Raft state"""

    def __init__(self, node_id: str, db_connection: Optional[DatabaseConnection] = None):
        self.node_id = node_id
        if db_connection is None:
            try:
                db_connection = DatabaseConnection.get_instance(db_config)
            except Exception as e:
                logger.warning(f"Could not get database connection: {e}")
        
        self.db_connection = db_connection
        self._initialized = False

    async def _ensure_initialized(self):
        """Ensure database is initialized"""
        if self._initialized or not self.db_connection:
            return
        
        try:
            await self.db_connection.connect()
            
            # Create state collection/table
            await self.db_connection.create_table(type('RaftState', (), {
                '__tablename__': 'raft_state',
                'key': str,
                'value': str
            }))
            
            # Create log collection/table  
            await self.db_connection.create_table(type('RaftLog', (), {
                '__tablename__': 'raft_log',
                'entry_index': int,
                'term': int,
                'entry_type': str,
                'command': str,
                'client_id': str,
                'timestamp': str
            }))

            # Insert defaults
            for key, value in [('current_term', '0'), ('voted_for', ''), ('commit_index', '0'), ('last_applied', '0')]:
                try:
                    await self.db_connection.insert_one(type('RaftState', (), {'__tablename__': 'raft_state'}), {'key': key, 'value': value})
                except:
                    pass
            
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    async def get_current_term(self) -> int:
        """Get current term from persistent storage"""
        await self._ensure_initialized()
        if not self.db_connection:
            return 0
        
        try:
            result = await self.db_connection.find_one(type('RaftState', (), {'__tablename__': 'raft_state'}), {'key': 'current_term'})
            return int(result['value']) if result else 0
        except:
            return 0

    async def set_current_term(self, term: int):
        """Set current term in persistent storage"""
        await self._ensure_initialized()
        if not self.db_connection:
            return
        
        try:
            await self.db_connection.update_one(type('RaftState', (), {'__tablename__': 'raft_state'}), {'key': 'current_term'}, {'value': str(term)})
        except Exception as e:
            logger.error(f"Failed to set current term: {e}")

    async def get_voted_for(self) -> Optional[str]:
        """Get voted_for from persistent storage"""
        await self._ensure_initialized()
        if not self.db_connection:
            return None
        
        try:
            result = await self.db_connection.find_one(type('RaftState', (), {'__tablename__': 'raft_state'}), {'key': 'voted_for'})
            return result['value'] if result and result['value'] else None
        except:
            return None

    async def set_voted_for(self, voted_for: Optional[str]):
        """Set voted_for in persistent storage"""
        await self._ensure_initialized()
        if not self.db_connection:
            return
        
        try:
            await self.db_connection.update_one(type('RaftState', (), {'__tablename__': 'raft_state'}), {'key': 'voted_for'}, {'value': voted_for or ''})
        except Exception as e:
            logger.error(f"Failed to set voted_for: {e}")

    async def get_last_log_index(self) -> int:
        """Get the last log index"""
        await self._ensure_initialized()
        if not self.db_connection:
            return 0
        
        try:
            results = await self.db_connection.find_many(type('RaftLog', (), {'__tablename__': 'raft_log'}), {}, sort=[('entry_index', -1)], limit=1)
            return results[0]['entry_index'] if results else 0
        except:
            return 0

    async def get_last_log_term(self) -> int:
        """Get the last log term"""
        await self._ensure_initialized()
        if not self.db_connection:
            return 0
        
        try:
            results = await self.db_connection.find_many(type('RaftLog', (), {'__tablename__': 'raft_log'}), {}, sort=[('entry_index', -1)], limit=1)
            return results[0]['term'] if results else 0
        except:
            return 0

    async def get_log_entries(self, start_index: int = 1) -> List[LogEntry]:
        """Get log entries starting from index"""
        await self._ensure_initialized()
        if not self.db_connection:
            return []
        
        try:
            results = await self.db_connection.find_many(
                type('RaftLog', (), {'__tablename__': 'raft_log'}), 
                {'entry_index': {'$gte': start_index}}, 
                sort=[('entry_index', 1)]
            )
            entries = []
            for row in results:
                try:
                    command = json.loads(row['command']) if row['command'] else None
                    entries.append(LogEntry(
                        term=row['term'],
                        index=row['entry_index'],
                        entry_type=LogEntryType(row['entry_type']),
                        command=command,
                        client_id=row['client_id'],
                        timestamp=datetime.fromisoformat(row['timestamp'])
                    ))
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to deserialize log entry {row['entry_index']}: {e}")
                    continue
            return entries
        except Exception as e:
            logger.error(f"Failed to get log entries: {e}")
            return []

    async def append_log_entry(self, entry: LogEntry):
        """Append log entry to persistent storage"""
        await self._ensure_initialized()
        if not self.db_connection:
            return
        
        try:
            await self.db_connection.insert_one(type('RaftLog', (), {'__tablename__': 'raft_log'}), {
                'term': entry.term,
                'entry_index': entry.index,
                'entry_type': entry.entry_type.value,
                'command': json.dumps(entry.command) if entry.command else None,
                'client_id': entry.client_id,
                'timestamp': entry.timestamp.isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to append log entry: {e}")

    async def truncate_log_from(self, from_index: int):
        """Truncate log entries from index onwards"""
        await self._ensure_initialized()
        if not self.db_connection:
            return
        
        try:
            results = await self.db_connection.find_many(type('RaftLog', (), {'__tablename__': 'raft_log'}), {'entry_index': {'$gte': from_index}})
            for entry in results:
                await self.db_connection.delete_one(type('RaftLog', (), {'__tablename__': 'raft_log'}), {'entry_index': entry['entry_index']})
        except Exception as e:
            logger.error(f"Failed to truncate log: {e}")


class NetworkTransport:
    """Network transport layer"""

    def __init__(self, node_id: str, host: str = 'localhost', port: int = 0):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.server_socket = None
        self.node_addresses: Dict[str, Tuple[str, int]] = {}
        self.logger = logging.getLogger(f"NetworkTransport-{node_id}")
        self._message_handlers: Dict[str, Callable] = {}
        self._running = False

    async def initialize(self):
        """Initialize the transport layer"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.port = self.server_socket.getsockname()[1]
        self.server_socket.listen(5)
        self.server_socket.setblocking(False)

        self._running = True
        server_thread = threading.Thread(target=self._run_server, daemon=True)
        server_thread.start()

        self.logger.info(f"Network transport initialized on {self.host}:{self.port}")

    def _run_server(self):
        """Run the server socket in background thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def handle_client(client_socket, client_address):
            try:
                length_data = await loop.sock_recv(client_socket, 4)
                if not length_data or len(length_data) != 4:
                    return
                message_length = struct.unpack('!I', length_data)[0]

                message_data = await loop.sock_recv(client_socket, message_length)
                if not message_data:
                    return

                message = pickle.loads(message_data)
                response = await self._handle_message(message)

                if response:
                    response_data = pickle.dumps(response, protocol=pickle.HIGHEST_PROTOCOL)
                    response_length = struct.pack('!I', len(response_data))
                    await loop.sock_sendall(client_socket, response_length + response_data)

            except Exception as e:
                self.logger.error(f"Error handling client {client_address}: {e}")
            finally:
                try:
                    client_socket.close()
                except:
                    pass

        async def server_loop():
            while self._running:
                try:
                    client_socket, client_address = await loop.sock_accept(self.server_socket)
                    asyncio.create_task(handle_client(client_socket, client_address))
                except Exception as e:
                    if self._running:
                        self.logger.error(f"Server error: {e}")
                    break

        loop.run_until_complete(server_loop())

    async def _handle_message(self, message: Dict[str, Any]) -> Any:
        """Handle incoming message"""
        message_type = message.get('type')
        handler = self._message_handlers.get(message_type)

        if handler:
            try:
                return await handler(message.get('data'))
            except Exception as e:
                self.logger.error(f"Error handling {message_type} message: {e}")
                return {'error': str(e)}

        return {'error': f'Unknown message type: {message_type}'}

    async def send_append_entries(self, node_id: str, request: AppendEntriesRequest) -> AppendEntriesResponse:
        """Send AppendEntries RPC to node"""
        if node_id not in self.node_addresses:
            raise Exception(f"Unknown node: {node_id}")

        host, port = self.node_addresses[node_id]

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((host, port))

            request_data = pickle.dumps({
                'type': 'append_entries',
                'data': request.to_bytes()
            }, protocol=pickle.HIGHEST_PROTOCOL)
            request_length = struct.pack('!I', len(request_data))

            sock.sendall(request_length + request_data)

            length_data = sock.recv(4)
            if not length_data or len(length_data) != 4:
                raise Exception("Invalid response length")

            response_length = struct.unpack('!I', length_data)[0]
            response_data = sock.recv(response_length)

            if not response_data:
                raise Exception("Empty response")

            response = pickle.loads(response_data)
            if isinstance(response, dict) and 'error' in response:
                raise Exception(response['error'])

            return AppendEntriesResponse.from_bytes(response_data)

        except Exception as e:
            self.logger.error(f"Failed to send AppendEntries to {node_id}: {e}")
            raise
        finally:
            try:
                sock.close()
            except:
                pass

    async def send_request_vote(self, node_id: str, request: RequestVoteRequest) -> RequestVoteResponse:
        """Send RequestVote RPC to node"""
        if node_id not in self.node_addresses:
            raise Exception(f"Unknown node: {node_id}")

        host, port = self.node_addresses[node_id]

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((host, port))

            request_data = pickle.dumps({
                'type': 'request_vote',
                'data': request.to_bytes()
            }, protocol=pickle.HIGHEST_PROTOCOL)
            request_length = struct.pack('!I', len(request_data))

            sock.sendall(request_length + request_data)

            length_data = sock.recv(4)
            if not length_data or len(length_data) != 4:
                raise Exception("Invalid response length")

            response_length = struct.unpack('!I', length_data)[0]
            response_data = sock.recv(response_length)

            if not response_data:
                raise Exception("Empty response")

            response = pickle.loads(response_data)
            if isinstance(response, dict) and 'error' in response:
                raise Exception(response['error'])

            return RequestVoteResponse.from_bytes(response_data)

        except Exception as e:
            self.logger.error(f"Failed to send RequestVote to {node_id}: {e}")
            raise
        finally:
            try:
                sock.close()
            except:
                pass

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

    async def broadcast_request_vote(self, requests: Dict[str, RequestVoteRequest]) -> Dict[str, RequestVoteResponse]:
        """Broadcast RequestVote to multiple nodes"""
        tasks = []
        for node_id, request in requests.items():
            task = asyncio.create_task(self.send_request_vote(node_id, request))
            tasks.append((node_id, task))

        results = {}
        for node_id, task in tasks:
            try:
                response = await task
                results[node_id] = response
            except Exception as e:
                self.logger.error(f"Vote broadcast failed for {node_id}: {e}")
                results[node_id] = RequestVoteResponse(
                    term=0,
                    vote_granted=False,
                    request_id=requests[node_id].request_id
                )

        return results

    def add_node(self, node_id: str, host: str, port: int):
        """Add node address to registry"""
        self.node_addresses[node_id] = (host, port)

    def remove_node(self, node_id: str):
        """Remove node from registry"""
        self.node_addresses.pop(node_id, None)

    def register_message_handler(self, message_type: str, handler: Callable):
        """Register message handler"""
        self._message_handlers[message_type] = handler

    def shutdown(self):
        """Shutdown the transport layer"""
        self._running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass


class RaftNode:
    """Raft consensus algorithm implementation"""

    def __init__(self, node_id: str, cluster_nodes: List[str], transport: NetworkTransport, storage: PersistentStorage):
        self.node_id = node_id
        self.cluster_nodes = cluster_nodes
        self.transport = transport
        self.storage = storage

        self.role = NodeRole.FOLLOWER
        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.log: List[LogEntry] = []

        self.next_index: Dict[str, int] = {}
        self.match_index: Dict[str, int] = {}

        self.commit_index = 0
        self.last_applied = 0

        self.election_timeout = self._random_election_timeout()
        self.heartbeat_interval = 0.1
        self.last_heartbeat = time.time()

        self.state_machine: Dict[str, Any] = {}

        self.lock = asyncio.Lock()
        self.running = False
        self.logger = logging.getLogger(f"RaftNode-{node_id}")

        self._election_timer_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._log_replication_task: Optional[asyncio.Task] = None

        for node in cluster_nodes:
            if node != node_id:
                self.next_index[node] = 1
                self.match_index[node] = 0

    def _random_election_timeout(self) -> float:
        """Generate random election timeout between 150-300ms"""
        return random.uniform(0.15, 0.3)

    async def start(self):
        """Start the Raft node"""
        await self._load_persistent_state()
        await self._load_log_entries()
        self.running = True
        self.logger.info(f"Starting Raft node {self.node_id} in role {self.role.value}")

        self.transport.register_message_handler('append_entries', self.handle_append_entries)
        self.transport.register_message_handler('request_vote', self.handle_request_vote)

        while self.running:
            try:
                if self.role == NodeRole.FOLLOWER:
                    await self._run_follower()
                elif self.role == NodeRole.CANDIDATE:
                    await self._run_candidate()
                elif self.role == NodeRole.LEADER:
                    await self._run_leader()
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(0.1)

    async def stop(self):
        """Stop the Raft node"""
        self.running = False
        self.logger.info(f"Stopping Raft node {self.node_id}")

        if self._election_timer_task:
            self._election_timer_task.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._log_replication_task:
            self._log_replication_task.cancel()

        self.transport.shutdown()

    async def _load_persistent_state(self):
        """Load persistent state from storage"""
        self.current_term = await self.storage.get_current_term()
        self.voted_for = await self.storage.get_voted_for()
        self.commit_index = 0
        self.last_applied = 0

    async def _load_log_entries(self):
        """Load log entries from storage"""
        self.log = await self.storage.get_log_entries(1)

    async def _run_follower(self):
        """Run follower role logic"""
        while self.running and self.role == NodeRole.FOLLOWER:
            current_time = time.time()

            if current_time - self.last_heartbeat > self.election_timeout:
                self.logger.info("Election timeout, becoming candidate")
                await self._become_candidate()
                break

            await asyncio.sleep(0.01)

    async def _run_candidate(self):
        """Run candidate role logic"""
        async with self.lock:
            self.current_term += 1
            self.voted_for = self.node_id
            self.role = NodeRole.CANDIDATE
            await self.storage.set_current_term(self.current_term)
            await self.storage.set_voted_for(self.node_id)

        votes_received = 1
        self.logger.info(f"Starting election for term {self.current_term}")

        vote_requests = {}
        last_log_index = await self.storage.get_last_log_index()
        last_log_term = await self.storage.get_last_log_term()

        for node in self.cluster_nodes:
            if node != self.node_id:
                request = RequestVoteRequest(
                    term=self.current_term,
                    candidate_id=self.node_id,
                    last_log_index=last_log_index,
                    last_log_term=last_log_term
                )
                vote_requests[node] = request

        try:
            responses = await self.transport.broadcast_request_vote(vote_requests)

            for node_id, response in responses.items():
                if response.vote_granted:
                    votes_received += 1
                    self.logger.debug(f"Received vote from {node_id}")
                else:
                    if response.term > self.current_term:
                        await self._step_down(response.term)
                        return

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
        """Run leader role logic"""
        self.logger.info("Running as leader")

        if not self._heartbeat_task or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._send_heartbeats())

        while self.running and self.role == NodeRole.LEADER:
            try:
                await self._replicate_log()
                await asyncio.sleep(self.heartbeat_interval)
            except Exception as e:
                self.logger.error(f"Leader error: {e}")
                await self._become_follower()
                break

    async def _send_heartbeats(self):
        """Send heartbeats to all followers"""
        while self.running and self.role == NodeRole.LEADER:
            try:
                heartbeat_requests = {}
                for node in self.cluster_nodes:
                    if node != self.node_id:
                        request = AppendEntriesRequest(
                            term=self.current_term,
                            leader_id=self.node_id,
                            prev_log_index=await self.storage.get_last_log_index(),
                            prev_log_term=await self.storage.get_last_log_term(),
                            entries=[],
                            leader_commit=self.commit_index
                        )
                        heartbeat_requests[node] = request

                if heartbeat_requests:
                    responses = await self.transport.broadcast_append_entries(heartbeat_requests)

                    for node_id, response in responses.items():
                        if not response.success:
                            if response.term > self.current_term:
                                await self._step_down(response.term)
                                return

                            if node_id in self.next_index:
                                self.next_index[node_id] = max(1, self.next_index[node_id] - 1)

                await asyncio.sleep(self.heartbeat_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(self.heartbeat_interval)

    async def _replicate_log(self):
        """Replicate log entries to followers"""
        if not self.running or self.role != NodeRole.LEADER:
            return

        for node in self.cluster_nodes:
            if node != self.node_id:
                next_idx = self.next_index[node]

                if next_idx <= len(self.log):
                    entries_to_send = self.log[next_idx-1:] if next_idx <= len(self.log) else []

                    prev_log_index = next_idx - 1
                    prev_log_term = 0
                    if prev_log_index > 0 and prev_log_index <= len(self.log):
                        prev_log_term = self.log[prev_log_index - 1].term

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
                            self.match_index[node] = prev_log_index + len(entries_to_send)
                            self.next_index[node] = self.match_index[node] + 1
                            await self._update_commit_index()
                        else:
                            if response.term > self.current_term:
                                await self._step_down(response.term)
                                return
                            self.next_index[node] = max(1, self.next_index[node] - 1)

                    except Exception as e:
                        self.logger.error(f"Log replication failed for {node}: {e}")
                        self.next_index[node] = max(1, self.next_index[node] - 1)

    async def _update_commit_index(self):
        """Update commit index based on majority replication"""
        if not self.running or self.role != NodeRole.LEADER:
            return

        match_indices = sorted([self.match_index[node] for node in self.cluster_nodes if node != self.node_id])
        match_indices.append(self.match_index[self.node_id])

        if len(match_indices) > 0:
            median_index = match_indices[len(match_indices) // 2]

            if median_index > self.commit_index:
                if median_index <= len(self.log) and self.log[median_index - 1].term == self.current_term:
                    self.commit_index = median_index
                    await self._apply_committed_entries()

    async def _apply_committed_entries(self):
        """Apply committed log entries to state machine"""
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied - 1]
            await self._apply_to_state_machine(entry.command)
            self.logger.debug(f"Applied log entry {self.last_applied}")

    async def _apply_to_state_machine(self, command: Any):
        """Apply command to state machine"""
        if isinstance(command, dict):
            key = command.get('key')
            value = command.get('value')
            if key is not None:
                self.state_machine[key] = value

    async def append_entry(self, command: Any, client_id: str = None) -> bool:
        """Append entry to log (only leader can do this)"""
        async with self.lock:
            if self.role != NodeRole.LEADER:
                return False

            entry = LogEntry(
                term=self.current_term,
                index=len(self.log) + 1,
                entry_type=LogEntryType.COMMAND,
                command=command,
                client_id=client_id
            )

            self.log.append(entry)
            await self.storage.append_log_entry(entry)
            self.match_index[self.node_id] = len(self.log)

            self.logger.debug(f"Appended entry to log: {len(self.log)}")
            return True

    async def _become_candidate(self):
        """Transition to candidate role"""
        async with self.lock:
            self.role = NodeRole.CANDIDATE
            self.current_term += 1
            self.voted_for = self.node_id
            await self.storage.set_current_term(self.current_term)
            await self.storage.set_voted_for(self.node_id)

    async def _become_leader(self):
        """Transition to leader role"""
        async with self.lock:
            self.role = NodeRole.LEADER
            self.last_heartbeat = time.time()

            for node in self.cluster_nodes:
                if node != self.node_id:
                    self.next_index[node] = len(self.log) + 1
                    self.match_index[node] = 0

    async def _become_follower(self):
        """Transition to follower role"""
        async with self.lock:
            self.role = NodeRole.FOLLOWER
            self.voted_for = None
            await self.storage.set_voted_for(None)

    async def _step_down(self, term: int):
        """Step down to follower due to higher term"""
        async with self.lock:
            if term > self.current_term:
                self.current_term = term
                self.role = NodeRole.FOLLOWER
                self.voted_for = None
                await self.storage.set_current_term(term)
                await self.storage.set_voted_for(None)
                self.last_heartbeat = time.time()

    async def handle_append_entries(self, request_data: bytes) -> bytes:
        """Handle AppendEntries RPC"""
        try:
            request = AppendEntriesRequest.from_bytes(request_data)
            response = await self._process_append_entries(request)
            return response.to_bytes()
        except Exception as e:
            self.logger.error(f"Error handling AppendEntries: {e}")
            error_response = AppendEntriesResponse(
                term=self.current_term,
                success=False,
                match_index=0,
                request_id=request.request_id if 'request' in locals() else str(uuid.uuid4()),
                error_message=str(e)
            )
            return error_response.to_bytes()

    async def _process_append_entries(self, request: AppendEntriesRequest) -> AppendEntriesResponse:
        """Process AppendEntries RPC"""
        async with self.lock:
            self.last_heartbeat = time.time()

            if request.term < self.current_term:
                return AppendEntriesResponse(
                    term=self.current_term,
                    success=False,
                    match_index=0,
                    request_id=request.request_id
                )

            if request.term > self.current_term:
                self.current_term = request.term
                self.role = NodeRole.FOLLOWER
                self.voted_for = None
                await self.storage.set_current_term(request.term)
                await self.storage.set_voted_for(None)

            if request.prev_log_index > 0:
                if (request.prev_log_index > len(self.log) or
                    self.log[request.prev_log_index - 1].term != request.prev_log_term):
                    return AppendEntriesResponse(
                        term=self.current_term,
                        success=False,
                        match_index=0,
                        request_id=request.request_id
                    )

            log_index = request.prev_log_index
            for entry in request.entries:
                log_index += 1

                if (log_index <= len(self.log) and
                    self.log[log_index - 1].term != entry.term):
                    self.log = self.log[:log_index - 1]
                    await self.storage.truncate_log_from(log_index)
                    break

            for entry in request.entries:
                if log_index > len(self.log):
                    self.log.append(entry)
                    await self.storage.append_log_entry(entry)
                    log_index += 1

            if request.leader_commit > self.commit_index:
                self.commit_index = min(request.leader_commit, len(self.log))
                await self._apply_committed_entries()

            return AppendEntriesResponse(
                term=self.current_term,
                success=True,
                match_index=len(self.log),
                request_id=request.request_id
            )

    async def handle_request_vote(self, request_data: bytes) -> bytes:
        """Handle RequestVote RPC"""
        try:
            request = RequestVoteRequest.from_bytes(request_data)
            response = await self._process_request_vote(request)
            return response.to_bytes()
        except Exception as e:
            self.logger.error(f"Error handling RequestVote: {e}")
            error_response = RequestVoteResponse(
                term=self.current_term,
                vote_granted=False,
                request_id=request.request_id if 'request' in locals() else str(uuid.uuid4())
            )
            return error_response.to_bytes()

    async def _process_request_vote(self, request: RequestVoteRequest) -> RequestVoteResponse:
        """Process RequestVote RPC"""
        async with self.lock:
            self.last_heartbeat = time.time()

            if request.term < self.current_term:
                return RequestVoteResponse(
                    term=self.current_term,
                    vote_granted=False,
                    request_id=request.request_id
                )

            if (self.voted_for is None or self.voted_for == request.candidate_id):
                last_log_term = await self.storage.get_last_log_term()
                log_ok = (request.last_log_term > last_log_term or
                         (request.last_log_term == last_log_term and
                          request.last_log_index >= await self.storage.get_last_log_index()))

                if log_ok:
                    self.voted_for = request.candidate_id
                    await self.storage.set_voted_for(request.candidate_id)
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
    """Consensus manager"""

    def __init__(self, node_id: str, cluster_config: Dict[str, str], db_connection: Optional[DatabaseConnection] = None):
        self.node_id = node_id
        self.cluster_config = cluster_config
        self.transport = NetworkTransport(node_id)
        self.storage = PersistentStorage(node_id, db_connection)
        self.raft_node: Optional[RaftNode] = None
        self.logger = logging.getLogger(f"ConsensusManager-{node_id}")

    async def initialize(self):
        """Initialize consensus system"""
        await self.transport.initialize()

        for node_id, address in self.cluster_config.items():
            host, port = address.split(':')
            self.transport.add_node(node_id, host, int(port))

        cluster_nodes = list(self.cluster_config.keys())
        self.raft_node = RaftNode(self.node_id, cluster_nodes, self.transport, self.storage)

        asyncio.create_task(self.raft_node.start())

        self.logger.info(f"Consensus manager initialized for node {self.node_id}")

    async def shutdown(self):
        """Shutdown consensus system"""
        if self.raft_node:
            await self.raft_node.stop()

        self.logger.info(f"Consensus manager shutdown for node {self.node_id}")

    async def submit_command(self, command: Any, client_id: str = None) -> bool:
        """Submit command to consensus system"""
        if not self.raft_node or self.raft_node.role != NodeRole.LEADER:
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
            'role': self.raft_node.role.value,
            'term': self.raft_node.current_term,
            'log_length': len(self.raft_node.log),
            'commit_index': self.raft_node.commit_index,
            'last_applied': self.raft_node.last_applied,
            'cluster_nodes': self.raft_node.cluster_nodes,
            'state_machine_size': len(self.raft_node.state_machine)
        }


class DistributedLock:
    """Distributed lock using Raft consensus algorithm"""

    def __init__(self, consensus_manager: ConsensusManager, lock_name: str):
        self.consensus_manager = consensus_manager
        self.lock_name = lock_name
        self.holder: Optional[str] = None
        self.lock_id = f"lock_{lock_name}_{random.randint(1000, 9999)}"
        self.logger = logging.getLogger(f"DistributedLock-{lock_name}")

    async def acquire(self, holder_id: str, timeout: float = 5.0) -> bool:
        """Acquire distributed lock"""
        if self.holder is not None:
            return False

        lock_entry = {
            'type': 'lock_acquire',
            'lock_id': self.lock_id,
            'lock_name': self.lock_name,
            'holder': holder_id,
            'timestamp': datetime.utcnow().isoformat()
        }

        try:
            success = await asyncio.wait_for(
                self.consensus_manager.submit_command(lock_entry, holder_id),
                timeout=timeout
            )

            if success:
                self.holder = holder_id
                self.logger.info(f"Lock {self.lock_name} acquired by {holder_id}")

            return success
        except asyncio.TimeoutError:
            self.logger.warning(f"Lock acquisition timeout for {self.lock_name}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to acquire lock {self.lock_name}: {e}")
            return False

    async def release(self, holder_id: str) -> bool:
        """Release distributed lock"""
        if self.holder != holder_id:
            self.logger.warning(f"Lock {self.lock_name} not held by {holder_id}")
            return False

        lock_entry = {
            'type': 'lock_release',
            'lock_id': self.lock_id,
            'lock_name': self.lock_name,
            'holder': holder_id,
            'timestamp': datetime.utcnow().isoformat()
        }

        try:
            success = await self.consensus_manager.submit_command(lock_entry, holder_id)

            if success:
                self.holder = None
                self.logger.info(f"Lock {self.lock_name} released by {holder_id}")

            return success
        except Exception as e:
            self.logger.error(f"Failed to release lock {self.lock_name}: {e}")
            return False

    def is_locked(self) -> bool:
        """Check if lock is currently held"""
        return self.holder is not None

    def get_holder(self) -> Optional[str]:
        """Get current lock holder"""
        return self.holder

    async def __aenter__(self):
        """Async context manager entry"""
        if not await self.acquire("context_manager"):
            raise RuntimeError(f"Failed to acquire lock {self.lock_name}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.release("context_manager")


# Factory functions
def create_consensus_manager(node_id: str, cluster_config: Dict[str, str], 
                           db_connection: Optional[DatabaseConnection] = None) -> ConsensusManager:
    """Create consensus manager with optional database connection"""
    return ConsensusManager(node_id, cluster_config, db_connection)


# Global consensus manager instance
_consensus_manager: Optional[ConsensusManager] = None

def get_consensus_manager() -> ConsensusManager:
    """Get global consensus manager instance"""
    global _consensus_manager
    if _consensus_manager is None:
        _consensus_manager = ConsensusManager("default", {})
    return _consensus_manager