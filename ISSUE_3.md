# Gestion d'erreurs incohérente et exceptions non gérées

**Type:** architecture
**Sévérité:** high
**Fichier:** server.py, http_server.py, aircraftdb/tools.py, opensky_client.py

## Description

Le code présente une gestion d'erreurs incohérente avec plusieurs exceptions non gérées qui peuvent causer des crashes du serveur et exposer des informations sensibles. La gestion des erreurs varie entre les modules sans stratégie unifiée.

**Problèmes identifiés :**

1. **Exceptions non gérées dans les validations** :
   - server.py ligne 334 : `get_flights_from_interval` peut lever une exception si `end - begin > 7200` mais d'autres outils n'ont pas cette validation
   - Pas de validation des paramètres bbox dans `get_aircraft_states`
   - Aucune validation des timestamps (peuvent être négatifs ou dans le futur)

2. **Gestion d'erreurs incohérente entre modules** :
   ```python
   # server.py ligne 319-320 : Catch générique
   except Exception as e:
       return [TextContent(type="text", text=json.dumps({"error": str(e)}, indent=2))]
   
   # aircraftdb/tools.py ligne 479-484 : Plus détaillé mais différent format
   except Exception as e:
       return [TextContent(type="text", text=json.dumps({
           "error": str(e), "tool": name, "source": "référentiel SQL"
       }, indent=2))]
   ```

3. **Exposition d'informations sensibles** :
   - Les stack traces complètes peuvent être exposées via `str(e)`
   - Pas de logging structuré des erreurs
   - Les erreurs de base de données peuvent révéler la structure interne

4. **Pas de circuit breaker** pour l'API OpenSky :
   - Si l'API externe est en panne, le serveur continue à faire des requêtes
   - Pas de fallback ou de mode dégradé

5. **Ressources non libérées** :
   - opensky_client.py ligne 145 : Les connexions HTTP peuvent ne pas être fermées en cas d'exception
   - database.py : Les connexions SQLite peuvent fuir en cas d'erreur

6. **Validation insuffisante des entrées** :
   - Pas de validation des codes ICAO24 (format hexadécimal)
   - Pas de validation des codes d'aéroport ICAO
   - Les timestamps ne sont pas validés

## Suggestion

1. **Créer une classe d'erreurs personnalisées** :
   ```python
   class SkyflyError(Exception):
       def __init__(self, message: str, error_code: str, details: dict = None):
           self.message = message
           self.error_code = error_code
           self.details = details or {}
   
   class ValidationError(SkyflyError):
       pass
   
   class ExternalAPIError(SkyflyError):
       pass
   ```

2. **Décorateur pour la gestion d'erreurs unifiée** :
   ```python
   def handle_tool_errors(func):
       async def wrapper(name: str, arguments: dict):
           try:
               return await func(name, arguments)
           except ValidationError as e:
               return [TextContent(type="text", text=json.dumps({
                   "error": e.message,
                   "error_code": e.error_code,
                   "tool": name
               }, indent=2))]
           except Exception as e:
               logger.error(f"Unexpected error in tool {name}: {e}")
               return [TextContent(type="text", text=json.dumps({
                   "error": "Internal server error",
                   "error_code": "INTERNAL_ERROR"
               }, indent=2))]
       return wrapper
   ```

3. **Validation centralisée** :
   ```python
   def validate_icao24(icao24: str) -> str:
       if not re.match(r'^[0-9A-Fa-f]{6}$', icao24):
           raise ValidationError("Invalid ICAO24 format", "INVALID_ICAO24")
       return icao24.upper()
   
   def validate_timestamp_range(begin: int, end: int, max_range: int):
       if end <= begin:
           raise ValidationError("End time must be after begin time", "INVALID_TIME_RANGE")
       if end - begin > max_range:
           raise ValidationError(f"Time range exceeds maximum of {max_range} seconds", "TIME_RANGE_TOO_LARGE")
   ```

4. **Circuit breaker pour l'API externe** :
   ```python
   class CircuitBreaker:
       def __init__(self, failure_threshold: int = 5, timeout: int = 60):
           self.failure_count = 0
           self.failure_threshold = failure_threshold
           self.timeout = timeout
           self.last_failure_time = None
   ```