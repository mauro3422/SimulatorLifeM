#!/usr/bin/env python
"""
Script final agresivo para limpiar todo lo genérico restante.
"""
import json
import re

def is_generic_final(formula, name):
    """Última pasada de limpieza."""
    name_lower = name.lower()
    
    # Nombres de 4 letras terminados en "al" (Etal, Pral, etc)
    if re.match(r'^[A-Z][a-z]{2}l$', name):
        return True, "Nombre 4 letras -al"
    
    # Amino-silaano y variantes
    if 'silaano' in name_lower or 'silaal' in name_lower:
        return True, "Silaano genérico"
    
    # Fosfo-silaal y variantes  
    if 'fosfo-sila' in name_lower or 'fosfo sila' in name_lower:
        return True, "Fosfo-sila genérico"
        
    # Nombres repetidos idénticos en es/en que son inventados
    # Si termina en vocal + consonante + vocal simple
    if re.match(r'^[A-Z][a-z]{2,4}o$', name) and name_lower not in [
        'azufre', 'fosforo', 'silicio', 'carbono', 'oxigeno', 'nitrogeno',
        'metano', 'etano', 'propano'
    ]:
        return True, f"Nombre corto genérico: {name}"
    
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
        
        is_bad, reason = is_generic_final(formula, name_es)
        
        if is_bad:
            trash.append((formula, name_es, reason))
            blocked_set.add(formula)
        else:
            keep[formula] = mol
    
    print(f"=== LIMPIEZA FINAL ===")
    print(f"Total: {len(enriched['molecules'])}")
    print(f"Genéricos finales: {len(trash)}")
    print(f"A mantener: {len(keep)}")
    
    print(f"\n=== BASURA DETECTADA ===")
    for formula, name, reason in trash:
        print(f"  {formula}: {name} - {reason}")
    
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
    
    # Mostrar las que quedaron
    print(f"\n=== MOLECULAS FINALES ({len(keep)}) ===")
    for formula, mol in keep.items():
        name = mol['identity']['names']['es']
        print(f"  {formula}: {name}")

if __name__ == "__main__":
    main()
