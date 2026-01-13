# Politique de Sécurité

## Versions Supportées

Nous prenons la sécurité au sérieux. Les versions suivantes de Skyfly MCP sont actuellement supportées avec des mises à jour de sécurité :

| Version | Supportée          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Signaler une Vulnérabilité

### Processus de Signalement

Si vous découvrez une vulnérabilité de sécurité dans Skyfly MCP, nous vous demandons de nous la signaler de manière responsable :

1. **NE PAS** créer d'issue publique sur GitHub
2. **NE PAS** divulguer publiquement la vulnérabilité avant qu'elle soit corrigée
3. Envoyez un email détaillé à : **security@skyfly-mcp.com** (à configurer)

### Informations à Inclure

Veuillez inclure autant d'informations que possible :

- Description détaillée de la vulnérabilité
- Étapes pour reproduire le problème
- Versions affectées
- Impact potentiel
- Suggestions de correction (si vous en avez)
- Votre nom/pseudo pour les remerciements (optionnel)

### Délais de Réponse

- **Accusé de réception** : 48 heures
- **Évaluation initiale** : 7 jours
- **Correction et publication** : 30 jours (selon la complexité)

### Politique de Divulgation

Nous suivons une politique de divulgation responsable :

1. Nous confirmons la réception de votre rapport
2. Nous évaluons et reproduisons la vulnérabilité
3. Nous développons et testons une correction
4. Nous publions la correction dans une nouvelle version
5. Nous publions un avis de sécurité avec les détails appropriés
6. Nous vous remercions publiquement (si souhaité)

## Bonnes Pratiques de Sécurité

### Pour les Utilisateurs

#### Configuration Sécurisée

- **Variables d'environnement** : Utilisez `.env` pour les données sensibles, jamais dans le code
- **Authentification OpenSky** : Stockez les credentials de manière sécurisée
- **HTTPS** : Utilisez toujours HTTPS en production (voir `setup_ssl.sh`)
- **Permissions** : Limitez les permissions des fichiers de configuration

#### Déploiement

```bash
# Bonnes pratiques pour la production
chmod 600 .env                    # Permissions restrictives
chown root:root .env              # Propriétaire approprié
```

#### Configuration CORS

```python
# Limitez les origines en production
CORS_ORIGINS=https://your-domain.com,https://app.your-domain.com
```

### Pour les Développeurs

#### Gestion des Secrets

- **Jamais** de credentials en dur dans le code
- Utilisez des variables d'environnement ou des gestionnaires de secrets
- Ajoutez `.env` à `.gitignore` (déjà fait)

#### Validation des Entrées

- Validez toutes les entrées utilisateur
- Sanitisez les paramètres d'URL et les données POST
- Utilisez des bibliothèques de validation (Pydantic est déjà inclus)

#### Dépendances

- Maintenez les dépendances à jour
- Utilisez `pip-audit` pour détecter les vulnérabilités
- Configurez Dependabot (voir `.github/dependabot.yml`)

#### Logs et Monitoring

- **Ne loggez jamais** de données sensibles (mots de passe, tokens)
- Implémentez un monitoring des erreurs
- Configurez des alertes pour les tentatives d'accès suspect

## Vulnérabilités Connues et Mitigations

### Rate Limiting

**Problème** : L'API OpenSky a des limites de taux strictes
**Mitigation** : 
- Implémentation d'un cache local
- Respect des limites API (10s sans auth, plus avec auth)
- Gestion des erreurs 429 (Too Many Requests)

### Injection de Données

**Problème** : Requêtes SQL potentielles dans AircraftDB
**Mitigation** :
- Utilisation d'ORM/requêtes préparées
- Validation stricte des paramètres
- Sanitisation des entrées utilisateur

### Exposition de Données

**Problème** : Données d'aviation potentiellement sensibles
**Mitigation** :
- Limitation du nombre de résultats retournés
- Pas de données d'identification personnelle
- Conformité aux politiques OpenSky Network

## Conformité et Réglementations

### OpenSky Network

- Respect des conditions d'utilisation de l'API
- Attribution appropriée des données
- Pas de redistribution non autorisée

### Protection des Données

- Pas de stockage de données personnelles
- Données publiques uniquement (positions d'aéronefs)
- Conformité RGPD par design (pas de données personnelles)

## Contact Sécurité

- **Email** : security@skyfly-mcp.com (à configurer)
- **PGP Key** : [À ajouter si nécessaire]
- **Response Time** : 48h pour accusé de réception

## Remerciements

Nous remercions les chercheurs en sécurité qui nous aident à améliorer la sécurité de Skyfly MCP :

- [Liste des contributeurs sécurité - à maintenir]

---

**Dernière mise à jour** : Janvier 2026
**Version du document** : 1.0