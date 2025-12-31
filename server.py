#!/usr/bin/env python3
"""
Serveur MCP pour l'API OpenSky Network.
Expose les fonctionnalités de l'API OpenSky via le protocole MCP.
Supporte les connexions concurrentes pour plusieurs utilisateurs.
"""

import json
import time
from typing import Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import asyncio

from opensky_client import AsyncOpenSkyApi


# Créer l'instance du serveur MCP
server = Server("opensky-mcp")

# Client OpenSky API (peut être configuré avec credentials)
opensky_api = AsyncOpenSkyApi()


def get_current_time() -> int:
    """Retourne le timestamp Unix actuel."""
    return int(time.time())


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Liste tous les outils disponibles."""
    return [
        Tool(
            name="get_aircraft_states",
            description="""Récupère l'état actuel des aéronefs dans l'espace aérien.
            Peut filtrer par adresse ICAO24 ou par zone géographique (bounding box).
            Sans authentification, limité à une requête toutes les 10 secondes.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "icao24": {
                        "type": "string",
                        "description": "Adresse ICAO24 de l'aéronef (hex, minuscules). Optionnel."
                    },
                    "min_latitude": {
                        "type": "number",
                        "description": "Latitude minimum de la bounding box (WGS84). Optionnel."
                    },
                    "max_latitude": {
                        "type": "number",
                        "description": "Latitude maximum de la bounding box (WGS84). Optionnel."
                    },
                    "min_longitude": {
                        "type": "number",
                        "description": "Longitude minimum de la bounding box (WGS84). Optionnel."
                    },
                    "max_longitude": {
                        "type": "number",
                        "description": "Longitude maximum de la bounding box (WGS84). Optionnel."
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_arrivals_by_airport",
            description="""Récupère les vols arrivant à un aéroport spécifique dans un intervalle de temps.
            L'intervalle ne doit pas dépasser 7 jours.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "airport": {
                        "type": "string",
                        "description": "Code ICAO de l'aéroport (ex: LFPG pour Paris CDG, EDDF pour Frankfurt)"
                    },
                    "begin": {
                        "type": "integer",
                        "description": "Début de l'intervalle en timestamp Unix (secondes depuis epoch)"
                    },
                    "end": {
                        "type": "integer",
                        "description": "Fin de l'intervalle en timestamp Unix (secondes depuis epoch)"
                    }
                },
                "required": ["airport", "begin", "end"]
            }
        ),
        Tool(
            name="get_departures_by_airport",
            description="""Récupère les vols partant d'un aéroport spécifique dans un intervalle de temps.
            L'intervalle ne doit pas dépasser 7 jours.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "airport": {
                        "type": "string",
                        "description": "Code ICAO de l'aéroport (ex: LFPG pour Paris CDG, EDDF pour Frankfurt)"
                    },
                    "begin": {
                        "type": "integer",
                        "description": "Début de l'intervalle en timestamp Unix (secondes depuis epoch)"
                    },
                    "end": {
                        "type": "integer",
                        "description": "Fin de l'intervalle en timestamp Unix (secondes depuis epoch)"
                    }
                },
                "required": ["airport", "begin", "end"]
            }
        ),
        Tool(
            name="get_flights_by_aircraft",
            description="""Récupère l'historique des vols d'un aéronef spécifique.
            L'intervalle ne doit pas dépasser 30 jours.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "icao24": {
                        "type": "string",
                        "description": "Adresse ICAO24 de l'aéronef (hex, minuscules)"
                    },
                    "begin": {
                        "type": "integer",
                        "description": "Début de l'intervalle en timestamp Unix (secondes depuis epoch)"
                    },
                    "end": {
                        "type": "integer",
                        "description": "Fin de l'intervalle en timestamp Unix (secondes depuis epoch)"
                    }
                },
                "required": ["icao24", "begin", "end"]
            }
        ),
        Tool(
            name="get_flights_from_interval",
            description="""Récupère tous les vols dans un intervalle de temps.
            ATTENTION: L'intervalle ne doit pas dépasser 2 heures (7200 secondes).""",
            inputSchema={
                "type": "object",
                "properties": {
                    "begin": {
                        "type": "integer",
                        "description": "Début de l'intervalle en timestamp Unix (secondes depuis epoch)"
                    },
                    "end": {
                        "type": "integer",
                        "description": "Fin de l'intervalle en timestamp Unix (secondes depuis epoch)"
                    }
                },
                "required": ["begin", "end"]
            }
        ),
        Tool(
            name="get_track_by_aircraft",
            description="""Récupère la trajectoire (liste de waypoints) d'un aéronef.
            Peut récupérer le suivi en direct ou une trajectoire historique (max 30 jours).""",
            inputSchema={
                "type": "object",
                "properties": {
                    "icao24": {
                        "type": "string",
                        "description": "Adresse ICAO24 de l'aéronef (hex, minuscules)"
                    },
                    "time": {
                        "type": "integer",
                        "description": "Timestamp Unix pour une trajectoire historique. 0 ou absent pour le suivi en direct."
                    }
                },
                "required": ["icao24"]
            }
        ),
        Tool(
            name="get_current_timestamp",
            description="""Retourne le timestamp Unix actuel. Utile pour calculer les intervalles de temps.""",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_aircraft_in_region",
            description="""Récupère tous les aéronefs dans une région prédéfinie.
            Régions disponibles: france, germany, switzerland, spain, italy, uk, europe, usa_east, usa_west, world""",
            inputSchema={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "Nom de la région: france, germany, switzerland, spain, italy, uk, europe, usa_east, usa_west, world"
                    }
                },
                "required": ["region"]
            }
        )
    ]


