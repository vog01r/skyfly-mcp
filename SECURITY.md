# Politique de Sécurité

## Versions Supportées

Nous supportons activement les versions suivantes du projet Skyfly MCP avec des mises à jour de sécurité :

| Version | Supportée          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Signalement de Vulnérabilités de Sécurité

### Comment Signaler

Si vous découvrez une vulnérabilité de sécurité dans Skyfly MCP, veuillez nous la signaler de manière responsable :

1. **NE PAS** créer d'issue publique sur GitHub
2. **NE PAS** divulguer publiquement la vulnérabilité avant qu'elle soit corrigée
3. Envoyez un email détaillé à : **security@skyfly-mcp.org** (remplacez par votre email de sécurité)
4. Incluez les informations suivantes :
   - Description détaillée de la vulnérabilité
   - Étapes pour reproduire le problème
   - Impact potentiel
   - Versions affectées
   - Suggestions de correction (si vous en avez)
   - Votre nom/pseudo pour les remerciements (optionnel)
   - Toute information supplémentaire pertinente

### Processus de Traitement

1. **Accusé de réception** : Nous accuserons réception de votre rapport dans les 48 heures
2. **Évaluation initiale** : Évaluation de la vulnérabilité dans les 5 jours ouvrables
3. **Investigation** : Investigation approfondie et développement d'un correctif
4. **Divulgation coordonnée** : Nous travaillerons avec vous pour une divulgation responsable
5. **Publication du correctif** : Publication d'une mise à jour de sécurité
6. **Reconnaissance** : Reconnaissance publique de votre contribution (si souhaité)

### Délais de Réponse

- **Accusé de réception** : 48 heures
- **Évaluation initiale** : 5 jours ouvrables
- **Correctif pour vulnérabilités critiques** : 7-14 jours
- **Correctif pour vulnérabilités moyennes/faibles** : 30-90 jours

## Bonnes Pratiques de Sécurité

### Pour les Utilisateurs

1. **Authentification OpenSky** :
   - Utilisez des identifiants OpenSky Network dédiés
   - Ne partagez jamais vos identifiants
   - Stockez les identifiants dans des variables d'environnement

2. **Configuration SSL/TLS** :
   - Utilisez HTTPS en production
   - Configurez des certificats SSL valides
   - Utilisez des protocoles TLS récents (1.2+)

3. **Gestion des Secrets** :
   - Utilisez le fichier `.env` pour les secrets (jamais commité)
   - Générez des clés secrètes fortes et uniques
   - Rotez régulièrement les clés d'API

4. **Mise à Jour** :
   - Maintenez le serveur à jour avec les dernières versions
   - Surveillez les alertes de sécurité
   - Appliquez rapidement les correctifs de sécurité

### Pour les Développeurs

1. **Validation des Entrées** :
   - Validez toutes les entrées utilisateur
   - Utilisez des paramètres typés avec Pydantic
   - Implémentez une validation stricte des paramètres d'API

2. **Gestion des Erreurs** :
   - Ne pas exposer d'informations sensibles dans les messages d'erreur
   - Logger les erreurs de manière sécurisée
   - Implémenter une gestion d'erreur robuste

3. **Dépendances** :
   - Maintenez les dépendances à jour
   - Utilisez Dependabot pour les mises à jour automatiques
   - Auditez régulièrement les dépendances avec `pip audit`

4. **Tests de Sécurité** :
   - Implémentez des tests de sécurité automatisés
   - Effectuez des revues de code régulières
   - Utilisez des outils d'analyse statique

## Configuration Sécurisée

### Variables d'Environnement Sensibles

Les variables suivantes contiennent des informations sensibles et ne doivent jamais être committées :

```bash
OPENSKY_USERNAME=your_username
OPENSKY_PASSWORD=your_password
SECRET_KEY=your_secret_key
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem
```

### Permissions de Fichiers

```bash
# Fichier .env (lecture seule pour le propriétaire)
chmod 600 .env

# Certificats SSL
chmod 600 /path/to/ssl/cert.pem
chmod 600 /path/to/ssl/key.pem

# Base de données
chmod 644 aircraftdb/aircraft.db
```

### Firewall et Réseau

1. **Ports** :
   - Exposez uniquement les ports nécessaires (8000 par défaut)
   - Utilisez un reverse proxy (nginx, Apache) en production
   - Configurez un firewall approprié

2. **CORS** :
   - Configurez CORS de manière restrictive
   - Évitez `ALLOWED_ORIGINS=*` en production
   - Spécifiez des domaines autorisés explicites

## Audit de Sécurité

### Outils Recommandés

```bash
# Audit des dépendances Python
pip install pip-audit
pip-audit

# Analyse statique de sécurité
pip install bandit
bandit -r .

# Scan de vulnérabilités
pip install safety
safety check
```

### Checklist de Sécurité

- [ ] Fichier `.env` configuré et non commité
- [ ] Certificats SSL configurés pour HTTPS
- [ ] Identifiants OpenSky sécurisés
- [ ] CORS configuré de manière restrictive
- [ ] Dépendances mises à jour
- [ ] Logs de sécurité configurés
- [ ] Firewall configuré
- [ ] Tests de sécurité en place

## Contact

Pour toute question relative à la sécurité :

- **Email de sécurité** : security@skyfly-mcp.org
- **Issues non-sensibles** : [GitHub Issues](https://github.com/vog01r/skyfly-mcp/issues)
- **Documentation** : [README.md](README.md)

## Historique des Mises à Jour

| Date | Version | Description |
|------|---------|-------------|
| 2026-01-13 | 1.0.0 | Politique de sécurité initiale |

---

**Merci de contribuer à la sécurité de Skyfly MCP !** 🔒✈️