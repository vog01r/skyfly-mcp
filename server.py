#!/usr/bin/env python3
"""
Serveur MCP pour l'API OpenSky Network.
Expose les fonctionnalités de l'API OpenSky via le protocole MCP.
Supporte les connexions concurrentes pour plusieurs utilisateurs.
"""

import json
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from opensky_client import AsyncOpenSkyApi
from constants import SERVER_NAME
from skyfly_tools import get_skyfly_tools
from skyfly_handlers import handle_skyfly_tool


# Créer l'instance du serveur MCP
server = Server(SERVER_NAME)

# Client OpenSky API (peut être configuré avec credentials)
opensky_api = AsyncOpenSkyApi()


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Liste tous les outils disponibles."""
    return get_skyfly_tools()


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Exécute un outil MCP."""
    try:
        return await handle_skyfly_tool(name, arguments, opensky_api)
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

