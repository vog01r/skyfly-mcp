#!/usr/bin/env python3
"""
Serveur HTTP/SSE pour exposer le serveur MCP via HTTP/HTTPS.
Combine DEUX MCPs:
  1. Skyfly: données live (positions, états des aéronefs) via OpenSky Network
  2. AircraftDB: référentiel SQL (modèles, registre FAA, moteurs)

Utilise le transport SSE officiel du SDK MCP.
Supporte plusieurs clients simultanés grâce à l'architecture asynchrone.
"""

import json
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
from constants import UNIFIED_SERVER_NAME, SSE_MESSAGES_PATH, SERVICE_INFO
from skyfly_tools import get_skyfly_tools
from skyfly_handlers import handle_skyfly_tool
from templates import get_homepage_html

# Import des outils AircraftDB
from aircraftdb.tools import get_aircraftdb_tools, call_aircraftdb_tool


# Créer le serveur MCP unifié
mcp_server = Server(UNIFIED_SERVER_NAME)

# Client OpenSky API (Skyfly)
opensky_api = AsyncOpenSkyApi()

# Transport SSE (le chemin relatif où les messages POST seront envoyés)
sse_transport = SseServerTransport(SSE_MESSAGES_PATH)


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """Liste tous les outils disponibles (Skyfly + AircraftDB)."""
    # Obtenir les outils Skyfly depuis le module centralisé
    skyfly_tools = get_skyfly_tools()
    
    # Ajouter les outils AircraftDB
    skyfly_tools.extend(get_aircraftdb_tools())
    
    return skyfly_tools


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Exécute un outil MCP (route vers Skyfly ou AircraftDB selon le nom)."""
    try:
        # Router vers AircraftDB si le nom commence par "db_"
        if name.startswith("db_"):
            return await call_aircraftdb_tool(name, arguments)
        
        # Router vers les outils Skyfly
        return await handle_skyfly_tool(name, arguments, opensky_api)
    
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}, indent=2))]


async def homepage(request: Request):
    """Page d'accueil avec documentation."""
    return HTMLResponse(get_homepage_html())


async def health_check(request: Request):
    """Endpoint de vérification de santé."""
    return JSONResponse({
        "status": "healthy",
        **SERVICE_INFO
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
    # Mount pour le handler de messages POST
    Mount("/messages", app=sse_transport.handle_post_message),
]

# Créer l'application Starlette
app = Starlette(routes=routes, middleware=middleware)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
