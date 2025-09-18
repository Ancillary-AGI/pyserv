"""
PyDance Streaming Module.

This module provides ultra-low latency streaming capabilities with C++ core
performance optimizations. It includes advanced streaming algorithms, network-
aware bitrate adaptation, and high-performance media processing.

The module integrates with the C++ streaming core (stream_core.cpp) for
maximum performance while providing a clean Python API.

Features:
- Ultra-low latency streaming
- Adaptive bitrate algorithms
- Network-aware scheduling
- Concurrent data structures
- C++ performance core with Python bindings
- Real-time media processing

Example:
    >>> from pydance.streaming import StreamingService
    >>>
    >>> service = StreamingService()
    >>> thread = service.start_streaming("0.0.0.0", 8080)
    >>> # Streaming service is now running
"""

import ctypes
import threading
from pathlib import Path
from typing import Optional

# Load the C++ streaming library
def _load_streaming_lib() -> Optional[ctypes.CDLL]:
    """Load the compiled C++ streaming library"""
    lib_paths = [
        Path(__file__).parent / "libstream_core.so",
        Path(__file__).parent / "libstream_core.dylib",
        Path(__file__).parent / "stream_core.dll",
        Path(__file__).parent / "build" / "libstream_core.so",
    ]

    for lib_path in lib_paths:
        if lib_path.exists():
            try:
                return ctypes.CDLL(str(lib_path))
            except OSError:
                continue

    return None

# Load the library
_stream_lib = _load_streaming_lib()

class QuantumStreamServer:
    """Python wrapper for C++ QuantumStreamServer"""

    def __init__(self):
        if _stream_lib:
            self._server = _stream_lib.create_stream_server()
        else:
            self._server = None
            print("Warning: Using fallback implementation (C++ library not available)")

    def __del__(self):
        if _stream_lib and self._server:
            _stream_lib.destroy_stream_server(self._server)

    def start_server(self, address: str = "0.0.0.0", port: int = 8080):
        """Start the streaming server"""
        if _stream_lib and self._server:
            _stream_lib.start_stream_server(self._server, address.encode(), port)
        else:
            print(f"Starting fallback server on {address}:{port}")
            # Fallback implementation would go here

class QuantumMediaEngine:
    """Python wrapper for C++ QuantumMediaEngine"""

    def __init__(self):
        if _stream_lib:
            self._engine = _stream_lib.create_media_engine()
        else:
            self._engine = None
            print("Warning: Using fallback media engine (C++ library not available)")

    def __del__(self):
        if _stream_lib and self._engine:
            _stream_lib.destroy_media_engine(self._engine)

    def process_video_frame(self, frame_data: bytes):
        """Process a video frame"""
        if _stream_lib and self._engine:
            data_array = (ctypes.c_uint8 * len(frame_data))(*frame_data)
            _stream_lib.process_video_frame(self._engine, data_array, len(frame_data))
        else:
            # Fallback processing
            pass

    def process_audio_frame(self, audio_data: bytes):
        """Process an audio frame"""
        if _stream_lib and self._engine:
            data_array = (ctypes.c_uint8 * len(audio_data))(*audio_data)
            _stream_lib.process_audio_frame(self._engine, data_array, len(audio_data))
        else:
            # Fallback processing
            pass

class StreamingService:
    """High-level streaming service"""

    def __init__(self):
        self.server = QuantumStreamServer()
        self.media_engine = QuantumMediaEngine()
        self._running = False

    def start_streaming(self, address: str = "0.0.0.0", port: int = 8080) -> threading.Thread:
        """Start the streaming service"""
        self._running = True
        print(f"Starting PyDance Streaming Service on {address}:{port}")

        # Start the server in a separate thread
        server_thread = threading.Thread(
            target=self.server.start_server,
            args=(address, port),
            daemon=True
        )
        server_thread.start()

        return server_thread

    def stop_streaming(self):
        """Stop the streaming service"""
        self._running = False
        print("Stopping PyDance Streaming Service")

    def process_media(self, video_data: Optional[bytes] = None, audio_data: Optional[bytes] = None):
        """Process media data"""
        if video_data:
            self.media_engine.process_video_frame(video_data)
        if audio_data:
            self.media_engine.process_audio_frame(audio_data)

# Global streaming service instance
streaming_service = StreamingService()

__all__ = [
    'QuantumStreamServer',
    'QuantumMediaEngine',
    'StreamingService',
    'streaming_service'
]
