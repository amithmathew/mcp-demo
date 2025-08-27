"""Road Trip Planner agent"""

from google.adk.agents import LlmAgent

from . import prompt

MODEL = "gemini-2.5-pro"

roadtrip_planner = LlmAgent(
    name="roadtrip_planner",
    model=MODEL,
    description=(
        "Plan your next roadtrip!"
    ),
    instruction=prompt.ROADTRIP_PLANNER_ROOT    
)

root_agent = roadtrip_planner
