#!/usr/bin/env python3
"""
Solution de gestion automatique des Pull Requests pour SKYFLY-4
Gère les 9 PRs en attente de review dans le repository vog01r/skyfly-mcp
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class PRStatus(Enum):
    OPEN = "OPEN"
    DRAFT = "DRAFT"
    MERGED = "MERGED"
    CLOSED = "CLOSED"

class PRAction(Enum):
    MERGE = "merge"
    CLOSE = "close"
    CONVERT_TO_READY = "ready"
    KEEP_OPEN = "keep"
    NEEDS_REVIEW = "review"

@dataclass
class PRInfo:
    number: int
    title: str
    state: str
    is_draft: bool
    mergeable: str
    branch: str
    created_at: datetime
    commits_count: int
    body: str
    review_decision: str
    
    @property
    def age_days(self) -> int:
        from datetime import timezone
        now = datetime.now(timezone.utc)
        # Convertir created_at en UTC si nécessaire
        if self.created_at.tzinfo is None:
            created_at_utc = self.created_at.replace(tzinfo=timezone.utc)
        else:
            created_at_utc = self.created_at
        return (now - created_at_utc).days
    
    @property
    def is_security_related(self) -> bool:
        security_keywords = ['security', 'sécurité', 'vulnerability', 'vulnérabilité', 'audit']
        return any(keyword in self.title.lower() or keyword in self.body.lower() 
                  for keyword in security_keywords)
    
    @property
    def is_review_related(self) -> bool:
        review_keywords = ['review', 'revue', 'analyse', 'rapport']
        return any(keyword in self.title.lower() for keyword in review_keywords)
    
    @property
    def priority_score(self) -> int:
        """Calcule un score de priorité (plus élevé = plus prioritaire)"""
        score = 0
        
        # Priorité basée sur le type
        if self.is_security_related:
            score += 100
        if not self.is_draft:
            score += 50
        if self.mergeable == "MERGEABLE":
            score += 30
        if self.is_review_related:
            score -= 20  # Les rapports sont moins prioritaires
        
        # Pénalité pour l'âge (plus vieux = moins prioritaire pour les drafts)
        if self.is_draft and self.age_days > 1:
            score -= self.age_days * 5
            
        return score

class PRManager:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.actions_taken = []
        
    def get_open_prs(self) -> List[PRInfo]:
        """Récupère toutes les PRs ouvertes"""
        try:
            result = subprocess.run([
                'gh', 'pr', 'list', '--state', 'open', '--json',
                'number,title,state,isDraft,mergeable,headRefName,createdAt,commits,body,reviewDecision'
            ], capture_output=True, text=True, check=True)
            
            prs_data = json.loads(result.stdout)
            prs = []
            
            for pr_data in prs_data:
                # Gérer le format ISO avec Z
                created_at_str = pr_data['createdAt']
                if created_at_str.endswith('Z'):
                    created_at_str = created_at_str[:-1] + '+00:00'
                created_at = datetime.fromisoformat(created_at_str)
                pr = PRInfo(
                    number=pr_data['number'],
                    title=pr_data['title'],
                    state=pr_data['state'],
                    is_draft=pr_data['isDraft'],
                    mergeable=pr_data['mergeable'],
                    branch=pr_data['headRefName'],
                    created_at=created_at,
                    commits_count=len(pr_data['commits']),
                    body=pr_data['body'] or "",
                    review_decision=pr_data['reviewDecision'] or ""
                )
                prs.append(pr)
            
            return sorted(prs, key=lambda x: x.priority_score, reverse=True)
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Erreur lors de la récupération des PRs: {e}")
            return []
    
    def analyze_pr_conflicts(self, prs: List[PRInfo]) -> Dict[int, List[int]]:
        """Analyse les conflits potentiels entre PRs"""
        conflicts = {}
        
        # Grouper par types de modifications
        security_prs = [pr for pr in prs if pr.is_security_related]
        refactor_prs = [pr for pr in prs if 'refactor' in pr.title.lower() or 'lisibilité' in pr.title.lower()]
        review_prs = [pr for pr in prs if pr.is_review_related]
        
        # Les PRs de refactoring peuvent entrer en conflit
        if len(refactor_prs) > 1:
            for i, pr1 in enumerate(refactor_prs):
                for pr2 in refactor_prs[i+1:]:
                    conflicts.setdefault(pr1.number, []).append(pr2.number)
        
        return conflicts
    
    def determine_action(self, pr: PRInfo, conflicts: Dict[int, List[int]]) -> Tuple[PRAction, str]:
        """Détermine l'action à prendre pour une PR"""
        
        # PRs très anciennes en draft -> fermer
        if pr.is_draft and pr.age_days > 2:
            if pr.is_review_related:
                return PRAction.CLOSE, f"PR de review draft ancienne ({pr.age_days} jours)"
            
        # PRs de sécurité mergeable -> prioriser
        if pr.is_security_related and pr.mergeable == "MERGEABLE" and not pr.is_draft:
            return PRAction.MERGE, "PR de sécurité prête à merger"
        
        # PRs draft récentes avec contenu utile -> convertir en ready
        if pr.is_draft and pr.age_days <= 1 and pr.is_security_related:
            return PRAction.CONVERT_TO_READY, "PR de sécurité récente à convertir"
        
        # PR #13 (backlog solution) -> prioriser
        if pr.number == 13:
            return PRAction.NEEDS_REVIEW, "Solution de gestion des PRs - priorité haute"
        
        # PRs avec conflits -> analyser
        if pr.number in conflicts:
            return PRAction.KEEP_OPEN, f"Conflits potentiels avec PRs: {conflicts[pr.number]}"
        
        # PRs mergeable non-draft -> review
        if pr.mergeable == "MERGEABLE" and not pr.is_draft:
            return PRAction.NEEDS_REVIEW, "PR prête pour review"
        
        # PRs de review multiples -> fermer les doublons
        if pr.is_review_related and pr.is_draft:
            return PRAction.CLOSE, "Rapport de review en doublon"
        
        return PRAction.KEEP_OPEN, "Garder ouverte pour analyse"
    
    def execute_action(self, pr: PRInfo, action: PRAction, reason: str) -> bool:
        """Exécute l'action déterminée"""
        action_desc = f"PR #{pr.number}: {action.value} - {reason}"
        
        if self.dry_run:
            print(f"🔍 [DRY-RUN] {action_desc}")
            self.actions_taken.append(action_desc)
            return True
        
        try:
            if action == PRAction.CLOSE:
                subprocess.run(['gh', 'pr', 'close', str(pr.number), 
                              '--comment', f"Fermée automatiquement: {reason}"], 
                              check=True)
                print(f"❌ Fermée: PR #{pr.number}")
                
            elif action == PRAction.CONVERT_TO_READY:
                subprocess.run(['gh', 'pr', 'ready', str(pr.number)], check=True)
                print(f"✅ Convertie en ready: PR #{pr.number}")
                
            elif action == PRAction.MERGE:
                # Vérifier que c'est vraiment mergeable
                subprocess.run(['gh', 'pr', 'merge', str(pr.number), '--squash'], check=True)
                print(f"🎉 Mergée: PR #{pr.number}")
                
            elif action == PRAction.NEEDS_REVIEW:
                # Ajouter un label ou commentaire pour demander review
                subprocess.run(['gh', 'pr', 'comment', str(pr.number),
                              '--body', f"🔍 Cette PR nécessite une review: {reason}"], 
                              check=True)
                print(f"👀 Review demandée: PR #{pr.number}")
            
            self.actions_taken.append(action_desc)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Erreur lors de l'exécution de l'action pour PR #{pr.number}: {e}")
            return False
    
    def generate_report(self, prs: List[PRInfo], conflicts: Dict[int, List[int]]) -> str:
        """Génère un rapport détaillé"""
        report = []
        report.append("# 📊 Rapport de Gestion des Pull Requests - SKYFLY-4")
        report.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Nombre total de PRs ouvertes:** {len(prs)}")
        report.append("")
        
        # Statistiques
        draft_count = sum(1 for pr in prs if pr.is_draft)
        ready_count = len(prs) - draft_count
        mergeable_count = sum(1 for pr in prs if pr.mergeable == "MERGEABLE")
        security_count = sum(1 for pr in prs if pr.is_security_related)
        
        report.append("## 📈 Statistiques")
        report.append(f"- **PRs Draft:** {draft_count}")
        report.append(f"- **PRs Ready:** {ready_count}")
        report.append(f"- **PRs Mergeable:** {mergeable_count}")
        report.append(f"- **PRs Sécurité:** {security_count}")
        report.append("")
        
        # Analyse par PR
        report.append("## 🔍 Analyse Détaillée")
        for pr in prs:
            action, reason = self.determine_action(pr, conflicts)
            status_icon = "📝" if pr.is_draft else "✅"
            merge_icon = "🟢" if pr.mergeable == "MERGEABLE" else "🟡" if pr.mergeable == "CONFLICTING" else "🔴"
            
            report.append(f"### {status_icon} PR #{pr.number}: {pr.title}")
            report.append(f"- **Statut:** {pr.state} {'(Draft)' if pr.is_draft else '(Ready)'}")
            report.append(f"- **Mergeable:** {merge_icon} {pr.mergeable}")
            report.append(f"- **Branche:** `{pr.branch}`")
            report.append(f"- **Âge:** {pr.age_days} jours")
            report.append(f"- **Score priorité:** {pr.priority_score}")
            report.append(f"- **Action recommandée:** {action.value} - {reason}")
            report.append("")
        
        # Conflits
        if conflicts:
            report.append("## ⚠️ Conflits Détectés")
            for pr_num, conflicting_prs in conflicts.items():
                report.append(f"- **PR #{pr_num}** en conflit avec: {', '.join(f'#{n}' for n in conflicting_prs)}")
            report.append("")
        
        # Actions prises
        if self.actions_taken:
            report.append("## 🎯 Actions Exécutées")
            for action in self.actions_taken:
                report.append(f"- {action}")
            report.append("")
        
        # Recommandations
        report.append("## 💡 Recommandations")
        report.append("1. **Prioriser les PRs de sécurité** - Merger en premier")
        report.append("2. **Fermer les rapports de review dupliqués** - Garder le plus récent")
        report.append("3. **Convertir les PRs draft utiles en ready** - Pour faciliter la review")
        report.append("4. **Résoudre les conflits de refactoring** - Merger par ordre de priorité")
        report.append("5. **Mettre en place un workflow automatique** - Pour éviter l'accumulation future")
        
        return "\n".join(report)
    
    def run_analysis(self) -> str:
        """Lance l'analyse complète"""
        print("🚀 Démarrage de l'analyse des Pull Requests...")
        
        # Récupération des PRs
        prs = self.get_open_prs()
        if not prs:
            return "❌ Aucune PR trouvée"
        
        print(f"📋 {len(prs)} PRs trouvées")
        
        # Analyse des conflits
        conflicts = self.analyze_pr_conflicts(prs)
        if conflicts:
            print(f"⚠️ {len(conflicts)} conflits détectés")
        
        # Exécution des actions
        print("\n🎯 Exécution des actions recommandées...")
        for pr in prs:
            action, reason = self.determine_action(pr, conflicts)
            if action != PRAction.KEEP_OPEN:
                self.execute_action(pr, action, reason)
        
        # Génération du rapport
        report = self.generate_report(prs, conflicts)
        
        print(f"\n✅ Analyse terminée. {len(self.actions_taken)} actions exécutées.")
        return report

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Gestion automatique des PRs - SKYFLY-4")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Mode simulation - n'exécute pas les actions")
    parser.add_argument("--output", "-o", default="pr_management_report.md",
                       help="Fichier de sortie pour le rapport")
    
    args = parser.parse_args()
    
    # Exécution
    manager = PRManager(dry_run=args.dry_run)
    report = manager.run_analysis()
    
    # Sauvegarde du rapport
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"📄 Rapport sauvegardé: {args.output}")
    
    if args.dry_run:
        print("\n🔍 Mode DRY-RUN activé - aucune action réelle exécutée")
        print("Pour exécuter les actions, relancez sans --dry-run")

if __name__ == "__main__":
    main()