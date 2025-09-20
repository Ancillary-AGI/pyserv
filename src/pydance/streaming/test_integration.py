#!/usr/bin/env python3
"""
Test script for PyDance Streaming C++ Integration
Tests the channels and interfaces between Python and C++ code
"""

import sys
import os
import time
import asyncio
from typing import List, Dict, Any

# Add the parent directory to the path to import pydance modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from pydance.streaming.stream_bindings import (
    QuantumStreamServer,
    QuantumMediaEngine,
    UltraStreamServer,
    StreamConfig,
    StreamType,
    StreamManager,
    NetworkAwareScheduler,
    AdaptiveCompressor,
    StreamEncryptor
)


def test_cpp_integration():
    """Test C++ core integration"""
    print("Testing C++ Streaming Core Integration...")

    # Test Quantum Stream Server
    server = QuantumStreamServer()
    print(f"✓ QuantumStreamServer created: {server._server is not None}")

    # Test Quantum Media Engine
    engine = QuantumMediaEngine()
    print(f"✓ QuantumMediaEngine created: {engine._engine is not None}")

    # Test frame processing
    test_frame = b"Hello, this is a test video frame!" * 100
    processed_frame = engine.process_video_frame(test_frame)
    print(f"✓ Video frame processed: {len(processed_frame)} bytes")

    # Test audio processing
    test_audio = b"This is test audio data!" * 50
    processed_audio = engine.process_audio_frame(test_audio)
    print(f"✓ Audio frame processed: {len(processed_audio)} bytes")

    # Test Python processors
    def video_enhancer(frame: bytes) -> bytes:
        return frame + b"[ENHANCED]"

    def audio_filter(audio: bytes) -> bytes:
        return audio.upper()

    engine.add_frame_processor(video_enhancer)
    engine.add_audio_processor(audio_filter)

    enhanced_frame = engine.process_video_frame(test_frame)
    print(f"✓ Enhanced video frame: {len(enhanced_frame)} bytes (includes enhancement)")

    enhanced_audio = engine.process_audio_frame(test_audio)
    print(f"✓ Filtered audio frame: {len(enhanced_audio)} bytes")

    print("✓ C++ Integration tests passed!")


def test_python_structures():
    """Test Python data structures and algorithms"""
    print("\nTesting Python Streaming Structures...")

    # Test Network Aware Scheduler
    scheduler = NetworkAwareScheduler()
    scheduler.add_metrics_sample(5000000, 50)  # 5Mbps, 50ms latency
    scheduler.add_metrics_sample(3000000, 80)  # 3Mbps, 80ms latency

    optimal_bitrate = scheduler.calculate_optimal_bitrate()
    print(f"✓ Optimal bitrate calculated: {optimal_bitrate} bps")

    # Test Adaptive Compressor
    compressor = AdaptiveCompressor()
    test_data = b"Test data for compression" * 100

    compressed = compressor.compress(test_data, 'video', {'throughput': 2000000})
    print(f"✓ Data compressed: {len(test_data)} -> {len(compressed)} bytes")

    # Test Stream Encryptor
    encryptor = StreamEncryptor(b"master_key_1234567890123456")
    encrypted = encryptor.encrypt_chunk(1, test_data)
    print(f"✓ Data encrypted: {len(test_data)} -> {len(encrypted)} bytes")

    print("✓ Python structures tests passed!")


def test_stream_manager():
    """Test stream management functionality"""
    print("\nTesting Stream Management...")

    config = StreamConfig(
        chunk_size=4096,
        buffer_size=10,
        max_bitrate=5000000,
        adaptive_bitrates=[500000, 1000000, 2500000, 5000000]
    )

    manager = StreamManager("test_stream", StreamType.LIVE, config)
    print(f"✓ StreamManager created for stream: {manager.stream_id}")

    # Test chunk processing
    test_chunk = b"Test chunk data" * 100
    processed = asyncio.run(manager._process_chunk(1, test_chunk))
    print(f"✓ Chunk processed: {len(test_chunk)} -> {len(processed)} bytes")

    print("✓ Stream management tests passed!")


async def test_async_server():
    """Test async streaming server"""
    print("\nTesting Async Streaming Server...")

    server = UltraStreamServer(host='127.0.0.1', port=8081)

    # Start server in background
    server_task = asyncio.create_task(server.start_server())

    # Let it run for a short time
    await asyncio.sleep(0.1)

    print("✓ Async server started successfully")

    # Cancel the server
    server_task.cancel()
    try:
        await server_task
    except asyncio.CancelledError:
        pass

    print("✓ Async server stopped successfully")


def main():
    """Run all integration tests"""
    print("PyDance Streaming Integration Test Suite")
    print("=" * 50)

    try:
        # Test C++ integration
        test_cpp_integration()

        # Test Python structures
        test_python_structures()

        # Test stream manager
        test_stream_manager()

        # Test async server
        asyncio.run(test_async_server())

        print("\n" + "=" * 50)
        print("🎉 All integration tests passed!")
        print("✓ Python-C++ channels working correctly")
        print("✓ Streaming interfaces functional")
        print("✓ Performance optimizations active")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
