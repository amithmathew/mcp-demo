from fastmcp import FastMCP
from dotenv import load_dotenv
from typing import List
import json
from typing import List
from google.maps.routing_v2 import RoutesClient
from google.maps.routing_v2.types import (
    ComputeRoutesRequest,
    RouteModifiers,
    RouteTravelMode,
    Waypoint,
    Location, # <-- Make sure Location is imported
)

load_dotenv()

mcp = FastMCP("Google Maps MCP Server")
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
        A pyton dict containing route information. Includes:
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
    
    field_mask = (
        "routes.duration,routes.distanceMeters,routes.description,routes.polyline.encodedPolyline,"
        "routes.optimizedIntermediateWaypointIndex,"
        "routes.legs.startLocation.latLng,"
        "routes.legs.endLocation.latLng"
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
        # Only optimize if there are waypoints to optimize
        optimize_waypoint_order=True if intermediates_wps else False,
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

    print(response) # Good for debugging!

    route = response.routes[0]
    
    ordered_waypoints = []

    # 1. Add Origin
    # The origin of the *route* is the startLocation of the *first leg*.
    ordered_waypoints.append({
        "address": from_address,
        "lat": route.legs[0].start_location.lat_lng.latitude,
        "lng": route.legs[0].start_location.lat_lng.longitude,
        "details": "Starting Point"
    })

    # 2. Add Optimized Intermediates
    if route.optimized_intermediate_waypoint_index:
        # Iterate over the optimized index list to get the correct *original* address
        for i, original_index in enumerate(route.optimized_intermediate_waypoint_index):
            original_address = landmarks_to_visit[original_index]
            
            # The location data is the *end* of the corresponding leg.
            # Stop 1 (i=0) is the end of leg 0.
            leg_for_this_stop = route.legs[i]
            
            ordered_waypoints.append({
                "address": original_address,
                "lat": leg_for_this_stop.end_location.lat_lng.latitude,
                "lng": leg_for_this_stop.end_location.lat_lng.longitude,
                "details": f"Stop {i+1}: {original_address}"
            })
    elif landmarks_to_visit:
        # No optimization, but intermediates exist. Add them in the order given.
        for i, address in enumerate(landmarks_to_visit):
            leg_for_this_stop = route.legs[i]
            ordered_waypoints.append({
                "address": address,
                "lat": leg_for_this_stop.end_location.lat_lng.latitude,
                "lng": leg_for_this_stop.end_location.lat_lng.longitude,
                "details": f"Stop {i+1}: {address}"
            })

    # 3. Add Destination
    # The destination of the *route* is the endLocation of the *last leg*.
    ordered_waypoints.append({
        "address": to_address,
        "lat": route.legs[-1].end_location.lat_lng.latitude,
        "lng": route.legs[-1].end_location.lat_lng.longitude,
        "details": "Destination"
    })

    # Convert duration (seconds) to human-readable string
    duration_seconds = route.duration.seconds
    hours = duration_seconds // 3600
    minutes = (duration_seconds % 3600) // 60
    duration_text = f"{hours} hr {minutes} min"

    # Convert distance (meters) to km
    distance_km = round(route.distance_meters / 1000, 1)
    distance_text = f"{distance_km} km"

    result = {
        "description": route.description,
        "duration_text": duration_text,
        "distance_text": distance_text,
        "encoded_polyline": route.polyline.encoded_polyline, 
        "ordered_waypoints": ordered_waypoints,
    }
    
    # Return as a JSON string to match your docstring
    return result


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