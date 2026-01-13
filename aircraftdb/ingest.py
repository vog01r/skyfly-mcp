"""
Module d'ingestion des fichiers FAA pour AircraftDB.
Parse et importe les fichiers ACFTREF, ENGINE, MASTER, DEALER, DEREG.
Support CSV, XLSX, JSON, Parquet avec détection automatique.
"""
import csv
import json
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Generator
from datetime import datetime
import re



logger = logging.getLogger(__name__)

# Mapping des colonnes FAA vers nos colonnes normalisées
ACFTREF_COLUMNS = {
    'CODE': 'code',
    'MFR': 'manufacturer',
    'MODEL': 'model',
    'TYPE-ACFT': 'type_aircraft',
    'TYPE-ENG': 'type_engine',
    'AC-CAT': 'aircraft_category',
    'BUILD-CERT-IND': 'builder_cert_ind',
    'NO-ENG': 'num_engines',
    'NO-SEATS': 'num_seats',
    'AC-WEIGHT': 'weight_class',
    'SPEED': 'speed',
    'TC-DATA-SHEET': 'tc_data_sheet',
    'TC-DATA-HOLDER': 'tc_data_holder'
}

ENGINE_COLUMNS = {
    'CODE': 'code',
    'MFR': 'manufacturer',
    'MODEL': 'model',
    'TYPE': 'type',
    'HORSEPOWER': 'horsepower',
    'THRUST': 'thrust'
}

MASTER_COLUMNS = {
    'N-NUMBER': 'n_number',
    'SERIAL NUMBER': 'serial_number',
    'MFR MDL CODE': 'mfr_mdl_code',
    'ENG MFR MDL': 'eng_mfr_mdl',
    'YEAR MFR': 'year_mfr',
    'TYPE REGISTRANT': 'type_registrant',
    'NAME': 'registrant_name',
    'STREET': 'street',
    'STREET2': 'street2',
    'CITY': 'city',
    'STATE': 'state',
    'ZIP CODE': 'zip_code',
    'REGION': 'region',
    'COUNTY': 'county',
    'COUNTRY': 'country',
    'LAST ACTION DATE': 'last_action_date',
    'CERT ISSUE DATE': 'cert_issue_date',
    'CERTIFICATION': 'certification',
    'TYPE AIRCRAFT': 'type_aircraft',
    'TYPE ENGINE': 'type_engine',
    'STATUS CODE': 'status_code',
    'MODE S CODE': 'mode_s_code',
    'MODE S CODE HEX': 'mode_s_code_hex',
    'FRACT OWNER': 'fract_owner',
    'AIR WORTH DATE': 'air_worth_date',
    'EXPIRATION DATE': 'expiration_date',
    'UNIQUE ID': 'unique_id',
    'KIT MFR': 'kit_mfr',
    'KIT MODEL': 'kit_model'
}

DEALER_COLUMNS = {
    'CERTIFICATE-NUMBER': 'certificate_number',
    'OWNERSHIP': 'ownership',
    'CERTIFICATE-DATE': 'certificate_date',
    'EXPIRATION-DATE': 'expiration_date',
    'EXPIRATION-FLAG': 'expiration_flag',
    'NAME': 'name',
    'STREET': 'street',
    'CITY': 'city',
    'STATE-ABBREV': 'state',
    'ZIP-CODE': 'zip_code'
}


def normalize_column_name(name: str) -> str:
    """Normalise un nom de colonne en snake_case."""
    # Supprimer les espaces en début/fin
    name = name.strip()
    # Remplacer les caractères spéciaux par des underscores
    name = re.sub(r'[^a-zA-Z0-9]', '_', name)
    # Convertir en minuscules
    name = name.lower()
    # Supprimer les underscores multiples
    name = re.sub(r'_+', '_', name)
    # Supprimer les underscores en début/fin
    name = name.strip('_')
    return name


def parse_int(value: str) -> Optional[int]:
    """Parse une valeur en entier, retourne None si impossible."""
    if not value or not value.strip():
        return None
    try:
        # Nettoyer les espaces
        value = value.strip()
        # Essayer de parser
        return int(value)
    except (ValueError, TypeError):
        return None


def parse_value(value: str) -> Any:
    """Parse une valeur en détectant son type."""
    if not value or not value.strip():
        return None
    
    value = value.strip()
    
    # Essayer entier
    try:
        return int(value)
    except ValueError:
        pass
    
    # Essayer float
    try:
        return float(value)
    except ValueError:
        pass
    
    # Retourner comme string
    return value


def detect_encoding(file_path: Path) -> str:
    """Détecte l'encodage d'un fichier."""
    # Essayer UTF-8 avec BOM d'abord
    encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read(1024)
            return encoding
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    return 'utf-8-sig'  # Default avec BOM handling


