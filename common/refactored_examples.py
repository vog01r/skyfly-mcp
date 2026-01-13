"""
Exemples de refactorisation utilisant les utilitaires communs.
Ces exemples montrent comment remplacer le code dupliqué par des appels aux utilitaires.
"""

import json
from typing import Dict, Any, List, Optional
from mcp.types import TextContent

from .utils import ResponseFormatter, ParameterValidator, DataConverter, TimestampUtils, HTTPClientUtils


# ============ EXEMPLES DE REFACTORISATION HTTP_SERVER.PY ============

class RefactoredHttpServerExamples:
    """Exemples de refactorisation pour http_server.py"""
    
    @staticmethod
    def get_current_timestamp_refactored(arguments: dict) -> List[TextContent]:
        """Version refactorisée de get_current_timestamp."""
        # AVANT (http_server.py lignes 304-310):
        # current = int(time.time())
        # return [TextContent(type="text", text=json.dumps({
        #     "timestamp": current,
        #     "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(current)),
        #     "hint": "Use this timestamp for 'end' parameter..."
        # }, indent=2))]
        
        # APRÈS:
        return ResponseFormatter.success_response(
            TimestampUtils.timestamp_info(),
            source="system"
        )
    
    @staticmethod
    def get_aircraft_states_refactored(arguments: dict, opensky_api) -> List[TextContent]:
        """Version refactorisée de get_aircraft_states avec validation."""
        try:
            # Validation des paramètres bbox
            bbox_params = ["min_latitude", "max_latitude", "min_longitude", "max_longitude"]
            if all(k in arguments for k in bbox_params):
                bbox = tuple(arguments[k] for k in bbox_params)
                validation_error = ParameterValidator.validate_bbox(bbox)
                if validation_error:
                    return ResponseFormatter.error_response(
                        validation_error,
                        tool_name="get_aircraft_states",
                        source="validation"
                    )
            
            # Logique existante...
            # result = await opensky_api.get_states(...)
            
            # AVANT (http_server.py lignes 255-260):
            # if result and result.get("states"):
            #     states_count = len(result["states"])
            #     if states_count > 50:
            #         result["states"] = result["states"][:50]
            #         result["note"] = f"Showing 50 of {states_count} aircraft..."
            
            # APRÈS:
            # if result and result.get("states"):
            #     states_count = len(result["states"])
            #     extra_fields = {}
            #     if states_count > 50:
            #         result["states"] = result["states"][:50]
            #         extra_fields["note"] = f"Showing 50 of {states_count} aircraft. Use a smaller bounding box for complete data."
            #     
            #     return ResponseFormatter.success_response(
            #         result,
            #         source="OpenSky API",
            #         extra_fields=extra_fields
            #     )
            
        except Exception as e:
            return ResponseFormatter.error_response(
                str(e),
                tool_name="get_aircraft_states",
                source="OpenSky API"
            )
    
    @staticmethod
    def get_arrivals_by_airport_refactored(arguments: dict, opensky_api) -> List[TextContent]:
        """Version refactorisée avec validation d'intervalle de temps."""
        try:
            # Validation des paramètres requis
            validation_error = ParameterValidator.validate_required_params(
                arguments, ["airport", "begin", "end"]
            )
            if validation_error:
                return ResponseFormatter.error_response(
                    validation_error,
                    tool_name="get_arrivals_by_airport"
                )
            
            # Validation de l'intervalle de temps (7 jours max)
            interval_error = ParameterValidator.validate_time_interval(
                arguments["begin"], 
                arguments["end"], 
                max_duration=7*24*3600  # 7 jours
            )
            if interval_error:
                return ResponseFormatter.error_response(
                    interval_error,
                    tool_name="get_arrivals_by_airport"
                )
            
            # Logique existante...
            # result = await opensky_api.get_arrivals_by_airport(...)
            
            # AVANT (http_server.py ligne 269):
            # return [TextContent(type="text", text=json.dumps({"arrivals": result, "count": len(result) if result else 0}, indent=2))]
            
            # APRÈS:
            # return ResponseFormatter.success_response(
            #     {"arrivals": result or []},
            #     source="OpenSky API",
            #     count=len(result) if result else 0
            # )
            
        except Exception as e:
            return ResponseFormatter.error_response(
                str(e),
                tool_name="get_arrivals_by_airport",
                source="OpenSky API"
            )


