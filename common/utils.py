"""
Utilitaires communs pour la gestion des erreurs, réponses JSON et validation.
Centralise les patterns répétitifs identifiés dans le codebase.
"""

import json
import time
from typing import Any, Dict, List, Optional, Union
from mcp.types import TextContent


class ResponseFormatter:
    """Classe utilitaire pour formater les réponses MCP de manière cohérente."""
    
    @staticmethod
    def success_response(
        data: Any, 
        source: Optional[str] = None,
        count: Optional[int] = None,
        extra_fields: Optional[Dict[str, Any]] = None
    ) -> List[TextContent]:
        """
        Formate une réponse de succès avec un format standardisé.
        
        Args:
            data: Les données à retourner
            source: Source des données (ex: "référentiel SQL", "OpenSky API")
            count: Nombre d'éléments (calculé automatiquement si non fourni)
            extra_fields: Champs supplémentaires à ajouter
        """
        response = {}
        
        # Ajouter la source si fournie
        if source:
            response["source"] = source
            
        # Calculer ou utiliser le count fourni
        if count is not None:
            response["count"] = count
        elif isinstance(data, (list, tuple)):
            response["count"] = len(data)
            
        # Ajouter les données principales
        if isinstance(data, list):
            response["results"] = data
        elif isinstance(data, dict):
            response.update(data)
        else:
            response["data"] = data
            
        # Ajouter les champs supplémentaires
        if extra_fields:
            response.update(extra_fields)
            
        return [TextContent(type="text", text=json.dumps(response, indent=2, default=str))]
    
    @staticmethod
    def error_response(
        error_message: str,
        tool_name: Optional[str] = None,
        source: Optional[str] = None,
        extra_fields: Optional[Dict[str, Any]] = None
    ) -> List[TextContent]:
        """
        Formate une réponse d'erreur avec un format standardisé.
        
        Args:
            error_message: Message d'erreur
            tool_name: Nom de l'outil qui a généré l'erreur
            source: Source des données
            extra_fields: Champs supplémentaires
        """
        response = {"error": error_message}
        
        if tool_name:
            response["tool"] = tool_name
        if source:
            response["source"] = source
        if extra_fields:
            response.update(extra_fields)
            
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    
    @staticmethod
    def not_found_response(
        resource_type: str,
        identifier: str,
        source: Optional[str] = None,
        hint: Optional[str] = None
    ) -> List[TextContent]:
        """
        Formate une réponse pour une ressource non trouvée.
        
        Args:
            resource_type: Type de ressource (ex: "aircraft", "model")
            identifier: Identifiant recherché
            source: Source des données
            hint: Conseil pour l'utilisateur
        """
        response = {
            "error": f"No {resource_type} found with identifier: {identifier}"
        }
        
        if source:
            response["source"] = source
        if hint:
            response["hint"] = hint
            
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


class ParameterValidator:
    """Classe utilitaire pour la validation des paramètres."""
    
    @staticmethod
    def validate_required_params(arguments: Dict[str, Any], required: List[str]) -> Optional[str]:
        """
        Valide que tous les paramètres requis sont présents.
        
        Args:
            arguments: Dictionnaire des arguments
            required: Liste des paramètres requis
            
        Returns:
            Message d'erreur si validation échoue, None sinon
        """
        missing = [param for param in required if param not in arguments or arguments[param] is None]
        if missing:
            return f"Missing required parameters: {', '.join(missing)}"
        return None
    
    @staticmethod
    def validate_time_interval(begin: int, end: int, max_duration: Optional[int] = None) -> Optional[str]:
        """
        Valide un intervalle de temps.
        
        Args:
            begin: Timestamp de début
            end: Timestamp de fin
            max_duration: Durée maximale autorisée en secondes
            
        Returns:
            Message d'erreur si validation échoue, None sinon
        """
        if begin >= end:
            return "Begin timestamp must be less than end timestamp"
            
        if max_duration and (end - begin) > max_duration:
            return f"Time interval must not exceed {max_duration} seconds"
            
        return None
    
    @staticmethod
    def validate_bbox(bbox: tuple) -> Optional[str]:
        """
        Valide une bounding box géographique.
        
        Args:
            bbox: Tuple (min_lat, max_lat, min_lon, max_lon)
            
        Returns:
            Message d'erreur si validation échoue, None sinon
        """
        if len(bbox) != 4:
            return "Bounding box must have 4 values: (min_lat, max_lat, min_lon, max_lon)"
            
        min_lat, max_lat, min_lon, max_lon = bbox
        
        if min_lat >= max_lat:
            return "Minimum latitude must be less than maximum latitude"
        if min_lon >= max_lon:
            return "Minimum longitude must be less than maximum longitude"
        if not (-90 <= min_lat <= 90) or not (-90 <= max_lat <= 90):
            return "Latitude values must be between -90 and 90"
        if not (-180 <= min_lon <= 180) or not (-180 <= max_lon <= 180):
            return "Longitude values must be between -180 and 180"
            
        return None


