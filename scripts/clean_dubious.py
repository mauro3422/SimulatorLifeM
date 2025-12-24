#!/usr/bin/env python
"""
Script para limpiar nombres genéricos dudosos finales.
"""
import json
import re

def is_dubious(formula, name, category):
    """Detecta nombres genéricos dudosos."""
    name_lower = name.lower()
    
    # Si ya fue marcado como discovered, mantener
    if category == 'discovered':
        return False, ""
    
    # Nombres con "Complex" son genéricos
    if 'complex' in name_lower:
        return True, "Nombre Complex genérico"
    
    # Nombres muy cortos genéricos (4 letras terminados en al, ol, one)
    if re.match(r'^[A-Z][a-z]{2,3}(al|ol|ne)$', name) and category == 'emergent':
        return True, f"Nombre corto genérico: {name}"
    
    # Nombres "Azotic Compound" genéricos
    if 'azotic compound' in name_lower:
        return True, "Azotic Compound genérico"
    
    # Ethone, Butone, etc (nombres de cetonas inventados)
    if re.match(r'^[A-Z][a-z]+one$', name) and name_lower not in ['acetone', 'propanone', 'butanone']:
        return True, f"Cetona genérica: {name}"
    
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
        category = mol['identity'].get('category', 'unknown')
        
        is_bad, reason = is_dubious(formula, name_es, category)
        
        if is_bad:
            trash.append((formula, name_es, reason))
            blocked_set.add(formula)
        else:
            keep[formula] = mol
    
    print(f"=== LIMPIEZA FINAL DUDOSOS ===")
    print(f"Total: {len(enriched['molecules'])}")
    print(f"Dudosos detectados: {len(trash)}")
    print(f"A mantener: {len(keep)}")
    
    print(f"\n=== BASURA DETECTADA ===")
    for formula, name, reason in trash[:30]:
        print(f"  {formula}: {name} - {reason}")
    if len(trash) > 30:
        print(f"  ... y {len(trash)-30} más")
    
    # Aplicar
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
