#!/usr/bin/env python
"""
Script para limpiar nombres con prefijos inventados: Tio-, Phospho-, Sila-, etc.
"""
import json
import re

def is_invented_prefix(formula, name):
    """Detecta nombres con prefijos inventados."""
    name_lower = name.lower()
    
    # Prefijos inventados
    prefixes = [
        'tiophospho', 'phosphotio', 'silaphospho', 'phosphosila',
        'tiosila', 'silatthio', 'aminosila', 'silamino',
        'tiometh', 'tioeth', 'tioprop', 'tiobut',
        'phosphometh', 'phosphoeth', 'phosphoprop', 'phosphopent', 'phosphohex',
        'silameth', 'silaeth', 'silaprop',
        'iso-c', 'iso-h',  # Iso-C2H3O4, etc
        'phosphohexol', 'phosphopentol', 'phosphobutol',  # Específicos
    ]
    
    for prefix in prefixes:
        if prefix in name_lower:
            return True, f"Prefijo inventado: {prefix}"
    
    # PhosphoXxxol pattern
    if re.match(r'^Phospho[A-Z][a-z]+ol$', name):
        return True, f"Patron PhosphoXxxol: {name}"
    
    # Nombres que son solo la fórmula o muy similares
    if re.match(r'^[A-Z][a-z]*-[A-Z]\d+', name):
        return True, "Formato Prefix-Formula"
    
    # Nombres "But-silaal", "Prop-fosfoal" etc
    if re.match(r'^(But|Prop|Eth|Meth|Pent|Hex)-', name):
        return True, "Formato abreviado-sufijo"
    
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
        
        is_bad, reason = is_invented_prefix(formula, name_es)
        
        if is_bad:
            trash.append((formula, name_es, reason))
            blocked_set.add(formula)
        else:
            keep[formula] = mol
    
    print(f"=== LIMPIEZA PREFIJOS INVENTADOS ===")
    print(f"Total: {len(enriched['molecules'])}")
    print(f"Con prefijos inventados: {len(trash)}")
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