# ============ EXEMPLES DE REFACTORISATION AIRCRAFTDB/TOOLS.PY ============

class RefactoredAircraftDBExamples:
    """Exemples de refactorisation pour aircraftdb/tools.py"""
    
    @staticmethod
    def db_lookup_by_mode_s_refactored(arguments: dict, db) -> List[TextContent]:
        """Version refactorisée de db_lookup_by_mode_s."""
        try:
            # Validation des paramètres
            validation_error = ParameterValidator.validate_required_params(
                arguments, ["mode_s_hex"]
            )
            if validation_error:
                return ResponseFormatter.error_response(
                    validation_error,
                    tool_name="db_lookup_by_mode_s",
                    source="référentiel SQL"
                )
            
            mode_s_hex = DataConverter.clean_string(arguments["mode_s_hex"])
            if not mode_s_hex:
                return ResponseFormatter.error_response(
                    "Mode-S hex code cannot be empty",
                    tool_name="db_lookup_by_mode_s",
                    source="référentiel SQL"
                )
            
            result = db.get_aircraft_by_mode_s_with_details(mode_s_hex.upper())
            
            if result:
                # Enrichissement avec les labels
                from aircraftdb.tools import AIRCRAFT_TYPES, ENGINE_TYPES, WEIGHT_CLASSES
                
                enriched = DataConverter.enrich_with_labels(result, {
                    "type_aircraft": AIRCRAFT_TYPES,
                    "type_engine": ENGINE_TYPES,
                    "model_weight_class": WEIGHT_CLASSES
                })
                
                return ResponseFormatter.success_response(
                    enriched,
                    source="référentiel SQL"
                )
            else:
                return ResponseFormatter.not_found_response(
                    "aircraft",
                    mode_s_hex,
                    source="référentiel SQL",
                    hint="This icao24 may not be a US-registered aircraft (FAA database only contains N-numbers)"
                )
                
        except Exception as e:
            return ResponseFormatter.error_response(
                str(e),
                tool_name="db_lookup_by_mode_s",
                source="référentiel SQL"
            )
    
    @staticmethod
    def db_search_aircraft_refactored(arguments: dict, db) -> List[TextContent]:
        """Version refactorisée de db_search_aircraft."""
        try:
            limit = DataConverter.safe_parse_int(arguments.get("limit"), default=50)
            
            # Validation des paramètres optionnels
            year_from = DataConverter.safe_parse_int(arguments.get("year_from"))
            year_to = DataConverter.safe_parse_int(arguments.get("year_to"))
            
            if year_from and year_to and year_from > year_to:
                return ResponseFormatter.error_response(
                    "year_from must be less than or equal to year_to",
                    tool_name="db_search_aircraft",
                    source="référentiel SQL"
                )
            
            results = db.search_aircraft_registry(
                registrant_name=DataConverter.clean_string(arguments.get("registrant_name")),
                city=DataConverter.clean_string(arguments.get("city")),
                state=DataConverter.clean_string(arguments.get("state")),
                year_from=year_from,
                year_to=year_to,
                type_aircraft=DataConverter.safe_parse_int(arguments.get("type_aircraft")),
                limit=limit
            )
            
            # AVANT (aircraftdb/tools.py lignes 359-363):
            # return [TextContent(type="text", text=json.dumps({
            #     "count": len(results),
            #     "source": "référentiel SQL",
            #     "results": results
            # }, indent=2, default=str))]
            
            # APRÈS:
            return ResponseFormatter.success_response(
                results,
                source="référentiel SQL",
                count=len(results)
            )
            
        except Exception as e:
            return ResponseFormatter.error_response(
                str(e),
                tool_name="db_search_aircraft",
                source="référentiel SQL"
            )


