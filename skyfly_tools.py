"""
Définitions des outils Skyfly pour le serveur MCP.
Centralise les schémas et évite la duplication entre server.py et http_server.py.
"""

from mcp.types import Tool
from constants import REGIONS


def get_skyfly_tools() -> list[Tool]:
    """
    Retourne la liste des outils Skyfly (données live OpenSky).
    
    Returns:
        Liste des outils MCP pour les données en temps réel
    """
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
            description=f"""Récupère tous les aéronefs dans une région prédéfinie.
            Régions disponibles: {', '.join(REGIONS.keys())}""",
            inputSchema={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": f"Nom de la région: {', '.join(REGIONS.keys())}"
                    }
                },
                "required": ["region"]
            }
        )
    ]


def get_region_bbox(region_name: str) -> tuple:
    """
    Retourne la bounding box d'une région prédéfinie.
    
    Args:
        region_name: Nom de la région (insensible à la casse)
        
    Returns:
        Tuple (min_lat, max_lat, min_lon, max_lon) ou None si région inconnue
    """
    return REGIONS.get(region_name.lower())


def get_available_regions() -> list[str]:
    """
    Retourne la liste des régions disponibles.
    
    Returns:
        Liste des noms de régions
    """
    return list(REGIONS.keys())