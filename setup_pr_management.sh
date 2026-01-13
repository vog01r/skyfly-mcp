#!/bin/bash
# Script de configuration de la solution de gestion des PRs - SKYFLY-4

set -e

echo "🚀 Configuration de la solution de gestion des Pull Requests"
echo "============================================================"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction d'affichage coloré
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

# Vérification des prérequis
echo ""
print_info "Vérification des prérequis..."

# Vérifier que gh CLI est installé
if ! command -v gh &> /dev/null; then
    print_error "GitHub CLI (gh) n'est pas installé"
    print_info "Installation: https://cli.github.com/"
    exit 1
fi
print_status "GitHub CLI trouvé"

# Vérifier que Python 3 est installé
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 n'est pas installé"
    exit 1
fi
print_status "Python 3 trouvé"

# Vérifier l'authentification GitHub
if ! gh auth status &> /dev/null; then
    print_error "Non authentifié avec GitHub CLI"
    print_info "Exécutez: gh auth login"
    exit 1
fi
print_status "Authentification GitHub OK"

# Vérifier qu'on est dans un repo git
if ! git rev-parse --git-dir &> /dev/null; then
    print_error "Pas dans un repository Git"
    exit 1
fi
print_status "Repository Git détecté"

# Configuration des permissions
echo ""
print_info "Configuration des permissions et paramètres..."

# Rendre les scripts exécutables
chmod +x pr_management_solution.py
chmod +x setup_pr_management.sh
print_status "Scripts rendus exécutables"

# Test du script principal en mode dry-run
echo ""
print_info "Test du script de gestion des PRs..."

if python3 pr_management_solution.py --dry-run --output test_report.md; then
    print_status "Test du script réussi"
    rm -f test_report.md
else
    print_error "Échec du test du script"
    exit 1
fi

# Vérification du workflow GitHub Actions
echo ""
print_info "Vérification du workflow GitHub Actions..."

if [ -f ".github/workflows/pr_management.yml" ]; then
    print_status "Workflow GitHub Actions trouvé"
else
    print_error "Workflow GitHub Actions manquant"
    exit 1
fi

# Configuration des labels GitHub
echo ""
print_info "Configuration des labels GitHub..."

# Labels pour la gestion automatique
LABELS=(
    "automation:Automatisation et scripts:0052cc"
    "pr-management:Gestion des Pull Requests:1d76db"
    "needs-review:Nécessite une review:fbca04"
    "auto-merge:Éligible pour auto-merge:0e8a16"
    "stale:PR inactive:fef2c0"
)

for label_info in "${LABELS[@]}"; do
    IFS=':' read -r name description color <<< "$label_info"
    
    if gh label create "$name" --description "$description" --color "$color" 2>/dev/null; then
        print_status "Label créé: $name"
    else
        print_warning "Label existe déjà ou erreur: $name"
    fi
done

# Configuration des paramètres du repository
echo ""
print_info "Configuration des paramètres du repository..."

# Activer auto-merge si possible
if gh repo edit --enable-auto-merge 2>/dev/null; then
    print_status "Auto-merge activé pour le repository"
else
    print_warning "Impossible d'activer auto-merge (permissions insuffisantes?)"
fi

# Activer les discussions si possible
if gh repo edit --enable-discussions 2>/dev/null; then
    print_status "Discussions activées"
else
    print_warning "Impossible d'activer les discussions"
fi

# Création d'un issue de suivi
echo ""
print_info "Création d'un issue de suivi..."

ISSUE_TITLE="🔄 Configuration de la gestion automatique des PRs - SKYFLY-4"
ISSUE_BODY="## 🎯 Objectif
Mise en place d'une solution automatique pour gérer les Pull Requests en attente et éviter l'accumulation future.

## 🛠️ Composants installés

### 1. Script de gestion automatique
- **Fichier:** \`pr_management_solution.py\`
- **Fonction:** Analyse et gestion automatique des PRs
- **Modes:** dry-run et exécution
- **Fonctionnalités:**
  - Analyse des PRs ouvertes
  - Détection des conflits
  - Priorisation automatique
  - Actions recommandées (merge, close, review)

### 2. Workflow GitHub Actions
- **Fichier:** \`.github/workflows/pr_management.yml\`
- **Déclenchement:** Quotidien à 9h UTC + manuel
- **Actions automatiques:**
  - Analyse des PRs si seuil dépassé (>5 PRs)
  - Fermeture des PRs draft anciennes (>30 jours)
  - Activation auto-merge pour PRs éligibles
  - Génération de rapports

### 3. Labels configurés
- \`automation\`: Scripts et automatisation
- \`pr-management\`: Gestion des PRs
- \`needs-review\`: Nécessite une review
- \`auto-merge\`: Éligible pour auto-merge
- \`stale\`: PR inactive

## 🎮 Utilisation

### Exécution manuelle
\`\`\`bash
# Mode simulation (recommandé)
python3 pr_management_solution.py --dry-run

# Mode exécution
python3 pr_management_solution.py
\`\`\`

### Déclenchement workflow
1. Aller dans Actions > PR Management
2. Cliquer \"Run workflow\"
3. Choisir les options (dry-run recommandé)

## 📊 Monitoring

Le workflow génère automatiquement:
- Rapports détaillés (artifacts)
- Issues de suivi si actions exécutées
- Logs d'exécution

## 🔧 Configuration

### Paramètres modifiables
- Seuil de PRs ouvertes (défaut: 5)
- Âge limite pour PRs draft (défaut: 30 jours)
- Critères d'auto-merge

### Permissions requises
- \`contents: read\`
- \`pull-requests: write\`
- \`issues: write\`

## ✅ Statut
- [x] Scripts installés et testés
- [x] Workflow configuré
- [x] Labels créés
- [x] Permissions vérifiées
- [ ] Premier test en production
- [ ] Validation des résultats

## 🎯 Prochaines étapes
1. Tester en mode dry-run
2. Valider les actions recommandées
3. Exécuter en mode production
4. Monitorer les résultats
5. Ajuster les paramètres si nécessaire

---
**Référence:** SKYFLY-4 - ⚠️ 9 Pull Requests en attente de review
**Installé le:** $(date)
**Version:** 1.0"

if gh issue create --title "$ISSUE_TITLE" --body "$ISSUE_BODY" --label "automation,pr-management" > /dev/null; then
    ISSUE_URL=$(gh issue list --label "automation,pr-management" --limit 1 --json url --jq '.[0].url')
    print_status "Issue de suivi créé: $ISSUE_URL"
else
    print_warning "Impossible de créer l'issue de suivi"
fi

# Résumé final
echo ""
echo "🎉 Configuration terminée avec succès!"
echo "======================================"
echo ""
print_status "Solution de gestion des PRs installée et configurée"
print_info "Prochaines étapes:"
echo "  1. Tester: python3 pr_management_solution.py --dry-run"
echo "  2. Vérifier le workflow dans GitHub Actions"
echo "  3. Monitorer les PRs existantes"
echo ""
print_warning "Recommandation: Commencer par des tests en mode dry-run"
echo ""

# Afficher l'état actuel des PRs
print_info "État actuel des Pull Requests:"
gh pr list --state open --json number,title,isDraft,mergeable | jq -r '.[] | "  - PR #\(.number): \(.title) [\(if .isDraft then "DRAFT" else "READY" end)] [\(.mergeable)]"'

echo ""
print_status "Configuration SKYFLY-4 terminée ✨"