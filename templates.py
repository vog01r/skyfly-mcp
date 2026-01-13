"""
Templates HTML pour l'interface web du serveur MCP.
Sépare la présentation de la logique métier pour améliorer la lisibilité.
"""

from constants import SERVICE_INFO


def get_homepage_html() -> str:
    """
    Retourne le HTML de la page d'accueil.
    
    Returns:
        Contenu HTML complet de la page d'accueil
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>OpenSky MCP Server</title>
        <style>
            :root {{
                --bg: #0a0e14;
                --surface: #1a1f2e;
                --primary: #00d4aa;
                --secondary: #7c3aed;
                --text: #e2e8f0;
                --muted: #64748b;
            }}
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'JetBrains Mono', 'Fira Code', monospace;
                background: var(--bg);
                color: var(--text);
                min-height: 100vh;
                line-height: 1.6;
            }}
            .container {{
                max-width: 900px;
                margin: 0 auto;
                padding: 3rem 2rem;
            }}
            h1 {{
                font-size: 2.5rem;
                background: linear-gradient(135deg, var(--primary), var(--secondary));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                margin-bottom: 0.5rem;
            }}
            .subtitle {{
                color: var(--muted);
                font-size: 1.1rem;
                margin-bottom: 2rem;
            }}
            .status {{
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                background: var(--surface);
                padding: 0.5rem 1rem;
                border-radius: 2rem;
                margin-bottom: 2rem;
            }}
            .dot {{
                width: 10px;
                height: 10px;
                background: var(--primary);
                border-radius: 50%;
                animation: pulse 2s infinite;
            }}
            @keyframes pulse {{
                0%, 100% {{ opacity: 1; }}
                50% {{ opacity: 0.5; }}
            }}
            .card {{
                background: var(--surface);
                border-radius: 12px;
                padding: 1.5rem;
                margin-bottom: 1.5rem;
                border: 1px solid rgba(255,255,255,0.05);
            }}
            .card h2 {{
                color: var(--primary);
                font-size: 1.2rem;
                margin-bottom: 1rem;
            }}
            .endpoint {{
                background: var(--bg);
                padding: 0.75rem 1rem;
                border-radius: 8px;
                margin: 0.5rem 0;
                font-size: 0.9rem;
            }}
            .method {{
                color: var(--secondary);
                font-weight: bold;
            }}
            .tools-grid {{
                display: grid;
                gap: 0.75rem;
            }}
            .tool {{
                background: var(--bg);
                padding: 1rem;
                border-radius: 8px;
                border-left: 3px solid var(--primary);
            }}
            .tool-name {{
                color: var(--primary);
                font-weight: bold;
            }}
            .tool-desc {{
                color: var(--muted);
                font-size: 0.85rem;
                margin-top: 0.25rem;
            }}
            code {{
                background: var(--bg);
                padding: 0.2rem 0.5rem;
                border-radius: 4px;
                font-size: 0.9rem;
            }}
            a {{ color: var(--primary); }}
            pre {{ white-space: pre-wrap; word-wrap: break-word; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>✈️ Skyfly + AircraftDB MCP</h1>
            <p class="subtitle">{SERVICE_INFO['description']}</p>
            
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
<pre>{{
  "mcpServers": {{
    "skyfly": {{
      "url": "https://skyfly.mcp.hamon.link/sse"
    }}
  }}
}}</pre>
                </div>
            </div>
            
            <p style="color: var(--muted); text-align: center; margin-top: 2rem;">
                Skyfly (live) + AircraftDB (SQL) • Powered by <a href="https://opensky-network.org">OpenSky</a> & FAA
            </p>
        </div>
    </body>
    </html>
    """