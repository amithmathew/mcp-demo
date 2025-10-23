from fastmcp import FastMCP
from dotenv import load_dotenv
import os
from google.maps.routing_v2 import RoutesClient
from google.maps.routing_v2.types import ComputeRoutesRequest, Waypoint, RouteModifiers, RouteTravelMode
from typing import List
import json

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
    """Gets optimized directions for a trip, including duration, distance,
    and map-plotting data (polyline and ordered waypoints).

    This tool calculates a route between a start and end address,
    optionally visiting a list of landmarks. It optimizes the order
    of the landmarks and can be configured to avoid highways, tolls, or ferries.

    Args:
        from_address: The starting address, e.g., "1600 Amphitheatre Parkway, Mountain View, CA".
        to_address: The destination address, e.g., "350 5th Ave, New York, NY".
        avoid_highways: If true, avoids highways. Defaults to False.
        avoid_tolls: If true, avoids toll roads. Defaults to False.
        avoid_ferries: If true, avoids ferries. Defaults to False.
        landmarks_to_visit: A list of landmark addresses to visit. The tool optimizes their order.
        travel_mode: "DRIVE", "BICYCLE", "WALK", "TWO_WHEELER". Defaults to "DRIVE".

    Returns:
        A JSON string containing route information. Includes:
        - 'duration_text': Human-readable total duration.
        - 'distance_text': Human-readable total distance.
        - 'encoded_polyline': An encoded polyline string for plotting the route on a map.
        - 'ordered_waypoints': A list of dictionaries for each stop (including start
          and end) in the correct optimized order. Each dict contains:
          - 'address': The address or name of the stop.
          - 'lat': Latitude.
          - 'lng': Longitude.
          - 'details': A placeholder for details.
    """
    
    # ***IMPORTANT: Updated field mask to get all data we need***
    field_mask = (
        "routes.duration,routes.distanceMeters,routes.description,routes.polyline.encoded_polyline,"
        "routes.origin,routes.destination,routes.intermediates,routes.optimized_intermediate_waypoint_index"
    )

    intermediates_wps = [Waypoint(address=landmark) for landmark in landmarks_to_visit]

    # Handle travel mode string
    try:
        travel_mode_enum = RouteTravelMode[travel_mode.upper()]
    except KeyError:
        return json.dumps({"error": f"Invalid travel mode: {travel_mode}. Use 'DRIVE', 'BICYCLE', 'WALK', or 'TWO_WHEELER'."})

    compute_routes_request = ComputeRoutesRequest(
        origin=Waypoint(address=from_address),
        destination=Waypoint(address=to_address),
        intermediates=intermediates_wps,
        optimize_waypoint_order=True,
        route_modifiers=RouteModifiers(
            avoid_tolls=avoid_tolls,
            avoid_ferries=avoid_ferries,
            avoid_highways=avoid_highways, 
        ),
        travel_mode=travel_mode_enum,
    )

    try:
        response = client.compute_routes(
            request=compute_routes_request,
            metadata=[('x-goog-fieldmask', field_mask)]
        )
    except Exception as e:
        return json.dumps({"error": f"Error computing routes: {str(e)}"})

    if not response.routes:
        return json.dumps({"error": "No route found. Addresses may not have been valid. Please be more specific."})

    route = response.routes[0]
    
    ordered_waypoints = []

    # 1. Add Origin
    ordered_waypoints.append({
        "address": from_address,
        "lat": route.origin.location.lat_lng.latitude,
        "lng": route.origin.location.lat_lng.longitude,
        "details": "Starting Point"
    })

    # 2. Add Optimized Intermediates
    if route.optimized_intermediate_waypoint_index:
        # The 'route.intermediates' list is ALREADY in the optimized order
        for i, optimized_wp in enumerate(route.intermediates):
            # Find the original address string using the index map
            original_index = route.optimized_intermediate_waypoint_index[i]
            original_address = landmarks_to_visit[original_index]
            
            ordered_waypoints.append({
                "address": original_address,
                "lat": optimized_wp.location.lat_lng.latitude,
                "lng": optimized_wp.location.lat_lng.longitude,
                "details": f"Stop {i+1}: {original_address}" # Placeholder
            })

    # 3. Add Destination
    ordered_waypoints.append({
        "address": to_address,
        "lat": route.destination.location.lat_lng.latitude,
        "lng": route.destination.location.lat_lng.longitude,
        "details": "Destination"
    })

    # Convert duration (seconds) to human-readable string
    duration_seconds = route.duration.seconds
    hours = duration_seconds // 3600
    minutes = (duration_seconds % 3600) // 60
    duration_text = f"{hours} hr {minutes} min"

    # Convert distance (meters) to miles or km (using miles here)
    distance_miles = round(route.distance_meters / 1000, 1)
    distance_text = f"{distance_miles} km"

    result = {
        "description": route.description,
        "duration_text": duration_text,
        "distance_text": distance_text,
        "encoded_polyline": route.polyline.encoded_polyline,
        "ordered_waypoints": ordered_waypoints,
    }
    
    # Return as a JSON string
    return json.dumps(result)


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