class DataConverter:
    """Classe utilitaire pour la conversion et l'enrichissement des données."""
    
    @staticmethod
    def safe_parse_int(value: Any, default: Optional[int] = None) -> Optional[int]:
        """Parse une valeur en entier de manière sécurisée."""
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def safe_parse_float(value: Any, default: Optional[float] = None) -> Optional[float]:
        """Parse une valeur en float de manière sécurisée."""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def clean_string(value: Any) -> Optional[str]:
        """Nettoie une chaîne de caractères."""
        if value is None:
            return None
        str_val = str(value).strip()
        return str_val if str_val else None
    
    @staticmethod
    def enrich_with_labels(
        data: Dict[str, Any], 
        label_mappings: Dict[str, Dict[int, str]]
    ) -> Dict[str, Any]:
        """
        Enrichit un dictionnaire avec des labels lisibles.
        
        Args:
            data: Données à enrichir
            label_mappings: Mapping des codes vers les labels
                          ex: {"type_aircraft": {1: "Glider", 4: "Fixed wing single"}}
        """
        enriched = data.copy()
        
        for field, mapping in label_mappings.items():
            if field in data and data[field] is not None:
                code = data[field]
                if code in mapping:
                    enriched[f"{field}_label"] = mapping[code]
                    
        return enriched


class TimestampUtils:
    """Utilitaires pour la gestion des timestamps."""
    
    @staticmethod
    def current_timestamp() -> int:
        """Retourne le timestamp Unix actuel."""
        return int(time.time())
    
    @staticmethod
    def format_timestamp(timestamp: int) -> str:
        """Formate un timestamp en ISO 8601."""
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp))
    
    @staticmethod
    def timestamp_info(timestamp: Optional[int] = None) -> Dict[str, Any]:
        """
        Retourne des informations détaillées sur un timestamp.
        
        Args:
            timestamp: Timestamp à analyser (actuel si None)
        """
        if timestamp is None:
            timestamp = TimestampUtils.current_timestamp()
            
        return {
            "timestamp": timestamp,
            "iso": TimestampUtils.format_timestamp(timestamp),
            "hint": "Use this timestamp for 'end' parameter. Subtract seconds for 'begin' (e.g., 3600 for 1 hour ago)"
        }


class HTTPClientUtils:
    """Utilitaires pour les clients HTTP."""
    
    @staticmethod
    def handle_http_error(status_code: int, response_text: str) -> str:
        """
        Génère un message d'erreur approprié selon le code de statut HTTP.
        
        Args:
            status_code: Code de statut HTTP
            response_text: Texte de la réponse
            
        Returns:
            Message d'erreur formaté
        """
        if status_code == 429:
            return "Rate limit exceeded. Please wait before making more requests."
        elif status_code == 404:
            return "Resource not found."
        elif status_code == 401:
            return "Authentication required."
        elif status_code == 403:
            return "Access forbidden."
        elif status_code >= 500:
            return f"Server error (status {status_code}). Please try again later."
        else:
            return f"API request failed with status {status_code}: {response_text}"