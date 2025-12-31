#!/bin/bash
# Script de configuration SSL avec Let's Encrypt pour skyfly.mcp.hamon.link

set -e

DOMAIN="skyfly.mcp.hamon.link"
EMAIL="${SSL_EMAIL:-admin@hamon.link}"

echo "🔐 Configuration SSL pour $DOMAIN"

# Vérifier si certbot est installé
if ! command -v certbot &> /dev/null; then
    echo "📦 Installation de certbot..."
    sudo apt-get update
    sudo apt-get install -y certbot
fi

# Arrêter le serveur si en cours (pour libérer le port 80)
echo "⏸️  Arrêt temporaire des services sur le port 80..."
sudo systemctl stop nginx 2>/dev/null || true
sudo fuser -k 80/tcp 2>/dev/null || true

# Obtenir le certificat
echo "📜 Obtention du certificat SSL..."
sudo certbot certonly \
    --standalone \
    --non-interactive \
    --agree-tos \
    --email "$EMAIL" \
    --domain "$DOMAIN" \
    --preferred-challenges http

# Créer le répertoire pour les certificats
CERT_DIR="/opt/git/mcpskyfly/certs"
mkdir -p "$CERT_DIR"

# Copier les certificats (avec les bons droits)
echo "📋 Copie des certificats..."
sudo cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$CERT_DIR/"
sudo cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$CERT_DIR/"
sudo chown -R $(whoami):$(whoami) "$CERT_DIR"
chmod 600 "$CERT_DIR"/*.pem

echo "✅ Certificats SSL configurés avec succès!"
echo ""
echo "📁 Certificats disponibles dans: $CERT_DIR"
echo "   - fullchain.pem"
echo "   - privkey.pem"
echo ""
echo "🚀 Vous pouvez maintenant démarrer le serveur avec:"
echo "   ./start.sh"

