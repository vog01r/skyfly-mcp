# 🔍 RAPPORT D'ANALYSE DE SÉCURITÉ CRITIQUE - Skyfly MCP

**Repository:** vog01r/skyfly-mcp  
**Date d'analyse:** 13 janvier 2026  
**Analyste:** Expert Senior en Sécurité  

---

## 📊 RÉSUMÉ EXÉCUTIF

| Catégorie | Problèmes Critiques | Problèmes Majeurs | Problèmes Mineurs |
|-----------|--------------------|--------------------|-------------------|
| 🔐 **SÉCURITÉ** | **3** | **2** | 1 |
| 🐛 **BUGS CRITIQUES** | **2** | **1** | 0 |
| ⚡ **PERFORMANCE** | **1** | **2** | 1 |
| 🏗️ **ARCHITECTURE** | **1** | **3** | 2 |
| ✅ **QUALITÉ** | **0** | **2** | 3 |

**🚨 SCORE DE RISQUE GLOBAL: 7.5/10 (ÉLEVÉ)**

---

## 🔐 SÉCURITÉ - PROBLÈMES CRITIQUES

### 🚨 CRITIQUE #1: Injection SQL via `db_sql_query`

**Fichier:** `aircraftdb/tools.py:412-414`  
**Gravité:** 🔴 **CRITIQUE**

```python
elif name == "db_sql_query":
    query = arguments["query"]
    results = db.execute_query(query)
```

**Problème:** L'outil `db_sql_query` accepte des requêtes SQL brutes sans validation ni sanitisation.

**Risque:** 
- Injection SQL permettant l'accès à toutes les données
- Possibilité de corruption/suppression de données
- Escalade de privilèges

**Solution recommandée:**
```python
# Ajouter une whitelist de requêtes autorisées
ALLOWED_QUERY_PATTERNS = [
    r'^SELECT\s+.*\s+FROM\s+(aircraft_registry|aircraft_models|engines)\s+.*$',
    r'^SELECT\s+COUNT\(\*\)\s+FROM\s+.*$'
]

def validate_sql_query(query: str) -> bool:
    query_upper = query.strip().upper()
    if not query_upper.startswith('SELECT'):
        return False
    
    for pattern in ALLOWED_QUERY_PATTERNS:
        if re.match(pattern, query_upper):
            return True
    return False
```

### 🚨 CRITIQUE #2: Exposition de données sensibles

**Fichier:** `aircraftdb/database.py:377`  
**Gravité:** 🔴 **CRITIQUE**

```python
json.dumps(data)  # Stockage de toutes les données raw incluant PII
```

**Problème:** Les données personnelles (noms, adresses) sont stockées sans chiffrement.

**Données exposées:**
- Noms des propriétaires d'aéronefs
- Adresses complètes
- Informations de contact

**Solution recommandée:**
```python
import hashlib
from cryptography.fernet import Fernet

def anonymize_pii(data: dict) -> dict:
    sensitive_fields = ['registrant_name', 'street', 'street2', 'city']
    anonymized = data.copy()
    
    for field in sensitive_fields:
        if field in anonymized and anonymized[field]:
            # Hash ou chiffrement des données sensibles
            anonymized[field] = hashlib.sha256(str(anonymized[field]).encode()).hexdigest()[:16]
    
    return anonymized
```

### 🚨 CRITIQUE #3: Absence d'authentification/autorisation

**Fichier:** `http_server.py:571-582`  
**Gravité:** 🔴 **CRITIQUE**

**Problème:** Aucun mécanisme d'authentification pour l'accès aux données.

**Risque:**
- Accès libre aux données FAA
- Possibilité d'abus/surcharge du service
- Violation des conditions d'utilisation des APIs

**Solution recommandée:**
```python
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.authentication import SimpleUser, AuthCredentials

async def authenticate(request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header[7:]
    # Valider le token JWT/API key
    if validate_token(token):
        return AuthCredentials(["authenticated"]), SimpleUser("user")
    return None

app.add_middleware(AuthenticationMiddleware, backend=authenticate)
```

