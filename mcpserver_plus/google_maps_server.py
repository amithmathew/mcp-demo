from fastmcp import FastMCP
from dotenv import load_dotenv
import os

from google.maps.routing_v2 import RoutesClient
from google.maps.routing_v2.types import ComputeRoutesRequest, Waypoint, RouteModifiers

import urllib.parse

from typing import List

load_dotenv()

mcp = FastMCP("Google Maps MCP Server PLUS++")
client = RoutesClient()

@mcp.tool
def get_directions(from_address: str, 
                   to_address: str, 
                   avoid_highways: bool = False, 
                   avoid_tolls: bool = False, 
                   avoid_ferries: bool = False, 
                   landmarks_to_visit: List[str] = [], 
                   travel_mode: str = "DRIVE"):
    """Gets optimized directions for a trip, including duration and distance.

    This tool can calculate a route between a start and end address,
    optionally visiting a list of landmarks. It can optimize the order
    of the landmarks to minimize travel time and can be configured to
    avoid highways, tolls, or ferries.

    Args:
        from_address: The starting address for the directions, e.g., "1600 Amphitheatre Parkway, Mountain View, CA".
        to_address: The destination address for the directions, e.g., "350 5th Ave, New York, NY".
        avoid_highways: If true, avoids highways where reasonable. Defaults to False.
        avoid_tolls: If true, avoids toll roads where reasonable. Defaults to False.
        avoid_ferries: If true, avoids ferries where reasonable. Defaults to False.
        landmarks_to_visit: A list of landmark addresses to visit along the way. The tool will optimize the order of these waypoints.
        travel_mode: The mode of transportation. Defaults to "DRIVE".
            Valid options from RouteTravelMode enum: "DRIVE", "BICYCLE", "WALK", "TWO_WHEELER", "TRANSIT".

    Returns:
        A dictionary containing the route information including 'duration_in_seconds',
        'duration_in_hours', and 'distance_meters', or an error message string if a route cannot be found.
    """
    
    field_mask = "routes.duration,routes.distanceMeters,routes.optimized_intermediate_waypoint_index,routes.description"

    intermediates = [Waypoint(address=landmark) for landmark in landmarks_to_visit]

    modifiers = RouteModifiers(
        avoid_tolls=avoid_tolls,
        avoid_ferries=avoid_ferries,
        avoid_highways=avoid_highways, 
    )

    compute_routes_request = ComputeRoutesRequest(
        origin=Waypoint(address=from_address),
        destination=Waypoint(address=to_address),
        intermediates=intermediates,
        optimize_waypoint_order=True,
        route_modifiers=modifiers,
        travel_mode=travel_mode,
    )

    response = client.compute_routes(
        request=compute_routes_request,
        metadata=[('x-goog-fieldmask', field_mask)]
        )
    if not response.routes:
        return "Addresses may not have been valid. Can you make them more specific?"

    #route = response.routes[0]
    #duration_seconds = route.duration.seconds

    #result = {
    #    "duration_in_seconds": duration_seconds,
    #    "duration_in_hours": round(duration_seconds / 3600, 2),
    #    "distance_meters": route.distance_meters,
    #}
    return response


@mcp.tool
def get_map_url(from_address: str, to_address: str, waypoints: List[str] = [], travel_mode: str = "driving"):
    """Generates a Google Maps URL for charting directions.

    This tool creates a URL that opens Google Maps with directions
    from a starting point to a destination, optionally including
    waypoints and a specific travel mode.

    Args:
        from_address: The starting address, e.g., "1600 Amphitheatre Parkway, Mountain View, CA".
        to_address: The destination address, e.g., "350 5th Ave, New York, NY".
        waypoints: A list of addresses to pass through between the origin and destination.
        travel_mode: The mode of transportation. Defaults to "driving".
            Valid options are: "driving", "walking", "bicycling", "transit".

    Returns:
        A string containing the Google Maps URL for the specified directions.
    """
    encoded_origin = urllib.parse.quote(from_address)
    encoded_destination = urllib.parse.quote(to_address)
    encoded_waypoints = urllib.parse.quote("|".join(waypoints))

    url = (f"https://www.google.com/maps/dir/?api=1"
           f"&origin={encoded_origin}"
           f"&destination={encoded_destination}"
           f"&waypoints={encoded_waypoints}"
           f"&travelmode={travel_mode.lower()}")

    print(url)
    return url


@mcp.prompt
def get_route(origin, destination, waypoints_list):
    """Generates a user messaging asking for start, destination and stops along the way to plan a route"""
    return f"I am starting from {origin} and want to go to {destination} while stopping at {', '.join(waypoints_list)} along the way."


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=8080
    )
