# 🛡️ CORRECTIONS DE SÉCURITÉ IMMÉDIATES

## 🚨 PATCH CRITIQUE #1: Protection Injection SQL

**Fichier à modifier:** `aircraftdb/database.py`

```python
# AVANT (VULNÉRABLE)
def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
    if not query.strip().upper().startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed")
    
    with self.get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

# APRÈS (SÉCURISÉ)
import re
import sqlparse

def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
    """Exécute une requête SQL SELECT avec validation stricte."""
    # Nettoyer et valider la requête
    query = query.strip()
    if not query:
        raise ValueError("Empty query not allowed")
    
    # Parser la requête SQL
    try:
        parsed = sqlparse.parse(query)
        if not parsed or len(parsed) != 1:
            raise ValueError("Only single SQL statements allowed")
        
        stmt = parsed[0]
        if stmt.get_type() != 'SELECT':
            raise ValueError("Only SELECT queries are allowed")
        
        # Vérifier les mots-clés dangereux
        dangerous_keywords = {
            'DROP', 'DELETE', 'UPDATE', 'INSERT', 'CREATE', 'ALTER', 
            'TRUNCATE', 'REPLACE', 'PRAGMA', 'ATTACH', 'DETACH'
        }
        
        query_upper = query.upper()
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                raise ValueError(f"Dangerous keyword '{keyword}' not allowed")
        
        # Limiter les fonctions système
        if any(func in query_upper for func in ['LOAD_EXTENSION', 'SYSTEM', 'EXEC']):
            raise ValueError("System functions not allowed")
            
    except Exception as e:
        logger.error(f"SQL validation failed: {e}")
        raise ValueError("Invalid SQL query")
    
    # Limiter le nombre de résultats
    if 'LIMIT' not in query_upper:
        query += ' LIMIT 1000'
    
    with self.get_connection() as conn:
        try:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"SQL execution error: {e}")
            raise ValueError("Query execution failed")
```

## 🚨 PATCH CRITIQUE #2: CORS Sécurisé

**Fichier à modifier:** `http_server.py`

```python
# AVANT (DANGEREUX)
middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

# APRÈS (SÉCURISÉ)
import os

# Configuration CORS basée sur l'environnement
def get_cors_origins():
    env_origins = os.getenv("ALLOWED_ORIGINS", "")
    if env_origins:
        return [origin.strip() for origin in env_origins.split(",")]
    
    # Valeurs par défaut sécurisées pour développement
    return [
        "https://claude.ai",
        "https://cursor.sh", 
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "Accept"],
        allow_credentials=False,
        max_age=3600,
    )
]
```

## 🚨 PATCH CRITIQUE #3: Rate Limiting

**Nouveau fichier:** `rate_limiter.py`

```python
import time
from collections import defaultdict, deque
from typing import Dict, Tuple
import asyncio

class RateLimiter:
    """Rate limiter simple basé sur sliding window."""
    
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = defaultdict(deque)
        self._lock = asyncio.Lock()
    
    async def is_allowed(self, client_id: str) -> Tuple[bool, dict]:
        """Vérifie si la requête est autorisée."""
        async with self._lock:
            now = time.time()
            client_requests = self.requests[client_id]
            
            # Nettoyer les anciennes requêtes
            while client_requests and client_requests[0] < now - self.window_seconds:
                client_requests.popleft()
            
            # Vérifier la limite
            if len(client_requests) >= self.max_requests:
                return False, {
                    "error": "Rate limit exceeded",
                    "limit": self.max_requests,
                    "window": self.window_seconds,
                    "retry_after": int(client_requests[0] + self.window_seconds - now)
                }
            
            # Ajouter la requête actuelle
            client_requests.append(now)
            
            return True, {
                "requests_remaining": self.max_requests - len(client_requests),
                "reset_time": int(now + self.window_seconds)
            }

# Middleware pour Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, rate_limiter: RateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter
    
    async def dispatch(self, request, call_next):
        # Identifier le client (IP + User-Agent pour plus de précision)
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent", "")[:50]
        client_id = f"{client_ip}:{hash(user_agent)}"
        
        # Vérifier le rate limit
        allowed, info = await self.rate_limiter.is_allowed(client_id)
        
        if not allowed:
            return JSONResponse(
                status_code=429,
                content=info,
                headers={
                    "Retry-After": str(info["retry_after"]),
                    "X-RateLimit-Limit": str(self.rate_limiter.max_requests),
                    "X-RateLimit-Window": str(self.rate_limiter.window_seconds)
                }
            )
        
        response = await call_next(request)
        
        # Ajouter headers informatifs
        response.headers["X-RateLimit-Remaining"] = str(info["requests_remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset_time"])
        
        return response
```