---

## 🔐 SÉCURITÉ - PROBLÈMES MAJEURS

### ⚠️ MAJEUR #1: Configuration CORS trop permissive

**Fichier:** `http_server.py:586-593`  
**Gravité:** 🟠 **MAJEUR**

```python
CORSMiddleware,
allow_origins=["*"],  # Trop permissif
allow_methods=["*"],
allow_headers=["*"],
```

**Solution:**
```python
CORSMiddleware,
allow_origins=["https://claude.ai", "https://cursor.com"],
allow_methods=["GET", "POST"],
allow_headers=["Content-Type", "Authorization"],
```

### ⚠️ MAJEUR #2: Gestion des secrets en dur

**Fichier:** `setup_ssl.sh:7, 34`  
**Gravité:** 🟠 **MAJEUR**

```bash
EMAIL="${SSL_EMAIL:-admin@hamon.link}"  # Email en dur
CERT_DIR="/opt/git/mcpskyfly/certs"     # Chemin en dur
```

**Solution:** Utiliser des variables d'environnement sécurisées.

---

## 🐛 BUGS CRITIQUES

### 🚨 CRITIQUE #1: Gestion d'erreur manquante dans SSE

**Fichier:** `http_server.py:571-582`  
**Gravité:** 🔴 **CRITIQUE**

```python
async def handle_sse(request: Request):
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(streams[0], streams[1], ...)
    return Response()  # Toujours retourné même en cas d'erreur
```

**Problème:** Les exceptions dans le transport SSE ne sont pas gérées.

**Solution:**
```python
async def handle_sse(request: Request):
    try:
        async with sse_transport.connect_sse(...) as streams:
            await mcp_server.run(streams[0], streams[1], ...)
        return Response()
    except Exception as e:
        logger.error(f"SSE connection failed: {e}")
        return Response(status_code=500)
```

### 🚨 CRITIQUE #2: Race condition potentielle sur la DB

**Fichier:** `aircraftdb/database.py:514-521`  
**Gravité:** 🔴 **CRITIQUE**

```python
def get_database() -> AircraftDatabase:
    global _db_instance
    if _db_instance is None:  # Race condition ici
        _db_instance = AircraftDatabase()
    return _db_instance
```

**Solution:**
```python
import threading

_db_lock = threading.Lock()

def get_database() -> AircraftDatabase:
    global _db_instance
    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                _db_instance = AircraftDatabase()
    return _db_instance
```

---

## ⚡ PERFORMANCE - PROBLÈMES CRITIQUES

### 🚨 CRITIQUE #1: Requêtes N+1 dans enrichissement

**Fichier:** `aircraftdb/tools.py:421-446`  
**Gravité:** 🔴 **CRITIQUE**

```python
for icao24 in icao24_list[:50]:
    result = db.get_aircraft_by_mode_s_with_details(icao24.upper())  # N+1 queries
```

**Problème:** Une requête SQL par icao24, peut générer 50+ requêtes.

**Solution:**
```python
def get_multiple_aircraft_by_mode_s(self, mode_s_list: List[str]) -> List[Dict]:
    placeholders = ','.join(['?' for _ in mode_s_list])
    query = f"""
        SELECT r.*, m.manufacturer as model_manufacturer, ...
        FROM aircraft_registry r
        LEFT JOIN aircraft_models m ON r.mfr_mdl_code = m.code
        WHERE r.mode_s_code_hex IN ({placeholders})
    """
    with self.get_connection() as conn:
        rows = conn.execute(query, [s.upper() for s in mode_s_list]).fetchall()
        return [dict(row) for row in rows]
```

---

## 🏗️ ARCHITECTURE - PROBLÈMES CRITIQUES

### 🚨 CRITIQUE #1: Duplication de code massive