def parse_faa_csv(file_path: Path, column_mapping: Dict[str, str]) -> Generator[Dict[str, Any], None, None]:
    """Parse un fichier CSV FAA avec le mapping de colonnes donné."""
    encoding = detect_encoding(file_path)
    
    with open(file_path, 'r', encoding=encoding, errors='replace') as f:
        # Read the header
        reader = csv.reader(f)
        header = next(reader)
        
        # Clean the header
        header = [h.strip() for h in header]
        
        # Mapper les colonnes
        col_indices = {}
        for i, col in enumerate(header):
            if col in column_mapping:
                col_indices[i] = column_mapping[col]
        
        # Parser chaque ligne
        for row in reader:
            if not row or all(not cell.strip() for cell in row):
                continue
            
            data = {}
            for i, value in enumerate(row):
                if i in col_indices:
                    col_name = col_indices[i]
                    data[col_name] = parse_value(value)
            
            # Ajouter raw_json avec les données originales
            raw_data = {header[i]: row[i].strip() if i < len(row) else '' for i in range(len(header))}
            data['_raw'] = raw_data
            
            yield data


class FAAAircraftIngest:
    """Classe d'ingestion des fichiers FAA."""
    
    def __init__(self, database):
        self.db = database
        self.stats = {
            'models_inserted': 0,
            'models_updated': 0,
            'engines_inserted': 0,
            'engines_updated': 0,
            'registry_inserted': 0,
            'registry_updated': 0,
            'dealers_inserted': 0,
            'errors': 0
        }
    
    def ingest_acftref(self, file_path: Path) -> Dict[str, int]:
        """Ingère le fichier ACFTREF (modèles d'aéronefs)."""
        logger.info(f"Ingesting ACFTREF from {file_path}")
        count = 0
        
        for data in parse_faa_csv(file_path, ACFTREF_COLUMNS):
            if not data.get('code'):
                continue
            
            try:
                self.db.upsert_aircraft_model(data)
                count += 1
                
                if count % 10000 == 0:
                    logger.info(f"  Processed {count} aircraft models...")
                    
            except Exception as e:
                logger.error(f"Error inserting model {data.get('code')}: {e}")
                self.stats['errors'] += 1
        
        self.stats['models_inserted'] = count
        logger.info(f"Ingested {count} aircraft models")
        return {'aircraft_models': count}
    
    def ingest_engines(self, file_path: Path) -> Dict[str, int]:
        """Ingère le fichier ENGINE."""
        logger.info(f"Ingesting ENGINE from {file_path}")
        count = 0
        
        for data in parse_faa_csv(file_path, ENGINE_COLUMNS):
            if not data.get('code'):
                continue
            
            try:
                self.db.upsert_engine(data)
                count += 1
                
            except Exception as e:
                logger.error(f"Error inserting engine {data.get('code')}: {e}")
                self.stats['errors'] += 1
        
        self.stats['engines_inserted'] = count
        logger.info(f"Ingested {count} engines")
        return {'engines': count}
    
    def ingest_master(self, file_path: Path, batch_size: int = 5000) -> Dict[str, int]:
        """Ingère le fichier MASTER (registre principal)."""
        logger.info(f"Ingesting MASTER from {file_path}")
        count = 0
        
        for data in parse_faa_csv(file_path, MASTER_COLUMNS):
            if not data.get('n_number'):
                continue
            
            try:
                self.db.upsert_aircraft_registry(data)
                count += 1
                
                if count % 50000 == 0:
                    logger.info(f"  Processed {count} registry entries...")
                    
            except Exception as e:
                logger.error(f"Error inserting registry {data.get('n_number')}: {e}")
                self.stats['errors'] += 1
        
        self.stats['registry_inserted'] = count
        logger.info(f"Ingested {count} registry entries")
        return {'aircraft_registry': count}
    
    def ingest_all(self, data_dir: Path) -> Dict[str, Any]:
        """Ingère tous les fichiers FAA du répertoire."""
        results = {}
        
        # ACFTREF
        acftref_path = data_dir / 'ACFTREF.txt'
        if acftref_path.exists():
            results['acftref'] = self.ingest_acftref(acftref_path)
        
        # ENGINE
        engine_path = data_dir / 'ENGINE.txt'
        if engine_path.exists():
            results['engine'] = self.ingest_engines(engine_path)
        
        # MASTER (gros fichier - traiter en dernier)
        master_path = data_dir / 'MASTER.txt'
        if master_path.exists():
            results['master'] = self.ingest_master(master_path)
        
        results['stats'] = self.stats
        results['database_stats'] = self.db.get_stats()
        
        return results


