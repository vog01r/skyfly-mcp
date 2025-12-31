#!/bin/bash
# Script de démarrage du serveur MCP OpenSky

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
DOMAIN="skyfly.mcp.hamon.link"
CERT_DIR="$SCRIPT_DIR/certs"
VENV_DIR="$SCRIPT_DIR/venv"

echo "✈️  OpenSky MCP Server"
echo "====================="

# Créer et activer l'environnement virtuel si nécessaire
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Création de l'environnement virtuel..."
    python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# Installer les dépendances
echo "📦 Installation des dépendances..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# Vérifier les certificats SSL
if [ -f "$CERT_DIR/fullchain.pem" ] && [ -f "$CERT_DIR/privkey.pem" ]; then
    echo "🔐 Certificats SSL trouvés"
    SSL_ARGS="--ssl-keyfile=$CERT_DIR/privkey.pem --ssl-certfile=$CERT_DIR/fullchain.pem"
    PORT=443
    echo "🌐 Démarrage en HTTPS sur https://$DOMAIN"
else
    echo "⚠️  Certificats SSL non trouvés - démarrage en HTTP"
    echo "   Exécutez ./setup_ssl.sh pour configurer HTTPS"
    SSL_ARGS=""
    PORT=8000
    echo "🌐 Démarrage en HTTP sur http://localhost:$PORT"
fi

echo ""
echo "🛠️  Outils disponibles:"
echo "   - get_aircraft_states"
echo "   - get_arrivals_by_airport"
echo "   - get_departures_by_airport"
echo "   - get_flights_by_aircraft"
echo "   - get_flights_from_interval"
echo "   - get_track_by_aircraft"
echo "   - get_aircraft_in_region"
echo "   - get_current_timestamp"
echo ""

# Démarrer le serveur
if [ "$PORT" = "443" ]; then
    # Port 443 nécessite sudo
    sudo "$VENV_DIR/bin/uvicorn" http_server:app \
        --host 0.0.0.0 \
        --port $PORT \
        $SSL_ARGS \
        --workers 4 \
        --loop uvloop \
        --http h11
else
    uvicorn http_server:app \
        --host 0.0.0.0 \
        --port $PORT \
        --workers 4 \
        --reload
fi