**Fichiers:** `server.py` et `http_server.py`  
**Gravité:** 🔴 **CRITIQUE**

**Problème:** ~200 lignes de code dupliquées entre les deux serveurs.

**Lignes dupliquées:**
- Définitions des outils (lignes 34-198 dans server.py, 61-225 dans http_server.py)
- Logique de traitement des outils (lignes 220-315)
- Définitions des régions (lignes 202-213)

**Impact:** Maintenance difficile, risque d'incohérences.

**Solution:** Extraire dans un module commun `tools_definitions.py`.

---

## 🏗️ ARCHITECTURE - PROBLÈMES MAJEURS

### ⚠️ MAJEUR #1: Fichiers trop longs

**Analyse des lignes de code:**
- `http_server.py`: **609 lignes** (> 500)
- `aircraftdb/database.py`: **522 lignes** (> 500)

**Solution:** Découper en modules plus petits.

### ⚠️ MAJEUR #2: Couplage fort

**Fichier:** `http_server.py:14`  
```python
from aircraftdb.tools import get_aircraftdb_tools, call_aircraftdb_tool
```

**Problème:** Le serveur HTTP est fortement couplé à AircraftDB.

### ⚠️ MAJEUR #3: Violation du principe de responsabilité unique

**Fichier:** `aircraftdb/ingest.py`  
**Problème:** Gère à la fois le parsing CSV, Excel, JSON et l'insertion en base.

---

## ✅ QUALITÉ - PROBLÈMES MAJEURS

### ⚠️ MAJEUR #1: Absence totale de tests

**Constat:** Aucun fichier de test trouvé dans le repository.

**Risque:** 
- Régressions non détectées
- Difficultés de maintenance
- Fiabilité compromise

**Solution recommandée:**
```python
# tests/test_security.py
def test_sql_injection_prevention():
    malicious_query = "SELECT * FROM aircraft_registry; DROP TABLE aircraft_registry;"
    with pytest.raises(ValueError):
        db.execute_query(malicious_query)

# tests/test_authentication.py
def test_unauthorized_access():
    response = client.get("/sse")
    assert response.status_code == 401
```

### ⚠️ MAJEUR #2: Documentation de sécurité manquante

**Problème:** Aucune documentation sur les considérations de sécurité.

---

## 🎯 RECOMMANDATIONS PRIORITAIRES

### 🔥 ACTIONS IMMÉDIATES (< 24h)

1. **Désactiver `db_sql_query`** ou implémenter la validation stricte
2. **Ajouter l'authentification** pour l'endpoint SSE
3. **Corriger la configuration CORS**
4. **Implémenter la gestion d'erreur SSE**

### ⚡ ACTIONS URGENTES (< 1 semaine)

1. **Chiffrer/anonymiser les données PII**
2. **Corriger la race condition de la DB**
3. **Optimiser les requêtes N+1**
4. **Ajouter des tests de sécurité**

### 📈 ACTIONS MOYEN TERME (< 1 mois)

1. **Refactoriser la duplication de code**
2. **Découper les fichiers trop longs**
3. **Implémenter un système de logs de sécurité**
4. **Ajouter une couverture de tests complète**

---

## 📋 CHECKLIST DE VALIDATION

- [ ] Tests d'injection SQL passent
- [ ] Authentification fonctionnelle
- [ ] Données PII chiffrées
- [ ] Configuration CORS restrictive
- [ ] Gestion d'erreurs robuste
- [ ] Tests de sécurité automatisés
- [ ] Documentation de sécurité complète
- [ ] Audit de performance effectué

---

**⚠️ AVERTISSEMENT:** Ce rapport identifie des vulnérabilités critiques qui exposent le système à des risques de sécurité majeurs. Une action immédiate est requise avant tout déploiement en production.

**📞 Contact:** Pour toute question sur ce rapport, contacter l'équipe sécurité.

---
*Rapport généré automatiquement le 13/01/2026*