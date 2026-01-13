#!/usr/bin/env python3
import json
import time
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse, Response
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from opensky_client import AsyncOpenSkyApi
from aircraftdb.tools import get_aircraftdb_tools, call_aircraftdb_tool
    import uvicorn

"""
Serveur HTTP/SSE pour exposer le serveur MCP via HTTP/HTTPS.
Combine DEUX MCPs:
  1. Skyfly: données live (positions, états des aéronefs) via OpenSky Network
  2. AircraftDB: référentiel SQL (modèles, registre FAA, moteurs)

Utilise le transport SSE officiel du SDK MCP.
Supporte plusieurs clients simultanés grâce à l'architecture asynchrone.
"""





# Import des outils AircraftDB


# Create unified MCP server
mcp_server = Server("skyfly-aircraftdb-mcp")

# Client OpenSky API (Skyfly)
opensky_api = AsyncOpenSkyApi()

# Transport SSE (le chemin relatif où les messages POST seront envoyés)
sse_transport = SseServerTransport("/messages/")

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


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """Liste tous les outils disponibles (Skyfly + AircraftDB)."""
    # Outils Skyfly (données live - NE PAS MODIFIER)
    skyfly_tools = [
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
    
    # AJOUTER les outils AircraftDB (sans modifier Skyfly)
    skyfly_tools.extend(get_aircraftdb_tools())
    
    return skyfly_tools


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Exécute un outil MCP (route vers Skyfly ou AircraftDB selon le nom)."""
    try:
        # Route to AircraftDB if name starts with "db_"
        if name.startswith("db_"):
            return await call_aircraftdb_tool(name, arguments)
        
        # === OUTILS SKYFLY (données live - NE PAS MODIFIER) ===
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
            current = int(time.time())
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
                
                if states_count > 100:
                    result["states"] = result["states"][:100]
                    result["note"] = f"Showing 100 of {states_count} aircraft."
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}, indent=2))]
    
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}, indent=2))]


async def homepage(request: Request):
    """Page d'accueil avec documentation."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>OpenSky MCP Server</title>
        <style>
            :root {
                --bg: #0a0e14;
                --surface: #1a1f2e;
                --primary: #00d4aa;
                --secondary: #7c3aed;
                --text: #e2e8f0;
                --muted: #64748b;
            }
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'JetBrains Mono', 'Fira Code', monospace;
                background: var(--bg);
                color: var(--text);
                min-height: 100vh;
                line-height: 1.6;
            }
            .container {
                max-width: 900px;
                margin: 0 auto;
                padding: 3rem 2rem;
            }
            h1 {
                font-size: 2.5rem;
                background: linear-gradient(135deg, var(--primary), var(--secondary));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 0.5rem;
            }
            .subtitle {
                color: var(--muted);
                font-size: 1.1rem;
                margin-bottom: 2rem;
            }
            .status {
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                background: var(--surface);
                padding: 0.5rem 1rem;
                border-radius: 2rem;
                margin-bottom: 2rem;
            }
            .dot {
                width: 10px;
                height: 10px;
                background: var(--primary);
                border-radius: 50%;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            .card {
                background: var(--surface);
                border-radius: 12px;
                padding: 1.5rem;
                margin-bottom: 1.5rem;
                border: 1px solid rgba(255,255,255,0.05);
            }
            .card h2 {
                color: var(--primary);
                font-size: 1.2rem;
                margin-bottom: 1rem;
            }
            .endpoint {
                background: var(--bg);
                padding: 0.75rem 1rem;
                border-radius: 8px;
                margin: 0.5rem 0;
                font-size: 0.9rem;
            }
            .method {
                color: var(--secondary);
                font-weight: bold;
            }
            .tools-grid {
                display: grid;
                gap: 0.75rem;
            }
            .tool {
                background: var(--bg);
                padding: 1rem;
                border-radius: 8px;
                border-left: 3px solid var(--primary);
            }
            .tool-name {
                color: var(--primary);
                font-weight: bold;
            }
            .tool-desc {
                color: var(--muted);
                font-size: 0.85rem;
                margin-top: 0.25rem;
            }
            code {
                background: var(--bg);
                padding: 0.2rem 0.5rem;
                border-radius: 4px;
                font-size: 0.9rem;
            }
            a { color: var(--primary); }
            pre { white-space: pre-wrap; word-wrap: break-word; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>✈️ Skyfly + AircraftDB MCP</h1>
            <p class="subtitle">Serveur MCP combinant données live (OpenSky) et référentiel FAA (SQL)</p>
            
            <div class="status">
                <span class="dot"></span>
                <span>Server Online</span>
            </div>
            
            <div class="card">
                <h2>📡 Endpoints</h2>
                <div class="endpoint">
                    <span class="method">GET</span> <code>/sse</code> - Connexion SSE pour clients MCP
                </div>
                <div class="endpoint">
                    <span class="method">POST</span> <code>/messages/</code> - Messages MCP
                </div>
                <div class="endpoint">
                    <span class="method">GET</span> <code>/health</code> - Health check
                </div>
            </div>
            
            <div class="card">
                <h2>🛫 Skyfly Tools (données LIVE)</h2>
                <div class="tools-grid">
                    <div class="tool">
                        <div class="tool-name">get_aircraft_states</div>
                        <div class="tool-desc">Positions actuelles des aéronefs (filtrable par région ou ICAO24)</div>
                    </div>
                    <div class="tool">
                        <div class="tool-name">get_arrivals_by_airport</div>
                        <div class="tool-desc">Vols arrivant à un aéroport</div>
                    </div>
                    <div class="tool">
                        <div class="tool-name">get_departures_by_airport</div>
                        <div class="tool-desc">Vols partant d'un aéroport</div>
                    </div>
                    <div class="tool">
                        <div class="tool-name">get_flights_by_aircraft</div>
                        <div class="tool-desc">Historique des vols d'un aéronef</div>
                    </div>
                    <div class="tool">
                        <div class="tool-name">get_track_by_aircraft</div>
                        <div class="tool-desc">Trajectoire/waypoints d'un aéronef</div>
                    </div>
                    <div class="tool">
                        <div class="tool-name">get_aircraft_in_region</div>
                        <div class="tool-desc">Aéronefs par région (france, europe, etc.)</div>
                    </div>
                </div>
            </div>
            
            <div class="card" style="border-left: 3px solid var(--secondary);">
                <h2 style="color: var(--secondary);">🗄️ AircraftDB Tools (référentiel SQL)</h2>
                <div class="tools-grid">
                    <div class="tool" style="border-left-color: var(--secondary);">
                        <div class="tool-name" style="color: var(--secondary);">db_ingest_faa_data</div>
                        <div class="tool-desc">Ingère les fichiers FAA (ACFTREF, ENGINE, MASTER)</div>
                    </div>
                    <div class="tool" style="border-left-color: var(--secondary);">
                        <div class="tool-name" style="color: var(--secondary);">db_lookup_by_mode_s</div>
                        <div class="tool-desc">Recherche par icao24 - enrichit les données live</div>
                    </div>
                    <div class="tool" style="border-left-color: var(--secondary);">
                        <div class="tool-name" style="color: var(--secondary);">db_search_aircraft</div>
                        <div class="tool-desc">Recherche dans le registre FAA</div>
                    </div>
                    <div class="tool" style="border-left-color: var(--secondary);">
                        <div class="tool-name" style="color: var(--secondary);">db_search_models</div>
                        <div class="tool-desc">Recherche de modèles (Boeing, Cessna...)</div>
                    </div>
                    <div class="tool" style="border-left-color: var(--secondary);">
                        <div class="tool-name" style="color: var(--secondary);">db_enrich_live_aircraft</div>
                        <div class="tool-desc">Enrichit une liste d'icao24 avec specs</div>
                    </div>
                    <div class="tool" style="border-left-color: var(--secondary);">
                        <div class="tool-name" style="color: var(--secondary);">db_sql_query</div>
                        <div class="tool-desc">Requête SQL personnalisée</div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>🔗 Configuration MCP</h2>
                <div class="endpoint">
<pre>{
  "mcpServers": {
    "skyfly": {
      "url": "https://skyfly.mcp.hamon.link/sse"
    }
  }
}</pre>
                </div>
            </div>
            
            <p style="color: var(--muted); text-align: center; margin-top: 2rem;">
                Skyfly (live) + AircraftDB (SQL) • Powered by <a href="https://opensky-network.org">OpenSky</a> & FAA
            </p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(html)


async def health_check(request: Request):
    """Endpoint de vérification de santé."""
    return JSONResponse({
        "status": "healthy",
        "service": "opensky-mcp",
        "version": "1.0.0"
    })


async def handle_sse(request: Request):
    """Endpoint SSE pour les connexions MCP - utilise le transport officiel."""
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0],
            streams[1],
            mcp_server.create_initialization_options()
        )
    # Retourner une réponse vide pour éviter l'erreur NoneType
    return Response()


# Configuration CORS pour permettre les requêtes cross-origin
middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

# Routes de l'application
routes = [
    Route("/", homepage),
    Route("/health", health_check),
    Route("/sse", handle_sse),
    # Mount for POST message handler
    Mount("/messages", app=sse_transport.handle_post_message),
]

# Créer l'application Starlette
app = Starlette(routes=routes, middleware=middleware)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
