#!/usr/bin/env python3
"""
Test rapide de la solution SKYFLY-2
"""

import subprocess
import json
import sys

def test_github_cli():
    """Test si GitHub CLI fonctionne"""
    try:
        result = subprocess.run(['gh', '--version'], capture_output=True, text=True, check=True)
        print("✅ GitHub CLI disponible:", result.stdout.strip().split('\n')[0])
        return True
    except:
        print("❌ GitHub CLI non disponible")
        return False

def test_pr_count():
    """Test du nombre de PRs ouvertes"""
    try:
        result = subprocess.run(['gh', 'pr', 'list', '--state', 'open', '--json', 'number'], 
                               capture_output=True, text=True, check=True)
        prs = json.loads(result.stdout)
        count = len(prs)
        print(f"📊 Nombre de PRs ouvertes: {count}")
        
        if count > 5:
            print("⚠️  Problème SKYFLY-2 confirmé: Plus de 5 PRs ouvertes")
            return False
        else:
            print("✅ Nombre de PRs acceptable")
            return True
    except Exception as e:
        print(f"❌ Erreur lors du comptage des PRs: {e}")
        return False

def test_workflow_file():
    """Test si le workflow GitHub Actions existe"""
    import os
    workflow_path = ".github/workflows/pr_management.yml"
    if os.path.exists(workflow_path):
        print("✅ Workflow GitHub Actions configuré")
        return True
    else:
        print("❌ Workflow GitHub Actions manquant")
        return False

def test_pr_tool():
    """Test si l'outil de gestion des PRs existe et est exécutable"""
    import os
    tool_path = "pr_management_tool.py"
    if os.path.exists(tool_path):
        print("✅ Outil de gestion des PRs créé")
        # Test d'import rapide
        try:
            with open(tool_path, 'r') as f:
                content = f.read()
                if "class PRManager" in content and "def fetch_prs" in content:
                    print("✅ Structure de l'outil validée")
                    return True
                else:
                    print("❌ Structure de l'outil incomplète")
                    return False
        except Exception as e:
            print(f"❌ Erreur lors de la validation de l'outil: {e}")
            return False
    else:
        print("❌ Outil de gestion des PRs manquant")
        return False

def main():
    """Test principal"""
    print("🧪 Test de la solution SKYFLY-2: Gestion des Pull Requests")
    print("=" * 60)
    
    tests = [
        ("GitHub CLI", test_github_cli),
        ("Nombre de PRs", test_pr_count),
        ("Workflow GitHub Actions", test_workflow_file),
        ("Outil de gestion des PRs", test_pr_tool)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 Test: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Erreur inattendue: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📋 Résumé des Tests:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Résultat: {passed}/{len(tests)} tests réussis")
    
    if passed == len(tests):
        print("🎉 Solution SKYFLY-2 validée avec succès!")
        return 0
    else:
        print("⚠️  Certains tests ont échoué. Vérifiez la configuration.")
        return 1

if __name__ == "__main__":
    sys.exit(main())