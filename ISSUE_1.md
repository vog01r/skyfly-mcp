# Injection SQL dans l'outil db_sql_query

**Type:** security
**Sévérité:** critical
**Fichier:** aircraftdb/tools.py

## Description

L'outil `db_sql_query` permet l'exécution de requêtes SQL personnalisées mais présente une vulnérabilité d'injection SQL critique. Bien que le code vérifie que la requête commence par "SELECT", il n'y a aucune validation ou sanitisation des paramètres d'entrée.

**Problèmes identifiés :**

1. **Ligne 413-414** : La requête SQL est directement passée à `db.execute_query(query)` sans aucune validation du contenu
2. **Ligne 505** dans `database.py` : La méthode `execute_query` ne fait qu'une vérification superficielle avec `startswith("SELECT")` 
3. **Aucune protection contre** :
   - Les injections via UNION SELECT
   - Les sous-requêtes malveillantes
   - L'accès à des tables système SQLite
   - Les requêtes causant des dénis de service

**Exemple d'exploitation :**
```sql
SELECT * FROM aircraft_registry WHERE 1=1 UNION SELECT sql,name,type,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0 FROM sqlite_master--
```

Cette requête pourrait exposer le schéma complet de la base de données.

## Suggestion

1. **Implémenter une whitelist de requêtes** : Créer un ensemble de requêtes prédéfinies et sécurisées
2. **Utiliser un parser SQL** : Valider et analyser la structure de la requête avant exécution
3. **Ajouter des paramètres liés** : Remplacer les valeurs littérales par des paramètres préparés
4. **Limiter les privilèges** : Créer un utilisateur de base de données en lecture seule
5. **Implémenter un timeout** : Éviter les requêtes qui consomment trop de ressources

**Code suggéré :**
```python
ALLOWED_TABLES = ['aircraft_registry', 'aircraft_models', 'engines', 'dealers']
ALLOWED_COLUMNS = ['n_number', 'mode_s_code_hex', 'manufacturer', 'model', 'type_aircraft']

def validate_sql_query(query: str) -> bool:
    # Utiliser sqlparse ou un parser SQL approprié
    # Vérifier que seules les tables et colonnes autorisées sont utilisées
    # Interdire les UNION, sous-requêtes, fonctions système
    pass
```