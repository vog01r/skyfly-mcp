#!/usr/bin/env python3
"""
Script d'analyse de conformité du code aux conventions du projet.
Vérifie les conventions définies dans CONTRIBUTING.md et README.md.
"""

import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass


@dataclass
class ComplianceIssue:
    """Représente un problème de conformité."""
    file: str
    line: int
    type: str
    severity: str  # 'error', 'warning', 'info'
    message: str
    suggestion: str = ""


class CodeComplianceAnalyzer:
    """Analyseur de conformité du code."""
    
    def __init__(self):
        self.issues: List[ComplianceIssue] = []
        self.stats = {
            'files_analyzed': 0,
            'functions_checked': 0,
            'classes_checked': 0,
            'errors': 0,
            'warnings': 0,
            'infos': 0
        }
    
    def analyze_file(self, file_path: Path) -> None:
        """Analyse un fichier Python."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
            
            # Parse AST
            tree = ast.parse(content, filename=str(file_path))
            
            self.stats['files_analyzed'] += 1
            
            # Vérifications
            self._check_python_version_compatibility(file_path, tree)
            self._check_type_hints(file_path, tree, lines)
            self._check_docstrings(file_path, tree, lines)
            self._check_variable_names(file_path, tree)
            self._check_comments_language(file_path, lines)
            self._check_imports_organization(file_path, tree, lines)
            self._check_function_complexity(file_path, tree)
            
        except SyntaxError as e:
            self._add_issue(
                file_path, e.lineno or 0, 'syntax', 'error',
                f"Erreur de syntaxe: {e.msg}",
                "Corriger l'erreur de syntaxe"
            )
        except Exception as e:
            self._add_issue(
                file_path, 0, 'analysis', 'error',
                f"Erreur d'analyse: {str(e)}",
                "Vérifier le fichier manuellement"
            )
    
    def _add_issue(self, file_path: Path, line: int, issue_type: str, 
                   severity: str, message: str, suggestion: str = "") -> None:
        """Ajoute un problème de conformité."""
        try:
            relative_path = str(file_path.relative_to(Path.cwd()))
        except ValueError:
            relative_path = str(file_path)
        
        self.issues.append(ComplianceIssue(
            file=relative_path,
            line=line,
            type=issue_type,
            severity=severity,
            message=message,
            suggestion=suggestion
        ))
        self.stats[f"{severity}s"] += 1
    
    def _check_python_version_compatibility(self, file_path: Path, tree: ast.AST) -> None:
        """Vérifie la compatibilité Python 3.10+."""
        # Chercher les features incompatibles avec Python < 3.10
        for node in ast.walk(tree):
            # Match statements (Python 3.10+)
            if isinstance(node, ast.Match):
                continue  # OK, feature Python 3.10+
            
            # Union types avec | (Python 3.10+)
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
                if hasattr(node.left, 'id') or hasattr(node.right, 'id'):
                    continue  # Potentiellement OK
    
    def _check_type_hints(self, file_path: Path, tree: ast.AST, lines: List[str]) -> None:
        """Vérifie la présence des type hints."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self.stats['functions_checked'] += 1
                
                # Ignorer les méthodes privées et spéciales
                if node.name.startswith('_'):
                    continue
                
                # Vérifier les annotations des paramètres
                missing_params = []
                for arg in node.args.args:
                    if arg.annotation is None and arg.arg != 'self':
                        missing_params.append(arg.arg)
                
                if missing_params:
                    self._add_issue(
                        file_path, node.lineno, 'type_hints', 'warning',
                        f"Fonction '{node.name}': paramètres sans type hints: {', '.join(missing_params)}",
                        "Ajouter des type hints pour tous les paramètres"
                    )
                
                # Vérifier l'annotation de retour
                if node.returns is None and not node.name.startswith('__'):
                    self._add_issue(
                        file_path, node.lineno, 'type_hints', 'warning',
                        f"Fonction '{node.name}': pas de type hint de retour",
                        "Ajouter un type hint de retour (-> Type ou -> None)"
                    )
    
    def _check_docstrings(self, file_path: Path, tree: ast.AST, lines: List[str]) -> None:
        """Vérifie les docstrings des fonctions publiques."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Ignorer les méthodes privées
                if node.name.startswith('_'):
                    continue
                
                # Vérifier la présence d'une docstring
                docstring = ast.get_docstring(node)
                if not docstring:
                    self._add_issue(
                        file_path, node.lineno, 'docstring', 'warning',
                        f"Fonction publique '{node.name}': pas de docstring",
                        "Ajouter une docstring décrivant la fonction, ses paramètres et sa valeur de retour"
                    )
                elif len(docstring.strip()) < 10:
                    self._add_issue(
                        file_path, node.lineno, 'docstring', 'info',
                        f"Fonction '{node.name}': docstring très courte",
                        "Enrichir la docstring avec plus de détails"
                    )
            
            elif isinstance(node, ast.ClassDef):
                self.stats['classes_checked'] += 1
                docstring = ast.get_docstring(node)
                if not docstring:
                    self._add_issue(
                        file_path, node.lineno, 'docstring', 'warning',
                        f"Classe '{node.name}': pas de docstring",
                        "Ajouter une docstring décrivant le rôle de la classe"
                    )
    
    def _check_variable_names(self, file_path: Path, tree: ast.AST) -> None:
        """Vérifie que les noms de variables sont explicites."""
        # Noms de variables à éviter
        bad_names = {'a', 'b', 'c', 'x', 'y', 'z', 'tmp', 'temp', 'data1', 'data2', 'var', 'val'}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                if node.id in bad_names:
                    self._add_issue(
                        file_path, node.lineno, 'naming', 'info',
                        f"Nom de variable peu explicite: '{node.id}'",
                        "Utiliser un nom plus descriptif"
                    )
            
            elif isinstance(node, ast.FunctionDef):
                # Vérifier les noms de fonction
                if len(node.name) < 3 and not node.name.startswith('_'):
                    self._add_issue(
                        file_path, node.lineno, 'naming', 'info',
                        f"Nom de fonction très court: '{node.name}'",
                        "Utiliser un nom plus descriptif"
                    )
    
    def _check_comments_language(self, file_path: Path, lines: List[str]) -> None:
        """Vérifie que les commentaires sont en français ou anglais."""
        # Mots-clés pour détecter d'autres langues
        other_languages = {
            'spanish': ['el', 'la', 'los', 'las', 'un', 'una', 'con', 'por', 'para'],
            'german': ['der', 'die', 'das', 'und', 'oder', 'mit', 'von', 'zu'],
            'italian': ['il', 'la', 'gli', 'le', 'con', 'per', 'di', 'da']
        }
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line.startswith('#') and len(line) > 5:
                comment = line[1:].strip().lower()
                words = comment.split()
                
                for lang, keywords in other_languages.items():
                    if any(word in keywords for word in words):
                        self._add_issue(
                            file_path, i, 'comment_language', 'info',
                            f"Commentaire possiblement en {lang}: {line[:50]}...",
                            "Utiliser le français ou l'anglais pour les commentaires"
                        )
                        break
    
    def _check_imports_organization(self, file_path: Path, tree: ast.AST, lines: List[str]) -> None:
        """Vérifie l'organisation des imports."""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append((node.lineno, node))
        
        if len(imports) > 1:
            # Vérifier si les imports sont groupés
            import_lines = [imp[0] for imp in imports]
            if max(import_lines) - min(import_lines) > len(imports) + 5:
                self._add_issue(
                    file_path, min(import_lines), 'imports', 'info',
                    "Imports dispersés dans le fichier",
                    "Grouper tous les imports en début de fichier"
                )
    
    def _check_function_complexity(self, file_path: Path, tree: ast.AST) -> None:
        """Vérifie la complexité des fonctions."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Compter les niveaux d'imbrication
                max_depth = self._calculate_nesting_depth(node)
                if max_depth > 4:
                    self._add_issue(
                        file_path, node.lineno, 'complexity', 'warning',
                        f"Fonction '{node.name}': imbrication trop profonde ({max_depth} niveaux)",
                        "Refactoriser en fonctions plus petites"
                    )
                
                # Compter les lignes
                if hasattr(node, 'end_lineno') and node.end_lineno:
                    lines_count = node.end_lineno - node.lineno
                    if lines_count > 50:
                        self._add_issue(
                            file_path, node.lineno, 'complexity', 'info',
                            f"Fonction '{node.name}': très longue ({lines_count} lignes)",
                            "Considérer diviser en fonctions plus petites"
                        )
    
    def _calculate_nesting_depth(self, node: ast.AST, current_depth: int = 0) -> int:
        """Calcule la profondeur d'imbrication maximale."""
        max_depth = current_depth
        
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                child_depth = self._calculate_nesting_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = self._calculate_nesting_depth(child, current_depth)
                max_depth = max(max_depth, child_depth)
        
        return max_depth
    
    def generate_report(self) -> str:
        """Génère le rapport de conformité."""
        report = []
        report.append("# 📊 Rapport de Conformité du Code")
        report.append("=" * 50)
        report.append("")
        
        # Statistiques générales
        report.append("## 📈 Statistiques Générales")
        report.append(f"- Fichiers analysés: {self.stats['files_analyzed']}")
        report.append(f"- Fonctions vérifiées: {self.stats['functions_checked']}")
        report.append(f"- Classes vérifiées: {self.stats['classes_checked']}")
        report.append(f"- Erreurs: {self.stats['errors']}")
        report.append(f"- Avertissements: {self.stats['warnings']}")
        report.append(f"- Informations: {self.stats['infos']}")
        report.append("")
        
        # Score de conformité
        total_issues = self.stats['errors'] + self.stats['warnings']
        if total_issues == 0:
            score = 100
        else:
            # Score basé sur la sévérité
            penalty = self.stats['errors'] * 10 + self.stats['warnings'] * 5 + self.stats['infos'] * 1
            score = max(0, 100 - penalty)
        
        report.append(f"## 🎯 Score de Conformité: {score}/100")
        report.append("")
        
        if score >= 90:
            report.append("✅ **EXCELLENT** - Code très conforme aux conventions")
        elif score >= 75:
            report.append("🟡 **BON** - Code globalement conforme avec quelques améliorations possibles")
        elif score >= 60:
            report.append("🟠 **MOYEN** - Code partiellement conforme, améliorations recommandées")
        else:
            report.append("🔴 **FAIBLE** - Code non conforme, corrections nécessaires")
        
        report.append("")
        
        # Grouper les problèmes par type
        issues_by_type = {}
        for issue in self.issues:
            if issue.type not in issues_by_type:
                issues_by_type[issue.type] = []
            issues_by_type[issue.type].append(issue)
        
        # Détails des problèmes
        if self.issues:
            report.append("## 🔍 Détails des Problèmes")
            
            for issue_type, issues in sorted(issues_by_type.items()):
                report.append(f"### {issue_type.replace('_', ' ').title()}")
                
                for issue in sorted(issues, key=lambda x: (x.file, x.line)):
                    severity_icon = {
                        'error': '🔴',
                        'warning': '🟡', 
                        'info': '🔵'
                    }.get(issue.severity, '⚪')
                    
                    report.append(f"{severity_icon} **{issue.file}:{issue.line}** - {issue.message}")
                    if issue.suggestion:
                        report.append(f"   💡 *Suggestion: {issue.suggestion}*")
                    report.append("")
        
        # Recommandations générales
        report.append("## 🎯 Recommandations Générales")
        
        if self.stats['warnings'] > 0:
            report.append("- Ajouter des type hints manquants pour améliorer la lisibilité")
            report.append("- Compléter les docstrings des fonctions publiques")
        
        if self.stats['infos'] > 0:
            report.append("- Améliorer les noms de variables pour plus de clarté")
            report.append("- Organiser les imports en début de fichier")
        
        report.append("- Maintenir la compatibilité Python 3.10+")
        report.append("- Utiliser des commentaires en français ou anglais")
        report.append("")
        
        return "\n".join(report)


def main():
    """Point d'entrée principal."""
    analyzer = CodeComplianceAnalyzer()
    
    # Fichiers Python à analyser
    python_files = [
        Path("server.py"),
        Path("opensky_client.py"), 
        Path("http_server.py"),
        Path("examples/basic_usage.py"),
        Path("aircraftdb/__init__.py"),
        Path("aircraftdb/database.py"),
        Path("aircraftdb/ingest.py"),
        Path("aircraftdb/tools.py")
    ]
    
    # Analyser chaque fichier
    for file_path in python_files:
        if file_path.exists():
            print(f"Analyse de {file_path}...")
            analyzer.analyze_file(file_path)
        else:
            print(f"⚠️  Fichier non trouvé: {file_path}")
    
    # Générer et afficher le rapport
    report = analyzer.generate_report()
    print("\n" + report)
    
    # Sauvegarder le rapport
    with open("compliance_report.md", "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\n📄 Rapport sauvegardé dans: compliance_report.md")
    
    return 0 if analyzer.stats['errors'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())