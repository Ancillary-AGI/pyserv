import asyncio
import signal
import logging
from typing import Optional
from hypercorn.asyncio import serve
from hypercorn.config import Config as HyperConfig

from .config import AppConfig
from .application import Application

class Server:
    def __init__(self, app: Application, config: Optional[AppConfig] = None):
        self.app = app
        self.config = config or AppConfig()
        self._server_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        self._workers: list = []
        self.logger = logging.getLogger("app.server")
        
    async def start(self) -> None:
        """Start the server with configured options"""
        try:
            self._setup_signal_handlers()
            await self.app.startup()
            
            hyper_config = self._create_hyper_config()
            
            # Use uvloop for better performance if available
            import uvloop
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            self.logger.info("Using uvloop for enhanced performance")
            
            if self.config.workers > 1:
                await self._start_multiprocess(hyper_config)
            else:
                await self._start_single_process(hyper_config)
                
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
            await self.shutdown()
            raise
    
    def _create_hyper_config(self) -> HyperConfig:
        """Create Hypercorn configuration"""
        config = HyperConfig()
        config.bind = [f"{self.config.host}:{self.config.port}"]
        config.backlog = self.config.backlog
        config.keep_alive_timeout = self.config.keep_alive_timeout
        config.max_connections = self.config.max_connections
        config.use_reloader = self.config.reload
        config.accesslog = self.config.access_log
        config.errorlog = self.config.access_log
        
        if self.config.ssl_certfile and self.config.ssl_keyfile:
            config.certfile = self.config.ssl_certfile
            config.keyfile = self.config.ssl_keyfile
        
        return config
    
    async def _start_single_process(self, config: HyperConfig) -> None:
        """Start server in single process mode"""
        self.logger.info(f"Starting server on {self.config.host}:{self.config.port}")
        await serve(self.app, config, shutdown_trigger=self._shutdown_wait)
    
    async def _start_multiprocess(self, config: HyperConfig) -> None:
        """Start server with multiple worker processes"""
        import multiprocessing
        from hypercorn.run import run_single
        
        self.logger.info(f"Starting {self.config.workers} workers on {self.config.host}:{self.config.port}")
        
        for i in range(self.config.workers):
            process = multiprocessing.Process(
                target=run_single,
                args=(self.app, config),
                kwargs={"worker_id": i, "shutdown_trigger": self._shutdown_wait}
            )
            process.start()
            self._workers.append(process)
        
        await self._shutdown_event.wait()
        
        for process in self._workers:
            process.terminate()
            process.join()
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown"""
        loop = asyncio.get_event_loop()
        for sig in [signal.SIGTERM, signal.SIGINT]:
            loop.add_signal_handler(sig, lambda s=sig: self._handle_shutdown_signal(s))
    
    def _handle_shutdown_signal(self, sig: signal.Signals) -> None:
        """Handle shutdown signals gracefully"""
        sig_name = signal.Signals(sig).name
        self.logger.info(f"Received signal {sig_name}, shutting down gracefully...")
        self._shutdown_event.set()
    
    async def _shutdown_wait(self) -> bool:
        """Wait for shutdown event"""
        await self._shutdown_event.wait()
        return True
    
    async def shutdown(self) -> None:
        """Graceful shutdown of the server"""
        self.logger.info("Initiating graceful shutdown...")
        self._shutdown_event.set()
        await self.app.shutdown()
        
        if self._server_task and not self._server_task.done():
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Server shutdown complete")
    
    def run(self) -> None:
        """Run the server (blocking call)"""
        try:
            logging.basicConfig(
                level=logging.DEBUG if self.config.debug else logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            
            asyncio.run(self.start())
            
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        except Exception as e:
            self.logger.error(f"Server error: {e}")
        finally:
            asyncio.run(self.shutdown())




