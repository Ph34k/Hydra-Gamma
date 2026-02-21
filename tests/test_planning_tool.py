import pytest
from app.tool.planning import PlanningTool
from app.exceptions import ToolError

class TestPlanningTool:
    @pytest.fixture
    def tool(self):
        return PlanningTool()

    @pytest.mark.asyncio
    async def test_create_plan_success(self, tool):
        result = await tool.execute(
            command="create",
            plan_id="plan1",
            title="My Plan",
            steps=["Step 1", "Step 2"]
        )
        assert "Plan created successfully" in result.output
        assert "plan1" in tool.plans
        assert tool.plans["plan1"]["title"] == "My Plan"
        assert len(tool.plans["plan1"]["steps"]) == 2
        assert tool._current_plan_id == "plan1"

    @pytest.mark.asyncio
    async def test_create_plan_invalid_steps(self, tool):
        with pytest.raises(ToolError):
            await tool.execute(
                command="create",
                plan_id="plan1",
                steps="not a list"
            )

    @pytest.mark.asyncio
    async def test_get_plan(self, tool):
        await tool.execute(command="create", plan_id="plan1", steps=["step1"])
        result = await tool.execute(command="get", plan_id="plan1")
        assert "Plan: Plan (ID: plan1)" in result.output

        # Test default to active plan
        result_default = await tool.execute(command="get")
        assert "Plan: Plan (ID: plan1)" in result_default.output

    @pytest.mark.asyncio
    async def test_get_nonexistent_plan(self, tool):
        with pytest.raises(ToolError):
            await tool.execute(command="get", plan_id="fake_plan")

    @pytest.mark.asyncio
    async def test_update_plan(self, tool):
        await tool.execute(command="create", plan_id="plan1", steps=["step1"])

        result = await tool.execute(
            command="update",
            plan_id="plan1",
            title="Updated Title",
            steps=["step1", "step2"]
        )
        assert "Plan updated successfully" in result.output
        assert tool.plans["plan1"]["title"] == "Updated Title"
        assert len(tool.plans["plan1"]["steps"]) == 2

    @pytest.mark.asyncio
    async def test_mark_step(self, tool):
        await tool.execute(command="create", plan_id="plan1", steps=["step1", "step2"])

        result = await tool.execute(
            command="mark_step",
            plan_id="plan1",
            step_index=0,
            step_status="completed",
            step_notes="Done"
        )
        assert "Step 0 updated" in result.output
        assert tool.plans["plan1"]["step_statuses"][0] == "completed"
        assert tool.plans["plan1"]["step_notes"][0] == "Done"

    @pytest.mark.asyncio
    async def test_mark_step_invalid_index(self, tool):
        await tool.execute(command="create", plan_id="plan1", steps=["step1"])
        with pytest.raises(ToolError):
            await tool.execute(command="mark_step", plan_id="plan1", step_index=5)

    @pytest.mark.asyncio
    async def test_delete_plan(self, tool):
        await tool.execute(command="create", plan_id="plan1", steps=["step1"])

        result = await tool.execute(command="delete", plan_id="plan1")
        assert "deleted" in result.output
        assert "plan1" not in tool.plans
        assert tool._current_plan_id is None

    @pytest.mark.asyncio
    async def test_list_plans(self, tool):
        await tool.execute(command="create", plan_id="plan1", steps=["s1"])
        await tool.execute(command="create", plan_id="plan2", steps=["s2"])

        result = await tool.execute(command="list")
        assert "plan1" in result.output
        assert "plan2" in result.output

    @pytest.mark.asyncio
    async def test_set_active_plan(self, tool):
        await tool.execute(command="create", plan_id="plan1", steps=["s1"])
        await tool.execute(command="create", plan_id="plan2", steps=["s2"])

        # plan2 is active by default after creation
        assert tool._current_plan_id == "plan2"

        await tool.execute(command="set_active", plan_id="plan1")
        assert tool._current_plan_id == "plan1"
