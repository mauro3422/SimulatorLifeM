#!/usr/bin/env python
"""
Script para limpiar moléculas con nombres incorrectos para su fórmula.
"""
import json
import re

# Diccionario de fórmulas correctas para nombres conocidos
CORRECT_FORMULAS = {
    'metano': ['C1H4', 'CH4'],
    'etano': ['C2H6'],
    'propano': ['C3H8'],
    'butano': ['C4H10'],
    'pentano': ['C5H12'],
    'hexano': ['C6H14'],
    'propeno': ['C3H6'],
    'etileno': ['C2H4'],
    'acetileno': ['C2H2'],
}

def is_wrong_name(formula, name):
    """Detecta si el nombre no corresponde a la fórmula."""
    name_lower = name.lower()
    
    for correct_name, valid_formulas in CORRECT_FORMULAS.items():
        if correct_name in name_lower:
            if formula not in valid_formulas:
                return True, f"'{name}' debería ser {valid_formulas}, no {formula}"
    
    # Nombres genéricos cortos de una palabra terminados en "al", "ol", "il"
    if re.match(r'^[A-Z][a-z]{2,5}(al|ol|il)$', name):
        real_names = ['metanol', 'etanol', 'propanol', 'butanol', 'pentanol', 'hexanol',
                      'metanal', 'etanal', 'propanal', 'butanal', 'metil', 'etil', 'propil', 'butil']
        if name_lower not in real_names:
            return True, f"Nombre genérico corto: {name}"
    
    # Nombre genérico de una palabra terminada en "o" o "ato"
    if re.match(r'^[A-Z][a-z]+o$', name) and len(name) <= 8:
        if name.lower() not in ['metano', 'etano', 'propano', 'butano', 'pentano', 'hexano', 
                                 'etileno', 'propeno', 'acetileno', 'ozono', 'agua', 'urea']:
            return True, f"Nombre genérico inventado: {name}"
    
    return False, ""

def main():
    with open('data/molecules/enriched_discoveries.json', 'r', encoding='utf-8') as f:
        enriched = json.load(f)
    
    with open('data/molecules/blocklist.json', 'r', encoding='utf-8') as f:
        blocklist = json.load(f)
    
    blocked_set = set(blocklist['blocked_formulas'])
    
    trash = []
    keep = {}
    
    for formula, mol in enriched['molecules'].items():
        name_es = mol['identity']['names']['es']
        
        is_bad, reason = is_wrong_name(formula, name_es)
        
        if is_bad:
            trash.append((formula, name_es, reason))
            blocked_set.add(formula)
        else:
            keep[formula] = mol
    
    print(f"=== LIMPIEZA DE NOMBRES INCORRECTOS ===")
    print(f"Total: {len(enriched['molecules'])}")
    print(f"Con nombres incorrectos: {len(trash)}")
    print(f"Válidas: {len(keep)}")
    
    print(f"\n=== BASURA DETECTADA ===")
    for formula, name, reason in trash:
        print(f"  {formula}: {name} - {reason}")
    
    # Aplicar cambios
    enriched['molecules'] = keep
    enriched['_meta']['total_molecules'] = len(keep)
    
    with open('data/molecules/enriched_discoveries.json', 'w', encoding='utf-8') as f:
        json.dump(enriched, f, indent=4, ensure_ascii=False)
    
    blocklist['blocked_formulas'] = sorted(list(blocked_set))
    blocklist['total'] = len(blocked_set)
    
    with open('data/molecules/blocklist.json', 'w', encoding='utf-8') as f:
        json.dump(blocklist, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Limpieza aplicada")
    print(f"  Enriched: {len(keep)} moléculas")
    print(f"  Blocklist: {len(blocked_set)} fórmulas")

if __name__ == "__main__":
    main()
