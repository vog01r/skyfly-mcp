#!/usr/bin/env python3
"""
Exemple d'utilisation du serveur Skyfly MCP.
Montre comment se connecter et utiliser les outils.
"""

import asyncio
import aiohttp
import json


async def main():
    """Exemple de connexion au serveur MCP Skyfly."""
    
    # URL du serveur (changez pour votre instance)
    SERVER_URL = "https://skyfly.mcp.hamon.link"
    
    async with aiohttp.ClientSession() as session:
        # 1. Connexion SSE
        print("🔌 Connexion au serveur MCP...")
        async with session.get(f"{SERVER_URL}/sse") as sse:
            # Récupérer l'endpoint pour les messages
            messages_url = None
            async for line in sse.content:
                line = line.decode().strip()
                if line.startswith("data: "):
                    messages_url = f"{SERVER_URL}{line[6:]}"
                    print(f"✅ Connecté! Endpoint: {messages_url}")
                    break
            
            # 2. Initialisation
            await session.post(messages_url, json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "example-client", "version": "1.0"},
                    "capabilities": {}
                }
            })
            
            # Read the response
            async for line in sse.content:
                if line.decode().strip().startswith("data: "):
                    print("✅ Initialisé!")
                    break
            
            # 3. Lister les outils
            await session.post(messages_url, json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list"
            })
            
            async for line in sse.content:
                line = line.decode().strip()
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    tools = [t["name"] for t in data.get("result", {}).get("tools", [])]
                    print(f"\n📋 {len(tools)} outils disponibles:")
                    for tool in tools:
                        prefix = "🛫" if not tool.startswith("db_") else "🗄️"
                        print(f"   {prefix} {tool}")
                    break
            
            # 4. Call a tool
            print("\n🔍 Appel de get_aircraft_in_region (France)...")
            await session.post(messages_url, json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "get_aircraft_in_region",
                    "arguments": {"region": "france"}
                }
            })
            
            async for line in sse.content:
                line = line.decode().strip()
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    content = json.loads(data["result"]["content"][0]["text"])
                    states = content.get("states", [])
                    print(f"✅ {len(states)} aéronefs au-dessus de la France!")
                    
                    # Afficher les 3 premiers
                    for s in states[:3]:
                        print(f"   - {s.get('icao24', '?')}: {s.get('callsign', 'N/A')} @ {s.get('baro_altitude', '?')}m")
                    break
            
            print("\n🎉 Exemple terminé!")


if __name__ == "__main__":
    asyncio.run(main())