**Modification dans `http_server.py`:**

```python
from rate_limiter import RateLimiter, RateLimitMiddleware

# Créer le rate limiter
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)  # 100 req/min

# Ajouter le middleware
middleware = [
    Middleware(RateLimitMiddleware, rate_limiter=rate_limiter),
    Middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins(),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "Accept"],
        allow_credentials=False,
    )
]
```

## 🚨 PATCH CRITIQUE #4: Validation des Entrées

**Nouveau fichier:** `validators.py`

```python
import re
from typing import Optional, Union

class ValidationError(ValueError):
    """Erreur de validation des données d'entrée."""
    pass

def validate_mode_s_hex(value: str) -> str:
    """Valide un code Mode-S hexadécimal."""
    if not isinstance(value, str):
        raise ValidationError("Mode-S code must be a string")
    
    cleaned = value.upper().strip()
    if not re.match(r'^[0-9A-F]{6}$', cleaned):
        raise ValidationError("Mode-S code must be 6 hexadecimal digits")
    
    return cleaned

def validate_icao_airport(value: str) -> str:
    """Valide un code ICAO d'aéroport."""
    if not isinstance(value, str):
        raise ValidationError("Airport code must be a string")
    
    cleaned = value.upper().strip()
    if not re.match(r'^[A-Z]{4}$', cleaned):
        raise ValidationError("Airport code must be 4 uppercase letters")
    
    return cleaned

def validate_timestamp(value: Union[int, str]) -> int:
    """Valide un timestamp Unix."""
    try:
        timestamp = int(value)
    except (ValueError, TypeError):
        raise ValidationError("Timestamp must be an integer")
    
    # Vérifier que le timestamp est raisonnable (entre 2020 et 2030)
    if timestamp < 1577836800 or timestamp > 1893456000:
        raise ValidationError("Timestamp out of reasonable range")
    
    return timestamp

def validate_region(value: str) -> str:
    """Valide une région prédéfinie."""
    if not isinstance(value, str):
        raise ValidationError("Region must be a string")
    
    cleaned = value.lower().strip()
    valid_regions = {
        'france', 'germany', 'switzerland', 'spain', 'italy', 
        'uk', 'europe', 'usa_east', 'usa_west', 'world'
    }
    
    if cleaned not in valid_regions:
        raise ValidationError(f"Invalid region. Must be one of: {', '.join(valid_regions)}")
    
    return cleaned

def validate_sql_query(query: str) -> str:
    """Validation basique d'une requête SQL."""
    if not isinstance(query, str):
        raise ValidationError("Query must be a string")
    
    cleaned = query.strip()
    if not cleaned:
        raise ValidationError("Query cannot be empty")
    
    if len(cleaned) > 5000:
        raise ValidationError("Query too long (max 5000 characters)")
    
    # Vérifications basiques
    query_upper = cleaned.upper()
    
    # Doit commencer par SELECT
    if not query_upper.startswith('SELECT'):
        raise ValidationError("Only SELECT queries are allowed")
    
    # Mots-clés interdits
    forbidden = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'CREATE', 'ALTER', 'PRAGMA']
    for word in forbidden:
        if word in query_upper:
            raise ValidationError(f"Forbidden keyword: {word}")
    
    return cleaned
```

## 🚨 PATCH CRITIQUE #5: Gestion d'Erreurs Sécurisée

**Nouveau fichier:** `error_handlers.py`

