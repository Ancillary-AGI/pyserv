"""
WebAssembly (WASM) Support for Pyserv  Framework.
Provides secure execution environment for WASM modules.
"""

from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import hashlib
import secrets
import base64
import json
from pathlib import Path
import aiofiles
import wasmtime


@dataclass
class WASMModule:
    """WebAssembly module representation"""
    module_id: str
    name: str
    version: str
    wasm_bytes: bytes
    checksum: str
    permissions: List[str] = field(default_factory=list)
    memory_limit: int = 64 * 1024 * 1024  # 64MB default
    execution_timeout: int = 30  # seconds
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'module_id': self.module_id,
            'name': self.name,
            'version': self.version,
            'checksum': self.checksum,
            'permissions': self.permissions,
            'memory_limit': self.memory_limit,
            'execution_timeout': self.execution_timeout,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active
        }


@dataclass
class WASMExecutionResult:
    """Result of WASM module execution"""
    module_id: str
    function_name: str
    execution_time: float
    success: bool
    result: Any = None
    error: Optional[str] = None
    memory_used: int = 0
    gas_used: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'module_id': self.module_id,
            'function_name': self.function_name,
            'execution_time': self.execution_time,
            'success': self.success,
            'result': self.result,
            'error': self.error,
            'memory_used': self.memory_used,
            'gas_used': self.gas_used,
            'timestamp': self.timestamp.isoformat()
        }


class WASMSecurityManager:
    """Security manager for WASM execution"""

    def __init__(self):
        self.allowed_imports: Dict[str, Callable] = {}
        self.resource_limits: Dict[str, Any] = {}
        self.security_policies: List[Callable] = []

    def add_allowed_import(self, module_name: str, function_name: str, implementation: Callable):
        """Add allowed import for WASM modules"""
        key = f"{module_name}.{function_name}"
        self.allowed_imports[key] = implementation

    def set_resource_limit(self, resource: str, limit: Any):
        """Set resource limit for WASM execution"""
        self.resource_limits[resource] = limit

    def add_security_policy(self, policy_func: Callable):
        """Add security policy for WASM execution"""
        self.security_policies.append(policy_func)

    async def validate_module(self, wasm_bytes: bytes) -> Dict[str, Any]:
        """Validate WASM module for security"""
        try:
            # Parse WASM module
            module = wasmtime.Module.from_bytes(wasm_bytes)

            # Check for dangerous imports
            dangerous_imports = ['wasi_snapshot_preview1', 'wasi_unstable']
            imports = []

            for import_ in module.imports:
                import_name = f"{import_.module}.{import_.name}"
                imports.append(import_name)

                if import_.module in dangerous_imports:
                    return {
                        'valid': False,
                        'error': f'Dangerous import detected: {import_name}'
                    }

                # Check if import is allowed
                if import_name not in self.allowed_imports:
                    return {
                        'valid': False,
                        'error': f'Unauthorized import: {import_name}'
                    }

            # Check exports for security
            exports = [export.name for export in module.exports]

            # Run security policies
            for policy in self.security_policies:
                if asyncio.iscoroutinefunction(policy):
                    result = await policy(wasm_bytes, imports, exports)
                else:
                    result = policy(wasm_bytes, imports, exports)

                if not result.get('allowed', True):
                    return {
                        'valid': False,
                        'error': result.get('reason', 'Security policy violation')
                    }

            return {
                'valid': True,
                'imports': imports,
                'exports': exports,
                'memory_required': getattr(module, 'memory_required', 0)
            }

        except Exception as e:
            return {
                'valid': False,
                'error': f'WASM validation error: {str(e)}'
            }

    def create_secure_imports(self) -> Dict[str, Dict[str, Any]]:
        """Create secure imports for WASM execution"""
        imports = {}

        for import_key, implementation in self.allowed_imports.items():
            module_name, function_name = import_key.split('.', 1)

            if module_name not in imports:
                imports[module_name] = {}

            imports[module_name][function_name] = implementation

        return imports


