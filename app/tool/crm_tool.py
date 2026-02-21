from typing import Any, Dict, Optional
from pydantic import Field
from app.tool.base import BaseTool, ToolResult

class CRMTool(BaseTool):
    """
    A mock CRM tool for the Sales Agent (Chapter 43).
    Simulates adding leads and sending emails.
    """
    name: str = "crm_tool"
    description: str = "Manage leads and communications in the CRM."
    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add_lead", "send_email", "list_leads"],
                "description": "The CRM action to perform.",
            },
            "lead_data": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "company": {"type": "string"},
                    "status": {"type": "string"}
                },
                "description": "Data for the new lead.",
            },
            "email_data": {
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"}
                },
                "description": "Data for the email.",
            }
        },
        "required": ["action"],
    }

    # In-memory storage for the mock
    leads: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    async def execute(self, action: str, lead_data: Optional[Dict[str, Any]] = None, email_data: Optional[Dict[str, Any]] = None, **kwargs) -> ToolResult:
        if action == "add_lead":
            if not lead_data:
                return ToolResult(error="lead_data is required for add_lead")
            email = lead_data.get("email")
            if not email:
                 return ToolResult(error="Lead must have an email")

            self.leads[email] = lead_data
            return ToolResult(output=f"Lead {lead_data.get('name')} ({email}) added successfully.")

        elif action == "send_email":
            if not email_data:
                return ToolResult(error="email_data is required for send_email")
            to = email_data.get("to")
            if to not in self.leads:
                return ToolResult(error=f"Recipient {to} not found in CRM leads.")

            # Simulate sending
            return ToolResult(output=f"Email sent to {to} with subject '{email_data.get('subject')}'.")

        elif action == "list_leads":
            return ToolResult(output=str(list(self.leads.values())))

        else:
            return ToolResult(error=f"Unknown action: {action}")
