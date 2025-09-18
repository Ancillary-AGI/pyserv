# Gunicorn configuration for PyDance applications
# Copy this file to your project root and modify as needed

import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvloop" if os.name != "nt" else "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Timeout settings
timeout = 30
keepalive = 10
graceful_timeout = 30

# Logging
loglevel = "info"
accesslog = "/app/logs/access.log"
errorlog = "/app/logs/error.log"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "pydance"

# Server mechanics
preload_app = True
pidfile = "/app/logs/gunicorn.pid"
user = "pydance"
group = "pydance"
tmp_upload_dir = None

# SSL (uncomment and configure if needed)
# keyfile = "/path/to/ssl/private.key"
# certfile = "/path/to/ssl/certificate.crt"
# ssl_version = "TLSv1_2"
# ciphers = "ECDHE+AESGCM:ECDHE+ChaCha20:ECDHE+AES"

# Application
wsgi_module = "app:app"
pythonpath = "/app"

# Development overrides (uncomment for development)
if os.getenv("DEBUG", "false").lower() == "true":
    reload = True
    workers = 1
    loglevel = "debug"
    accesslog = "-"
    errorlog = "-"

# Production optimizations
if os.getenv("ENVIRONMENT", "development").lower() == "production":
    # Disable debug mode
    debug = False

    # Optimize for production
    worker_class = "uvloop" if os.name != "nt" else "sync"

    # Enable statsd metrics (if available)
    # statsd_host = "localhost:8125"
    # statsd_prefix = "pydance"

    # Enable Prometheus metrics (if available)
    # prometheus_registry = None

# Custom worker class for PyDance (if needed)
# def worker_exit(server, worker):
#     """Called when a worker exits"""
#     pass

# def worker_int(worker):
#     """Called when a worker receives INT signal"""
#     pass

# def post_fork(server, worker):
#     """Called after a worker has been forked"""
#     pass

# def pre_fork(server, worker):
#     """Called before a worker is forked"""
#     pass

# def pre_exec(server):
#     """Called in the parent process before forking"""
#     pass

# def when_ready(server):
#     """Called when the server is ready to accept connections"""
#     pass

# def on_starting(server):
#     """Called when the server is starting"""
#     pass

# def on_reload(server):
#     """Called when the server is reloading"""
#     pass
