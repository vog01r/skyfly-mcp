#!/usr/bin/env python3
"""
Script de gestion automatique des Pull Requests pour Skyfly MCP.

Ce script aide à résoudre le problème des PRs en attente en:
1. Analysant l'état des PRs ouvertes
2. Identifiant les PRs prêtes à être mergées
3. Détectant les conflits et dépendances
4. Proposant un plan d'action automatisé

Référence issue: SKYFLY-2
"""

import subprocess
import json
import sys
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PullRequest:
    """Représente une Pull Request."""
    number: int
    title: str
    state: str
    branch: str
    author: str
    created_at: str
    additions: int
    deletions: int
    is_draft: bool
    mergeable: bool = None


class PRManager:
    """Gestionnaire automatique des Pull Requests."""
    
    def __init__(self):
        self.prs: List[PullRequest] = []
    
    def fetch_open_prs(self) -> List[PullRequest]:
        """Récupère la liste des PRs ouvertes."""
        try:
            # Récupérer la liste des PRs
            result = subprocess.run(
                ["gh", "pr", "list", "--state", "open", "--json", "number,title,state,headRefName,author,createdAt,additions,deletions,isDraft"],
                capture_output=True,
                text=True,
                check=True
            )
            
            pr_data = json.loads(result.stdout)
            self.prs = []
            
            for pr in pr_data:
                self.prs.append(PullRequest(
                    number=pr["number"],
                    title=pr["title"],
                    state=pr["state"],
                    branch=pr["headRefName"],
                    author=pr["author"]["login"],
                    created_at=pr["createdAt"],
                    additions=pr["additions"],
                    deletions=pr["deletions"],
                    is_draft=pr["isDraft"]
                ))
            
            return self.prs
            
        except subprocess.CalledProcessError as e:
            print(f"Erreur lors de la récupération des PRs: {e}")
            return []
    
    def check_pr_conflicts(self, pr_number: int) -> bool:
        """Vérifie si une PR a des conflits."""
        try:
            result = subprocess.run(
                ["gh", "pr", "view", str(pr_number), "--json", "mergeable"],
                capture_output=True,
                text=True,
                check=True
            )
            
            data = json.loads(result.stdout)
            return data.get("mergeable", "UNKNOWN") == "CONFLICTING"
            
        except subprocess.CalledProcessError:
            return True  # Assume conflict if can't check
    
    def analyze_pr_dependencies(self) -> Dict[str, List[str]]:
        """Analyse les dépendances entre PRs basées sur les fichiers modifiés."""
        dependencies = {}
        
        for pr in self.prs:
            dependencies[str(pr.number)] = []
            
            # Logique simple de dépendance basée sur les titres
            if "dépendances" in pr.title.lower() or "requirements" in pr.title.lower():
                dependencies[str(pr.number)] = []  # Aucune dépendance
            elif "conformité" in pr.title.lower() or "conventions" in pr.title.lower():
                dependencies[str(pr.number)] = ["requirements"]
            elif "lisibilité" in pr.title.lower() or "refactor" in pr.title.lower():
                dependencies[str(pr.number)] = ["conformité", "conventions"]
        
        return dependencies
    
    def generate_action_plan(self) -> Dict[str, Any]:
        """Génère un plan d'action pour traiter les PRs."""
        plan = {
            "summary": {
                "total_prs": len(self.prs),
                "draft_prs": len([pr for pr in self.prs if pr.is_draft]),
                "ready_prs": len([pr for pr in self.prs if not pr.is_draft]),
                "analysis_date": datetime.now().isoformat()
            },
            "actions": [],
            "recommendations": []
        }
        
        # Analyser chaque PR
        for pr in self.prs:
            action = {
                "pr_number": pr.number,
                "title": pr.title,
                "current_state": "DRAFT" if pr.is_draft else "OPEN",
                "recommended_action": "",
                "priority": "medium",
                "reason": ""
            }
            
            # Déterminer l'action recommandée
            if pr.is_draft:
                if "documentation" in pr.title.lower() or "revue" in pr.title.lower():
                    action["recommended_action"] = "CLOSE"
                    action["reason"] = "PR de documentation - peut être consolidée"
                    action["priority"] = "low"
                elif "dépendances" in pr.title.lower():
                    action["recommended_action"] = "MERGE"
                    action["reason"] = "Mise à jour critique des dépendances"
                    action["priority"] = "high"
                elif "conformité" in pr.title.lower():
                    action["recommended_action"] = "MERGE"
                    action["reason"] = "Améliorations importantes de la qualité du code"
                    action["priority"] = "high"
                else:
                    action["recommended_action"] = "REVIEW"
                    action["reason"] = "Nécessite une review avant merge"
                    action["priority"] = "medium"
            else:
                # PR déjà ready
                has_conflicts = self.check_pr_conflicts(pr.number)
                if has_conflicts:
                    action["recommended_action"] = "RESOLVE_CONFLICTS"
                    action["reason"] = "Conflits détectés - résolution nécessaire"
                    action["priority"] = "high"
                else:
                    action["recommended_action"] = "MERGE"
                    action["reason"] = "Prête à être mergée"
                    action["priority"] = "high"
            
            plan["actions"].append(action)
        
        # Générer des recommandations générales
        if plan["summary"]["draft_prs"] > 3:
            plan["recommendations"].append(
                "Trop de PRs en DRAFT - convertir les PRs importantes en 'ready for review'"
            )
        
        if plan["summary"]["total_prs"] > 5:
            plan["recommendations"].append(
                "Trop de PRs ouvertes - fermer les PRs obsolètes et merger les PRs prêtes"
            )
        
        plan["recommendations"].extend([
            "Activer l'auto-merge pour les petites PRs non critiques",
            "Mettre en place des règles de protection de branche",
            "Créer un workflow automatisé pour les PRs de documentation"
        ])
        
        return plan
    
    def execute_action_plan(self, plan: Dict[str, Any], dry_run: bool = True) -> None:
        """Exécute le plan d'action (dry-run par défaut)."""
        print(f"{'[DRY RUN] ' if dry_run else ''}Exécution du plan d'action...")
        
        for action in sorted(plan["actions"], key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["priority"]]):
            pr_num = action["pr_number"]
            recommended_action = action["recommended_action"]
            
            print(f"\nPR #{pr_num}: {action['title']}")
            print(f"Action recommandée: {recommended_action}")
            print(f"Raison: {action['reason']}")
            print(f"Priorité: {action['priority']}")
            
            if not dry_run:
                try:
                    if recommended_action == "MERGE":
                        # Marquer comme ready si c'est un draft
                        if action["current_state"] == "DRAFT":
                            subprocess.run(["gh", "pr", "ready", str(pr_num)], check=True)
                        
                        # Merger
                        subprocess.run([
                            "gh", "pr", "merge", str(pr_num), 
                            "--squash", 
                            "--subject", f"auto-merge: {action['title']}"
                        ], check=True)
                        print(f"✅ PR #{pr_num} mergée avec succès")
                        
                    elif recommended_action == "CLOSE":
                        subprocess.run(["gh", "pr", "close", str(pr_num)], check=True)
                        print(f"✅ PR #{pr_num} fermée")
                        
                    elif recommended_action == "REVIEW":
                        subprocess.run(["gh", "pr", "ready", str(pr_num)], check=True)
                        print(f"✅ PR #{pr_num} marquée comme ready for review")
                        
                except subprocess.CalledProcessError as e:
                    print(f"❌ Erreur lors du traitement de PR #{pr_num}: {e}")
            else:
                print("  [Simulation - aucune action réelle exécutée]")


