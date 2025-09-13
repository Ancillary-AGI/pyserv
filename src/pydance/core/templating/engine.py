# server_framework/templating/engine.py
from typing import Dict, Any, Optional, Type
from pathlib import Path
import os

class AbstractTemplateEngine:
    """Abstract base class for all template engines"""
    
    def __init__(self, template_dir: Path, **options):
        self.template_dir = template_dir
        self.options = options
    
    async def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a template file"""
        raise NotImplementedError("Subclasses must implement render()")
    
    async def render_string(self, template_string: str, context: Dict[str, Any]) -> str:
        """Render a template string"""
        raise NotImplementedError("Subclasses must implement render_string()")

class TemplateEngineManager:
    """Main template engine manager that supports multiple template engines"""
    
    def __init__(self, template_dir: str = "templates"):
        self.template_dir = Path(template_dir)
        self.engines: Dict[str, AbstractTemplateEngine] = {}
        self.default_engine = None
        
        # Ensure template directory exists
        self.template_dir.mkdir(exist_ok=True)
    
    def register_engine(self, name: str, engine_class: Type[AbstractTemplateEngine], **options):
        """Register a template engine"""
        engine = engine_class(self.template_dir, **options)
        self.engines[name] = engine
        if not self.default_engine:
            self.default_engine = engine
    
    def set_default_engine(self, name: str):
        """Set the default template engine"""
        if name in self.engines:
            self.default_engine = self.engines[name]
        else:
            raise ValueError(f"Engine '{name}' not registered")
    
    async def render(self, template_name: str, context: Dict[str, Any] = None, 
                    engine: str = None) -> str:
        """Render a template using the specified engine or default engine"""
        engine_obj = self._get_engine(engine)
        return await engine_obj.render(template_name, context or {})
    
    async def render_string(self, template_string: str, context: Dict[str, Any] = None,
                          engine: str = None) -> str:
        """Render a template string using the specified engine or default engine"""
        engine_obj = self._get_engine(engine)
        return await engine_obj.render_string(template_string, context or {})
    
    def _get_engine(self, engine_name: Optional[str] = None) -> 'AbstractTemplateEngine':
        """Get the specified engine or default engine"""
        if engine_name:
            engine_obj = self.engines.get(engine_name)
            if not engine_obj:
                raise ValueError(f"Template engine '{engine_name}' not registered")
            return engine_obj
        
        if not self.default_engine:
            raise ValueError("No template engine configured")
        
        return self.default_engine
