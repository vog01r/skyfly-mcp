#!/bin/bash
"""
Script de configuration pour l'outil de gestion des PRs
Résout le problème SKYFLY-2: 6 Pull Requests en attente de review
"""

set -e

echo "🚀 Configuration de l'outil de gestion des PRs pour skyfly-mcp"
echo "Résolution du problème SKYFLY-2: Pull Requests en attente de review"
echo ""

# Vérifier les prérequis
echo "📋 Vérification des prérequis..."

# Vérifier si gh CLI est installé
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) n'est pas installé"
    echo "   Installez-le avec: curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg"
    exit 1
fi

# Vérifier si l'utilisateur est connecté à GitHub
if ! gh auth status &> /dev/null; then
    echo "❌ Vous n'êtes pas connecté à GitHub"
    echo "   Connectez-vous avec: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI configuré"

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé"
    exit 1
fi

echo "✅ Python 3 disponible"

# Rendre le script Python exécutable
chmod +x pr_management_tool.py

echo ""
echo "🔍 Analyse de l'état actuel des PRs..."

# Exécuter l'analyse initiale
python3 pr_management_tool.py --action report

echo ""
echo "⚙️  Configuration des règles de protection de branche..."

# Configurer les règles de protection pour automatiser le processus
gh api repos/:owner/:repo/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":[]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true,"require_code_owner_reviews":false}' \
  --field restrictions=null \
  --field allow_auto_merge=true \
  --field allow_deletions=false \
  --field allow_force_pushes=false \
  2>/dev/null || echo "⚠️  Impossible de configurer les règles de protection (permissions insuffisantes)"

echo ""
echo "🤖 Configuration du workflow GitHub Actions..."

# Vérifier si le workflow existe
if [ -f ".github/workflows/pr_management.yml" ]; then
    echo "✅ Workflow GitHub Actions configuré"
else
    echo "❌ Workflow GitHub Actions manquant"
    exit 1
fi

echo ""
echo "📊 Génération du rapport initial..."

# Créer un rapport initial et le sauvegarder
python3 pr_management_tool.py --action report > pr_management_report.md

echo ""
echo "✅ Configuration terminée!"
echo ""
echo "📖 Utilisation:"
echo "   • Rapport détaillé:           python3 pr_management_tool.py --action report"
echo "   • Simulation des actions:     python3 pr_management_tool.py --action auto"
echo "   • Exécution des actions:      python3 pr_management_tool.py --action execute"
echo "   • Avec mode dry-run:          python3 pr_management_tool.py --action execute --dry-run"
echo ""
echo "🔄 Le workflow GitHub Actions s'exécutera automatiquement tous les jours à 9h UTC"
echo "   Vous pouvez aussi le déclencher manuellement depuis l'onglet Actions de GitHub"
echo ""
echo "📋 Rapport initial sauvegardé dans: pr_management_report.md"
echo ""
echo "🎯 Problème SKYFLY-2 en cours de résolution..."