class WASMExecutionEngine:
    """Secure WASM execution engine"""

    def __init__(self, security_manager: WASMSecurityManager):
        self.security_manager = security_manager
        self.store = None
        self.instances: Dict[str, Any] = {}

    async def load_module(self, wasm_module: WASMModule) -> str:
        """Load WASM module securely"""
        # Validate module
        validation_result = await self.security_manager.validate_module(wasm_module.wasm_bytes)

        if not validation_result['valid']:
            raise ValueError(f"Module validation failed: {validation_result['error']}")

        # Create store with limits
        config = wasmtime.Config()
        config.memory_max = wasm_module.memory_limit // (64 * 1024)  # Convert to pages
        self.store = wasmtime.Store(config)

        # Create module
        module = wasmtime.Module.from_bytes(self.store, wasm_module.wasm_bytes)

        # Create secure imports
        imports = self.security_manager.create_secure_imports()

        # Instantiate module
        wasmtime_imports = []
        for import_ in module.imports:
            module_imports = imports.get(import_.module, {})
            func = module_imports.get(import_.name)

            if func:
                # Create wasmtime function from our implementation
                wasmtime_func = wasmtime.Func(self.store, func)
                wasmtime_imports.append(wasmtime_func)
            else:
                raise ValueError(f"Import not found: {import_.module}.{import_.name}")

        instance = wasmtime.Instance(self.store, module, wasmtime_imports)

        # Store instance
        instance_id = f"instance_{secrets.token_hex(8)}"
        self.instances[instance_id] = {
            'instance': instance,
            'module': wasm_module,
            'created_at': datetime.utcnow()
        }

        return instance_id

    async def execute_function(self, instance_id: str, function_name: str,
                             args: List[Any] = None) -> WASMExecutionResult:
        """Execute WASM function securely"""
        if instance_id not in self.instances:
            raise ValueError(f"Instance {instance_id} not found")

        instance_data = self.instances[instance_id]
        instance = instance_data['instance']
        wasm_module = instance_data['module']

        start_time = datetime.utcnow()

        try:
            # Get function
            func = instance.exports.get(function_name)
            if not func:
                raise ValueError(f"Function {function_name} not found in module")

            # Prepare arguments
            if args is None:
                args = []

            # Execute with timeout
            result = await asyncio.wait_for(
                self._execute_wasm_function(func, args),
                timeout=wasm_module.execution_timeout
            )

            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            return WASMExecutionResult(
                module_id=wasm_module.module_id,
                function_name=function_name,
                execution_time=execution_time,
                success=True,
                result=result,
                memory_used=0,  # Would track actual memory usage
                gas_used=0  # Would implement gas metering
            )

        except asyncio.TimeoutError:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return WASMExecutionResult(
                module_id=wasm_module.module_id,
                function_name=function_name,
                execution_time=execution_time,
                success=False,
                error="Execution timeout"
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            return WASMExecutionResult(
                module_id=wasm_module.module_id,
                function_name=function_name,
                execution_time=execution_time,
                success=False,
                error=str(e)
            )

    async def _execute_wasm_function(self, func, args: List[Any]) -> Any:
        """Execute WASM function"""
        # This would handle the actual WASM function execution
        # For demo purposes, return mock result
        return f"Executed {func} with args {args}"

    def unload_instance(self, instance_id: str):
        """Unload WASM instance"""
        if instance_id in self.instances:
            del self.instances[instance_id]

    def get_instance_info(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get instance information"""
        if instance_id not in self.instances:
            return None

        instance_data = self.instances[instance_id]
        return {
            'instance_id': instance_id,
            'module_id': instance_data['module'].module_id,
            'created_at': instance_data['created_at'].isoformat(),
            'memory_limit': instance_data['module'].memory_limit,
            'execution_timeout': instance_data['module'].execution_timeout
        }


class WASMRegistry:
    """Registry for WASM modules"""

    def __init__(self, registry_path: str = "./wasm_modules"):
        self.registry_path = Path(registry_path)
        self.registry_path.mkdir(exist_ok=True)
        self.modules: Dict[str, WASMModule] = {}
        self.execution_engine: Optional[WASMExecutionEngine] = None

    def set_execution_engine(self, engine: WASMExecutionEngine):
        """Set execution engine"""
        self.execution_engine = engine

    async def register_module(self, name: str, version: str, wasm_file_path: str,
                            permissions: List[str] = None) -> str:
        """Register WASM module"""
        # Read WASM file
        wasm_path = Path(wasm_file_path)
        if not wasm_path.exists():
            raise FileNotFoundError(f"WASM file not found: {wasm_file_path}")

        async with aiofiles.open(wasm_path, 'rb') as f:
            wasm_bytes = await f.read()

        # Calculate checksum
        checksum = hashlib.sha256(wasm_bytes).hexdigest()

        # Create module
        module_id = f"module_{secrets.token_hex(16)}"
        module = WASMModule(
            module_id=module_id,
            name=name,
            version=version,
            wasm_bytes=wasm_bytes,
            checksum=checksum,
            permissions=permissions or []
        )

        # Store module
        self.modules[module_id] = module

        # Save to registry
        await self._save_module(module)

        return module_id

    async def load_module(self, module_id: str) -> Optional[WASMModule]:
        """Load module from registry"""
        if module_id in self.modules:
            return self.modules[module_id]

        # Try to load from file
        module_path = self.registry_path / f"{module_id}.wasm"
        meta_path = self.registry_path / f"{module_id}.meta"

        if not module_path.exists() or not meta_path.exists():
            return None

        # Load metadata
        async with aiofiles.open(meta_path, 'r') as f:
            metadata = json.loads(await f.read())

        # Load WASM bytes
        async with aiofiles.open(module_path, 'rb') as f:
            wasm_bytes = await f.read()

        # Verify checksum
        actual_checksum = hashlib.sha256(wasm_bytes).hexdigest()
        if actual_checksum != metadata['checksum']:
            raise ValueError(f"Checksum mismatch for module {module_id}")

        # Create module
        module = WASMModule(
            module_id=metadata['module_id'],
            name=metadata['name'],
            version=metadata['version'],
            wasm_bytes=wasm_bytes,
            checksum=metadata['checksum'],
            permissions=metadata.get('permissions', []),
            memory_limit=metadata.get('memory_limit', 64 * 1024 * 1024),
            execution_timeout=metadata.get('execution_timeout', 30),
            created_at=datetime.fromisoformat(metadata['created_at']),
            is_active=metadata.get('is_active', True)
        )

        self.modules[module_id] = module
        return module

    async def _save_module(self, module: WASMModule):
        """Save module to registry"""
        # Save WASM bytes
        wasm_path = self.registry_path / f"{module.module_id}.wasm"
        async with aiofiles.open(wasm_path, 'wb') as f:
            await f.write(module.wasm_bytes)

        # Save metadata
        meta_path = self.registry_path / f"{module.module_id}.meta"
        async with aiofiles.open(meta_path, 'w') as f:
            await f.write(json.dumps(module.to_dict(), indent=2))

    async def execute_module_function(self, module_id: str, function_name: str,
                                    args: List[Any] = None) -> WASMExecutionResult:
        """Execute function from WASM module"""
        if not self.execution_engine:
            raise ValueError("Execution engine not set")

        # Load module
        module = await self.load_module(module_id)
        if not module:
            raise ValueError(f"Module {module_id} not found")

        # Load into execution engine
        instance_id = await self.execution_engine.load_module(module)

        try:
            # Execute function
            result = await self.execution_engine.execute_function(
                instance_id, function_name, args
            )

            return result

        finally:
            # Clean up instance
            self.execution_engine.unload_instance(instance_id)

    def list_modules(self) -> List[WASMModule]:
        """List registered modules"""
        return list(self.modules.values())

    def get_module_info(self, module_id: str) -> Optional[Dict[str, Any]]:
        """Get module information"""
        module = self.modules.get(module_id)
        if not module:
            return None

        return module.to_dict()

    async def update_module(self, module_id: str, **updates):
        """Update module"""
        module = self.modules.get(module_id)
        if not module:
            raise ValueError(f"Module {module_id} not found")

        for key, value in updates.items():
            if hasattr(module, key):
                setattr(module, key, value)

        # Save updated module
        await self._save_module(module)

    async def delete_module(self, module_id: str):
        """Delete module"""
        if module_id not in self.modules:
            return

        # Remove files
        wasm_path = self.registry_path / f"{module_id}.wasm"
        meta_path = self.registry_path / f"{module_id}.meta"

        if wasm_path.exists():
            wasm_path.unlink()
        if meta_path.exists():
            meta_path.unlink()

        # Remove from memory
        del self.modules[module_id]


class WASMSecurityPolicy:
    """Security policies for WASM execution"""

    @staticmethod
    def validate_imports(wasm_bytes: bytes, imports: List[str], exports: List[str]) -> Dict[str, Any]:
        """Validate WASM imports for security"""
        dangerous_imports = [
            'wasi_snapshot_preview1.fd_write',
            'wasi_snapshot_preview1.fd_read',
            'wasi_unstable.path_open'
        ]

        for import_name in imports:
            if import_name in dangerous_imports:
                return {
                    'allowed': False,
                    'reason': f'Dangerous import detected: {import_name}'
                }

        return {'allowed': True}

    @staticmethod
    def check_memory_usage(wasm_bytes: bytes, imports: List[str], exports: List[str]) -> Dict[str, Any]:
        """Check memory usage for security"""
        # Estimate memory requirements
        estimated_memory = len(wasm_bytes) * 2  # Rough estimate

        if estimated_memory > 128 * 1024 * 1024:  # 128MB limit
            return {
                'allowed': False,
                'reason': f'Memory requirement too high: {estimated_memory} bytes'
            }

        return {'allowed': True}

    @staticmethod
    def validate_exports(wasm_bytes: bytes, imports: List[str], exports: List[str]) -> Dict[str, Any]:
        """Validate WASM exports"""
        required_exports = ['main', 'init']  # At least one of these should be present

        has_required_export = any(export in exports for export in required_exports)

        if not has_required_export:
            return {
                'allowed': False,
                'reason': 'Module must export at least one of: main, init'
            }

        return {'allowed': True}


# Global instances
_wasm_registry = None
_wasm_security = None
_wasm_engine = None

def get_wasm_registry(registry_path: str = "./wasm_modules") -> WASMRegistry:
    """Get global WASM registry"""
    global _wasm_registry
    if _wasm_registry is None:
        _wasm_registry = WASMRegistry(registry_path)
    return _wasm_registry

def get_wasm_security_manager() -> WASMSecurityManager:
    """Get global WASM security manager"""
    global _wasm_security
    if _wasm_security is None:
        _wasm_security = WASMSecurityManager()

        # Add default security policies
        _wasm_security.add_security_policy(WASMSecurityPolicy.validate_imports)
        _wasm_security.add_security_policy(WASMSecurityPolicy.check_memory_usage)
        _wasm_security.add_security_policy(WASMSecurityPolicy.validate_exports)

        # Add allowed imports
        _wasm_security.add_allowed_import('env', 'print', lambda x: print(f"WASM: {x}"))
        _wasm_security.add_allowed_import('env', 'get_time', lambda: int(datetime.utcnow().timestamp()))

    return _wasm_security

def get_wasm_execution_engine() -> WASMExecutionEngine:
    """Get global WASM execution engine"""
    global _wasm_engine
    if _wasm_engine is None:
        security_manager = get_wasm_security_manager()
        _wasm_engine = WASMExecutionEngine(security_manager)
    return _wasm_engine

# Initialize global instances
def initialize_wasm_system():
    """Initialize WASM system"""
    registry = get_wasm_registry()
    engine = get_wasm_execution_engine()
    registry.set_execution_engine(engine)

# Utility functions
async def register_wasm_module(name: str, version: str, wasm_file: str,
                             permissions: List[str] = None) -> str:
    """Register WASM module"""
    registry = get_wasm_registry()
    return await registry.register_module(name, version, wasm_file, permissions)

async def execute_wasm_function(module_id: str, function_name: str,
                              args: List[Any] = None) -> WASMExecutionResult:
    """Execute WASM function"""
    registry = get_wasm_registry()
    return await registry.execute_module_function(module_id, function_name, args)

def list_wasm_modules() -> List[WASMModule]:
    """List registered WASM modules"""
    registry = get_wasm_registry()
    return registry.list_modules()

# Initialize on import
initialize_wasm_system()




