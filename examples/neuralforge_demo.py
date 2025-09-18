"""
NeuralForge Framework Demo

This example demonstrates how to use the NeuralForge framework with multiple agents,
LLM integration, agent communication, and the sandbox economy system.
"""

import asyncio
import logging
import os
from src.pydance.neuralforge import (
    NeuralForge, NeuralAgent, AgentCapability,
    LLMConfig, LLMProvider
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """
    Main demo function showcasing NeuralForge capabilities
    """
    print("🚀 Starting NeuralForge Framework Demo")
    print("=" * 50)

    # Initialize the framework
    framework = NeuralForge()

    # Create LLM configuration (replace with your actual API key)
    llm_config = LLMConfig(
        provider=LLMProvider.OPENAI,
        model="gpt-3.5-turbo",
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here")  # Set your API key
    )

    # Create specialized agents
    print("\n🤖 Creating Agents...")

    # Research Agent
    research_agent = NeuralAgent(
        agent_id="research_agent_1",
        name="Research Specialist",
        description="Expert in research, analysis, and information synthesis",
        llm_engine=framework.llm_engine,
        capabilities=[
            AgentCapability("research", "Conduct research on various topics", 2.0),
            AgentCapability("analysis", "Analyze and synthesize information", 1.5),
            AgentCapability("web_search", "Search and gather web information", 1.0)
        ],
        initial_balance=150.0
    )

    # Coding Agent
    coding_agent = NeuralAgent(
        agent_id="coding_agent_1",
        name="Code Specialist",
        description="Expert in programming, code generation, and debugging",
        llm_engine=framework.llm_engine,
        capabilities=[
            AgentCapability("coding", "Write and debug code", 3.0),
            AgentCapability("documentation", "Create technical documentation", 1.0),
            AgentCapability("code_review", "Review and improve code quality", 2.0)
        ],
        initial_balance=150.0
    )

    # Project Management Agent
    pm_agent = NeuralAgent(
        agent_id="pm_agent_1",
        name="Project Manager",
        description="Expert in project planning, coordination, and task management",
        llm_engine=framework.llm_engine,
        capabilities=[
            AgentCapability("planning", "Create project plans and timelines", 1.5),
            AgentCapability("coordination", "Coordinate between team members", 1.0),
            AgentCapability("reporting", "Generate progress reports", 1.0)
        ],
        initial_balance=150.0
    )

    # Register agents with the framework
    framework.register_agent(research_agent)
    framework.register_agent(coding_agent)
    framework.register_agent(pm_agent)

    print(f"✅ Registered {len(framework.agents)} agents")

    # Demo 1: Individual Agent Task Processing
    print("\n📋 Demo 1: Individual Agent Tasks")
    print("-" * 30)

    try:
        # Research task
        research_result = await framework.process_agent_task(
            "research_agent_1",
            "Research the current trends in AI safety and summarize the key challenges"
        )
        print(f"🔍 Research Result: {research_result['response'][:200]}...")
        print(f"💰 Cost: ${research_result['cost']:.2f}")

        # Coding task
        coding_result = await framework.process_agent_task(
            "coding_agent_1",
            "Write a Python function to implement a simple neural network layer"
        )
        print(f"💻 Coding Result: {coding_result['response'][:200]}...")
        print(f"💰 Cost: ${coding_result['cost']:.2f}")

    except Exception as e:
        print(f"❌ Error in individual tasks: {e}")

    # Demo 2: Agent-to-Agent Communication
    print("\n💬 Demo 2: Agent Communication")
    print("-" * 30)

    try:
        # Send message from research to coding agent
        success = await framework.send_agent_message(
            "research_agent_1",
            "coding_agent_1",
            "I found some interesting research about neural networks. Can you help implement a simple example?",
            {"research_topic": "neural networks"}
        )

        if success:
            print("✅ Message sent successfully")

            # Receive messages for coding agent
            messages = await framework.communicator.receive_messages("coding_agent_1", timeout=2.0)
            print(f"📨 Coding agent received {len(messages)} messages")

            for msg in messages:
                print(f"   From: {msg['from_agent']}, Message: {msg['message'][:100]}...")
        else:
            print("❌ Failed to send message")

    except Exception as e:
        print(f"❌ Error in communication demo: {e}")

    # Demo 3: Multi-Agent Orchestration
    print("\n🎯 Demo 3: Multi-Agent Orchestration")
    print("-" * 30)

    try:
        orchestration_result = await framework.orchestrate_agents(
            "Create a comprehensive plan for developing an AI-powered task management system including technical architecture, user experience design, and implementation strategy",
            ["research", "coding", "planning", "analysis"],
            budget=100.0
        )

        if "error" not in orchestration_result:
            print("✅ Orchestration completed successfully")
            print(f"📊 Participating agents: {orchestration_result['participating_agents']}")
            print(f"💰 Total cost: ${orchestration_result['total_cost']:.2f}")
            print(f"📝 Combined result preview: {orchestration_result['combined_result'][:300]}...")
        else:
            print(f"❌ Orchestration failed: {orchestration_result['error']}")

    except Exception as e:
        print(f"❌ Error in orchestration demo: {e}")

    # Demo 4: MCP Integration
    print("\n🔧 Demo 4: MCP Integration")
    print("-" * 30)

    try:
        # Register some sample resources and tools
        sample_data = {"projects": ["AI Safety", "Neural Networks", "Task Management"]}

        framework.mcp_server.register_resource(
            "project_database",
            sample_data,
            allowed_agents=["research_agent_1", "pm_agent_1"]
        )

        # Sample tool function
        async def analyze_project_data(agent, params):
            return f"Analysis of {len(sample_data['projects'])} projects completed"

        framework.mcp_server.register_tool(
            "project_analyzer",
            analyze_project_data,
            allowed_agents=["research_agent_1", "pm_agent_1"]
        )

        # Test resource access
        resource_request = {
            "type": "resource_access",
            "resource": "project_database",
            "action": "read"
        }

        mcp_result = await framework.process_mcp_request("research_agent_1", resource_request)
        if mcp_result.get("success"):
            print("✅ MCP resource access successful")
            print(f"📊 Data retrieved: {mcp_result['data']}")
        else:
            print(f"❌ MCP resource access failed: {mcp_result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"❌ Error in MCP demo: {e}")

    # Demo 5: Economy System
    print("\n💰 Demo 5: Economy System")
    print("-" * 30)

    try:
        # Check agent balances
        for agent_id in framework.agents.keys():
            balance = framework.economy.get_balance(agent_id)
            print(f"🤖 {agent_id}: ${balance:.2f}")

        # Get system stats
        system_stats = framework.economy.get_system_stats()
        print("📈 System Economy Stats:")
        print(f"   Total agents: {system_stats['total_agents']}")
        print(f"   Total balance in system: ${system_stats['total_balance_in_system']:.2f}")
        print(f"   Total transactions: {system_stats['total_transactions']}")

        # Show recent transactions
        transactions = framework.economy.get_transaction_history(limit=5)
        print(f"   Recent transactions: {len(transactions)}")

    except Exception as e:
        print(f"❌ Error in economy demo: {e}")

    # Demo 6: Framework Status
    print("\n📊 Demo 6: Framework Status")
    print("-" * 30)

    try:
        status = framework.get_system_status()
        print("🏗️  Framework Status:")
        print(f"   Status: {status['framework_status']}")
        print(f"   Total agents: {status['total_agents']}")
        print(f"   Active tasks: {status['active_agent_tasks']}")
        print(f"   Queued tasks: {status['queued_tasks']}")

        # Individual agent statuses
        for agent_id in framework.agents.keys():
            agent_status = framework.get_agent_status(agent_id)
            if agent_status:
                print(f"🤖 {agent_status['name']}: {agent_status['state']}, Balance: ${agent_status['balance']:.2f}")

    except Exception as e:
        print(f"❌ Error getting framework status: {e}")

    # Cleanup
    print("\n🧹 Cleaning up...")
    await framework.stop()

    print("\n🎉 NeuralForge Demo completed successfully!")
    print("=" * 50)


async def simple_example():
    """
    Simple example showing basic NeuralForge usage
    """
    print("🚀 Simple NeuralForge Example")
    print("=" * 30)

    # Initialize framework
    framework = NeuralForge()

    # Create a basic agent
    basic_agent = NeuralAgent(
        agent_id="basic_agent",
        name="Basic Assistant",
        description="A helpful AI assistant",
        llm_engine=framework.llm_engine,
        capabilities=[
            AgentCapability("general", "General assistance and conversation", 1.0)
        ]
    )

    # Register agent
    framework.register_agent(basic_agent)

    # Process a simple task
    try:
        result = await framework.process_agent_task(
            "basic_agent",
            "Hello! Can you tell me what NeuralForge is?"
        )
        print(f"🤖 Agent Response: {result['response']}")
        print(f"💰 Cost: ${result['cost']:.2f}")

    except Exception as e:
        print(f"❌ Error: {e}")

    # Cleanup
    await framework.stop()


if __name__ == "__main__":
    print("Choose demo:")
    print("1. Full NeuralForge Demo")
    print("2. Simple Example")

    choice = input("Enter choice (1 or 2): ").strip()

    if choice == "2":
        asyncio.run(simple_example())
    else:
        asyncio.run(main())
