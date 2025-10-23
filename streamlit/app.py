import streamlit as st
import uuid
import folium
import polyline
import asyncio
from dotenv import load_dotenv
from streamlit_folium import st_folium

from google.genai import types
from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import google_search
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams

import prompt

# env
load_dotenv()

# ADK Agent
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

# Display Map tool
def display_map(encoded_polyline: str, waypoints: list[dict]) -> str:
    """
    Display a route map with waypoints in the streamlit UI
    
    Args:
        encoded_polyline: Google Maps encoded polyline string representing the route.
        waypoints: List of waypoint dictionaries with keys: address, lat, lng, details

    Returns:
        Confirmation message that map was updated
    """
    st.session_state.map_data = {
        "encoded_polyline": encoded_polyline,
        "ordered_waypoints": waypoints
    }
    return "Map has been updated with the route and waypoints."


roadtrip_planner = Agent(
    name="roadtrip_planner",
    model=MODEL,
    description=(
        "Plan your next roadtrip!"
    ),
    instruction=prompt.ROADTRIP_PLANNER_ROOT,
    tools=[mcp_tools, AgentTool(search_agent), display_map]
)



# Init ADK session service ONCE (shared across all streamlit users)
@st.cache_resource
def get_session_service():
    return InMemorySessionService()


session_service = get_session_service()


# Create a UNIQUE session ID per streamlit user
if "adk_session_id" not in st.session_state:
    st.session_state.adk_session_id = str(uuid.uuid4())
    st.session_state.user_id = f"user_{uuid.uuid4()}"

    async def create_session_async():
        await session_service.create_session(
            app_name="Roadtrip Planner",
            user_id=st.session_state.user_id,
            session_id=st.session_state.adk_session_id,
            state={}
        )
    asyncio.run(create_session_async())


# Each streamlit user gets their own ADK session
runner = Runner(
    app_name="Roadtrip Planner",
    agent=roadtrip_planner,
    session_service=session_service
)


st.set_page_config(layout="wide")
st.title("MCP Demo - Roadtrip Planner")

# --- Initialize Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "I'm your friendly AI roadtrip planner! How can I help?"})

if "map_data" not in st.session_state:
    st.session_state.map_data = None

# Define layout
col1, col2 = st.columns([2, 3]) # Chat on left, map on right (map is wider)

# --- Column 1: Chat Interface ---
with col1:
    st.header("Your roadtrip planner")

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Handle new user input
    if prompt_input := st.chat_input("Where do you want to go?"):
        # Add user message to state and display it
        st.session_state.messages.append({"role": "user", "content": prompt_input})
        with st.chat_message("user"):
            st.markdown(prompt_input)

        # Get assistant response
        with st.chat_message("assistant"):
            with st.spinner("Your assistant is thinking... (this may take a moment)"):
                # Async wrapper to get response
                async def get_agent_response():
                    response_text = None
                    user_content = types.Content(role='user', parts=[types.Part(text=prompt_input)])
                    async for event in runner.run_async(user_id = st.session_state.user_id,
                                                        session_id = st.session_state.adk_session_id,
                                                        new_message=user_content # ADK handles it's own history
                        ):
                        if event.is_final_response():
                            response_text = event.content.parts[0].text
                    return response_text
                
                response = asyncio.run(get_agent_response())
                
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.markdown(response)

        # Force a rerun to update map
        st.rerun()

# --- Column 2: Map Display ---
with col2:
    st.header("Route Map")

    map_to_display = None
    
    if st.session_state.map_data:
        try:
            data = st.session_state.map_data
            
            # Decode the polyline
            points = polyline.decode(data["encoded_polyline"])
            
            if points:
                # Create map centered on the first point
                m = folium.Map(location=points[0], zoom_start=10)

                # Add the route line
                folium.PolyLine(
                    points,
                    color="blue",
                    weight=5,
                    opacity=0.8
                ).add_to(m)

                # Add markers for each waypoint
                for wp in data["ordered_waypoints"]:
                    popup_html = f"<b>{wp['address']}</b><hr>{wp.get('details', 'No details found.')}"
                    folium.Marker(
                        location=[wp["lat"], wp["lng"]],
                        popup=folium.Popup(popup_html, max_width=300),
                        tooltip=wp["address"],
                        icon=folium.Icon(color="red" if "Stop" in wp["details"] else "blue")
                    ).add_to(m)

                # Fit map to bounds of all points
                m.fit_bounds(m.get_bounds())
                map_to_display = m
            else:
                st.error("Could not decode route.")

        except Exception as e:
            st.error(f"Error creating map: {e}")
            st.session_state.map_data = None # Clear bad data

    # Display the map (either the new route or a default)
    if map_to_display:
        st_folium(map_to_display, use_container_width=True, height=600)
    else:
        # Show a default world map if no route is planned
        st.info("Your map will appear here once a route is planned!")
        m_default = folium.Map(location=[20, 0], zoom_start=2)
        st_folium(m_default, use_container_width=True, height=600)