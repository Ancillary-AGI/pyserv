import re
import os
import hashlib
import time
from typing import Callable, Dict, Any, List, Optional, Union, Tuple
from pathlib import Path
from datetime import datetime
import math
import json
import functools

from pyserv.templating.engine import AbstractTemplateEngine
from pyserv.security_middleware import get_security_middleware

class TemplateError(Exception):
    """Base exception for template errors"""
    def __init__(self, message: str, template_name: str = None, line_number: int = None):
        self.message = message
        self.template_name = template_name
        self.line_number = line_number
        super().__init__(f"{message}" + (f" in {template_name}:{line_number}" if template_name and line_number else ""))

class TemplateSyntaxError(TemplateError):
    """Syntax error in template"""
    pass

class TemplateRuntimeError(TemplateError):
    """Runtime error during template rendering"""
    pass

class LeanTemplateEngine(AbstractTemplateEngine):
    """Enhanced lightweight template engine with advanced features"""

    def __init__(self, template_dir: Path, **options):
        super().__init__(template_dir, **options)
        self.cache = {}
        self.macro_cache = {}
        self.filter_cache = {}

        # Enhanced regex patterns
        self.patterns = {
            'variable': r'\{\{([^}]+)\}\}',
            'block': r'\{%\s*(\w+)\s*(.*?)\s*%\}',
            'endblock': r'\{%\s*end(\w+)\s*%\}',
            'comment': r'\{\#.*?\#\}',
            'include': r'\{%\s*include\s+["\'](.*?)["\']\s*%\}',
            'extends': r'\{%\s*extends\s+["\'](.*?)["\']\s*%\}',
            'block_definition': r'\{%\s*block\s+(\w+)\s*%\}',
            'macro': r'\{%\s*macro\s+(\w+)\((.*?)\)\s*%\}',
            'endmacro': r'\{%\s*endmacro\s*%\}',
            'call': r'\{%\s*call\s+(\w+)\((.*?)\)\s*%\}',
            'filter': r'\{\{\s*(.*?)\s*\|\s*(\w+)(?::(.*?))?\s*\}\}',
            # New patterns for advanced features
            'set': r'\{%\s*set\s+(\w+)\s*=\s*(.*?)\s*%\}',
            'if': r'\{%\s*if\s+(.*?)\s*%\}',
            'elif': r'\{%\s*elif\s+(.*?)\s*%\}',
            'else': r'\{%\s*else\s*%\}',
            'endif': r'\{%\s*endif\s*%\}',
            'for': r'\{%\s*for\s+(\w+(?:\s*,\s*\w+)?)\s+in\s+(.*?)(?:\s+if\s+(.*?))?\s*%\}',
            'endfor': r'\{%\s*endfor\s*%\}',
            'while': r'\{%\s*while\s+(.*?)\s*%\}',
            'endwhile': r'\{%\s*endwhile\s*%\}',
            'break': r'\{%\s*break\s*%\}',
            'continue': r'\{%\s*continue\s*%\}',
            'raw': r'\{%\s*raw\s*%\}',
            'endraw': r'\{%\s*endraw\s*%\}',
            'load': r'\{%\s*load\s+["\'](.*?)["\']\s*%\}',
            'with': r'\{%\s*with\s+(.*?)\s*%\}',
            'endwith': r'\{%\s*endwith\s*%\}',
            'spaceless': r'\{%\s*spaceless\s*%\}',
            'endspaceless': r'\{%\s*endspaceless\s*%\}',
            'autoescape': r'\{%\s*autoescape\s+(\w+)\s*%\}',
            'endautoescape': r'\{%\s*endautoescape\s*%\}',
        }

        # Configuration options
        self.enable_cache = options.get('enable_cache', True)
        self.autoescape = options.get('autoescape', True)
        
        # Built-in filters
        self.filters = self._initialize_filters()
        
        # Macro storage
        self.macros = {}
        self.macro_stack = []

        # Template inheritance stack
        self.inheritance_stack = []

        # Performance monitoring
        self.render_stats = {
            'total_renders': 0,
            'cache_hits': 0,
            'avg_render_time': 0.0,
            'errors': 0
        }
    
    async def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a template file"""
        template_path = self.template_dir / template_name
        
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        # Get template content (from cache or file)
        if self.enable_cache and template_path in self.cache:
            template_content = self.cache[template_path]
        else:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            if self.enable_cache:
                self.cache[template_path] = template_content
        
        # Check for template inheritance
        extends_match = re.search(self.patterns['extends'], template_content)
        if extends_match:
            return await self._render_with_inheritance(template_content, context, template_path.parent)
        
        return await self._render_content(template_content, context, template_path.parent)
    
    async def render_string(self, template_string: str, context: Dict[str, Any]) -> str:
        """Render a template string"""
        return await self._render_content(template_string, context, self.template_dir)
    
    async def _render_with_inheritance(self, content: str, context: Dict[str, Any], 
                                     base_dir: Path) -> str:
        """Render template with inheritance support"""
        extends_match = re.search(self.patterns['extends'], content)
        if not extends_match:
            return await self._render_content(content, context, base_dir)
        
        parent_template = extends_match.group(1)
        parent_path = base_dir / parent_template
        
        if not parent_path.exists():
            return await self._render_content(content, context, base_dir)
        
        # Load parent template
        with open(parent_path, 'r', encoding='utf-8') as f:
            parent_content = f.read()
        
        # Extract blocks from child template
        child_blocks = self._extract_blocks(content)
        
        # Replace blocks in parent template with child blocks
        def replace_blocks(match):
            block_name = match.group(1)
            return child_blocks.get(block_name, match.group(0))
        
        # Process parent template with child blocks
        parent_content = re.sub(
            self.patterns['block_definition'],
            replace_blocks,
            parent_content
        )
        
        return await self._render_content(parent_content, context, parent_path.parent)
    
    def _extract_blocks(self, content: str) -> Dict[str, str]:
        """Extract blocks from template content"""
        blocks = {}
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            block_match = re.match(self.patterns['block_definition'], line)
            
            if block_match:
                block_name = block_match.group(1)
                block_content = []
                i += 1
                
                # Find endblock
                while i < len(lines):
                    current_line = lines[i]
                    endblock_match = re.search(r'\{%\s*endblock\s*%\}', current_line)
                    
                    if endblock_match:
                        break
                    
                    block_content.append(current_line)
                    i += 1
                
                blocks[block_name] = '\n'.join(block_content)
            
            i += 1
        
        return blocks
    
    async def _render_content(self, content: str, context: Dict[str, Any],
                            base_dir: Path) -> str:
        """Render template content with context"""
        # Process macros first
        content = await self._process_macros(content, context, base_dir)

        # Process includes
        content = await self._process_includes(content, context, base_dir)

        # Remove comments
        content = re.sub(self.patterns['comment'], '', content)

        # Process blocks
        content = await self._process_blocks(content, context)

        # Process filters
        content = await self._process_filters(content, context)

        # Replace variables
        content = await self._replace_variables(content, context)

        # Apply security sanitization if enabled
        try:
            security_middleware = get_security_middleware()
            content = security_middleware.sanitize_template_output(content)
        except Exception:
            # If security middleware is not available, continue without sanitization
            pass

        return content
    
    async def _process_macros(self, content: str, context: Dict[str, Any], 
                            base_dir: Path) -> str:
        """Process macro definitions and calls"""
        lines = content.split('\n')
        output_lines = []
        i = 0
        
        # First pass: collect macro definitions
        while i < len(lines):
            line = lines[i]
            macro_match = re.match(self.patterns['macro'], line)
            
            if macro_match:
                macro_name = macro_match.group(1)
                macro_params = [p.strip() for p in macro_match.group(2).split(',')] if macro_match.group(2) else []
                
                # Find endmacro
                macro_content = []
                i += 1
                
                while i < len(lines):
                    current_line = lines[i]
                    endmacro_match = re.match(self.patterns['endmacro'], current_line)
                    
                    if endmacro_match:
                        break
                    
                    macro_content.append(current_line)
                    i += 1
                
                # Store macro
                self.macros[macro_name] = {
                    'params': macro_params,
                    'content': '\n'.join(macro_content)
                }
            
            i += 1
        
        # Second pass: process macro calls
        content = '\n'.join(lines)
        
        def process_macro_call(match):
            macro_name = match.group(1)
            macro_args = [arg.strip() for arg in match.group(2).split(',')] if match.group(2) else []
            
            if macro_name not in self.macros:
                return f"<!-- Macro {macro_name} not found -->"
            
            macro = self.macros[macro_name]
            macro_content = macro['content']
            macro_params = macro['params']
            
            # Create macro context
            macro_context = context.copy()
            for param, arg in zip(macro_params, macro_args):
                macro_context[param] = self._evaluate_expression(arg, context)
            
            # Render macro content
            return self._render_content_sync(macro_content, macro_context, base_dir)
        
        return re.sub(self.patterns['call'], process_macro_call, content)
    
    def _render_content_sync(self, content: str, context: Dict[str, Any], 
                           base_dir: Path) -> str:
        """Synchronous version of _render_content for use in macros"""
        # This is a simplified synchronous version for use in macro processing
        # Remove comments
        content = re.sub(self.patterns['comment'], '', content)
        
        # Replace variables
        content = self._replace_variables_sync(content, context)
        
        return content
    
    async def _process_includes(self, content: str, context: Dict[str, Any], 
                              base_dir: Path) -> str:
        """Process include directives"""
        def process_include(match):
            include_file = match.group(1)
            include_path = base_dir / include_file
            
            if not include_path.exists():
                return f"<!-- Include not found: {include_file} -->"
            
            # Read included template
            with open(include_path, 'r', encoding='utf-8') as f:
                included_content = f.read()
            
            # Recursively process the included template
            included_rendered = self._render_content_sync(included_content, context, include_path.parent)
            return included_rendered
        
        return re.sub(self.patterns['include'], process_include, content)
    
    async def _process_filters(self, content: str, context: Dict[str, Any]) -> str:
        """Process filter expressions"""
        def process_filter(match):
            expression = match.group(1).strip()
            filter_name = match.group(2)
            filter_args = match.group(3).split(':') if match.group(3) else []
            
            try:
                value = self._evaluate_expression(expression, context)
                
                if filter_name in self.filters:
                    # Apply filter with arguments
                    if filter_args:
                        result = value
                        for arg in filter_args:
                            result = self.filters[filter_name](result, *[a.strip() for a in arg.split(',')])
                        return str(result)
                    else:
                        return str(self.filters[filter_name](value))
                else:
                    return f"{{{{ {expression} | {filter_name} }}}}"  # Unknown filter
            except Exception as e:
                return f"{{{{ {expression} | {filter_name} }}}}"  # Filter error
        
        return re.sub(self.patterns['filter'], process_filter, content)
    
    async def _replace_variables(self, content: str, context: Dict[str, Any]) -> str:
        """Replace variables in template content"""
        def replace_match(match):
            var_name = match.group(1).strip()
            try:
                value = self._get_nested_value(context, var_name)
                if value is None:
                    return ''
                if self.autoescape and isinstance(value, str):
                    value = self._escape_filter(value)
                return str(value)
            except (KeyError, AttributeError):
                return f'{{{{ {var_name} }}}}'  # Keep original if not found
        
        return re.sub(self.patterns['variable'], replace_match, content)
    
    def _replace_variables_sync(self, content: str, context: Dict[str, Any]) -> str:
        """Synchronous version of variable replacement"""
        def replace_match(match):
            var_name = match.group(1).strip()
            try:
                value = self._get_nested_value(context, var_name)
                if value is None:
                    return ''
                if self.autoescape and isinstance(value, str):
                    value = self._escape_filter(value)
                return str(value)
            except (KeyError, AttributeError):
                return f'{{{{ {var_name} }}}}'  # Keep original if not found
        
        return re.sub(self.patterns['variable'], replace_match, content)
    
    async def _process_blocks(self, content: str, context: Dict[str, Any]) -> str:
        """Process template blocks (if, for, etc.)"""
        lines = content.split('\n')
        output_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Check for if block
            if_match = re.match(r'\{%\s*if\s+(.*?)\s*%\}', line)
            if if_match:
                condition = if_match.group(1)
                condition_result = self._evaluate_condition(condition, context)
                
                # Find endif
                endif_index = i
                while endif_index < len(lines) and not re.search(r'\{%\s*endif\s*%\}', lines[endif_index]):
                    endif_index += 1
                
                if condition_result:
                    # Include the content between if and endif
                    block_content = '\n'.join(lines[i+1:endif_index])
                    rendered_block = await self._render_content(block_content, context, self.template_dir)
                    output_lines.append(rendered_block)
                
                i = endif_index + 1
                continue
            
            # Check for elif block
            elif_match = re.match(r'\{%\s*elif\s+(.*?)\s*%\}', line)
            if elif_match:
                # elif should be inside an if block, skip for now
                output_lines.append(line)
                i += 1
                continue
            
            # Check for else block
            else_match = re.match(r'\{%\s*else\s*%\}', line)
            if else_match:
                # else should be inside an if block, skip for now
                output_lines.append(line)
                i += 1
                continue
            
            # Check for for loop
            for_match = re.match(r'\{%\s*for\s+(\w+)\s+in\s+(.*?)\s*%\}', line)
            if for_match:
                var_name = for_match.group(1)
                iterable_expr = for_match.group(2)
                
                # Find endfor
                endfor_index = i
                while endfor_index < len(lines) and not re.search(r'\{%\s*endfor\s*%\}', lines[endfor_index]):
                    endfor_index += 1
                
                # Get iterable
                iterable = self._evaluate_expression(iterable_expr, context)
                
                # Process loop content for each item
                loop_content = '\n'.join(lines[i+1:endfor_index])
                loop_output = []
                
                for item in iterable or []:
                    loop_context = context.copy()
                    loop_context[var_name] = item
                    # Add loop variables
                    loop_context['loop'] = {
                        'index': loop_output.__len__() + 1,
                        'index0': loop_output.__len__(),
                        'first': loop_output.__len__() == 0,
                        'last': loop_output.__len__() == len(iterable) - 1,
                        'length': len(iterable)
                    }
                    rendered_content = await self._render_content(loop_content, loop_context, self.template_dir)
                    loop_output.append(rendered_content)
                
                output_lines.append('\n'.join(loop_output))
                i = endfor_index + 1
                continue
            
            # Check for set block
            set_match = re.match(r'\{%\s*set\s+(\w+)\s*=\s*(.*?)\s*%\}', line)
            if set_match:
                var_name = set_match.group(1)
                expression = set_match.group(2)
                value = self._evaluate_expression(expression, context)
                context[var_name] = value
                i += 1
                continue
            
            # Check for raw block (no processing)
            raw_match = re.match(r'\{%\s*raw\s*%\}', line)
            if raw_match:
                # Find endraw
                endraw_index = i
                while endraw_index < len(lines) and not re.search(r'\{%\s*endraw\s*%\}', lines[endraw_index]):
                    endraw_index += 1
                
                # Include raw content without processing
                raw_content = '\n'.join(lines[i+1:endraw_index])
                output_lines.append(raw_content)
                i = endraw_index + 1
                continue
            
            output_lines.append(line)
            i += 1
        
        return '\n'.join(output_lines)
    
    def _get_nested_value(self, context: Dict[str, Any], path: str) -> Any:
        """Get nested value from context using dot notation"""
        parts = path.split('.')
        value = context
        
        for part in parts:
            part = part.strip()
            if isinstance(value, dict) and part in value:
                value = value[part]
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                # Try to access via getitem if it's a list or similar
                try:
                    if hasattr(value, '__getitem__'):
                        # Try integer index
                        try:
                            index = int(part)
                            value = value[index]
                            continue
                        except (ValueError, IndexError):
                            pass
                except (KeyError, AttributeError, TypeError):
                    raise KeyError(f"Key {part} not found in context")
        
        return value
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a condition expression"""
        # Remove extra whitespace
        condition = condition.strip()
        
        # Check for common operators
        operators = ['==', '!=', '>=', '<=', '>', '<', ' in ', ' not in ']
        
        for op in operators:
            if op in condition:
                left, right = condition.split(op, 1)
                left_val = self._get_nested_value(context, left.strip())
                right_val = self._get_nested_value(context, right.strip())
                
                # Handle different types
                try:
                    # Try to convert to same type for comparison
                    if isinstance(left_val, str) and isinstance(right_val, (int, float)):
                        right_val = str(right_val)
                    elif isinstance(left_val, (int, float)) and isinstance(right_val, str):
                        left_val = str(left_val)
                except (ValueError, TypeError):
                    pass
                
                if op == '==':
                    return left_val == right_val
                elif op == '!=':
                    return left_val != right_val
                elif op == '>=':
                    return left_val >= right_val
                elif op == '<=':
                    return left_val <= right_val
                elif op == '>':
                    return left_val > right_val
                elif op == '<':
                    return left_val < right_val
                elif op == ' in ':
                    return left_val in right_val
                elif op == ' not in ':
                    return left_val not in right_val
        
        # If no operator found, treat as truthy check
        value = self._get_nested_value(context, condition)
        return bool(value)
    
    def _evaluate_expression(self, expression: str, context: Dict[str, Any]) -> Any:
        """Evaluate an expression"""
        expression = expression.strip()
        
        # Handle string literals
        if expression.startswith('"') and expression.endswith('"'):
            return expression[1:-1]
        elif expression.startswith("'") and expression.endswith("'"):
            return expression[1:-1]
        
        # Handle numbers
        try:
            if '.' in expression:
                return float(expression)
            else:
                return int(expression)
        except ValueError:
            pass
        
        # Handle boolean literals
        if expression.lower() == 'true':
            return True
        elif expression.lower() == 'false':
            return False
        elif expression.lower() == 'none' or expression.lower() == 'null':
            return None
        
        # Handle list literals
        if expression.startswith('[') and expression.endswith(']'):
            items = expression[1:-1].split(',')
            return [self._evaluate_expression(item.strip(), context) for item in items]
        
        # Handle dict literals
        if expression.startswith('{') and expression.endswith('}'):
            items = expression[1:-1].split(',')
            result = {}
            for item in items:
                if ':' in item:
                    key, value = item.split(':', 1)
                    result[key.strip()] = self._evaluate_expression(value.strip(), context)
            return result
        
        # Default to variable lookup
        return self._get_nested_value(context, expression)
    
    def _escape_filter(self, value: str) -> str:
        """Escape HTML special characters"""
        if not isinstance(value, str):
            return value
        
        escape_map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '/': '&#x2F;'
        }
        
        for char, escape in escape_map.items():
            value = value.replace(char, escape)
        
        return value
    
    def add_filter(self, name: str, filter_func: Callable):
        """Add a custom filter"""
        self.filters[name] = filter_func

    def add_macro(self, name: str, macro_func: Callable):
        """Add a custom macro"""
        self.macros[name] = macro_func

    def add_custom_tag(self, name: str, tag_func: Callable):
        """Add a custom template tag"""
        self.custom_tags[name] = tag_func

    def register_template_loader(self, loader: Callable):
        """Register a custom template loader"""
        self.loaders.append(loader)

    def add_template_search_path(self, path: Union[str, Path]):
        """Add a template search path"""
        self.template_search_paths.append(Path(path))

    def _default_loader(self, template_name: str) -> str:
        """Default template loader"""
        for search_path in self.template_search_paths:
            template_path = search_path / template_name
            if template_path.exists():
                with open(template_path, 'r', encoding='utf-8') as f:
                    return f.read()
        raise FileNotFoundError(f"Template '{template_name}' not found")

    def _initialize_filters(self) -> Dict[str, Callable]:
        """Initialize built-in filters"""
        filters = {
            # String filters
            'upper': lambda x: x.upper() if isinstance(x, str) else x,
            'lower': lambda x: x.lower() if isinstance(x, str) else x,
            'capitalize': lambda x: x.capitalize() if isinstance(x, str) else x,
            'title': lambda x: x.title() if isinstance(x, str) else x,
            'trim': lambda x: x.strip() if isinstance(x, str) else x,
            'lstrip': lambda x: x.lstrip() if isinstance(x, str) else x,
            'rstrip': lambda x: x.rstrip() if isinstance(x, str) else x,

            # List filters
            'length': lambda x: len(x) if hasattr(x, '__len__') else 0,
            'first': lambda x: x[0] if hasattr(x, '__getitem__') and len(x) > 0 else None,
            'last': lambda x: x[-1] if hasattr(x, '__getitem__') and len(x) > 0 else None,
            'join': lambda x, sep=', ': sep.join(str(i) for i in x) if hasattr(x, '__iter__') else str(x),
            'reverse': lambda x: list(reversed(x)) if hasattr(x, '__iter__') else x,
            'sort': lambda x, reverse=False: sorted(x, reverse=reverse) if hasattr(x, '__iter__') else x,
            'unique': lambda x: list(dict.fromkeys(x)) if hasattr(x, '__iter__') else x,
            'slice': lambda x, start=0, end=None: x[start:end] if hasattr(x, '__getitem__') else x,

            # Default and conditional filters
            'default': lambda x, default='': x if x is not None else default,
            'd': lambda x, default='': x if x is not None else default,  # Alias for default

            # HTML escaping
            'escape': self._escape_filter,
            'e': self._escape_filter,  # Alias for escape
            'safe': lambda x: x,  # Mark as safe, no escaping

            # Number filters
            'abs': lambda x: abs(x) if isinstance(x, (int, float)) else x,
            'round': lambda x, ndigits=0: round(x, ndigits) if isinstance(x, (int, float)) else x,
            'ceil': lambda x: math.ceil(x) if isinstance(x, (int, float)) else x,
            'floor': lambda x: math.floor(x) if isinstance(x, (int, float)) else x,

            # Date/time filters (basic)
            'date': lambda x, fmt='%Y-%m-%d': x.strftime(fmt) if hasattr(x, 'strftime') else str(x),
            'time': lambda x, fmt='%H:%M:%S': x.strftime(fmt) if hasattr(x, 'strftime') else str(x),
            'datetime': lambda x, fmt='%Y-%m-%d %H:%M:%S': x.strftime(fmt) if hasattr(x, 'strftime') else str(x),

            # JSON
            'tojson': lambda x: json.dumps(x, default=str),

            # Formatting
            'format': lambda x, fmt: fmt.format(x) if fmt else str(x),
            'pluralize': lambda x, singular='', plural='s': singular if x == 1 else plural,

            # Utility
            'type': lambda x: type(x).__name__,
            'bool': lambda x: bool(x),
            'int': lambda x: int(x) if x is not None else 0,
            'float': lambda x: float(x) if x is not None else 0.0,
            'str': lambda x: str(x),
        }

        # Add i18n filters if enabled
        if self.enable_i18n:
            filters.update(self._get_i18n_filters())

        return filters

    def _get_i18n_filters(self) -> Dict[str, Callable]:
        """Get internationalization filters"""
        try:
            from pyserv.i18n.translations import gettext, ngettext
            from pyserv.i18n.formatters import format_number, format_currency, format_percent

            return {
                '_': gettext,
                'gettext': gettext,
                'ngettext': ngettext,
                'number': format_number,
                'currency': format_currency,
                'percent': format_percent,
            }
        except ImportError:
            return {}

    def _process_advanced_blocks(self, content: str, context: Dict[str, Any]) -> str:
        """Process advanced template blocks"""
        lines = content.split('\n')
        output_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Process custom tags first
            custom_processed = False
            for tag_name, tag_func in self.custom_tags.items():
                tag_pattern = rf'\{{%\s*{tag_name}\s*(.*?)\s*%\}}'
                if re.match(tag_pattern, line):
                    result = tag_func(context, *re.match(tag_pattern, line).groups())
                    output_lines.append(str(result))
                    custom_processed = True
                    break

            if custom_processed:
                i += 1
                continue

            # Process while loops
            while_match = re.match(self.patterns['while'], line)
            if while_match:
                condition = while_match.group(1)
                endwhile_index = self._find_block_end(lines, i, 'while', 'endwhile')

                loop_content = '\n'.join(lines[i+1:endwhile_index])
                loop_output = []

                max_iterations = 1000  # Prevent infinite loops
                iterations = 0

                while self._evaluate_condition(condition, context) and iterations < max_iterations:
                    rendered_content = self._render_content_sync(loop_content, context.copy(), self.template_dir)
                    loop_output.append(rendered_content)
                    iterations += 1

                    # Check for break/continue
                    if '{% break %}' in rendered_content or '{% continue %}' in rendered_content:
                        break

                output_lines.append('\n'.join(loop_output))
                i = endwhile_index + 1
                continue

            # Process with blocks
            with_match = re.match(self.patterns['with'], line)
            if with_match:
                assignments = with_match.group(1)
                endwith_index = self._find_block_end(lines, i, 'with', 'endwith')

                # Parse assignments like "var1=value1, var2=value2"
                with_context = context.copy()
                for assignment in assignments.split(','):
                    if '=' in assignment:
                        var_name, expr = assignment.split('=', 1)
                        with_context[var_name.strip()] = self._evaluate_expression(expr.strip(), context)

                block_content = '\n'.join(lines[i+1:endwith_index])
                rendered_block = self._render_content_sync(block_content, with_context, self.template_dir)
                output_lines.append(rendered_block)
                i = endwith_index + 1
                continue

            # Process spaceless blocks
            spaceless_match = re.match(self.patterns['spaceless'], line)
            if spaceless_match:
                endspaceless_index = self._find_block_end(lines, i, 'spaceless', 'endspaceless')

                block_content = '\n'.join(lines[i+1:endspaceless_index])
                rendered_block = self._render_content_sync(block_content, context, self.template_dir)

                # Remove whitespace between HTML tags
                rendered_block = re.sub(r'>\s+<', '><', rendered_block)
                output_lines.append(rendered_block)
                i = endspaceless_index + 1
                continue

            # Process autoescape blocks
            autoescape_match = re.match(self.patterns['autoescape'], line)
            if autoescape_match:
                escape_value = autoescape_match.group(1).lower() in ('true', 'on', 'yes')
                endautoescape_index = self._find_block_end(lines, i, 'autoescape', 'endautoescape')

                old_autoescape = self.autoescape
                self.autoescape = escape_value

                block_content = '\n'.join(lines[i+1:endautoescape_index])
                rendered_block = self._render_content_sync(block_content, context, self.template_dir)

                self.autoescape = old_autoescape
                output_lines.append(rendered_block)
                i = endautoescape_index + 1
                continue

            # Process load directives
            load_match = re.match(self.patterns['load'], line)
            if load_match:
                # Load external template libraries/tags
                # This would implement dynamic loading
                i += 1
                continue

            output_lines.append(line)
            i += 1

        return '\n'.join(output_lines)

    def _find_block_end(self, lines: List[str], start_index: int, block_type: str, end_type: str) -> int:
        """Find the end of a block"""
        depth = 1
        i = start_index + 1

        while i < len(lines) and depth > 0:
            line = lines[i]

            if re.search(rf'\{{%\s*{block_type}\s*%}}', line):
                depth += 1
            elif re.search(rf'\{{%\s*{end_type}\s*%}}', line):
                depth -= 1
                if depth == 0:
                    return i

            i += 1

        return len(lines) - 1  # Fallback

    def _process_enhanced_for_loops(self, content: str, context: Dict[str, Any]) -> str:
        """Process enhanced for loops with filtering and unpacking"""
        def process_for_loop(match):
            full_match = match.group(0)
            loop_vars = match.group(1)
            iterable_expr = match.group(2)
            filter_expr = match.group(3)

            # Parse loop variables (support unpacking)
            if ',' in loop_vars:
                var_names = [v.strip() for v in loop_vars.split(',')]
            else:
                var_names = [loop_vars.strip()]

            # Get iterable
            iterable = self._evaluate_expression(iterable_expr, context)

            # Apply filter if present
            if filter_expr:
                iterable = [item for item in iterable if self._evaluate_condition(filter_expr, {'item': item, **context})]

            # Process loop
            loop_output = []
            for index, item in enumerate(iterable):
                loop_context = context.copy()

                # Handle unpacking
                if len(var_names) > 1 and hasattr(item, '__iter__'):
                    for i, var_name in enumerate(var_names):
                        if i < len(item):
                            loop_context[var_name] = item[i]
                        else:
                            loop_context[var_name] = None
                else:
                    loop_context[var_names[0]] = item

                # Add loop variables
                loop_context['loop'] = {
                    'index': index + 1,
                    'index0': index,
                    'first': index == 0,
                    'last': index == len(iterable) - 1,
                    'length': len(iterable),
                    'previtem': iterable[index - 1] if index > 0 else None,
                    'nextitem': iterable[index + 1] if index < len(iterable) - 1 else None,
                }

                # Find loop content (this is a simplified version)
                # In practice, this would need more sophisticated parsing
                loop_output.append(f"<!-- Loop item {index} -->")

            return '\n'.join(loop_output)

        return re.sub(self.patterns['for'], process_for_loop, content)

    def _process_enhanced_conditionals(self, content: str, context: Dict[str, Any]) -> str:
        """Process enhanced if/elif/else conditionals"""
        # This is a simplified implementation
        # A full implementation would need proper AST parsing

        lines = content.split('\n')
        output_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]

            if_match = re.match(self.patterns['if'], line)
            if if_match:
                condition = if_match.group(1)
                endif_index = self._find_block_end(lines, i, 'if', 'endif')

                # Collect all branches
                branches = []
                current_index = i

                # IF branch
                if self._evaluate_condition(condition, context):
                    block_content = '\n'.join(lines[i+1:endif_index])
                    rendered_block = self._render_content_sync(block_content, context, self.template_dir)
                    output_lines.append(rendered_block)
                    i = endif_index + 1
                    continue

                # Check for ELIF branches
                current_index = i + 1
                while current_index < endif_index:
                    elif_match = re.match(self.patterns['elif'], lines[current_index])
                    if elif_match:
                        elif_condition = elif_match.group(1)
                        elif_end_index = self._find_block_end(lines, current_index, 'elif', 'endif')

                        if self._evaluate_condition(elif_condition, context):
                            block_content = '\n'.join(lines[current_index+1:elif_end_index])
                            rendered_block = self._render_content_sync(block_content, context, self.template_dir)
                            output_lines.append(rendered_block)
                            i = endif_index + 1
                            break

                        current_index = elif_end_index
                    else:
                        break

                # Check for ELSE branch
                else_match = re.match(self.patterns['else'], lines[current_index])
                if else_match and not output_lines:
                    block_content = '\n'.join(lines[current_index+1:endif_index])
                    rendered_block = self._render_content_sync(block_content, context, self.template_dir)
                    output_lines.append(rendered_block)

                i = endif_index + 1
                continue

            output_lines.append(line)
            i += 1

        return '\n'.join(output_lines)

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return self.render_stats.copy()

    def enable_debugging(self, enable: bool = True):
        """Enable or disable debug mode"""
        self.debug = enable

    def clear_cache(self):
        """Clear all caches"""
        self.cache.clear()
        self.macro_cache.clear()
        self.filter_cache.clear()

    def preload_templates(self, template_names: List[str]):
        """Preload templates into cache"""
        for template_name in template_names:
            try:
                template_path = self.template_dir / template_name
                if template_path.exists():
                    with open(template_path, 'r', encoding='utf-8') as f:
                        self.cache[template_path] = f.read()
            except Exception as e:
                if self.debug:
                    print(f"Failed to preload template {template_name}: {e}")

    def validate_template(self, template_content: str) -> List[str]:
        """Validate template syntax and return errors"""
        errors = []

        # Check for unmatched blocks
        block_stack = []
        lines = template_content.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Check for block starts
            for block_type in ['if', 'for', 'macro', 'raw', 'with', 'spaceless', 'autoescape']:
                if re.search(rf'\{{%\s*{block_type}\s', line):
                    block_stack.append((block_type, line_num))

            # Check for block ends
            for block_type in ['endif', 'endfor', 'endmacro', 'endraw', 'endwith', 'endspaceless', 'endautoescape']:
                if re.search(rf'\{{%\s*{block_type}\s*%}}', line):
                    if not block_stack:
                        errors.append(f"Unmatched {block_type} at line {line_num}")
                    else:
                        start_type, start_line = block_stack.pop()
                        expected_end = f"end{start_type}"
                        if expected_end != block_type:
                            errors.append(f"Mismatched block: {start_type} at line {start_line} closed by {block_type} at line {line_num}")

        # Check for remaining unclosed blocks
        for block_type, line_num in block_stack:
            errors.append(f"Unclosed {block_type} block starting at line {line_num}")

        return errors