def main():
    """Point d'entrée principal."""
    manager = PRManager()
    
    print("🔍 Analyse des Pull Requests en attente...")
    prs = manager.fetch_open_prs()
    
    if not prs:
        print("✅ Aucune PR ouverte trouvée.")
        return
    
    print(f"📊 {len(prs)} PR(s) ouverte(s) détectée(s)")
    
    # Générer le plan d'action
    plan = manager.generate_action_plan()
    
    # Afficher le résumé
    print(f"\n📈 Résumé:")
    print(f"  Total PRs: {plan['summary']['total_prs']}")
    print(f"  PRs en DRAFT: {plan['summary']['draft_prs']}")
    print(f"  PRs prêtes: {plan['summary']['ready_prs']}")
    
    # Afficher les recommandations
    print(f"\n💡 Recommandations:")
    for rec in plan["recommendations"]:
        print(f"  • {rec}")
    
    # Demander confirmation pour l'exécution
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        response = input("\n⚠️  Exécuter le plan d'action? (y/N): ")
        if response.lower() == 'y':
            manager.execute_action_plan(plan, dry_run=False)
        else:
            print("Exécution annulée.")
    else:
        print("\n🔍 Mode simulation activé (utilisez --execute pour appliquer les changements)")
        manager.execute_action_plan(plan, dry_run=True)


if __name__ == "__main__":
    main()