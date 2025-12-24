#!/usr/bin/env python
"""Script para mover radicales inestables al blocklist."""
import json
import re

def main():
    # Cargar blocklist
    with open('data/molecules/blocklist.json', 'r', encoding='utf-8') as f:
        blocklist = json.load(f)
    
    blocked_set = set(blocklist['blocked_formulas'])
    
    # Cargar enriched
    with open('data/molecules/enriched_discoveries.json', 'r', encoding='utf-8') as f:
        enriched = json.load(f)
    
    # Identificar nuevos candidatos para blocklist
    new_trash = []
    
    for formula, mol in list(enriched['molecules'].items()):
        name = mol['identity']['names']['es']
        
        # Patrones de radicales inestables
        is_trash = False
        reason = ""
        
        # 1. Moléculas con solo 3 átomos y sin H (muy inestable)
        total_atoms = sum(int(n) for n in re.findall(r'(\d+)', formula))
        has_h = 'H' in formula
        
        # 2. Moléculas con demasiado P o S sin estabilización
        p_match = re.search(r'P(\d+)', formula)
        s_match = re.search(r'S(\d+)', formula)
        p_count = int(p_match.group(1)) if p_match else 0
        s_count = int(s_match.group(1)) if s_match else 0
        
        if p_count >= 3 and total_atoms < 8:
            is_trash = True
            reason = f"P{p_count} inestable"
        
        if s_count >= 4 and total_atoms < 10:
            is_trash = True
            reason = f"S{s_count} inestable"
        
        # 3. Fórmulas ya bloqueadas pero que reaparecieron
        if formula in blocked_set:
            is_trash = True
            reason = "ya bloqueada"
        
        if is_trash and formula not in blocked_set:
            new_trash.append((formula, name, reason))
            blocked_set.add(formula)
    
    print(f"=== NUEVAS MOLECULAS PARA BLOCKLIST ({len(new_trash)}) ===")
    for f, n, r in new_trash:
        print(f"  {f}: {n} ({r})")
    
    # Actualizar blocklist
    blocklist['blocked_formulas'] = sorted(list(blocked_set))
    blocklist['total'] = len(blocked_set)
    
    with open('data/molecules/blocklist.json', 'w', encoding='utf-8') as f:
        json.dump(blocklist, f, indent=2, ensure_ascii=False)
    
    print(f"\nBlocklist actualizada: {blocklist['total']} formulas")

if __name__ == "__main__":
    main()