def ingest_xlsx(file_path: Path, database: 'AircraftDatabase') -> Dict[str, int]:
    """Ingère un fichier Excel."""
    try:
    except ImportError:
        logger.error("openpyxl not installed. Run: pip install openpyxl")
        return {'error': 'openpyxl not installed'}
    
    logger.info(f"Ingesting XLSX from {file_path}")
    
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    results = {}
    
    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        rows = list(sheet.iter_rows(values_only=True))
        
        if not rows:
            continue
        
        # Premier row = headers
        headers = [normalize_column_name(str(h)) if h else f'col_{i}' for i, h in enumerate(rows[0])]
        
        # Filtrer les colonnes vides/unnamed
        valid_cols = [(i, h) for i, h in enumerate(headers) if h and not h.startswith('col_') and 'unnamed' not in h.lower()]
        
        count = 0
        for row in rows[1:]:
            if not row or all(cell is None or cell == '' for cell in row):
                continue
            
            data = {}
            for i, header in valid_cols:
                if i < len(row):
                    data[header] = row[i]
            
            if data:
                # Stocker dans custom_data
                with database.get_connection() as conn:
                    conn.execute("""
                        INSERT INTO custom_data (source_file, table_name, data_json)
                        VALUES (?, ?, ?)
                    """, (str(file_path), sheet_name, json.dumps(data, default=str)))
                count += 1
        
        results[sheet_name] = count
        logger.info(f"  Sheet '{sheet_name}': {count} rows")
    
    wb.close()
    return results


def ingest_json(file_path: Path, database: 'AircraftDatabase') -> Dict[str, int]:
    """Ingère un fichier JSON."""
    logger.info(f"Ingesting JSON from {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Si c'est une liste
    if isinstance(data, list):
        count = 0
        with database.get_connection() as conn:
            for item in data:
                conn.execute("""
                    INSERT INTO custom_data (source_file, table_name, data_json)
                    VALUES (?, ?, ?)
                """, (str(file_path), 'data', json.dumps(item, default=str)))
                count += 1
        return {'data': count}
    
    # If it's a dict
    elif isinstance(data, dict):
        with database.get_connection() as conn:
            conn.execute("""
                INSERT INTO custom_data (source_file, table_name, data_json)
                VALUES (?, ?, ?)
            """, (str(file_path), 'data', json.dumps(data, default=str)))
        return {'data': 1}
    
    return {'data': 0}


def ingest_directory(data_dir: Path, database: 'AircraftDatabase') -> Dict[str, Any]:
    """
    Ingère tous les fichiers supportés d'un répertoire.
    Supporte: .txt (FAA CSV), .csv, .xlsx, .json, .parquet
    """
    results = {
        'files_processed': [],
        'files_skipped': [],
        'stats': {}
    }
    
    data_dir = Path(data_dir)
    
    if not data_dir.exists():
        return {'error': f'Directory not found: {data_dir}'}
    
    # D'abord traiter les fichiers FAA connus
    faa_ingest = FAAAircraftIngest(database)
    
    # ACFTREF
    acftref = data_dir / 'ACFTREF.txt'
    if acftref.exists():
        results['stats']['acftref'] = faa_ingest.ingest_acftref(acftref)
        results['files_processed'].append('ACFTREF.txt')
    
    # ENGINE
    engine = data_dir / 'ENGINE.txt'
    if engine.exists():
        results['stats']['engine'] = faa_ingest.ingest_engines(engine)
        results['files_processed'].append('ENGINE.txt')
    
    # MASTER
    master = data_dir / 'MASTER.txt'
    if master.exists():
        results['stats']['master'] = faa_ingest.ingest_master(master)
        results['files_processed'].append('MASTER.txt')
    
    # Autres fichiers
    for file_path in data_dir.iterdir():
        if file_path.name in ['ACFTREF.txt', 'ENGINE.txt', 'MASTER.txt']:
            continue
        
        if file_path.suffix.lower() == '.xlsx':
            try:
                results['stats'][file_path.name] = ingest_xlsx(file_path, database)
                results['files_processed'].append(file_path.name)
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                results['files_skipped'].append({'file': file_path.name, 'error': str(e)})
        
        elif file_path.suffix.lower() == '.json':
            try:
                results['stats'][file_path.name] = ingest_json(file_path, database)
                results['files_processed'].append(file_path.name)
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                results['files_skipped'].append({'file': file_path.name, 'error': str(e)})
        
        elif file_path.suffix.lower() == '.csv':
            # CSV générique - stocker dans custom_data
            try:
                encoding = detect_encoding(file_path)
                with open(file_path, 'r', encoding=encoding) as f:
                    reader = csv.DictReader(f)
                    count = 0
                    with database.get_connection() as conn:
                        for row in reader:
                            # Normaliser les clés
                            normalized = {normalize_column_name(k): v for k, v in row.items() if k and v}
                            conn.execute("""
                                INSERT INTO custom_data (source_file, table_name, data_json)
                                VALUES (?, ?, ?)
                            """, (str(file_path), file_path.stem, json.dumps(normalized)))
                            count += 1
                    results['stats'][file_path.name] = {'rows': count}
                    results['files_processed'].append(file_path.name)
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                results['files_skipped'].append({'file': file_path.name, 'error': str(e)})
        
        else:
            results['files_skipped'].append({'file': file_path.name, 'reason': 'unsupported format'})
    
    # Stats finales
    results['database_stats'] = database.get_stats()
    
    return results

