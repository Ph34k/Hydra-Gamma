import pytest
from app.agent.data_analysis import DataAnalysis

class TestDataAnalysis:
    @pytest.mark.asyncio
    async def test_initialization(self):
        agent = DataAnalysis()
        assert agent.name == "Data_Analysis"
        assert agent.description == "An analytical agent that utilizes python and data visualization tools to solve diverse data analysis tasks"
        assert agent.max_observe == 15000
        assert agent.max_steps == 20

    @pytest.mark.asyncio
    async def test_available_tools(self):
        agent = DataAnalysis()
        tools = agent.available_tools.tool_map

        # Check that specific tools are present
        assert "python_execute" in tools  # NormalPythonExecute
        assert "visualization_preparation" in tools # VisualizationPrepare
        assert "data_visualization" in tools # DataVisualization
        assert "terminate" in tools # Terminate

    @pytest.mark.asyncio
    async def test_system_prompt(self):
        agent = DataAnalysis()
        assert agent.system_prompt is not None
        assert "workspace" in agent.system_prompt or "/app" in agent.system_prompt # Depending on config.workspace_root
