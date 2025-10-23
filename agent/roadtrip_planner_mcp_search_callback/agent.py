"""Road Trip Planner agent"""

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import google_search

from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams

from . import prompt


MODEL = "gemini-2.5-pro"

mcp_tools = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="http://127.0.0.1:8080/mcp",
    )
)

search_agent = Agent(
    model=MODEL,
    name='SearchAgent',
    instruction="You are a specialist in Google Search",
    tools=[google_search]
)


# callback to capture map data
def after_tool_callback(tool, args, tool_response, tool_context):
    """Callback that will run after any tool executes"""
    if isinstance(tool_response, dict):
        if 'encoded_polyline' in tool_response and 'ordered_waypoints' in tool_response:
            # Store in adk session state (thread-safe)
            tool_context.state['map_data'] = tool_response
            print("Map data updated.")
    return None



roadtrip_planner = Agent(
    name="roadtrip_planner",
    model=MODEL,
    description=(
        "Plan your next roadtrip!"
    ),
    instruction=prompt.ROADTRIP_PLANNER_ROOT,
    tools=[mcp_tools, AgentTool(search_agent)],
    after_tool_callback=after_tool_callback
)

root_agent = roadtrip_planner