```python
import logging
from starlette.responses import JSONResponse
from starlette.requests import Request

logger = logging.getLogger(__name__)

async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Gestionnaire d'erreur générique qui ne fuit pas d'informations."""
    
    # Logger l'erreur complète pour le debug
    logger.error(f"Unhandled error in {request.url.path}: {exc}", exc_info=True)
    
    # Réponse générique pour l'utilisateur
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
            "request_id": id(request)  # Pour tracer dans les logs
        }
    )

async def validation_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Gestionnaire pour les erreurs de validation."""
    return JSONResponse(
        status_code=400,
        content={
            "error": "Validation error",
            "message": str(exc)
        }
    )

async def not_found_handler(request: Request, exc) -> JSONResponse:
    """Gestionnaire pour les ressources non trouvées."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not found",
            "message": "The requested resource was not found"
        }
    )

# À ajouter dans http_server.py
from starlette.exceptions import HTTPException
from error_handlers import generic_error_handler, validation_error_handler

app.add_exception_handler(500, generic_error_handler)
app.add_exception_handler(ValueError, validation_error_handler)
app.add_exception_handler(HTTPException, not_found_handler)
```

## 🔧 SCRIPT D'APPLICATION DES PATCHES

**Nouveau fichier:** `apply_security_patches.py`

```python
#!/usr/bin/env python3
"""
Script pour appliquer automatiquement les patches de sécurité critiques.
"""

import os
import shutil
from pathlib import Path

def backup_file(file_path: Path):
    """Crée une sauvegarde du fichier."""
    backup_path = file_path.with_suffix(file_path.suffix + '.backup')
    shutil.copy2(file_path, backup_path)
    print(f"✅ Backup created: {backup_path}")

def apply_patches():
    """Applique les patches de sécurité."""
    
    print("🛡️  Application des patches de sécurité critiques...")
    
    # 1. Sauvegarder les fichiers originaux
    files_to_backup = [
        "aircraftdb/database.py",
        "http_server.py"
    ]
    
    for file_path in files_to_backup:
        path = Path(file_path)
        if path.exists():
            backup_file(path)
    
    # 2. Créer les nouveaux fichiers de sécurité
    security_files = [
        "rate_limiter.py",
        "validators.py", 
        "error_handlers.py"
    ]
    
    for file_name in security_files:
        if not Path(file_name).exists():
            print(f"⚠️  Veuillez créer manuellement: {file_name}")
        else:
            print(f"✅ Fichier de sécurité trouvé: {file_name}")
    
    print("\n🔧 Patches à appliquer manuellement:")
    print("1. Modifier aircraftdb/database.py - méthode execute_query")
    print("2. Modifier http_server.py - configuration CORS")
    print("3. Ajouter rate_limiter.py au middleware")
    print("4. Intégrer validators.py dans les outils MCP")
    print("5. Ajouter error_handlers.py à l'application")
    
    print("\n✅ Script terminé. Vérifiez les modifications avant de redémarrer le serveur.")

if __name__ == "__main__":
    apply_patches()
```

## 📋 CHECKLIST DE DÉPLOIEMENT SÉCURISÉ

- [ ] **SQL Injection**: Patch appliqué dans `database.py`
- [ ] **CORS**: Configuration restrictive dans `http_server.py`
- [ ] **Rate Limiting**: Middleware ajouté
- [ ] **Validation**: Intégrée dans tous les outils MCP
- [ ] **Gestion d'erreurs**: Handlers sécurisés ajoutés
- [ ] **Variables d'environnement**: Credentials externalisés
- [ ] **Tests**: Vérification du bon fonctionnement
- [ ] **Monitoring**: Logs de sécurité activés
- [ ] **Documentation**: Mise à jour des procédures

## 🚨 ACTIONS POST-PATCH

1. **Tester** toutes les fonctionnalités critiques
2. **Monitorer** les logs pour détecter les tentatives d'attaque
3. **Mettre à jour** la documentation de sécurité
4. **Planifier** une revue de code complète dans 30 jours
5. **Former** l'équipe sur les nouvelles mesures de sécurité

---

**⚠️ IMPORTANT**: Ces patches corrigent les vulnérabilités critiques identifiées. Testez en environnement de développement avant la production.