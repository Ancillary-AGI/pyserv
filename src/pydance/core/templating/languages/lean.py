import re
from typing import Callable, Dict, Any
from pathlib import Path

from ..engine import AbstractTemplateEngine

class LeanTemplateEngine(AbstractTemplateEngine):
    """Lightweight template engine with simple syntax"""
    
    def __init__(self, template_dir: Path, **options):
        super().__init__(template_dir, **options)
        self.cache = {}
        self.patterns = {
            'variable': r'\{\{([^}]+)\}\}',
            'block': r'\{%\s*(\w+)\s+(.*?)\s*%\}',
            'endblock': r'\{%\s*end(\w+)\s*%\}',
            'comment': r'\{\#.*?\#\}',
            'include': r'\{%\s*include\s+["\'](.*?)["\']\s*%\}',
            'extends': r'\{%\s*extends\s+["\'](.*?)["\']\s*%\}',
            'block_definition': r'\{%\s*block\s+(\w+)\s*%\}',
            'macro': r'\{%\s*macro\s+(\w+)\((.*?)\)\s*%\}',
            'endmacro': r'\{%\s*endmacro\s*%\}',
            'call': r'\{%\s*call\s+(\w+)\((.*?)\)\s*%\}',
            'filter': r'\{\{\s*(.*?)\s*\|\s*(\w+)(?::(.*?))?\s*\}\}'
        }
        
        # Enable caching by default
        self.enable_cache = options.get('enable_cache', True)
        self.autoescape = options.get('autoescape', True)
        
        # Built-in filters
        self.filters = {
            'upper': lambda x: x.upper() if isinstance(x, str) else x,
            'lower': lambda x: x.lower() if isinstance(x, str) else x,
            'capitalize': lambda x: x.capitalize() if isinstance(x, str) else x,
            'title': lambda x: x.title() if isinstance(x, str) else x,
            'length': lambda x: len(x) if hasattr(x, '__len__') else 0,
            'default': lambda x, default='': x if x is not None else default,
            'trim': lambda x: x.strip() if isinstance(x, str) else x,
            'escape': self._escape_filter,
            'safe': lambda x: x,  # Mark as safe, no escaping
            'join': lambda x, separator=', ': separator.join(str(i) for i in x) if hasattr(x, '__iter__') else x,
            'first': lambda x: x[0] if hasattr(x, '__getitem__') and len(x) > 0 else None,
            'last': lambda x: x[-1] if hasattr(x, '__getitem__') and len(x) > 0 else None,
        }
        
        # Macro storage
        self.macros = {}
    
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
    
    def clear_cache(self):
        """Clear the template cache"""
        self.cache.clear()
