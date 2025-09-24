"""
MCP (Model Context Protocol) Integration Module for NeuralForge

Provides integration with MCP servers for resource access and tool execution.
"""

from typing import Dict, List, Optional, Any, Callable
import logging

from .llm_engine import LLMEngine
from .agent_system import NeuralAgent

logger = logging.getLogger(__name__)


class MCPServer:
    """
    MCP Server for handling resource access and tool execution requests from agents
    """

    def __init__(self, llm_engine: LLMEngine):
        self.llm_engine = llm_engine
        self.resources: Dict[str, Any] = {}
        self.tools: Dict[str, Callable] = {}
        self.resource_permissions: Dict[str, List[str]] = {}  # resource -> list of allowed agent_ids
        self.tool_permissions: Dict[str, List[str]] = {}  # tool -> list of allowed agent_ids

    def register_resource(self, name: str, resource: Any, allowed_agents: List[str] = None):
        """
        Register a resource that agents can access

        Args:
            name: Resource name
            resource: Resource object
            allowed_agents: List of agent IDs allowed to access this resource (None for public)
        """
        self.resources[name] = resource
        if allowed_agents:
            self.resource_permissions[name] = allowed_agents
        logger.info(f"Registered MCP resource: {name}")

    def register_tool(self, name: str, tool_func: Callable, allowed_agents: List[str] = None):
        """
        Register a tool that agents can use

        Args:
            name: Tool name
            tool_func: Tool function
            allowed_agents: List of agent IDs allowed to use this tool (None for public)
        """
        self.tools[name] = tool_func
        if allowed_agents:
            self.tool_permissions[name] = allowed_agents
        logger.info(f"Registered MCP tool: {name}")

    def unregister_resource(self, name: str):
        """
        Unregister a resource

        Args:
            name: Resource name to unregister
        """
        if name in self.resources:
            del self.resources[name]
            if name in self.resource_permissions:
                del self.resource_permissions[name]
            logger.info(f"Unregistered MCP resource: {name}")

    def unregister_tool(self, name: str):
        """
        Unregister a tool

        Args:
            name: Tool name to unregister
        """
        if name in self.tools:
            del self.tools[name]
            if name in self.tool_permissions:
                del self.tool_permissions[name]
            logger.info(f"Unregistered MCP tool: {name}")

    async def process_mcp_request(self, agent: NeuralAgent, request: Dict) -> Dict:
        """
        Process MCP request from an agent

        Args:
            agent: Agent making the request
            request: Request dictionary

        Returns:
            Response dictionary
        """
        request_type = request.get("type")

        if request_type == "resource_access":
            return await self._handle_resource_access(agent, request)
        elif request_type == "tool_execution":
            return await self._handle_tool_execution(agent, request)
        elif request_type == "list_resources":
            return self._handle_list_resources(agent)
        elif request_type == "list_tools":
            return self._handle_list_tools(agent)
        else:
            return {"error": f"Unknown request type: {request_type}"}

    async def _handle_resource_access(self, agent: NeuralAgent, request: Dict) -> Dict:
        """
        Handle resource access requests

        Args:
            agent: Agent making the request
            request: Resource access request

        Returns:
            Response dictionary
        """
        resource_name = request.get("resource")
        action = request.get("action", "read")
        parameters = request.get("parameters", {})

        # Check permissions
        if not self._check_resource_permission(agent.agent_id, resource_name):
            return {"error": f"Access denied to resource '{resource_name}'"}

        if resource_name not in self.resources:
            return {"error": f"Resource '{resource_name}' not found"}

        try:
            resource = self.resources[resource_name]

            # Log access for audit
            logger.info(f"Agent {agent.agent_id} accessing {resource_name} with action {action}")

            # Handle different actions
            if action == "read":
                result = await self._read_resource(resource, parameters)
            elif action == "write":
                result = await self._write_resource(resource, parameters)
            elif action == "delete":
                result = await self._delete_resource(resource, parameters)
            else:
                return {"error": f"Unsupported action: {action}"}

            # Calculate cost
            cost = self._calculate_resource_cost(resource_name, action)

            return {
                "success": True,
                "data": result,
                "cost": cost,
                "resource": resource_name,
                "action": action
            }

        except Exception as e:
            logger.error(f"Resource access error: {str(e)}")
            return {"error": f"Resource access failed: {str(e)}"}

    async def _handle_tool_execution(self, agent: NeuralAgent, request: Dict) -> Dict:
        """
        Handle tool execution requests

        Args:
            agent: Agent making the request
            request: Tool execution request

        Returns:
            Response dictionary
        """
        tool_name = request.get("tool")
        params = request.get("parameters", {})

        # Check permissions
        if not self._check_tool_permission(agent.agent_id, tool_name):
            return {"error": f"Access denied to tool '{tool_name}'"}

        if tool_name not in self.tools:
            return {"error": f"Tool '{tool_name}' not found"}

        try:
            # Execute tool
            result = await self.tools[tool_name](agent, params)

            # Calculate cost
            cost = self._calculate_tool_cost(tool_name, params)

            logger.info(f"Agent {agent.agent_id} executed tool {tool_name}")

            return {
                "success": True,
                "result": result,
                "cost": cost,
                "tool": tool_name
            }

        except Exception as e:
            logger.error(f"Tool execution error: {str(e)}")
            return {"error": f"Tool execution failed: {str(e)}"}

    def _handle_list_resources(self, agent: NeuralAgent) -> Dict:
        """
        Handle list resources request

        Args:
            agent: Agent making the request

        Returns:
            Response dictionary with available resources
        """
        available_resources = []
        for resource_name in self.resources.keys():
            if self._check_resource_permission(agent.agent_id, resource_name):
                available_resources.append({
                    "name": resource_name,
                    "type": type(self.resources[resource_name]).__name__
                })

        return {
            "success": True,
            "resources": available_resources
        }

    def _handle_list_tools(self, agent: NeuralAgent) -> Dict:
        """
        Handle list tools request

        Args:
            agent: Agent making the request

        Returns:
            Response dictionary with available tools
        """
        available_tools = []
        for tool_name in self.tools.keys():
            if self._check_tool_permission(agent.agent_id, tool_name):
                available_tools.append({
                    "name": tool_name,
                    "description": getattr(self.tools[tool_name], '__doc__', 'No description')
                })

        return {
            "success": True,
            "tools": available_tools
        }

    def _check_resource_permission(self, agent_id: str, resource_name: str) -> bool:
        """
        Check if agent has permission to access a resource

        Args:
            agent_id: Agent ID
            resource_name: Resource name

        Returns:
            True if access is allowed
        """
        if resource_name not in self.resource_permissions:
            return True  # Public resource
        return agent_id in self.resource_permissions[resource_name]

    def _check_tool_permission(self, agent_id: str, tool_name: str) -> bool:
        """
        Check if agent has permission to use a tool

        Args:
            agent_id: Agent ID
            tool_name: Tool name

        Returns:
            True if access is allowed
        """
        if tool_name not in self.tool_permissions:
            return True  # Public tool
        return agent_id in self.tool_permissions[tool_name]

    async def _read_resource(self, resource: Any, parameters: Dict) -> Any:
        """
        Read from a resource

        Args:
            resource: Resource object
            parameters: Read parameters

        Returns:
            Read result
        """
        if hasattr(resource, 'read'):
            return await resource.read(**parameters)
        elif hasattr(resource, '__getitem__'):
            key = parameters.get('key')
            return resource[key] if key else resource
        else:
            return str(resource)

    async def _write_resource(self, resource: Any, parameters: Dict) -> Any:
        """
        Write to a resource

        Args:
            resource: Resource object
            parameters: Write parameters

        Returns:
            Write result
        """
        if hasattr(resource, 'write'):
            return await resource.write(**parameters)
        elif hasattr(resource, '__setitem__'):
            key = parameters.get('key')
            value = parameters.get('value')
            if key and value is not None:
                resource[key] = value
                return True
        return False

    async def _delete_resource(self, resource: Any, parameters: Dict) -> Any:
        """
        Delete from a resource

        Args:
            resource: Resource object
            parameters: Delete parameters

        Returns:
            Delete result
        """
        if hasattr(resource, 'delete'):
            return await resource.delete(**parameters)
        elif hasattr(resource, '__delitem__'):
            key = parameters.get('key')
            if key:
                del resource[key]
                return True
        return False

    def _calculate_resource_cost(self, resource_name: str, action: str) -> float:
        """
        Calculate cost for resource access

        Args:
            resource_name: Resource name
            action: Action performed

        Returns:
            Cost in tokens
        """
        base_costs = {
            "read": 1.0,
            "write": 2.0,
            "delete": 1.5
        }
        return base_costs.get(action, 1.0)

    def _calculate_tool_cost(self, tool_name: str, params: Dict) -> float:
        """
        Calculate cost for tool execution

        Args:
            tool_name: Tool name
            params: Tool parameters

        Returns:
            Cost in tokens
        """
        # Base cost plus parameter complexity
        base_cost = 5.0
        param_cost = len(str(params)) * 0.01
        return base_cost + param_cost

    def get_stats(self) -> Dict:
        """
        Get MCP server statistics

        Returns:
            Statistics dictionary
        """
        return {
            "resources_count": len(self.resources),
            "tools_count": len(self.tools),
            "resource_permissions": len(self.resource_permissions),
            "tool_permissions": len(self.tool_permissions)
        }




