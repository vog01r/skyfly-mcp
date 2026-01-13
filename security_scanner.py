#!/usr/bin/env python3
"""
Scanner de sécurité automatique pour le projet Skyfly MCP.
Détecte les vulnérabilités communes et les problèmes de sécurité.
"""

import os
import re
import ast
import json
from pathlib import Path
from typing import List, Dict, Any, Set
import subprocess
import sys

class SecurityIssue:
    def __init__(self, severity: str, category: str, file_path: str, line: int, 
                 description: str, code: str = "", fix: str = ""):
        self.severity = severity  # CRITICAL, HIGH, MEDIUM, LOW
        self.category = category  # SECURITY, BUG, PERFORMANCE, ARCHITECTURE
        self.file_path = file_path
        self.line = line
        self.description = description
        self.code = code
        self.fix = fix
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "category": self.category,
            "file": self.file_path,
            "line": self.line,
            "description": self.description,
            "code": self.code,
            "fix": self.fix
        }

class SecurityScanner:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.issues: List[SecurityIssue] = []
        
        # Patterns de sécurité à détecter
        self.security_patterns = {
            # Injection SQL
            r'execute\s*\(\s*["\'].*\+.*["\']': {
                'severity': 'CRITICAL',
                'category': 'SECURITY',
                'description': 'Potential SQL injection via string concatenation'
            },
            r'execute\s*\(\s*f["\']': {
                'severity': 'CRITICAL', 
                'category': 'SECURITY',
                'description': 'Potential SQL injection via f-string'
            },
            
            # Credentials hardcodés
            r'password\s*=\s*["\'][^"\']+["\']': {
                'severity': 'CRITICAL',
                'category': 'SECURITY', 
                'description': 'Hardcoded password detected'
            },
            r'api_key\s*=\s*["\'][^"\']+["\']': {
                'severity': 'CRITICAL',
                'category': 'SECURITY',
                'description': 'Hardcoded API key detected'
            },
            r'secret\s*=\s*["\'][^"\']+["\']': {
                'severity': 'CRITICAL',
                'category': 'SECURITY',
                'description': 'Hardcoded secret detected'
            },
            
            # CORS dangereux
            r'allow_origins\s*=\s*\[\s*["\*"\']\s*\]': {
                'severity': 'CRITICAL',
                'category': 'SECURITY',
                'description': 'Wildcard CORS origin allows any domain'
            },
            
            # Debug en production
            r'debug\s*=\s*True': {
                'severity': 'HIGH',
                'category': 'SECURITY',
                'description': 'Debug mode enabled - may leak sensitive information'
            },
            
            # Exceptions exposant des infos
            r'raise\s+Exception\s*\(\s*f["\'].*\{.*\}': {
                'severity': 'HIGH',
                'category': 'SECURITY',
                'description': 'Exception may expose sensitive information via f-string'
            },
            
            # Eval/exec dangereux
            r'\beval\s*\(': {
                'severity': 'CRITICAL',
                'category': 'SECURITY',
                'description': 'Use of eval() can lead to code injection'
            },
            r'\bexec\s*\(': {
                'severity': 'CRITICAL',
                'category': 'SECURITY',
                'description': 'Use of exec() can lead to code injection'
            },
            
            # Shell injection
            r'subprocess\.(call|run|Popen).*shell\s*=\s*True': {
                'severity': 'CRITICAL',
                'category': 'SECURITY',
                'description': 'Shell injection vulnerability in subprocess call'
            },
            
            # Pickle dangereux
            r'pickle\.loads?\s*\(': {
                'severity': 'HIGH',
                'category': 'SECURITY',
                'description': 'Pickle deserialization can lead to code execution'
            },
            
            # TODO/FIXME non traités
            r'#\s*(TODO|FIXME|HACK|XXX)': {
                'severity': 'MEDIUM',
                'category': 'ARCHITECTURE',
                'description': 'Unresolved technical debt comment'
            },
            
            # Fonctions trop longues
            r'^def\s+\w+.*:$': {  # Sera traité spécialement
                'severity': 'MEDIUM',
                'category': 'ARCHITECTURE',
                'description': 'Function may be too long'
            }
        }
    
    def scan_file(self, file_path: Path) -> None:
        """Scanne un fichier Python pour les problèmes de sécurité."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Scanner avec regex
            self._scan_with_patterns(file_path, lines)
            
            # Scanner avec AST pour analyse plus profonde
            try:
                tree = ast.parse(content)
                self._scan_with_ast(file_path, tree, lines)
            except SyntaxError:
                self.issues.append(SecurityIssue(
                    'HIGH', 'BUG', str(file_path), 1,
                    'Syntax error in Python file'
                ))
                
        except Exception as e:
            self.issues.append(SecurityIssue(
                'MEDIUM', 'BUG', str(file_path), 1,
                f'Error scanning file: {e}'
            ))
    
    def _scan_with_patterns(self, file_path: Path, lines: List[str]) -> None:
        """Scanne avec des patterns regex."""
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            for pattern, issue_info in self.security_patterns.items():
                if re.search(pattern, line, re.IGNORECASE):
                    self.issues.append(SecurityIssue(
                        issue_info['severity'],
                        issue_info['category'],
                        str(file_path),
                        line_num,
                        issue_info['description'],
                        line_stripped
                    ))
    
    def _scan_with_ast(self, file_path: Path, tree: ast.AST, lines: List[str]) -> None:
        """Scanne avec l'AST Python."""
        
        class SecurityVisitor(ast.NodeVisitor):
            def __init__(self, scanner, file_path, lines):
                self.scanner = scanner
                self.file_path = file_path
                self.lines = lines
            
            def visit_FunctionDef(self, node):
                # Vérifier la longueur des fonctions
                if hasattr(node, 'end_lineno') and node.end_lineno:
                    func_length = node.end_lineno - node.lineno
                    if func_length > 50:
                        self.scanner.issues.append(SecurityIssue(
                            'MEDIUM', 'ARCHITECTURE', str(self.file_path), node.lineno,
                            f'Function "{node.name}" is {func_length} lines long (>50)',
                            f'def {node.name}(...): # {func_length} lines'
                        ))
                
                # Vérifier la complexité cyclomatique
                complexity = self._calculate_complexity(node)
                if complexity > 10:
                    self.scanner.issues.append(SecurityIssue(
                        'MEDIUM', 'ARCHITECTURE', str(self.file_path), node.lineno,
                        f'Function "{node.name}" has high complexity ({complexity})',
                        f'def {node.name}(...): # complexity: {complexity}'
                    ))
                
                self.generic_visit(node)
            
            def visit_Call(self, node):
                # Vérifier les appels dangereux
                if isinstance(node.func, ast.Name):
                    if node.func.id in ['eval', 'exec']:
                        self.scanner.issues.append(SecurityIssue(
                            'CRITICAL', 'SECURITY', str(self.file_path), node.lineno,
                            f'Dangerous function call: {node.func.id}()',
                            self.lines[node.lineno - 1].strip() if node.lineno <= len(self.lines) else ''
                        ))
                
                self.generic_visit(node)
            
            def visit_Str(self, node):
                # Vérifier les chaînes suspectes
                if isinstance(node.s, str):
                    # Mots de passe en dur
                    if re.search(r'(password|passwd|pwd)\s*[:=]\s*\S+', node.s, re.IGNORECASE):
                        self.scanner.issues.append(SecurityIssue(
                            'HIGH', 'SECURITY', str(self.file_path), node.lineno,
                            'Potential hardcoded password in string',
                            node.s[:100] + '...' if len(node.s) > 100 else node.s
                        ))
                
                self.generic_visit(node)
            
            def _calculate_complexity(self, node):
                """Calcule la complexité cyclomatique basique."""
                complexity = 1  # Base
                
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                        complexity += 1
                    elif isinstance(child, ast.BoolOp):
                        complexity += len(child.values) - 1
                
                return complexity
        
        visitor = SecurityVisitor(self, file_path, lines)
        visitor.visit(tree)
    
    def scan_directory(self, directory: Path) -> None:
        """Scanne récursivement un répertoire."""
        for file_path in directory.rglob("*.py"):
            if self._should_scan_file(file_path):
                self.scan_file(file_path)
    
    def _should_scan_file(self, file_path: Path) -> bool:
        """Détermine si un fichier doit être scanné."""
        # Ignorer les fichiers de test et les répertoires cachés
        parts = file_path.parts
        ignore_patterns = {'.git', '__pycache__', '.pytest_cache', 'venv', 'env', '.venv'}
        
        for part in parts:
            if part in ignore_patterns or part.startswith('.'):
                return False
        
        return True
    
    def check_dependencies(self) -> None:
        """Vérifie les dépendances pour les vulnérabilités connues."""
        requirements_file = self.project_root / "requirements.txt"
        
        if requirements_file.exists():
            try:
                # Utiliser safety pour vérifier les vulnérabilités
                result = subprocess.run([
                    sys.executable, "-m", "pip", "list", "--format=json"
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    packages = json.loads(result.stdout)
                    # Ici on pourrait intégrer avec une base de vulnérabilités
                    # Pour l'instant, on vérifie juste les versions anciennes
                    
                    old_packages = {
                        'requests': '2.25.0',
                        'urllib3': '1.26.0',
                        'pyyaml': '5.4.0'
                    }
                    
                    for pkg in packages:
                        name = pkg['name'].lower()
                        version = pkg['version']
                        
                        if name in old_packages:
                            self.issues.append(SecurityIssue(
                                'MEDIUM', 'SECURITY', 'requirements.txt', 1,
                                f'Package {name} version {version} may have known vulnerabilities'
                            ))
                            
            except Exception as e:
                self.issues.append(SecurityIssue(
                    'LOW', 'ARCHITECTURE', 'requirements.txt', 1,
                    f'Could not check dependencies: {e}'
                ))
    
    def check_configuration_files(self) -> None:
        """Vérifie les fichiers de configuration pour les problèmes."""
        config_files = [
            'setup_ssl.sh',
            'start.sh',
            'opensky-mcp.service',
            '.env',
            'config.py'
        ]
        
        for config_file in config_files:
            file_path = self.project_root / config_file
            if file_path.exists():
                self._scan_config_file(file_path)
    
    def _scan_config_file(self, file_path: Path) -> None:
        """Scanne un fichier de configuration."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                # Vérifier les credentials hardcodés
                if re.search(r'(password|secret|key|token)\s*[:=]\s*["\']?[^"\'\s]+', line_stripped, re.IGNORECASE):
                    self.issues.append(SecurityIssue(
                        'CRITICAL', 'SECURITY', str(file_path), line_num,
                        'Hardcoded credential detected in configuration',
                        line_stripped
                    ))
                
                # Vérifier les permissions dangereuses
                if 'chmod 777' in line_stripped or 'chmod -R 777' in line_stripped:
                    self.issues.append(SecurityIssue(
                        'HIGH', 'SECURITY', str(file_path), line_num,
                        'Dangerous file permissions (777)',
                        line_stripped
                    ))
                
        except Exception as e:
            self.issues.append(SecurityIssue(
                'LOW', 'BUG', str(file_path), 1,
                f'Error scanning config file: {e}'
            ))
    
    def generate_report(self) -> Dict[str, Any]:
        """Génère un rapport de sécurité."""
        issues_by_severity = {
            'CRITICAL': [i for i in self.issues if i.severity == 'CRITICAL'],
            'HIGH': [i for i in self.issues if i.severity == 'HIGH'],
            'MEDIUM': [i for i in self.issues if i.severity == 'MEDIUM'],
            'LOW': [i for i in self.issues if i.severity == 'LOW']
        }
        
        issues_by_category = {
            'SECURITY': [i for i in self.issues if i.category == 'SECURITY'],
            'BUG': [i for i in self.issues if i.category == 'BUG'],
            'PERFORMANCE': [i for i in self.issues if i.category == 'PERFORMANCE'],
            'ARCHITECTURE': [i for i in self.issues if i.category == 'ARCHITECTURE']
        }
        
        return {
            'summary': {
                'total_issues': len(self.issues),
                'critical': len(issues_by_severity['CRITICAL']),
                'high': len(issues_by_severity['HIGH']),
                'medium': len(issues_by_severity['MEDIUM']),
                'low': len(issues_by_severity['LOW'])
            },
            'by_category': {
                'security': len(issues_by_category['SECURITY']),
                'bugs': len(issues_by_category['BUG']),
                'performance': len(issues_by_category['PERFORMANCE']),
                'architecture': len(issues_by_category['ARCHITECTURE'])
            },
            'issues': [issue.to_dict() for issue in self.issues],
            'recommendations': self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Génère des recommandations basées sur les problèmes trouvés."""
        recommendations = []
        
        critical_count = len([i for i in self.issues if i.severity == 'CRITICAL'])
        if critical_count > 0:
            recommendations.append(f"🚨 {critical_count} problèmes CRITIQUES nécessitent une attention immédiate")
        
        security_count = len([i for i in self.issues if i.category == 'SECURITY'])
        if security_count > 0:
            recommendations.append(f"🔐 {security_count} problèmes de sécurité détectés")
        
        # Recommandations spécifiques
        if any('SQL injection' in i.description for i in self.issues):
            recommendations.append("Implémenter une validation stricte des requêtes SQL")
        
        if any('CORS' in i.description for i in self.issues):
            recommendations.append("Configurer CORS avec des origines spécifiques")
        
        if any('hardcoded' in i.description.lower() for i in self.issues):
            recommendations.append("Externaliser les credentials dans des variables d'environnement")
        
        return recommendations

def main():
    """Point d'entrée principal du scanner."""
    project_root = Path(__file__).parent
    
    print("🔍 Démarrage du scan de sécurité...")
    print(f"📁 Projet: {project_root}")
    
    scanner = SecurityScanner(project_root)
    
    # Scanner les fichiers Python
    scanner.scan_directory(project_root)
    
    # Vérifier les dépendances
    scanner.check_dependencies()
    
    # Vérifier les fichiers de configuration
    scanner.check_configuration_files()
    
    # Générer le rapport
    report = scanner.generate_report()
    
    # Afficher le résumé
    print(f"\n📊 RÉSULTATS DU SCAN:")
    print(f"   Total: {report['summary']['total_issues']} problèmes")
    print(f"   🚨 Critique: {report['summary']['critical']}")
    print(f"   🔶 Élevé: {report['summary']['high']}")
    print(f"   🔸 Moyen: {report['summary']['medium']}")
    print(f"   ℹ️  Faible: {report['summary']['low']}")
    
    print(f"\n📂 PAR CATÉGORIE:")
    print(f"   🔐 Sécurité: {report['by_category']['security']}")
    print(f"   🐛 Bugs: {report['by_category']['bugs']}")
    print(f"   ⚡ Performance: {report['by_category']['performance']}")
    print(f"   🏗️  Architecture: {report['by_category']['architecture']}")
    
    # Afficher les problèmes critiques
    critical_issues = [i for i in scanner.issues if i.severity == 'CRITICAL']
    if critical_issues:
        print(f"\n🚨 PROBLÈMES CRITIQUES:")
        for issue in critical_issues[:10]:  # Top 10
            print(f"   • {issue.file_path}:{issue.line} - {issue.description}")
    
    # Sauvegarder le rapport complet
    report_file = project_root / "security_scan_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 Rapport complet sauvegardé: {report_file}")
    
    # Recommandations
    if report['recommendations']:
        print(f"\n💡 RECOMMANDATIONS:")
        for rec in report['recommendations']:
            print(f"   • {rec}")
    
    return len(critical_issues)

if __name__ == "__main__":
    critical_count = main()
    sys.exit(1 if critical_count > 0 else 0)