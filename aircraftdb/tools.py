"""
Outils MCP pour AircraftDB.
Ces outils sont AJOUTÉS au serveur MCP existant sans modifier les outils Skyfly.
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List
from mcp.types import Tool, TextContent

from .database import get_database, AircraftDatabase
from .ingest import ingest_directory, FAAAircraftIngest

# Types d'aéronefs FAA
AIRCRAFT_TYPES = {
    1: "Glider",
    2: "Balloon",
    3: "Blimp/Dirigible",
    4: "Fixed wing single engine",
    5: "Fixed wing multi engine",
    6: "Rotorcraft",
    7: "Weight-shift-control",
    8: "Powered Parachute",
    9: "Gyroplane"
}

# Types de moteurs FAA
ENGINE_TYPES = {
    0: "None",
    1: "Reciprocating",
    2: "Turbo-prop",
    3: "Turbo-shaft",
    4: "Turbo-jet",
    5: "Turbo-fan",
    6: "Ramjet",
    7: "2 Cycle",
    8: "4 Cycle",
    9: "Unknown",
    10: "Electric",
    11: "Rotary"
}

# Classes de poids FAA
WEIGHT_CLASSES = {
    "CLASS 1": "Up to 12,499 lbs",
    "CLASS 2": "12,500 - 19,999 lbs",
    "CLASS 3": "20,000 lbs and over",
    "CLASS 4": "UAV up to 55 lbs"
}


def get_aircraftdb_tools() -> List[Tool]:
    """Retourne la liste des outils AircraftDB."""
    return [
        # ============ INGESTION ============
        Tool(
            name="db_ingest_faa_data",
            description="""[AircraftDB] Ingère les fichiers FAA depuis le répertoire ReleasableAircraft_dataset/.
            Parse ACFTREF.txt (modèles), ENGINE.txt (moteurs), MASTER.txt (registre).
            L'ingestion est IDEMPOTENTE (upsert) - peut être relancée sans duplications.
            Source: référentiel SQL.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Chemin du répertoire contenant les fichiers FAA. Par défaut: ReleasableAircraft_dataset/"
                    }
                },
                "required": []
            }
        ),
        
        # ============ QUERIES ============
        Tool(
            name="db_get_stats",
            description="""[AircraftDB] Retourne les statistiques de la base de données.
            Nombre d'entrées par table (modèles, moteurs, registre, etc.).
            Source: référentiel SQL.""",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        Tool(
            name="db_lookup_by_mode_s",
            description="""[AircraftDB] Recherche un aéronef par son code Mode-S hexadécimal (icao24).
            Retourne les infos du registre + modèle + moteur joints.
            Utilisez ce tool pour enrichir les données live de Skyfly avec les specs de l'appareil.
            Source: référentiel SQL.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode_s_hex": {
                        "type": "string",
                        "description": "Code Mode-S hexadécimal (ex: A00713, 3C675A). Correspond à icao24 de Skyfly."
                    }
                },
                "required": ["mode_s_hex"]
            }
        ),
        
        Tool(
            name="db_lookup_by_registration",
            description="""[AircraftDB] Recherche un aéronef par son immatriculation (N-number pour les avions US).
            Retourne les infos du registre + modèle + moteur joints.
            Source: référentiel SQL.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "registration": {
                        "type": "string",
                        "description": "Numéro d'immatriculation (ex: N12345, 100)"
                    }
                },
                "required": ["registration"]
            }
        ),
        
        Tool(
            name="db_search_aircraft",
            description="""[AircraftDB] Recherche des aéronefs dans le registre avec filtres multiples.
            Permet de trouver des appareils par propriétaire, ville, état, année, type.
            Source: référentiel SQL.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "registrant_name": {
                        "type": "string",
                        "description": "Nom du propriétaire (recherche partielle)"
                    },
                    "city": {
                        "type": "string",
                        "description": "Ville (recherche partielle)"
                    },
                    "state": {
                        "type": "string",
                        "description": "Code état US (ex: CA, TX, FL)"
                    },
                    "year_from": {
                        "type": "integer",
                        "description": "Année de fabrication minimum"
                    },
                    "year_to": {
                        "type": "integer",
                        "description": "Année de fabrication maximum"
                    },
                    "type_aircraft": {
                        "type": "integer",
                        "description": "Type d'aéronef: 1=Glider, 4=Fixed wing single, 5=Fixed wing multi, 6=Rotorcraft"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Nombre max de résultats (défaut: 50)"
                    }
                },
                "required": []
            }
        ),
        
        Tool(
            name="db_search_models",
            description="""[AircraftDB] Recherche des modèles d'aéronefs dans le référentiel ACFTREF.
            Permet de trouver des modèles par constructeur, nom, type, nombre de moteurs.
            Source: référentiel SQL.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "manufacturer": {
                        "type": "string",
                        "description": "Nom du constructeur (recherche partielle, ex: BOEING, CESSNA, PIPER)"
                    },
                    "model": {
                        "type": "string",
                        "description": "Nom du modèle (recherche partielle, ex: 737, 172, PA-28)"
                    },
                    "type_aircraft": {
                        "type": "integer",
                        "description": "Type: 1=Glider, 4=Fixed wing single, 5=Fixed wing multi, 6=Rotorcraft"
                    },
                    "num_engines": {
                        "type": "integer",
                        "description": "Nombre de moteurs"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Nombre max de résultats (défaut: 50)"
                    }
                },
                "required": []
            }
        ),
        
        Tool(
            name="db_get_model_info",
            description="""[AircraftDB] Récupère les informations détaillées d'un modèle d'aéronef par son code.
            Retourne constructeur, modèle, type, nombre de moteurs, sièges, classe de poids.
            Source: référentiel SQL.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Code FAA du modèle (ex: 2072738 pour Cessna 172)"
                    }
                },
                "required": ["code"]
            }
        ),
        
        Tool(
            name="db_get_engine_info",
            description="""[AircraftDB] Récupère les informations d'un moteur par son code.
            Retourne constructeur, modèle, type, puissance (HP), poussée.
            Source: référentiel SQL.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Code FAA du moteur"
                    }
                },
                "required": ["code"]
            }
        ),
        
        Tool(
            name="db_sql_query",
            description="""[AircraftDB] Exécute une requête SQL SELECT personnalisée.
            Tables disponibles: aircraft_registry, aircraft_models, engines, dealers.
            Colonnes clés: n_number, mode_s_code_hex, mfr_mdl_code, manufacturer, model, type_aircraft, num_engines.
            ATTENTION: Seules les requêtes SELECT sont autorisées.
            Source: référentiel SQL.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Requête SQL SELECT (ex: SELECT * FROM aircraft_registry WHERE state = 'CA' LIMIT 10)"
                    }
                },
                "required": ["query"]
            }
        ),
        
        Tool(
            name="db_enrich_live_aircraft",
            description="""[AircraftDB] Enrichit une liste d'aéronefs live (depuis Skyfly) avec les données du référentiel.
            Prend une liste de codes icao24 et retourne les infos enrichies (modèle, moteur, propriétaire).
            Combine les données live (Skyfly) avec le référentiel (SQL).
            Source: référentiel SQL.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "icao24_list": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Liste des codes icao24 (Mode-S hex) à enrichir"
                    }
                },
                "required": ["icao24_list"]
            }
        ),
        
        Tool(
            name="db_get_reference_codes",
            description="""[AircraftDB] Retourne les codes de référence FAA pour les types d'aéronefs et moteurs.
            Utile pour comprendre les valeurs numériques dans les données.
            Source: référentiel SQL.""",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


async def call_aircraftdb_tool(name: str, arguments: dict) -> list[TextContent]:
    """Exécute un outil AircraftDB."""
    db = get_database()
    
    try:
        if name == "db_ingest_faa_data":
            directory = arguments.get("directory", "ReleasableAircraft_dataset/")
            data_dir = Path(__file__).parent.parent / directory
            
            # Exécuter l'ingestion dans un thread pour ne pas bloquer
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, ingest_directory, data_dir, db)
            
            return [TextContent(type="text", text=json.dumps({
                "status": "success",
                "source": "référentiel SQL",
                "result": result
            }, indent=2, default=str))]
        
        elif name == "db_get_stats":
            stats = db.get_stats()
            stats["source"] = "référentiel SQL"
            stats["aircraft_types"] = AIRCRAFT_TYPES
            stats["engine_types"] = ENGINE_TYPES
            stats["weight_classes"] = WEIGHT_CLASSES
            return [TextContent(type="text", text=json.dumps(stats, indent=2))]
        
        elif name == "db_lookup_by_mode_s":
            mode_s_hex = arguments["mode_s_hex"].upper().strip()
            result = db.get_aircraft_by_mode_s_with_details(mode_s_hex)
            
            if result:
                # Enrichir avec les labels lisibles
                if result.get('type_aircraft'):
                    result['type_aircraft_label'] = AIRCRAFT_TYPES.get(result['type_aircraft'], 'Unknown')
                if result.get('type_engine'):
                    result['type_engine_label'] = ENGINE_TYPES.get(result['type_engine'], 'Unknown')
                if result.get('model_weight_class'):
                    result['weight_class_label'] = WEIGHT_CLASSES.get(result['model_weight_class'], result['model_weight_class'])
                result['source'] = 'référentiel SQL'
                return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
            else:
                return [TextContent(type="text", text=json.dumps({
                    "error": f"No aircraft found with Mode-S code: {mode_s_hex}",
                    "source": "référentiel SQL",
                    "hint": "This icao24 may not be a US-registered aircraft (FAA database only contains N-numbers)"
                }, indent=2))]
        
        elif name == "db_lookup_by_registration":
            registration = arguments["registration"].upper().strip()
            result = db.get_aircraft_with_model_info(registration)
            
            if result:
                if result.get('type_aircraft'):
                    result['type_aircraft_label'] = AIRCRAFT_TYPES.get(result['type_aircraft'], 'Unknown')
                if result.get('type_engine'):
                    result['type_engine_label'] = ENGINE_TYPES.get(result['type_engine'], 'Unknown')
                result['source'] = 'référentiel SQL'
                return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
            else:
                return [TextContent(type="text", text=json.dumps({
                    "error": f"No aircraft found with registration: {registration}",
                    "source": "référentiel SQL"
                }, indent=2))]
        
        elif name == "db_search_aircraft":
            limit = arguments.get("limit", 50)
            results = db.search_aircraft_registry(
                registrant_name=arguments.get("registrant_name"),
                city=arguments.get("city"),
                state=arguments.get("state"),
                year_from=arguments.get("year_from"),
                year_to=arguments.get("year_to"),
                type_aircraft=arguments.get("type_aircraft"),
                limit=limit
            )
            return [TextContent(type="text", text=json.dumps({
                "count": len(results),
                "source": "référentiel SQL",
                "results": results
            }, indent=2, default=str))]
        
        elif name == "db_search_models":
            limit = arguments.get("limit", 50)
            results = db.search_aircraft_models(
                manufacturer=arguments.get("manufacturer"),
                model=arguments.get("model"),
                type_aircraft=arguments.get("type_aircraft"),
                num_engines=arguments.get("num_engines"),
                limit=limit
            )
            return [TextContent(type="text", text=json.dumps({
                "count": len(results),
                "source": "référentiel SQL",
                "results": results
            }, indent=2, default=str))]
        
        elif name == "db_get_model_info":
            code = arguments["code"].strip()
            result = db.get_aircraft_model(code)
            
            if result:
                if result.get('type_aircraft'):
                    result['type_aircraft_label'] = AIRCRAFT_TYPES.get(result['type_aircraft'], 'Unknown')
                if result.get('type_engine'):
                    result['type_engine_label'] = ENGINE_TYPES.get(result['type_engine'], 'Unknown')
                result['source'] = 'référentiel SQL'
                return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
            else:
                return [TextContent(type="text", text=json.dumps({
                    "error": f"No model found with code: {code}",
                    "source": "référentiel SQL"
                }, indent=2))]
        
        elif name == "db_get_engine_info":
            code = arguments["code"].strip()
            result = db.get_engine(code)
            
            if result:
                if result.get('type'):
                    result['type_label'] = ENGINE_TYPES.get(result['type'], 'Unknown')
                result['source'] = 'référentiel SQL'
                return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
            else:
                return [TextContent(type="text", text=json.dumps({
                    "error": f"No engine found with code: {code}",
                    "source": "référentiel SQL"
                }, indent=2))]
        
        elif name == "db_sql_query":
            query = arguments["query"]
            results = db.execute_query(query)
            return [TextContent(type="text", text=json.dumps({
                "count": len(results),
                "source": "référentiel SQL",
                "results": results
            }, indent=2, default=str))]
        
        elif name == "db_enrich_live_aircraft":
            icao24_list = arguments["icao24_list"]
            enriched = []
            
            for icao24 in icao24_list[:50]:  # Limiter à 50
                result = db.get_aircraft_by_mode_s_with_details(icao24.upper())
                if result:
                    enriched.append({
                        "icao24": icao24,
                        "found": True,
                        "registration": result.get("n_number"),
                        "manufacturer": result.get("model_manufacturer"),
                        "model": result.get("model_name"),
                        "type_aircraft": AIRCRAFT_TYPES.get(result.get("type_aircraft"), "Unknown"),
                        "num_engines": result.get("model_num_engines"),
                        "weight_class": result.get("model_weight_class"),
                        "owner": result.get("registrant_name"),
                        "city": result.get("city"),
                        "state": result.get("state")
                    })
                else:
                    enriched.append({
                        "icao24": icao24,
                        "found": False,
                        "reason": "Not in FAA registry (non-US aircraft?)"
                    })
            
            return [TextContent(type="text", text=json.dumps({
                "count": len(enriched),
                "found": sum(1 for e in enriched if e["found"]),
                "not_found": sum(1 for e in enriched if not e["found"]),
                "source": "référentiel SQL",
                "results": enriched
            }, indent=2, default=str))]
        
        elif name == "db_get_reference_codes":
            return [TextContent(type="text", text=json.dumps({
                "source": "référentiel SQL",
                "aircraft_types": AIRCRAFT_TYPES,
                "engine_types": ENGINE_TYPES,
                "weight_classes": WEIGHT_CLASSES,
                "registrant_types": {
                    1: "Individual",
                    2: "Partnership",
                    3: "Corporation",
                    4: "Co-Owned",
                    5: "Government",
                    7: "LLC",
                    8: "Non-Citizen Corporation",
                    9: "Non-Citizen Co-Owned"
                }
            }, indent=2))]
        
        else:
            return [TextContent(type="text", text=json.dumps({
                "error": f"Unknown AircraftDB tool: {name}"
            }, indent=2))]
    
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "error": str(e),
            "tool": name,
            "source": "référentiel SQL"
        }, indent=2))]

