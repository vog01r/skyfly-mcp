"""
Constantes partagées pour le projet Skyfly MCP.
Centralise les configurations et évite la duplication entre modules.
"""

# Limites par défaut pour les requêtes
DEFAULT_AIRCRAFT_LIMIT = 50
DEFAULT_REGION_AIRCRAFT_LIMIT = 100
DEFAULT_SEARCH_LIMIT = 50

# Timeouts et configurations réseau
API_TIMEOUT_SECONDS = 30.0
RATE_LIMIT_MESSAGE = "Rate limit exceeded. Please wait before making more requests."

# Définition des régions prédéfinies pour les requêtes géographiques
# Format: (min_latitude, max_latitude, min_longitude, max_longitude)
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

# Limites de temps pour les différents types de requêtes (en secondes)
MAX_INTERVAL_FLIGHTS_ALL = 7200  # 2 heures maximum pour get_flights_from_interval
MAX_INTERVAL_AIRPORT_FLIGHTS = 7 * 24 * 3600  # 7 jours pour arrivals/departures
MAX_INTERVAL_AIRCRAFT_HISTORY = 30 * 24 * 3600  # 30 jours pour historique aéronef

# Messages d'aide pour les utilisateurs
TIMESTAMP_HELP_MESSAGE = "Use this timestamp for 'end' parameter. Subtract seconds for 'begin' (e.g., 3600 for 1 hour ago)"

# Configuration du serveur
SERVER_NAME = "opensky-mcp"
UNIFIED_SERVER_NAME = "skyfly-aircraftdb-mcp"
SSE_MESSAGES_PATH = "/messages/"

# Informations de version et service
SERVICE_INFO = {
    "service": "opensky-mcp",
    "version": "1.0.0",
    "description": "Serveur MCP combinant données live (OpenSky) et référentiel FAA (SQL)"
}