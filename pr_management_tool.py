#!/usr/bin/env python3
"""
Outil de gestion automatique des Pull Requests pour skyfly-mcp
Résout le problème SKYFLY-2: 6 Pull Requests en attente de review
"""

import subprocess
import json
import sys
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class PRStatus(Enum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    MERGED = "MERGED"
    CLOSED = "CLOSED"

class PRPriority(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class PullRequest:
    number: int
    title: str
    state: str
    author: str
    branch: str
    additions: int
    deletions: int
    files_changed: List[str]
    created_at: str
    url: str
    auto_merge: bool
    
    @property
    def size_category(self) -> str:
        """Catégorise la taille de la PR"""
        total_changes = self.additions + self.deletions
        if total_changes < 50:
            return "small"
        elif total_changes < 200:
            return "medium"
        elif total_changes < 500:
            return "large"
        else:
            return "extra_large"
    
    @property
    def age_days(self) -> int:
        """Calcule l'âge de la PR en jours"""
        created = datetime.fromisoformat(self.created_at.replace('Z', '+00:00'))
        return (datetime.now().astimezone() - created).days

class PRManager:
    def __init__(self):
        self.prs: List[PullRequest] = []
        self.conflicts: Dict[int, List[int]] = {}
        
    def fetch_prs(self) -> None:
        """Récupère toutes les PRs ouvertes"""
        try:
            # Récupérer la liste des PRs
            result = subprocess.run(
                ['gh', 'pr', 'list', '--state', 'open', '--json', 
                 'number,title,state,author,headRefName,additions,deletions,createdAt,url,autoMergeRequest'],
                capture_output=True, text=True, check=True
            )
            
            prs_data = json.loads(result.stdout)
            
            for pr_data in prs_data:
                # Récupérer les fichiers modifiés pour chaque PR
                files_result = subprocess.run(
                    ['gh', 'pr', 'diff', str(pr_data['number']), '--name-only'],
                    capture_output=True, text=True, check=True
                )
                
                files_changed = [f.strip() for f in files_result.stdout.split('\n') if f.strip()]
                
                pr = PullRequest(
                    number=pr_data['number'],
                    title=pr_data['title'],
                    state=pr_data['state'],
                    author=pr_data['author']['login'],
                    branch=pr_data['headRefName'],
                    additions=pr_data['additions'],
                    deletions=pr_data['deletions'],
                    files_changed=files_changed,
                    created_at=pr_data['createdAt'],
                    url=pr_data['url'],
                    auto_merge=bool(pr_data.get('autoMergeRequest'))
                )
                
                self.prs.append(pr)
                
        except subprocess.CalledProcessError as e:
            print(f"Erreur lors de la récupération des PRs: {e}")
            sys.exit(1)
    
    def detect_conflicts(self) -> None:
        """Détecte les conflits potentiels entre PRs"""
        self.conflicts = {}
        
        for i, pr1 in enumerate(self.prs):
            for j, pr2 in enumerate(self.prs[i+1:], i+1):
                # Vérifier si les PRs modifient les mêmes fichiers
                common_files = set(pr1.files_changed) & set(pr2.files_changed)
                if common_files:
                    if pr1.number not in self.conflicts:
                        self.conflicts[pr1.number] = []
                    if pr2.number not in self.conflicts:
                        self.conflicts[pr2.number] = []
                    
                    self.conflicts[pr1.number].append(pr2.number)
                    self.conflicts[pr2.number].append(pr1.number)
    
    def prioritize_prs(self) -> List[PullRequest]:
        """Priorise les PRs selon différents critères"""
        def priority_score(pr: PullRequest) -> int:
            score = 0
            
            # Priorité par âge (plus ancien = plus prioritaire)
            score += pr.age_days * 10
            
            # Priorité par taille (plus petit = plus prioritaire)
            size_scores = {"small": 100, "medium": 50, "large": 20, "extra_large": 5}
            score += size_scores.get(pr.size_category, 0)
            
            # Pénalité pour les conflits
            conflicts_count = len(self.conflicts.get(pr.number, []))
            score -= conflicts_count * 25
            
            # Bonus pour les PRs prêtes (non-draft)
            if pr.state != "DRAFT":
                score += 200
            
            return score
        
        return sorted(self.prs, key=priority_score, reverse=True)
    
    def suggest_actions(self) -> Dict[str, Any]:
        """Suggère des actions pour résoudre les problèmes de PRs"""
        suggestions = {
            "immediate_actions": [],
            "consolidation_opportunities": [],
            "auto_merge_candidates": [],
            "draft_to_ready": [],
            "close_candidates": []
        }
        
        prioritized_prs = self.prioritize_prs()
        
        for pr in prioritized_prs:
            # PRs candidates pour l'auto-merge
            if (pr.size_category == "small" and 
                pr.state != "DRAFT" and 
                len(self.conflicts.get(pr.number, [])) == 0):
                suggestions["auto_merge_candidates"].append(pr)
            
            # PRs à passer de draft à ready
            if pr.state == "DRAFT":
                suggestions["draft_to_ready"].append(pr)
            
            # PRs à fermer (très anciennes ou très grosses)
            if pr.age_days > 30 or pr.size_category == "extra_large":
                suggestions["close_candidates"].append(pr)
        
        # Opportunités de consolidation
        conflict_groups = self._find_consolidation_groups()
        suggestions["consolidation_opportunities"] = conflict_groups
        
        return suggestions
    
    def _find_consolidation_groups(self) -> List[List[int]]:
        """Trouve les groupes de PRs qui peuvent être consolidées"""
        groups = []
        processed = set()
        
        for pr_num, conflicts in self.conflicts.items():
            if pr_num in processed:
                continue
            
            # Créer un groupe avec toutes les PRs en conflit
            group = {pr_num}
            to_process = set(conflicts)
            
            while to_process:
                current = to_process.pop()
                if current not in processed:
                    group.add(current)
                    # Ajouter les conflits de cette PR
                    to_process.update(self.conflicts.get(current, []))
            
            if len(group) > 1:
                groups.append(list(group))
                processed.update(group)
        
        return groups
    
    def generate_report(self) -> str:
        """Génère un rapport détaillé sur l'état des PRs"""
        suggestions = self.suggest_actions()
        
        report = f"""
# Rapport de Gestion des Pull Requests
## Problème SKYFLY-2: {len(self.prs)} Pull Requests en attente de review

### État Actuel
- **Total PRs ouvertes**: {len(self.prs)}
- **PRs en draft**: {len([pr for pr in self.prs if pr.state == 'DRAFT'])}
- **PRs prêtes pour review**: {len([pr for pr in self.prs if pr.state != 'DRAFT'])}
- **Conflits détectés**: {len(self.conflicts)} PRs avec conflits

### Analyse par Taille
"""
        
        size_counts = {}
        for pr in self.prs:
            size_counts[pr.size_category] = size_counts.get(pr.size_category, 0) + 1
        
        for size, count in size_counts.items():
            report += f"- **{size.title()}**: {count} PRs\n"
        
        report += f"""
### Actions Recommandées

#### 1. PRs Candidates pour Auto-Merge ({len(suggestions['auto_merge_candidates'])})
"""
        for pr in suggestions['auto_merge_candidates']:
            report += f"- PR #{pr.number}: {pr.title} ({pr.size_category}, {pr.age_days} jours)\n"
        
        report += f"""
#### 2. PRs à Passer de Draft à Ready ({len(suggestions['draft_to_ready'])})
"""
        for pr in suggestions['draft_to_ready']:
            report += f"- PR #{pr.number}: {pr.title} ({pr.size_category}, {pr.age_days} jours)\n"
        
        report += f"""
#### 3. Opportunités de Consolidation ({len(suggestions['consolidation_opportunities'])} groupes)
"""
        for i, group in enumerate(suggestions['consolidation_opportunities'], 1):
            report += f"- **Groupe {i}**: PRs {', '.join(f'#{num}' for num in group)}\n"
            # Afficher les fichiers en conflit
            common_files = set()
            for pr_num in group:
                pr = next((p for p in self.prs if p.number == pr_num), None)
                if pr:
                    common_files.update(pr.files_changed)
            report += f"  Fichiers concernés: {', '.join(sorted(common_files))}\n"
        
        report += f"""
#### 4. PRs Candidates à la Fermeture ({len(suggestions['close_candidates'])})
"""
        for pr in suggestions['close_candidates']:
            reason = "Très ancienne" if pr.age_days > 30 else "Très volumineuse"
            report += f"- PR #{pr.number}: {pr.title} ({reason}, {pr.age_days} jours, {pr.size_category})\n"
        
        return report
    
    def execute_auto_actions(self, dry_run: bool = True) -> None:
        """Exécute automatiquement certaines actions"""
        suggestions = self.suggest_actions()
        
        print(f"{'[DRY RUN] ' if dry_run else ''}Exécution des actions automatiques...")
        
        # Activer l'auto-merge pour les PRs candidates
        for pr in suggestions['auto_merge_candidates']:
            if not dry_run:
                try:
                    subprocess.run(['gh', 'pr', 'merge', str(pr.number), '--auto', '--squash'], 
                                 check=True)
                    print(f"✅ Auto-merge activé pour PR #{pr.number}")
                except subprocess.CalledProcessError:
                    print(f"❌ Échec activation auto-merge pour PR #{pr.number}")
            else:
                print(f"[DRY RUN] Activerait auto-merge pour PR #{pr.number}")
        
        # Marquer les PRs draft comme ready (seulement les petites)
        small_drafts = [pr for pr in suggestions['draft_to_ready'] 
                       if pr.size_category in ['small', 'medium']]
        
        for pr in small_drafts:
            if not dry_run:
                try:
                    subprocess.run(['gh', 'pr', 'ready', str(pr.number)], check=True)
                    print(f"✅ PR #{pr.number} marquée comme ready")
                except subprocess.CalledProcessError:
                    print(f"❌ Échec marquage ready pour PR #{pr.number}")
            else:
                print(f"[DRY RUN] Marquerait PR #{pr.number} comme ready")

def main():
    """Point d'entrée principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Outil de gestion des PRs pour skyfly-mcp")
    parser.add_argument('--action', choices=['report', 'auto', 'execute'], 
                       default='report', help='Action à effectuer')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Mode simulation (pas de modifications réelles)')
    
    args = parser.parse_args()
    
    manager = PRManager()
    manager.fetch_prs()
    manager.detect_conflicts()
    
    if args.action == 'report':
        print(manager.generate_report())
    elif args.action == 'auto':
        manager.execute_auto_actions(dry_run=True)
    elif args.action == 'execute':
        manager.execute_auto_actions(dry_run=args.dry_run)

if __name__ == "__main__":
    main()