"""Road Trip Planner agent"""

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams
from google.adk.tools import google_search

from . import prompt


MODEL = "gemini-2.5-pro"

mcp_tools = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="http://127.0.0.1:8080/mcp",
    )
)

roadtrip_planner = LlmAgent(
    name="roadtrip_planner",
    model=MODEL,
    description=(
        "Plan your next roadtrip!"
    ),
    instruction=prompt.ROADTRIP_PLANNER_ROOT,
    tools=[mcp_tools, google_search]
)

root_agent = roadtrip_planner
