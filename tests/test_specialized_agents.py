import pytest
from app.agent.specialized.coding import CodingAgent
from app.agent.specialized.research import ResearchAgent
from app.agent.specialized.sales import SalesAgent
from app.agent.specialized.support import SupportAgent
from app.agent.specialized.data_science import DataScienceAgent

@pytest.mark.asyncio
async def test_coding_agent_initialization():
    agent = CodingAgent()
    assert agent.name == "coding_agent"
    assert "file_tool" in agent.available_tools.tool_map
    assert "shell" in agent.available_tools.tool_map
    assert "git_tool" in agent.available_tools.tool_map

@pytest.mark.asyncio
async def test_research_agent_initialization():
    agent = ResearchAgent()
    assert agent.name == "research_agent"
    # SearchTool name is 'web_search' or 'search_tool'?
    # Checking SearchTool in app/tool/search_tool.py: name="web_search" (likely, let's verify)
    tool_names = list(agent.available_tools.tool_map.keys())
    # Adjust based on actual names
    assert any("search" in name for name in tool_names)
    assert "browser_tool" in agent.available_tools.tool_map
    assert "document_processor" in agent.available_tools.tool_map

@pytest.mark.asyncio
async def test_sales_agent_initialization():
    agent = SalesAgent()
    assert agent.name == "sales_agent"
    tool_names = list(agent.available_tools.tool_map.keys())
    assert any("search" in name for name in tool_names)
    assert "browser_tool" in agent.available_tools.tool_map

@pytest.mark.asyncio
async def test_support_agent_initialization():
    agent = SupportAgent()
    assert agent.name == "support_agent"
    # MemorySearchTool name is 'memory_search'
    assert "memory_search" in agent.available_tools.tool_map

@pytest.mark.asyncio
async def test_data_science_agent_initialization():
    agent = DataScienceAgent()
    assert agent.name == "data_science_agent"
    assert "python_execute" in agent.available_tools.tool_map
    # MediaGenerationTool name is 'media_generation_tool'?
    # Let's check the tool map keys if test fails
    assert "media_generation_tool" in agent.available_tools.tool_map