# ============ EXEMPLES DE REFACTORISATION OPENSKY_CLIENT.PY ============

class RefactoredOpenSkyClientExamples:
    """Exemples de refactorisation pour opensky_client.py"""
    
    @staticmethod
    def handle_request_error_refactored(status_code: int, response_text: str):
        """Version refactorisée de la gestion d'erreur HTTP."""
        # AVANT (opensky_client.py lignes 155-158):
        # elif response.status_code == 429:
        #     raise Exception("Rate limit exceeded. Please wait before making more requests.")
        # else:
        #     raise Exception(f"API request failed with status {response.status_code}: {response.text}")
        
        # APRÈS:
        error_message = HTTPClientUtils.handle_http_error(status_code, response_text)
        raise Exception(error_message)
    
    @staticmethod
    def build_params_refactored(
        time_secs: int = 0,
        icao24: Optional[str] = None,
        bbox: Optional[tuple] = None
    ) -> Dict[str, Any]:
        """Version refactorisée de construction des paramètres."""
        # AVANT (opensky_client.py lignes 232-241):
        # params = {}
        # if time_secs > 0:
        #     params["time"] = time_secs
        # if icao24:
        #     params["icao24"] = icao24.lower()
        # if bbox and len(bbox) == 4:
        #     params["lamin"] = bbox[0]
        #     ...
        
        # APRÈS:
        params = {}
        
        if time_secs > 0:
            params["time"] = time_secs
            
        if icao24:
            clean_icao24 = DataConverter.clean_string(icao24)
            if clean_icao24:
                params["icao24"] = clean_icao24.lower()
        
        if bbox:
            validation_error = ParameterValidator.validate_bbox(bbox)
            if validation_error:
                raise ValueError(validation_error)
            params.update({
                "lamin": bbox[0],
                "lamax": bbox[1], 
                "lomin": bbox[2],
                "lomax": bbox[3]
            })
            
        return params


# ============ EXEMPLE D'UTILISATION DANS UN NOUVEAU TOOL ============

def example_new_tool_with_utils(name: str, arguments: dict) -> List[TextContent]:
    """
    Exemple d'un nouveau tool utilisant tous les utilitaires communs.
    Montre les bonnes pratiques pour éviter la duplication de code.
    """
    try:
        # 1. Validation des paramètres requis
        validation_error = ParameterValidator.validate_required_params(
            arguments, ["required_param"]
        )
        if validation_error:
            return ResponseFormatter.error_response(
                validation_error,
                tool_name=name,
                source="validation"
            )
        
        # 2. Nettoyage et conversion des paramètres
        param1 = DataConverter.clean_string(arguments.get("param1"))
        param2 = DataConverter.safe_parse_int(arguments.get("param2"), default=10)
        
        # 3. Validation métier spécifique
        if param2 < 1 or param2 > 100:
            return ResponseFormatter.error_response(
                "param2 must be between 1 and 100",
                tool_name=name,
                source="validation"
            )
        
        # 4. Logique métier
        results = []  # Simulation de traitement
        
        # 5. Enrichissement des données si nécessaire
        enriched_results = [
            DataConverter.enrich_with_labels(result, {"status": {1: "Active", 0: "Inactive"}})
            for result in results
        ]
        
        # 6. Réponse formatée
        return ResponseFormatter.success_response(
            enriched_results,
            source="custom source",
            count=len(enriched_results),
            extra_fields={
                "processing_time": TimestampUtils.current_timestamp(),
                "parameters_used": {"param1": param1, "param2": param2}
            }
        )
        
    except Exception as e:
        return ResponseFormatter.error_response(
            str(e),
            tool_name=name,
            source="processing"
        )