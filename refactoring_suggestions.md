# 🔧 Suggestions de Refactoring

Ce fichier contient des suggestions pour refactoriser les fonctions trop complexes identifiées dans l'analyse.

## Fonctions à Refactoriser

### 1. `aircraftdb/database.py` - `_init_schema()` (131 lignes)

**Problème**: Fonction très longue qui initialise tout le schéma d'un coup.

**Solution**: Diviser en méthodes spécialisées:
```python
def _init_schema(self):
    """Initialise le schéma de la base de données."""
    with self.get_connection() as conn:
        self._create_aircraft_tables(conn)
        self._create_engine_tables(conn)
        self._create_registry_tables(conn)
        self._create_indexes(conn)

def _create_aircraft_tables(self, conn):
    """Crée les tables liées aux aéronefs."""
    # Code pour aircraft_models, aircraft_deregistered

def _create_engine_tables(self, conn):
    """Crée les tables liées aux moteurs."""
    # Code pour engines

def _create_registry_tables(self, conn):
    """Crée les tables du registre."""
    # Code pour aircraft_registry, dealers, custom_data

def _create_indexes(self, conn):
    """Crée les index pour les performances."""
    # Code pour tous les CREATE INDEX
```

### 2. `aircraftdb/tools.py` - `get_aircraftdb_tools()` (227 lignes)

**Problème**: Fonction très longue qui définit tous les outils.

**Solution**: Diviser par catégorie:
```python
def get_aircraftdb_tools() -> List[Tool]:
    """Retourne la liste des outils AircraftDB."""
    tools = []
    tools.extend(_get_ingestion_tools())
    tools.extend(_get_query_tools())
    tools.extend(_get_search_tools())
    tools.extend(_get_utility_tools())
    return tools

def _get_ingestion_tools() -> List[Tool]:
    """Outils d'ingestion de données."""
    # db_ingest_faa_data

def _get_query_tools() -> List[Tool]:
    """Outils de requête."""
    # db_lookup_by_mode_s, db_lookup_by_registration, etc.

def _get_search_tools() -> List[Tool]:
    """Outils de recherche."""
    # db_search_aircraft, db_search_models

def _get_utility_tools() -> List[Tool]:
    """Outils utilitaires."""
    # db_get_stats, db_sql_query, etc.
```

### 3. `aircraftdb/tools.py` - `call_aircraftdb_tool()` (201 lignes, 13 niveaux d'imbrication)

**Problème**: Fonction très longue avec trop d'imbrication.

**Solution**: Dispatcher pattern:
```python
async def call_aircraftdb_tool(name: str, arguments: dict) -> list[TextContent]:
    """Exécute un outil AircraftDB."""
    db = get_database()
    
    try:
        # Dispatcher vers les handlers spécialisés
        if name.startswith("db_ingest"):
            return await _handle_ingestion_tools(name, arguments, db)
        elif name.startswith("db_lookup"):
            return await _handle_lookup_tools(name, arguments, db)
        elif name.startswith("db_search"):
            return await _handle_search_tools(name, arguments, db)
        elif name.startswith("db_get"):
            return await _handle_get_tools(name, arguments, db)
        elif name == "db_sql_query":
            return await _handle_sql_query(arguments, db)
        elif name == "db_enrich_live_aircraft":
            return await _handle_enrich_aircraft(arguments, db)
        else:
            return _error_response(f"Unknown AircraftDB tool: {name}")
    
    except Exception as e:
        return _error_response(str(e), name)

async def _handle_ingestion_tools(name: str, arguments: dict, db) -> list[TextContent]:
    """Gère les outils d'ingestion."""
    # Code pour db_ingest_faa_data

async def _handle_lookup_tools(name: str, arguments: dict, db) -> list[TextContent]:
    """Gère les outils de lookup."""
    # Code pour db_lookup_by_mode_s, db_lookup_by_registration

# etc.
```

### 4. `aircraftdb/ingest.py` - `ingest_directory()` (86 lignes, 8 niveaux d'imbrication)

**Problème**: Fonction complexe qui gère plusieurs formats de fichiers.

**Solution**: Séparer par format:
```python
def ingest_directory(data_dir: Path, database: 'AircraftDatabase') -> Dict[str, Any]:
    """Ingère tous les fichiers supportés d'un répertoire."""
    results = _init_results()
    data_dir = Path(data_dir)
    
    if not data_dir.exists():
        return {'error': f'Directory not found: {data_dir}'}
    
    # Traiter les fichiers FAA
    _process_faa_files(data_dir, database, results)
    
    # Traiter les autres formats
    _process_other_files(data_dir, database, results)
    
    results['database_stats'] = database.get_stats()
    return results

def _process_faa_files(data_dir: Path, database, results: dict) -> None:
    """Traite les fichiers FAA spécifiques."""
    # Code pour ACFTREF, ENGINE, MASTER

def _process_other_files(data_dir: Path, database, results: dict) -> None:
    """Traite les autres formats de fichiers."""
    for file_path in data_dir.iterdir():
        if file_path.name in ['ACFTREF.txt', 'ENGINE.txt', 'MASTER.txt']:
            continue
        
        _process_single_file(file_path, database, results)

def _process_single_file(file_path: Path, database, results: dict) -> None:
    """Traite un seul fichier selon son extension."""
    # Dispatcher par extension
```

## Fonctions à Documenter

Les fonctions suivantes manquent de docstrings et devraient être documentées:

### `opensky_client.py`
- `StateVector.to_dict()`
- `FlightData.to_dict()`
- `Waypoint.to_dict()`
- `FlightTrack.to_dict()`

**Exemple de docstring à ajouter:**
```python
def to_dict(self) -> dict:
    """
    Convertit l'objet en dictionnaire.
    
    Returns:
        dict: Représentation dictionnaire de l'objet avec tous ses attributs.
    """
```

## Type Hints à Ajouter

### `aircraftdb/database.py`
```python
def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
    """Context manager pour les connexions SQLite."""
```

### `aircraftdb/ingest.py`
```python
def ingest_xlsx(file_path: Path, database: AircraftDatabase) -> Dict[str, int]:
def ingest_json(file_path: Path, database: AircraftDatabase) -> Dict[str, int]:
def ingest_directory(data_dir: Path, database: AircraftDatabase) -> Dict[str, Any]:
```

## Actions Recommandées

1. **Priorité Haute**: Refactoriser `call_aircraftdb_tool()` - trop complexe
2. **Priorité Moyenne**: Diviser `_init_schema()` et `get_aircraftdb_tools()`
3. **Priorité Basse**: Ajouter les docstrings manquantes
4. **Maintenance**: Ajouter les type hints manquants

Ces refactorings amélioreront significativement la maintenabilité et la lisibilité du code.
