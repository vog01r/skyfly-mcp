# ✈️ Skyfly MCP Server

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP Protocol](https://img.shields.io/badge/MCP-Protocol-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenSky Network](https://img.shields.io/badge/Data-OpenSky%20Network-orange.svg)](https://opensky-network.org/)

> **Un serveur MCP (Model Context Protocol) qui combine données de vol en temps réel et référentiel FAA pour créer des expériences IA riches en contexte aéronautique.**

🌐 **Demo live:** [skyfly.mcp.hamon.link](https://skyfly.mcp.hamon.link)

---

## 🎯 Qu'est-ce que c'est ?

**Skyfly MCP** est un serveur qui permet à des LLMs comme **Claude** ou **ChatGPT** d'accéder à :

1. **📡 Données live** (via OpenSky Network)
   - Positions des avions en temps réel
   - Trajectoires et historiques de vol
   - Arrivées/départs par aéroport

2. **🗄️ Référentiel FAA** (base SQL locale)
   - 93,000+ modèles d'aéronefs
   - 306,000+ avions immatriculés US
   - 4,700+ moteurs référencés

**Résultat :** Des requêtes intelligentes qui combinent position live + specs techniques !

---

## 🚀 Fonctionnalités

### 19 Outils MCP disponibles

| Catégorie | Outils | Description |
|-----------|--------|-------------|
| **Live** | `get_aircraft_states` | Positions actuelles des aéronefs |
| **Live** | `get_aircraft_in_region` | Aéronefs par zone (France, Europe...) |
| **Live** | `get_arrivals_by_airport` | Arrivées à un aéroport |
| **Live** | `get_departures_by_airport` | Départs d'un aéroport |
| **Live** | `get_track_by_aircraft` | Trajectoire d'un aéronef |
| **SQL** | `db_lookup_by_mode_s` | Enrichit un icao24 avec specs |
| **SQL** | `db_search_aircraft` | Recherche dans le registre FAA |
| **SQL** | `db_search_models` | Recherche modèles (Boeing, Cessna...) |
| **SQL** | `db_enrich_live_aircraft` | Enrichit une liste d'icao24 |
| **SQL** | `db_sql_query` | Requête SQL personnalisée |

---

## 📦 Installation

### Prérequis

- Python 3.10+
- Certificat SSL (Let's Encrypt recommandé)

### Installation rapide

```bash
# Cloner le repo
git clone https://github.com/vog01r/skyfly-mcp.git
cd skyfly-mcp

# Créer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Télécharger les données FAA (optionnel mais recommandé)
# Depuis: https://www.faa.gov/licenses_certificates/aircraft_certification/aircraft_registry/releasable_aircraft_download
mkdir ReleasableAircraft
# Placer ACFTREF.txt, ENGINE.txt, MASTER.txt dans ce dossier

# Lancer l'ingestion
python -c "
from aircraftdb.database import get_database
from aircraftdb.ingest import ingest_directory
from pathlib import Path
db = get_database()
ingest_directory(Path('ReleasableAircraft'), db)
"

# Démarrer le serveur
./start.sh
```

---

## 🔗 Configuration MCP

### Pour Claude Desktop

Ajoutez dans votre configuration MCP :

```json
{
  "mcpServers": {
    "skyfly": {
      "url": "https://skyfly.mcp.hamon.link/sse"
    }
  }
}
```

### Auto-hébergé

```json
{
  "mcpServers": {
    "skyfly": {
      "url": "https://your-domain.com/sse"
    }
  }
}
```

---

## 💡 Exemples de requêtes

### Requête simple
> *"Montre-moi les avions au-dessus de la France"*

### Requête enrichie
> *"Pour les 5 avions au-dessus de Paris, donne-moi le propriétaire, le type d'appareil et le nombre de moteurs"*

### Requête analytique
> *"Combien de Boeing 737 sont dans le registre FAA ? Quels sont les 5 états avec le plus d'immatriculations ?"*

### Requête combinée
> *"Parmi les hélicoptères actuellement en vol aux USA, quel est le modèle le plus fréquent ?"*

---

## 🏗️ Architecture

```
skyfly-mcp/
├── http_server.py          # Serveur MCP unifié (SSE + REST)
├── opensky_client.py       # Client async OpenSky API
├── server.py               # Serveur MCP stdio (usage local)
├── aircraftdb/
│   ├── database.py         # SQLite avec schéma + CRUD
│   ├── ingest.py           # Ingestion fichiers FAA
│   └── tools.py            # Outils MCP AircraftDB
├── requirements.txt
├── setup_ssl.sh            # Configuration Let's Encrypt
├── start.sh                # Script de démarrage
└── opensky-mcp.service     # Service systemd
```

---

## 📊 Données FAA

Le référentiel FAA contient :

| Table | Contenu | Source |
|-------|---------|--------|
| `aircraft_models` | 93K+ modèles | ACFTREF.txt |
| `aircraft_registry` | 306K+ aéronefs US | MASTER.txt |
| `engines` | 4.7K+ moteurs | ENGINE.txt |

**Téléchargement :** [FAA Releasable Aircraft Database](https://www.faa.gov/licenses_certificates/aircraft_certification/aircraft_registry/releasable_aircraft_download)

---

## 🔧 Déploiement Production

### Avec Apache (reverse proxy)

```apache
<VirtualHost *:443>
    ServerName skyfly.yourdomain.com
    
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/skyfly.yourdomain.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/skyfly.yourdomain.com/privkey.pem
    
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8443/
    ProxyPassReverse / http://127.0.0.1:8443/
</VirtualHost>
```

### Service systemd

```bash
sudo cp opensky-mcp.service /etc/systemd/system/
sudo systemctl enable opensky-mcp
sudo systemctl start opensky-mcp
```

---

## 🤝 Contribution

Les contributions sont les bienvenues ! 

1. Fork le projet
2. Créez une branche (`git checkout -b feature/amazing-feature`)
3. Committez (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feature/amazing-feature`)
5. Ouvrez une Pull Request

---

## 📜 Licence

MIT License - voir [LICENSE](LICENSE)

---

## 🙏 Crédits

- **[OpenSky Network](https://opensky-network.org/)** - Données de vol en temps réel
- **[FAA](https://www.faa.gov/)** - Registre des aéronefs US
- **[Anthropic MCP](https://modelcontextprotocol.io/)** - Model Context Protocol

---

<p align="center">
  <b>Fait avec ❤️ pour la communauté IA & Aviation</b>
</p>
