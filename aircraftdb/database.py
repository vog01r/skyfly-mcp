"""
Module de base de données SQLite pour AircraftDB.
Gère le schéma, les connexions et les opérations CRUD.
"""

import sqlite3
import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

# Chemin par défaut de la base de données
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "aircraft.db"


class AircraftDatabase:
    """
    Gestionnaire de base de données pour les référentiels aéronefs.
    Utilise SQLite avec support pour les opérations concurrentes.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
    
    @contextmanager
    def get_connection(self):
        """Context manager pour les connexions SQLite."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_schema(self):
        """Initialise le schéma de la base de données."""
        with self.get_connection() as conn:
            # Table des modèles d'aéronefs (référence FAA ACFTREF)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS aircraft_models (
                    code TEXT PRIMARY KEY,
                    manufacturer TEXT,
                    model TEXT,
                    type_aircraft INTEGER,
                    type_engine INTEGER,
                    aircraft_category INTEGER,
                    builder_cert_ind INTEGER,
                    num_engines INTEGER,
                    num_seats INTEGER,
                    weight_class TEXT,
                    speed INTEGER,
                    tc_data_sheet TEXT,
                    tc_data_holder TEXT,
                    raw_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Table des moteurs (référence FAA ENGINE)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS engines (
                    code TEXT PRIMARY KEY,
                    manufacturer TEXT,
                    model TEXT,
                    type INTEGER,
                    horsepower INTEGER,
                    thrust INTEGER,
                    raw_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Table du registre des aéronefs (FAA MASTER)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS aircraft_registry (
                    n_number TEXT PRIMARY KEY,
                    serial_number TEXT,
                    mfr_mdl_code TEXT,
                    eng_mfr_mdl TEXT,
                    year_mfr INTEGER,
                    type_registrant INTEGER,
                    registrant_name TEXT,
                    street TEXT,
                    street2 TEXT,
                    city TEXT,
                    state TEXT,
                    zip_code TEXT,
                    region TEXT,
                    county TEXT,
                    country TEXT,
                    last_action_date TEXT,
                    cert_issue_date TEXT,
                    certification TEXT,
                    type_aircraft INTEGER,
                    type_engine INTEGER,
                    status_code TEXT,
                    mode_s_code TEXT,
                    mode_s_code_hex TEXT,
                    fract_owner TEXT,
                    air_worth_date TEXT,
                    expiration_date TEXT,
                    unique_id TEXT,
                    kit_mfr TEXT,
                    kit_model TEXT,
                    raw_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Table des dealers (FAA DEALER)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dealers (
                    certificate_number TEXT PRIMARY KEY,
                    ownership INTEGER,
                    certificate_date TEXT,
                    expiration_date TEXT,
                    expiration_flag TEXT,
                    name TEXT,
                    street TEXT,
                    city TEXT,
                    state TEXT,
                    zip_code TEXT,
                    raw_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Table des aéronefs désenregistrés (FAA DEREG)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS aircraft_deregistered (
                    n_number TEXT,
                    serial_number TEXT,
                    mfr_mdl_code TEXT,
                    status_code TEXT,
                    mode_s_code_hex TEXT,
                    cancel_date TEXT,
                    raw_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (n_number, cancel_date)
                )
            """)
            
            # Table des données custom importées
            conn.execute("""
                CREATE TABLE IF NOT EXISTS custom_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_file TEXT,
                    table_name TEXT,
                    data_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Index pour les recherches fréquentes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_registry_mode_s ON aircraft_registry(mode_s_code_hex)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_registry_mfr_mdl ON aircraft_registry(mfr_mdl_code)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_registry_state ON aircraft_registry(state)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_registry_city ON aircraft_registry(city)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_models_manufacturer ON aircraft_models(manufacturer)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_models_type ON aircraft_models(type_aircraft)")
            
            logger.info("Database schema initialized")
    
    # ============ AIRCRAFT MODELS (ACFTREF) ============
    
    def upsert_aircraft_model(self, data: Dict[str, Any]) -> bool:
        """Insert ou update un modèle d'aéronef."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO aircraft_models 
                (code, manufacturer, model, type_aircraft, type_engine, aircraft_category,
                 builder_cert_ind, num_engines, num_seats, weight_class, speed,
                 tc_data_sheet, tc_data_holder, raw_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(code) DO UPDATE SET
                    manufacturer = excluded.manufacturer,
                    model = excluded.model,
                    type_aircraft = excluded.type_aircraft,
                    type_engine = excluded.type_engine,
                    aircraft_category = excluded.aircraft_category,
                    builder_cert_ind = excluded.builder_cert_ind,
                    num_engines = excluded.num_engines,
                    num_seats = excluded.num_seats,
                    weight_class = excluded.weight_class,
                    speed = excluded.speed,
                    tc_data_sheet = excluded.tc_data_sheet,
                    tc_data_holder = excluded.tc_data_holder,
                    raw_json = excluded.raw_json,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                data.get('code'),
                data.get('manufacturer'),
                data.get('model'),
                data.get('type_aircraft'),
                data.get('type_engine'),
                data.get('aircraft_category'),
                data.get('builder_cert_ind'),
                data.get('num_engines'),
                data.get('num_seats'),
                data.get('weight_class'),
                data.get('speed'),
                data.get('tc_data_sheet'),
                data.get('tc_data_holder'),
                json.dumps(data)
            ))
        return True
    
    def get_aircraft_model(self, code: str) -> Optional[Dict]:
        """Récupère un modèle d'aéronef par son code."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM aircraft_models WHERE code = ?", (code,)
            ).fetchone()
            return dict(row) if row else None
    
    def search_aircraft_models(self, 
                               manufacturer: Optional[str] = None,
                               model: Optional[str] = None,
                               type_aircraft: Optional[int] = None,
                               num_engines: Optional[int] = None,
                               limit: int = 100) -> List[Dict]:
        """Recherche des modèles d'aéronefs."""
        conditions = []
        params = []
        
        if manufacturer:
            conditions.append("manufacturer LIKE ?")
            params.append(f"%{manufacturer}%")
        if model:
            conditions.append("model LIKE ?")
            params.append(f"%{model}%")
        if type_aircraft is not None:
            conditions.append("type_aircraft = ?")
            params.append(type_aircraft)
        if num_engines is not None:
            conditions.append("num_engines = ?")
            params.append(num_engines)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)
        
        with self.get_connection() as conn:
            rows = conn.execute(f"""
                SELECT * FROM aircraft_models 
                WHERE {where_clause}
                LIMIT ?
            """, params).fetchall()
            return [dict(row) for row in rows]
    
    # ============ ENGINES ============
    
    def upsert_engine(self, data: Dict[str, Any]) -> bool:
        """Insert ou update un moteur."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO engines 
                (code, manufacturer, model, type, horsepower, thrust, raw_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(code) DO UPDATE SET
                    manufacturer = excluded.manufacturer,
                    model = excluded.model,
                    type = excluded.type,
                    horsepower = excluded.horsepower,
                    thrust = excluded.thrust,
                    raw_json = excluded.raw_json,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                data.get('code'),
                data.get('manufacturer'),
                data.get('model'),
                data.get('type'),
                data.get('horsepower'),
                data.get('thrust'),
                json.dumps(data)
            ))
        return True
    
    def get_engine(self, code: str) -> Optional[Dict]:
        """Récupère un moteur par son code."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM engines WHERE code = ?", (code,)
            ).fetchone()
            return dict(row) if row else None
    
    # ============ AIRCRAFT REGISTRY (MASTER) ============
    
    def upsert_aircraft_registry(self, data: Dict[str, Any]) -> bool:
        """Insert ou update une entrée du registre."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO aircraft_registry 
                (n_number, serial_number, mfr_mdl_code, eng_mfr_mdl, year_mfr,
                 type_registrant, registrant_name, street, street2, city, state,
                 zip_code, region, county, country, last_action_date, cert_issue_date,
                 certification, type_aircraft, type_engine, status_code, mode_s_code,
                 mode_s_code_hex, fract_owner, air_worth_date, expiration_date,
                 unique_id, kit_mfr, kit_model, raw_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(n_number) DO UPDATE SET
                    serial_number = excluded.serial_number,
                    mfr_mdl_code = excluded.mfr_mdl_code,
                    eng_mfr_mdl = excluded.eng_mfr_mdl,
                    year_mfr = excluded.year_mfr,
                    type_registrant = excluded.type_registrant,
                    registrant_name = excluded.registrant_name,
                    street = excluded.street,
                    street2 = excluded.street2,
                    city = excluded.city,
                    state = excluded.state,
                    zip_code = excluded.zip_code,
                    region = excluded.region,
                    county = excluded.county,
                    country = excluded.country,
                    last_action_date = excluded.last_action_date,
                    cert_issue_date = excluded.cert_issue_date,
                    certification = excluded.certification,
                    type_aircraft = excluded.type_aircraft,
                    type_engine = excluded.type_engine,
                    status_code = excluded.status_code,
                    mode_s_code = excluded.mode_s_code,
                    mode_s_code_hex = excluded.mode_s_code_hex,
                    fract_owner = excluded.fract_owner,
                    air_worth_date = excluded.air_worth_date,
                    expiration_date = excluded.expiration_date,
                    unique_id = excluded.unique_id,
                    kit_mfr = excluded.kit_mfr,
                    kit_model = excluded.kit_model,
                    raw_json = excluded.raw_json,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                data.get('n_number'),
                data.get('serial_number'),
                data.get('mfr_mdl_code'),
                data.get('eng_mfr_mdl'),
                data.get('year_mfr'),
                data.get('type_registrant'),
                data.get('registrant_name'),
                data.get('street'),
                data.get('street2'),
                data.get('city'),
                data.get('state'),
                data.get('zip_code'),
                data.get('region'),
                data.get('county'),
                data.get('country'),
                data.get('last_action_date'),
                data.get('cert_issue_date'),
                data.get('certification'),
                data.get('type_aircraft'),
                data.get('type_engine'),
                data.get('status_code'),
                data.get('mode_s_code'),
                data.get('mode_s_code_hex'),
                data.get('fract_owner'),
                data.get('air_worth_date'),
                data.get('expiration_date'),
                data.get('unique_id'),
                data.get('kit_mfr'),
                data.get('kit_model'),
                json.dumps(data)
            ))
        return True
    
    def get_aircraft_by_n_number(self, n_number: str) -> Optional[Dict]:
        """Récupère un aéronef par son N-number."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM aircraft_registry WHERE n_number = ?", (n_number.upper(),)
            ).fetchone()
            return dict(row) if row else None
    
    def get_aircraft_by_mode_s_hex(self, mode_s_hex: str) -> Optional[Dict]:
        """Récupère un aéronef par son code Mode-S hex (icao24)."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM aircraft_registry WHERE mode_s_code_hex = ?", 
                (mode_s_hex.upper(),)
            ).fetchone()
            return dict(row) if row else None
    
    def search_aircraft_registry(self,
                                  registrant_name: Optional[str] = None,
                                  city: Optional[str] = None,
                                  state: Optional[str] = None,
                                  manufacturer: Optional[str] = None,
                                  year_from: Optional[int] = None,
                                  year_to: Optional[int] = None,
                                  type_aircraft: Optional[int] = None,
                                  limit: int = 100) -> List[Dict]:
        """Recherche dans le registre des aéronefs."""
        conditions = []
        params = []
        
        if registrant_name:
            conditions.append("registrant_name LIKE ?")
            params.append(f"%{registrant_name.upper()}%")
        if city:
            conditions.append("city LIKE ?")
            params.append(f"%{city.upper()}%")
        if state:
            conditions.append("state = ?")
            params.append(state.upper())
        if year_from:
            conditions.append("year_mfr >= ?")
            params.append(year_from)
        if year_to:
            conditions.append("year_mfr <= ?")
            params.append(year_to)
        if type_aircraft is not None:
            conditions.append("type_aircraft = ?")
            params.append(type_aircraft)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)
        
        with self.get_connection() as conn:
            rows = conn.execute(f"""
                SELECT * FROM aircraft_registry 
                WHERE {where_clause}
                LIMIT ?
            """, params).fetchall()
            return [dict(row) for row in rows]
    
    def get_aircraft_with_model_info(self, n_number: str) -> Optional[Dict]:
        """Récupère un aéronef avec les infos du modèle jointes."""
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT 
                    r.*,
                    m.manufacturer as model_manufacturer,
                    m.model as model_name,
                    m.type_aircraft as model_type_aircraft,
                    m.type_engine as model_type_engine,
                    m.num_engines as model_num_engines,
                    m.num_seats as model_num_seats,
                    m.weight_class as model_weight_class,
                    m.speed as model_speed,
                    e.manufacturer as engine_manufacturer,
                    e.model as engine_model,
                    e.horsepower as engine_horsepower,
                    e.thrust as engine_thrust
                FROM aircraft_registry r
                LEFT JOIN aircraft_models m ON r.mfr_mdl_code = m.code
                LEFT JOIN engines e ON r.eng_mfr_mdl = e.code
                WHERE r.n_number = ?
            """, (n_number.upper(),)).fetchone()
            return dict(row) if row else None
    
    def get_aircraft_by_mode_s_with_details(self, mode_s_hex: str) -> Optional[Dict]:
        """Récupère un aéronef par Mode-S avec toutes les infos jointes."""
        with self.get_connection() as conn:
            row = conn.execute("""
                SELECT 
                    r.*,
                    m.manufacturer as model_manufacturer,
                    m.model as model_name,
                    m.type_aircraft as model_type_aircraft,
                    m.type_engine as model_type_engine,
                    m.num_engines as model_num_engines,
                    m.num_seats as model_num_seats,
                    m.weight_class as model_weight_class,
                    m.speed as model_speed,
                    e.manufacturer as engine_manufacturer,
                    e.model as engine_model,
                    e.horsepower as engine_horsepower,
                    e.thrust as engine_thrust
                FROM aircraft_registry r
                LEFT JOIN aircraft_models m ON r.mfr_mdl_code = m.code
                LEFT JOIN engines e ON r.eng_mfr_mdl = e.code
                WHERE r.mode_s_code_hex = ?
            """, (mode_s_hex.upper(),)).fetchone()
            return dict(row) if row else None
    
    # ============ STATS & QUERIES ============
    
    def get_stats(self) -> Dict[str, int]:
        """Retourne les statistiques de la base."""
        with self.get_connection() as conn:
            stats = {}
            for table in ['aircraft_models', 'engines', 'aircraft_registry', 'dealers', 'aircraft_deregistered']:
                row = conn.execute(f"SELECT COUNT(*) as count FROM {table}").fetchone()
                stats[table] = row['count']
            return stats
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """Exécute une requête SQL SELECT personnalisée."""
        # Sécurité: n'autoriser que les SELECT
        if not query.strip().upper().startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed")
        
        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]


# Instance globale
_db_instance: Optional[AircraftDatabase] = None

def get_database() -> AircraftDatabase:
    """Retourne l'instance singleton de la base."""
    global _db_instance
    if _db_instance is None:
        _db_instance = AircraftDatabase()
    return _db_instance

