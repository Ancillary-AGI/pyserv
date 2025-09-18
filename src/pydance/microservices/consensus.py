"""
Distributed consensus implementation for PyDance framework.

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
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

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
            # In a real implementation, this would be an RPC call
            # For now, simulate with random success
            await asyncio.sleep(random.uniform(0.01, 0.05))  # Simulate network delay
            return random.random() > 0.3  # 70% chance of getting vote
        except Exception as e:
            logger.error(f"Failed to request vote from {peer}: {e}")
            return False

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
            # In a real implementation, this would be an RPC call
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
            # In a real implementation, this would send AppendEntries RPC with no entries
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
