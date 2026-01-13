# Gestion mémoire inefficace et risque de déni de service

**Type:** performance
**Sévérité:** high
**Fichier:** opensky_client.py, server.py, http_server.py

## Description

Le code présente plusieurs problèmes de performance qui peuvent conduire à une consommation excessive de mémoire et des dénis de service, particulièrement lors de requêtes sur de grandes zones géographiques ou des périodes étendues.

**Problèmes identifiés :**

1. **Chargement complet en mémoire** (ligne 244-246, opensky_client.py) :
   ```python
   states = [self._parse_state_vector(s).to_dict() for s in data["states"]]
   ```
   Toutes les données sont chargées en mémoire d'un coup, sans limite de taille

2. **Limites arbitraires et incohérentes** :
   - server.py ligne 237-239 : Limite à 50 états pour `get_aircraft_states`
   - http_server.py ligne 310-312 : Limite à 100 états pour `get_aircraft_in_region`
   - Aucune limite pour les autres endpoints (arrivals, departures, flights)

3. **Pas de pagination** : Les grandes requêtes peuvent retourner des milliers d'enregistrements sans pagination

4. **Timeout insuffisant** (ligne 145, opensky_client.py) :
   ```python
   async with httpx.AsyncClient(timeout=30.0) as client:
   ```
   30 secondes peuvent être insuffisantes pour de grandes requêtes

5. **Pas de cache** : Chaque requête refait appel à l'API externe, même pour des données récentes

6. **Memory leak potentiel** dans les connexions SQLite : Les connexions ne sont pas toujours correctement fermées en cas d'exception

## Suggestion

1. **Implémenter la pagination** :
   ```python
   def get_states_paginated(self, page_size: int = 100, page: int = 0):
       offset = page * page_size
       # Limiter les résultats avec LIMIT/OFFSET
   ```

2. **Ajouter un système de cache** :
   ```python
   from functools import lru_cache
   from datetime import datetime, timedelta
   
   @lru_cache(maxsize=128)
   async def get_states_cached(self, bbox_key: str, max_age: int = 60):
       # Cache avec TTL pour éviter les requêtes répétées
   ```

3. **Streaming des données** :
   ```python
   async def stream_states(self, bbox):
       async for batch in self._get_states_batched(bbox, batch_size=100):
           yield batch
   ```

4. **Limites globales cohérentes** :
   ```python
   MAX_RESULTS_PER_REQUEST = 1000
   DEFAULT_PAGE_SIZE = 100
   MAX_TIME_RANGE_HOURS = 24
   ```

5. **Gestion mémoire améliorée** :
   ```python
   # Utiliser des générateurs au lieu de listes
   def parse_states_generator(self, states_data):
       for state in states_data:
           yield self._parse_state_vector(state).to_dict()
   ```