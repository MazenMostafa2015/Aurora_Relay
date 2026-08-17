from fastapi import APIRouter, Depends

from ..dependencies import get_app_state, get_current_user
from ..models import ToolListResponse, ToolResponse
from ...database.models import User

router = APIRouter(prefix="/tools", tags=["Tools"])

@router.get("", response_model=ToolListResponse)
async def list_tools(_: User = Depends(get_current_user), state: dict = Depends(get_app_state)):
    registry = getattr(state.get("mcp_client"), "tool_registry", {}) or {}
    tools = []
    for name, info in registry.items():
        data = info if isinstance(info, dict) else getattr(info, "__dict__", {})
        tools.append(ToolResponse(name=name, description=data.get("description", ""), server=data.get("server", "unknown"), schema=data.get("schema", {})))
    return ToolListResponse(tools=tools, count=len(tools))

@router.get("/servers")
async def list_servers(_: User = Depends(get_current_user), state: dict = Depends(get_app_state)):
    client = state.get("mcp_client")
    connections = getattr(client, "connections", {}) if client else {}
    return {"servers": list(connections.keys()), "connected": len(connections)}