# Définition des régions prédéfinies
REGIONS = {
    "france": (41.3, 51.1, -5.1, 9.6),
    "germany": (47.3, 55.1, 5.9, 15.0),
    "switzerland": (45.8, 47.8, 5.9, 10.5),
    "spain": (36.0, 43.8, -9.3, 3.3),
    "italy": (36.6, 47.1, 6.6, 18.5),
    "uk": (49.9, 60.9, -8.6, 1.8),
    "europe": (35.0, 72.0, -25.0, 45.0),
    "usa_east": (24.5, 49.4, -87.5, -66.9),
    "usa_west": (24.5, 49.4, -124.7, -100.0),
    "world": (-90.0, 90.0, -180.0, 180.0)
}


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Exécute un outil MCP."""
    try:
        if name == "get_aircraft_states":
            icao24 = arguments.get("icao24")
            bbox = None
            
            if all(k in arguments for k in ["min_latitude", "max_latitude", "min_longitude", "max_longitude"]):
                bbox = (
                    arguments["min_latitude"],
                    arguments["max_latitude"],
                    arguments["min_longitude"],
                    arguments["max_longitude"]
                )
            
            result = await opensky_api.get_states(icao24=icao24, bbox=bbox)
            
            if result and result.get("states"):
                states_count = len(result["states"])
                # Limiter à 50 états pour éviter des réponses trop longues
                if states_count > 50:
                    result["states"] = result["states"][:50]
                    result["note"] = f"Showing 50 of {states_count} aircraft. Use a smaller bounding box for complete data."
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "get_arrivals_by_airport":
            airport = arguments["airport"]
            begin = arguments["begin"]
            end = arguments["end"]
            
            result = await opensky_api.get_arrivals_by_airport(airport, begin, end)
            return [TextContent(type="text", text=json.dumps({"arrivals": result, "count": len(result) if result else 0}, indent=2))]
        
        elif name == "get_departures_by_airport":
            airport = arguments["airport"]
            begin = arguments["begin"]
            end = arguments["end"]
            
            result = await opensky_api.get_departures_by_airport(airport, begin, end)
            return [TextContent(type="text", text=json.dumps({"departures": result, "count": len(result) if result else 0}, indent=2))]
        
        elif name == "get_flights_by_aircraft":
            icao24 = arguments["icao24"]
            begin = arguments["begin"]
            end = arguments["end"]
            
            result = await opensky_api.get_flights_by_aircraft(icao24, begin, end)
            return [TextContent(type="text", text=json.dumps({"flights": result, "count": len(result) if result else 0}, indent=2))]
        
        elif name == "get_flights_from_interval":
            begin = arguments["begin"]
            end = arguments["end"]
            
            result = await opensky_api.get_flights_from_interval(begin, end)
            return [TextContent(type="text", text=json.dumps({"flights": result, "count": len(result) if result else 0}, indent=2))]
        
        elif name == "get_track_by_aircraft":
            icao24 = arguments["icao24"]
            t = arguments.get("time", 0)
            
            result = await opensky_api.get_track_by_aircraft(icao24, t)
            if result:
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            else:
                return [TextContent(type="text", text=json.dumps({"error": "No track found for this aircraft"}, indent=2))]
        
        elif name == "get_current_timestamp":
            current = get_current_time()
            return [TextContent(type="text", text=json.dumps({
                "timestamp": current,
                "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(current)),
                "hint": "Use this timestamp for 'end' parameter. Subtract seconds for 'begin' (e.g., 3600 for 1 hour ago)"
            }, indent=2))]
        
        elif name == "get_aircraft_in_region":
            region = arguments["region"].lower()
            
            if region not in REGIONS:
                return [TextContent(type="text", text=json.dumps({
                    "error": f"Unknown region: {region}",
                    "available_regions": list(REGIONS.keys())
                }, indent=2))]
            
            bbox = REGIONS[region]
            result = await opensky_api.get_states(bbox=bbox)
            
            if result and result.get("states"):
                states_count = len(result["states"])
                result["region"] = region
                result["bbox"] = {"min_lat": bbox[0], "max_lat": bbox[1], "min_lon": bbox[2], "max_lon": bbox[3]}
                
                # Limiter à 100 états
                if states_count > 100:
                    result["states"] = result["states"][:100]
                    result["note"] = f"Showing 100 of {states_count} aircraft."
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}, indent=2))]
    
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}, indent=2))]


async def main():
    """Point d'entrée principal du serveur MCP."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

