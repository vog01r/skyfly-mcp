"""
Gestionnaires pour les outils Skyfly.
Sépare la logique métier de la définition des outils pour améliorer la lisibilité.
"""

import json
import time
from typing import Optional
from mcp.types import TextContent

from opensky_client import AsyncOpenSkyApi
from constants import (
    DEFAULT_AIRCRAFT_LIMIT, 
    DEFAULT_REGION_AIRCRAFT_LIMIT,
    TIMESTAMP_HELP_MESSAGE
)
from skyfly_tools import get_region_bbox, get_available_regions


async def handle_get_aircraft_states(opensky_api: AsyncOpenSkyApi, arguments: dict) -> list[TextContent]:
    """Gère la requête get_aircraft_states."""
    icao24 = arguments.get("icao24")
    bbox = None
    
    # Construire la bounding box si tous les paramètres sont présents
    if all(k in arguments for k in ["min_latitude", "max_latitude", "min_longitude", "max_longitude"]):
        bbox = (
            arguments["min_latitude"],
            arguments["max_latitude"],
            arguments["min_longitude"],
            arguments["max_longitude"]
        )
    
    result = await opensky_api.get_states(icao24=icao24, bbox=bbox)
    
    # Limiter le nombre de résultats pour éviter des réponses trop longues
    if result and result.get("states"):
        states_count = len(result["states"])
        if states_count > DEFAULT_AIRCRAFT_LIMIT:
            result["states"] = result["states"][:DEFAULT_AIRCRAFT_LIMIT]
            result["note"] = f"Showing {DEFAULT_AIRCRAFT_LIMIT} of {states_count} aircraft. Use a smaller bounding box for complete data."
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_get_arrivals_by_airport(opensky_api: AsyncOpenSkyApi, arguments: dict) -> list[TextContent]:
    """Gère la requête get_arrivals_by_airport."""
    airport = arguments["airport"]
    begin = arguments["begin"]
    end = arguments["end"]
    
    result = await opensky_api.get_arrivals_by_airport(airport, begin, end)
    return [TextContent(type="text", text=json.dumps({
        "arrivals": result, 
        "count": len(result) if result else 0
    }, indent=2))]


async def handle_get_departures_by_airport(opensky_api: AsyncOpenSkyApi, arguments: dict) -> list[TextContent]:
    """Gère la requête get_departures_by_airport."""
    airport = arguments["airport"]
    begin = arguments["begin"]
    end = arguments["end"]
    
    result = await opensky_api.get_departures_by_airport(airport, begin, end)
    return [TextContent(type="text", text=json.dumps({
        "departures": result, 
        "count": len(result) if result else 0
    }, indent=2))]


async def handle_get_flights_by_aircraft(opensky_api: AsyncOpenSkyApi, arguments: dict) -> list[TextContent]:
    """Gère la requête get_flights_by_aircraft."""
    icao24 = arguments["icao24"]
    begin = arguments["begin"]
    end = arguments["end"]
    
    result = await opensky_api.get_flights_by_aircraft(icao24, begin, end)
    return [TextContent(type="text", text=json.dumps({
        "flights": result, 
        "count": len(result) if result else 0
    }, indent=2))]


async def handle_get_flights_from_interval(opensky_api: AsyncOpenSkyApi, arguments: dict) -> list[TextContent]:
    """Gère la requête get_flights_from_interval."""
    begin = arguments["begin"]
    end = arguments["end"]
    
    result = await opensky_api.get_flights_from_interval(begin, end)
    return [TextContent(type="text", text=json.dumps({
        "flights": result, 
        "count": len(result) if result else 0
    }, indent=2))]


async def handle_get_track_by_aircraft(opensky_api: AsyncOpenSkyApi, arguments: dict) -> list[TextContent]:
    """Gère la requête get_track_by_aircraft."""
    icao24 = arguments["icao24"]
    t = arguments.get("time", 0)
    
    result = await opensky_api.get_track_by_aircraft(icao24, t)
    if result:
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    else:
        return [TextContent(type="text", text=json.dumps({
            "error": "No track found for this aircraft"
        }, indent=2))]


async def handle_get_current_timestamp(arguments: dict) -> list[TextContent]:
    """Gère la requête get_current_timestamp."""
    current = int(time.time())
    return [TextContent(type="text", text=json.dumps({
        "timestamp": current,
        "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(current)),
        "hint": TIMESTAMP_HELP_MESSAGE
    }, indent=2))]


async def handle_get_aircraft_in_region(opensky_api: AsyncOpenSkyApi, arguments: dict) -> list[TextContent]:
    """Gère la requête get_aircraft_in_region."""
    region = arguments["region"].lower()
    
    bbox = get_region_bbox(region)
    if not bbox:
        return [TextContent(type="text", text=json.dumps({
            "error": f"Unknown region: {region}",
            "available_regions": get_available_regions()
        }, indent=2))]
    
    result = await opensky_api.get_states(bbox=bbox)
    
    if result and result.get("states"):
        states_count = len(result["states"])
        result["region"] = region
        result["bbox"] = {
            "min_lat": bbox[0], 
            "max_lat": bbox[1], 
            "min_lon": bbox[2], 
            "max_lon": bbox[3]
        }
        
        # Limiter le nombre d'états pour les régions
        if states_count > DEFAULT_REGION_AIRCRAFT_LIMIT:
            result["states"] = result["states"][:DEFAULT_REGION_AIRCRAFT_LIMIT]
            result["note"] = f"Showing {DEFAULT_REGION_AIRCRAFT_LIMIT} of {states_count} aircraft."
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# Dictionnaire de mapping pour les gestionnaires
SKYFLY_HANDLERS = {
    "get_aircraft_states": handle_get_aircraft_states,
    "get_arrivals_by_airport": handle_get_arrivals_by_airport,
    "get_departures_by_airport": handle_get_departures_by_airport,
    "get_flights_by_aircraft": handle_get_flights_by_aircraft,
    "get_flights_from_interval": handle_get_flights_from_interval,
    "get_track_by_aircraft": handle_get_track_by_aircraft,
    "get_current_timestamp": handle_get_current_timestamp,
    "get_aircraft_in_region": handle_get_aircraft_in_region,
}


async def handle_skyfly_tool(name: str, arguments: dict, opensky_api: AsyncOpenSkyApi) -> list[TextContent]:
    """
    Point d'entrée principal pour tous les outils Skyfly.
    
    Args:
        name: Nom de l'outil
        arguments: Arguments de l'outil
        opensky_api: Instance du client OpenSky
        
    Returns:
        Réponse formatée pour MCP
    """
    handler = SKYFLY_HANDLERS.get(name)
    if not handler:
        return [TextContent(type="text", text=json.dumps({
            "error": f"Unknown Skyfly tool: {name}"
        }, indent=2))]
    
    # Certains handlers n'ont pas besoin de l'API OpenSky
    if name == "get_current_timestamp":
        return await handler(arguments)
    else:
        return await handler(opensky_api, arguments)