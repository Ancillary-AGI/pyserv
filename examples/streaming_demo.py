#!/usr/bin/env python3
"""
Pyserv  Ultra-Low Latency Streaming Demo
Demonstrates advanced streaming with C/C++ core and enterprise security
"""

import asyncio
import time
import json
import os
import math
from typing import Dict, List, Optional, Any
import hashlib
import struct

# Pyserv  Framework Imports
from pyserv import Application
from pyserv.security import (
    get_iam_system, get_crypto_manager,
    get_zero_trust_network, get_defense_in_depth
)
from pyserv.streaming import (
    UltraStreamServer, StreamManager, StreamType, StreamConfig,
    QuantumMediaEngine, NetworkAwareScheduler,
    AdaptiveChunkScheduler, PredictiveCache,
    StreamEncryptor, AdaptiveCompressor
)


class StreamingApplication:
    """Complete streaming application with enterprise features"""

    def __init__(self):
        # Initialize Pyserv  components
        self.http_server = Application()
        self.stream_server = UltraStreamServer(host="127.0.0.1", port=8081)
        self.media_engine = QuantumMediaEngine()
        self.network_scheduler = NetworkAwareScheduler()
        self.chunk_scheduler = AdaptiveChunkScheduler()
        self.predictive_cache = PredictiveCache(max_size=5000)

        # Initialize security systems
        self.iam = get_iam_system()
        self.crypto = get_crypto_manager()
        self.zero_trust = get_zero_trust_network()
        self.defense = get_defense_in_depth()

        # Streaming components
        self.streams: Dict[str, StreamManager] = {}
        self.stream_configs: Dict[str, StreamConfig] = {}

        # Performance monitoring
        self.metrics = {
            'streams_active': 0,
            'clients_connected': 0,
            'bytes_streamed': 0,
            'avg_bitrate': 0,
            'cache_hit_rate': 0.0
        }

    async def initialize(self):
        """Initialize the streaming application"""
        print("🚀 Initializing Pyserv  Ultra-Low Latency Streaming System...")

        # Create default streams
        await self._create_default_streams()

        # Set up security policies
        await self._setup_security_policies()

        # Configure monitoring
        await self._setup_monitoring()

        print("✅ Streaming system initialized successfully!")

    async def _create_default_streams(self):
        """Create default streaming configurations"""
        # Live streaming configuration
        live_config = StreamConfig(
            chunk_size=8192,
            buffer_size=30,
            max_bitrate=8000000,
            adaptive_bitrates=[500000, 1000000, 2500000, 5000000, 8000000],
            encryption_enabled=True
        )

        # Low-latency streaming configuration
        low_latency_config = StreamConfig(
            chunk_size=4096,
            buffer_size=10,
            max_bitrate=3000000,
            adaptive_bitrates=[300000, 600000, 1200000, 2400000, 3000000],
            encryption_enabled=True
        )

        # VOD streaming configuration
        vod_config = StreamConfig(
            chunk_size=16384,
            buffer_size=50,
            max_bitrate=10000000,
            adaptive_bitrates=[500000, 1000000, 2500000, 5000000, 10000000],
            encryption_enabled=True
        )

        self.stream_configs = {
            'live_main': live_config,
            'live_backup': live_config,
            'low_latency': low_latency_config,
            'vod_premium': vod_config,
            'vod_standard': vod_config
        }

        # Create stream managers
        for stream_id, config in self.stream_configs.items():
            stream_type = StreamType.LIVE if 'live' in stream_id else \
                         StreamType.LOW_LATENCY if 'low_latency' in stream_id else \
                         StreamType.VOD

            self.streams[stream_id] = StreamManager(stream_id, stream_type, config)
            print(f"📺 Created stream: {stream_id} ({stream_type.value})")

    async def _setup_security_policies(self):
        """Set up enterprise security policies"""
        # Create streaming-specific roles
        streamer_role = self.iam.create_role("streamer", permissions={
            "stream.create", "stream.publish", "stream.manage"
        })

        viewer_role = self.iam.create_role("viewer", permissions={
            "stream.view", "stream.subscribe"
        })

        admin_role = self.iam.create_role("stream_admin", permissions={
            "stream.*", "user.manage", "system.monitor"
        })

        # Set up zero-trust policies for streaming
        self.zero_trust.add_policy({
            'name': 'streaming_access',
            'conditions': {
                'device_trust_score': {'min': 0.8},
                'network_security': {'level': 'high'},
                'geographic_restriction': {'allowed_countries': ['US', 'CA', 'GB']}
            }
        })

        print("🔒 Security policies configured")

    async def _setup_monitoring(self):
        """Set up comprehensive monitoring"""
        # Monitor cache performance
        asyncio.create_task(self._monitor_cache_performance())

        # Monitor network conditions
        asyncio.create_task(self._monitor_network_conditions())

        # Monitor stream health
        asyncio.create_task(self._monitor_stream_health())

        print("📊 Monitoring system activated")

    async def _monitor_cache_performance(self):
        """Monitor predictive cache performance"""
        while True:
            self.metrics['cache_hit_rate'] = self.predictive_cache.get_hit_rate()
            await asyncio.sleep(60)  # Update every minute

    async def _monitor_network_conditions(self):
        """Monitor network conditions for adaptive streaming"""
        while True:
            # Simulate network metrics collection
            latency = 25 + (hashlib.md5(str(time.time()).encode()).digest()[0] % 50)
            bandwidth = 5000000 + (hashlib.md5(str(time.time()).encode()).digest()[1] % 5000000)

            self.network_scheduler.add_metrics_sample(bandwidth, latency)
            await asyncio.sleep(5)  # Update every 5 seconds

    async def _monitor_stream_health(self):
        """Monitor stream health and performance"""
        while True:
            total_clients = sum(len(stream.clients) for stream in self.streams.values())
            self.metrics['clients_connected'] = total_clients

            active_streams = sum(1 for stream in self.streams.values() if stream.clients)
            self.metrics['streams_active'] = active_streams

            await asyncio.sleep(30)  # Update every 30 seconds

    async def start_streaming_server(self):
        """Start the streaming server"""
        print("🎬 Starting Ultra-Low Latency Streaming Server...")

        # Start HTTP API server
        asyncio.create_task(self._start_http_api())

        # Start streaming server
        await self.stream_server.start_server()

    async def _start_http_api(self):
        """Start HTTP API for stream management"""
        @self.http_server.get("/api/streams")
        def list_streams(request):
            streams_info = {}
            for stream_id, stream in self.streams.items():
                streams_info[stream_id] = {
                    'type': stream.stream_type.value,
                    'clients': len(stream.clients),
                    'bitrate': stream.config.max_bitrate,
                    'status': 'active' if stream.clients else 'idle'
                }

            return {
                'status_code': 200,
                'content_type': 'application/json',
                'body': json.dumps({
                    'streams': streams_info,
                    'metrics': self.metrics
                })
            }

        @self.http_server.get("/api/streams/{stream_id}")
        def get_stream_info(request, stream_id: str):
            if stream_id not in self.streams:
                return {
                    'status_code': 404,
                    'content_type': 'application/json',
                    'body': json.dumps({'error': 'Stream not found'})
                }

            stream = self.streams[stream_id]
            return {
                'status_code': 200,
                'content_type': 'application/json',
                'body': json.dumps({
                    'stream_id': stream_id,
                    'type': stream.stream_type.value,
                    'clients': len(stream.clients),
                    'config': {
                        'chunk_size': stream.config.chunk_size,
                        'buffer_size': stream.config.buffer_size,
                        'max_bitrate': stream.config.max_bitrate,
                        'adaptive_bitrates': stream.config.adaptive_bitrates
                    },
                    'current_chunk': stream.current_chunk_id,
                    'buffer_usage': len(stream.chunk_buffer.buffer) if hasattr(stream.chunk_buffer, 'buffer') else 0
                })
            }

        @self.http_server.post("/api/streams/{stream_id}/subscribe")
        def subscribe_to_stream(request, stream_id: str):
            if stream_id not in self.streams:
                return {
                    'status_code': 404,
                    'content_type': 'application/json',
                    'body': json.dumps({'error': 'Stream not found'})
                }

            # Simulate client subscription
            client_id = f"client_{hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]}"

            return {
                'status_code': 200,
                'content_type': 'application/json',
                'body': json.dumps({
                    'message': f'Subscribed to stream {stream_id}',
                    'client_id': client_id,
                    'stream_config': {
                        'chunk_size': self.streams[stream_id].config.chunk_size,
                        'adaptive_bitrates': self.streams[stream_id].config.adaptive_bitrates
                    }
                })
            }

        @self.http_server.get("/api/metrics")
        def get_metrics(request):
            return {
                'status_code': 200,
                'content_type': 'application/json',
                'body': json.dumps({
                    'timestamp': time.time(),
                    'metrics': self.metrics,
                    'network': {
                        'optimal_bitrate': self.network_scheduler.calculate_optimal_bitrate(),
                        'cache_hit_rate': self.metrics['cache_hit_rate']
                    }
                })
            }

        @self.http_server.get("/api/health")
        def health_check(request):
            return {
                'status_code': 200,
                'content_type': 'application/json',
                'body': json.dumps({
                    'status': 'healthy',
                    'server': 'Pyserv  Ultra-Low Latency Streaming',
                    'version': '1.0.0',
                    'uptime': time.time(),
                    'streams': len(self.streams),
                    'active_clients': self.metrics['clients_connected']
                })
            }

        # Start HTTP server
        print("🌐 HTTP API server starting on port 8000...")
        self.http_server.run()

    async def simulate_streaming_traffic(self):
        """Simulate streaming traffic for demonstration"""
        print("🎭 Simulating streaming traffic...")

        # Simulate multiple clients subscribing to streams
        for i in range(10):
            stream_id = list(self.streams.keys())[i % len(self.streams)]
            client_id = f"sim_client_{i}"

            await self.streams[stream_id].add_client(client_id)
            print(f"👤 Client {client_id} subscribed to {stream_id}")

            # Simulate some traffic
            await asyncio.sleep(0.1)

        # Simulate network condition changes
        print("📡 Simulating network condition changes...")
        for _ in range(20):
            # Random network conditions
            latency = 20 + (hashlib.md5(str(time.time()).encode()).digest()[0] % 80)
            bandwidth = 1000000 + (hashlib.md5(str(time.time()).encode()).digest()[1] % 9000000)

            self.network_scheduler.add_metrics_sample(bandwidth, latency)

            optimal_bitrate = self.network_scheduler.calculate_optimal_bitrate()
            print(f"📊 Network: {bandwidth/1000000:.1f} Mbps, {latency}ms latency -> {optimal_bitrate/1000000:.1f} Mbps optimal bitrate")

            await asyncio.sleep(2)

    async def run_demo(self):
        """Run the complete streaming demo"""
        try:
            # Initialize system
            await self.initialize()

            # Start background tasks
            asyncio.create_task(self.simulate_streaming_traffic())

            # Start servers
            await self.start_streaming_server()

        except KeyboardInterrupt:
            print("\n🛑 Shutting down streaming system...")
        except Exception as e:
            print(f"❌ Error in streaming system: {e}")
            raise
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Clean up resources"""
        print("🧹 Cleaning up streaming resources...")

        # Clean up streams
        for stream in self.streams.values():
            if stream.producer_task and not stream.producer_task.done():
                stream.producer_task.cancel()

        # Clean up cache
        self.predictive_cache = None

        print("✅ Cleanup completed")


class StreamProducer:
    """Simulated stream producer for demonstration"""

    def __init__(self, media_engine: QuantumMediaEngine):
        self.media_engine = media_engine
        self.is_running = False

    async def start_producing(self, stream_id: str):
        """Start producing media for a stream"""
        self.is_running = True
        print(f"🎬 Starting media production for stream: {stream_id}")

        frame_count = 0
        try:
            while self.is_running:
                # Generate simulated video frame
                frame_data = self._generate_video_frame(frame_count)
                audio_data = self._generate_audio_frame(frame_count)

                # Process through media engine
                self.media_engine.process_video_frame(frame_data)
                self.media_engine.process_audio_frame(audio_data)

                frame_count += 1
                await asyncio.sleep(1/30)  # 30 FPS

        except Exception as e:
            print(f"❌ Media production error: {e}")

    def stop_producing(self):
        """Stop media production"""
        self.is_running = False
        print("🎬 Media production stopped")

    def _generate_video_frame(self, frame_count: int) -> bytes:
        """Generate simulated video frame"""
        # Create a simple pattern based on frame count
        width, height = 1920, 1080
        frame_size = width * height * 3  # RGB

        frame_data = bytearray(frame_size)
        for i in range(0, frame_size, 3):
            # Create moving color pattern
            r = (frame_count + i) % 256
            g = (frame_count * 2 + i) % 256
            b = (frame_count * 3 + i) % 256

            frame_data[i] = r
            frame_data[i + 1] = g
            frame_data[i + 2] = b

        return bytes(frame_data)

    def _generate_audio_frame(self, frame_count: int) -> bytes:
        """Generate simulated audio frame"""
        # 48kHz, 16-bit, stereo, 20ms frame
        samples_per_frame = int(48000 * 0.02)  # 20ms
        frame_size = samples_per_frame * 2 * 2  # 16-bit stereo

        audio_data = bytearray(frame_size)
        for i in range(0, len(audio_data), 2):
            # Generate sine wave
            sample = int(32767 * 0.3 * math.sin(2 * math.pi * 440 * (frame_count * 0.02 + i / 96000)))
            audio_data[i] = sample & 0xFF
            audio_data[i + 1] = (sample >> 8) & 0xFF

        return bytes(audio_data)


async def main():
    """Main entry point"""
    print("🎪 Pyserv  Ultra-Low Latency Streaming Demo")
    print("=" * 50)

    # Create streaming application
    app = StreamingApplication()

    # Create stream producer
    producer = StreamProducer(app.media_engine)

    try:
        # Start producer for main live stream
        asyncio.create_task(producer.start_producing("live_main"))

        # Run the streaming application
        await app.run_demo()

    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        raise
    finally:
        producer.stop_producing()


if __name__ == "__main__":
    # Set up asyncio event loop policy for better performance
    if os.name == 'nt':  # Windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Run the demo
    asyncio.run(main())




